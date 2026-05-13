"""Admin user-management routes."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from ..models.user import User
from ..services.api_key_service import get_api_key_service
from ..services.auth import get_auth_service
from ..services.login_crypto import get_login_crypto_service
from ..utils.errors import NotFoundError, ValidationError
from .decorators import handle_api_errors

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _get_target_user(user_id: int) -> User:
    user = User.get_by_id(int(user_id))
    if not user:
        raise NotFoundError("用户不存在")
    return user


def _resolve_encrypted_or_plain(crypto_service: Any, value: Any, *, required: bool = False) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        if required:
            raise ValidationError("缺少必要字段")
        return ""

    try:
        return crypto_service.decrypt(raw_value).strip()
    except Exception:
        return raw_value


@admin_bp.get("/users")
@handle_api_errors
def list_users() -> Any:
    auth_service = get_auth_service()
    auth_service.require_admin()
    return jsonify({"users": [user.to_public_dict() for user in User.list_all()]})


@admin_bp.post("/users")
@handle_api_errors
def create_user() -> Any:
    auth_service = get_auth_service()
    auth_service.require_admin()
    crypto_service = get_login_crypto_service()
    api_key_service = get_api_key_service()
    data = request.get_json(force=True, silent=True) or {}

    username = _resolve_encrypted_or_plain(crypto_service, data.get("username"), required=True)
    password = _resolve_encrypted_or_plain(crypto_service, data.get("password"), required=True)
    role = auth_service.validate_role(data.get("role") or "user")
    status = auth_service.validate_status(data.get("status") or "active")

    user = auth_service.create_user_account(username, password, role=role, status=status)
    api_key_service.bootstrap_api_keys(int(user.id or 0))
    return jsonify({"success": True, "user": user.to_public_dict()})


@admin_bp.patch("/users/<int:user_id>")
@handle_api_errors
def update_user(user_id: int) -> Any:
    auth_service = get_auth_service()
    current_admin = auth_service.require_admin()
    target_user = _get_target_user(user_id)
    data = request.get_json(force=True, silent=True) or {}

    next_role = data.get("role")
    next_status = data.get("status")
    validated_role = auth_service.validate_role(next_role) if next_role is not None else target_user.role
    validated_status = (
        auth_service.validate_status(next_status) if next_status is not None else target_user.status
    )

    auth_service.ensure_not_last_active_admin(
        target_user,
        next_role=validated_role,
        next_status=validated_status,
    )

    if int(current_admin.id or 0) == int(target_user.id or 0):
        if validated_status != "active":
            raise ValidationError("不能禁用当前登录账号")
        if validated_role != "admin":
            raise ValidationError("不能降级当前登录账号")

    target_user.role = validated_role
    target_user.status = validated_status
    target_user.save()
    if validated_status != "active":
        auth_service.revoke_access_tokens(int(target_user.id or 0))
        auth_service.revoke_all_remember_tokens(int(target_user.id or 0))

    return jsonify({"success": True, "user": target_user.to_public_dict()})


@admin_bp.post("/users/<int:user_id>/reset-password")
@handle_api_errors
def reset_user_password(user_id: int) -> Any:
    auth_service = get_auth_service()
    auth_service.require_admin()
    crypto_service = get_login_crypto_service()
    data = request.get_json(force=True, silent=True) or {}

    password = _resolve_encrypted_or_plain(crypto_service, data.get("password"), required=True)
    confirm_password = _resolve_encrypted_or_plain(
        crypto_service,
        data.get("confirmPassword"),
        required=True,
    )
    if password != confirm_password:
        raise ValidationError("两次输入的密码不一致")

    user = auth_service.admin_reset_password(user_id, password)
    return jsonify({"success": True, "user": user.to_public_dict()})


@admin_bp.delete("/users/<int:user_id>")
@handle_api_errors
def delete_user(user_id: int) -> Any:
    auth_service = get_auth_service()
    current_admin = auth_service.require_admin()
    target_user = _get_target_user(user_id)

    auth_service.ensure_not_last_active_admin(target_user, action="delete")

    if int(current_admin.id or 0) == int(target_user.id or 0):
        raise ValidationError("不能删除当前登录账号")
    auth_service.revoke_access_tokens(int(target_user.id or 0))
    auth_service.revoke_all_remember_tokens(int(target_user.id or 0))
    User.delete_by_id(int(target_user.id or 0))
    return jsonify({"success": True, "message": "用户已删除"})
