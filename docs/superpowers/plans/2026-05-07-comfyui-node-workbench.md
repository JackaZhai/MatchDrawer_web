# ComfyUI Node Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the left-sidebar **生图工作台** with a native ComfyUI-style node canvas, real ComfyUI API execution, and managed local ComfyUI runtime support.

**Architecture:** Add focused backend services for workflow normalization, ComfyUI HTTP calls, and local runtime management, then expose them through `/api/comfyui/*` Flask routes. Add a vanilla JavaScript workbench module that renders API-format workflow JSON as editable nodes and submits the updated workflow to the backend. Keep ComfyUI itself outside the Git repository under `data/comfyui/runtime/`.

**Tech Stack:** Flask, Python `unittest`, `requests`, vanilla JavaScript, Jinja2 templates, CSS, local filesystem state under ignored `data/**`.

---

## File Structure

**Create**
- `src/services/comfyui_workflow_service.py`: Parse ComfyUI API workflow JSON into a canvas model, recognize known GrsAI nodes, preserve unknown nodes, and apply input edits.
- `src/services/comfyui_service.py`: Safe HTTP adapter for ComfyUI `/system_stats`, `/queue`, `/object_info`, `/upload/image`, `/prompt`, `/history/{prompt_id}`, and `/view`.
- `src/services/comfyui_runtime_service.py`: Local runtime state and managed install/start/stop command orchestration under `data/comfyui/runtime/`.
- `src/routes/comfyui_routes.py`: Authenticated `/api/comfyui/*` Flask routes.
- `static/js/comfyui-workbench.js`: Frontend state, import, render, edit, upload, run, poll, and result rendering for the node workbench.
- `static/css/comfyui-workbench.css`: Workbench-specific layout and node canvas styling.
- `integrations/comfyui_grsai/workflows/text_image_api.json`: Compact starter API workflow for GrsAI text/image mode.
- `tests/test_comfyui_workflow_service.py`: Unit tests for workflow parsing and edit preservation.
- `tests/test_comfyui_service.py`: Unit tests for ComfyUI upstream adapter behavior.
- `tests/test_comfyui_runtime_service.py`: Unit tests for runtime state and command construction.
- `tests/test_comfyui_routes.py`: Flask route tests using mocked services.
- `tests/test_comfyui_workbench_assets.py`: Static frontend/template tests.

**Modify**
- `app.py`: Register `comfyui_bp`.
- `templates/index.html`: Add sidebar entry, page container, script/style includes, and workbench DOM anchors.
- `static/js/app.js`: Add page config, i18n labels, DOM references, page initialization, and nav behavior for `comfyui-workbench`.
- `.gitignore`: Already ignores `data/**` and `.superpowers/`; verify this remains true.

**Verification Commands**
- `.venv/bin/python -m unittest tests.test_comfyui_workflow_service -v`
- `.venv/bin/python -m unittest tests.test_comfyui_service -v`
- `.venv/bin/python -m unittest tests.test_comfyui_runtime_service -v`
- `.venv/bin/python -m unittest tests.test_comfyui_routes -v`
- `.venv/bin/python -m unittest tests.test_comfyui_workbench_assets -v`
- `.venv/bin/python -m unittest discover -s tests`

### Task 1: Workflow JSON Normalization

**Files:**
- Create: `src/services/comfyui_workflow_service.py`
- Create: `tests/test_comfyui_workflow_service.py`

- [ ] **Step 1: Write the failing workflow normalization tests**

Create `tests/test_comfyui_workflow_service.py`:

```python
import unittest


SAMPLE_WORKFLOW = {
    "1": {
        "class_type": "LoadImage",
        "inputs": {"image": "input.png"},
        "_meta": {"title": "Load reference"},
    },
    "2": {
        "class_type": "GrsAINanoBananaTextImage",
        "inputs": {
            "prompt": "a clean product photo",
            "model": "nano-banana-pro",
            "aspectRatio": "1:1",
            "imageSize": "1K",
            "image1": ["1", 0],
        },
        "_meta": {"title": "GrsAI Nano Banana"},
    },
    "3": {
        "class_type": "PreviewImage",
        "inputs": {"images": ["2", 0]},
        "_meta": {"title": "Preview"},
    },
    "7": {
        "class_type": "ThirdPartyUnknownNode",
        "inputs": {"value": 4, "source": ["2", 1]},
    },
}


class ComfyUIWorkflowServiceTest(unittest.TestCase):
    def test_normalize_workflow_extracts_nodes_and_links(self):
        from src.services.comfyui_workflow_service import normalize_workflow

        result = normalize_workflow(SAMPLE_WORKFLOW)

        self.assertEqual(result["nodeCount"], 4)
        self.assertEqual(result["linkCount"], 3)
        self.assertEqual(result["nodes"][1]["id"], "2")
        self.assertEqual(result["nodes"][1]["classType"], "GrsAINanoBananaTextImage")
        self.assertEqual(result["nodes"][1]["kind"], "grsai")
        self.assertEqual(result["nodes"][3]["kind"], "unknown")
        self.assertEqual(result["links"][0]["fromNode"], "1")
        self.assertEqual(result["links"][0]["fromOutput"], 0)
        self.assertEqual(result["links"][0]["toNode"], "2")
        self.assertEqual(result["links"][0]["toInput"], "image1")

    def test_normalize_workflow_rejects_non_api_format(self):
        from src.services.comfyui_workflow_service import normalize_workflow
        from src.utils.errors import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            normalize_workflow({"nodes": [], "links": []})

        self.assertIn("ComfyUI API workflow", str(ctx.exception))

    def test_apply_input_patch_preserves_unknown_fields(self):
        from src.services.comfyui_workflow_service import apply_input_patch

        updated = apply_input_patch(
            SAMPLE_WORKFLOW,
            node_id="2",
            inputs={
                "prompt": "new prompt",
                "imageSize": "2K",
            },
        )

        self.assertEqual(updated["2"]["inputs"]["prompt"], "new prompt")
        self.assertEqual(updated["2"]["inputs"]["imageSize"], "2K")
        self.assertEqual(updated["2"]["inputs"]["image1"], ["1", 0])
        self.assertEqual(updated["7"]["inputs"]["value"], 4)

    def test_apply_input_patch_rejects_missing_node(self):
        from src.services.comfyui_workflow_service import apply_input_patch
        from src.utils.errors import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            apply_input_patch(SAMPLE_WORKFLOW, node_id="999", inputs={"prompt": "x"})

        self.assertIn("node not found", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workflow_service -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.services.comfyui_workflow_service'`.

- [ ] **Step 3: Implement the workflow service**

Create `src/services/comfyui_workflow_service.py`:

