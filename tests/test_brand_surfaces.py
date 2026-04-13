import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


APP_ENV_VARS = ("APP_SECRET_KEY", "AUTH_USERNAME", "AUTH_PASSWORD", "DATA_DIR", "DB_PATH")


def _clear_app_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("src."):
            sys.modules.pop(module_name, None)


def _reset_cached_singletons() -> None:
    module_names = [
        "src.config",
        "src.services.database",
        "src.services.auth",
        "src.services.api_key_service",
        "src.services.paper_banana_service",
        "src.services.provider_config_service",
        "src.services.ai_service",
    ]
    for module_name in module_names:
        module = sys.modules.get(module_name)
        if not module:
            continue
        for attr in (
            "_config_instance",
            "db_manager",
            "_auth_service",
            "_api_key_service",
            "_paper_banana_service",
            "_provider_config_service",
            "_ai_service",
        ):
            if hasattr(module, attr):
                setattr(module, attr, None)


class BrandSurfaceSmokeTest(unittest.TestCase):
    def setUp(self):
        self._env_backup = {key: os.environ.get(key) for key in APP_ENV_VARS}
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        self.addCleanup(self._restore_environment)
        self.addCleanup(_reset_cached_singletons)
        self.addCleanup(_clear_app_modules)
        db_path = Path(self._tempdir.name) / "app.db"

        os.environ["APP_SECRET_KEY"] = "test-secret-key"
        os.environ["AUTH_USERNAME"] = "admin"
        os.environ["AUTH_PASSWORD"] = "banana123"
        os.environ["DATA_DIR"] = self._tempdir.name
        os.environ["DB_PATH"] = str(db_path)

        _reset_cached_singletons()
        _clear_app_modules()
        importlib.invalidate_caches()

        self.app_module = importlib.import_module("app")
        self.client = self.app_module.app.test_client()

    def _restore_environment(self):
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

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
