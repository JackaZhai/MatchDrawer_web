import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ComfyUIRuntimeServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name) / "data"
        self.previous_data_dir = os.environ.get("DATA_DIR")
        os.environ["DATA_DIR"] = str(self.data_dir)

    def tearDown(self):
        if self.previous_data_dir is None:
            os.environ.pop("DATA_DIR", None)
        else:
            os.environ["DATA_DIR"] = self.previous_data_dir
        self.tmpdir.cleanup()

    def test_status_missing_when_runtime_dir_absent(self):
        from src.services.comfyui_runtime_service import ComfyUIRuntimeService

        svc = ComfyUIRuntimeService()
        status = svc.status()

        self.assertEqual(status["state"], "missing")
        self.assertFalse(status["installed"])
        self.assertTrue(str(status["runtimeDir"]).endswith("data/comfyui/runtime"))

    def test_status_installed_when_main_file_exists(self):
        from src.services.comfyui_runtime_service import ComfyUIRuntimeService

        svc = ComfyUIRuntimeService()
        svc.runtime_dir.mkdir(parents=True)
        (svc.runtime_dir / "main.py").write_text("print('comfy')", encoding="utf-8")

        status = svc.status()

        self.assertEqual(status["state"], "installed")
        self.assertTrue(status["installed"])

    def test_install_commands_clone_comfyui_and_grsai(self):
        from src.services.comfyui_runtime_service import ComfyUIRuntimeService

        svc = ComfyUIRuntimeService()
        commands = svc.install_commands()

        joined = "\n".join(" ".join(cmd) for cmd in commands)
        self.assertIn("comfyanonymous/ComfyUI.git", joined)
        self.assertIn("31702160136/ComfyUI-GrsAI.git", joined)
        self.assertIn("requirements.txt", joined)

    def test_start_command_uses_configured_port(self):
        from src.services.comfyui_runtime_service import ComfyUIRuntimeService

        svc = ComfyUIRuntimeService(host="127.0.0.1", port=8199)
        command = svc.start_command()

        self.assertIn("main.py", command)
        self.assertIn("--listen", command)
        self.assertIn("127.0.0.1", command)
        self.assertIn("--port", command)
        self.assertIn("8199", command)


if __name__ == "__main__":
    unittest.main()
