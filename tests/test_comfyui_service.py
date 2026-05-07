import base64
import unittest
from unittest.mock import Mock, patch


class ComfyUIServiceTest(unittest.TestCase):
    def test_status_reports_disconnected_when_system_stats_fails(self):
        from src.services.comfyui_service import ComfyUIService

        service = ComfyUIService()

        with patch("src.services.comfyui_service.requests.get", side_effect=Exception("connection refused")):
            result = service.status()

        self.assertFalse(result["connected"])
        self.assertEqual(result["baseUrl"], "http://127.0.0.1:8188")
        self.assertIn("connection refused", result["error"])

    def test_status_reads_system_stats_and_queue(self):
        from src.services.comfyui_service import ComfyUIService

        system_response = Mock()
        system_response.json.return_value = {"system": {"python_version": "3.11.8"}}
        queue_response = Mock()
        queue_response.json.return_value = {"queue_running": [], "queue_pending": [{"prompt": "x"}]}

        with patch(
            "src.services.comfyui_service.requests.get",
            side_effect=[system_response, queue_response],
        ):
            result = ComfyUIService().status()

        self.assertTrue(result["connected"])
        self.assertEqual(result["system"]["python_version"], "3.11.8")
        self.assertEqual(result["queue"]["pending"], 1)

    def test_submit_prompt_posts_client_id_and_workflow(self):
        from src.services.comfyui_service import ComfyUIService

        response = Mock()
        response.json.return_value = {"prompt_id": "abc"}
        workflow = {"1": {"class_type": "PreviewImage", "inputs": {}}}

        with patch("src.services.comfyui_service.requests.post", return_value=response) as post:
            result = ComfyUIService().submit_prompt(workflow, "client-1")

        self.assertEqual(result["prompt_id"], "abc")
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:8188/prompt")
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"prompt": workflow, "client_id": "client-1"},
        )

    def test_normalize_history_extracts_image_references(self):
        from src.services.comfyui_service import ComfyUIService

        history = {
            "abc": {
                "outputs": {
                    "3": {
                        "images": [
                            {"filename": "a.png", "subfolder": "foo", "type": "temp"},
                            {"filename": "b.png"},
                        ]
                    }
                }
            }
        }

        result = ComfyUIService().normalize_history("abc", history)

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(
            result["results"],
            [
                {"nodeId": "3", "filename": "a.png", "subfolder": "foo", "type": "temp"},
                {"nodeId": "3", "filename": "b.png", "subfolder": "", "type": "output"},
            ],
        )

    def test_upload_data_url_posts_file_to_comfyui(self):
        from src.services.comfyui_service import ComfyUIService

        response = Mock()
        response.json.return_value = {"name": "input.png"}
        payload = base64.b64encode(b"image-bytes").decode("ascii")
        data_url = f"data:image/png;base64,{payload}"

        with patch("src.services.comfyui_service.requests.post", return_value=response) as post:
            result = ComfyUIService().upload_data_url(data_url)

        self.assertEqual(result["name"], "input.png")
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:8188/upload/image")
        self.assertIn("image", post.call_args.kwargs["files"])
        self.assertEqual(post.call_args.kwargs["data"], {"overwrite": "true", "type": "input"})

    def test_view_image_fetches_bytes_without_exposing_comfyui_url(self):
        from src.services.comfyui_service import ComfyUIService

        response = Mock()
        response.content = b"png-bytes"
        response.headers = {"content-type": "image/png"}

        with patch("src.services.comfyui_service.requests.get", return_value=response) as get:
            result = ComfyUIService().view_image("out.png", "", "output")

        get.assert_called_once()
        self.assertEqual(
            get.call_args.args[0],
            "http://127.0.0.1:8188/view?filename=out.png&subfolder=&type=output",
        )
        self.assertEqual(result, {"bytes": b"png-bytes", "mimetype": "image/png"})


if __name__ == "__main__":
    unittest.main()
