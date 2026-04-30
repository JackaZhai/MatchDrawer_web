import unittest
from pathlib import Path


class ModelCatalogTest(unittest.TestCase):
    def test_grsai_image_models_match_current_dashboard_catalog(self):
        api_service = Path("static/js/api-service.js").read_text(encoding="utf-8")
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")
        manual = Path("templates/manual.html").read_text(encoding="utf-8")
        ai_service = Path("src/services/ai_service.py").read_text(encoding="utf-8")

        expected_models = [
            "sora-image",
            "gpt-image-1.5",
            "nano-banana-fast",
            "nano-banana",
            "nano-banana-2",
            "nano-banana-pro",
            "nano-banana-pro-vt",
            "nano-banana-2-cl",
            "nano-banana-pro-cl",
            "nano-banana-2-4k-cl",
            "nano-banana-pro-vip",
            "nano-banana-pro-4k-vip",
        ]

        for model in expected_models:
            self.assertIn(model, api_service, model)
            self.assertIn(model, app_js, model)
            self.assertIn(model, ai_service, model)

        self.assertIn("nano-banana-2", manual)
        self.assertIn("nano-banana-pro-vip", manual)


if __name__ == "__main__":
    unittest.main()
