import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


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
        svc.python_bin.parent.mkdir(parents=True)
        svc.python_bin.write_text("# python", encoding="utf-8")
        command = svc.start_command()

        self.assertIn(str(svc.runtime_dir / "main.py"), command)
        self.assertIn("--listen", command)
        self.assertIn("127.0.0.1", command)
        self.assertIn("--port", command)
        self.assertIn("8199", command)

    def test_start_command_requires_managed_python(self):
        from src.services.comfyui_runtime_service import ComfyUIRuntimeService
        from src.utils.errors import ServiceError

        svc = ComfyUIRuntimeService()

        with self.assertRaises(ServiceError):
            svc.start_command()

    def test_run_install_skips_existing_clone_dirs(self):
        from src.services.comfyui_runtime_service import COMFYUI_REPO, GRSAI_REPO
        from src.services.comfyui_runtime_service import ComfyUIRuntimeService

        svc = ComfyUIRuntimeService()
        svc.runtime_dir.mkdir(parents=True)
        svc.grsai_dir.mkdir(parents=True)
        svc.python_bin.parent.mkdir(parents=True, exist_ok=True)
        svc.python_bin.write_text("# python", encoding="utf-8")

        with patch("src.services.comfyui_runtime_service.subprocess.run") as run:
            svc.run_install()

        calls = [call.args[0] for call in run.call_args_list]
        self.assertNotIn(["git", "clone", COMFYUI_REPO, str(svc.runtime_dir)], calls)
        self.assertNotIn(["git", "clone", GRSAI_REPO, str(svc.grsai_dir)], calls)
        self.assertIn(["mkdir", "-p", str(svc.runtime_dir / "custom_nodes")], calls)

    def test_start_returns_existing_when_backend_reachable(self):
        from src.services.comfyui_runtime_service import ComfyUIRuntimeService

        svc = ComfyUIRuntimeService()
        svc.runtime_dir.mkdir(parents=True)
        (svc.runtime_dir / "main.py").write_text("print('comfy')", encoding="utf-8")

        with patch.object(svc, "_is_reachable", return_value=True):
            with patch("src.services.comfyui_runtime_service.subprocess.Popen") as popen:
                result = svc.start()

        popen.assert_not_called()
        self.assertFalse(result["started"])
        self.assertTrue(result["alreadyRunning"])
        self.assertEqual(result["baseUrl"], "http://127.0.0.1:8188")

    def test_start_raises_when_process_exits_before_ready(self):
        from src.services.comfyui_runtime_service import ComfyUIRuntimeService
        from src.utils.errors import ServiceError

        svc = ComfyUIRuntimeService()
        svc.runtime_dir.mkdir(parents=True)
        (svc.runtime_dir / "main.py").write_text("print('comfy')", encoding="utf-8")
        svc.python_bin.parent.mkdir(parents=True)
        svc.python_bin.write_text("# python", encoding="utf-8")

        proc = Mock()
        proc.poll.return_value = 1
        proc.communicate.return_value = (b"", b"boom")

        with patch.object(svc, "_is_reachable", return_value=False):
            with patch("src.services.comfyui_runtime_service.subprocess.Popen", return_value=proc):
                with self.assertRaises(ServiceError) as ctx:
                    svc.start(startup_timeout=0.01, poll_interval=0)

        self.assertIn("exited early", str(ctx.exception))
        self.assertEqual(ctx.exception.details, "boom")


if __name__ == "__main__":
    unittest.main()
