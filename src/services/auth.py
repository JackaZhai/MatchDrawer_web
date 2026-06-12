"""Authentication service."""

from __future__ import annotations

import hashlib
import re
import secrets
import time

import requests
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from flask import g, has_request_context, request, session
from itsdangerous import BadSignature, URLSafeTimedSerializer

from ..config import get_config
from ..models.remember_token import RememberToken
from ..models.user import User
from ..utils.errors import ApiError, AuthenticationError, NotFoundError, ValidationError
from .database import get_db_manager

TOKEN_SALT = "matchdrawer-auth-token-v1"
REMEMBER_COOKIE_NAME = "matchdrawer_remember_token"


class AuthService:
    """认证服务"""

    USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
    VALID_ROLES = {"admin", "user"}
    VALID_STATUSES = {"active", "disabled"}

    def __init__(self):
        self.config = get_config()
        self.login_attempts: Dict[str, Dict[str, Any]] = {}
        self.serializer = URLSafeTimedSerializer(self.config.app_secret_key, salt=TOKEN_SALT)

    def verify_credentials(self, username: str, password: str) -> Optional[int]:
        """验证用户凭证"""
        # 确保默认用户存在，作为 New API 不可用时的本地管理员兜底。
        User.ensure_default_user()

        username = str(username or "").strip()
        password = str(password or "")

        if self.config.newapi_auth_enabled:
            newapi_user, upstream_available = self._verify_newapi_credentials(username, password)
            if newapi_user:
                synced_user = self._sync_newapi_user(username, newapi_user)
                if synced_user and synced_user.status == "active":
                    return synced_user.id
                return None

            # New API 是主认证源；仅保留本地种子管理员作为故障兜底。
            if username != self.config.seed_username:
                return None
            if upstream_available:
                return self._verify_local_seed_admin(username, password)

        return self._verify_local_seed_admin(username, password)

    def _verify_local_seed_admin(self, username: str, password: str) -> Optional[int]:
        """Verify the local seeded admin account used as an emergency fallback."""
        user = User.get_by_username(username)
        if not user:
            return None
        if user.status != "active":
            return None
        if not user.verify_password(password):
            return None
        return user.id

    def _verify_newapi_credentials(
        self, username: str, password: str
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Validate credentials against New API and return its user payload."""
        base_url = str(self.config.newapi_base_url or "").rstrip("/")
        if not base_url:
            return None, False

        try:
            response = requests.post(
                f"{base_url}/api/user/login",
                json={"username": username, "password": password},
                timeout=float(self.config.newapi_auth_timeout_seconds),
            )
            upstream_available = True
            if response.status_code >= 500:
                return None, False
            payload = response.json()
        except (requests.RequestException, ValueError):
            return None, False

        if not payload.get("success"):
            return None, upstream_available

        data = payload.get("data") or {}
        if not isinstance(data, dict):
            return None, upstream_available
        return data, upstream_available

    def _sync_newapi_user(self, fallback_username: str, newapi_user: Dict[str, Any]) -> Optional[User]:
        """Create or update a local Matchdrawer user from New API login data."""
        username = str(newapi_user.get("username") or fallback_username or "").strip()
        if not username:
            return None

        try:
            newapi_role = int(newapi_user.get("role") or 0)
        except (TypeError, ValueError):
            newapi_role = 0
        try:
            newapi_status = int(newapi_user.get("status") or 0)
        except (TypeError, ValueError):
            newapi_status = 0

        role = "admin" if newapi_role >= self.config.newapi_admin_role_threshold else "user"
        status = "active" if newapi_status == 1 else "disabled"

        user = User.get_by_username(username)
        if not user:
            user = User(username=username, role=role, status=status)
            user.set_password(secrets.token_urlsafe(32))
        else:
            user.role = role
            user.status = status
        user.save()
        return user

    @classmethod
    def validate_username(cls, username: str) -> str:
        """Validate and normalize a username."""
        normalized = str(username or "").strip()
        if not normalized:
            raise ValidationError("用户名不能为空")
        if not cls.USERNAME_PATTERN.fullmatch(normalized):
            raise ValidationError("用户名需为 3-32 位，仅允许字母、数字、下划线、点和中横线")
        return normalized

    @staticmethod
    def validate_password(password: str) -> str:
        """Validate password length constraints."""
        candidate = str(password or "")
        if not candidate:
            raise ValidationError("密码不能为空")
        if len(candidate) < 6 or len(candidate) > 64:
            raise ValidationError("密码需为 6-64 位")
        return candidate

    @classmethod
    def validate_role(cls, role: str) -> str:
        candidate = str(role or "user").strip().lower() or "user"
        if candidate not in cls.VALID_ROLES:
            raise ValidationError("用户角色无效")
        return candidate

    @classmethod
    def validate_status(cls, status: str) -> str:
        candidate = str(status or "active").strip().lower() or "active"
        if candidate not in cls.VALID_STATUSES:
            raise ValidationError("用户状态无效")
        return candidate

    def check_login_attempts(self, username: str) -> Tuple[bool, Optional[str]]:
        """检查登录尝试次数"""
        attempt = self.login_attempts.get(username, {"count": 0, "locked_until": None})
        locked_until = attempt.get("locked_until")
        now = datetime.now(timezone.utc)

        if locked_until and locked_until > now:
            remaining = int((locked_until - now).total_seconds() // 60) + 1
            return False, f"账号已锁定，请 {remaining} 分钟后重试"

        return True, None

    def record_failed_attempt(self, username: str) -> str:
        """记录失败的登录尝试"""
        attempt = self.login_attempts.get(username, {"count": 0, "locked_until": None})
        attempt["count"] = attempt.get("count", 0) + 1

        if attempt["count"] >= self.config.max_login_attempts:
            attempt["locked_until"] = datetime.now(timezone.utc) + timedelta(
                minutes=self.config.lock_minutes
            )
            error_msg = f"错误次数过多，已锁定 {self.config.lock_minutes} 分钟"
        else:
            remaining = self.config.max_login_attempts - attempt["count"]
            error_msg = f"用户名或密码错误，剩余重试次数 {remaining} 次"

        self.login_attempts[username] = attempt
        return error_msg

    def clear_login_attempts(self, username: str) -> None:
        """清除登录尝试记录"""
        self.login_attempts.pop(username, None)

    def login_user(
        self,
        user_id: int,
        username: str,
        issued_at: Optional[datetime] = None,
    ) -> None:
        """登录用户"""
        issued_at_dt = issued_at or self._utcnow()
        session["authenticated"] = True
        session["user_id"] = user_id
        session["username"] = username
        session["auth_issued_at"] = issued_at_dt.isoformat()
        self.clear_login_attempts(username)

    def logout_user(self) -> None:
        """登出用户"""
        session.clear()
        if has_request_context():
            g.pop("_auth_context", None)

    def _set_user_last_login_at(self, user_id: int, timestamp: datetime) -> None:
        user = User.get_by_id(int(user_id))
        if not user:
            raise AuthenticationError("登录用户不存在，请重新登录")
        user.last_login_at = timestamp.isoformat()
        user.save()

    def issue_token(
        self,
        user_id: int,
        username: str,
        issued_at: Optional[datetime] = None,
    ) -> str:
        """Issue a signed auth token for frontend storage."""
        self.clear_login_attempts(username)
        issued_at_dt = issued_at or self._utcnow()
        issued_at = issued_at_dt.timestamp()
        self._set_user_last_login_at(int(user_id), issued_at_dt)
        return self.serializer.dumps(
            {"uid": int(user_id), "username": username, "iat": issued_at}
        )

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    def _future_timestamp(self, ttl_seconds: int) -> str:
        return (self._utcnow() + timedelta(seconds=int(ttl_seconds))).isoformat()

    def _parse_timestamp(self, raw_timestamp: str) -> Optional[datetime]:
        value = str(raw_timestamp or "").strip()
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def issue_remember_token(self, user_id: int, user_agent: str = "") -> str:
        """Create and persist a remember-login token."""
        raw_token = secrets.token_urlsafe(48)
        token_hash = self._hash_token(raw_token)
        db = get_db_manager()
        db.execute_insert(
            """
            INSERT INTO remember_tokens (user_id, token_hash, expires_at, user_agent)
            VALUES (?, ?, ?, ?)
            """,
            (
                int(user_id),
                token_hash,
                self._future_timestamp(self.config.auth_remember_token_ttl_seconds),
                (user_agent or "")[:255],
            ),
        )
        return raw_token

    def revoke_remember_token(self, remember_token: str) -> None:
        """Delete a single remember token by its raw value."""
        raw_token = str(remember_token or "").strip()
        if not raw_token:
            return
        get_db_manager().execute_query(
            "DELETE FROM remember_tokens WHERE token_hash = ?",
            (self._hash_token(raw_token),),
        )

    def revoke_all_remember_tokens(self, user_id: int) -> None:
        """Delete all remember tokens for a user."""
        if not user_id:
            return
        get_db_manager().execute_query(
            "DELETE FROM remember_tokens WHERE user_id = ?",
            (int(user_id),),
        )

    def revoke_access_tokens(self, user_id: int) -> None:
        """Revoke existing bearer tokens for a user."""
        if not user_id:
            return
        self._set_user_last_login_at(int(user_id), self._utcnow())

    def create_user_account(
        self,
        username: str,
        password: str,
        role: str = "user",
        status: str = "active",
    ) -> User:
        """Create a user account with validated role/status."""
        normalized = self.validate_username(username)
        validated_password = self.validate_password(password)
        validated_role = self.validate_role(role)
        validated_status = self.validate_status(status)
        if User.get_by_username(normalized):
            raise ValidationError("用户名已存在")

        user = User(username=normalized, role=validated_role, status=validated_status)
        user.set_password(validated_password)
        user.save()
        return user

    def register_user(self, username: str, password: str) -> User:
        """Register a new active normal user."""
        return self.create_user_account(username, password, role="user", status="active")

    def change_password(self, user_id: int, old_password: str, new_password: str) -> None:
        """Change the authenticated user's password after verifying the old password."""
        user = User.get_by_id(int(user_id))
        if not user or user.status != "active":
            raise AuthenticationError("用户不可用")
        if not user.verify_password(str(old_password or "")):
            raise ValidationError("旧密码错误")

        validated_password = self.validate_password(new_password)
        user.set_password(validated_password)
        user.save()
        self.revoke_all_remember_tokens(int(user_id))

    def admin_reset_password(self, target_user_id: int, new_password: str) -> User:
        """Reset another user's password."""
        user = User.get_by_id(int(target_user_id))
        if not user:
            raise NotFoundError("用户不存在")

        user.set_password(self.validate_password(new_password))
        user.save()
        self.revoke_access_tokens(int(user.id or 0))
        self.revoke_all_remember_tokens(int(user.id or 0))
        return user

    def refresh_access_token(self, remember_token: str) -> Dict[str, Any]:
        """Issue a fresh access token from a valid remember token."""
        raw_token = str(remember_token or "").strip()
        if not raw_token:
            raise AuthenticationError("无可用 remember 登录状态，请重新登录")

        db = get_db_manager()
        row = db.fetch_one(
            "SELECT * FROM remember_tokens WHERE token_hash = ?",
            (self._hash_token(raw_token),),
        )
        if not row:
            raise AuthenticationError("无可用 remember 登录状态，请重新登录")

        record = RememberToken.from_row(row)
        expires_at = self._parse_timestamp(record.expires_at)
        if not expires_at or expires_at <= self._utcnow():
            self.revoke_remember_token(raw_token)
            raise AuthenticationError("remember 登录状态已过期，请重新登录")

        user = User.get_by_id(record.user_id)
        if not user or user.status != "active":
            self.revoke_all_remember_tokens(record.user_id)
            raise AuthenticationError("用户不可用，请重新登录")

        db.execute_query(
            "UPDATE remember_tokens SET last_used_at = ? WHERE id = ?",
            (self._utcnow().isoformat(), int(record.id or 0)),
        )
        return {
            "token": self.issue_token(int(user.id or 0), user.username),
            "user": {"id": int(user.id or 0), "username": user.username},
        }

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify a signed auth token and return the user context."""
        raw_token = str(token or "").strip()
        if not raw_token:
            raise AuthenticationError("请先登录")

        try:
            payload = self.serializer.loads(raw_token)
        except BadSignature as exc:
            raise AuthenticationError("登录令牌无效，请重新登录") from exc

        issued_at = float(payload.get("iat") or 0)
        if not issued_at:
            raise AuthenticationError("登录令牌无效，请重新登录")
        if time.time() - issued_at > float(self.config.auth_token_ttl_seconds):
            raise AuthenticationError("登录已过期，请重新登录")

        user_id = int(payload.get("uid") or 0)
        username = str(payload.get("username") or "").strip()
        user = User.get_by_id(user_id) if user_id else None
        if not user:
            raise AuthenticationError("登录用户不存在，请重新登录")
        if user.status != "active":
            raise AuthenticationError("用户不可用，请重新登录")
        token_valid_after = self._parse_timestamp(user.last_login_at or "")
        if token_valid_after and issued_at < token_valid_after.timestamp():
            raise AuthenticationError("登录已失效，请重新登录")
        if username and user.username != username:
            raise AuthenticationError("登录用户信息已变化，请重新登录")

        return {"user_id": int(user.id or 0), "username": user.username, "source": "token"}

    @staticmethod
    def _get_bearer_token() -> Optional[str]:
        if not has_request_context():
            return None
        auth_header = str(request.headers.get("Authorization") or "").strip()
        if not auth_header:
            return None
        if not auth_header.lower().startswith("bearer "):
            raise AuthenticationError("登录令牌格式无效，请重新登录")
        return auth_header[7:].strip()

    def _resolve_auth_context(self) -> Dict[str, Any]:
        if not has_request_context():
            raise AuthenticationError("请先登录")

        cached = getattr(g, "_auth_context", None)
        if cached:
            return cached

        token = self._get_bearer_token()
        if token is not None:
            context = self.verify_token(token)
            g._auth_context = context
            return context

        if session.get("authenticated") and session.get("user_id") is not None:
            user_id = int(session["user_id"])
            user = User.get_by_id(user_id)
            if not user:
                self.logout_user()
                raise AuthenticationError("登录会话无效，请重新登录")
            if user.status != "active":
                self.logout_user()
                raise AuthenticationError("用户不可用，请重新登录")
            session_issued_at = self._parse_timestamp(session.get("auth_issued_at", ""))
            if not session_issued_at:
                self.logout_user()
                raise AuthenticationError("登录会话无效，请重新登录")
            token_valid_after = self._parse_timestamp(user.last_login_at or "")
            if token_valid_after and session_issued_at < token_valid_after:
                self.logout_user()
                raise AuthenticationError("登录已失效，请重新登录")

            context = {"user_id": user_id, "username": user.username, "source": "session"}
            g._auth_context = context
            return context

        raise AuthenticationError("请先登录")

    def is_authenticated(self) -> bool:
        """Check whether the current request is authenticated."""
        try:
            self._resolve_auth_context()
            return True
        except AuthenticationError:
            return False

    def get_current_user_id(self) -> Optional[int]:
        """Get the current authenticated user id."""
        try:
            return int(self._resolve_auth_context()["user_id"])
        except AuthenticationError:
            return None

    def get_current_username(self) -> Optional[str]:
        """获取当前用户名"""
        try:
            return str(self._resolve_auth_context()["username"])
        except AuthenticationError:
            return None

    def get_current_user(self) -> Optional[User]:
        """Get the current authenticated user object."""
        user_id = self.get_current_user_id()
        if not user_id:
            return None
        return User.get_by_id(int(user_id))

    def require_auth(self) -> int:
        """Require authentication and return the current user id."""
        context = self._resolve_auth_context()
        user_id = int(context.get("user_id") or 0)
        if not user_id:
            raise AuthenticationError("登录状态无效，请重新登录")
        return user_id

    def require_admin(self) -> User:
        """Require the current authenticated user to be an active admin."""
        user = self.get_current_user()
        if not user:
            self.require_auth()
            raise AuthenticationError("请先登录")
        if user.role != "admin" or user.status != "active":
            raise ApiError("权限不足", status_code=403)
        return user

    def ensure_not_last_active_admin(
        self,
        target_user: User,
        *,
        next_role: Optional[str] = None,
        next_status: Optional[str] = None,
        action: str = "update",
    ) -> None:
        """Prevent destructive changes to the last active admin."""
        if target_user.role != "admin" or target_user.status != "active":
            return

        resulting_role = (
            self.validate_role(next_role) if next_role is not None else str(target_user.role or "user")
        )
        resulting_status = (
            self.validate_status(next_status)
            if next_status is not None
            else str(target_user.status or "active")
        )
        if action != "delete" and resulting_role == "admin" and resulting_status == "active":
            return
        if User.count_active_admins() > 1:
            return

        if action == "delete":
            raise ValidationError("不能删除最后一个管理员")
        if resulting_status != "active":
            raise ValidationError("不能禁用最后一个管理员")
        if resulting_role != "admin":
            raise ValidationError("不能降级最后一个管理员")
        raise ValidationError("不能修改最后一个管理员")


# 全局认证服务实例
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """获取认证服务实例（单例模式）"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
