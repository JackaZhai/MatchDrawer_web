"""Authentication routes."""

import ipaddress
import json
from typing import Any
from urllib.parse import urlencode, urlsplit

from flask import Blueprint, jsonify, make_response, redirect, render_template, request, url_for

from ..services.api_key_service import get_api_key_service
from ..services.auth import REMEMBER_COOKIE_NAME, get_auth_service
from ..services.login_crypto import get_login_crypto_service
from ..utils.errors import AuthenticationError, ValidationError
from .decorators import handle_api_errors

# 创建认证蓝图
auth_bp = Blueprint("auth", __name__)


def _wants_remember_login(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _json_script_literal(value: str) -> str:
    return (
        json.dumps(str(value))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _resolve_next_url(raw_next: Any) -> str:
    candidate = str(raw_next or "").strip()
    if not candidate:
        return url_for("main.index")

    parts = urlsplit(candidate)
    if parts.scheme or parts.netloc or not candidate.startswith("/") or candidate.startswith("//"):
        return url_for("main.index")
    return candidate


def _is_local_fallback_request() -> bool:
    hostname = (urlsplit(f"//{request.host}").hostname or "").strip().lower()
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _build_external_callback_url(auth_service: Any, next_url: str) -> str:
    callback_path = url_for("auth.newapi_sso_callback", next=next_url)
    public_base_url = str(auth_service.config.public_base_url or "").rstrip("/")
    if public_base_url:
        return f"{public_base_url}{callback_path}"

    scheme = "https" if request.host.endswith(".happyresearch.xyz") else request.scheme
    return url_for("auth.newapi_sso_callback", _external=True, _scheme=scheme, next=next_url)


def _remember_cookie_kwargs(auth_service: Any) -> dict[str, Any]:
    return {
        "httponly": True,
        "samesite": "Lax",
        "secure": auth_service.config.cookie_secure or request.is_secure,
    }


def _clear_remember_cookie(response: Any, auth_service: Any) -> Any:
    response.delete_cookie(REMEMBER_COOKIE_NAME, **_remember_cookie_kwargs(auth_service))
    return response


def _build_login_success_response(token: str, next_url: str) -> str:
    token_literal = _json_script_literal(token)
    next_literal = _json_script_literal(next_url)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<script>"
        "localStorage.setItem('matchdrawer_auth_token_v1', "
        f"{token_literal});"
        f"window.location.replace({next_literal});"
        "</script></head><body></body></html>"
    )


def _revoke_current_access_tokens(auth_service: Any) -> None:
    user_id = auth_service.get_current_user_id()
    if user_id:
        auth_service.revoke_access_tokens(int(user_id))


@auth_bp.get("/api/auth/newapi/start")
def newapi_sso_start() -> Any:
    """Start New API SSO by redirecting to the central gateway."""
    auth_service = get_auth_service()
    next_url = _resolve_next_url(request.args.get("next"))
    if not auth_service.config.newapi_sso_enabled or not auth_service.config.newapi_sso_authorize_url:
        return redirect(url_for("auth.login", sso="0", next=next_url))

    callback_url = _build_external_callback_url(auth_service, next_url)
    separator = "&" if "?" in auth_service.config.newapi_sso_authorize_url else "?"
    return redirect(
        f"{auth_service.config.newapi_sso_authorize_url}"
        f"{separator}{urlencode({'redirect_uri': callback_url})}"
    )


@auth_bp.get("/api/auth/newapi/callback")
def newapi_sso_callback() -> Any:
    """Exchange a New API SSO token for a MatchDrawer access token."""
    auth_service = get_auth_service()
    next_url = _resolve_next_url(request.args.get("next"))
    token = request.args.get("token") or ""
    try:
        user = auth_service.verify_newapi_sso_token(token)
    except AuthenticationError:
        return redirect(url_for("auth.login", sso="0", next=next_url))

    user_id = int(user.id or 0)
    if not user_id:
        return redirect(url_for("auth.login", sso="0", next=next_url))

    auth_timestamp = auth_service._utcnow()
    auth_service.login_user(user_id, user.username, issued_at=auth_timestamp)

    api_key_service = get_api_key_service()
    api_key_service.bootstrap_api_keys(user_id)

    return _build_login_success_response(
        auth_service.issue_token(user_id, user.username, issued_at=auth_timestamp),
        next_url,
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """登录页面"""
    auth_service = get_auth_service()
    error: str = ""
    next_url = _resolve_next_url(request.args.get("next"))
    local_fallback_requested = request.args.get("sso") == "0"

    if (
        auth_service.config.newapi_sso_enabled
        and local_fallback_requested
        and not _is_local_fallback_request()
    ):
        return redirect(url_for("auth.newapi_sso_start", next=next_url))

    if request.method == "POST":
        if auth_service.config.newapi_sso_enabled and request.args.get("sso") != "0":
            error = "请通过 New API 统一登录入口访问"
            return render_template("login.html", error=error, next_url=request.args.get("next") or "")

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        # 检查登录尝试
        allowed, lock_error = auth_service.check_login_attempts(username)
        if not allowed:
            return render_template("login.html", error=lock_error)

        # 验证凭证
        user_id = auth_service.verify_credentials(username, password)
        if user_id:
            # 登录成功
            auth_timestamp = auth_service._utcnow()
            auth_service.login_user(user_id, username, issued_at=auth_timestamp)

            # 引导API密钥
            api_key_service = get_api_key_service()
            api_key_service.bootstrap_api_keys(user_id)

            return _build_login_success_response(
                auth_service.issue_token(user_id, username, issued_at=auth_timestamp),
                next_url,
            )
        else:
            # 登录失败
            error = auth_service.record_failed_attempt(username)
    elif auth_service.config.newapi_sso_enabled and request.args.get("sso") != "0":
        return redirect(url_for("auth.newapi_sso_start", next=next_url))


    return render_template("login.html", error=error, next_url=request.args.get("next") or "")


@auth_bp.get("/api/auth/public-key")
@handle_api_errors
def auth_public_key() -> Any:
    """Return the RSA public key for frontend login encryption."""
    crypto_service = get_login_crypto_service()
    return jsonify({"publicKey": crypto_service.get_public_key_pem()})


@auth_bp.post("/api/auth/login")
@handle_api_errors
def auth_login() -> Any:
    """Login with RSA-encrypted credentials and return a bearer token."""
    auth_service = get_auth_service()
    api_key_service = get_api_key_service()
    crypto_service = get_login_crypto_service()
    data = request.get_json(force=True, silent=True) or {}

    encrypted_username = data.get("username") or ""
    encrypted_password = data.get("password") or ""

    username = crypto_service.decrypt(encrypted_username).strip()
    password = crypto_service.decrypt(encrypted_password)

    allowed, lock_error = auth_service.check_login_attempts(username)
    if not allowed:
        raise AuthenticationError(lock_error or "账号已锁定")

    user_id = auth_service.verify_credentials(username, password)
    if not user_id:
        raise AuthenticationError(auth_service.record_failed_attempt(username))

    api_key_service.bootstrap_api_keys(user_id)
    token = auth_service.issue_token(user_id, username)
    remember = _wants_remember_login(data.get("remember"))
    response = jsonify(
        {
            "success": True,
            "message": "登录成功",
            "token": token,
            "user": {"id": user_id, "username": username},
            "expiresIn": auth_service.config.auth_token_ttl_seconds,
        }
    )
    if remember:
        auth_service.revoke_remember_token(request.cookies.get(REMEMBER_COOKIE_NAME, ""))
        remember_token = auth_service.issue_remember_token(
            user_id,
            request.headers.get("User-Agent", ""),
        )
        response.set_cookie(
            REMEMBER_COOKIE_NAME,
            remember_token,
            max_age=auth_service.config.auth_remember_token_ttl_seconds,
            **_remember_cookie_kwargs(auth_service),
        )
    else:
        auth_service.revoke_remember_token(request.cookies.get(REMEMBER_COOKIE_NAME, ""))
        _clear_remember_cookie(response, auth_service)
    return response


@auth_bp.post("/api/auth/register")
@handle_api_errors
def auth_register() -> Any:
    """Register a new user and issue an access token."""
    auth_service = get_auth_service()
    api_key_service = get_api_key_service()
    crypto_service = get_login_crypto_service()
    data = request.get_json(force=True, silent=True) or {}

    username = crypto_service.decrypt(data.get("username") or "").strip()
    password = crypto_service.decrypt(data.get("password") or "")
    confirm_password = crypto_service.decrypt(data.get("confirmPassword") or "")
    if password != confirm_password:
        raise ValidationError("两次输入的密码不一致")

    user = auth_service.register_user(username, password)
    api_key_service.bootstrap_api_keys(int(user.id or 0))
    auth_service.revoke_remember_token(request.cookies.get(REMEMBER_COOKIE_NAME, ""))
    token = auth_service.issue_token(int(user.id or 0), user.username)
    response = jsonify(
        {
            "success": True,
            "message": "注册成功",
            "token": token,
            "user": {"id": int(user.id or 0), "username": user.username},
            "expiresIn": auth_service.config.auth_token_ttl_seconds,
        }
    )
    return _clear_remember_cookie(response, auth_service)


@auth_bp.post("/api/auth/refresh")
@handle_api_errors
def auth_refresh() -> Any:
    """Refresh an access token from the remember-login cookie."""
    auth_service = get_auth_service()
    try:
        payload = auth_service.refresh_access_token(request.cookies.get(REMEMBER_COOKIE_NAME, ""))
    except AuthenticationError as exc:
        response = jsonify(exc.to_dict())
        response.status_code = exc.status_code
        return _clear_remember_cookie(response, auth_service)
    return jsonify(
        {
            "success": True,
            "message": "刷新成功",
            **payload,
            "expiresIn": auth_service.config.auth_token_ttl_seconds,
        }
    )


@auth_bp.post("/api/auth/change-password")
@handle_api_errors
def auth_change_password() -> Any:
    """Allow the current authenticated user to change their own password."""
    auth_service = get_auth_service()
    crypto_service = get_login_crypto_service()
    user_id = auth_service.require_auth()
    data = request.get_json(force=True, silent=True) or {}

    old_password = crypto_service.decrypt(data.get("oldPassword") or "")
    new_password = crypto_service.decrypt(data.get("newPassword") or "")
    confirm_password = crypto_service.decrypt(data.get("confirmPassword") or "")
    if new_password != confirm_password:
        raise ValidationError("两次输入的密码不一致")

    auth_service.change_password(user_id, old_password, new_password)
    auth_service.revoke_access_tokens(user_id)
    auth_service.logout_user()
    response = jsonify({"success": True, "message": "密码修改成功"})
    return _clear_remember_cookie(response, auth_service)


@auth_bp.post("/api/auth/logout")
@handle_api_errors
def auth_logout() -> Any:
    """Logout an authenticated API user and revoke existing bearer tokens."""
    auth_service = get_auth_service()
    auth_service.require_auth()
    _revoke_current_access_tokens(auth_service)
    auth_service.revoke_remember_token(request.cookies.get(REMEMBER_COOKIE_NAME, ""))
    auth_service.logout_user()
    response = jsonify({"success": True, "message": "退出成功"})
    return _clear_remember_cookie(response, auth_service)


@auth_bp.get("/api/auth/validate")
@handle_api_errors
def auth_validate() -> Any:
    """Validate the current bearer token."""
    auth_service = get_auth_service()
    user_id = auth_service.require_auth()
    username = auth_service.get_current_username() or ""
    return jsonify(
        {
            "authenticated": True,
            "user": {"id": user_id, "username": username},
            "expiresIn": auth_service.config.auth_token_ttl_seconds,
        }
    )


@auth_bp.get("/logout")
def logout() -> Any:
    """登出"""
    auth_service = get_auth_service()
    _revoke_current_access_tokens(auth_service)
    auth_service.revoke_remember_token(request.cookies.get(REMEMBER_COOKIE_NAME, ""))
    auth_service.logout_user()
    login_url = url_for("auth.login")
    response = make_response(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<script>"
        "localStorage.removeItem('matchdrawer_auth_token_v1');"
        f"window.location.replace({login_url!r});"
        "</script></head><body></body></html>"
    )
    return _clear_remember_cookie(response, auth_service)