```python
"""ComfyUI API workflow parsing helpers."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from ..utils.errors import ValidationError


GRSAI_CLASS_MARKERS = (
    "grsai",
    "nano banana",
    "nanobanana",
    "banana",
    "flux",
    "gpt image",
    "gptimage",
)


def _is_node_payload(node: Any) -> bool:
    return isinstance(node, dict) and isinstance(node.get("class_type"), str)


def _class_kind(class_type: str) -> str:
    normalized = class_type.replace("_", " ").replace("-", " ").lower()
    joined = normalized.replace(" ", "")
    for marker in GRSAI_CLASS_MARKERS:
        if marker in normalized or marker.replace(" ", "") in joined:
            return "grsai"
    if class_type in {"LoadImage", "PreviewImage", "SaveImage"}:
        return "core"
    return "unknown"


def _node_title(node_id: str, node: Dict[str, Any]) -> str:
    meta = node.get("_meta") if isinstance(node.get("_meta"), dict) else {}
    title = str(meta.get("title") or "").strip()
    return title or str(node.get("class_type") or node_id)


def _extract_links(workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    links: List[Dict[str, Any]] = []
    for node_id, node in workflow.items():
        inputs = node.get("inputs") if isinstance(node, dict) else {}
        if not isinstance(inputs, dict):
            continue
        for input_name, value in inputs.items():
            if (
                isinstance(value, list)
                and len(value) == 2
                and str(value[0]) in workflow
                and isinstance(value[1], int)
            ):
                links.append(
                    {
                        "fromNode": str(value[0]),
                        "fromOutput": value[1],
                        "toNode": str(node_id),
                        "toInput": str(input_name),
                    }
                )
    return links


def normalize_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Convert ComfyUI API workflow JSON to a canvas-friendly model."""
    if not isinstance(workflow, dict) or not workflow:
        raise ValidationError("Expected ComfyUI API workflow object")
    if "nodes" in workflow and "links" in workflow:
        raise ValidationError("Expected ComfyUI API workflow JSON, not UI workflow JSON")

    nodes: List[Dict[str, Any]] = []
    for index, node_id in enumerate(sorted(workflow.keys(), key=lambda item: int(item) if str(item).isdigit() else str(item))):
        node = workflow[node_id]
        if not _is_node_payload(node):
            raise ValidationError(f"Invalid ComfyUI API workflow node: {node_id}")
        class_type = str(node.get("class_type") or "")
        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
        nodes.append(
            {
                "id": str(node_id),
                "classType": class_type,
                "title": _node_title(str(node_id), node),
                "kind": _class_kind(class_type),
                "inputs": copy.deepcopy(inputs),
                "position": {"x": 120 + index * 220, "y": 120 + (index % 3) * 110},
            }
        )

    links = _extract_links(workflow)
    return {
        "nodes": nodes,
        "links": links,
        "nodeCount": len(nodes),
        "linkCount": len(links),
        "workflow": copy.deepcopy(workflow),
    }


def apply_input_patch(workflow: Dict[str, Any], node_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Patch one node's scalar inputs while preserving all other workflow JSON."""
    if str(node_id) not in workflow:
        raise ValidationError(f"Workflow node not found: {node_id}")
    if not isinstance(inputs, dict):
        raise ValidationError("inputs must be an object")

    updated = copy.deepcopy(workflow)
    node_inputs = updated[str(node_id)].setdefault("inputs", {})
    if not isinstance(node_inputs, dict):
        raise ValidationError(f"Workflow node inputs are invalid: {node_id}")
    for key, value in inputs.items():
        node_inputs[str(key)] = value
    return updated
```

- [ ] **Step 4: Run the workflow tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workflow_service -v
```

Expected: PASS for all 4 tests.

- [ ] **Step 5: Commit workflow normalization**

Run:

```bash
git add src/services/comfyui_workflow_service.py tests/test_comfyui_workflow_service.py
git commit -m "feat: add comfyui workflow normalization"
```

### Task 2: ComfyUI HTTP Adapter

**Files:**
- Create: `src/services/comfyui_service.py`
- Create: `tests/test_comfyui_service.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/test_comfyui_service.py`:

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class ComfyUIServiceTest(unittest.TestCase):
    def test_status_reports_disconnected_when_system_stats_fails(self):
        from src.services.comfyui_service import ComfyUIService

        svc = ComfyUIService(base_url="http://127.0.0.1:8188")
        with patch("src.services.comfyui_service.requests.get") as get_mock:
            get_mock.side_effect = Exception("connection refused")

            status = svc.status()

        self.assertFalse(status["connected"])
        self.assertEqual(status["baseUrl"], "http://127.0.0.1:8188")
        self.assertIn("connection refused", status["error"])

    def test_status_reads_system_stats_and_queue(self):
        from src.services.comfyui_service import ComfyUIService

        svc = ComfyUIService(base_url="http://127.0.0.1:8188")
        stats_resp = MagicMock()
        stats_resp.json.return_value = {"system": {"python_version": "3.12"}}
        stats_resp.raise_for_status.return_value = None
        queue_resp = MagicMock()
        queue_resp.json.return_value = {"queue_running": [], "queue_pending": [["id", 1]]}
        queue_resp.raise_for_status.return_value = None

        with patch("src.services.comfyui_service.requests.get", side_effect=[stats_resp, queue_resp]):
            status = svc.status()

        self.assertTrue(status["connected"])
        self.assertEqual(status["system"]["python_version"], "3.12")
        self.assertEqual(status["queue"]["pending"], 1)

    def test_submit_prompt_posts_client_id_and_workflow(self):
        from src.services.comfyui_service import ComfyUIService

        svc = ComfyUIService(base_url="http://127.0.0.1:8188")
        response = MagicMock()
        response.json.return_value = {"prompt_id": "abc", "number": 3}
        response.raise_for_status.return_value = None

        with patch("src.services.comfyui_service.requests.post", return_value=response) as post_mock:
            result = svc.submit_prompt({"1": {"class_type": "PreviewImage", "inputs": {}}}, "client-1")

        self.assertEqual(result["prompt_id"], "abc")
        post_mock.assert_called_once()
        url = post_mock.call_args.args[0]
        payload = post_mock.call_args.kwargs["json"]
        self.assertEqual(url, "http://127.0.0.1:8188/prompt")
        self.assertEqual(payload["client_id"], "client-1")
        self.assertIn("1", payload["prompt"])

    def test_normalize_history_extracts_image_references(self):
        from src.services.comfyui_service import ComfyUIService

        history = {
            "abc": {
                "outputs": {
                    "9": {
                        "images": [
                            {"filename": "out.png", "subfolder": "", "type": "output"},
                            {"filename": "temp.png", "subfolder": "x", "type": "temp"},
                        ]
                    }
                }
            }
        }

        result = ComfyUIService.normalize_history("abc", history)

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["results"][0]["filename"], "out.png")
        self.assertEqual(result["results"][1]["subfolder"], "x")

    def test_upload_data_url_posts_file_to_comfyui(self):
        from src.services.comfyui_service import ComfyUIService

        svc = ComfyUIService(base_url="http://127.0.0.1:8188")
        response = MagicMock()
        response.json.return_value = {"name": "input.png", "subfolder": "", "type": "input"}
        response.raise_for_status.return_value = None

        with patch("src.services.comfyui_service.requests.post", return_value=response) as post_mock:
            result = svc.upload_data_url("data:image/png;base64,ZmFrZQ==", "input.png")

        self.assertEqual(result["name"], "input.png")
        files = post_mock.call_args.kwargs["files"]
        self.assertIn("image", files)

    def test_view_image_fetches_bytes_without_exposing_comfyui_url(self):
        from src.services.comfyui_service import ComfyUIService

        svc = ComfyUIService(base_url="http://127.0.0.1:8188")
        response = MagicMock()
        response.content = b"png-bytes"
        response.headers = {"content-type": "image/png"}
        response.raise_for_status.return_value = None

        with patch("src.services.comfyui_service.requests.get", return_value=response) as get_mock:
            payload = svc.view_image("out.png", "", "output")

        self.assertEqual(payload["bytes"], b"png-bytes")
        self.assertEqual(payload["mimetype"], "image/png")
        self.assertEqual(get_mock.call_args.args[0], "http://127.0.0.1:8188/view?filename=out.png&subfolder=&type=output")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the adapter tests to verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_service -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.services.comfyui_service'`.

