"""Ollama (local open-weights) generative provider (Phase 5g-i).

Doctrine anchor: ``docs/26-INFERENCE-POLICY.md`` § "The floor-model
choice (Gemma 4 E4B-it)".

Talks to an Ollama daemon over ``XION_OLLAMA_URL`` (default
``http://localhost:11434`` for local D2; Akash deployments point this at the
private ``xion-ollama`` sidecar), using stdlib ``http.client``. The provider's
``category`` is ``"open_weights_self_hostable"`` — this is the provider that
holds the Invariant-17 floor at runtime. It is NOT the ``xion-verify
inference-sovereignty`` target; that verifier walks the manifest's
structural sentinel pins. The runtime floor is held by ``health()``
returning True, not by any hash check here.

Two checks in ``health()`` together determine reachability:
  1. The daemon responds to ``GET /api/tags``.
  2. The configured floor model (``XION_OLLAMA_FLOOR_MODEL``, default
     ``gemma3:4b``) is listed in that response.

Either check failing returns False. A True result means: the daemon
is up and the configured deployment has pulled the pinned floor model.
This satisfies Invariant 17 clause 2(iv)'s "health-checkable locally
without a third-party API call" — in production-style Akash posture the
"local" boundary is the private deployment network, not the operator laptop.
"""

from __future__ import annotations

import http.client
import json
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, ClassVar
from urllib.parse import urlparse

from orchestrator.inference_router.provider import (
    GenerationResult,
    ModerationRefusalError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnreachableError,
    UnknownProviderError,
)
from orchestrator.inference_router.router import Category


class OllamaProviderError(ProviderError):
    """Raised on construction-time validation failures.

    Phase 5g-vii note. Pre-5g-vii this class was the single exception
    type raised from every Ollama-side failure path. Phase 5g-vii
    split generate-site failures into the typed ``ProviderError``
    subclasses per doctrine property P5 in
    ``docs/26-INFERENCE-POLICY.md``. This class is retained for
    construction-time validation (a malformed ``XION_OLLAMA_URL``)
    and for backward compatibility: it now extends ``ProviderError``,
    so ``except ProviderError:`` catches both this class and the
    typed generate-site subclasses.

    Ollama is a loopback daemon with no billing, no upstream quota,
    and no cross-region routing — so ``InsufficientCreditsError`` and
    ``RateLimitedUpstreamError`` never apply. The Ollama paths emit
    ``ProviderTimeoutError``, ``ProviderUnreachableError``,
    ``ModerationRefusalError`` (for local guardrail models that
    refuse), and ``UnknownProviderError`` (residual).
    """

    failure_reason_class = "unknown_provider_error"


_PROVIDER_ID = "ollama"
_DEFAULT_URL = "http://localhost:11434"
_DEFAULT_MODEL = "gemma4:e4b-it-q4_K_M"
_HEALTH_CACHE_TTL_S = 30.0
_HEALTH_TIMEOUT_S = 3.0


