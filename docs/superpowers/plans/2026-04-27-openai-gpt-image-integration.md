# OpenAI GPT Image Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real `openai` image-provider path that calls the official OpenAI Images API for `gpt-image-1.5`, `gpt-image-1`, and `gpt-image-1-mini` text-to-image and reference-image edits while preserving the existing `/api/draw` and `/api/result` flow.

**Architecture:** Keep the current Flask + vanilla JS app structure and branch inside `AIService.generate_image()` when the generic image lane selects `imageProvider=openai`. The OpenAI path runs synchronously against the official Images API, then writes the completed result into a lightweight local task store so the existing frontend submit/poll/render flow continues to work with minimal UI changes.

**Tech Stack:** Flask, Python `unittest`, `requests`, vanilla JavaScript, Jinja2, local JSON/status-file storage

---

## File Structure

**Create**
- `src/services/openai_image_service.py`
- `tests/test_openai_gpt_image_integration.py`

**Modify**
- `src/services/ai_service.py`
- `src/services/provider_config_service.py`
- `static/js/app.js`
- `static/js/api-service.js`
- `tests/test_model_catalog.py`

**Regression Tests**
- `tests/test_brand_surfaces.py`
- `tests/test_user_model.py`

### Task 1: Lock The OpenAI Image Routing In Tests

**Files:**
- Create: `tests/test_openai_gpt_image_integration.py`
- Test: `tests/test_openai_gpt_image_integration.py`

- [ ] **Step 1: Write the failing routing and defaults tests**

Create `tests/test_openai_gpt_image_integration.py` with:

```python
import base64
import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def build_services():
    tmpdir = tempfile.TemporaryDirectory()
    data_dir = Path(tmpdir.name) / "data"
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["DB_PATH"] = str(data_dir / "app.db")
    os.environ["APP_SECRET_KEY"] = "test-secret"

    import src.config as config_module
    import src.services.ai_service as ai_service_module
    import src.services.api_key_service as api_key_service_module
    import src.services.database as database_module
    import src.services.provider_config_service as provider_config_service_module

    config_module._config_instance = None
    ai_service_module._ai_service = None
    api_key_service_module._api_key_service = None
    provider_config_service_module._provider_config_service = None
    database_module.db_manager = None

    ai_service_module = importlib.reload(ai_service_module)
    provider_config_service_module = importlib.reload(provider_config_service_module)

    return (
        tmpdir,
        ai_service_module.get_ai_service(),
        provider_config_service_module.get_provider_config_service(),
    )


class OpenAIGptImageIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in ("DATA_DIR", "DB_PATH", "APP_SECRET_KEY")
        }
        self.tmpdir, self.ai_service, self.provider_config = build_services()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_openai_defaults_to_gpt_image_1_5(self):
        defaults = self.provider_config.get_defaults(1, "openai")
        self.assertEqual(defaults["imageModel"], "gpt-image-1.5")

    @patch("src.services.ai_service.get_paper_banana_service")
    @patch("src.services.ai_service.get_openai_image_service")
    def test_generate_image_routes_generic_openai_requests_to_openai_service(
        self, openai_factory, paper_factory
    ):
        openai_service = MagicMock()
        openai_service.submit_generation.return_value = {"id": "oa-task-1"}
        openai_factory.return_value = openai_service

        result = self.ai_service.generate_image(
            1,
            {
                "prompt": "a realistic microscope photo of neurons",
                "provider": "openai",
                "imageProvider": "openai",
                "imageModel": "gpt-image-1.5",
                "imageSize": "1K",
                "urls": [],
            },
        )

        self.assertEqual(result["code"], 0)
        self.assertEqual(result["data"]["id"], "oa-task-1")
        openai_service.submit_generation.assert_called_once()
        paper_factory.assert_not_called()

    @patch("src.services.ai_service.get_paper_banana_service")
    @patch("src.services.ai_service.get_openai_image_service")
    def test_generate_image_keeps_non_openai_requests_on_paperbanana(
        self, openai_factory, paper_factory
    ):
        paper_service = MagicMock()
        paper_service.submit_diagram.return_value = "paper-task-1"
        paper_factory.return_value = paper_service

        result = self.ai_service.generate_image(
            1,
            {
                "prompt": "a signaling pathway diagram",
                "provider": "grsai",
                "imageProvider": "grsai",
                "imageModel": "nano-banana-pro",
            },
        )

        self.assertEqual(result["data"]["id"], "paper-task-1")
        openai_factory.assert_not_called()
        paper_service.submit_diagram.assert_called_once()
```

