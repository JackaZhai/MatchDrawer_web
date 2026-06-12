import unittest
from unittest.mock import Mock, patch

from requests import HTTPError, Response

from src.services.ai_service import AIService
from src.utils.errors import ApiError, NotFoundError


class GrsaiImageRoutingTest(unittest.TestCase):
    def test_image_only_generation_uses_grsai_not_paperbanana(self):
        service = AIService()
        service._resolve_grsai_host = Mock(return_value="https://grsaiapi.com")
        service.call_api = Mock(return_value={"code": 0, "data": {"id": "grs-task-1"}})

        with patch("src.services.ai_service.get_paper_banana_service") as paper_service:
            result = service.generate_image(
                None,
                {
                    "prompt": "生成一张产品展示图",
                    "pipelineMode": "image_only",
                    "imageModel": "nano-banana-pro",
                    "imageSize": "1K",
                    "urls": [],
                },
            )

        self.assertEqual(result["data"]["id"], "grs-task-1")
        paper_service.assert_not_called()
        service.call_api.assert_called_once()
        endpoint, payload, _user_id = service.call_api.call_args.args
        self.assertEqual(endpoint, "https://grsaiapi.com/v1/api/generate")
        self.assertEqual(payload["model"], "nano-banana-pro")
        self.assertNotIn("webHook", payload)

    def test_image_only_generation_tries_next_grsai_host_after_network_error(self):
        service = AIService()
        service._candidate_grsai_hosts = Mock(
            return_value=["https://grsaiapi.com", "https://grsai.dakka.com.cn"]
        )
        service.call_api = Mock(
            side_effect=[
                ApiError("Network error: ssl eof", status_code=502),
                {"code": 0, "data": {"id": "grs-task-fallback"}},
            ]
        )

        result = service.generate_image(
            None,
            {
                "prompt": "生成一张产品展示图",
                "pipelineMode": "image_only",
                "imageModel": "nano-banana-fast",
                "imageSize": "1K",
                "urls": [],
            },
        )

        self.assertEqual(result["data"]["id"], "grs-task-fallback")
        self.assertEqual(
            [call.args[0] for call in service.call_api.call_args_list],
            [
                "https://grsaiapi.com/v1/api/generate",
                "https://grsai.dakka.com.cn/v1/api/generate",
            ],
        )

    def test_image_only_generation_retries_transient_upstream_generate_failed(self):
        service = AIService()
        service._candidate_grsai_hosts = Mock(
            return_value=["https://grsaiapi.com", "https://grsai.dakka.com.cn"]
        )
        service.call_api = Mock(
            side_effect=[
                ApiError(
                    "API request failed",
                    status_code=400,
                    details='{"id":"bad-task","status":"failed","error":"generate failed"}',
                ),
                {"code": 0, "data": {"id": "grs-task-retry"}},
            ]
        )

        result = service.generate_image(
            None,
            {
                "prompt": "生成一张产品展示图",
                "pipelineMode": "image_only",
                "imageModel": "nano-banana-fast",
                "imageSize": "1K",
                "urls": [],
            },
        )

        self.assertEqual(result["data"]["id"], "grs-task-retry")
        self.assertEqual(service.call_api.call_count, 2)

    def test_image_only_generation_caches_synchronous_grsai_result(self):
        service = AIService()
        service._resolve_grsai_host = Mock(return_value="https://grsaiapi.com")
        service.call_api = Mock(
            return_value={
                "id": "grs-task-sync",
                "status": "succeeded",
                "results": [{"url": "https://example.com/generated.png"}],
            }
        )

        generated = service.generate_image(
            None,
            {
                "prompt": "生成一张产品展示图",
                "pipelineMode": "image_only",
                "imageModel": "nano-banana-fast",
                "imageSize": "1K",
                "urls": [],
            },
        )
        service.call_api.reset_mock()

        result = service._get_grsai_image_result(None, generated["data"]["id"])

        self.assertEqual(result["data"]["status"], "succeeded")
        self.assertEqual(result["data"]["results"][0]["url"], "https://example.com/generated.png")
        service.call_api.assert_not_called()

    def test_unknown_local_job_result_falls_back_to_grsai_result_api(self):
        service = AIService()
        service._resolve_grsai_host = Mock(return_value="https://grsaiapi.com")
        service.call_api = Mock(
            return_value={
                "code": 0,
                "data": {
                    "status": "success",
                    "url": "https://example.com/result.png",
                },
            }
        )
        paper_service = Mock()
        paper_service.get_result_payload.side_effect = NotFoundError("Job not found")

        with patch("src.services.ai_service.get_paper_banana_service", return_value=paper_service):
            result = service.get_image_result(None, "grs-task-1")

        self.assertEqual(result["data"]["status"], "succeeded")
        self.assertEqual(result["data"]["progress"], 100)
        self.assertEqual(result["data"]["results"][0]["url"], "https://example.com/result.png")
        service.call_api.assert_called_once_with(
            "https://grsaiapi.com/v1/api/result",
            {"id": "grs-task-1"},
            None,
        )

    def test_full_paperbanana_generation_normalizes_auto_aspect_ratio(self):
        service = AIService()
        service.api_key_service.get_global_key_owner_id = Mock(return_value=1)
        paper_service = Mock()
        paper_service.submit_diagram.return_value = "paper-job-1"
        provider_config_service = Mock()
        provider_config_service.get_defaults.return_value = {}

        with patch("src.services.ai_service.get_paper_banana_service", return_value=paper_service):
            with patch(
                "src.services.ai_service.get_provider_config_service",
                return_value=provider_config_service,
            ):
                result = service.generate_image(
                    None,
                    {
                        "prompt": "Draw a horizontal scientific flowchart.",
                        "pipelineMode": "full",
                        "expMode": "dev_planner_stylist",
                        "provider": "grsai",
                        "textProvider": "openai",
                        "imageProvider": "grsai",
                        "textModel": "gpt-4o-mini",
                        "imageModel": "nano-banana-pro",
                        "aspectRatio": "auto",
                        "criticEnabled": False,
                        "evalEnabled": False,
                        "maxCriticRounds": 0,
                    },
                )

        self.assertEqual(result["data"]["id"], "paper-job-1")
        self.assertEqual(paper_service.submit_diagram.call_args.kwargs["aspect_ratio"], "16:9")

    def test_grsai_result_tries_next_host_after_network_error(self):
        service = AIService()
        service._candidate_grsai_hosts = Mock(
            return_value=["https://grsaiapi.com", "https://grsai.dakka.com.cn"]
        )
        service.call_api = Mock(
            side_effect=[
                ApiError("Network error: ssl eof", status_code=502),
                {
                    "code": 0,
                    "data": {
                        "status": "success",
                        "url": "https://example.com/result.png",
                    },
                },
            ]
        )

        result = service._get_grsai_image_result(None, "grs-task-1")

        self.assertEqual(result["data"]["status"], "succeeded")
        self.assertEqual(
            [call.args[0] for call in service.call_api.call_args_list],
            [
                "https://grsaiapi.com/v1/api/result",
                "https://grsai.dakka.com.cn/v1/api/result",
            ],
        )

    def test_call_api_preserves_http_error_status_from_upstream(self):
        service = AIService()
        service.api_key_service.build_headers = Mock(return_value={"Authorization": "Bearer test"})
        response = Response()
        response.status_code = 400
        response._content = b'{"error":"bad request"}'
        response.url = "https://grsaiapi.com/v1/api/generate"

        def raise_http_error():
            raise HTTPError("400 Client Error", response=response)

        response.raise_for_status = raise_http_error

        with patch("src.services.ai_service.requests.post", return_value=response):
            with self.assertRaises(ApiError) as context:
                service.call_api("https://grsaiapi.com/v1/api/generate", {}, None)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.details, '{"error":"bad request"}')

    def test_call_api_closes_grsai_connections(self):
        service = AIService()
        service.api_key_service.build_headers = Mock(return_value={"Authorization": "Bearer test"})
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"ok": True}

        with patch("src.services.ai_service.requests.post", return_value=response) as post:
            result = service.call_api("https://grsaiapi.com/v1/api/generate", {}, None)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(post.call_args.kwargs["headers"]["Connection"], "close")


if __name__ == "__main__":
    unittest.main()