- [ ] **Step 3: Implement `ComfyUIService`**

Create `src/services/comfyui_service.py`:

```python
"""ComfyUI HTTP adapter."""

from __future__ import annotations

import base64
import io
import mimetypes
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from ..config import get_config
from ..utils.errors import ApiError, ValidationError


class ComfyUIService:
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        config = get_config()
        configured = base_url or getattr(config, "comfyui_base_url", "")
        self.base_url = (configured or "http://127.0.0.1:8188").rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _get_json(self, path: str) -> Dict[str, Any]:
        try:
            response = requests.get(self._url(path), timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ApiError(f"ComfyUI request failed: {exc}", status_code=502)
        except ValueError as exc:
            raise ApiError(f"Invalid JSON from ComfyUI: {exc}", status_code=502)
        return payload if isinstance(payload, dict) else {"data": payload}

    def status(self) -> Dict[str, Any]:
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
                "running": len(queue.get("queue_running") or []),
                "pending": len(queue.get("queue_pending") or []),
            },
        }

    def object_info(self) -> Dict[str, Any]:
        return self._get_json("/object_info")

    def submit_prompt(self, workflow: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        if not isinstance(workflow, dict) or not workflow:
            raise ValidationError("workflow is required")
        payload = {"prompt": workflow, "client_id": client_id}
        try:
            response = requests.post(self._url("/prompt"), json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.HTTPError as exc:
            details = exc.response.text if exc.response is not None else ""
            raise ApiError("ComfyUI prompt submission failed", status_code=502, details=details)
        except requests.RequestException as exc:
            raise ApiError(f"ComfyUI prompt submission failed: {exc}", status_code=502)
        except ValueError as exc:
            raise ApiError(f"Invalid JSON from ComfyUI: {exc}", status_code=502)
        if isinstance(data, dict) and data.get("error"):
            raise ApiError("ComfyUI workflow validation failed", status_code=400, details=str(data))
        return data

    def history(self, prompt_id: str) -> Dict[str, Any]:
        prompt_id = (prompt_id or "").strip()
        if not prompt_id:
            raise ValidationError("prompt_id is required")
        return self._get_json(f"/history/{prompt_id}")

    @staticmethod
    def normalize_history(prompt_id: str, history: Dict[str, Any]) -> Dict[str, Any]:
        item = history.get(prompt_id) if isinstance(history, dict) else None
        if not item:
            return {"id": prompt_id, "status": "running", "results": []}
        outputs = item.get("outputs") if isinstance(item, dict) else {}
        results = []
        if isinstance(outputs, dict):
            for node_id, output in outputs.items():
                images = output.get("images") if isinstance(output, dict) else []
                for image in images or []:
                    if isinstance(image, dict) and image.get("filename"):
                        results.append(
                            {
                                "nodeId": str(node_id),
                                "filename": image.get("filename"),
                                "subfolder": image.get("subfolder") or "",
                                "type": image.get("type") or "output",
                            }
                        )
        return {
            "id": prompt_id,
            "status": "succeeded" if results else "running",
            "results": results,
        }

    def upload_data_url(self, data_url: str, filename: str = "input.png") -> Dict[str, Any]:
        if "," not in data_url:
            raise ValidationError("Invalid image data URL")
        header, encoded = data_url.split(",", 1)
        mime_type = header.split(";")[0].replace("data:", "") or "image/png"
        raw = base64.b64decode(encoded)
        guessed_ext = mimetypes.guess_extension(mime_type) or ".png"
        safe_name = filename or f"input{guessed_ext}"
        files = {"image": (safe_name, io.BytesIO(raw), mime_type)}
        data = {"overwrite": "true", "type": "input"}
        try:
            response = requests.post(
                self._url("/upload/image"),
                files=files,
                data=data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ApiError(f"ComfyUI image upload failed: {exc}", status_code=502)
        except ValueError as exc:
            raise ApiError(f"Invalid JSON from ComfyUI: {exc}", status_code=502)
        return payload

    def view_url(self, filename: str, subfolder: str = "", image_type: str = "output") -> str:
        if not filename:
            raise ValidationError("filename is required")
        query = urlencode({"filename": filename, "subfolder": subfolder or "", "type": image_type or "output"})
        return self._url(f"/view?{query}")

    def view_image(self, filename: str, subfolder: str = "", image_type: str = "output") -> Dict[str, Any]:
        try:
            response = requests.get(self.view_url(filename, subfolder, image_type), timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ApiError(f"ComfyUI image proxy failed: {exc}", status_code=502)
        return {
            "bytes": response.content,
            "mimetype": response.headers.get("content-type") or "image/png",
        }


_comfyui_service: Optional[ComfyUIService] = None


def get_comfyui_service() -> ComfyUIService:
    global _comfyui_service
    if _comfyui_service is None:
        _comfyui_service = ComfyUIService()
    return _comfyui_service
```

- [ ] **Step 4: Run the adapter tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_service -v
```

Expected: PASS for all 6 tests.

- [ ] **Step 5: Commit the ComfyUI adapter**

Run:

```bash
git add src/services/comfyui_service.py tests/test_comfyui_service.py
git commit -m "feat: add comfyui api adapter"
```

### Task 3: Managed Local Runtime Service

**Files:**
- Create: `src/services/comfyui_runtime_service.py`
- Create: `tests/test_comfyui_runtime_service.py`

- [ ] **Step 1: Write failing runtime tests**

Create `tests/test_comfyui_runtime_service.py`:

```python
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
```

- [ ] **Step 2: Run runtime tests to verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_runtime_service -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.services.comfyui_runtime_service'`.

- [ ] **Step 3: Implement the runtime service without running downloads**

Create `src/services/comfyui_runtime_service.py`:

```python
"""Managed local ComfyUI runtime state and command construction."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from ..config import get_config
from ..utils.errors import ServiceError


COMFYUI_REPO = "https://github.com/comfyanonymous/ComfyUI.git"
GRSAI_REPO = "https://github.com/31702160136/ComfyUI-GrsAI.git"


class ComfyUIRuntimeService:
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        config = get_config()
        self.data_dir = Path(os.getenv("DATA_DIR", config.data_dir))
        self.runtime_dir = self.data_dir / "comfyui" / "runtime"
        self.host = host
        self.port = int(port)

    @property
    def python_bin(self) -> Path:
        return self.runtime_dir / ".venv" / "bin" / "python"

    @property
    def grsai_dir(self) -> Path:
        return self.runtime_dir / "custom_nodes" / "ComfyUI-GrsAI"

    def status(self) -> Dict[str, object]:
        main_py = self.runtime_dir / "main.py"
        installed = main_py.exists()
        grsai_installed = self.grsai_dir.exists()
        state = "installed" if installed else "missing"
        return {
            "state": state,
            "installed": installed,
            "grsaiInstalled": grsai_installed,
            "runtimeDir": str(self.runtime_dir),
            "baseUrl": f"http://{self.host}:{self.port}",
        }

    def install_commands(self) -> List[List[str]]:
        return [
            ["git", "clone", COMFYUI_REPO, str(self.runtime_dir)],
            ["python3", "-m", "venv", str(self.runtime_dir / ".venv")],
            [str(self.python_bin), "-m", "pip", "install", "-r", str(self.runtime_dir / "requirements.txt")],
            ["git", "clone", GRSAI_REPO, str(self.grsai_dir)],
            [str(self.python_bin), "-m", "pip", "install", "-r", str(self.grsai_dir / "requirements.txt")],
        ]

    def start_command(self) -> List[str]:
        python_bin = self.python_bin if self.python_bin.exists() else Path("python3")
        return [
            str(python_bin),
            str(self.runtime_dir / "main.py"),
            "--listen",
            self.host,
            "--port",
            str(self.port),
        ]

    def run_install(self) -> Dict[str, object]:
        self.runtime_dir.parent.mkdir(parents=True, exist_ok=True)
        for command in self.install_commands():
            try:
                subprocess.run(command, check=True, cwd=str(self.runtime_dir.parent))
            except subprocess.CalledProcessError as exc:
                raise ServiceError(f"ComfyUI install failed: {' '.join(command)}") from exc
        return self.status()

    def start(self) -> Dict[str, object]:
        if not (self.runtime_dir / "main.py").exists():
            raise ServiceError("ComfyUI runtime is not installed")
        subprocess.Popen(
            self.start_command(),
            cwd=str(self.runtime_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"started": True, "baseUrl": f"http://{self.host}:{self.port}"}


_runtime_service: Optional[ComfyUIRuntimeService] = None


def get_comfyui_runtime_service() -> ComfyUIRuntimeService:
    global _runtime_service
    if _runtime_service is None:
        _runtime_service = ComfyUIRuntimeService()
    return _runtime_service
```

