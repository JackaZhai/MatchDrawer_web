import os
import tempfile
import unittest
from pathlib import Path


class BrandSurfaceSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tempdir = tempfile.TemporaryDirectory()
        db_path = Path(cls._tempdir.name) / "app.db"
        os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
        os.environ.setdefault("AUTH_USERNAME", "admin")
        os.environ.setdefault("AUTH_PASSWORD", "banana123")
        os.environ["DATA_DIR"] = cls._tempdir.name
        os.environ["DB_PATH"] = str(db_path)

        import app as app_module

        cls.app_module = app_module
        cls.client = app_module.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls._tempdir.cleanup()

    def test_login_brand_surface(self):
        response = self.client.get("/login")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("MatchDrawer", body)
        self.assertIn("通用画图平台", body)
        self.assertIn("PaperBanana 工作流", body)

    def test_index_brand_surface(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("MatchDrawer", body)
        self.assertIn("架构图模板", body)
        self.assertIn("PaperBanana 专业工作流", body)

    def test_manual_brand_surface(self):
        response = self.client.get("/manual")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("MatchDrawer 使用指南", body)
        self.assertIn("论文图、流程图、架构图、机制图", body)
        self.assertIn("PaperBanana 专业工作流", body)
