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

    def test_apply_input_patch_rejects_malformed_node(self):
        from src.services.comfyui_workflow_service import apply_input_patch
        from src.utils.errors import ValidationError

        with self.assertRaises(ValidationError):
            apply_input_patch({"1": None}, node_id="1", inputs={"prompt": "x"})


if __name__ == "__main__":
    unittest.main()