- [ ] **Step 2: Add failing reference-image and result-shape tests**

Extend the same file with:

```python
    @patch("src.services.ai_service.get_openai_image_service")
    def test_generate_image_passes_reference_images_to_openai_service(self, openai_factory):
        openai_service = MagicMock()
        openai_service.submit_generation.return_value = {"id": "oa-task-edit"}
        openai_factory.return_value = openai_service

        image_data = base64.b64encode(b"fake-png").decode("ascii")
        self.ai_service.generate_image(
            1,
            {
                "prompt": "turn this into a clean lab photo",
                "provider": "openai",
                "imageProvider": "openai",
                "imageModel": "gpt-image-1.5",
                "urls": [f"data:image/png;base64,{image_data}"],
            },
        )

        args, kwargs = openai_service.submit_generation.call_args
        self.assertEqual(kwargs["reference_images"][0], f"data:image/png;base64,{image_data}")

    @patch("src.services.ai_service.get_openai_image_service")
    def test_get_image_result_reads_completed_openai_payload(self, openai_factory):
        openai_service = MagicMock()
        openai_service.submit_generation.return_value = {"id": "oa-task-2"}
        openai_service.get_result_payload.return_value = {
            "id": "oa-task-2",
            "status": "succeeded",
            "progress": 100,
            "stage": "completed",
            "stageMessage": "图像生成完成",
            "model": "gpt-image-1.5",
            "results": [{"url": "data:image/png;base64,ZmFrZQ==", "content": "ok"}],
        }
        openai_factory.return_value = openai_service

        self.ai_service.generate_image(
            1,
            {
                "prompt": "a realistic microscope photo of neurons",
                "provider": "openai",
                "imageProvider": "openai",
                "imageModel": "gpt-image-1.5",
            },
        )
        result = self.ai_service.get_image_result(1, "oa-task-2")

        self.assertEqual(result["code"], 0)
        self.assertEqual(result["data"]["status"], "succeeded")
        self.assertEqual(result["data"]["results"][0]["url"], "data:image/png;base64,ZmFrZQ==")
```

