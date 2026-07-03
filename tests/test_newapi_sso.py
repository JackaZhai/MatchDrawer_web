import base64
import hashlib
import hmac
import importlib
import json
import os
import re
import tempfile
import time
import unittest
from pathlib import Path


def build_test_client():
    tmpdir = tempfile.TemporaryDirectory()
    data_dir = Path(tmpdir.name) / "data"
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["DB_PATH"] = str(data_dir / "app.db")
    os.environ["APP_SECRET_KEY"] = "test-secret"
    os.environ["NEWAPI_SSO_ENABLED"] = "true"
    os.environ["NEWAPI_SSO_AUTHORIZE_URL"] = "https://api.happyresearch.xyz/api/happyresearch/sso"
    os.environ["HAPPYRESEARCH_SSO_SECRET"] = "shared-sso-secret"
    os.environ["HAPPYRESEARCH_SSO_ISSUER"] = "happyresearch-newapi"
    os.environ["HAPPYRESEARCH_SSO_AUDIENCE"] = "happyresearch-apps"

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


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def build_sso_token(secret: str, payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{b64url(signature)}"


def build_valid_token(**overrides):
    now = int(time.time())
    payload = {
        "id": 42,
        "username": "newapi-user",
        "display_name": "New API User",
        "role": 100,
        "status": 1,
        "group": "default",
        "iat": now,
        "exp": now + 60,
        "iss": "happyresearch-newapi",
        "aud": "happyresearch-apps",
    }
    payload.update(overrides)
    return build_sso_token("shared-sso-secret", payload)


class NewApiSsoTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in (
                "DATA_DIR",
                "DB_PATH",
                "APP_SECRET_KEY",
                "NEWAPI_SSO_ENABLED",
                "NEWAPI_SSO_AUTHORIZE_URL",
                "HAPPYRESEARCH_SSO_SECRET",
                "HAPPYRESEARCH_SSO_ISSUER",
                "HAPPYRESEARCH_SSO_AUDIENCE",
            )
        }
        self.tmpdir, self.client = build_test_client()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_login_redirects_to_newapi_sso_start_when_enabled(self):
        response = self.client.get("/login?next=%2Fworkspace")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/api/auth/newapi/start?"))
        self.assertIn("next=/workspace", response.headers["Location"])

    def test_sso_disabled_query_preserves_local_fallback_login(self):
        response = self.client.post(
            "/login?sso=0",
            data={"username": "admin", "password": "banana123"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("matchdrawer_auth_token_v1", body)

    def test_public_sso_disabled_query_still_uses_newapi_sso(self):
        response = self.client.get(
            "/login?sso=0",
            headers={"Host": "drawer.happyresearch.xyz"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/api/auth/newapi/start?"))

    def test_newapi_sso_callback_issues_matchdrawer_token_and_syncs_user(self):
        token = build_valid_token()

        response = self.client.get(f"/api/auth/newapi/callback?token={token}&next=%2F")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("matchdrawer_auth_token_v1", body)
        match = re.search(r"localStorage\.setItem\('matchdrawer_auth_token_v1',\s*\"([^\"]+)\"", body)
        self.assertIsNotNone(match)

        validate_response = self.client.get(
            "/api/auth/validate",
            headers={"Authorization": f"Bearer {match.group(1)}"},
        )
        self.assertEqual(validate_response.status_code, 200)
        self.assertEqual(validate_response.get_json()["user"]["username"], "newapi-user")

        from src.models.user import User

        user = User.get_by_username("newapi-user")
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "admin")
        self.assertEqual(user.status, "active")

    def test_newapi_sso_callback_rejects_tampered_token(self):
        token = build_valid_token().rsplit(".", 1)[0] + ".bad-signature"

        response = self.client.get(f"/api/auth/newapi/callback?token={token}")

        self.assertEqual(response.status_code, 302)
