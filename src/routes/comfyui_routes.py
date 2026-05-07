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
