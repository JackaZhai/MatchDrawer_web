"""ComfyUI workbench API routes."""

from __future__ import annotations

import io
import json
import os
from ipaddress import ip_address
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request, send_file

from ..services.comfyui_runtime_service import get_comfyui_runtime_service
from ..services.comfyui_service import get_comfyui_service
from ..services.comfyui_workflow_service import normalize_workflow
from ..utils.errors import ApiError
from .decorators import api_login_required, handle_api_errors


comfyui_bp = Blueprint("comfyui", __name__, url_prefix="/api/comfyui")

RUNTIME_CONFIRM_HEADER = "X-ComfyUI-Runtime-Action"
RUNTIME_CONFIRM_VALUE = "confirm-local-runtime"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STARTER_WORKFLOWS = {
    "text-image": PROJECT_ROOT / "integrations/comfyui_grsai/workflows/text_image_api.json",
    "image-fusion": PROJECT_ROOT / "integrations/comfyui_grsai/workflows/image_fusion_api.json",
    "batch-generate": PROJECT_ROOT / "integrations/comfyui_grsai/workflows/batch_generate_api.json",
}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _require_runtime_action_request() -> None:
    if not _truthy(os.getenv("COMFYUI_RUNTIME_ACTIONS_ENABLED")):
        raise ApiError("ComfyUI runtime actions are disabled", status_code=403)

    remote_addr = request.remote_addr or ""
    try:
        is_loopback = ip_address(remote_addr).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback:
        raise ApiError("ComfyUI runtime actions require a local request", status_code=403)
    if request.headers.get(RUNTIME_CONFIRM_HEADER) != RUNTIME_CONFIRM_VALUE:
        raise ApiError("ComfyUI runtime action confirmation is required", status_code=403)


def _public_connection_status(status: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "connected": bool(status.get("connected")),
        "queue": status.get("queue") or {"running": 0, "pending": 0},
    }
    if status.get("system"):
        payload["system"] = status["system"]
    if not payload["connected"]:
        payload["error"] = "ComfyUI backend is not reachable"
    return payload


def _public_runtime_status(status: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": status.get("state") or "missing",
        "installed": bool(status.get("installed")),
        "grsaiInstalled": bool(status.get("grsaiInstalled")),
    }


def _public_runtime_start(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "started": bool(result.get("started")),
        "alreadyRunning": bool(result.get("alreadyRunning")),
    }


@comfyui_bp.get("/status")
@api_login_required
@handle_api_errors
def status() -> Any:
    service = get_comfyui_service()
    runtime = get_comfyui_runtime_service()
    return jsonify(
        {
            "connection": _public_connection_status(service.status()),
            "runtime": _public_runtime_status(runtime.status()),
        }
    )


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


@comfyui_bp.get("/workflows/starter/<name>")
@api_login_required
@handle_api_errors
def starter_workflow(name: str) -> Any:
    path = STARTER_WORKFLOWS.get(name)
    if path is None:
        raise ApiError("Unknown starter workflow", status_code=404)
    with path.open("r", encoding="utf-8") as file:
        return jsonify({"workflow": json.load(file), "name": name})


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
    _require_runtime_action_request()
    result = get_comfyui_runtime_service().run_install()
    return jsonify(_public_runtime_status(result))


@comfyui_bp.post("/runtime/start")
@api_login_required
@handle_api_errors
def runtime_start() -> Any:
    _require_runtime_action_request()
    result = get_comfyui_runtime_service().start()
    return jsonify(_public_runtime_start(result))
