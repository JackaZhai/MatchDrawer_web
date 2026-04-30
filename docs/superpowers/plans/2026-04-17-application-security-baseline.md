# Application Security Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish an application-layer security baseline for MatchDrawer by restoring real authentication, adding CSRF, removing frontend-sensitive configuration exposure, hardening validation, and tightening error handling.

**Architecture:** Keep the existing Flask + Jinja + vanilla JS stack and harden it in place. The backend remains the sole owner of upstream hosts, providers, and API keys; the frontend becomes a thin authenticated client that only talks to local `/api/*` routes with session + CSRF protection. Regression coverage centers on new security tests plus existing smoke tests.

**Tech Stack:** Flask, Jinja2 templates, vanilla JavaScript, Python `unittest`, `cryptography`, Pillow

---

## File Structure

**Create**
- `src/services/csrf.py`
- `tests/test_security_baseline.py`

**Modify**
- `app.py`
- `src/config.py`
- `src/routes/auth_routes.py`
- `src/routes/api_routes.py`
- `src/routes/decorators.py`
- `src/services/auth.py`
- `src/services/api_key_service.py`
- `src/utils/validation.py`
- `src/utils/errors.py`
- `static/js/api-service.js`
- `static/js/app.js`
- `templates/index.html`
- `templates/login.html`

**Regression Tests**
- `tests/test_brand_surfaces.py`
- `tests/test_deploy_branding.py`
- `tests/test_model_catalog.py`
- `tests/test_user_model.py`

### Task 1: Lock The Security Baseline In Tests

**Files:**
- Create: `tests/test_security_baseline.py`
- Test: `tests/test_security_baseline.py`

- [ ] **Step 1: Write the failing authentication and privacy tests**

Add a new test module that covers:

```python
class SecurityBaselineTest(unittest.TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_manual_requires_login(self):
        response = self.client.get("/manual", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_profile_requires_login(self):
        response = self.client.get("/api/profile")
        self.assertEqual(response.status_code, 401)

    def test_login_page_does_not_prefill_default_credentials(self):
        html = self.client.get("/login").get_data(as_text=True)
        self.assertNotIn('value="admin"', html)
        self.assertNotIn('value="banana123"', html)

    def test_profile_payload_hides_host_fields(self):
        self.login()
        payload = self.client.get("/api/profile").get_json()
        self.assertNotIn("apiHost", payload)
        self.assertNotIn("activeBaseUrl", payload)

    def test_key_list_hides_provider_and_base_url(self):
        self.login()
        payload = self.client.get("/api/keys").get_json()
        key = (payload.get("keys") or [{}])[0]
        self.assertNotIn("provider", key)
        self.assertNotIn("baseUrl", key)
```

- [ ] **Step 2: Add failing CSRF and upload validation tests**

Extend the same file with:

```python
    def test_login_requires_csrf_token(self):
        response = self.client.post("/login", data={"username": "admin", "password": "banana123"})
        self.assertEqual(response.status_code, 403)

    def test_api_write_requires_csrf(self):
        self.login()
        response = self.client.post("/api/keys", json={"value": "abc123456789"})
        self.assertEqual(response.status_code, 403)

    def test_invalid_reference_image_is_rejected(self):
        self.login()
        response = self.client.post(
            "/api/draw",
            json={"prompt": "x", "urls": ["data:image/png;base64,not-valid-base64"]},
            headers=self.csrf_headers(),
        )
        self.assertEqual(response.status_code, 400)
```

