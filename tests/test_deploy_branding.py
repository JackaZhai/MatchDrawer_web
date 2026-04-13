import unittest
from pathlib import Path


class DeployBrandingTest(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]
        self.readme = self.repo_root / "README.md"
        self.env_example = self.repo_root / ".env.example"
        self.deploy_script = self.repo_root / "scripts" / "deploy_linux.sh"
        self.template = self.repo_root / "templates" / "index.html"
        self.systemd = self.repo_root / "deploy" / "systemd" / "matchdrawer.service"
        self.nginx = self.repo_root / "deploy" / "nginx" / "matchdrawer.conf"

    def test_renamed_deploy_assets_exist(self):
        self.assertTrue(self.systemd.exists(), "deploy/systemd/matchdrawer.service should exist")
        self.assertTrue(self.nginx.exists(), "deploy/nginx/matchdrawer.conf should exist")
        self.assertFalse((self.repo_root / "deploy" / "systemd" / "scidrawer.service").exists())
        self.assertFalse((self.repo_root / "deploy" / "nginx" / "scidrawer.conf").exists())

    def test_readme_and_env_example_are_rebranded(self):
        readme = self.readme.read_text(encoding="utf-8")
        env_example = self.env_example.read_text(encoding="utf-8-sig")

        self.assertIn("MatchDrawer Web", readme)
        self.assertIn("/opt/matchdrawer/MatchDrawer_web", readme)
        self.assertIn("deploy/systemd/matchdrawer.service", readme)
        self.assertIn("deploy/nginx/matchdrawer.conf", readme)
        self.assertIn("# MatchDrawer 服务配置", env_example)
        self.assertIn("/opt/matchdrawer/MatchDrawer_web/integrations/PaperBanana", env_example)

    def test_deploy_script_uses_matchdrawer_paths(self):
        script = self.deploy_script.read_text(encoding="utf-8")

        self.assertIn('APP_DIR="${APP_DIR:-/opt/matchdrawer/MatchDrawer_web}"', script)
        self.assertIn("sudo systemctl enable --now matchdrawer", script)

    def test_service_and_nginx_configs_use_matchdrawer_paths(self):
        systemd = self.systemd.read_text(encoding="utf-8")
        nginx = self.nginx.read_text(encoding="utf-8")

        self.assertIn("Description=MatchDrawer Web", systemd)
        self.assertIn("WorkingDirectory=/opt/matchdrawer/MatchDrawer_web", systemd)
        self.assertIn("alias /opt/matchdrawer/MatchDrawer_web/static/", nginx)

    def test_task_scope_files_do_not_contain_old_branding(self):
        tracked_files = [
            self.readme,
            self.env_example,
            self.deploy_script,
            self.template,
            self.systemd,
            self.nginx,
        ]
        for path in tracked_files:
            body = path.read_text(encoding="utf-8-sig")
            self.assertNotIn("SCIdrawer", body, f"{path} still contains SCIdrawer")
            self.assertNotIn("scidrawer", body, f"{path} still contains scidrawer")
