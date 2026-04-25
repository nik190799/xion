"""Chutes (Bittensor Subnet 64) hosted generative provider.

Property promised. Hosted inference can be served by a decentralized
GPU subnet with on-chain TAO billing, and the Genesis Default hosted
path is TEE-by-default when the configured Chutes model advertises
``confidential_compute=true``.

Implementation note. Chutes exposes an OpenAI-compatible API at
``https://llm.chutes.ai/v1``. This provider intentionally mirrors the
existing OpenRouter implementation: stdlib ``http.client`` for the
non-streaming path, ``httpx`` only inside the native streaming method,
and aggressive credential scrubbing before any error escapes.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, ClassVar
from urllib.parse import urlparse

from orchestrator.inference_router.provider import (
    CacheControl,
    GenerationResult,
    InsufficientCreditsError,
    Message,
    ModerationRefusalError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnreachableError,
    RateLimitedUpstreamError,
    UnknownProviderError,
)
from orchestrator.inference_router.router import Category


class ChutesProviderError(ProviderError):
    """Raised on Chutes construction-time validation failures."""

    failure_reason_class = "unknown_provider_error"


_DEFAULT_BASE_URL = "https://llm.chutes.ai/v1"
_DEFAULT_API_BASE_URL = "https://api.chutes.ai"
_DEFAULT_MODEL = "moonshotai/Kimi-K2.6-TEE"
_DEFAULT_TEE_REQUIRED = "true"
_HEALTH_CACHE_TTL_S = 60.0
_HEALTH_TIMEOUT_S = 5.0
_PROVIDER_ID = "chutes"

_RE_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE)
_RE_CHUTES_KEY = re.compile(r"cpk_[A-Za-z0-9_\-\.]+")


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _scrub(msg: str, api_key: str) -> str:
    out = msg
    if api_key:
        out = out.replace(api_key, "<api_key_redacted>")
    out = _RE_BEARER.sub("Bearer <redacted>", out)
    return _RE_CHUTES_KEY.sub("<api_key_redacted>", out)


def _error_for_status(status: int, message: str) -> ProviderError:
    if status == 402:
        return InsufficientCreditsError(message, provider_id=_PROVIDER_ID)
    if status == 403:
        return ModerationRefusalError(message, provider_id=_PROVIDER_ID)
    if status == 429:
        return RateLimitedUpstreamError(message, provider_id=_PROVIDER_ID)
    if 500 <= status < 600:
        return ProviderUnreachableError(message, provider_id=_PROVIDER_ID)
    return UnknownProviderError(message, provider_id=_PROVIDER_ID)


@dataclass
class ChutesGenerativeProvider:
    """OpenAI-compatible Chutes hosted provider."""

    provider_id: str = "chutes"
    category: ClassVar[Category] = "hosted_api"

    base_url: str = field(default_factory=lambda: os.environ.get(
        "XION_CHUTES_BASE_URL", _DEFAULT_BASE_URL,
    ))
    api_base_url: str = field(default_factory=lambda: os.environ.get(
        "XION_CHUTES_API_BASE_URL", _DEFAULT_API_BASE_URL,
    ))
    model: str = field(default_factory=lambda: os.environ.get(
        "XION_CHUTES_HOSTED_MODEL", _DEFAULT_MODEL,
    ))
    tee_required: bool = field(default_factory=lambda: _truthy(os.environ.get(
        "XION_CHUTES_TEE_REQUIRED", _DEFAULT_TEE_REQUIRED,
    )))
    _api_key: str = field(default_factory=lambda: os.environ.get(
        "XION_CHUTES_API_KEY", "",
    ), repr=False)

    _cached_health: bool = field(default=False, init=False, repr=False)
    _cached_health_at: float = field(default=0.0, init=False, repr=False)
    _model_record: dict[str, Any] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self._api_key:
            raise ChutesProviderError(
                "ChutesGenerativeProvider requires XION_CHUTES_API_KEY to be set."
            )
        for label, url in (("XION_CHUTES_BASE_URL", self.base_url), ("XION_CHUTES_API_BASE_URL", self.api_base_url)):
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ChutesProviderError(
                    f"ChutesGenerativeProvider: {label} is not a valid http(s) URL: {url!r}"
                )

    @property
    def provider_fingerprint(self) -> str:
        suffix = "tee" if self.confidential_compute else "nontee"
        return f"chutes-sn64:{self.model}:{suffix}"

    @property
    def confidential_compute(self) -> bool:
        record = self._model_record or {}
        return bool(record.get("confidential_compute"))

    @property
    def tee_attestation(self) -> str | None:
        if self.confidential_compute:
            return "intel_tdx_via_chutes"
        return None

    def health(self) -> bool:
        now = time.monotonic()
        if now - self._cached_health_at < _HEALTH_CACHE_TTL_S:
            return self._cached_health

        healthy = False
        try:
            payload = self._get_json(self.base_url, "/models", timeout=_HEALTH_TIMEOUT_S)
            data = payload.get("data") if isinstance(payload, dict) else None
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("id") == self.model:
                        self._model_record = item
                        healthy = True
                        break
            if healthy and self.tee_required and not self.confidential_compute:
                healthy = False
        except ProviderError:
            healthy = False

        self._cached_health = healthy
        self._cached_health_at = now
        return healthy

    def generate(
        self,
        prompt: str,
        *,
        system: str | None,
        max_tokens: int,
        deadline_s: float,
    ) -> GenerationResult:
        if deadline_s <= 0:
            raise ChutesProviderError("generate: deadline_s must be positive")
        self._assert_tee_if_required()

        messages: list[dict[str, str]] = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
        }).encode("utf-8")

        started = time.monotonic()
        raw, status = self._post_raw(
            self.base_url,
            "/chat/completions",
            body=body,
            timeout=deadline_s,
            headers={"Content-Type": "application/json", "User-Agent": "xion-os/0.4.0 (+phase-6.9)"},
        )
        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        if not (200 <= status < 300):
            snippet = raw[:512].decode("utf-8", errors="replace")
            raise _error_for_status(status, f"chutes HTTP {status}: {_scrub(snippet, self._api_key)}")
        try:
            payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise UnknownProviderError(
                f"chutes response not valid JSON: {_scrub(str(e), self._api_key)}",
                provider_id=_PROVIDER_ID,
            ) from None
        return _parse_openai_completion(
            payload,
            model=self.model,
            latency_ms=latency_ms,
            provider_fingerprint=self.provider_fingerprint,
            tee_attestation=self.tee_attestation,
        )

    def generate_messages(
        self,
        messages: list[Message],
        *,
        max_tokens: int,
        temperature: float | None = None,
        top_p: float | None = None,
        seed: int | None = None,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
        cache_control: CacheControl | None = None,
        deadline_s: float = 30.0,
    ) -> GenerationResult:
        """Canonical Phase 6.9 capability-rich generate surface."""
        if stream:
            raise ChutesProviderError("generate_messages(stream=True) is not supported; use generate_stream")
        if deadline_s <= 0:
            raise ChutesProviderError("generate_messages: deadline_s must be positive")
        self._assert_tee_if_required()
        body_dict: dict[str, Any] = {
            "model": self.model,
            "messages": [message.to_openai() for message in messages],
            "max_tokens": max_tokens,
            "stream": False,
        }
        if temperature is not None:
            body_dict["temperature"] = temperature
        if top_p is not None:
            body_dict["top_p"] = top_p
        if seed is not None:
            body_dict["seed"] = seed
        if tools is not None:
            body_dict["tools"] = tools
        if response_format is not None:
            body_dict["response_format"] = response_format
        if reasoning_effort is not None:
            body_dict["reasoning_effort"] = reasoning_effort
        if cache_control is not None and cache_control.mode != "default":
            body_dict["cache_control"] = {"mode": cache_control.mode, "namespace": cache_control.namespace}

        started = time.monotonic()
        raw, status = self._post_raw(
            self.base_url,
            "/chat/completions",
            body=json.dumps(body_dict).encode("utf-8"),
            timeout=deadline_s,
            headers={"Content-Type": "application/json", "User-Agent": "xion-os/0.4.0 (+phase-6.9)"},
        )
        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        if not (200 <= status < 300):
            snippet = raw[:512].decode("utf-8", errors="replace")
            raise _error_for_status(status, f"chutes HTTP {status}: {_scrub(snippet, self._api_key)}")
        try:
            payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise UnknownProviderError(
                f"chutes response not valid JSON: {_scrub(str(e), self._api_key)}",
                provider_id=_PROVIDER_ID,
            ) from None
        return _parse_openai_completion(
            payload,
            model=self.model,
            latency_ms=latency_ms,
            provider_fingerprint=self.provider_fingerprint,
            tee_attestation=self.tee_attestation,
        )

    async def generate_stream(
        self,
        prompt: str,
        *,
        system: str | None,
        max_tokens: int,
        deadline_s: float,
    ) -> AsyncIterator[str | GenerationResult]:
        import httpx

        if deadline_s <= 0:
            raise ChutesProviderError("generate_stream: deadline_s must be positive")
        self._assert_tee_if_required()

        messages: list[dict[str, str]] = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = self._auth_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "text/event-stream"
        headers["User-Agent"] = "xion-os/0.4.0 (+phase-6.9)"

        started = time.monotonic()
        model_id = self.model
        usage_in = 0
        usage_out = 0
        finish = "stop"
        try:
            async with httpx.AsyncClient(timeout=deadline_s) as client:
                async with client.stream("POST", url, json=body, headers=headers) as resp:
                    if not (200 <= resp.status_code < 300):
                        raw_bytes = await resp.aread()
                        snippet = raw_bytes[:512].decode("utf-8", errors="replace")
                        raise _error_for_status(
                            resp.status_code,
                            f"chutes HTTP {resp.status_code}: {_scrub(snippet, self._api_key)}",
                        )
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        payload_text = line[len("data:"):].strip()
                        if payload_text == "[DONE]":
                            break
                        try:
                            event = json.loads(payload_text)
                        except json.JSONDecodeError:
                            continue
                        choices = event.get("choices") or []
                        if choices:
                            first = choices[0] or {}
                            delta = first.get("delta") or {}
                            content = delta.get("content")
                            if isinstance(content, str) and content:
                                yield content
                            finish_reason = first.get("finish_reason")
                            if finish_reason:
                                finish = str(finish_reason)
                        usage_obj = event.get("usage")
                        if isinstance(usage_obj, dict):
                            usage_in = int(usage_obj.get("prompt_tokens") or usage_in)
                            usage_out = int(usage_obj.get("completion_tokens") or usage_out)
                        returned_model = event.get("model")
                        if isinstance(returned_model, str) and returned_model:
                            model_id = returned_model
        except TimeoutError as e:
            raise ProviderTimeoutError(
                f"chutes stream transport timeout: {_scrub(str(e), self._api_key)}",
                provider_id=_PROVIDER_ID,
            ) from None
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(
                f"chutes stream transport timeout: {_scrub(str(e), self._api_key)}",
                provider_id=_PROVIDER_ID,
            ) from None
        except httpx.HTTPError as e:
            raise ProviderUnreachableError(
                f"chutes stream transport error: {_scrub(str(e), self._api_key)}",
                provider_id=_PROVIDER_ID,
            ) from None

        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        yield GenerationResult(
            text="",
            model_id=model_id,
            usage_in=usage_in,
            usage_out=usage_out,
            finish_reason=finish,
            latency_ms=latency_ms,
            provider_fingerprint=self.provider_fingerprint,
            model_version=model_id,
            tee_attestation=self.tee_attestation,
        )

    def _assert_tee_if_required(self) -> None:
        if self.tee_required and not self.health():
            raise ProviderUnreachableError(
                "chutes TEE-required model is not healthy or lacks confidential_compute=true",
                provider_id=_PROVIDER_ID,
            )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _get_json(self, base_url: str, path_suffix: str, *, timeout: float) -> dict[str, Any]:
        raw, status = self._request_raw(base_url, "GET", path_suffix, body=None, timeout=timeout, headers={})
        if not (200 <= status < 300):
            snippet = raw[:512].decode("utf-8", errors="replace")
            raise _error_for_status(status, f"chutes HTTP {status}: {_scrub(snippet, self._api_key)}")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise UnknownProviderError(
                f"chutes response not valid JSON: {_scrub(str(e), self._api_key)}",
                provider_id=_PROVIDER_ID,
            ) from None
        return payload if isinstance(payload, dict) else {}

    def _post_raw(
        self,
        base_url: str,
        path_suffix: str,
        *,
        body: bytes,
        timeout: float,
        headers: dict[str, str],
    ) -> tuple[bytes, int]:
        return self._request_raw(base_url, "POST", path_suffix, body=body, timeout=timeout, headers=headers)

    def _request_raw(
        self,
        base_url: str,
        method: str,
        path_suffix: str,
        *,
        body: bytes | None,
        timeout: float,
        headers: dict[str, str],
    ) -> tuple[bytes, int]:
        parsed = urlparse(base_url)
        request_headers = self._auth_headers()
        request_headers.update(headers)
        path = (parsed.path.rstrip("/") or "") + path_suffix
        try:
            conn = self._open_connection(parsed, timeout=timeout)
            try:
                conn.request(method, path, body=body, headers=request_headers)
                resp = conn.getresponse()
                return resp.read(), resp.status
            finally:
                conn.close()
        except TimeoutError as e:
            raise ProviderTimeoutError(
                f"chutes transport timeout: {_scrub(str(e), self._api_key)}",
                provider_id=_PROVIDER_ID,
            ) from None
        except (OSError, http.client.HTTPException) as e:
            raise ProviderUnreachableError(
                f"chutes transport error: {_scrub(str(e), self._api_key)}",
                provider_id=_PROVIDER_ID,
            ) from None

    @staticmethod
    def _open_connection(parsed: Any, *, timeout: float) -> http.client.HTTPConnection:
        host = parsed.hostname
        port = parsed.port
        if parsed.scheme == "https":
            return http.client.HTTPSConnection(host, port=port, timeout=timeout)
        return http.client.HTTPConnection(host, port=port, timeout=timeout)


def _parse_openai_completion(
    payload: dict[str, Any],
    *,
    model: str,
    latency_ms: int,
    provider_fingerprint: str,
    tee_attestation: str | None,
) -> GenerationResult:
    choices = payload.get("choices") or []
    text = ""
    finish = "stop"
    if choices:
        first = choices[0] or {}
        message = first.get("message") or {}
        text = str(message.get("content") or "")
        finish = str(first.get("finish_reason") or "stop")
    usage = payload.get("usage") or {}
    usage_in = int(usage.get("prompt_tokens") or 0)
    usage_out = int(usage.get("completion_tokens") or 0)
    reasoning_tokens = int(
        (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    )
    returned_model = str(payload.get("model") or model)
    return GenerationResult(
        text=text,
        model_id=returned_model,
        usage_in=usage_in,
        usage_out=usage_out,
        finish_reason=finish,
        latency_ms=latency_ms,
        provider_fingerprint=provider_fingerprint,
        model_version=returned_model,
        reasoning_tokens=reasoning_tokens,
        tee_attestation=tee_attestation,
    )


__all__ = ["ChutesGenerativeProvider", "ChutesProviderError", "_scrub"]