- [ ] **Step 3: Run the new test file to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_security_baseline -v`

Expected: multiple failures for anonymous access, missing CSRF enforcement, login prefill leakage, and key/profile de-sensitization gaps.

- [ ] **Step 4: Commit the red tests**

```bash
git add tests/test_security_baseline.py
git commit -m "test: add application security baseline coverage"
```

### Task 2: Restore Real Authentication And Harden Session Bootstrapping

**Files:**
- Modify: `src/services/auth.py`
- Modify: `src/routes/auth_routes.py`
- Modify: `src/routes/decorators.py`
- Modify: `templates/login.html`
- Modify: `src/routes/api_routes.py`
- Test: `tests/test_security_baseline.py`

- [ ] **Step 1: Remove auto-login behavior from the auth service**

Replace the permissive session helpers with explicit checks:

```python
def is_authenticated(self) -> bool:
    return (
        session.get("authenticated") is True
        and session.get("user_id") is not None
        and bool(session.get("username"))
    )

def get_current_user_id(self) -> Optional[int]:
    user_id = session.get("user_id")
    return int(user_id) if self.is_authenticated() and user_id is not None else None

def require_auth(self) -> int:
    user_id = self.get_current_user_id()
    if user_id is None:
        raise AuthenticationError("请先登录")
    return user_id
```

- [ ] **Step 2: Rotate the session on login and change logout to POST**

Update login/logout routes:

```python
if user_id:
    session.clear()
    auth_service.login_user(user_id, username)
    return redirect(next_url)

@auth_bp.post("/logout")
def logout() -> Any:
    auth_service.logout_user()
    return redirect(url_for("auth.login"))
```

- [ ] **Step 3: Remove login-page default credential prefill**

Update the template inputs:

```html
<input id="username" name="username" type="text" autocomplete="username" required>
<input id="password" name="password" type="password" autocomplete="current-password" required>
```

- [ ] **Step 4: Protect `/manual` with login**

Make the route authenticated:

```python
@main_bp.get("/manual")
@login_required
def manual() -> Any:
    return render_template("manual.html")
```

- [ ] **Step 5: Run the auth-focused tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_security_baseline.SecurityBaselineTest.test_dashboard_requires_login tests.test_security_baseline.SecurityBaselineTest.test_manual_requires_login tests.test_security_baseline.SecurityBaselineTest.test_profile_requires_login tests.test_security_baseline.SecurityBaselineTest.test_login_page_does_not_prefill_default_credentials -v`

Expected: all four tests pass.

- [ ] **Step 6: Commit the authentication hardening**

```bash
git add src/services/auth.py src/routes/auth_routes.py src/routes/decorators.py src/routes/api_routes.py templates/login.html
git commit -m "feat: restore real authentication checks"
```

### Task 3: Add CSRF Protection And Secure Session/App Configuration

**Files:**
- Create: `src/services/csrf.py`
- Modify: `app.py`
- Modify: `src/config.py`
- Modify: `src/routes/auth_routes.py`
- Modify: `src/routes/decorators.py`
- Modify: `templates/login.html`
- Modify: `templates/index.html`
- Modify: `static/js/api-service.js`
- Test: `tests/test_security_baseline.py`

- [ ] **Step 1: Create a lightweight CSRF service**

Add a session-backed token manager:

```python
class CsrfService:
    SESSION_KEY = "csrf_token"

    def issue_token(self) -> str:
        token = session.get(self.SESSION_KEY)
        if not token:
            token = secrets.token_urlsafe(32)
            session[self.SESSION_KEY] = token
        return token

    def validate_token(self, token: str) -> bool:
        expected = session.get(self.SESSION_KEY, "")
        return bool(expected) and secrets.compare_digest(expected, token or "")
```

- [ ] **Step 2: Add CSRF decorators for form posts and JSON API writes**

Implement a request validator in `src/routes/decorators.py`:

```python
def csrf_protected(view_func: Callable) -> Callable:
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not get_csrf_service().validate_token(token):
            return jsonify({"error": "CSRF 校验失败"}), 403
        return view_func(*args, **kwargs)
    return wrapper
```

- [ ] **Step 3: Wire CSRF into login, logout, and state-changing `/api/*` routes**

Apply the decorator to:

