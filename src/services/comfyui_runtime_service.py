"""Managed local ComfyUI runtime command service."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Optional

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

    def start_command(self) -> list[str]:
        python = str(self.python_bin) if self.python_bin.exists() else "python3"
        return [
            python,
            "main.py",
            "--listen",
            self.host,
            "--port",
            str(self.port),
        ]

    def run_install(self) -> dict[str, Any]:
        self.runtime_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            for command in self.install_commands():
                subprocess.run(command, check=True, cwd=self.runtime_dir.parent)
        except subprocess.CalledProcessError as exc:
            raise ServiceError("ComfyUI install failed", details=str(exc)) from exc

        return self.status()

    def start(self) -> dict[str, Any]:
        if not (self.runtime_dir / "main.py").exists():
            raise ServiceError(f"ComfyUI runtime not installed at {self.runtime_dir}")

        subprocess.Popen(
            self.start_command(),
            cwd=self.runtime_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"started": True, "baseUrl": self.base_url}


def get_comfyui_runtime_service() -> ComfyUIRuntimeService:
    global _service_instance
    if _service_instance is None:
        _service_instance = ComfyUIRuntimeService()
    return _service_instance
