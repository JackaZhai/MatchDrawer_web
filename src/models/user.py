"""
用户模型
"""

import base64
import os
import sqlite3
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from typing import Dict, List, Optional

from .base import BaseModel


class User(BaseModel):
    """用户模型类"""

    def __init__(
        self,
        id: Optional[int] = None,
        username: str = "",
        salt: bytes = b"",
        password_hash: str = "",
        role: str = "user",
        status: str = "active",
        created_at: Optional[str] = None,
        last_login_at: Optional[str] = None,
    ):
        self.id = id
        self.username = username
        self.salt = salt
        self.password_hash = password_hash
        self.role = role or "user"
        self.status = status or "active"
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.last_login_at = last_login_at

    @classmethod
    def get_table_name(cls) -> str:
        return "users"

    @classmethod
    def get_create_table_sql(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            salt BLOB NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login_at TEXT
        );
        """

    @classmethod
    def init_table(cls, conn: sqlite3.Connection) -> None:
        """Initialize table and backfill auth-management columns for older databases."""
        from ..config import get_config

        conn.execute(cls.get_create_table_sql())

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        added_role = False
        added_status = False
        if "role" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            added_role = True
        if "status" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
            added_status = True
        if "last_login_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")

        conn.execute("UPDATE users SET role = 'user' WHERE role IS NULL OR role = ''")
        conn.execute("UPDATE users SET status = 'active' WHERE status IS NULL OR status = ''")

        if added_role:
            seed_username = get_config().seed_username
            conn.execute(
                "UPDATE users SET role = 'admin' WHERE username = ? AND role = 'user'",
                (seed_username,),
            )

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            username=row["username"],
            salt=row["salt"],
            password_hash=row["password_hash"],
            role=row["role"] if "role" in row.keys() else "user",
            status=row["status"] if "status" in row.keys() else "active",
            created_at=row["created_at"],
            last_login_at=row["last_login_at"] if "last_login_at" in row.keys() else None,
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
        }

    def to_public_dict(self) -> Dict:
        return self.to_dict()

    @staticmethod
    def generate_salt() -> bytes:
        """生成随机盐"""
        return os.urandom(16)

    @staticmethod
    def hash_password(password: str, salt: bytes) -> str:
        """哈希密码"""
        digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return base64.b64encode(digest).decode("utf-8")

    def set_password(self, password: str) -> None:
        """设置密码"""
        self.salt = self.generate_salt()
        self.password_hash = self.hash_password(password, self.salt)

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        if not self.salt or not self.password_hash:
            return False
        return self.hash_password(password, self.salt) == self.password_hash

    @classmethod
    def get_by_username(cls, username: str) -> Optional["User"]:
        """根据用户名获取用户"""
        from ..services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one("SELECT * FROM users WHERE username = ?", (username,))
        return cls.from_row(row) if row else None

    @classmethod
    def get_by_id(cls, user_id: int) -> Optional["User"]:
        """根据ID获取用户"""
        from ..services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return cls.from_row(row) if row else None

    @classmethod
    def list_all(cls) -> List["User"]:
        """List all users for admin management."""
        from ..services.database import get_db_manager

        db = get_db_manager()
        rows = db.fetch_all(
            """
            SELECT * FROM users
            ORDER BY
                CASE role WHEN 'admin' THEN 0 ELSE 1 END,
                created_at ASC,
                id ASC
            """
        )
        return [cls.from_row(row) for row in rows]

    @classmethod
    def count_active_admins(cls) -> int:
        """Count active admin users."""
        from ..services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one(
            "SELECT COUNT(*) AS total FROM users WHERE role = 'admin' AND status = 'active'"
        )
        return int(row["total"] if row else 0)

    @classmethod
    def delete_by_id(cls, user_id: int) -> bool:
        """Delete a user by id."""
        from ..services.database import get_db_manager

        db = get_db_manager()
        return db.execute_query("DELETE FROM users WHERE id = ?", (int(user_id),)) > 0

    def save(self) -> None:
        """保存用户到数据库"""
        from ..services.database import get_db_manager

        db = get_db_manager()

        if self.id is None:
            # 插入新用户
            self.id = db.execute_insert(
                """
                INSERT INTO users (username, salt, password_hash, role, status, last_login_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.username,
                    self.salt,
                    self.password_hash,
                    self.role,
                    self.status,
                    self.last_login_at,
                ),
            )
        else:
            # 更新现有用户
            db.execute_query(
                """
                UPDATE users
                SET username = ?, salt = ?, password_hash = ?, role = ?, status = ?, last_login_at = ?
                WHERE id = ?
                """,
                (
                    self.username,
                    self.salt,
                    self.password_hash,
                    self.role,
                    self.status,
                    self.last_login_at,
                    self.id,
                ),
            )

    @classmethod
    def create_default_user(
        cls,
        username: str,
        password: str,
        role: str = "admin",
        status: str = "active",
    ) -> "User":
        """创建默认用户"""
        user = cls(username=username, role=role, status=status)
        user.set_password(password)
        user.save()
        return user

    @classmethod
    def ensure_default_user(
        cls, username: Optional[str] = None, password: Optional[str] = None
    ) -> "User":
        """确保默认用户存在"""
        from ..config import get_config

        config = get_config()

        default_username = username or config.seed_username
        default_password = password or config.seed_password

        user = cls.get_by_username(default_username)
        if not user:
            user = cls.create_default_user(
                default_username,
                default_password,
                role="admin",
                status="active",
            )
        return user
