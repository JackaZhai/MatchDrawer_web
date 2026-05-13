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

    def _admin_create_user(
        self,
        username: str,
        password: str = "banana999",
        role: str = "user",
        status: str = "active",
    ):
        return self.client.post(
            "/api/admin/users",
            headers=self.admin_headers,
            json={
                "username": encrypt_rsa_oaep(self.public_key, username),
                "password": encrypt_rsa_oaep(self.public_key, password),
                "role": role,
                "status": status,
            },
        )

    def _login_headers(self, username: str, password: str):
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(self.public_key, username),
                "password": encrypt_rsa_oaep(self.public_key, password),
            },
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.get_json()['token']}"}

    def test_admin_can_list_users(self):
        response = self.client.get("/api/admin/users", headers=self.admin_headers)

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("users", payload)
        self.assertTrue(any(user["username"] == "admin" for user in payload["users"]))

    def test_admin_can_create_user(self):
        response = self._admin_create_user("bob", password="bob12345")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["user"]["username"], "bob")
        self.assertEqual(payload["user"]["role"], "user")
        self.assertEqual(payload["user"]["status"], "active")

    def test_non_admin_cannot_access_admin_users(self):
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "username": encrypt_rsa_oaep(self.public_key, "alice"),
                "password": encrypt_rsa_oaep(self.public_key, "alice123"),
                "confirmPassword": encrypt_rsa_oaep(self.public_key, "alice123"),
            },
        )
        user_headers = {"Authorization": f"Bearer {register_response.get_json()['token']}"}

        response = self.client.get("/api/admin/users", headers=user_headers)

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.get_json())

    def test_non_admin_cannot_access_api_key_settings(self):
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "username": encrypt_rsa_oaep(self.public_key, "alice"),
                "password": encrypt_rsa_oaep(self.public_key, "alice123"),
                "confirmPassword": encrypt_rsa_oaep(self.public_key, "alice123"),
            },
        )
        user_headers = {"Authorization": f"Bearer {register_response.get_json()['token']}"}

        response = self.client.get("/api/keys", headers=user_headers)

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.get_json())

    def test_admin_can_access_api_key_settings(self):
        response = self.client.get("/api/keys", headers=self.admin_headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn("keys", response.get_json())

    def test_normal_user_profile_uses_admin_global_api_key_status(self):
        add_response = self.client.post(
            "/api/keys",
            headers=self.admin_headers,
            json={
                "provider": "grsai",
                "value": "sk-test-global-admin",
                "name": "global",
                "baseUrl": "https://grsaiapi.com/v1",
            },
        )
        self.assertEqual(add_response.status_code, 200)

        register_response = self.client.post(
            "/api/auth/register",
            json={
                "username": encrypt_rsa_oaep(self.public_key, "alice"),
                "password": encrypt_rsa_oaep(self.public_key, "alice123"),
                "confirmPassword": encrypt_rsa_oaep(self.public_key, "alice123"),
            },
        )
        user_headers = {"Authorization": f"Bearer {register_response.get_json()['token']}"}

        profile_response = self.client.get("/api/profile", headers=user_headers)
        payload = profile_response.get_json()

        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(payload["user"]["username"], "alice")
        self.assertFalse(payload["isAdmin"])
        self.assertTrue(payload["hasKey"])
        self.assertEqual(payload["activeBaseUrl"], "https://grsaiapi.com/v1")

    def test_last_admin_cannot_be_deleted(self):
        response = self.client.delete("/api/admin/users/1", headers=self.admin_headers)

        self.assertEqual(response.status_code, 400)
        self.assertIn("最后一个管理员", response.get_json()["error"])

    def test_last_admin_cannot_be_disabled(self):
        response = self.client.patch(
            "/api/admin/users/1",
            headers=self.admin_headers,
            json={"status": "disabled"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("最后一个管理员", response.get_json()["error"])

    def test_last_admin_cannot_be_downgraded(self):
        response = self.client.patch(
            "/api/admin/users/1",
            headers=self.admin_headers,
            json={"role": "user"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("最后一个管理员", response.get_json()["error"])

    def test_admin_can_disable_user_and_block_future_access(self):
        create_response = self._admin_create_user("bob", password="bob12345")
        user_id = create_response.get_json()["user"]["id"]
        user_headers = self._login_headers("bob", "bob12345")

        disable_response = self.client.patch(
            f"/api/admin/users/{user_id}",
            headers=self.admin_headers,
            json={"status": "disabled"},
        )
        self.assertEqual(disable_response.status_code, 200)

        profile_response = self.client.get("/api/profile", headers=user_headers)

        self.assertEqual(profile_response.status_code, 401)
        self.assertIn("error", profile_response.get_json())

    def test_admin_can_reset_user_password(self):
        create_response = self._admin_create_user("bob", password="bob12345")
        user_id = create_response.get_json()["user"]["id"]

        reset_response = self.client.post(
            f"/api/admin/users/{user_id}/reset-password",
            headers=self.admin_headers,
            json={
                "password": encrypt_rsa_oaep(self.public_key, "bob99999"),
                "confirmPassword": encrypt_rsa_oaep(self.public_key, "bob99999"),
            },
        )
        self.assertEqual(reset_response.status_code, 200)

        old_login = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(self.public_key, "bob"),
                "password": encrypt_rsa_oaep(self.public_key, "bob12345"),
            },
        )
        new_login = self.client.post(
            "/api/auth/login",
            json={
                "username": encrypt_rsa_oaep(self.public_key, "bob"),
                "password": encrypt_rsa_oaep(self.public_key, "bob99999"),
            },
        )

        self.assertEqual(old_login.status_code, 401)
        self.assertEqual(new_login.status_code, 200)


if __name__ == "__main__":
    unittest.main()