@dataclass
class OllamaGenerativeProvider:
    """Local open-weights floor provider (Ollama).

    Registered unconditionally at lifespan startup; its ``health()``
    reflects whether the Ollama daemon is actually reachable and the
    floor model is pulled. An absent or unhealthy daemon does not
    crash registration — but does make the Router's ``bootstrap()``
    refuse, which is what Invariant 17 clause 3 requires.
    """

    provider_id: str = "ollama"
    category: ClassVar[Category] = "open_weights_self_hostable"

    base_url: str = field(default_factory=lambda: os.environ.get(
        "XION_OLLAMA_URL", _DEFAULT_URL,
    ))
    model: str = field(default_factory=lambda: os.environ.get(
        "XION_OLLAMA_FLOOR_MODEL", _DEFAULT_MODEL,
    ))

    _cached_health: bool = field(default=False, init=False, repr=False)
    _cached_health_at: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise OllamaProviderError(
                f"OllamaGenerativeProvider: XION_OLLAMA_URL is not a valid "
                f"http(s) URL: {self.base_url!r}"
            )

    def health(self) -> bool:
        """Probe ``GET /api/tags`` and check the floor model is present.

        Cached 30s. The cache is deliberately short because
        Ollama is loopback and the check is cheap; operators who start
        or stop the daemon during dev expect the next ``/chat`` to
        notice promptly.
        """
        now = time.monotonic()
        if now - self._cached_health_at < _HEALTH_CACHE_TTL_S:
            return self._cached_health

        healthy = False
        try:
            parsed = urlparse(self.base_url)
            conn = self._open_connection(parsed, timeout=_HEALTH_TIMEOUT_S)
            try:
                conn.request("GET", "/api/tags")
                resp = conn.getresponse()
                raw = resp.read()
                if 200 <= resp.status < 300:
                    try:
                        tags = json.loads(raw.decode("utf-8"))
                        models = tags.get("models") or []
                        names = [str(m.get("name") or m.get("model") or "") for m in models]
                        healthy = self.model in names or any(
                            n.split(":", 1)[0] == self.model.split(":", 1)[0]
                            and n == self.model
                            for n in names
                        )
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        healthy = False
            finally:
                conn.close()
        except (TimeoutError, OSError, http.client.HTTPException):
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
        """Call Ollama's ``/api/generate`` synchronously.

        Uses ``stream=False`` so the daemon returns a single JSON blob
        instead of the newline-delimited stream. Max tokens maps to
        ``options.num_predict``.
        """
        if deadline_s <= 0:
            raise OllamaProviderError("generate: deadline_s must be positive")

        body_dict: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": int(max_tokens)},
        }
        if system is not None:
            body_dict["system"] = system
        body = json.dumps(body_dict).encode("utf-8")

        parsed = urlparse(self.base_url)

        started = time.monotonic()
        try:
            conn = self._open_connection(parsed, timeout=deadline_s)
            try:
                conn.request(
                    "POST",
                    "/api/generate",
                    body=body,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "xion-os/0.2.0 (+phase-5g-i)",
                    },
                )
                resp = conn.getresponse()
                raw = resp.read()
                status = resp.status
            finally:
                conn.close()
        except TimeoutError as e:
            raise ProviderTimeoutError(
                f"ollama transport timeout: {e}",
                provider_id=_PROVIDER_ID,
            ) from None
        except (OSError, http.client.HTTPException) as e:
            raise ProviderUnreachableError(
                f"ollama transport error: {e}",
                provider_id=_PROVIDER_ID,
            ) from None

        latency_ms = max(0, int((time.monotonic() - started) * 1000))

        if not (200 <= status < 300):
            snippet = raw[:512].decode("utf-8", errors="replace")
            if status == 403:
                raise ModerationRefusalError(
                    f"ollama HTTP {status}: {snippet}",
                    provider_id=_PROVIDER_ID,
                )
            if 500 <= status < 600:
                raise ProviderUnreachableError(
                    f"ollama HTTP {status}: {snippet}",
                    provider_id=_PROVIDER_ID,
                )
            raise UnknownProviderError(
                f"ollama HTTP {status}: {snippet}",
                provider_id=_PROVIDER_ID,
            )

        try:
            payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise UnknownProviderError(
                f"ollama response not valid JSON: {e}",
                provider_id=_PROVIDER_ID,
            ) from None

        text = str(payload.get("response") or "")
        finish = "stop" if bool(payload.get("done", True)) else "length"
        usage_in = int(payload.get("prompt_eval_count") or 0)
        usage_out = int(payload.get("eval_count") or 0)
        returned_model = str(payload.get("model") or self.model)

        return GenerationResult(
            text=text,
            model_id=returned_model,
            usage_in=usage_in,
            usage_out=usage_out,
            finish_reason=finish,
            latency_ms=latency_ms,
        )

    async def generate_stream(
        self,
        prompt: str,
        *,
        system: str | None,
        max_tokens: int,
        deadline_s: float,
    ) -> AsyncIterator[str | GenerationResult]:
        """Phase 5g-ii streaming generation via Ollama's NDJSON stream.

        Ollama emits one JSON object per line with a ``response`` field
        carrying the delta text and a ``done`` bool that flips True on
        the final line (which also carries ``prompt_eval_count`` and
        ``eval_count`` for usage). Uses ``httpx.AsyncClient`` so an
        ``asyncio.CancelledError`` on the handler side closes the
        upstream HTTP connection promptly.

        Falls back to the same ``GenerationResult`` terminal convention
        as the Chutes streaming path: yields ``str`` chunks, then
        exactly one ``GenerationResult`` with ``text=""`` and the full
        metadata.
        """
        import httpx

        if deadline_s <= 0:
            raise OllamaProviderError("generate_stream: deadline_s must be positive")

        body_dict: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_predict": int(max_tokens)},
        }
        if system is not None:
            body_dict["system"] = system

        url = self.base_url.rstrip("/") + "/api/generate"

        started = time.monotonic()
        model_id = self.model
        usage_in = 0
        usage_out = 0
        finish = "stop"

        try:
            async with httpx.AsyncClient(timeout=deadline_s) as client, client.stream(
                "POST",
                url,
                json=body_dict,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "xion-os/0.3.0 (+phase-5g-ii)",
                },
            ) as resp:
                if not (200 <= resp.status_code < 300):
                    raw_bytes = await resp.aread()
                    snippet = raw_bytes[:512].decode("utf-8", errors="replace")
                    status = resp.status_code
                    if status == 403:
                        raise ModerationRefusalError(
                            f"ollama HTTP {status}: {snippet}",
                            provider_id=_PROVIDER_ID,
                        )
                    if 500 <= status < 600:
                        raise ProviderUnreachableError(
                            f"ollama HTTP {status}: {snippet}",
                            provider_id=_PROVIDER_ID,
                        )
                    raise UnknownProviderError(
                        f"ollama HTTP {status}: {snippet}",
                        provider_id=_PROVIDER_ID,
                    )
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    chunk = event.get("response")
                    if isinstance(chunk, str) and chunk:
                        yield chunk
                    if event.get("done"):
                        usage_in = int(event.get("prompt_eval_count") or 0)
                        usage_out = int(event.get("eval_count") or 0)
                        returned = event.get("model")
                        if isinstance(returned, str) and returned:
                            model_id = returned
                        finish = "length" if event.get("done_reason") == "length" else "stop"
                        break
        except TimeoutError as e:
            raise ProviderTimeoutError(
                f"ollama stream transport timeout: {e}",
                provider_id=_PROVIDER_ID,
            ) from None
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(
                f"ollama stream transport timeout: {e}",
                provider_id=_PROVIDER_ID,
            ) from None
        except httpx.HTTPError as e:
            raise ProviderUnreachableError(
                f"ollama stream transport error: {e}",
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
        )

    @staticmethod
    def _open_connection(
        parsed: Any,
        *,
        timeout: float,
    ) -> http.client.HTTPConnection:
        host = parsed.hostname
        port = parsed.port
        if parsed.scheme == "https":
            return http.client.HTTPSConnection(host, port=port, timeout=timeout)
        return http.client.HTTPConnection(host, port=port, timeout=timeout)


__all__ = [
    "OllamaGenerativeProvider",
    "OllamaProviderError",
]