- [ ] **Step 3: Run the new test file to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_openai_gpt_image_integration -v`

Expected: failures because `get_openai_image_service` does not exist yet, `openai` defaults still point at `gpt-image-1`, and `AIService.generate_image()` still routes all requests to `PaperBanana`.

- [ ] **Step 4: Commit the red tests**

```bash
git add tests/test_openai_gpt_image_integration.py
git commit -m "test: add openai gpt-image integration coverage"
```

### Task 2: Add A Dedicated OpenAI Image Service

**Files:**
- Create: `src/services/openai_image_service.py`
- Test: `tests/test_openai_gpt_image_integration.py`

- [ ] **Step 1: Write the failing service tests for generations and edits**

Add a new test class to `tests/test_openai_gpt_image_integration.py`:

```python
class OpenAIImageServiceTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in ("DATA_DIR", "DB_PATH", "APP_SECRET_KEY")
        }
        self.tmpdir, self.ai_service, _ = build_services()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    @patch("src.services.openai_image_service.requests.post")
    def test_submit_generation_uses_images_generations_without_reference_images(self, post_mock):
        from src.services.openai_image_service import get_openai_image_service

        post_mock.return_value.status_code = 200
        post_mock.return_value.json.return_value = {
            "data": [{"b64_json": "ZmFrZQ=="}],
            "usage": {"total_tokens": 123},
        }

        with patch.object(
            self.ai_service.api_key_service,
            "get_active_api_key_value",
            return_value="sk-test",
        ), patch.object(
            self.ai_service.api_key_service,
            "get_active_base_url",
            return_value="https://api.openai.com/v1",
        ):
            result = get_openai_image_service().submit_generation(
                user_id=1,
                prompt="photo of a neuron culture",
                model="gpt-image-1.5",
                image_size="1K",
                reference_images=[],
            )

        self.assertTrue(result["id"].startswith("oa-"))
        self.assertIn("results", get_openai_image_service().get_result_payload(result["id"]))
        self.assertIn("/images/generations", post_mock.call_args.kwargs["url"])

    @patch("src.services.openai_image_service.requests.post")
    def test_submit_generation_uses_images_edits_with_reference_images(self, post_mock):
        from src.services.openai_image_service import get_openai_image_service

        post_mock.return_value.status_code = 200
        post_mock.return_value.json.return_value = {"data": [{"b64_json": "ZmFrZQ=="}]}

        with patch.object(
            self.ai_service.api_key_service,
            "get_active_api_key_value",
            return_value="sk-test",
        ), patch.object(
            self.ai_service.api_key_service,
            "get_active_base_url",
            return_value="https://api.openai.com/v1",
        ):
            get_openai_image_service().submit_generation(
                user_id=1,
                prompt="edit this into a clean microscopy photo",
                model="gpt-image-1.5",
                image_size="1K",
                reference_images=["data:image/png;base64,ZmFrZS1pbWFnZQ=="],
            )

        self.assertIn("/images/edits", post_mock.call_args.kwargs["url"])
        self.assertIn("files", post_mock.call_args.kwargs)
```

- [ ] **Step 2: Implement the minimal OpenAI image service**

Create `src/services/openai_image_service.py` with:

```python
from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..config import get_config
from ..utils.errors import ApiError, NotFoundError, ValidationError
from ..utils.validation import get_validation_service
from .api_key_service import get_api_key_service


