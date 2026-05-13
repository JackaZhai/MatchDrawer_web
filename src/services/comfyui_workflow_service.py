"""
ComfyUI workflow normalization helpers.
"""

from copy import deepcopy
from typing import Any, Union

from ..utils.errors import ValidationError


CORE_NODE_TYPES = {"LoadImage", "PreviewImage", "SaveImage"}
GRSAI_MARKERS = ("grsai", "nano banana", "nanobanana", "flux", "gpt image", "gptimage")


def normalize_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    """Normalize a ComfyUI API workflow into nodes and links."""
    _validate_api_workflow(workflow)

    nodes = []
    links = []
    for index, node_id in enumerate(sorted(workflow.keys(), key=_node_sort_key)):
        node = workflow[node_id]
        class_type = _validate_workflow_node(node)

        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            inputs = {}

        nodes.append(
            {
                "id": node_id,
                "classType": class_type,
                "title": _node_title(node, class_type),
                "kind": _node_kind(class_type),
                "inputs": deepcopy(inputs),
                "position": _node_position(node, index),
            }
        )
        links.extend(_extract_links(node_id, inputs))

    return {
        "nodes": nodes,
        "links": links,
        "nodeCount": len(nodes),
        "linkCount": len(links),
        "workflow": deepcopy(workflow),
    }


def apply_input_patch(workflow: dict[str, Any], node_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Patch a node's inputs while preserving all other workflow fields."""
    _validate_api_workflow(workflow)
    if node_id not in workflow:
        raise ValidationError("Workflow node not found")
    if not isinstance(inputs, dict):
        raise ValidationError("Workflow input patch must be a dict")
    _validate_workflow_node(workflow[node_id])

    updated = deepcopy(workflow)
    node_inputs = updated[node_id].setdefault("inputs", {})
    if not isinstance(node_inputs, dict):
        node_inputs = {}
        updated[node_id]["inputs"] = node_inputs
    node_inputs.update(deepcopy(inputs))
    return updated


def _validate_api_workflow(workflow: dict[str, Any]) -> None:
    if not isinstance(workflow, dict) or not workflow:
        raise ValidationError("Expected non-empty ComfyUI API workflow")
    if "nodes" in workflow and "links" in workflow:
        raise ValidationError("Expected ComfyUI API workflow, not UI workflow")


def _validate_workflow_node(node: Any) -> str:
    if not isinstance(node, dict):
        raise ValidationError("Invalid ComfyUI API workflow node")
    class_type = node.get("class_type")
    if not isinstance(class_type, str):
        raise ValidationError("Invalid ComfyUI API workflow node")
    return class_type


def _node_sort_key(node_id: str) -> tuple[int, Union[int, str]]:
    try:
        return (0, int(node_id))
    except (TypeError, ValueError):
        return (1, str(node_id))


def _default_node_position(index: int) -> dict[str, int]:
    return {"x": 120 + index * 220, "y": 120 + (index % 3) * 110}


def _node_position(node: dict[str, Any], index: int) -> dict[str, int]:
    meta = node.get("_meta", {})
    position = meta.get("position") if isinstance(meta, dict) else None
    if isinstance(position, dict):
        x = position.get("x")
        y = position.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return {"x": int(x), "y": int(y)}
    return _default_node_position(index)


def _node_title(node: dict[str, Any], class_type: str) -> str:
    meta = node.get("_meta", {})
    if isinstance(meta, dict) and isinstance(meta.get("title"), str):
        return meta["title"]
    return class_type


def _node_kind(class_type: str) -> str:
    normalized = class_type.replace("_", " ").replace("-", " ").lower()
    compact = class_type.replace("_", "").replace("-", "").lower()
    if any(marker in normalized or marker in compact for marker in GRSAI_MARKERS):
        return "grsai"
    if class_type in CORE_NODE_TYPES:
        return "core"
    return "unknown"


def _extract_links(node_id: str, inputs: dict[str, Any]) -> list[dict[str, Any]]:
    links = []
    for input_name, value in inputs.items():
        if _is_link(value):
            links.append(
                {
                    "fromNode": value[0],
                    "fromOutput": value[1],
                    "toNode": node_id,
                    "toInput": input_name,
                }
            )
    return links


def _is_link(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], int)
    )
