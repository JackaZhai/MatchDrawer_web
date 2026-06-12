"""AI service."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from ..config import get_config
from ..models.usage_stats import UsageStats
from ..utils.errors import ApiError, NotFoundError, ValidationError
from .api_key_service import get_api_key_service
from .paper_banana_service import get_paper_banana_service
from .provider_config_service import get_provider_config_service


class AIService:
    """AI service."""

    def __init__(self):
        self.config = get_config()
        self.api_key_service = get_api_key_service()
        self._grsai_image_results: dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _is_text_model_multimodal(provider: str, model: str) -> bool:
        p = (provider or "").strip().lower()
        m = (model or "").strip().lower()
        if not m:
            return False

        # 当前产品约束：grsai / deepseek 语言模型按非多模态处理
        if p in {"grsai", "deepseek"}:
            return False

        if p == "openrouter":
            openrouter_multimodal_models = {
                "google/gemini-3-flash-preview",
                "anthropic/claude-opus-4.6",
                "anthropic/claude-sonnet-4.6",
                "moonshotai/kimi-k2.5",
                "google/gemini-2.5-flash",
                "google/gemini-2.5-flash-lite",
                "anthropic/claude-sonnet-4.5",
                "openai/gpt-5.4",
                "openai/gpt-4o-mini",
            }
            if m in openrouter_multimodal_models:
                return True
            return any(
                k in m
                for k in (
                    "gemini",
                    "claude",
                    "gpt-4o",
                    "gpt-5",
                    "kimi-k2.5",
                    "vision",
                    "vl",
                    "multimodal",
                )
            )

        if p == "google":
            return "gemini" in m
        if p == "anthropic":
            return ("claude-3" in m) or ("claude-4" in m)

        multimodal_keywords = (
            "gpt-4o",
            "gpt-4.1",
            "gpt-4.5",
            "o1",
            "o3",
            "gemini",
            "claude-3",
            "claude-4",
            "vision",
            "vl",
            "gpt-image",
            "-vt",
            "multimodal",
        )
        return any(k in m for k in multimodal_keywords)

    @staticmethod
    def _requires_multimodal_text_model(
        exp_mode: str,
        pipeline_mode: str,
        critic_enabled: Optional[bool],
        eval_enabled: Optional[bool],
        max_critic_rounds: Optional[int],
    ) -> bool:
        mode = (pipeline_mode or "full").strip().lower()
        requested_exp_mode = (exp_mode or "").strip()
        if requested_exp_mode:
            selected_exp_mode = requested_exp_mode
        elif mode == "image_only":
            selected_exp_mode = "vanilla"
        else:
            selected_exp_mode = "dev_full"

        critic_rounds = 3 if max_critic_rounds is None else max(0, int(max_critic_rounds))
        if critic_enabled is False:
            critic_rounds = 0
        if selected_exp_mode not in {
            "dev_full",
            "demo_full",
            "dev_planner_critic",
            "demo_planner_critic",
        }:
            critic_rounds = 0

        do_eval = True if eval_enabled is None else bool(eval_enabled)
        if selected_exp_mode in {"demo_full", "demo_planner_critic", "dev_retriever"}:
            do_eval = False

        return critic_rounds > 0 or do_eval

    def _resolve_grsai_host(self, user_id: Optional[int]) -> str:
        """Resolve grsai host from active base URL first, then config host."""
        active_base = (
            self.api_key_service.get_active_base_url(user_id, provider="grsai") or ""
        ).rstrip("/")
        if active_base:
            if active_base.lower().endswith("/v1"):
                return active_base[:-3].rstrip("/")
            return active_base
        return self.config.api_host.rstrip("/")

    def _candidate_grsai_hosts(self, user_id: Optional[int]) -> list[str]:
        """Build ordered fallback hosts for grsai requests."""
        active_host = self._resolve_grsai_host(user_id)
        config_host = self.config.api_host.rstrip("/")
        candidates = [
            active_host,
            config_host,
            "https://grsai.dakka.com.cn",
            "https://grsaiapi.com",
        ]
        result: list[str] = []
        for host in candidates:
            h = (host or "").strip().rstrip("/")
            if "api.grsai.com" in h.lower():
                continue
            if h and h not in result:
                result.append(h)
        return result

    def _resolve_grsai_v1_base(self, user_id: Optional[int]) -> str:
        """Resolve OpenAI-compatible grsai v1 base URL."""
        active_base = (
            self.api_key_service.get_active_base_url(user_id, provider="grsai") or ""
        ).rstrip("/")
        if active_base:
            if "api.grsai.com" in active_base.lower():
                return "https://grsai.dakka.com.cn/v1"
            return active_base if active_base.lower().endswith("/v1") else f"{active_base}/v1"
        config_host = self.config.api_host.rstrip("/")
        if "api.grsai.com" in config_host.lower():
            return "https://grsai.dakka.com.cn/v1"
        return f"{config_host}/v1"

    @staticmethod
    def _extract_numeric_credits(payload: Any) -> Optional[float]:
        """Best-effort extraction of credits value from nested payload."""
        keys = {
            "credits",
            "credit",
            "balance",
            "remaining",
            "available",
            "availablecredits",
            "available_credit",
            "totalcredits",
            "quota",
        }

        def _walk(node: Any) -> Optional[float]:
            if isinstance(node, (int, float)):
                return float(node)
            if isinstance(node, dict):
                for k, v in node.items():
                    if str(k).replace("_", "").lower() in keys and isinstance(v, (int, float)):
                        return float(v)
                for v in node.values():
                    found = _walk(v)
                    if found is not None:
                        return found
            if isinstance(node, list):
                for item in node:
                    found = _walk(item)
                    if found is not None:
                        return found
            return None

        return _walk(payload)

    def call_api(
        self, endpoint: str, payload: Dict[str, Any], user_id: Optional[int]
    ) -> Dict[str, Any]:
        """Call upstream API (POST)."""
        headers = self.api_key_service.build_headers(user_id, provider="grsai")
        headers["Connection"] = "close"
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            response = exc.response
            text = response.text if response is not None else ""
            raise ApiError(
                "API request failed",
                status_code=response.status_code if response is not None else 502,
                details=text,
            )
        except requests.RequestException as exc:
            raise ApiError(f"Network error: {exc}", status_code=502)

        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(
                f"Invalid JSON from upstream: {exc}",
                status_code=502,
                details=response.text,
            )

    def call_get_api(self, endpoint: str, user_id: Optional[int]) -> Dict[str, Any]:
        """Call upstream API (GET)."""
        headers = self.api_key_service.build_headers(user_id, provider="grsai")
        headers["Connection"] = "close"
        try:
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=120,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            response = exc.response
            text = response.text if response is not None else ""
            raise ApiError(
                "API request failed",
                status_code=response.status_code if response is not None else 502,
                details=text,
            )
        except requests.RequestException as exc:
            raise ApiError(f"Network error: {exc}", status_code=502)

        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(
                f"Invalid JSON from upstream: {exc}",
                status_code=502,
                details=response.text,
            )

    def call_streaming_api(self, endpoint: str, payload: Dict[str, Any], user_id: Optional[int]):
        """Call upstream streaming API."""
        headers = self.api_key_service.build_headers(user_id, provider="grsai")
        headers["Connection"] = "close"
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=120,
                stream=True,
            )
            response.raise_for_status()
            return response
        except requests.HTTPError as exc:
            response = exc.response
            text = response.text if response is not None else ""
            raise ApiError(
                "API request failed",
                status_code=response.status_code if response is not None else 502,
                details=text,
            )
        except requests.RequestException as exc:
            raise ApiError(f"Network error: {exc}", status_code=502)

    def get_credits(self, user_id: Optional[int]) -> Dict[str, Any]:
        """Get credits for the active grsai key."""
        api_key = self.api_key_service.get_active_api_key_value(user_id, provider="grsai")
        if not api_key:
            raise ApiError("Missing API key", status_code=400)

        last_error: Optional[ApiError] = None
        for host in self._candidate_grsai_hosts(user_id):
            candidates = [
                (f"{host}/client/openapi/getCredits", {}),
                (f"{host}/client/openapi/getAPIKeyCredits", {"apiKey": api_key}),
                (f"{host}/client/openapi/getAPIKeyCredits", {}),
            ]
            for endpoint, payload in candidates:
                try:
                    result = self.call_api(endpoint, payload, user_id)
                    credits = self._extract_numeric_credits(result)
                    if credits is not None:
                        return {"code": 0, "data": {"credits": credits}, "msg": "success"}
                    return result
                except ApiError as exc:
                    last_error = exc
                    continue

        if last_error is not None:
            raise last_error
        raise ApiError("API request failed", status_code=502)

    def get_model_status(self, user_id: Optional[int], model: str) -> Dict[str, Any]:
        model = (model or "").strip()
        if not model:
            raise ApiError("model is required", status_code=400)

        last_error: Optional[ApiError] = None
        for host in self._candidate_grsai_hosts(user_id):
            # Legacy model status endpoint (if provider still supports it).
            legacy_endpoint = f"{host}/client/common/getModelStatus?model={quote(model)}"
            try:
                return self.call_get_api(legacy_endpoint, user_id)
            except ApiError as exc:
                last_error = exc

            # OpenAI-compatible fallback: probe /v1/models list.
            v1_base = f"{host}/v1"
            models_endpoint = f"{v1_base}/models"
            try:
                models_resp = self.call_get_api(models_endpoint, user_id)
                models = models_resp.get("data") if isinstance(models_resp, dict) else None
                available = False
                if isinstance(models, list):
                    available = any(
                        isinstance(item, dict) and str(item.get("id") or "").strip() == model
                        for item in models
                    )
                return {
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "status": available,
                        "model": model,
                    },
                }
            except ApiError as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise last_error
        raise ApiError("API request failed", status_code=502)

    def _extract_upstream_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else payload

    def _extract_upstream_task_id(self, payload: Dict[str, Any]) -> str:
        data = self._extract_upstream_data(payload)
        candidates = [
            data.get("id"),
            data.get("taskId"),
            data.get("task_id"),
            data.get("drawId"),
            data.get("draw_id"),
        ]
        for value in candidates:
            if value:
                return str(value).strip()
        raise ApiError(
            "Upstream image API did not return task id",
            status_code=502,
            details=json.dumps(payload, ensure_ascii=False),
        )

    def _normalise_image_result_payload(self, payload: Dict[str, Any], draw_id: str) -> Dict[str, Any]:
        data = self._extract_upstream_data(payload)
        if not isinstance(data, dict):
            return {"id": draw_id, "status": "running", "progress": 10, "raw": payload}

        result = dict(data)
        result["id"] = str(result.get("id") or draw_id)

        raw_status = str(result.get("status") or result.get("state") or "").strip().lower()
        if raw_status in {"success", "completed", "complete", "done", "finish", "finished"}:
            result["status"] = "succeeded"
        elif raw_status in {"error", "failed", "fail", "failure"}:
            result["status"] = "failed"
        elif raw_status:
            result["status"] = raw_status
        else:
            result["status"] = "running"

        if result["status"] == "succeeded":
            result["progress"] = 100
        else:
            progress_raw = str(result.get("progress") or result.get("percent") or "10")
            progress_digits = "".join(ch for ch in progress_raw if ch.isdigit())
            result["progress"] = int(progress_digits or "10")

        image_values: list[str] = []
        for key in ("url", "imageUrl", "image_url", "output", "result"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                image_values.append(value.strip())
        for key in ("urls", "images", "outputs", "results"):
            value = result.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.strip():
                        image_values.append(item.strip())
                    elif isinstance(item, dict):
                        url = item.get("url") or item.get("imageUrl") or item.get("image_url")
                        if isinstance(url, str) and url.strip():
                            image_values.append(url.strip())
        if image_values:
            result["results"] = [{"url": url, "content": "GrsAI generated"} for url in image_values]

        return result

    @staticmethod
    def _can_try_next_grsai_host(error: ApiError) -> bool:
        if error.status_code >= 500 or error.message.startswith("Network error:"):
            return True
        if error.status_code == 400 and error.details:
            try:
                payload = json.loads(error.details)
            except ValueError:
                return False
            if not isinstance(payload, dict):
                return False
            status = str(payload.get("status") or "").strip().lower()
            message = str(payload.get("error") or payload.get("message") or "").strip().lower()
            return status == "failed" and message == "generate failed"
        return False

    def _call_grsai_image_api(
        self, user_id: Optional[int], path: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        last_error: Optional[ApiError] = None
        for host in self._candidate_grsai_hosts(user_id):
            try:
                return self.call_api(f"{host}{path}", payload, user_id)
            except ApiError as exc:
                last_error = exc
                if not self._can_try_next_grsai_host(exc):
                    raise
                continue

        if last_error is not None:
            raise last_error
        raise ApiError("API request failed", status_code=502)

    def _generate_grsai_image(self, user_id: Optional[int], data: Dict[str, Any]) -> Dict[str, Any]:
        from ..utils.validation import get_validation_service

        validation = get_validation_service()
        prompt = (data.get("prompt") or data.get("caption") or "").strip()
        validation.validate_prompt(prompt)
        urls = validation.sanitize_urls(data.get("urls") or [])
        validation.validate_reference_images(urls)

        model = (
            data.get("imageModel")
            or data.get("image_model")
            or data.get("model")
            or "nano-banana-pro"
        )
        model = str(model).strip() or "nano-banana-pro"
        payload = {
            "model": model,
            "prompt": prompt,
            "aspectRatio": (data.get("aspectRatio") or "auto"),
            "imageSize": (data.get("imageSize") or "1K"),
            "urls": urls,
            "shutProgress": bool(data.get("shutProgress", False)),
        }
        webhook = str(data.get("webHook", data.get("webhook", "")) or "").strip()
        if webhook and webhook != "-1":
            payload["webHook"] = webhook

        response = self._call_grsai_image_api(user_id, "/v1/api/generate", payload)
        task_id = self._extract_upstream_task_id(response)
        result_payload = self._normalise_image_result_payload(response, task_id)
        if result_payload.get("status") in {"succeeded", "failed"} or result_payload.get("results"):
            self._grsai_image_results[task_id] = result_payload

        if user_id:
            UsageStats.record_usage_for_user(user_id)

        return {"code": 0, "data": {"id": task_id}}

    def _get_grsai_image_result(self, user_id: Optional[int], draw_id: str) -> Dict[str, Any]:
        cached = self._grsai_image_results.get(draw_id)
        if cached is not None:
            return {"code": 0, "data": cached}

        response = self._call_grsai_image_api(user_id, "/v1/api/result", {"id": draw_id})
        payload = self._normalise_image_result_payload(response, draw_id)
        if payload.get("status") in {"succeeded", "failed"} or payload.get("results"):
            self._grsai_image_results[draw_id] = payload

        if user_id:
            UsageStats.record_usage_for_user(user_id)

        return {"code": 0, "data": payload}

    def generate_image(self, user_id: Optional[int], data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image through GrsAI or the PaperBanana workflow wrapper."""
        from ..utils.validation import get_validation_service

        validation = get_validation_service()

        prompt = (data.get("prompt") or "").strip()
        caption = (data.get("caption") or "").strip()
        aspect_ratio = (data.get("aspectRatio") or "16:9").strip() or "16:9"
        image_size = (data.get("imageSize") or "1K").strip() or "1K"
        pipeline_mode = (
            data.get("pipelineMode") or data.get("pipeline_mode") or "full"
        ).strip().lower() or "full"
        if pipeline_mode == "image_only":
            return self._generate_grsai_image(user_id, data)
        if aspect_ratio.lower() == "auto":
            aspect_ratio = "16:9"

        exp_mode = (data.get("expMode") or data.get("exp_mode") or "").strip()
        retrieval_setting = (
            data.get("retrievalSetting") or data.get("retrieval_setting") or ""
        ).strip()
        critic_enabled_raw = data.get("criticEnabled", data.get("critic_enabled", None))
        eval_enabled_raw = data.get("evalEnabled", data.get("eval_enabled", None))
        max_critic_raw = data.get("maxCriticRounds", data.get("max_critic_rounds", None))

        def _parse_optional_bool(value):
            if value is None:
                return None
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in {"1", "true", "yes", "on"}:
                return True
            if s in {"0", "false", "no", "off"}:
                return False
            return bool(value)

        critic_enabled = _parse_optional_bool(critic_enabled_raw)
        eval_enabled = _parse_optional_bool(eval_enabled_raw)
        if max_critic_raw is None or str(max_critic_raw).strip() == "":
            max_critic_rounds = None
        else:
            max_critic_rounds = int(max_critic_raw)

        provider = (data.get("provider") or "grsai").strip() or "grsai"
        text_provider = (
            data.get("textProvider") or data.get("text_provider") or provider
        ).strip() or provider
        image_provider = (
            data.get("imageProvider") or data.get("image_provider") or provider
        ).strip() or provider
        text_provider = self.api_key_service.normalize_provider(text_provider)
        image_provider = self.api_key_service.normalize_provider(image_provider)
        provider = (
            image_provider or text_provider or self.api_key_service.normalize_provider(provider)
        )
        preset = (data.get("model") or "nano-banana-pro").strip() or "nano-banana-pro"

        text_model = (data.get("textModel") or data.get("text_model") or "").strip()
        image_model = (data.get("imageModel") or data.get("image_model") or "").strip()
        svc = get_provider_config_service()
        key_owner_id = self.api_key_service.get_global_key_owner_id()
        text_defaults = svc.get_defaults(key_owner_id, text_provider)
        image_defaults = svc.get_defaults(key_owner_id, image_provider)

        # If UI did not specify, use defaults per selected provider.
        text_model = text_model or text_defaults.get("textModel") or ""
        image_model = image_model or image_defaults.get("imageModel") or ""

        # Final fallback mapping from the legacy "nano-banana-*" preset.
        if not text_model or not image_model:
            preset_map = {
                "gpt-image-2": ("gemini-2.5-pro", "gpt-image-2"),
                "nano-banana-pro": ("gemini-2.5-pro", "nano-banana-pro"),
                "nano-banana-pro-vt": ("gemini-2.5-pro", "nano-banana-pro-vt"),
                "nano-banana-2": ("gemini-2.5-pro", "nano-banana-2"),
                "nano-banana-fast": ("gemini-2.5-pro", "nano-banana-fast"),
                "nano-banana": ("gemini-2.5-pro", "nano-banana"),
            }
            mapped = preset_map.get(preset) or preset_map["nano-banana-pro"]
            text_model = text_model or mapped[0]
            image_model = image_model or mapped[1]

        if self._requires_multimodal_text_model(
            exp_mode=exp_mode,
            pipeline_mode=pipeline_mode,
            critic_enabled=critic_enabled,
            eval_enabled=eval_enabled,
            max_critic_rounds=max_critic_rounds,
        ) and not self._is_text_model_multimodal(text_provider, text_model):
            raise ValidationError(
                f"当前语言提供商/模型不支持多模态能力：provider={text_provider}, model={text_model}。"
                "请切换到支持视觉的语言模型（如 gemini / gpt-4o / claude-3+）。"
            )
        if not caption:
            caption = prompt[:120] if prompt else "diagram"

        validation.validate_prompt(prompt or caption)

        service = get_paper_banana_service()
        job_id = service.submit_diagram(
            user_id=user_id,
            provider=provider,
            text_provider=text_provider,
            image_provider=image_provider,
            text_model=text_model,
            image_model=image_model,
            method_content=prompt,
            caption=caption,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            pipeline_mode=pipeline_mode,
            max_critic_rounds=max_critic_rounds,
            exp_mode=exp_mode,
            retrieval_setting=retrieval_setting,
            critic_enabled=critic_enabled,
            eval_enabled=eval_enabled,
        )

        if user_id:
            UsageStats.record_usage_for_user(user_id)

        return {"code": 0, "data": {"id": job_id}}

    def get_image_result(self, user_id: Optional[int], draw_id: str) -> Dict[str, Any]:
        """Get image generation result from local PaperBanana or GrsAI."""
        from ..utils.validation import get_validation_service

        validation = get_validation_service()
        validation.validate_draw_id(draw_id)

        service = get_paper_banana_service()
        try:
            payload = service.get_result_payload(draw_id)
        except NotFoundError:
            return self._get_grsai_image_result(user_id, draw_id)

        if user_id:
            UsageStats.record_usage_for_user(user_id)

        return {"code": 0, "data": payload}

    def cancel_image_result(self, user_id: Optional[int], draw_id: str) -> Dict[str, Any]:
        """Cancel image generation task (PaperBanana local)."""
        from ..utils.validation import get_validation_service

        validation = get_validation_service()
        validation.validate_draw_id(draw_id)

        service = get_paper_banana_service()
        payload = service.cancel_job(draw_id)

        if user_id:
            UsageStats.record_usage_for_user(user_id)

        return {"code": 0, "data": payload}

    def chat_completion(self, user_id: Optional[int], data: Dict[str, Any]) -> Any:
        """Chat completion.

        Always routes via the backend key store (provider-aware).
        """
        from ..utils.validation import get_validation_service

        validation = get_validation_service()

        provider = (data.get("provider") or "grsai").strip()
        provider = self.api_key_service.normalize_provider(provider)

        model = (data.get("model") or "gemini-2.5-pro").strip()
        messages = data.get("messages") or []
        stream = bool(data.get("stream", False))
        temperature = data.get("temperature", None)
        max_tokens = data.get("max_tokens", data.get("maxTokens", None))

        validation.validate_messages(messages)

        if provider == "anthropic":
            if stream:
                raise ApiError(
                    "Anthropic streaming is not supported in this UI yet. Use OpenRouter or disable stream.",
                    status_code=400,
                )

            base_url = self.api_key_service.get_active_base_url(
                user_id, provider="anthropic"
            ).rstrip("/")
            endpoint = f"{base_url}/v1/messages"
            headers = self.api_key_service.build_headers(user_id, provider="anthropic")

            system_texts = [
                m.get("content")
                for m in messages
                if m and m.get("role") == "system" and isinstance(m.get("content"), str)
            ]
            system = "\n".join([t for t in system_texts if t]) if system_texts else None

            converted = []
            for m in messages:
                if not m:
                    continue
                role = m.get("role")
                if role not in ("user", "assistant"):
                    continue
                content = m.get("content")
                if isinstance(content, str):
                    text = content
                else:
                    text = json.dumps(content, ensure_ascii=False)
                converted.append({"role": role, "content": [{"type": "text", "text": text}]})

            body: Dict[str, Any] = {
                "model": model,
                "max_tokens": int(max_tokens) if max_tokens is not None else 2000,
                "temperature": float(temperature) if temperature is not None else 0.7,
                "messages": converted,
            }
            if system:
                body["system"] = system

            try:
                resp = requests.post(endpoint, headers=headers, json=body, timeout=120)
                resp.raise_for_status()
                data_json = resp.json()
            except requests.HTTPError as exc:
                raise ApiError(
                    "API request failed",
                    status_code=exc.response.status_code if exc.response else 502,
                    details=(exc.response.text if exc.response else ""),
                )
            except requests.RequestException as exc:
                raise ApiError(f"Network error: {exc}", status_code=502)
            except ValueError as exc:
                raise ApiError(
                    f"Invalid JSON from upstream: {exc}",
                    status_code=502,
                    details=resp.text if "resp" in locals() else "",
                )

            # Convert to OpenAI-ish shape for the existing UI
            parts = data_json.get("content") or []
            text_parts = []
            for part in parts:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text") or "")
            content_text = "".join(text_parts).strip()

            result = {
                "id": data_json.get("id") or "anthropic",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content_text},
                        "finish_reason": "stop",
                    }
                ],
            }

            if user_id:
                UsageStats.record_usage_for_user(user_id)
            return result

        # Default: OpenAI-compatible providers
        headers = self.api_key_service.build_headers(user_id, provider=provider)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if provider == "grsai":
            base_candidates = [f"{h}/v1" for h in self._candidate_grsai_hosts(user_id)]
        else:
            active_base = self.api_key_service.get_active_base_url(
                user_id, provider=provider
            ).rstrip("/")
            base_candidates = [active_base] if active_base else []

        last_error: Optional[ApiError] = None
        for base_url in base_candidates:
            endpoint = f"{base_url}/chat/completions"
            if stream:
                try:
                    response = requests.post(
                        endpoint, headers=headers, json=payload, timeout=120, stream=True
                    )
                    response.raise_for_status()
                    if user_id:
                        UsageStats.record_usage_for_user(user_id)
                    return response
                except requests.HTTPError as exc:
                    last_error = ApiError(
                        "API request failed",
                        status_code=exc.response.status_code if exc.response else 502,
                        details=(exc.response.text if exc.response else ""),
                    )
                    continue
                except requests.RequestException as exc:
                    last_error = ApiError(f"Network error: {exc}", status_code=502)
                    continue
            else:
                try:
                    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
                    response.raise_for_status()
                    result = response.json()
                    if user_id:
                        UsageStats.record_usage_for_user(user_id)
                    return result
                except requests.HTTPError as exc:
                    last_error = ApiError(
                        "API request failed",
                        status_code=exc.response.status_code if exc.response else 502,
                        details=(exc.response.text if exc.response else ""),
                    )
                    continue
                except requests.RequestException as exc:
                    last_error = ApiError(f"Network error: {exc}", status_code=502)
                    continue
                except ValueError as exc:
                    last_error = ApiError(
                        f"Invalid JSON from upstream: {exc}",
                        status_code=502,
                        details=response.text if "response" in locals() else "",
                    )
                    continue

        if last_error is not None:
            raise last_error
        raise ApiError("API request failed", status_code=502)

    def generate_stream_response(self, response):
        """Generate SSE response."""

        def generate():
            for chunk in response.iter_lines():
                if chunk:
                    text = chunk.decode("utf-8", errors="ignore")
                    payload = text if text.startswith("data:") else f"data: {text}"
                    yield (payload + "\n\n").encode("utf-8")

        return generate()


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