class OpenAIImageService:
    def __init__(self) -> None:
        self.config = get_config()
        self.api_key_service = get_api_key_service()
        self.root = Path(self.config.data_dir) / "openai_image_jobs"
        self.root.mkdir(parents=True, exist_ok=True)

    def _job_path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"

    def _resolve_base_url(self, user_id: Optional[int]) -> str:
        base_url = self.api_key_service.get_active_base_url(user_id, provider="openai").rstrip("/")
        return base_url or "https://api.openai.com/v1"

    def _build_headers(self, user_id: Optional[int]) -> Dict[str, str]:
        api_key = self.api_key_service.get_active_api_key_value(user_id, provider="openai")
        if not api_key:
            raise ValidationError("Missing API key. 请在“API 设置”中添加 OpenAI Key。")
        return {
            "Authorization": f"Bearer {api_key}",
        }

    def _size_for_model(self, model: str, image_size: str) -> str:
        normalized_size = (image_size or "1K").upper()
        return {
            "1K": "1024x1024",
            "2K": "1536x1024",
            "4K": "1536x1024",
        }.get(normalized_size, "1024x1024")

    def _decode_data_url(self, data_url: str, index: int) -> Tuple[str, bytes, str]:
        if not data_url.startswith("data:"):
            raise ValidationError("参考图必须是 data URL")
        try:
            header, encoded = data_url.split(",", 1)
        except ValueError as exc:
            raise ValidationError("参考图数据格式无效") from exc
        if ";base64" not in header:
            raise ValidationError("参考图必须使用 base64 data URL")
        mime = header[5:].split(";", 1)[0] or "image/png"
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValidationError("参考图 base64 数据无效") from exc
        extension = mime.split("/")[-1] or "png"
        filename = f"reference-{index}.{extension}"
        return filename, raw, mime

    def _write_payload(self, payload: Dict[str, Any]) -> None:
        self._job_path(payload["id"]).write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )

    def submit_generation(
        self,
        *,
        user_id: Optional[int],
        prompt: str,
        model: str,
        image_size: str,
        reference_images: List[str],
    ) -> Dict[str, Any]:
        validation = get_validation_service()
        reference_images = validation.sanitize_urls(reference_images)
        validation.validate_reference_images(reference_images)

        base_url = self._resolve_base_url(user_id)
        headers = self._build_headers(user_id)
        size = self._size_for_model(model, image_size)
        job_id = f"oa-{uuid.uuid4().hex}"

        if reference_images:
            files = []
            data = {"model": model, "prompt": prompt, "size": size}
            for index, item in enumerate(reference_images, start=1):
                filename, raw, mime = self._decode_data_url(item, index)
                files.append(("image[]", (filename, raw, mime)))
            response = requests.post(
                url=f"{base_url}/images/edits",
                headers=headers,
                data=data,
                files=files,
                timeout=180,
            )
        else:
            response = requests.post(
                url=f"{base_url}/images/generations",
                headers={**headers, "Content-Type": "application/json"},
                json={"model": model, "prompt": prompt, "size": size},
                timeout=180,
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            details = exc.response.text if exc.response is not None else ""
            raise ApiError("OpenAI image request failed", status_code=exc.response.status_code if exc.response else 502, details=details)

        payload = response.json()
        image_data = ((payload.get("data") or [{}])[0].get("b64_json") or "").strip()
        if not image_data:
            raise ApiError("OpenAI image response did not contain image data", status_code=502)

        result_payload = {
            "id": job_id,
            "status": "succeeded",
            "progress": 100,
            "stage": "completed",
            "stageMessage": "图像生成完成",
            "model": model,
            "results": [
                {
                    "url": f"data:image/png;base64,{image_data}",
                    "content": payload.get("revised_prompt") or "OpenAI generated",
                }
            ],
            "usage": payload.get("usage") or {},
        }
        self._write_payload(result_payload)
        return {"id": job_id}

    def get_result_payload(self, job_id: str) -> Dict[str, Any]:
        path = self._job_path(job_id)
        if not path.exists():
            raise NotFoundError("Output not ready")
        return json.loads(path.read_text(encoding="utf-8"))

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        payload = self.get_result_payload(job_id)
        return payload


_openai_image_service: Optional[OpenAIImageService] = None


def get_openai_image_service() -> OpenAIImageService:
    global _openai_image_service
    if _openai_image_service is None:
        _openai_image_service = OpenAIImageService()
    return _openai_image_service
```

- [ ] **Step 3: Run the service tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_openai_gpt_image_integration.OpenAIImageServiceTest -v`

Expected: generation path hits `/images/generations`, edit path hits `/images/edits`, and completed payloads are written to the local OpenAI job store.

- [ ] **Step 4: Commit the new service**

```bash
git add src/services/openai_image_service.py tests/test_openai_gpt_image_integration.py
git commit -m "feat: add openai image service"
```

### Task 3: Branch AIService Into OpenAI And PaperBanana Paths

**Files:**
- Modify: `src/services/ai_service.py`
- Modify: `src/services/provider_config_service.py`
- Test: `tests/test_openai_gpt_image_integration.py`

- [ ] **Step 1: Write the failing default-model and get-result integration tests**

Extend `tests/test_openai_gpt_image_integration.py` with:

```python
    @patch("src.services.ai_service.get_openai_image_service")
    def test_generate_image_uses_default_openai_model_when_image_model_missing(self, openai_factory):
        openai_service = MagicMock()
        openai_service.submit_generation.return_value = {"id": "oa-default-model"}
        openai_factory.return_value = openai_service

        self.ai_service.generate_image(
            1,
            {
                "prompt": "photo of neurons",
                "provider": "openai",
                "imageProvider": "openai",
            },
        )

        _, kwargs = openai_service.submit_generation.call_args
        self.assertEqual(kwargs["model"], "gpt-image-1.5")

    @patch("src.services.ai_service.get_openai_image_service")
    def test_cancel_image_result_uses_openai_service_for_openai_jobs(self, openai_factory):
        openai_service = MagicMock()
        openai_service.cancel_job.return_value = {"id": "oa-task-3", "status": "succeeded"}
        openai_factory.return_value = openai_service

        result = self.ai_service.cancel_image_result(1, "oa-task-3")

        self.assertEqual(result["code"], 0)
        openai_service.cancel_job.assert_called_once_with("oa-task-3")
```

- [ ] **Step 2: Update provider defaults and add OpenAI routing in `AIService`**

Modify `src/services/provider_config_service.py`:

```python
DEFAULT_MODELS: Dict[str, Dict[str, str]] = {
    "grsai": {"textModel": "gemini-2.5-pro", "imageModel": "nano-banana-pro"},
    "openai": {"textModel": "gpt-4o-mini", "imageModel": "gpt-image-1.5"},
    "deepseek": {"textModel": "deepseek-chat", "imageModel": "gpt-image-1"},
    "openrouter": {"textModel": "openai/gpt-4o-mini", "imageModel": "gpt-image-1"},
    "anthropic": {"textModel": "claude-3-5-sonnet-latest", "imageModel": "gpt-image-1"},
    "google": {"textModel": "gemini-2.5-pro", "imageModel": "gemini-3-pro-image-preview"},
}
```

Modify `src/services/ai_service.py`:

```python
from .openai_image_service import get_openai_image_service


OPENAI_IMAGE_MODELS = {
    "gpt-image-1.5",
    "gpt-image-1",
    "gpt-image-1-mini",
}


def _is_openai_image_request(self, pipeline_mode: str, image_provider: str) -> bool:
    mode = (pipeline_mode or "full").strip().lower()
    return mode in {"full", "image_only"} and (image_provider or "").strip().lower() == "openai"
```

Then branch `generate_image()` before the `PaperBanana` submit call:

```python
        if self._is_openai_image_request(pipeline_mode, image_provider):
            if image_model not in OPENAI_IMAGE_MODELS:
                raise ValidationError(f"OpenAI 图像模型不受支持：{image_model}")

            payload = get_openai_image_service().submit_generation(
                user_id=user_id,
                prompt=prompt or caption,
                model=image_model,
                image_size=image_size,
                reference_images=validation.sanitize_urls(data.get("urls") or []),
            )

            if user_id:
                UsageStats.record_usage_for_user(user_id)

            return {"code": 0, "data": payload}
```

Also branch `get_image_result()` and `cancel_image_result()`:

```python
        if draw_id.startswith("oa-") or draw_id.startswith("openai-"):
            payload = get_openai_image_service().get_result_payload(draw_id)
            if user_id:
                UsageStats.record_usage_for_user(user_id)
            return {"code": 0, "data": payload}
```

Use the same pattern for `cancel_image_result()` with `cancel_job()`.

- [ ] **Step 3: Refine the OpenAI job id prefix to make result routing deterministic**

Adjust `src/services/openai_image_service.py`:

```python
job_id = f"oa-{uuid.uuid4().hex}"
```

- [ ] **Step 4: Run the AI service integration tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_openai_gpt_image_integration.OpenAIGptImageIntegrationTest -v`

Expected: OpenAI requests route to `OpenAIImageService`, defaults fall back to `gpt-image-1.5`, and non-OpenAI traffic still uses `PaperBanana`.

- [ ] **Step 5: Commit the service routing changes**

```bash
git add src/services/ai_service.py src/services/provider_config_service.py src/services/openai_image_service.py tests/test_openai_gpt_image_integration.py
git commit -m "feat: route openai image requests through official api"
```

### Task 4: Keep The Existing Frontend Flow But Add OpenAI Model Catalog Support

**Files:**
- Modify: `static/js/app.js`
- Modify: `static/js/api-service.js`
- Modify: `tests/test_model_catalog.py`
- Test: `tests/test_model_catalog.py`

- [ ] **Step 1: Write the failing catalog test for the OpenAI provider**

Extend `tests/test_model_catalog.py` with:

```python
    def test_openai_provider_catalog_includes_current_gpt_image_models(self):
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")
        provider_block = app_js.split("openai:", 1)[1]

        for model in ("gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini"):
            self.assertIn(model, provider_block, model)
```

- [ ] **Step 2: Update the frontend model catalogs and defaults**

Modify `static/js/api-service.js`:

```javascript
    imageModels: [
        { id: 'sora-image', name: 'Sora Image', description: 'grsai 生图模型' },
        { id: 'gpt-image-1.5', name: 'GPT Image 1.5', description: '高质量图像模型' },
        { id: 'gpt-image-1', name: 'GPT Image 1', description: 'OpenAI 官方图像模型' },
        { id: 'gpt-image-1-mini', name: 'GPT Image 1 Mini', description: '轻量 OpenAI 图像模型' },
```

Modify `static/js/app.js`:

```javascript
    openai: {
        text: ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini', 'gpt-4.1'],
        image: ['gpt-image-1.5', 'gpt-image-1', 'gpt-image-1-mini']
    },
```

Keep the generic submit path unchanged so the frontend still sends `/api/draw` and then polls `/api/result`.

- [ ] **Step 3: Run the catalog test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_model_catalog -v`

Expected: the OpenAI provider lists `gpt-image-1.5`, `gpt-image-1`, and `gpt-image-1-mini`, while the existing grsai catalog assertions remain green.

- [ ] **Step 4: Commit the frontend catalog update**

```bash
git add static/js/app.js static/js/api-service.js tests/test_model_catalog.py
git commit -m "feat: expose current openai gpt-image models in ui"
```

### Task 5: Verify The End-To-End Contract And Regression Suite

**Files:**
- Test: `tests/test_openai_gpt_image_integration.py`
- Test: `tests/test_model_catalog.py`
- Regression Tests: `tests/test_brand_surfaces.py`
- Regression Tests: `tests/test_user_model.py`

- [ ] **Step 1: Add one end-to-end contract test for the completed OpenAI payload**

Extend `tests/test_openai_gpt_image_integration.py` with:

```python
    @patch("src.services.openai_image_service.requests.post")
    def test_submit_generation_persists_payload_for_existing_polling_flow(self, post_mock):
        from src.services.openai_image_service import get_openai_image_service

        post_mock.return_value.status_code = 200
        post_mock.return_value.json.return_value = {
            "data": [{"b64_json": "ZmFrZQ=="}],
            "revised_prompt": "clean microscope photo of neurons",
        }

        with patch.object(
            self.ai_service.api_key_service,
            "get_active_api_key_value",
            return_value="sk-test",
        ), patch.object(
            self.ai_service.api_key_service,
            "get_active_base_url",
            return_value="https://api.openai.com/v1",
        ):
            job = get_openai_image_service().submit_generation(
                user_id=1,
                prompt="photo of neurons",
                model="gpt-image-1.5",
                image_size="1K",
                reference_images=[],
            )

        payload = get_openai_image_service().get_result_payload(job["id"])
        self.assertEqual(payload["status"], "succeeded")
        self.assertTrue(payload["results"][0]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(payload["stage"], "completed")
```

- [ ] **Step 2: Run the focused OpenAI suite**

Run: `.venv/bin/python -m unittest tests.test_openai_gpt_image_integration tests.test_model_catalog -v`

Expected: all OpenAI integration and model catalog tests pass.

- [ ] **Step 3: Run the small regression suite**

Run: `.venv/bin/python -m unittest tests.test_brand_surfaces tests.test_user_model -v`

Expected: branding/login/manual surfaces still render and the user timestamp test remains green.

- [ ] **Step 4: Run the full project unittest suite**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: full green test run with the new OpenAI integration coverage included.

- [ ] **Step 5: Commit the verification pass**

```bash
git add tests/test_openai_gpt_image_integration.py tests/test_model_catalog.py
git commit -m "test: verify openai gpt-image integration"
```
