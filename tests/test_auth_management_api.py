import importlib
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


def reset_modules():
    import src.config as config_module
    import src.services.auth as auth_module
    import src.services.database as database_module

    config_module._config_instance = None
    auth_module._auth_service = None
    database_module.db_manager = None


def load_app_from_env():
    reset_modules()

    import app as app_module

    app_module = importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return app_module.app


def build_app():
    tmpdir = tempfile.TemporaryDirectory()
    data_dir = Path(tmpdir.name) / "data"
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["DB_PATH"] = str(data_dir / "app.db")
    os.environ["APP_SECRET_KEY"] = "test-secret"
    return tmpdir, load_app_from_env()


def create_legacy_users_table(db_path: Path, users):
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                salt BLOB NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.executemany(
            "INSERT INTO users (username, salt, password_hash, created_at) VALUES (?, ?, ?, ?)",
            users,
        )
        conn.commit()
    finally:
        conn.close()


def create_current_users_table(db_path: Path, users):
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                salt BLOB NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login_at TEXT
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO users (
                username, salt, password_hash, role, status, created_at, last_login_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            users,
        )
        conn.commit()
    finally:
        conn.close()


def build_seeded_user_row(username, password_hash, created_at="2026-01-01T00:00:00+00:00"):
    return (username, b"legacy-salt", password_hash, created_at)


def build_current_user_row(
    username,
    password_hash,
    role,
    status,
    created_at="2026-01-01T00:00:00+00:00",
    last_login_at=None,
):
    return (username, b"current-salt", password_hash, role, status, created_at, last_login_at)


class AuthSchemaTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in (
                "DATA_DIR",
                "DB_PATH",
                "APP_SECRET_KEY",
                "APP_USERNAME",
                "APP_PASSWORD",
                "AUTH_USERNAME",
                "AUTH_PASSWORD",
            )
        }
        os.environ["APP_USERNAME"] = "schema-seed-user"
        os.environ["APP_PASSWORD"] = "schema-seed-password"
        os.environ.pop("AUTH_USERNAME", None)
        os.environ.pop("AUTH_PASSWORD", None)
        self.tmpdir, self.app = build_app()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_default_admin_has_admin_role_and_active_status(self):
        from src.config import get_config
        from src.models.user import User

        config = get_config()
        user = User.get_by_username(config.seed_username)

        self.assertEqual(config.seed_username, "schema-seed-user")
        self.assertEqual(user.role, "admin")
        self.assertEqual(user.status, "active")

    def test_remember_tokens_table_is_initialized(self):
        from src.services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("remember_tokens",),
        )

        self.assertIsNotNone(row)

    def test_remember_tokens_token_hash_has_unique_lookup_index(self):
        from src.services.database import get_db_manager

        db = get_db_manager()
        indexes = db.fetch_all("PRAGMA index_list(remember_tokens)")

        token_hash_indexes = []
        for index in indexes:
            columns = db.fetch_all(f"PRAGMA index_info({index['name']})")
            if [column["name"] for column in columns] == ["token_hash"]:
                token_hash_indexes.append(index)

        self.assertTrue(token_hash_indexes)
        self.assertTrue(any(index["unique"] for index in token_hash_indexes))


class AuthSchemaMigrationTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in (
                "DATA_DIR",
                "DB_PATH",
                "APP_SECRET_KEY",
                "AUTH_USERNAME",
                "AUTH_PASSWORD",
                "APP_USERNAME",
                "APP_PASSWORD",
            )
        }

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_existing_legacy_users_table_is_migrated_and_backfilled_for_seed_user(self):
        from src.models.user import User

        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        data_dir = Path(tmpdir.name) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "app.db"
        os.environ["DATA_DIR"] = str(data_dir)
        os.environ["DB_PATH"] = str(db_path)
        os.environ["APP_SECRET_KEY"] = "test-secret"
        os.environ["APP_USERNAME"] = "seed-user"
        os.environ["APP_PASSWORD"] = "banana123"

        password_hash = User.hash_password("banana123", b"legacy-salt")
        create_legacy_users_table(
            db_path,
            [
                build_seeded_user_row("seed-user", password_hash),
                build_seeded_user_row("other-user", password_hash),
            ],
        )

        reset_modules()
        from src.services.database import get_db_manager
        from src.models.user import User as ReloadedUser

        db = get_db_manager()
        columns = {row["name"] for row in db.fetch_all("PRAGMA table_info(users)")}
        seed_user = ReloadedUser.get_by_username("seed-user")
        other_user = ReloadedUser.get_by_username("other-user")

        self.assertIn("role", columns)
        self.assertIn("status", columns)
        self.assertIn("last_login_at", columns)
        self.assertEqual(seed_user.role, "admin")
        self.assertEqual(seed_user.status, "active")
        self.assertEqual(other_user.role, "user")
        self.assertEqual(other_user.status, "active")
        self.assertIsNone(seed_user.last_login_at)

    def test_existing_seeded_user_keeps_stored_role_and_status(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        data_dir = Path(tmpdir.name) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "app.db"
        os.environ["DATA_DIR"] = str(data_dir)
        os.environ["DB_PATH"] = str(db_path)
        os.environ["APP_SECRET_KEY"] = "test-secret"
        os.environ["APP_USERNAME"] = "seed-user"
        os.environ["APP_PASSWORD"] = "banana123"

        create_current_users_table(
            db_path,
            [
                build_current_user_row(
                    "seed-user",
                    "stored-hash",
                    role="viewer",
                    status="disabled",
                )
            ],
        )

        app = load_app_from_env()
        del app

        reset_modules()
        from src.models.user import User

        user = User.get_by_username("seed-user")

        self.assertEqual(user.role, "viewer")
        self.assertEqual(user.status, "disabled")


class RememberLoginFlowTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in (
                "DATA_DIR",
                "DB_PATH",
                "APP_SECRET_KEY",
                "AUTH_TOKEN_TTL_SECONDS",
                "AUTH_REMEMBER_TOKEN_TTL_SECONDS",
            )
        }
        os.environ["AUTH_TOKEN_TTL_SECONDS"] = "1"
        os.environ["AUTH_REMEMBER_TOKEN_TTL_SECONDS"] = "3600"
        self.tmpdir, app = build_app()
        self.client = app.test_client()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_login_with_remember_sets_cookie(self):
        from tests.test_auth_api import encrypt_rsa_oaep

        public_key = self.client.get("/api/auth/public-key").get_json()["publicKey"]
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
                "remember": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        cookie_header = response.headers.get("Set-Cookie", "")
        self.assertIn("matchdrawer_remember_token", cookie_header)

    def test_refresh_issues_new_access_token_from_remember_cookie(self):
        from tests.test_auth_api import encrypt_rsa_oaep

        public_key = self.client.get("/api/auth/public-key").get_json()["publicKey"]
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
                "remember": True,
            },
        )
        self.assertEqual(login_response.status_code, 200)

        refresh_response = self.client.post("/api/auth/refresh")

        self.assertEqual(refresh_response.status_code, 200)
        self.assertIn("token", refresh_response.get_json())

    def test_failed_refresh_clears_stale_remember_cookie(self):
        from src.services.database import get_db_manager
        from tests.test_auth_api import encrypt_rsa_oaep

        public_key = self.client.get("/api/auth/public-key").get_json()["publicKey"]
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
                "remember": True,
            },
        )
        self.assertEqual(login_response.status_code, 200)

        get_db_manager().execute_query("DELETE FROM remember_tokens")

        refresh_response = self.client.post("/api/auth/refresh")

        self.assertEqual(refresh_response.status_code, 401)
        self.assertIn("matchdrawer_remember_token=;", refresh_response.headers.get("Set-Cookie", ""))
        self.assertIn("error", refresh_response.get_json())


class RegistrationAndPasswordChangeTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in ("DATA_DIR", "DB_PATH", "APP_SECRET_KEY")
        }
        self.tmpdir, app = build_app()
        self.client = app.test_client()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_register_creates_normal_active_user(self):
        from src.models.user import User
        from tests.test_auth_api import encrypt_rsa_oaep

        public_key = self.client.get("/api/auth/public-key").get_json()["publicKey"]
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": encrypt_rsa_oaep(public_key, "alice"),
                "password": encrypt_rsa_oaep(public_key, "alice123"),
                "confirmPassword": encrypt_rsa_oaep(public_key, "alice123"),
            },
        )

        self.assertEqual(response.status_code, 200)
        user = User.get_by_username("alice")
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "user")
        self.assertEqual(user.status, "active")

    def test_register_clears_previous_remember_cookie(self):
        from tests.test_auth_api import encrypt_rsa_oaep

        public_key = self.client.get("/api/auth/public-key").get_json()["publicKey"]
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
                "remember": True,
            },
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("matchdrawer_remember_token", login_response.headers.get("Set-Cookie", ""))

        register_response = self.client.post(
            "/api/auth/register",
            json={
                "username": encrypt_rsa_oaep(public_key, "alice"),
                "password": encrypt_rsa_oaep(public_key, "alice123"),
                "confirmPassword": encrypt_rsa_oaep(public_key, "alice123"),
            },
        )

        self.assertEqual(register_response.status_code, 200)
        self.assertIn("matchdrawer_remember_token=;", register_response.headers.get("Set-Cookie", ""))

        refresh_response = self.client.post("/api/auth/refresh")

        self.assertEqual(refresh_response.status_code, 401)
        self.assertIn("error", refresh_response.get_json())

    def test_change_password_requires_old_password_and_invalidates_old_password(self):
        from tests.test_auth_api import encrypt_rsa_oaep

        public_key = self.client.get("/api/auth/public-key").get_json()["publicKey"]
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
            },
        )
        token = login_response.get_json()["token"]

        rejected_response = self.client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "oldPassword": encrypt_rsa_oaep(public_key, "wrong-old-password"),
                "newPassword": encrypt_rsa_oaep(public_key, "banana999"),
                "confirmPassword": encrypt_rsa_oaep(public_key, "banana999"),
            },
        )

        self.assertEqual(rejected_response.status_code, 400)
        self.assertIn("error", rejected_response.get_json())

        change_response = self.client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "oldPassword": encrypt_rsa_oaep(public_key, "banana123"),
                "newPassword": encrypt_rsa_oaep(public_key, "banana999"),
                "confirmPassword": encrypt_rsa_oaep(public_key, "banana999"),
            },
        )

        self.assertEqual(change_response.status_code, 200)

        old_password_retry = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
            },
        )
        new_password_login = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana999"),
            },
        )

        self.assertEqual(old_password_retry.status_code, 401)
        self.assertEqual(new_password_login.status_code, 200)

    def test_change_password_invalidates_session_authentication(self):
        from tests.test_auth_api import encrypt_rsa_oaep

        login_response = self.client.post(
            "/login",
            data={"username": "admin", "password": "banana123"},
        )
        self.assertEqual(login_response.status_code, 200)

        validate_before = self.client.get("/api/auth/validate")
        self.assertEqual(validate_before.status_code, 200)

        public_key = self.client.get("/api/auth/public-key").get_json()["publicKey"]
        change_response = self.client.post(
            "/api/auth/change-password",
            json={
                "oldPassword": encrypt_rsa_oaep(public_key, "banana123"),
                "newPassword": encrypt_rsa_oaep(public_key, "banana999"),
                "confirmPassword": encrypt_rsa_oaep(public_key, "banana999"),
            },
        )
        self.assertEqual(change_response.status_code, 200)

        validate_after = self.client.get("/api/auth/validate")

        self.assertEqual(validate_after.status_code, 401)
        self.assertIn("error", validate_after.get_json())


if __name__ == "__main__":
    unittest.main()
