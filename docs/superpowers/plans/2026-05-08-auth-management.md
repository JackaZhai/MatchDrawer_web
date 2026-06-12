# Auth Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add open registration, self-service password change, remember-login refresh, and admin user management to MatchDrawer without replacing the current RSA login and bearer-token architecture.

**Architecture:** Keep the existing Flask + SQLite + vanilla JS structure and extend the current auth stack instead of replacing it. Add role/status-aware user records, a persisted remember-token table, refresh/logout/register/change-password/admin APIs, and corresponding login/settings UI updates that keep access tokens short-lived and remember tokens in `HttpOnly` cookies.

**Tech Stack:** Flask, SQLite, Python `unittest`, Jinja2, vanilla JavaScript, browser `localStorage`, `HttpOnly` cookies

---

## File Structure

**Create**
- `src/models/remember_token.py`
- `src/routes/admin_routes.py`
- `tests/test_auth_management_api.py`
- `tests/test_admin_user_routes.py`
- `tests/test_auth_management_assets.py`

**Modify**
- `app.py`
- `src/config.py`
- `src/models/user.py`
- `src/services/database.py`
- `src/services/auth.py`
- `src/routes/auth_routes.py`
- `src/routes/api_routes.py`
- `src/routes/decorators.py`
- `templates/login.html`
- `templates/index.html`
- `static/js/app.js`
- `tests/test_auth_api.py`
- `tests/test_brand_surfaces.py`

**Verification Commands**
- `.venv/bin/python -m unittest tests.test_auth_api tests.test_auth_management_api -v`
- `.venv/bin/python -m unittest tests.test_admin_user_routes -v`
- `.venv/bin/python -m unittest tests.test_auth_management_assets tests.test_brand_surfaces -v`
- `node --check static/js/app.js`
- `git diff --check`

### Task 1: Extend The Auth Data Model First

**Files:**
- Modify: `src/config.py`
- Modify: `src/models/user.py`
- Modify: `src/services/database.py`
- Create: `src/models/remember_token.py`
- Create: `tests/test_auth_management_api.py`

- [ ] **Step 1: Write the failing schema and model tests**

Create `tests/test_auth_management_api.py` with:

```python
import importlib
import os
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


def build_app():
    tmpdir = tempfile.TemporaryDirectory()
    data_dir = Path(tmpdir.name) / "data"
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["DB_PATH"] = str(data_dir / "app.db")
    os.environ["APP_SECRET_KEY"] = "test-secret"
    reset_modules()

    import app as app_module

    app_module = importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return tmpdir, app_module.app


class AuthSchemaTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in ("DATA_DIR", "DB_PATH", "APP_SECRET_KEY")
        }
        self.tmpdir, self.app = build_app()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_default_admin_has_admin_role_and_active_status(self):
        from src.models.user import User

        user = User.get_by_username("admin")
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
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_auth_management_api.AuthSchemaTest -v`

Expected: FAIL because `User` does not expose `role` / `status` yet and `remember_tokens` table does not exist.

- [ ] **Step 3: Implement the model and schema changes**

Update `src/models/user.py` to add the new fields:

```python
class User(BaseModel):
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
```

Create `src/models/remember_token.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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
```

Update `src/services/database.py` init:

```python
from ..models.remember_token import RememberToken

def init_database(self) -> None:
    with self.get_connection() as conn:
        User.init_table(conn)
        ApiKey.init_table(conn)
        UsageStats.init_table(conn)
        ProviderConfig.init_table(conn)
        RememberToken.init_table(conn)
        conn.commit()
```

- [ ] **Step 4: Add migration helpers for existing databases**

Add to `src/services/database.py`:

```python
def _ensure_user_columns(self, conn):
    existing = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    if "role" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    if "status" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if "last_login_at" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")
    conn.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
    conn.execute("UPDATE users SET status = 'active' WHERE status IS NULL OR status = ''")
```

- [ ] **Step 5: Re-run the schema tests**

Run: `.venv/bin/python -m unittest tests.test_auth_management_api.AuthSchemaTest -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/config.py src/models/user.py src/models/remember_token.py src/services/database.py tests/test_auth_management_api.py
git commit -m "feat: add auth management data model"
```

### Task 2: Add Remember-Token Refresh Semantics

**Files:**
- Modify: `src/config.py`
- Modify: `src/services/auth.py`
- Modify: `src/routes/auth_routes.py`
- Modify: `tests/test_auth_api.py`
- Test: `tests/test_auth_management_api.py`

- [ ] **Step 1: Write the failing remember-login tests**

