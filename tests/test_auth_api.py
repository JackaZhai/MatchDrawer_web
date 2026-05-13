import importlib
import os
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import quote

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def build_test_client():
    tmpdir = tempfile.TemporaryDirectory()
    data_dir = Path(tmpdir.name) / "data"
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["DB_PATH"] = str(data_dir / "app.db")
    os.environ["APP_SECRET_KEY"] = "test-secret"
    os.environ["AUTH_TOKEN_TTL_SECONDS"] = "1"

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


def encrypt_rsa_oaep(public_key_pem: str, plaintext: str) -> str:
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    ciphertext = public_key.encrypt(
        plaintext.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return ciphertext.hex()


class AuthApiTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in ("DATA_DIR", "DB_PATH", "APP_SECRET_KEY", "AUTH_TOKEN_TTL_SECONDS")
        }
        self.tmpdir, self.client = build_test_client()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_public_key_endpoint_returns_pem(self):
        response = self.client.get("/api/auth/public-key")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("publicKey", payload)
        self.assertIn("BEGIN PUBLIC KEY", payload["publicKey"])

    def test_login_api_returns_token_for_encrypted_credentials(self):
        key_response = self.client.get("/api/auth/public-key")
        public_key = key_response.get_json()["publicKey"]

        response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
            },
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertIn("token", payload)
        self.assertEqual(payload["user"]["username"], "admin")

    def test_profile_requires_bearer_token(self):
        response = self.client.get("/api/profile")

        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.get_json())

    def test_profile_accepts_valid_bearer_token(self):
        key_response = self.client.get("/api/auth/public-key")
        public_key = key_response.get_json()["publicKey"]
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
            },
        )
        token = login_response.get_json()["token"]

        response = self.client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("hasKey", response.get_json())

    def test_profile_rejects_expired_bearer_token(self):
        key_response = self.client.get("/api/auth/public-key")
        public_key = key_response.get_json()["publicKey"]
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
            },
        )
        token = login_response.get_json()["token"]

        time.sleep(1.2)

        response = self.client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 401)
        error_text = response.get_json().get("error", "").lower()
        self.assertTrue("expired" in error_text or "过期" in error_text)

    def test_logout_api_revokes_existing_bearer_token(self):
        key_response = self.client.get("/api/auth/public-key")
        public_key = key_response.get_json()["publicKey"]
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(public_key, "admin"),
                "password": encrypt_rsa_oaep(public_key, "banana123"),
            },
        )
        token = login_response.get_json()["token"]

        logout_response = self.client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(logout_response.status_code, 200)

        profile_response = self.client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(profile_response.status_code, 401)
        self.assertIn("error", profile_response.get_json())

    def test_form_login_success_response_escapes_next_url_for_script_context(self):
        attacker_next = "/workspace?next=" + quote("</script><script>alert(1)</script>", safe="")

        response = self.client.post(
            f"/login?next={attacker_next}",
            data={"username": "admin", "password": "banana123"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("window.location.replace(", body)
        self.assertNotIn("</script><script>alert(1)</script>", body)
        self.assertIn("\\u003c/script\\u003e\\u003cscript\\u003ealert(1)\\u003c/script\\u003e", body)


if __name__ == "__main__":
    unittest.main()
