import unittest
from pathlib import Path


class ModelCatalogTest(unittest.TestCase):
    def test_grsai_image_models_match_current_dashboard_catalog(self):
        api_service = Path("static/js/api-service.js").read_text(encoding="utf-8")
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")
        manual = Path("templates/manual.html").read_text(encoding="utf-8")
        ai_service = Path("src/services/ai_service.py").read_text(encoding="utf-8")

        expected_models = [
            "gpt-image-2",
            "nano-banana-pro",
            "nano-banana-pro-vt",
            "nano-banana-2",
            "nano-banana-fast",
            "nano-banana",
        ]
        expected_text_models = [
            "gemini-3.1-pro",
            "gemini-3-pro",
            "gemini-2.5-pro",
        ]
        excluded_models = [
            "gpt-image-2-vip",
            "nano-banana-2-cl",
            "nano-banana-2-4k-cl",
            "nano-banana-pro-cl",
            "nano-banana-pro-vip",
            "nano-banana-pro-4k-vip",
        ]

        for model in expected_models:
            self.assertIn(model, api_service, model)
            self.assertIn(model, app_js, model)
            self.assertIn(model, ai_service, model)

        for model in expected_text_models:
            self.assertIn(model, api_service, model)
            self.assertIn(model, app_js, model)
            self.assertNotIn(f'"{model}": ("{model}", "{model}")', ai_service)

        self.assertIn("nano-banana-2", manual)
        self.assertIn("nano-banana-pro-vt", manual)

        for model in excluded_models:
            self.assertNotIn(model, api_service, model)
            self.assertNotIn(model, app_js, model)
            self.assertNotIn(model, ai_service, model)
            self.assertNotIn(model, manual, model)


if __name__ == "__main__":
    unittest.main()
