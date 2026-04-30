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


class BrandSurfacesTest(unittest.TestCase):
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

    def test_login_page_uses_matchdrawer_brand(self):
        response = self.client.get("/login")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("MatchDrawer", html)
        self.assertIn("通用画图平台", html)
        self.assertIn("PaperBanana 工作流", html)

    def test_dashboard_promotes_general_diagram_work_and_visible_paperbanana(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("MatchDrawer", html)
        self.assertIn("架构图模板", html)
        self.assertIn(">图像生成<", html)
        self.assertIn(">PaperBanana<", html)
        self.assertIn("结果预览", html)

    def test_manual_mentions_general_drawing_scope(self):
        response = self.client.get("/manual")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("MatchDrawer 使用指南", html)
        self.assertIn("论文图、流程图、架构图、机制图", html)
        self.assertIn("PaperBanana 专业工作流", html)


if __name__ == "__main__":
    unittest.main()
