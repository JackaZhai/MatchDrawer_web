import importlib
import os
import tempfile
import unittest
from pathlib import Path


def build_test_client():
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


class AuthManagementAssetsTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in ("DATA_DIR", "DB_PATH", "APP_SECRET_KEY")
        }
        self.tmpdir, self.client = build_test_client()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_login_page_exposes_register_toggle_and_remember_login(self):
        response = self.client.get("/login")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-mode="login"', html)
        self.assertIn('data-mode="register"', html)
        self.assertIn('id="rememberLogin"', html)
        self.assertIn('id="confirmPassword"', html)
        self.assertNotIn('value="banana123"', html)
        self.assertNotIn("默认账号来自配置", html)
        self.assertNotIn("长期 cookie", html)
        self.assertNotIn("面向论文图、流程图、架构图、机制图与产品示意图", html)
        self.assertNotIn("支持通用图像生成与 PaperBanana 工作流", html)
        self.assertNotIn("首次启动会自动创建默认账户", html)

    def test_settings_page_contains_account_security_and_admin_management_sections(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="accountSecurityGroup"', html)
        self.assertIn('id="changePasswordBtn"', html)
        self.assertIn('id="userManagementGroup" hidden', html)
        self.assertIn('id="adminUserSearchInput"', html)
        self.assertIn('id="adminUsersPageSizeSelect"', html)
        self.assertIn('id="adminUsersCollapseBtn"', html)
        self.assertIn('id="adminUsersTableBody"', html)
        self.assertIn('data-page="api-keys" data-admin-only hidden', html)
        self.assertIn('id="comfyFeatureLockOverlay" hidden', html)
        self.assertIn('class="form-group provider-locked-field"', html)
        self.assertIn("开发中", html)
        self.assertIn("敬请期待", html)
        self.assertNotIn('id="gptUrlBtn"', html)
        self.assertNotIn('id="gptSettingsApiKey"', html)
        self.assertIn('class="admin-users-toolbar"', html)
        self.assertIn('class="admin-users-pagination"', html)
        self.assertIn("全局 API 设置", html)
        self.assertIn("用量按账号记录", html)
        self.assertNotIn("Image Desk", html)
        self.assertNotIn(">Preview<", html)
        self.assertNotIn("GitHub 仓库", html)


if __name__ == "__main__":
    unittest.main()
