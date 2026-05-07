"""Managed local ComfyUI runtime command service."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Optional
from urllib.error import URLError
from urllib.request import urlopen

from ..config import get_config
from ..utils.errors import ServiceError


COMFYUI_REPO = "https://github.com/comfyanonymous/ComfyUI.git"
GRSAI_REPO = "https://github.com/31702160136/ComfyUI-GrsAI.git"

_service_instance: Optional["ComfyUIRuntimeService"] = None


class ComfyUIRuntimeService:
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        config = get_config()
        data_dir = os.getenv("DATA_DIR") or getattr(config, "data_dir", "data")

        self.data_dir = Path(data_dir)
        self.runtime_dir = self.data_dir / "comfyui" / "runtime"
        self.host = host
        self.port = port
        self.process: Optional[subprocess.Popen[bytes]] = None

    @property
    def python_bin(self) -> Path:
        return self.runtime_dir / ".venv" / "bin" / "python"

    @property
    def grsai_dir(self) -> Path:
        return self.runtime_dir / "custom_nodes" / "ComfyUI-GrsAI"

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def status(self) -> dict[str, Any]:
        installed = (self.runtime_dir / "main.py").exists()
        return {
            "state": "installed" if installed else "missing",
            "installed": installed,
            "grsaiInstalled": self.grsai_dir.exists(),
            "runtimeDir": str(self.runtime_dir),
            "baseUrl": self.base_url,
        }

    def install_commands(self) -> list[list[str]]:
        return [
            ["git", "clone", COMFYUI_REPO, str(self.runtime_dir)],
            ["python3", "-m", "venv", str(self.runtime_dir / ".venv")],
            [
                str(self.python_bin),
                "-m",
                "pip",
                "install",
                "-r",
                str(self.runtime_dir / "requirements.txt"),
            ],
            ["mkdir", "-p", str(self.runtime_dir / "custom_nodes")],
            ["git", "clone", GRSAI_REPO, str(self.grsai_dir)],
            [
                str(self.python_bin),
                "-m",
                "pip",
                "install",
                "-r",
                str(self.grsai_dir / "requirements.txt"),
            ],
        ]

    def _pending_install_commands(self) -> list[list[str]]:
        commands = []
        if not self.runtime_dir.exists():
            commands.append(["git", "clone", COMFYUI_REPO, str(self.runtime_dir)])
        if not self.python_bin.exists():
            commands.append(["python3", "-m", "venv", str(self.runtime_dir / ".venv")])
        commands.append(
            [
                str(self.python_bin),
                "-m",
                "pip",
                "install",
                "-r",
                str(self.runtime_dir / "requirements.txt"),
            ]
        )
        commands.append(["mkdir", "-p", str(self.runtime_dir / "custom_nodes")])
        if not self.grsai_dir.exists():
            commands.append(["git", "clone", GRSAI_REPO, str(self.grsai_dir)])
        commands.append(
            [
                str(self.python_bin),
                "-m",
                "pip",
                "install",
                "-r",
                str(self.grsai_dir / "requirements.txt"),
            ]
        )
        return commands

    def start_command(self) -> list[str]:
        if not self.python_bin.exists():
            raise ServiceError(f"Managed ComfyUI python not found at {self.python_bin}")
        return [
            str(self.python_bin),
            str(self.runtime_dir / "main.py"),
            "--listen",
            self.host,
            "--port",
            str(self.port),
        ]

    def run_install(self) -> dict[str, Any]:
        self.runtime_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            for command in self._pending_install_commands():
                subprocess.run(command, check=True, cwd=self.runtime_dir.parent)
        except subprocess.CalledProcessError as exc:
            raise ServiceError("ComfyUI install failed", details=str(exc)) from exc

        return self.status()

    def _is_reachable(self, timeout: float = 0.5) -> bool:
        try:
            with urlopen(f"{self.base_url}/system_stats", timeout=timeout) as response:
                return response.status < 500
        except (OSError, TimeoutError, URLError):
            return False

    def _process_output(self, process: subprocess.Popen[bytes]) -> str:
        try:
            stdout, stderr = process.communicate(timeout=1)
        except Exception:
            return ""

        details = stderr or stdout or b""
        if isinstance(details, bytes):
            return details.decode("utf-8", errors="replace").strip()
        return str(details).strip()

    def start(self, startup_timeout: float = 30.0, poll_interval: float = 0.5) -> dict[str, Any]:
        if not (self.runtime_dir / "main.py").exists():
            raise ServiceError(f"ComfyUI runtime not installed at {self.runtime_dir}")

        if self._is_reachable():
            return {"started": False, "alreadyRunning": True, "baseUrl": self.base_url}

        self.process = subprocess.Popen(
            self.start_command(),
            cwd=self.runtime_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        deadline = time.monotonic() + startup_timeout
        while time.monotonic() <= deadline:
            if self._is_reachable():
                return {"started": True, "alreadyRunning": False, "baseUrl": self.base_url}

            exit_code = self.process.poll()
            if exit_code is not None:
                raise ServiceError(
                    f"ComfyUI process exited early with code {exit_code}",
                    details=self._process_output(self.process),
                )

            time.sleep(poll_interval)

        raise ServiceError(
            f"ComfyUI did not become reachable at {self.base_url} within {startup_timeout}s"
        )


def get_comfyui_runtime_service() -> ComfyUIRuntimeService:
    global _service_instance
    if _service_instance is None:
        _service_instance = ComfyUIRuntimeService()
    return _service_instance
