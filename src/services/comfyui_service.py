"""HTTP adapter for a local ComfyUI server."""

from __future__ import annotations

import base64
import binascii
import re
import uuid
from pathlib import PurePath
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from ..config import get_config
from ..utils.errors import ApiError


DEFAULT_COMFYUI_BASE_URL = "http://127.0.0.1:8188"
ALLOWED_IMAGE_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
ALLOWED_VIEW_TYPES = {"input", "output", "temp"}
PROMPT_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


class ComfyUIService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_upload_bytes: Optional[int] = None,
    ):
        config = get_config()
        configured_url = getattr(config, "comfyui_base_url", None)
        self.base_url = (base_url or configured_url or DEFAULT_COMFYUI_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_upload_bytes = max_upload_bytes
        if self.max_upload_bytes is None:
            self.max_upload_bytes = int(getattr(config, "max_reference_image_bytes", 5 * 1024 * 1024))

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
        if not isinstance(prompt_id, str) or not PROMPT_ID_PATTERN.fullmatch(prompt_id):
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
        mime_type = self._parse_data_url_mime_type(header)
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise ApiError("Unsupported image MIME type", status_code=400)
        if self._estimated_base64_bytes(encoded) > int(self.max_upload_bytes or 0):
            raise ApiError("Image upload is too large", status_code=400)

        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ApiError(f"Invalid image data URL: {exc}", status_code=400) from exc
        if len(image_bytes) > int(self.max_upload_bytes or 0):
            raise ApiError("Image upload is too large", status_code=400)

        upload_filename = self._upload_filename(filename, mime_type)

        try:
            response = requests.post(
                self._url("/upload/image"),
                files={"image": (upload_filename, image_bytes, mime_type)},
                data={"overwrite": "false", "type": "input"},
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
        self._validate_view_name("filename", filename, allow_empty=False)
        self._validate_view_name("subfolder", subfolder or "", allow_empty=True)
        if image_type not in ALLOWED_VIEW_TYPES:
            raise ApiError("Invalid image type", status_code=400)
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

        mimetype = response.headers.get("content-type") or ""
        if not mimetype.lower().startswith("image/"):
            raise ApiError("ComfyUI returned non-image content", status_code=400)

        return {
            "bytes": response.content,
            "mimetype": mimetype,
        }

    @staticmethod
    def _queue_count(value: Any) -> int:
        if isinstance(value, list):
            return len(value)
        if isinstance(value, int):
            return value
        return 0

    @staticmethod
    def _parse_data_url_mime_type(header: str) -> str:
        if not header.startswith("data:"):
            raise ApiError("Invalid data URL", status_code=400)
        mime_type = (header[5:].split(";", 1)[0] or "").strip().lower()
        if not mime_type:
            raise ApiError("Invalid data URL MIME type", status_code=400)
        return mime_type

    @staticmethod
    def _estimated_base64_bytes(encoded: str) -> int:
        padding = len(encoded) - len(encoded.rstrip("="))
        return max(0, (len(encoded) * 3 // 4) - padding)

    @staticmethod
    def _upload_filename(filename: str, mime_type: str) -> str:
        default_ext = ALLOWED_IMAGE_MIME_TYPES[mime_type]
        raw_name = PurePath(filename or "").name
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_name).strip("._-")
        if not safe_name:
            safe_name = f"input{default_ext}"

        path = PurePath(safe_name)
        ext = path.suffix.lower()
        if ext not in set(ALLOWED_IMAGE_MIME_TYPES.values()) | {".jpeg"}:
            safe_name = f"{path.stem or 'input'}{default_ext}"
        return f"{uuid.uuid4().hex}_{safe_name}"

    @staticmethod
    def _validate_view_name(label: str, value: str, allow_empty: bool) -> None:
        if value == "" and allow_empty:
            return
        if not isinstance(value, str) or not value:
            raise ApiError(f"{label} is required", status_code=400)
        if "/" in value or "\\" in value or "?" in value or "#" in value:
            raise ApiError(f"Invalid {label}", status_code=400)
        if value in {".", ".."} or ".." in value:
            raise ApiError(f"Invalid {label}", status_code=400)


_comfyui_service: Optional[ComfyUIService] = None


def get_comfyui_service() -> ComfyUIService:
    global _comfyui_service
    if _comfyui_service is None:
        _comfyui_service = ComfyUIService()
    return _comfyui_service