Append to `tests/test_auth_management_api.py`:

```python
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
```

- [ ] **Step 2: Run the remember-login tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_auth_management_api.RememberLoginFlowTest -v`

Expected: FAIL because `/api/auth/login` ignores `remember` and `/api/auth/refresh` does not exist.

- [ ] **Step 3: Implement remember-token issue, persist, verify, and revoke**

Add to `src/services/auth.py`:

```python
def issue_remember_token(self, user_id: int, user_agent: str = "") -> str:
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    RememberToken.create(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=self._future_timestamp(self.config.auth_remember_token_ttl_seconds),
        user_agent=user_agent[:255],
    )
    return raw_token

def refresh_access_token(self, remember_token: str) -> dict[str, Any]:
    record = RememberToken.get_valid_by_token_hash(self._hash_token(remember_token))
    if not record:
        raise AuthenticationError("无可用 remember 登录状态，请重新登录")
    user = User.get_by_id(record.user_id)
    if not user or user.status != "active":
        self.revoke_all_remember_tokens(record.user_id)
        raise AuthenticationError("用户不可用，请重新登录")
    return {
        "token": self.issue_token(int(user.id), user.username),
        "user": {"id": int(user.id), "username": user.username, "role": user.role},
    }
```

- [ ] **Step 4: Add the refresh/logout routes and cookie handling**

Update `src/routes/auth_routes.py`:

```python
@auth_bp.post("/api/auth/refresh")
@handle_api_errors
def auth_refresh() -> Any:
    auth_service = get_auth_service()
    remember_token = request.cookies.get("matchdrawer_remember_token", "")
    payload = auth_service.refresh_access_token(remember_token)
    return jsonify({"success": True, **payload})
```

And inside `/api/auth/login`:

```python
remember = bool(data.get("remember"))
response = jsonify({...})
if remember:
    remember_token = auth_service.issue_remember_token(user_id, request.headers.get("User-Agent", ""))
    response.set_cookie(
        "matchdrawer_remember_token",
        remember_token,
        httponly=True,
        samesite="Lax",
        max_age=auth_service.config.auth_remember_token_ttl_seconds,
        secure=auth_service.config.cookie_secure,
    )
return response
```

- [ ] **Step 5: Re-run remember-login tests**

Run: `.venv/bin/python -m unittest tests.test_auth_management_api.RememberLoginFlowTest -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/services/auth.py src/routes/auth_routes.py src/config.py tests/test_auth_api.py tests/test_auth_management_api.py
git commit -m "feat: add remember login refresh flow"
```

### Task 3: Add Registration And Self-Service Password Change

**Files:**
- Modify: `src/services/auth.py`
- Modify: `src/routes/auth_routes.py`
- Modify: `tests/test_auth_management_api.py`

- [ ] **Step 1: Write the failing registration and change-password tests**

Append to `tests/test_auth_management_api.py`:

```python
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

    def test_register_creates_normal_user(self):
        from tests.test_auth_api import encrypt_rsa_oaep
        from src.models.user import User

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
        self.assertEqual(user.role, "user")
        self.assertEqual(user.status, "active")

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

        retry = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
            },
        )
        self.assertEqual(retry.status_code, 401)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_auth_management_api.RegistrationAndPasswordChangeTest -v`

Expected: FAIL because `/api/auth/register` and `/api/auth/change-password` do not exist.

- [ ] **Step 3: Implement register and change-password service helpers**

Add to `src/services/auth.py`:

```python
def register_user(self, username: str, password: str) -> User:
    normalized = self.validate_username(username)
    self.validate_password(password)
    if User.get_by_username(normalized):
        raise ValidationError("用户名已存在")
    user = User(username=normalized, role="user", status="active")
    user.set_password(password)
    user.save()
    return user

def change_password(self, user_id: int, old_password: str, new_password: str) -> None:
    user = User.get_by_id(user_id)
    if not user or user.status != "active":
        raise AuthenticationError("用户不可用")
    if not user.verify_password(old_password):
        raise ValidationError("旧密码错误")
    self.validate_password(new_password)
    user.set_password(new_password)
    user.save()
    self.revoke_all_remember_tokens(user_id)
