"""OpenRouter hosted-gateway generative provider (Phase 5g-i.1).

Doctrine anchor: ``docs/26-INFERENCE-POLICY.md`` § "The hosted-provider
choice (OpenRouter gateway + `moonshotai/kimi-k2` default model)" and
§ "Gateway vs direct (a vendor-of-vendors honest accounting)".

Hits OpenRouter's OpenAI-compatible ``/v1/chat/completions`` endpoint
via stdlib ``http.client`` — no third-party SDK, no new dependency.
The implementation is ~200 lines of the Protocol's contract plus
careful credential scrubbing and two optional app-identity headers
OpenRouter uses for developer-portal attribution.

Why OpenRouter, not Moonshot-direct (Phase 5g-i's shipped shape).
OpenRouter is a vendor-of-vendors: it routes requests to upstream model
providers (Moonshot, Anthropic, OpenAI, Google, and others) under one
OpenAI-compatible API and one credential. Switching hosted models is
now a one-env-var change (``XION_OPENROUTER_MODEL``), which unblocks
(a) Phase 5g-iii's ``GET /pricing`` reading OpenRouter's catalog, and
(b) future ``KW-INFER-001`` pay-down work that lands a multi-model
failover list without a code change. The honest trust-surface cost
(OpenRouter now sits inside the Covenant-relevant path as an additional
third party) is named in ``docs/26-INFERENCE-POLICY.md`` § "Gateway vs
direct".

Credential discipline. The API key lives in ``XION_OPENROUTER_API_KEY``;
this module:
  - NEVER logs the key, the ``Authorization`` header, or any request
    body that contains it;
  - raises ``OpenRouterProviderError`` with a sanitised message when
    the endpoint returns non-200 (status + truncated body, scrubbed of
    any key material);
  - scrubs bare ``sk-or-...`` tokens (OpenRouter's key format) from
    every outward error message — not just the exact key instance
    this provider holds — so a leaked key-shape fragment from an
    upstream error payload does not ride out to a user in an envelope;
  - keeps the key in a private attribute with no accessor.

App-identity headers. OpenRouter accepts two optional headers —
``HTTP-Referer`` (a URL attributing traffic to the calling app) and
``X-Title`` (a human-readable app name). These do NOT authenticate the
request; they feed OpenRouter's developer-portal analytics. Setting
them is a courtesy, not a security control. ``XION_OPENROUTER_REFERER``
(default empty; the header is suppressed when empty) and
``XION_OPENROUTER_APP_NAME`` (default ``xion-os``) configure them.

Health check. ``health()`` issues a cheap ``GET /models`` against the
configured base URL with a short timeout. The result is cached for 60
seconds so the Chat Surface does not hammer the gateway on every turn
while the lifespan's startup bootstrap has already confirmed
reachability. If the cache is stale, one health probe runs
synchronously; if that probe fails, ``health()`` returns False and the
Router's ``hosted_api_first`` policy falls through to the floor.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar
from urllib.parse import urlparse

from orchestrator.inference_router.provider import GenerationResult
from orchestrator.inference_router.router import Category


class OpenRouterProviderError(RuntimeError):
    """Raised on non-200 responses or transport errors.

    The message is scrubbed of API-key value, Authorization-header
    value, and any bare ``sk-or-...`` token before construction; callers
    may surface the message to end users via ``ProviderErrorEnvelope``
    without leaking credentials.
    """


_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "moonshotai/kimi-k2"
_DEFAULT_APP_NAME = "xion-os"
_HEALTH_CACHE_TTL_S = 60.0
_HEALTH_TIMEOUT_S = 5.0

_RE_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE)
# OpenRouter keys have shape ``sk-or-v1-<hex>`` (current) or ``sk-or-<hex>``
# (legacy). The generic prefix ``sk-or-`` plus [A-Za-z0-9_\-\.]+ covers both.
# This is defence in depth: if an upstream error payload echoes a fragment of
# a key that is not the exact instance this provider holds, it still gets
# redacted before it rides out to a user in an envelope.
_RE_OPENROUTER_KEY = re.compile(r"sk-or-[A-Za-z0-9_\-\.]+")


def _scrub(msg: str, api_key: str) -> str:
    """Scrub the API key, Authorization header values, and any bare
    ``sk-or-...`` token from a string.

    Defence in depth: even if the key itself or a ``Bearer <key>`` token
    sneaks into an upstream error payload, this scrubber strips it
    before the message leaves the provider. The ``sk-or-...`` pattern
    catches leaked fragments that are not the exact key this provider
    was constructed with (e.g., a colocation's logged key prefix).
    """
    out = msg
    if api_key:
        out = out.replace(api_key, "<api_key_redacted>")
    out = _RE_BEARER.sub("Bearer <redacted>", out)
    out = _RE_OPENROUTER_KEY.sub("<api_key_redacted>", out)
    return out


@dataclass
class OpenRouterGenerativeProvider:
    """OpenRouter hosted-gateway generative provider.

    Construction reads from the environment; tests may override via
    explicit kwargs. ``provider_id`` is pinned to ``"openrouter"`` so
    the Router's log lines, health reports, and ``ChatResponse.model_id``
    surface a stable string regardless of which upstream-model slug is
    selected. ``ChatResponse.model_id`` still carries the underlying
    slug OpenRouter returns (e.g., ``moonshotai/kimi-k2``), so the
    auditor can see which upstream model served each turn.
    """

    provider_id: str = "openrouter"
    category: ClassVar[Category] = "hosted_api"

    base_url: str = field(default_factory=lambda: os.environ.get(
        "XION_OPENROUTER_BASE_URL", _DEFAULT_BASE_URL,
    ))
    model: str = field(default_factory=lambda: os.environ.get(
        "XION_OPENROUTER_MODEL", _DEFAULT_MODEL,
    ))
    referer: str = field(default_factory=lambda: os.environ.get(
        "XION_OPENROUTER_REFERER", "",
    ))
    app_name: str = field(default_factory=lambda: os.environ.get(
        "XION_OPENROUTER_APP_NAME", _DEFAULT_APP_NAME,
    ))
    _api_key: str = field(default_factory=lambda: os.environ.get(
        "XION_OPENROUTER_API_KEY", "",
    ), repr=False)

    _cached_health: bool = field(default=False, init=False, repr=False)
    _cached_health_at: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self._api_key:
            raise OpenRouterProviderError(
                "OpenRouterGenerativeProvider requires XION_OPENROUTER_API_KEY "
                "to be set. The provider must NOT register without a key — see "
                "docs/26-INFERENCE-POLICY.md § 'The hosted-provider choice'."
            )
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise OpenRouterProviderError(
                f"OpenRouterGenerativeProvider: XION_OPENROUTER_BASE_URL is not "
                f"a valid http(s) URL: {self.base_url!r}"
            )

    def health(self) -> bool:
        """Best-effort reachability check against ``GET /models``.

        Cached 60s. A stale cache forces one synchronous probe. A failed
        probe returns False and the cache is updated (including the
        False value) so subsequent calls within the TTL do not repeat
        the outbound request.
        """
        now = time.monotonic()
        if now - self._cached_health_at < _HEALTH_CACHE_TTL_S:
            return self._cached_health

        healthy = False
        try:
            parsed = urlparse(self.base_url)
            conn = self._open_connection(parsed, timeout=_HEALTH_TIMEOUT_S)
            try:
                path = (parsed.path.rstrip("/") or "") + "/models"
                conn.request(
                    "GET",
                    path,
                    headers=self._auth_headers(),
                )
                resp = conn.getresponse()
                _ = resp.read()
                healthy = 200 <= resp.status < 300
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
        """Issue an OpenAI-compatible ``/chat/completions`` request
        through the OpenRouter gateway.

        Blocks until the response is in hand or the deadline elapses.
        Caller runs this in ``asyncio.to_thread`` so the event loop is
        not pinned on the sync HTTP call.
        """
        if deadline_s <= 0:
            raise OpenRouterProviderError("generate: deadline_s must be positive")

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

        parsed = urlparse(self.base_url)
        path = (parsed.path.rstrip("/") or "") + "/chat/completions"

        headers = self._auth_headers()
        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = "xion-os/0.2.0 (+phase-5g-i.1)"

        started = time.monotonic()
        try:
            conn = self._open_connection(parsed, timeout=deadline_s)
            try:
                conn.request("POST", path, body=body, headers=headers)
                resp = conn.getresponse()
                raw = resp.read()
                status = resp.status
            finally:
                conn.close()
        except (TimeoutError, OSError, http.client.HTTPException) as e:
            raise OpenRouterProviderError(
                f"openrouter transport error: {_scrub(str(e), self._api_key)}"
            ) from None

        latency_ms = max(0, int((time.monotonic() - started) * 1000))

        if not (200 <= status < 300):
            snippet = raw[:512].decode("utf-8", errors="replace")
            raise OpenRouterProviderError(
                f"openrouter HTTP {status}: {_scrub(snippet, self._api_key)}"
            )

        try:
            payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise OpenRouterProviderError(
                f"openrouter response not valid JSON: "
                f"{_scrub(str(e), self._api_key)}"
            ) from None

        return _parse_openai_completion(payload, model=self.model, latency_ms=latency_ms)

    def _auth_headers(self) -> dict[str, str]:
        """Assemble auth + optional app-identity headers.

        ``HTTP-Referer`` is suppressed when empty — sending an empty
        referer can trigger OpenRouter's analytics pipeline to attribute
        traffic to the wrong app slot. ``X-Title`` always ships with
        its configured or default value; the default ``xion-os`` is
        harmless and identifies the traffic correctly even in
        development.
        """
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "X-Title": self.app_name or _DEFAULT_APP_NAME,
        }
        if self.referer:
            headers["HTTP-Referer"] = self.referer
        return headers

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


def _parse_openai_completion(
    payload: dict[str, Any],
    *,
    model: str,
    latency_ms: int,
) -> GenerationResult:
    """Parse an OpenAI-compatible chat-completions response into a
    ``GenerationResult``. Defensive — any missing field yields a
    sensible default rather than raising, because gateway quirks
    (OpenRouter massages some upstream responses and passes others
    through verbatim) are common and the Chat handler already has a
    full set of error paths for the empty-text case (it maps to
    egress-refused by convention)."""
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

    returned_model = str(payload.get("model") or model)

    return GenerationResult(
        text=text,
        model_id=returned_model,
        usage_in=usage_in,
        usage_out=usage_out,
        finish_reason=finish,
        latency_ms=latency_ms,
    )


__all__ = [
    "OpenRouterGenerativeProvider",
    "OpenRouterProviderError",
]
