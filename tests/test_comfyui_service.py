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
        upload_name, upload_bytes, upload_mime = post.call_args.kwargs["files"]["image"]
        self.assertNotEqual(upload_name, "input.png")
        self.assertTrue(upload_name.endswith(".png"))
        self.assertEqual(upload_bytes, b"image-bytes")
        self.assertEqual(upload_mime, "image/png")
        self.assertEqual(post.call_args.kwargs["data"], {"overwrite": "false", "type": "input"})

    def test_upload_data_url_uses_generated_safe_filename(self):
        from src.services.comfyui_service import ComfyUIService

        response = Mock()
        response.json.return_value = {"name": "uploaded.png"}
        payload = base64.b64encode(b"image-bytes").decode("ascii")
        data_url = f"data:image/png;base64,{payload}"

        with patch("src.services.comfyui_service.uuid.uuid4") as uuid4:
            uuid4.return_value.hex = "abc123"
            with patch("src.services.comfyui_service.requests.post", return_value=response) as post:
                ComfyUIService().upload_data_url(data_url, "../input.png")

        upload_name = post.call_args.kwargs["files"]["image"][0]
        self.assertEqual(upload_name, "abc123_input.png")
        self.assertEqual(post.call_args.kwargs["data"], {"overwrite": "false", "type": "input"})

    def test_upload_data_url_rejects_too_large_payload_before_posting(self):
        from src.services.comfyui_service import ComfyUIService
        from src.utils.errors import ApiError

        payload = base64.b64encode(b"12345").decode("ascii")
        data_url = f"data:image/png;base64,{payload}"

        with patch("src.services.comfyui_service.requests.post") as post:
            with self.assertRaises(ApiError) as ctx:
                ComfyUIService(max_upload_bytes=4).upload_data_url(data_url)

        self.assertEqual(ctx.exception.status_code, 400)
        post.assert_not_called()

    def test_upload_data_url_rejects_unsupported_mime_before_posting(self):
        from src.services.comfyui_service import ComfyUIService
        from src.utils.errors import ApiError

        payload = base64.b64encode(b"plain text").decode("ascii")
        data_url = f"data:text/plain;base64,{payload}"

        with patch("src.services.comfyui_service.requests.post") as post:
            with self.assertRaises(ApiError) as ctx:
                ComfyUIService().upload_data_url(data_url)

        self.assertEqual(ctx.exception.status_code, 400)
        post.assert_not_called()

    def test_history_rejects_unsafe_prompt_id(self):
        from src.services.comfyui_service import ComfyUIService
        from src.utils.errors import ApiError

        service = ComfyUIService()

        for prompt_id in ("../x", "abc/def"):
            with self.subTest(prompt_id=prompt_id):
                with self.assertRaises(ApiError) as ctx:
                    service.history(prompt_id)
                self.assertEqual(ctx.exception.status_code, 400)

    def test_view_url_rejects_unsafe_parameters(self):
        from src.services.comfyui_service import ComfyUIService
        from src.utils.errors import ApiError

        service = ComfyUIService()
        cases = [
            ("../x.png", "", "output"),
            ("ok.png", "../secret", "output"),
            ("ok.png", "", "bad"),
        ]

        for filename, subfolder, image_type in cases:
            with self.subTest(filename=filename, subfolder=subfolder, image_type=image_type):
                with self.assertRaises(ApiError) as ctx:
                    service.view_url(filename, subfolder, image_type)
                self.assertEqual(ctx.exception.status_code, 400)

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

    def test_view_image_rejects_non_image_content_type(self):
        from src.services.comfyui_service import ComfyUIService
        from src.utils.errors import ApiError

        response = Mock()
        response.content = b"not-image"
        response.headers = {"content-type": "text/plain"}

        with patch("src.services.comfyui_service.requests.get", return_value=response):
            with self.assertRaises(ApiError) as ctx:
                ComfyUIService().view_image("out.png", "", "output")

        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