- [ ] **Step 4: Run runtime tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_runtime_service -v
```

Expected: PASS for all 4 tests.

- [ ] **Step 5: Commit the runtime service**

Run:

```bash
git add src/services/comfyui_runtime_service.py tests/test_comfyui_runtime_service.py
git commit -m "feat: add managed comfyui runtime service"
```

### Task 4: Flask ComfyUI Routes

**Files:**
- Create: `src/routes/comfyui_routes.py`
- Create: `tests/test_comfyui_routes.py`
- Modify: `app.py`

- [ ] **Step 1: Write failing route tests**

Create `tests/test_comfyui_routes.py`:

```python
import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def build_test_client():
    tmpdir = tempfile.TemporaryDirectory()
    data_dir = Path(tmpdir.name) / "data"
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["DB_PATH"] = str(data_dir / "app.db")
    os.environ["APP_SECRET_KEY"] = "test-secret"

    import src.config as config_module
    import src.services.auth as auth_module
    import src.services.database as database_module

    config_module._config_instance = None
    auth_module._auth_service = None
    database_module.db_manager = None

    import app as app_module

    app_module = importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return tmpdir, app_module.app.test_client()


class ComfyUIRoutesTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in ("DATA_DIR", "DB_PATH", "APP_SECRET_KEY")
        }
        self.tmpdir, self.client = build_test_client()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    @patch("src.routes.comfyui_routes.get_comfyui_runtime_service")
    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_status_combines_runtime_and_connection(self, service_factory, runtime_factory):
        service = MagicMock()
        service.status.return_value = {"connected": True, "baseUrl": "http://127.0.0.1:8188"}
        service_factory.return_value = service
        runtime = MagicMock()
        runtime.status.return_value = {"state": "installed", "installed": True}
        runtime_factory.return_value = runtime

        response = self.client.get("/api/comfyui/status")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["connection"]["connected"])
        self.assertEqual(payload["runtime"]["state"], "installed")

    @patch("src.routes.comfyui_routes.normalize_workflow")
    def test_workflow_import_returns_canvas_model(self, normalize_mock):
        normalize_mock.return_value = {"nodes": [{"id": "1"}], "links": [], "nodeCount": 1, "linkCount": 0}

        response = self.client.post("/api/comfyui/workflows/import", json={"workflow": {"1": {"class_type": "PreviewImage", "inputs": {}}}})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["nodeCount"], 1)

    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_prompt_route_submits_workflow(self, service_factory):
        service = MagicMock()
        service.submit_prompt.return_value = {"prompt_id": "abc", "number": 1}
        service_factory.return_value = service

        response = self.client.post("/api/comfyui/prompt", json={"workflow": {"1": {"class_type": "PreviewImage", "inputs": {}}}, "clientId": "client-1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["prompt_id"], "abc")
        service.submit_prompt.assert_called_once()

    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_history_route_normalizes_result(self, service_factory):
        service = MagicMock()
        service.history.return_value = {"abc": {"outputs": {"9": {"images": [{"filename": "out.png", "type": "output"}]}}}}
        service.normalize_history.return_value = {"id": "abc", "status": "succeeded", "results": [{"filename": "out.png"}]}
        service_factory.return_value = service

        response = self.client.get("/api/comfyui/history/abc")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run route tests to verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_routes -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.routes.comfyui_routes'` or Flask 404.

- [ ] **Step 3: Implement route blueprint**

Create `src/routes/comfyui_routes.py`:

```python
"""ComfyUI workbench API routes."""

from __future__ import annotations

import io
from typing import Any

from flask import Blueprint, jsonify, request, send_file

from ..services.comfyui_runtime_service import get_comfyui_runtime_service
from ..services.comfyui_service import get_comfyui_service
from ..services.comfyui_workflow_service import normalize_workflow
from .decorators import api_login_required, handle_api_errors

comfyui_bp = Blueprint("comfyui", __name__, url_prefix="/api/comfyui")


@comfyui_bp.get("/status")
@api_login_required
@handle_api_errors
def status() -> Any:
    service = get_comfyui_service()
    runtime = get_comfyui_runtime_service()
    return jsonify({"connection": service.status(), "runtime": runtime.status()})


@comfyui_bp.get("/object-info")
@api_login_required
@handle_api_errors
def object_info() -> Any:
    return jsonify(get_comfyui_service().object_info())


@comfyui_bp.post("/workflows/import")
@api_login_required
@handle_api_errors
def import_workflow() -> Any:
    data = request.get_json(force=True, silent=True) or {}
    workflow = data.get("workflow") or data
    return jsonify(normalize_workflow(workflow))


@comfyui_bp.post("/upload-image")
@api_login_required
@handle_api_errors
def upload_image() -> Any:
    data = request.get_json(force=True, silent=True) or {}
    image = data.get("image") or ""
    filename = data.get("filename") or "input.png"
    return jsonify(get_comfyui_service().upload_data_url(image, filename))


@comfyui_bp.post("/prompt")
@api_login_required
@handle_api_errors
def prompt() -> Any:
    data = request.get_json(force=True, silent=True) or {}
    workflow = data.get("workflow") or {}
    client_id = data.get("clientId") or data.get("client_id") or "matchdrawer"
    return jsonify(get_comfyui_service().submit_prompt(workflow, client_id))


@comfyui_bp.get("/history/<prompt_id>")
@api_login_required
@handle_api_errors
def history(prompt_id: str) -> Any:
    service = get_comfyui_service()
    raw = service.history(prompt_id)
    return jsonify(service.normalize_history(prompt_id, raw))


@comfyui_bp.get("/view")
@api_login_required
@handle_api_errors
def view() -> Any:
    filename = request.args.get("filename") or ""
    subfolder = request.args.get("subfolder") or ""
    image_type = request.args.get("type") or "output"
    payload = get_comfyui_service().view_image(filename, subfolder, image_type)
    return send_file(
        io.BytesIO(payload["bytes"]),
        mimetype=payload["mimetype"],
        conditional=True,
        max_age=0,
    )


@comfyui_bp.post("/runtime/install")
@api_login_required
@handle_api_errors
def runtime_install() -> Any:
    return jsonify(get_comfyui_runtime_service().run_install())


@comfyui_bp.post("/runtime/start")
@api_login_required
@handle_api_errors
def runtime_start() -> Any:
    return jsonify(get_comfyui_runtime_service().start())
```

Modify `app.py` imports and blueprint registration:

```python
from src.routes.comfyui_routes import comfyui_bp
```

Register it after `api_bp`:

```python
app.register_blueprint(comfyui_bp)
```

- [ ] **Step 4: Run route tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_routes -v
```

Expected: PASS for all 4 tests.

- [ ] **Step 5: Commit routes**

Run:

```bash
git add app.py src/routes/comfyui_routes.py tests/test_comfyui_routes.py
git commit -m "feat: add comfyui workbench routes"
```

### Task 5: Page Shell And Static Assets

**Files:**
- Create: `static/js/comfyui-workbench.js`
- Create: `static/css/comfyui-workbench.css`
- Create: `tests/test_comfyui_workbench_assets.py`
- Modify: `templates/index.html`
- Modify: `static/js/app.js`

- [ ] **Step 1: Write failing asset tests**

Create `tests/test_comfyui_workbench_assets.py`:

```python
import unittest
from pathlib import Path


class ComfyUIWorkbenchAssetsTest(unittest.TestCase):
    def test_sidebar_and_page_shell_exist(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")

        self.assertIn('data-page="comfyui-workbench"', html)
        self.assertIn("生图工作台", html)
        self.assertIn('id="page-comfyui-workbench"', html)
        self.assertIn("js/comfyui-workbench.js", html)
        self.assertIn("css/comfyui-workbench.css", html)

    def test_app_registers_page_config_and_i18n(self):
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")

        self.assertIn("'nav.comfyui_workbench': '生图工作台'", app_js)
        self.assertIn("'page.comfyui_workbench': '生图工作台'", app_js)
        self.assertIn("'comfyui-workbench':", app_js)
        self.assertIn("ComfyUIWorkbench.init", app_js)

    def test_workbench_js_uses_backend_routes_only(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("window.ComfyUIWorkbench", workbench_js)
        self.assertIn("/api/comfyui/status", workbench_js)
        self.assertIn("/api/comfyui/prompt", workbench_js)
        self.assertNotIn("127.0.0.1:8188", workbench_js)
        self.assertNotIn("localhost:8188", workbench_js)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run asset tests to verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workbench_assets -v
```

Expected: FAIL because the new page assets do not exist.

- [ ] **Step 3: Add template shell**

Modify `templates/index.html`:

Add a sidebar item after 图像生成:

```html
<a href="#" class="nav-item" data-page="comfyui-workbench">
    <i class="fas fa-project-diagram nav-icon"></i>
    <span class="nav-label" data-i18n="nav.comfyui_workbench">生图工作台</span>
</a>
```

Add stylesheet in `<head>` after the main app styles:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/comfyui-workbench.css') }}">
```

Add the page section before `page-gpt-image`:

```html
<div class="page-section" id="page-comfyui-workbench">
    <div class="comfy-workbench" id="comfyWorkbenchRoot">
        <aside class="comfy-node-library">
            <div class="comfy-panel-title">节点库</div>
            <button type="button" class="comfy-node-template" data-template="grsai-text-image">GrsAI Text/Image</button>
            <button type="button" class="comfy-node-template" data-template="grsai-fusion">Multi Image Fusion</button>
            <button type="button" class="comfy-node-template" data-template="grsai-batch">Batch Generate</button>
        </aside>
        <section class="comfy-main">
            <div class="comfy-toolbar">
                <div>
                    <div class="workbench-eyebrow">ComfyUI</div>
                    <h3 class="content-card-title">生图工作台</h3>
                </div>
                <div class="comfy-toolbar-actions">
                    <span class="comfy-status" id="comfyConnectionStatus">未连接</span>
                    <button type="button" class="btn btn-outline btn-sm" id="comfyImportBtn">导入 Workflow</button>
                    <input type="file" id="comfyImportInput" accept="application/json" hidden>
                    <button type="button" class="btn btn-outline btn-sm" id="comfyInstallBtn">安装 ComfyUI</button>
                    <button type="button" class="btn btn-outline btn-sm" id="comfyStartBtn">启动</button>
                    <button type="button" class="btn btn-primary btn-sm" id="comfyRunBtn">运行</button>
                </div>
            </div>
            <div class="comfy-canvas-shell">
                <svg class="comfy-link-layer" id="comfyLinkLayer" aria-hidden="true"></svg>
                <div class="comfy-canvas" id="comfyCanvas"></div>
                <div class="comfy-empty-state" id="comfyEmptyState">导入 ComfyUI API workflow JSON 后开始编辑</div>
            </div>
            <div class="comfy-run-panel">
                <div class="comfy-log" id="comfyRunLog">等待运行</div>
                <div class="comfy-results" id="comfyResults"></div>
            </div>
        </section>
        <aside class="comfy-property-panel">
            <div class="comfy-panel-title">属性面板</div>
            <div id="comfyPropertyPanel" class="comfy-property-empty">选择一个节点</div>
        </aside>
    </div>
</div>
```

Add the script include before `app.js` or after `api-service.js` and before the closing body:

```html
<script src="{{ url_for('static', filename='js/comfyui-workbench.js') }}"></script>
```

- [ ] **Step 4: Add page config and initialization**

Modify `static/js/app.js`:

Add i18n entries in both language tables:

```javascript
'nav.comfyui_workbench': '生图工作台',
'page.comfyui_workbench': '生图工作台',
```

```javascript
'nav.comfyui_workbench': 'Image Workbench',
'page.comfyui_workbench': 'Image Workbench',
```

Add page config:

```javascript
'comfyui-workbench': {
    titleKey: 'page.comfyui_workbench'
},
```

Add show-page handling:

```javascript
case 'comfyui-workbench':
    if (window.ComfyUIWorkbench && window.ComfyUIWorkbench.init) {
        window.ComfyUIWorkbench.init();
    }
    break;
```

- [ ] **Step 5: Add placeholder JS and CSS**

Create `static/js/comfyui-workbench.js`:

```javascript
(function () {
    'use strict';

    const State = {
        initialized: false,
        workflow: null,
        nodes: [],
        links: [],
        selectedNodeId: null,
        promptId: null,
        pollTimer: null,
    };

    const API = {
        status: '/api/comfyui/status',
        importWorkflow: '/api/comfyui/workflows/import',
        prompt: '/api/comfyui/prompt',
        history: (id) => `/api/comfyui/history/${encodeURIComponent(id)}`,
        uploadImage: '/api/comfyui/upload-image',
        runtimeInstall: '/api/comfyui/runtime/install',
        runtimeStart: '/api/comfyui/runtime/start',
        view: (image) => `/api/comfyui/view?filename=${encodeURIComponent(image.filename)}&subfolder=${encodeURIComponent(image.subfolder || '')}&type=${encodeURIComponent(image.type || 'output')}`,
    };

    const DOM = {};

    function cacheDom() {
        DOM.root = document.getElementById('comfyWorkbenchRoot');
        DOM.status = document.getElementById('comfyConnectionStatus');
        DOM.importBtn = document.getElementById('comfyImportBtn');
        DOM.importInput = document.getElementById('comfyImportInput');
        DOM.installBtn = document.getElementById('comfyInstallBtn');
        DOM.startBtn = document.getElementById('comfyStartBtn');
        DOM.runBtn = document.getElementById('comfyRunBtn');
        DOM.canvas = document.getElementById('comfyCanvas');
        DOM.links = document.getElementById('comfyLinkLayer');
        DOM.empty = document.getElementById('comfyEmptyState');
        DOM.panel = document.getElementById('comfyPropertyPanel');
        DOM.log = document.getElementById('comfyRunLog');
        DOM.results = document.getElementById('comfyResults');
    }

    async function requestJson(url, options = {}) {
        const response = await fetch(url, {
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            ...options,
        });
        if (!response.ok) {
            throw new Error(await response.text());
        }
        return response.json();
    }

    async function refreshStatus() {
        try {
            const payload = await requestJson(API.status);
            const connected = payload.connection && payload.connection.connected;
            if (DOM.status) {
                DOM.status.textContent = connected ? '已连接' : '未连接';
                DOM.status.classList.toggle('is-connected', !!connected);
            }
        } catch (error) {
            if (DOM.status) DOM.status.textContent = '连接失败';
        }
    }

    function init() {
        cacheDom();
        if (!DOM.root || State.initialized) return;
        State.initialized = true;
        if (DOM.importBtn && DOM.importInput) {
            DOM.importBtn.addEventListener('click', () => DOM.importInput.click());
        }
        refreshStatus();
    }

    window.ComfyUIWorkbench = {
        init,
        _state: State,
        _api: API,
    };
})();
```

Create `static/css/comfyui-workbench.css`:

```css
.comfy-workbench {
  display: grid;
  grid-template-columns: 13rem minmax(0, 1fr) 19rem;
  height: calc(100vh - 7rem);
  min-height: 42rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}

.comfy-node-library,
.comfy-property-panel {
  padding: var(--space-4);
  background: var(--color-bg-surface-subtle);
  overflow: auto;
}

.comfy-main {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) 8.5rem;
  min-width: 0;
  border-left: 1px solid var(--color-border);
  border-right: 1px solid var(--color-border);
}

.comfy-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.comfy-toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.comfy-status {
  font-size: var(--font-size-xs);
  padding: 0.35rem 0.6rem;
  border-radius: var(--radius-full);
  background: var(--color-bg-surface-subtle);
  color: var(--color-text-secondary);
}

.comfy-status.is-connected {
  color: var(--color-success);
}

.comfy-canvas-shell {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(90deg, rgba(148, 163, 184, 0.18) 1px, transparent 1px),
    linear-gradient(0deg, rgba(148, 163, 184, 0.18) 1px, transparent 1px);
  background-size: 24px 24px;
}

.comfy-canvas,
.comfy-link-layer {
  position: absolute;
  inset: 0;
}

.comfy-empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.comfy-run-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 17rem;
  border-top: 1px solid var(--color-border);
}

.comfy-log,
.comfy-results {
  padding: var(--space-3);
  overflow: auto;
}

.comfy-node-template {
  width: 100%;
  margin-bottom: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  text-align: left;
}

.comfy-panel-title {
  margin-bottom: var(--space-3);
  font-weight: var(--font-weight-semibold);
}
```

- [ ] **Step 6: Run asset tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workbench_assets -v
```

Expected: PASS for all 3 tests.

- [ ] **Step 7: Commit page shell**

Run:

```bash
git add templates/index.html static/js/app.js static/js/comfyui-workbench.js static/css/comfyui-workbench.css tests/test_comfyui_workbench_assets.py
git commit -m "feat: add comfyui workbench page shell"
```

### Task 6: Workflow Import And Canvas Rendering

**Files:**
- Modify: `static/js/comfyui-workbench.js`
- Modify: `static/css/comfyui-workbench.css`
- Modify: `tests/test_comfyui_workbench_assets.py`

- [ ] **Step 1: Extend frontend asset tests**

Append to `tests/test_comfyui_workbench_assets.py`:

```python
    def test_workbench_js_contains_import_render_and_selection_paths(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("async function importWorkflowFile", workbench_js)
        self.assertIn("function renderCanvas", workbench_js)
        self.assertIn("function renderLinks", workbench_js)
        self.assertIn("function selectNode", workbench_js)
        self.assertIn("comfy-node-card", workbench_js)
```

- [ ] **Step 2: Run frontend asset tests to verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workbench_assets -v
```

Expected: FAIL because import and render functions are not present.

- [ ] **Step 3: Implement import and render functions**

Add these functions to `static/js/comfyui-workbench.js` before `init()`:

```javascript
    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    async function importWorkflowFile(file) {
        const text = await file.text();
        const workflow = JSON.parse(text);
        const payload = await requestJson(API.importWorkflow, {
            method: 'POST',
            body: JSON.stringify({ workflow }),
        });
        State.workflow = payload.workflow || workflow;
        State.nodes = payload.nodes || [];
        State.links = payload.links || [];
        State.selectedNodeId = null;
        renderCanvas();
        renderPropertyPanel();
        if (DOM.log) DOM.log.textContent = `已导入 ${payload.nodeCount || State.nodes.length} 个节点`;
    }

    function renderCanvas() {
        if (!DOM.canvas) return;
        if (DOM.empty) DOM.empty.style.display = State.nodes.length ? 'none' : 'flex';
        DOM.canvas.innerHTML = State.nodes.map((node) => {
            const pos = node.position || { x: 120, y: 120 };
            const selected = node.id === State.selectedNodeId ? ' is-selected' : '';
            return `
                <button type="button"
                        class="comfy-node-card comfy-node-${escapeHtml(node.kind)}${selected}"
                        data-node-id="${escapeHtml(node.id)}"
                        style="left:${Number(pos.x) || 0}px;top:${Number(pos.y) || 0}px">
                    <span class="comfy-node-title">${escapeHtml(node.title || node.classType)}</span>
                    <span class="comfy-node-meta">#${escapeHtml(node.id)} · ${escapeHtml(node.classType)}</span>
                </button>
            `;
        }).join('');
        DOM.canvas.querySelectorAll('[data-node-id]').forEach((el) => {
            el.addEventListener('click', () => selectNode(el.getAttribute('data-node-id')));
        });
        renderLinks();
    }

    function renderLinks() {
        if (!DOM.links) return;
        DOM.links.innerHTML = State.links.map((link, index) => {
            const fromIndex = State.nodes.findIndex((node) => node.id === link.fromNode);
            const toIndex = State.nodes.findIndex((node) => node.id === link.toNode);
            if (fromIndex < 0 || toIndex < 0) return '';
            const from = State.nodes[fromIndex].position || { x: 120, y: 120 };
            const to = State.nodes[toIndex].position || { x: 120, y: 120 };
            const x1 = (Number(from.x) || 0) + 170;
            const y1 = (Number(from.y) || 0) + 34;
            const x2 = Number(to.x) || 0;
            const y2 = (Number(to.y) || 0) + 34;
            const cx = Math.max(40, Math.abs(x2 - x1) / 2);
            return `<path class="comfy-link-path" data-link-index="${index}" d="M ${x1} ${y1} C ${x1 + cx} ${y1}, ${x2 - cx} ${y2}, ${x2} ${y2}" />`;
        }).join('');
    }

    function selectNode(nodeId) {
        State.selectedNodeId = nodeId;
        renderCanvas();
        renderPropertyPanel();
    }

    function selectedNode() {
        return State.nodes.find((node) => node.id === State.selectedNodeId) || null;
    }

    function renderPropertyPanel() {
        if (!DOM.panel) return;
        const node = selectedNode();
        if (!node) {
            DOM.panel.innerHTML = '<div class="comfy-property-empty">选择一个节点</div>';
            return;
        }
        DOM.panel.innerHTML = `
            <div class="comfy-property-node-title">${escapeHtml(node.title || node.classType)}</div>
            <div class="comfy-property-node-meta">#${escapeHtml(node.id)} · ${escapeHtml(node.kind)}</div>
            <pre class="comfy-json-preview">${escapeHtml(JSON.stringify(node.inputs || {}, null, 2))}</pre>
        `;
    }
```

Update the import input event in `init()`:

```javascript
        if (DOM.importInput) {
            DOM.importInput.addEventListener('change', (event) => {
                const file = event.target.files && event.target.files[0];
                if (file) {
                    importWorkflowFile(file).catch((error) => {
                        if (DOM.log) DOM.log.textContent = `导入失败: ${error.message}`;
                    });
                }
                DOM.importInput.value = '';
            });
        }
```

Add CSS:

```css
.comfy-node-card {
  position: absolute;
  width: 11rem;
  min-height: 4.25rem;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  text-align: left;
  box-shadow: var(--shadow-sm);
}

.comfy-node-card.is-selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(45, 127, 249, 0.18);
}

.comfy-node-title,
.comfy-node-meta {
  display: block;
}

.comfy-node-title {
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-1);
}

.comfy-node-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.comfy-link-path {
  fill: none;
  stroke: var(--color-primary);
  stroke-width: 2.5;
}

.comfy-json-preview {
  margin-top: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg-subtle);
  color: var(--color-text-secondary);
  overflow: auto;
  font-size: var(--font-size-xs);
}
```

- [ ] **Step 4: Run frontend asset tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workbench_assets -v
```

Expected: PASS for all tests.

- [ ] **Step 5: Commit import and rendering**

Run:

```bash
git add static/js/comfyui-workbench.js static/css/comfyui-workbench.css tests/test_comfyui_workbench_assets.py
git commit -m "feat: render imported comfyui workflows"
```

### Task 7: GrsAI Property Editing And Workflow Submission

**Files:**
- Modify: `static/js/comfyui-workbench.js`
- Modify: `static/css/comfyui-workbench.css`
- Modify: `tests/test_comfyui_workbench_assets.py`

- [ ] **Step 1: Extend asset tests for editing and run loop**

Append to `tests/test_comfyui_workbench_assets.py`:

```python
    def test_workbench_js_contains_grsai_editing_and_run_loop(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("function renderKnownGrsaiInputs", workbench_js)
        self.assertIn("function updateSelectedNodeInput", workbench_js)
        self.assertIn("async function runWorkflow", workbench_js)
        self.assertIn("function pollHistory", workbench_js)
        self.assertIn("renderResults", workbench_js)
```

- [ ] **Step 2: Run asset tests to verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workbench_assets -v
```

Expected: FAIL because editing and run-loop functions are not present.

- [ ] **Step 3: Add known GrsAI input rendering**

Add to `static/js/comfyui-workbench.js` after `selectedNode()`:

```javascript
    const KNOWN_INPUTS = [
        { key: 'prompt', label: 'prompt', type: 'textarea' },
        { key: 'negative_prompt', label: 'negative prompt', type: 'textarea' },
        { key: 'model', label: 'model', type: 'text' },
        { key: 'aspectRatio', label: 'aspectRatio', type: 'select', options: ['auto', '1:1', '16:9', '9:16', '4:3', '3:4', '3:2', '2:3', '5:4', '4:5', '21:9'] },
        { key: 'imageSize', label: 'imageSize', type: 'select', options: ['1K', '2K', '4K'] },
        { key: 'seed', label: 'seed', type: 'number' },
        { key: 'steps', label: 'steps', type: 'number' },
        { key: 'cfg', label: 'cfg', type: 'number' },
        { key: 'batch_size', label: 'batch size', type: 'number' },
    ];

    function renderKnownGrsaiInputs(node) {
        const inputs = node.inputs || {};
        return KNOWN_INPUTS
            .filter((field) => Object.prototype.hasOwnProperty.call(inputs, field.key))
            .map((field) => {
                const value = inputs[field.key];
                if (Array.isArray(value)) return '';
                if (field.type === 'textarea') {
                    return `
                        <label class="comfy-field">
                            <span>${escapeHtml(field.label)}</span>
                            <textarea data-comfy-input="${escapeHtml(field.key)}">${escapeHtml(value)}</textarea>
                        </label>
                    `;
                }
                if (field.type === 'select') {
                    const options = field.options.map((option) => {
                        const selected = String(option) === String(value) ? ' selected' : '';
                        return `<option value="${escapeHtml(option)}"${selected}>${escapeHtml(option)}</option>`;
                    }).join('');
                    return `
                        <label class="comfy-field">
                            <span>${escapeHtml(field.label)}</span>
                            <select data-comfy-input="${escapeHtml(field.key)}">${options}</select>
                        </label>
                    `;
                }
                return `
                    <label class="comfy-field">
                        <span>${escapeHtml(field.label)}</span>
                        <input data-comfy-input="${escapeHtml(field.key)}" type="${field.type}" value="${escapeHtml(value)}">
                    </label>
                `;
            })
            .join('') || '<div class="comfy-property-empty">这个节点没有首版可编辑字段</div>';
    }

    function updateSelectedNodeInput(key, value) {
        const node = selectedNode();
        if (!node || !State.workflow || !State.workflow[node.id]) return;
        const nextValue = value === '' ? '' : value;
        node.inputs[key] = nextValue;
        State.workflow[node.id].inputs = State.workflow[node.id].inputs || {};
        State.workflow[node.id].inputs[key] = nextValue;
    }
```

Replace the selected-node branch in `renderPropertyPanel()` with:

```javascript
        const editor = node.kind === 'grsai' ? renderKnownGrsaiInputs(node) : '';
        DOM.panel.innerHTML = `
            <div class="comfy-property-node-title">${escapeHtml(node.title || node.classType)}</div>
            <div class="comfy-property-node-meta">#${escapeHtml(node.id)} · ${escapeHtml(node.kind)}</div>
            ${editor}
            <pre class="comfy-json-preview">${escapeHtml(JSON.stringify(node.inputs || {}, null, 2))}</pre>
        `;
        DOM.panel.querySelectorAll('[data-comfy-input]').forEach((input) => {
            input.addEventListener('input', () => updateSelectedNodeInput(input.getAttribute('data-comfy-input'), input.value));
        });
```

- [ ] **Step 4: Add run and polling functions**

Add before `init()`:

```javascript
    async function runWorkflow() {
        if (!State.workflow) {
            if (DOM.log) DOM.log.textContent = '请先导入 workflow';
            return;
        }
        if (DOM.runBtn) DOM.runBtn.disabled = true;
        try {
            const result = await requestJson(API.prompt, {
                method: 'POST',
                body: JSON.stringify({ workflow: State.workflow, clientId: 'matchdrawer-web' }),
            });
            State.promptId = result.prompt_id || result.promptId;
            if (DOM.log) DOM.log.textContent = `已提交: ${State.promptId || 'unknown'}`;
            if (State.promptId) pollHistory(State.promptId);
        } catch (error) {
            if (DOM.log) DOM.log.textContent = `运行失败: ${error.message}`;
            if (DOM.runBtn) DOM.runBtn.disabled = false;
        }
    }

    async function pollHistory(promptId) {
        window.clearTimeout(State.pollTimer);
        try {
            const payload = await requestJson(API.history(promptId));
            if (payload.status === 'succeeded') {
                if (DOM.log) DOM.log.textContent = `完成: ${promptId}`;
                renderResults(payload.results || []);
                if (DOM.runBtn) DOM.runBtn.disabled = false;
                return;
            }
            if (DOM.log) DOM.log.textContent = `运行中: ${promptId}`;
            State.pollTimer = window.setTimeout(() => pollHistory(promptId), 2500);
        } catch (error) {
            if (DOM.log) DOM.log.textContent = `查询失败: ${error.message}`;
            if (DOM.runBtn) DOM.runBtn.disabled = false;
        }
    }

    function renderResults(results) {
        if (!DOM.results) return;
        DOM.results.innerHTML = results.map((image) => `
            <a class="comfy-result-thumb" href="${escapeHtml(API.view(image))}" target="_blank" rel="noopener">
                <img src="${escapeHtml(API.view(image))}" alt="ComfyUI output">
            </a>
        `).join('') || '<div class="comfy-property-empty">暂无结果</div>';
    }
```

Add in `init()`:

```javascript
        if (DOM.runBtn) {
            DOM.runBtn.addEventListener('click', () => runWorkflow());
        }
```

Add CSS:

```css
.comfy-field {
  display: grid;
  gap: var(--space-1);
  margin-top: var(--space-3);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.comfy-field input,
.comfy-field select,
.comfy-field textarea {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  padding: 0.55rem 0.65rem;
}

.comfy-field textarea {
  min-height: 5rem;
  resize: vertical;
}

.comfy-results {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}

.comfy-result-thumb img {
  display: block;
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}
```

- [ ] **Step 5: Run frontend asset tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workbench_assets -v
```

Expected: PASS for all tests.

- [ ] **Step 6: Commit editing and run loop**

Run:

```bash
git add static/js/comfyui-workbench.js static/css/comfyui-workbench.css tests/test_comfyui_workbench_assets.py
git commit -m "feat: edit and run comfyui workflows"
```

### Task 8: Runtime UI Actions And Starter Workflow

**Files:**
- Create: `integrations/comfyui_grsai/workflows/text_image_api.json`
- Modify: `static/js/comfyui-workbench.js`
- Modify: `tests/test_comfyui_workbench_assets.py`

- [ ] **Step 1: Extend tests for runtime actions and starter workflow**

Append to `tests/test_comfyui_workbench_assets.py`:

```python
    def test_runtime_actions_and_starter_workflow_are_present(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")
        starter = Path("integrations/comfyui_grsai/workflows/text_image_api.json")

        self.assertIn("async function installRuntime", workbench_js)
        self.assertIn("async function startRuntime", workbench_js)
        self.assertTrue(starter.exists())
        content = starter.read_text(encoding="utf-8")
        self.assertIn("GrsAI", content)
        self.assertIn("class_type", content)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workbench_assets -v
```

Expected: FAIL because runtime action functions and starter workflow are missing.

- [ ] **Step 3: Add starter workflow**

Create `integrations/comfyui_grsai/workflows/text_image_api.json`:

```json
{
  "1": {
    "class_type": "GrsAINanoBananaTextImage",
    "inputs": {
      "prompt": "a clean scientific product-style image on a white background",
      "model": "nano-banana-pro",
      "aspectRatio": "1:1",
      "imageSize": "1K"
    },
    "_meta": {
      "title": "GrsAI Nano Banana Text/Image"
    }
  },
  "2": {
    "class_type": "PreviewImage",
    "inputs": {
      "images": ["1", 0]
    },
    "_meta": {
      "title": "Preview Image"
    }
  }
}
```

- [ ] **Step 4: Add runtime UI actions**

Add before `runWorkflow()` in `static/js/comfyui-workbench.js`:

```javascript
    async function installRuntime() {
        if (DOM.log) DOM.log.textContent = '开始安装 ComfyUI，本步骤会下载 ComfyUI 和 ComfyUI-GrsAI';
        try {
            const result = await requestJson(API.runtimeInstall, { method: 'POST', body: '{}' });
            if (DOM.log) DOM.log.textContent = `安装状态: ${result.state || '完成'}`;
            await refreshStatus();
        } catch (error) {
            if (DOM.log) DOM.log.textContent = `安装失败: ${error.message}`;
        }
    }

    async function startRuntime() {
        if (DOM.log) DOM.log.textContent = '正在启动 ComfyUI';
        try {
            const result = await requestJson(API.runtimeStart, { method: 'POST', body: '{}' });
            if (DOM.log) DOM.log.textContent = `启动请求已发送: ${result.baseUrl || ''}`;
            window.setTimeout(refreshStatus, 2500);
        } catch (error) {
            if (DOM.log) DOM.log.textContent = `启动失败: ${error.message}`;
        }
    }
```

Add event listeners in `init()`:

```javascript
        if (DOM.installBtn) {
            DOM.installBtn.addEventListener('click', () => installRuntime());
        }
        if (DOM.startBtn) {
            DOM.startBtn.addEventListener('click', () => startRuntime());
        }
```

- [ ] **Step 5: Run frontend asset tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_comfyui_workbench_assets -v
```

Expected: PASS for all tests.

- [ ] **Step 6: Commit runtime UI and starter workflow**

Run:

```bash
git add static/js/comfyui-workbench.js tests/test_comfyui_workbench_assets.py integrations/comfyui_grsai/workflows/text_image_api.json
git commit -m "feat: add comfyui runtime actions and starter workflow"
```

### Task 9: Full Regression And Browser Verification

**Files:**
- Modify only files required by failures found in this task.

- [ ] **Step 1: Run all unit tests**

Run:

```bash
.venv/bin/python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 2: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 3: Start the Flask app**

Run:

```bash
.venv/bin/python app.py
```

Expected: server listens on the configured port, usually `8788`.

- [ ] **Step 4: Open the app in the browser**

Open:

```text
http://127.0.0.1:8788
```

Expected:
- Login page loads if not authenticated.
- After login, left sidebar contains **生图工作台**.
- Clicking **生图工作台** shows the workbench shell.
- ComfyUI disconnected state is visible when no runtime is running.

- [ ] **Step 5: Import starter workflow through the UI**

Use the import button and select:

```text
integrations/comfyui_grsai/workflows/text_image_api.json
```

Expected:
- Canvas shows `GrsAI Nano Banana Text/Image` and `Preview Image`.
- Selecting the GrsAI node shows editable `prompt`, `model`, `aspectRatio`, and `imageSize`.
- The JSON preview still includes the original workflow inputs.

- [ ] **Step 6: Verify backend status endpoint manually**

Run:

```bash
curl -sS http://127.0.0.1:8788/api/comfyui/status
```

Expected:
- If unauthenticated, returns the app's auth response.
- If authenticated through browser session only, use browser dev tools or route tests for authenticated confirmation.
- No server traceback appears in Flask logs.

- [ ] **Step 7: Commit any verification fixes**

If any fixes were required, run:

```bash
git add <changed-files>
git commit -m "fix: stabilize comfyui workbench verification"
```

If no fixes were required, do not create an empty commit.

### Task 10: Final Review And Handoff

**Files:**
- No code changes unless final review finds a defect.

- [ ] **Step 1: Check final git state**

Run:

```bash
git status --short
```

Expected:
- Only intentional untracked user files remain.
- No unexpected modifications are present.

- [ ] **Step 2: Review committed changes**

Run:

```bash
git log --oneline -8
```

Expected: recent commits correspond to the plan tasks.

- [ ] **Step 3: Summarize implementation results**

Prepare a concise summary with:
- Files added and modified.
- Tests run and pass/fail status.
- Whether a live ComfyUI run was verified.
- Any remaining manual setup required for installing ComfyUI-GrsAI and adding a GrsAI API key.

- [ ] **Step 4: Offer integration options**

Offer:
- keep on current branch,
- push and open PR,
- continue hardening runtime installer and WebSocket progress.
