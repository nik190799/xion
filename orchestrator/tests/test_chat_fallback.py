"""Tests for the Phase 5g-vii chat-handler fallback loop.

Doctrine anchor: `docs/26-INFERENCE-POLICY.md` § "Provider fallback
semantics (Phase 5g-vii)" P1-P5.

Coverage:

    Typed failure class surfacing (P4)
      - Each of the six P5 classes, raised by the hosted provider with
        no floor fallback wired, surfaces verbatim in the 503
        ProviderErrorEnvelope.reason field.

    Automatic hosted -> floor fallback (P1)
      - A hosted provider that raises InsufficientCreditsError falls
        through to a healthy floor which serves the turn 200 OK.
      - A hosted provider that raises ProviderTimeoutError-equivalent
        (TimeoutError) falls through to the floor.

    REQUEST_LEDGER v2 per-attempt writes (P3)
      - A single-attempt successful turn writes exactly one v2 row with
        outcome="success".
      - A two-attempt hosted-fail + floor-success writes two v2 rows
        sharing a chat_turn_id, attempt_index 0 and 1.
      - An all-failure turn writes one v2 row per attempted provider
        with outcome="failure" and the correct failure_reason_class.

    Policy-mode boundary (P2)
      - `open_weights_only` never calls the hosted provider, regardless
        of hosted health.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi.testclient import TestClient

from orchestrator.inference_router import Category, GenerationResult
from orchestrator.inference_router.provider import (
    FAILURE_REASON_CLASSES,
    InsufficientCreditsError,
    ModerationRefusalError,
    ProviderTimeoutError,
    ProviderUnreachableError,
    RateLimitedUpstreamError,
    UnknownProviderError,
)
from orchestrator.relay.ledger import iter_rows


@dataclass
class _FakeProvider:
    provider_id: str = "fake-hosted"
    category: Category = "hosted_api"
    response_text: str = "ok text"
    model_id_echoed: str = "fake-model"
    is_healthy: bool = True
    raise_on_generate: Exception | None = None
    sleep_s: float = 0.0
    calls: list[dict[str, Any]] = field(default_factory=list)

    def health(self) -> bool:
        return self.is_healthy

    def generate(
        self,
        prompt: str,
        *,
        system: str | None,
        max_tokens: int,
        deadline_s: float,
    ) -> GenerationResult:
        import time

        self.calls.append({"prompt": prompt})
        if self.sleep_s > 0:
            time.sleep(self.sleep_s)
        if self.raise_on_generate is not None:
            raise self.raise_on_generate
        return GenerationResult(
            text=self.response_text,
            model_id=self.model_id_echoed,
            usage_in=1,
            usage_out=1,
            finish_reason="stop",
            latency_ms=1,
        )


def _floor(text: str = "floor says hi") -> _FakeProvider:
    return _FakeProvider(
        provider_id="sentinel-llm-v0",
        category="open_weights_self_hostable",
        response_text=text,
        model_id_echoed="sentinel-llm-v0",
    )


def _request_ledger_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "REQUEST_LEDGER.jsonl"
    monkeypatch.setenv("XION_REQUEST_LEDGER", str(path))
    return path


# ---- P4: typed class surfacing ------------------------------------------

_P4_CASES: list[tuple[Exception, str]] = [
    (InsufficientCreditsError("402", provider_id="hosted"), "insufficient_credits"),
    (RateLimitedUpstreamError("429", provider_id="hosted"), "rate_limited_upstream"),
    (ProviderUnreachableError("conn refused", provider_id="hosted"), "provider_unreachable"),
    (ProviderTimeoutError("deadline", provider_id="hosted"), "timeout"),
    (ModerationRefusalError("filter", provider_id="hosted"), "moderation_refusal"),
    (UnknownProviderError("???", provider_id="hosted"), "unknown_provider_error"),
]


@pytest.mark.parametrize("exc, expected_reason", _P4_CASES)
def test_typed_failure_class_surfaces_in_envelope(
    exc: Exception,
    expected_reason: str,
    app_factory: Callable[..., Any],
) -> None:
    """P4: when the only provider raises a typed ProviderError, the
    envelope carries that failure_reason_class verbatim.

    No floor provider is registered (policy `open_weights_only` would
    trap the floor; we use `hosted_api_first` with no floor fallback
    wired — the floor stub is registered but cannot generate, so the
    loop sees only the hosted provider).
    """
    hosted = _FakeProvider(raise_on_generate=exc)
    app = app_factory(generative_provider=hosted)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 503, r.text
    assert r.json()["reason"] == expected_reason


def test_p4_coverage_is_complete_for_frozen_p5_enum() -> None:
    """Meta-test: the parametrized cases above cover every P5 class.

    If a new class is added to FAILURE_REASON_CLASSES without adding
    a case here, the test fails loudly — forcing the doctrine-to-test
    coupling that the P5 frozen-enumeration requires.
    """
    covered = {reason for _, reason in _P4_CASES}
    assert covered == set(FAILURE_REASON_CLASSES)


# ---- P1: automatic hosted -> floor fallback -----------------------------


def test_hosted_insufficient_credits_falls_through_to_floor(
    app_factory: Callable[..., Any],
) -> None:
    """P1: InsufficientCreditsError from hosted must not 503 the turn;
    the floor is tried next and serves 200.
    """
    hosted = _FakeProvider(
        raise_on_generate=InsufficientCreditsError("402", provider_id="hosted")
    )
    floor = _floor(text="floor served")
    app = app_factory(generative_provider=hosted, floor_stub_id="sentinel-llm-v0")
    app.state.test_router.register(floor)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "floor served"
    assert len(hosted.calls) == 1
    assert len(floor.calls) == 1


def test_hosted_timeout_falls_through_to_floor(
    app_factory: Callable[..., Any],
) -> None:
    """P1: a wall-clock timeout (TimeoutError via asyncio.wait_for) on
    hosted must not 503; floor is tried next. The handler classifies
    this as `failure_reason_class="timeout"` on the hosted attempt row.
    """
    hosted = _FakeProvider(sleep_s=2.0)
    floor = _floor(text="floor served after hosted timeout")
    app = app_factory(
        generative_provider=hosted,
        chat_deadline_s=0.3,
    )
    app.state.test_router.register(floor)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "floor served after hosted timeout"


# ---- P3: REQUEST_LEDGER v2 per-attempt rows -----------------------------


def test_single_attempt_success_writes_one_v2_row(
    app_factory: Callable[..., Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _request_ledger_path(tmp_path, monkeypatch)
    hosted = _FakeProvider(response_text="hello")
    app = app_factory(generative_provider=hosted)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 200, r.text
    v2_rows = [row for row in iter_rows(path) if row["schema_version"] == 2]
    assert len(v2_rows) == 1
    row = v2_rows[0]
    assert row["outcome"] == "success"
    assert row["failure_reason_class"] is None
    assert row["attempt_index"] == 0
    assert row["provider_id"] == "fake-hosted"


def test_two_attempt_hosted_fail_floor_success_writes_two_v2_rows(
    app_factory: Callable[..., Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _request_ledger_path(tmp_path, monkeypatch)
    hosted = _FakeProvider(
        raise_on_generate=InsufficientCreditsError("402", provider_id="hosted")
    )
    floor = _floor(text="floor served")
    app = app_factory(generative_provider=hosted, floor_stub_id="sentinel-llm-v0")
    app.state.test_router.register(floor)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 200, r.text
    v2_rows = [row for row in iter_rows(path) if row["schema_version"] == 2]
    assert len(v2_rows) == 2
    # Shared chat_turn_id:
    assert v2_rows[0]["chat_turn_id"] == v2_rows[1]["chat_turn_id"]
    # Ordering by attempt_index:
    v2_rows.sort(key=lambda r: r["attempt_index"])
    assert v2_rows[0]["attempt_index"] == 0
    assert v2_rows[0]["outcome"] == "failure"
    assert v2_rows[0]["failure_reason_class"] == "insufficient_credits"
    assert v2_rows[1]["attempt_index"] == 1
    assert v2_rows[1]["outcome"] == "success"
    assert v2_rows[1]["failure_reason_class"] is None


def test_all_fail_turn_surfaces_last_class_and_writes_two_failure_rows(
    app_factory: Callable[..., Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P4 + P3: when every attempt fails, the envelope carries the
    LAST attempt's failure_reason_class, and the ledger carries one
    row per attempted provider."""
    path = _request_ledger_path(tmp_path, monkeypatch)
    hosted = _FakeProvider(
        raise_on_generate=InsufficientCreditsError("402", provider_id="hosted")
    )
    floor = _floor()
    floor.raise_on_generate = ProviderUnreachableError(
        "ollama down", provider_id="sentinel-llm-v0"
    )
    app = app_factory(generative_provider=hosted, floor_stub_id="sentinel-llm-v0")
    app.state.test_router.register(floor)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 503, r.text
    # Last failure class is the floor's, not the hosted's:
    assert r.json()["reason"] == "provider_unreachable"
    v2_rows = [row for row in iter_rows(path) if row["schema_version"] == 2]
    assert len(v2_rows) == 2
    v2_rows.sort(key=lambda r: r["attempt_index"])
    assert [row["failure_reason_class"] for row in v2_rows] == [
        "insufficient_credits",
        "provider_unreachable",
    ]


# ---- P2: open_weights_only never attempts hosted ------------------------


def test_open_weights_only_never_attempts_hosted_on_fallback_loop(
    app_factory: Callable[..., Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _request_ledger_path(tmp_path, monkeypatch)
    hosted = _FakeProvider(response_text="hosted must never speak")
    floor = _floor(text="floor only")
    app = app_factory(
        generative_provider=hosted,
        policy_mode="open_weights_only",
    )
    app.state.test_router.register(floor)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "cutover"})
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "floor only"
    assert len(hosted.calls) == 0
    assert len(floor.calls) == 1
    v2_rows = [row for row in iter_rows(path) if row["schema_version"] == 2]
    assert len(v2_rows) == 1
    assert v2_rows[0]["provider_id"] == "sentinel-llm-v0"