```python
@auth_bp.route("/login", methods=["GET", "POST"])
...
@auth_bp.post("/logout")
...
@api_bp.post("/keys")
@api_bp.post("/keys/active")
@api_bp.post("/draw")
@api_bp.post("/result")
@api_bp.post("/cancel")
@api_bp.post("/provider-configs")
```

- [ ] **Step 4: Add secure session configuration and production secret enforcement**

Update app/config initialization:

```python
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=config.is_production,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)

if config.is_production and config.app_secret_key == "change-me":
    raise RuntimeError("APP_SECRET_KEY must be changed in production")
```

- [ ] **Step 5: Expose CSRF token to the login form and authenticated app shell**

Use:

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<meta name="csrf-token" content="{{ csrf_token }}">
```

and read it in `static/js/api-service.js`:

```javascript
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') || '' : '';
}
```

- [ ] **Step 6: Attach CSRF headers to local API writes**

Update the shared fetch helper:

```javascript
if (isLocal && ["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase())) {
  options.headers["X-CSRF-Token"] = getCsrfToken();
}
```

- [ ] **Step 7: Run the CSRF-focused tests**

Run: `.venv/bin/python -m unittest tests.test_security_baseline.SecurityBaselineTest.test_login_requires_csrf_token tests.test_security_baseline.SecurityBaselineTest.test_api_write_requires_csrf -v`

Expected: missing-token requests return `403`; token-backed requests pass.

- [ ] **Step 8: Commit the CSRF and session config changes**

```bash
git add src/services/csrf.py app.py src/config.py src/routes/auth_routes.py src/routes/decorators.py templates/login.html templates/index.html static/js/api-service.js
git commit -m "feat: add csrf and secure session baseline"
```

### Task 4: Remove Frontend Sensitive Exposure And Local Storage Secrets

**Files:**
- Modify: `src/routes/api_routes.py`
- Modify: `src/services/api_key_service.py`
- Modify: `templates/index.html`
- Modify: `static/js/api-service.js`
- Modify: `static/js/app.js`
- Test: `tests/test_security_baseline.py`

- [ ] **Step 1: Stop returning sensitive host fields from `/api/profile`**

Reduce the payload to non-sensitive status only:

```python
return jsonify(
    {
        "hasKey": bool(has_key),
        "activeKeyMask": api_key_service.encryption.mask_key(active_value),
        "usage": usage_payload,
    }
)
```

- [ ] **Step 2: Stop returning provider/base URL fields from `/api/keys`**

Trim serialized key items:

```python
{
    "id": item.get("id"),
    "name": item.get("name") or "",
    "mask": self.encryption.mask_key(item.get("value", "")),
    "source": item.get("source", "custom"),
    "isActive": item.get("id") == active_by_provider.get(item.get("provider")),
    "createdAt": item.get("created_at"),
}
```

- [ ] **Step 3: Remove sensitive frontend storage**

Delete reads/writes for:

```javascript
localStorage.getItem("apiKey")
localStorage.getItem("chatApiKey")
localStorage.getItem("apiHost")
localStorage.setItem("apiKey", ...)
localStorage.setItem("chatApiKey", ...)
localStorage.setItem("apiHost", ...)
```

and keep all API requests local-only.

- [ ] **Step 4: Simplify the API settings UI**

Update the template and renderers so the public form becomes:

```html
<input type="password" id="newApiKey" class="form-input" placeholder="输入 API Key">
<input type="text" id="keyName" class="form-input" placeholder="例如：主账号 / 备用">
```

and the table no longer shows provider/base URL columns.

- [ ] **Step 5: Adjust frontend state loaders to tolerate de-sensitized payloads**

Change code paths that currently depend on `apiHost`, `activeBaseUrl`, `provider`, or `baseUrl` so they either:
- stop rendering those fields entirely, or
- use backend-derived defaults without displaying them.

- [ ] **Step 6: Run the privacy-focused tests**

Run: `.venv/bin/python -m unittest tests.test_security_baseline.SecurityBaselineTest.test_profile_payload_hides_host_fields tests.test_security_baseline.SecurityBaselineTest.test_key_list_hides_provider_and_base_url -v`

Expected: both tests pass; no frontend code still assumes those fields exist.

- [ ] **Step 7: Commit the frontend de-sensitization**

```bash
git add src/routes/api_routes.py src/services/api_key_service.py templates/index.html static/js/api-service.js static/js/app.js
git commit -m "feat: remove frontend sensitive config exposure"
```

### Task 5: Harden Validation, Error Responses, And Final Regression

**Files:**
- Modify: `src/utils/validation.py`
- Modify: `src/utils/errors.py`
- Modify: `src/routes/decorators.py`
- Modify: `src/routes/api_routes.py`
- Test: `tests/test_security_baseline.py`
- Test: `tests/test_brand_surfaces.py`
- Test: `tests/test_deploy_branding.py`
- Test: `tests/test_model_catalog.py`
- Test: `tests/test_user_model.py`

- [ ] **Step 1: Upgrade reference-image validation to verify real image content**

Implement base64 + Pillow validation:

```python
payload = base64.b64decode(encoded, validate=True)
with Image.open(io.BytesIO(payload)) as img:
    img.verify()
if mime not in {"image/png", "image/jpeg", "image/webp"}:
    raise ValidationError("参考图格式不受支持")
```

- [ ] **Step 2: Add input-length and identifier guards**

Add explicit checks like:

```python
if len(prompt.strip()) > 8000:
    raise ValidationError("Prompt 过长")
if len(api_key.strip()) < 16:
    raise ValidationError("API key 格式无效")
if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", draw_id):
    raise ValidationError("id 格式无效")
```

- [ ] **Step 3: Stop leaking internal error details in production responses**

Tighten error serialization:

```python
def to_dict(self, include_details: bool = False) -> dict:
    result = {"error": self.message}
    if include_details and self.details:
        result["details"] = self.details
    return result
```

and in the decorator:

```python
except ApiError as exc:
    return jsonify(exc.to_dict(include_details=current_app.debug)), exc.status_code
except Exception:
    current_app.logger.exception("Unhandled API error")
    return jsonify({"error": "服务器内部错误"}), 500
```

- [ ] **Step 4: Run the new validation tests**

Run: `.venv/bin/python -m unittest tests.test_security_baseline.SecurityBaselineTest.test_invalid_reference_image_is_rejected -v`

Expected: malformed image payload is rejected with `400`.

- [ ] **Step 5: Run the full regression suite**

Run: `.venv/bin/python -m unittest discover -s tests -q`

Expected: all security tests and existing regression tests pass.

- [ ] **Step 6: Run runtime verification for app startup**

Run: `.venv/bin/gunicorn --check-config -c gunicorn.conf.py app:app`

Expected: exit code `0` in development mode with a non-production config.

- [ ] **Step 7: Commit the hardening and regression updates**

```bash
git add src/utils/validation.py src/utils/errors.py src/routes/decorators.py src/routes/api_routes.py tests/test_security_baseline.py
git commit -m "feat: harden validation and error handling"
```

## Self-Review

- Spec coverage:
  - Authentication/session: Task 2
  - Cookie config + secret enforcement: Task 3
  - CSRF: Task 3
  - Frontend de-sensitization + no sensitive local storage: Task 4
  - Upload/input validation: Task 5
  - Error/logging boundary: Task 5
  - Security headers: Task 3
- Placeholder scan:
  - All tasks point to exact files and concrete commands.
  - All verification steps specify expected results.
- Type consistency:
  - `csrf_token` is used consistently for HTML form fields and `X-CSRF-Token` for JSON/API requests.
  - Auth helpers consistently return `Optional[int]` for passive lookups and `int` for `require_auth()`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-application-security-baseline.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
