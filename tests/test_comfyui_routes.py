import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.utils.errors import AuthenticationError


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
    from src.models.user import User
    from src.services.auth import get_auth_service

    app_module = importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    user = User.ensure_default_user()
    token = get_auth_service().issue_token(int(user.id or 0), user.username)
    return tmpdir, app_module.app.test_client(), {"Authorization": f"Bearer {token}"}


class ComfyUIRoutesTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in (
                "DATA_DIR",
                "DB_PATH",
                "APP_SECRET_KEY",
                "COMFYUI_RUNTIME_ACTIONS_ENABLED",
            )
        }
        self.tmpdir, self.client, self.auth_headers = build_test_client()

    def runtime_headers(self):
        return {
            **self.auth_headers,
            "X-ComfyUI-Runtime-Action": "confirm-local-runtime",
        }

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

        response = self.client.get("/api/comfyui/status", headers=self.auth_headers)
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["connection"]["connected"])
        self.assertEqual(payload["runtime"]["state"], "installed")
        self.assertNotIn("baseUrl", payload["connection"])
        self.assertNotIn("baseUrl", payload["runtime"])
        self.assertNotIn("runtimeDir", payload["runtime"])

    @patch("src.routes.comfyui_routes.get_comfyui_runtime_service")
    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_status_sanitizes_disconnected_details(self, service_factory, runtime_factory):
        service = MagicMock()
        service.status.return_value = {
            "connected": False,
            "baseUrl": "http://127.0.0.1:8188",
            "error": "connection refused at /private/path",
            "queue": {"running": 0, "pending": 0},
        }
        service_factory.return_value = service
        runtime = MagicMock()
        runtime.status.return_value = {
            "state": "missing",
            "installed": False,
            "grsaiInstalled": False,
            "runtimeDir": "/private/data/comfyui/runtime",
            "baseUrl": "http://127.0.0.1:8188",
        }
        runtime_factory.return_value = runtime

        response = self.client.get("/api/comfyui/status", headers=self.auth_headers)
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(payload["connection"]["connected"])
        self.assertEqual(payload["connection"]["error"], "ComfyUI backend is not reachable")
        self.assertNotIn("127.0.0.1", json.dumps(payload))
        self.assertNotIn("/private", json.dumps(payload))

    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_object_info_returns_service_payload(self, service_factory):
        service = MagicMock()
        service.object_info.return_value = {"PreviewImage": {"input": {}}}
        service_factory.return_value = service

        response = self.client.get("/api/comfyui/object-info", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["PreviewImage"], {"input": {}})

    @patch("src.routes.comfyui_routes.normalize_workflow")
    def test_workflow_import_returns_canvas_model(self, normalize_mock):
        workflow = {"1": {"class_type": "PreviewImage", "inputs": {}}}
        normalize_mock.return_value = {"nodes": [{"id": "1"}], "links": [], "nodeCount": 1, "linkCount": 0}

        response = self.client.post(
            "/api/comfyui/workflows/import",
            json={"workflow": workflow},
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["nodeCount"], 1)
        normalize_mock.assert_called_once_with(workflow)

    def test_starter_workflow_route_returns_bundled_workflow(self):
        response = self.client.get(
            "/api/comfyui/workflows/starter/text-image", headers=self.auth_headers
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["name"], "text-image")
        self.assertEqual(payload["workflow"]["1"]["class_type"], "GrsAINanoBananaTextImage")

    def test_starter_workflow_route_rejects_unknown_name(self):
        response = self.client.get(
            "/api/comfyui/workflows/starter/unknown", headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 404)

    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_upload_image_sends_data_url_and_filename(self, service_factory):
        service = MagicMock()
        service.upload_data_url.return_value = {"name": "uploaded.png"}
        service_factory.return_value = service

        response = self.client.post(
            "/api/comfyui/upload-image",
            json={"image": "data:image/png;base64,ZmFrZQ==", "filename": "input.png"},
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["name"], "uploaded.png")
        service.upload_data_url.assert_called_once_with("data:image/png;base64,ZmFrZQ==", "input.png")

    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_prompt_route_submits_workflow(self, service_factory):
        workflow = {"1": {"class_type": "PreviewImage", "inputs": {}}}
        service = MagicMock()
        service.submit_prompt.return_value = {"prompt_id": "abc", "number": 1}
        service_factory.return_value = service

        response = self.client.post(
            "/api/comfyui/prompt",
            json={"workflow": workflow, "clientId": "client-1"},
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["prompt_id"], "abc")
        service.submit_prompt.assert_called_once_with(workflow, "client-1")

    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_prompt_route_accepts_snake_case_client_id(self, service_factory):
        workflow = {"1": {"class_type": "PreviewImage", "inputs": {}}}
        service = MagicMock()
        service.submit_prompt.return_value = {"prompt_id": "abc"}
        service_factory.return_value = service

        response = self.client.post(
            "/api/comfyui/prompt",
            json={"workflow": workflow, "client_id": "client-2"},
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        service.submit_prompt.assert_called_once_with(workflow, "client-2")

    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_prompt_route_defaults_client_id(self, service_factory):
        workflow = {"1": {"class_type": "PreviewImage", "inputs": {}}}
        service = MagicMock()
        service.submit_prompt.return_value = {"prompt_id": "abc"}
        service_factory.return_value = service

        response = self.client.post(
            "/api/comfyui/prompt", json={"workflow": workflow}, headers=self.auth_headers
        )

        self.assertEqual(response.status_code, 200)
        service.submit_prompt.assert_called_once_with(workflow, "matchdrawer")

    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_history_route_normalizes_result(self, service_factory):
        raw_history = {"abc": {"outputs": {"9": {"images": [{"filename": "out.png", "type": "output"}]}}}}
        service = MagicMock()
        service.history.return_value = raw_history
        service.normalize_history.return_value = {
            "promptId": "abc",
            "status": "succeeded",
            "results": [{"filename": "out.png"}],
        }
        service_factory.return_value = service

        response = self.client.get("/api/comfyui/history/abc", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "succeeded")
        service.history.assert_called_once_with("abc")
        service.normalize_history.assert_called_once_with("abc", raw_history)

    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_view_route_returns_image_bytes(self, service_factory):
        service = MagicMock()
        service.view_image.return_value = {"bytes": b"image-bytes", "mimetype": "image/png"}
        service_factory.return_value = service

        response = self.client.get(
            "/api/comfyui/view?filename=out.png&subfolder=foo&type=output",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertEqual(response.get_data(), b"image-bytes")
        service.view_image.assert_called_once_with("out.png", "foo", "output")

    @patch("src.routes.decorators.get_auth_service")
    @patch("src.routes.comfyui_routes.get_comfyui_service")
    def test_view_route_requires_api_auth(self, service_factory, auth_factory):
        auth = MagicMock()
        auth.require_auth.side_effect = AuthenticationError("请先登录")
        auth_factory.return_value = auth
        service = MagicMock()
        service_factory.return_value = service

        response = self.client.get("/api/comfyui/view?filename=out.png&type=output")

        self.assertEqual(response.status_code, 401)
        self.assertIn("登录", response.get_json()["error"])
        service.view_image.assert_not_called()

    @patch("src.routes.comfyui_routes.get_comfyui_runtime_service")
    def test_runtime_install_runs_service(self, runtime_factory):
        os.environ["COMFYUI_RUNTIME_ACTIONS_ENABLED"] = "1"
        runtime = MagicMock()
        runtime.run_install.return_value = {
            "state": "installed",
            "installed": True,
            "grsaiInstalled": True,
            "runtimeDir": "/private/data",
            "baseUrl": "http://127.0.0.1:8188",
        }
        runtime_factory.return_value = runtime

        response = self.client.post(
            "/api/comfyui/runtime/install",
            headers=self.runtime_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["state"], "installed")
        self.assertNotIn("runtimeDir", response.get_json())
        self.assertNotIn("baseUrl", response.get_json())
        runtime.run_install.assert_called_once_with()

    @patch("src.routes.comfyui_routes.get_comfyui_runtime_service")
    def test_runtime_install_requires_feature_flag(self, runtime_factory):
        runtime = MagicMock()
        runtime_factory.return_value = runtime

        response = self.client.post(
            "/api/comfyui/runtime/install",
            headers=self.runtime_headers(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("disabled", response.get_json()["error"])
        runtime.run_install.assert_not_called()

    @patch("src.routes.comfyui_routes.get_comfyui_runtime_service")
    def test_runtime_install_requires_confirmation_header(self, runtime_factory):
        os.environ["COMFYUI_RUNTIME_ACTIONS_ENABLED"] = "1"
        runtime = MagicMock()
        runtime_factory.return_value = runtime

        response = self.client.post("/api/comfyui/runtime/install", headers=self.auth_headers)

        self.assertEqual(response.status_code, 403)
        self.assertIn("confirmation", response.get_json()["error"])
        runtime.run_install.assert_not_called()

    @patch("src.routes.comfyui_routes.get_comfyui_runtime_service")
    def test_runtime_install_rejects_non_local_request(self, runtime_factory):
        os.environ["COMFYUI_RUNTIME_ACTIONS_ENABLED"] = "1"
        runtime = MagicMock()
        runtime_factory.return_value = runtime

        response = self.client.post(
            "/api/comfyui/runtime/install",
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
            headers=self.runtime_headers(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("local", response.get_json()["error"].lower())
        runtime.run_install.assert_not_called()

    @patch("src.routes.comfyui_routes.get_comfyui_runtime_service")
    def test_runtime_start_runs_service(self, runtime_factory):
        os.environ["COMFYUI_RUNTIME_ACTIONS_ENABLED"] = "1"
        runtime = MagicMock()
        runtime.start.return_value = {
            "started": True,
            "alreadyRunning": False,
            "baseUrl": "http://127.0.0.1:8188",
        }
        runtime_factory.return_value = runtime

        response = self.client.post(
            "/api/comfyui/runtime/start",
            headers=self.runtime_headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["started"])
        self.assertFalse(payload["alreadyRunning"])
        self.assertNotIn("baseUrl", payload)
        runtime.start.assert_called_once_with()

    @patch("src.routes.comfyui_routes.get_comfyui_runtime_service")
    def test_runtime_start_rejects_non_local_request(self, runtime_factory):
        os.environ["COMFYUI_RUNTIME_ACTIONS_ENABLED"] = "1"
        runtime = MagicMock()
        runtime_factory.return_value = runtime

        response = self.client.post(
            "/api/comfyui/runtime/start",
            environ_base={"REMOTE_ADDR": "198.51.100.8"},
            headers=self.runtime_headers(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("local", response.get_json()["error"].lower())
        runtime.start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
