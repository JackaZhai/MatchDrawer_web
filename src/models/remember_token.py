"""Remember-token persistence model."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from .base import BaseModel


@dataclass
class RememberToken(BaseModel):
    id: Optional[int] = None
    user_id: int = 0
    token_hash: str = ""
    expires_at: str = ""
    created_at: str = ""
    last_used_at: Optional[str] = None
    user_agent: str = ""

    def __init__(
        self,
        id: Optional[int] = None,
        user_id: int = 0,
        token_hash: str = "",
        expires_at: str = "",
        created_at: Optional[str] = None,
        last_used_at: Optional[str] = None,
        user_agent: str = "",
    ):
        self.id = id
        self.user_id = int(user_id)
        self.token_hash = token_hash
        self.expires_at = expires_at
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.last_used_at = last_used_at
        self.user_agent = user_agent or ""

    @classmethod
    def get_table_name(cls) -> str:
        return "remember_tokens"

    @classmethod
    def get_create_table_sql(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS remember_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_used_at TEXT,
            user_agent TEXT DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """

    @classmethod
    def init_table(cls, conn: sqlite3.Connection) -> None:
        conn.execute(cls.get_create_table_sql())
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_remember_tokens_token_hash
            ON remember_tokens(token_hash)
            """
        )

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RememberToken":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            token_hash=row["token_hash"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
            last_used_at=row["last_used_at"],
            user_agent=row["user_agent"] if "user_agent" in row.keys() else "",
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token_hash": self.token_hash,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "user_agent": self.user_agent,
        }
