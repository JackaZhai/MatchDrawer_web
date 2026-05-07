"""HTTP adapter for a local ComfyUI server."""

from __future__ import annotations

import base64
import binascii
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from ..config import get_config
from ..utils.errors import ApiError


DEFAULT_COMFYUI_BASE_URL = "http://127.0.0.1:8188"


class ComfyUIService:
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        config = get_config()
        configured_url = getattr(config, "comfyui_base_url", None)
        self.base_url = (base_url or configured_url or DEFAULT_COMFYUI_BASE_URL).rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _get_json(self, path: str) -> dict[str, Any]:
        try:
            response = requests.get(self._url(path), timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ApiError(f"ComfyUI request failed: {exc}", status_code=502) from exc
        except ValueError as exc:
            details = response.text if "response" in locals() else ""
            raise ApiError(
                f"Invalid JSON from ComfyUI: {exc}",
                status_code=502,
                details=details,
            ) from exc

        if isinstance(payload, dict):
            return payload
        return {"data": payload}

    def status(self) -> dict[str, Any]:
        try:
            stats = self._get_json("/system_stats")
            queue = self._get_json("/queue")
        except Exception as exc:
            return {
                "connected": False,
                "baseUrl": self.base_url,
                "error": str(exc),
                "queue": {"running": 0, "pending": 0},
            }

        return {
            "connected": True,
            "baseUrl": self.base_url,
            "system": stats.get("system") or stats,
            "queue": {
                "running": self._queue_count(queue.get("queue_running")),
                "pending": self._queue_count(queue.get("queue_pending")),
            },
        }

    def object_info(self) -> dict[str, Any]:
        return self._get_json("/object_info")

    def submit_prompt(self, workflow: dict[str, Any], client_id: str) -> dict[str, Any]:
        if not isinstance(workflow, dict) or not workflow:
            raise ApiError("ComfyUI workflow must be a non-empty dict", status_code=400)

        try:
            response = requests.post(
                self._url("/prompt"),
                json={"prompt": workflow, "client_id": client_id},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.HTTPError as exc:
            response_obj = exc.response
            raise ApiError(
                "ComfyUI prompt request failed",
                status_code=response_obj.status_code if response_obj is not None else 502,
                details=response_obj.text if response_obj is not None else "",
            ) from exc
        except requests.RequestException as exc:
            raise ApiError(f"ComfyUI prompt request failed: {exc}", status_code=502) from exc
        except ValueError as exc:
            details = response.text if "response" in locals() else ""
            raise ApiError(
                f"Invalid JSON from ComfyUI: {exc}",
                status_code=502,
                details=details,
            ) from exc

        if not isinstance(payload, dict):
            return {"data": payload}
        if payload.get("error"):
            raise ApiError("ComfyUI prompt rejected", status_code=400, details=str(payload["error"]))
        return payload

    def history(self, prompt_id: str) -> dict[str, Any]:
        if not prompt_id:
            raise ApiError("prompt_id is required", status_code=400)
        return self._get_json(f"/history/{prompt_id}")

    def normalize_history(self, prompt_id: str, history: dict[str, Any]) -> dict[str, Any]:
        item = history.get(prompt_id) if isinstance(history, dict) else None
        if not isinstance(item, dict):
            return {"promptId": prompt_id, "status": "running", "results": []}

        results = []
        outputs = item.get("outputs") or {}
        if isinstance(outputs, dict):
            for node_id, output in outputs.items():
                if not isinstance(output, dict):
                    continue
                images = output.get("images") or []
                if not isinstance(images, list):
                    continue
                for image in images:
                    if not isinstance(image, dict) or not image.get("filename"):
                        continue
                    results.append(
                        {
                            "nodeId": str(node_id),
                            "filename": image["filename"],
                            "subfolder": image.get("subfolder") or "",
                            "type": image.get("type") or "output",
                        }
                    )

        return {
            "promptId": prompt_id,
            "status": "succeeded" if results else "running",
            "results": results,
        }

    def upload_data_url(self, data_url: str, filename: str = "input.png") -> dict[str, Any]:
        if not isinstance(data_url, str) or "," not in data_url:
            raise ApiError("Invalid data URL", status_code=400)
        header, encoded = data_url.split(",", 1)
        mime_type = "image/png"
        if header.startswith("data:"):
            mime_type = (header[5:].split(";", 1)[0] or mime_type).strip()

        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ApiError(f"Invalid image data URL: {exc}", status_code=400) from exc

        try:
            response = requests.post(
                self._url("/upload/image"),
                files={"image": (filename, image_bytes, mime_type)},
                data={"overwrite": "true", "type": "input"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.HTTPError as exc:
            response_obj = exc.response
            raise ApiError(
                "ComfyUI upload failed",
                status_code=response_obj.status_code if response_obj is not None else 502,
                details=response_obj.text if response_obj is not None else "",
            ) from exc
        except requests.RequestException as exc:
            raise ApiError(f"ComfyUI upload failed: {exc}", status_code=502) from exc
        except ValueError as exc:
            details = response.text if "response" in locals() else ""
            raise ApiError(
                f"Invalid JSON from ComfyUI: {exc}",
                status_code=502,
                details=details,
            ) from exc

        if isinstance(payload, dict):
            return payload
        return {"data": payload}

    def view_url(self, filename: str, subfolder: str = "", image_type: str = "output") -> str:
        if not filename:
            raise ApiError("filename is required", status_code=400)
        query = urlencode(
            {
                "filename": filename,
                "subfolder": subfolder or "",
                "type": image_type or "output",
            }
        )
        return self._url(f"/view?{query}")

    def view_image(
        self,
        filename: str,
        subfolder: str = "",
        image_type: str = "output",
    ) -> dict[str, Any]:
        try:
            response = requests.get(
                self.view_url(filename, subfolder, image_type),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ApiError(f"ComfyUI image request failed: {exc}", status_code=502) from exc

        return {
            "bytes": response.content,
            "mimetype": response.headers.get("content-type") or "image/png",
        }

    @staticmethod
    def _queue_count(value: Any) -> int:
        if isinstance(value, list):
            return len(value)
        if isinstance(value, int):
            return value
        return 0


_comfyui_service: Optional[ComfyUIService] = None


def get_comfyui_service() -> ComfyUIService:
    global _comfyui_service
    if _comfyui_service is None:
        _comfyui_service = ComfyUIService()
    return _comfyui_service