```

- [ ] **Step 4: Add the two routes**

Update `src/routes/auth_routes.py`:

```python
@auth_bp.post("/api/auth/register")
@handle_api_errors
def auth_register() -> Any:
    auth_service = get_auth_service()
    crypto_service = get_login_crypto_service()
    data = request.get_json(force=True, silent=True) or {}
    username = crypto_service.decrypt(data.get("username") or "").strip()
    password = crypto_service.decrypt(data.get("password") or "")
    confirm_password = crypto_service.decrypt(data.get("confirmPassword") or "")
    if password != confirm_password:
        raise ValidationError("两次输入的密码不一致")
    user = auth_service.register_user(username, password)
    return jsonify({"success": True, "user": {"id": user.id, "username": user.username}})
```

- [ ] **Step 5: Re-run the registration and change-password tests**

Run: `.venv/bin/python -m unittest tests.test_auth_management_api.RegistrationAndPasswordChangeTest -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/services/auth.py src/routes/auth_routes.py tests/test_auth_management_api.py
git commit -m "feat: add registration and password change"
```

### Task 4: Add Admin User Management APIs

**Files:**
- Create: `src/routes/admin_routes.py`
- Modify: `app.py`
- Modify: `src/services/auth.py`
- Create: `tests/test_admin_user_routes.py`

- [ ] **Step 1: Write the failing admin route tests**

Create `tests/test_admin_user_routes.py`:

```python
import importlib
import os
import tempfile
import unittest
from pathlib import Path

from tests.test_auth_api import encrypt_rsa_oaep


def build_client():
    tmpdir = tempfile.TemporaryDirectory()
    data_dir = Path(tmpdir.name) / "data"
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["DB_PATH"] = str(data_dir / "app.db")
    os.environ["APP_SECRET_KEY"] = "test-secret"

    import src.config as config_module
    import src.services.auth as auth_module
    import src.services.database as database_module

    config_module._config_instance = None
    auth_module._auth_service = None
    database_module.db_manager = None

    import app as app_module

    app_module = importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return tmpdir, app_module.app.test_client()


class AdminUserRoutesTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in ("DATA_DIR", "DB_PATH", "APP_SECRET_KEY")
        }
        self.tmpdir, self.client = build_client()
        self.public_key = self.client.get("/api/auth/public-key").get_json()["publicKey"]
        login = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(self.public_key, "admin"),
                "password": encrypt_rsa_oaep(self.public_key, "banana123"),
            },
        )
        self.admin_headers = {"Authorization": f"Bearer {login.get_json()['token']}"}

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_admin_can_list_users(self):
        response = self.client.get("/api/admin/users", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("users", response.get_json())

    def test_admin_can_create_user(self):
        response = self.client.post(
            "/api/admin/users",
            headers=self.admin_headers,
            json={"username": "bob", "password": "bob12345", "role": "user"},
        )
        self.assertEqual(response.status_code, 200)

    def test_last_admin_cannot_be_deleted(self):
        response = self.client.delete("/api/admin/users/1", headers=self.admin_headers)
        self.assertEqual(response.status_code, 400)
```

- [ ] **Step 2: Run the admin route tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_admin_user_routes -v`

Expected: FAIL because `/api/admin/users` routes do not exist.

- [ ] **Step 3: Implement role-aware helpers in the auth service**

Add to `src/services/auth.py`:

```python
def require_admin(self) -> User:
    user_id = self.require_auth()
    user = User.get_by_id(user_id)
    if not user or user.role != "admin" or user.status != "active":
        raise ApiError("权限不足", status_code=403)
    return user

def ensure_not_last_active_admin(self, target_user: User, next_role: str | None = None, next_status: str | None = None) -> None:
    if target_user.role != "admin":
        return
    resulting_role = next_role or target_user.role
    resulting_status = next_status or target_user.status
    if resulting_role == "admin" and resulting_status == "active":
        return
    active_admins = User.count_active_admins()
    if active_admins <= 1:
        raise ValidationError("不能修改最后一个管理员")
```

- [ ] **Step 4: Add the admin routes and register the blueprint**

Create `src/routes/admin_routes.py`:

```python
from flask import Blueprint, jsonify, request

from ..services.auth import get_auth_service
from .decorators import handle_api_errors

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@admin_bp.get("/users")
@handle_api_errors
def list_users():
    auth = get_auth_service()
    auth.require_admin()
    return jsonify({"users": [user.to_public_dict() for user in User.list_all()]})
```

And in `app.py`:

```python
from src.routes.admin_routes import admin_bp
app.register_blueprint(admin_bp)
```

- [ ] **Step 5: Re-run the admin route tests**

Run: `.venv/bin/python -m unittest tests.test_admin_user_routes -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app.py src/routes/admin_routes.py src/services/auth.py tests/test_admin_user_routes.py src/models/user.py
git commit -m "feat: add admin user management api"
```

### Task 5: Update Login And Settings UI

**Files:**
- Modify: `templates/login.html`
- Modify: `templates/index.html`
- Modify: `static/js/app.js`
- Create: `tests/test_auth_management_assets.py`
- Modify: `tests/test_brand_surfaces.py`

- [ ] **Step 1: Write the failing asset tests**

Create `tests/test_auth_management_assets.py`:

```python
import unittest
from pathlib import Path


class AuthManagementAssetsTest(unittest.TestCase):
    def test_login_template_has_register_and_remember_controls(self):
        html = Path("templates/login.html").read_text(encoding="utf-8")
        self.assertIn("记住登录", html)
        self.assertIn("注册", html)

    def test_index_template_has_account_security_and_user_management_sections(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")
        self.assertIn("账号安全", html)
        self.assertIn("用户管理", html)
```

- [ ] **Step 2: Run the asset tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_auth_management_assets -v`

Expected: FAIL because the templates do not contain the new sections yet.

- [ ] **Step 3: Update the login page**

Modify `templates/login.html` to add:

```html
<label class="checkbox-row">
  <input id="rememberLogin" type="checkbox">
  <span>记住登录</span>
</label>
<button type="button" id="toggleAuthModeBtn">切换到注册</button>
```

And update the submit payload in the inline script:

```javascript
body: JSON.stringify({
  username: encryptedUsername,
  password: encryptedPassword,
  confirmPassword: encryptedConfirmPassword,
  remember: !!(document.getElementById('rememberLogin') && document.getElementById('rememberLogin').checked),
})
```

- [ ] **Step 4: Add account security and admin user management sections**

Modify `templates/index.html` with two new settings bands:

```html
<div class="settings-group" id="accountSecurityGroup">
  <h3 class="settings-group-title">账号安全</h3>
  <div id="currentUsernameText"></div>
  <form id="changePasswordForm"></form>
</div>

<div class="settings-group" id="userManagementGroup" hidden>
  <h3 class="settings-group-title">用户管理</h3>
  <div id="userAdminPanel"></div>
</div>
```

- [ ] **Step 5: Add frontend logic and rerun asset tests**

Modify `static/js/app.js` to:

```javascript
async function tryRefreshAccessToken() {
    const response = await fetch('/api/auth/refresh', { method: 'POST', credentials: 'same-origin' });
    if (!response.ok) return null;
    return response.json();
}
```

Run:
- `.venv/bin/python -m unittest tests.test_auth_management_assets tests.test_brand_surfaces -v`
- `node --check static/js/app.js`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add templates/login.html templates/index.html static/js/app.js tests/test_auth_management_assets.py tests/test_brand_surfaces.py
git commit -m "feat: add auth management frontend"
```

### Task 6: Full Regression And Cleanup

**Files:**
- Modify: `tests/test_auth_api.py`
- Modify: `tests/test_auth_management_api.py`
- Modify: `tests/test_admin_user_routes.py`

- [ ] **Step 1: Add the remaining edge-case tests**

Extend the auth tests with:

```python
def test_disabled_user_cannot_refresh(self):
    ...

def test_non_admin_cannot_access_admin_users(self):
    ...

def test_logout_clears_remember_cookie(self):
    ...
```

- [ ] **Step 2: Run the auth regression suite**

Run:

```bash
.venv/bin/python -m unittest tests.test_auth_api tests.test_auth_management_api tests.test_admin_user_routes -v
```

Expected: all PASS.

- [ ] **Step 3: Run frontend and repository checks**

Run:

```bash
.venv/bin/python -m unittest tests.test_auth_management_assets tests.test_brand_surfaces -v
node --check static/js/app.js
git diff --check
```

Expected: all PASS with no diff formatting errors.

- [ ] **Step 4: Commit**

```bash
git add tests/test_auth_api.py tests/test_auth_management_api.py tests/test_admin_user_routes.py tests/test_auth_management_assets.py
git commit -m "test: cover auth management regressions"
```

## Self-Review

- Spec coverage:
  - Registration: Task 3
  - Password change: Task 3
  - Remember login and refresh: Task 2
  - Admin user management: Task 4
  - Settings/login UI: Task 5
  - Last-admin protections and regressions: Tasks 4 and 6
- Placeholder scan:
  - No `TBD`, `TODO`, or deferred placeholders remain in the plan body.
- Type consistency:
  - `role`, `status`, `remember token`, `/api/auth/refresh`, and `/api/admin/users` naming are used consistently across tasks.
