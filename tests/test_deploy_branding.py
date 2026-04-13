import unittest
from pathlib import Path


class DeployBrandingTest(unittest.TestCase):
    def test_renamed_deploy_assets_exist(self):
        self.assertTrue(Path("deploy/systemd/matchdrawer.service").exists())
        self.assertTrue(Path("deploy/nginx/matchdrawer.conf").exists())

    def test_docs_and_scripts_use_matchdrawer_paths(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        env_example = Path(".env.example").read_text(encoding="utf-8")
        script = Path("scripts/deploy_linux.sh").read_text(encoding="utf-8")
        systemd_path = Path("deploy/systemd/matchdrawer.service")
        nginx_path = Path("deploy/nginx/matchdrawer.conf")

        self.assertTrue(systemd_path.exists())
        self.assertTrue(nginx_path.exists())

        systemd = systemd_path.read_text(encoding="utf-8")
        nginx = nginx_path.read_text(encoding="utf-8")

        self.assertIn("MatchDrawer Web", readme)
        self.assertIn("/opt/matchdrawer/MatchDrawer_web", readme)
        self.assertIn("deploy/systemd/matchdrawer.service", readme)
        self.assertIn("deploy/nginx/matchdrawer.conf", readme)
        self.assertIn("# MatchDrawer 服务配置", env_example)
        self.assertIn("/opt/matchdrawer/MatchDrawer_web/integrations/PaperBanana", env_example)
        self.assertIn('APP_DIR="${APP_DIR:-/opt/matchdrawer/MatchDrawer_web}"', script)
        self.assertIn("sudo systemctl enable --now matchdrawer", script)
        self.assertIn("Description=MatchDrawer Web", systemd)
        self.assertIn("WorkingDirectory=/opt/matchdrawer/MatchDrawer_web", systemd)
        self.assertIn("alias /opt/matchdrawer/MatchDrawer_web/static/", nginx)

    def test_old_scidrawer_brand_is_removed_from_tracked_files(self):
        tracked_files = [
            Path("README.md"),
            Path(".env.example"),
            Path("scripts/deploy_linux.sh"),
            Path("app.py"),
            Path("templates/index.html"),
            Path("templates/login.html"),
            Path("templates/manual.html"),
            Path("static/js/app.js"),
            Path("static/css/app.css"),
            Path("static/css/design-system.css"),
            Path("deploy/systemd/matchdrawer.service"),
            Path("deploy/nginx/matchdrawer.conf"),
        ]

        for path in tracked_files:
            self.assertTrue(path.exists(), path.as_posix())
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("scidrawer", text.lower(), path.as_posix())


if __name__ == "__main__":
    unittest.main()
