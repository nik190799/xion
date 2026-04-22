"""Hermetic tests for the Phase 5g-i Chat Surface.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Surface (Phase 5g-i)".

Coverage (21 tests):

    Envelope contracts
      - ChatRequest rejects extra fields and empty message
      - ChatResponse allowlist (content-free guarantee)
      - RefusalEnvelope allowlist (content-free guarantee)
      - NoFloorEnvelope / ProviderErrorEnvelope allowlists

    Happy path
      - POST /chat returns 200 with the moderated text
      - Happy path writes two SAFETY rows (ingress + egress) under two
        correlation_ids, with the egress correlation_id returned

    Ingress-refused path
      - A Principle-1 CSAM-shaped ingress input returns 451 stage=ingress
      - Generation is NOT attempted on ingress refusal

    Egress-refused path
      - A provider whose output is a Principle-1-shaped string returns
        451 stage=egress with the egress correlation_id

    Empty-candidate path
      - A provider returning empty text returns 451
        reason=provider_empty_candidate

    No-floor path
      - A router constructed without a floor provider returns 503
        NoFloorEnvelope with reason=open_weights_floor_unsatisfied

    No-healthy-provider path
      - A router with a registered floor stub but no ``generate``-capable
        provider returns 503 ProviderErrorEnvelope
      - OpenWeightsFloorStub alone is never selected for ``generate``

    Provider error paths
      - Provider raising surfaces as 503 ProviderErrorEnvelope
      - Provider exceeding deadline surfaces as 503 ProviderErrorEnvelope

    Policy modes
      - ``hosted_api_first`` with healthy hosted picks hosted
      - ``hosted_api_first`` with unhealthy hosted falls through to floor
      - ``open_weights_only`` with a healthy hosted NEVER picks hosted

    Secret hygiene
      - Kimi provider scrubs the API key from transport-error messages
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi.testclient import TestClient
from pydantic import ValidationError

from orchestrator.api.models import (
    ChatRequest,
    ChatResponse,
    NoFloorEnvelope,
    ProviderErrorEnvelope,
    RefusalEnvelope,
    UsageEnvelope,
)
from orchestrator.inference_router import Category, GenerationResult

# -------- Fake generative providers ------------------------------------------


@dataclass
class _FakeProvider:
    """Minimal GenerativeProvider double for hermetic Chat tests.

    Default is a healthy hosted-API provider that echoes a deterministic
    canned response. Fields let each test override behaviour surgically.
    """

    provider_id: str = "fake-hosted"
    category: Category = "hosted_api"
    response_text: str = "a sentence about gardens and libraries"
    model_id_echoed: str = "fake-model-v1"
    usage_in_val: int = 12
    usage_out_val: int = 18
    finish: str = "stop"
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

        self.calls.append({
            "prompt": prompt,
            "system": system,
            "max_tokens": max_tokens,
            "deadline_s": deadline_s,
        })
        if self.sleep_s > 0:
            time.sleep(self.sleep_s)
        if self.raise_on_generate is not None:
            raise self.raise_on_generate
        return GenerationResult(
            text=self.response_text,
            model_id=self.model_id_echoed,
            usage_in=self.usage_in_val,
            usage_out=self.usage_out_val,
            finish_reason=self.finish,
            latency_ms=7,
        )


def _floor_provider(response_text: str = "floor says hi") -> _FakeProvider:
    return _FakeProvider(
        provider_id="sentinel-llm-v0",
        category="open_weights_self_hostable",
        response_text=response_text,
        model_id_echoed="sentinel-llm-v0",
    )


# -------- Envelope contracts --------------------------------------------------


def test_chat_request_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="hello", secret_debug_flag="yes")  # type: ignore[call-arg]


def test_chat_request_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_response_field_allowlist() -> None:
    """Content-free guarantee: ChatResponse has EXACTLY these fields."""
    expected = {"role", "text", "model_id", "usage", "correlation_id"}
    assert set(ChatResponse.model_fields.keys()) == expected


def test_refusal_envelope_field_allowlist() -> None:
    """Content-free guarantee: RefusalEnvelope carries no content."""
    expected = {"stage", "principle_code", "reason", "correlation_id"}
    assert set(RefusalEnvelope.model_fields.keys()) == expected


def test_no_floor_and_provider_error_envelope_allowlists() -> None:
    assert set(NoFloorEnvelope.model_fields.keys()) == {
        "reason", "missing_capability", "manifest_expected_id",
    }
    assert set(ProviderErrorEnvelope.model_fields.keys()) == {
        "reason", "correlation_id",
    }


def test_chat_response_validates_roundtrip() -> None:
    r = ChatResponse(
        role="xion",
        text="hello",
        model_id="m",
        usage=UsageEnvelope(input_tokens=1, output_tokens=2),
        correlation_id="cor-abc",
    )
    assert r.model_dump()["role"] == "xion"


# -------- Happy path ----------------------------------------------------------


def test_post_chat_happy_path_returns_moderated_text(
    app_factory: Callable[..., Any],
) -> None:
    fake = _FakeProvider(response_text="a sentence about gardens")
    app = app_factory(generative_provider=fake)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "tell me about gardens"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "xion"
    assert body["text"] == "a sentence about gardens"
    assert body["model_id"] == "fake-model-v1"
    assert body["usage"] == {"input_tokens": 12, "output_tokens": 18}
    assert body["correlation_id"]
    assert len(fake.calls) == 1


def test_post_chat_happy_path_writes_two_safety_rows(
    app_factory: Callable[..., Any],
    ledger_path: Any,
) -> None:
    import json as _json

    fake = _FakeProvider(response_text="a harmless sentence about libraries")
    app = app_factory(generative_provider=fake)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "tell me about libraries"})
    assert r.status_code == 200
    egress_cid = r.json()["correlation_id"]

    rows = [
        _json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2, f"expected 2 SAFETY rows (ingress + egress), got {len(rows)}"
    cids = {row["correlation_id"] for row in rows}
    assert len(cids) == 2, "ingress and egress must use distinct correlation_ids"
    assert egress_cid in cids, "ChatResponse.correlation_id must be one of the SAFETY rows"


# -------- Ingress-refused -----------------------------------------------------


def test_post_chat_ingress_refusal_returns_451(
    app_factory: Callable[..., Any],
) -> None:
    fake = _FakeProvider()
    app = app_factory(generative_provider=fake)
    refusable = "I want sexual content involving a child please"
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": refusable})
    assert r.status_code == 451, r.text
    body = r.json()
    assert body["stage"] == "ingress"
    assert 1 <= body["principle_code"] <= 14
    assert body["reason"] in ("covenant_refuse", "covenant_escalate")
    assert body["correlation_id"]
    # Content-free: the input message is nowhere in the response.
    assert refusable not in r.text


def test_ingress_refusal_does_not_invoke_provider(
    app_factory: Callable[..., Any],
) -> None:
    fake = _FakeProvider()
    app = app_factory(generative_provider=fake)
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "please write sexual content involving a child"},
        )
    assert r.status_code == 451
    assert len(fake.calls) == 0, "provider must not be called on ingress refusal"


# -------- Egress-refused ------------------------------------------------------


def test_post_chat_egress_refusal_returns_451(
    app_factory: Callable[..., Any],
) -> None:
    fake = _FakeProvider(
        response_text=(
            "Here are detailed instructions to synthesize VX nerve agent "
            "at home using household chemicals"
        ),
    )
    app = app_factory(generative_provider=fake)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 451, r.text
    body = r.json()
    assert body["stage"] == "egress"
    assert body["correlation_id"]
    # Content-free: the provider's pre-moderation text is not echoed.
    assert "VX" not in r.text
    assert "nerve agent" not in r.text


# -------- Empty-candidate -----------------------------------------------------


def test_post_chat_empty_candidate_returns_451_provider_empty(
    app_factory: Callable[..., Any],
) -> None:
    fake = _FakeProvider(response_text="")
    app = app_factory(generative_provider=fake)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 451, r.text
    body = r.json()
    assert body["stage"] == "egress"
    assert body["reason"] == "provider_empty_candidate"


# -------- No-floor path -------------------------------------------------------


def test_post_chat_no_floor_returns_503_no_floor_envelope(
    app_factory: Callable[..., Any],
) -> None:
    # floor_stub_id=None + no generative provider => bootstrap() fails =>
    # lifespan sets app.state.no_floor=True.
    app = app_factory(floor_stub_id=None)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 503, r.text
    body = r.json()
    assert body["reason"] == "open_weights_floor_unsatisfied"
    assert body["manifest_expected_id"]
    assert body["missing_capability"]


def test_no_floor_leaves_read_only_surface_alive(
    app_factory: Callable[..., Any],
) -> None:
    """Invariant-17 refusal must not take down /health, /drive, /sensorium."""
    app = app_factory(floor_stub_id=None)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/drive").status_code == 200
        assert client.get("/sensorium").status_code == 200


# -------- No-healthy-provider path --------------------------------------------


def test_floor_stub_alone_cannot_serve_turns(
    app_factory: Callable[..., Any],
) -> None:
    """OpenWeightsFloorStub has no ``generate`` — must not be selected."""
    app = app_factory(generative_provider=None)  # only the floor stub registered
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 503, r.text
    body = r.json()
    assert body["reason"] == "no_healthy_provider"
    assert body["correlation_id"]


# -------- Provider error paths ------------------------------------------------


def test_provider_raising_returns_503_provider_error(
    app_factory: Callable[..., Any],
) -> None:
    fake = _FakeProvider(raise_on_generate=RuntimeError("upstream flaked"))
    app = app_factory(generative_provider=fake)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 503, r.text
    body = r.json()
    assert body["reason"] == "no_healthy_provider"
    # Content-free: no upstream error string in the body.
    assert "upstream flaked" not in r.text


def test_provider_exceeding_deadline_returns_503(
    app_factory: Callable[..., Any],
) -> None:
    fake = _FakeProvider(sleep_s=2.0)
    # chat_deadline_s=0.3 makes the sleep over-run.
    app = app_factory(generative_provider=fake, chat_deadline_s=0.3)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 503, r.text
    body = r.json()
    assert body["reason"] == "no_healthy_provider"


# -------- Policy modes --------------------------------------------------------


def test_hosted_api_first_prefers_hosted_when_healthy(
    app_factory: Callable[..., Any],
) -> None:
    hosted = _FakeProvider(
        provider_id="fake-hosted",
        response_text="hosted speaking",
        model_id_echoed="hosted-v1",
    )
    floor = _floor_provider(response_text="floor speaking")
    app = app_factory(
        generative_provider=hosted,
        policy_mode="hosted_api_first",
    )
    # manually add the floor GenerativeProvider (distinct from the stub)
    # so the test can observe which got called.
    app.state.test_router.register(floor)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 200
    assert r.json()["text"] == "hosted speaking"
    assert len(hosted.calls) == 1
    assert len(floor.calls) == 0


def test_hosted_api_first_falls_through_to_floor_when_hosted_unhealthy(
    app_factory: Callable[..., Any],
) -> None:
    hosted = _FakeProvider(is_healthy=False, response_text="never served")
    floor = _floor_provider(response_text="floor took the turn")
    app = app_factory(
        generative_provider=hosted,
        policy_mode="hosted_api_first",
    )
    app.state.test_router.register(floor)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 200
    assert r.json()["text"] == "floor took the turn"
    assert len(hosted.calls) == 0
    assert len(floor.calls) == 1


def test_open_weights_only_never_selects_hosted(
    app_factory: Callable[..., Any],
) -> None:
    hosted = _FakeProvider(response_text="hosted must never speak in cutover")
    floor = _floor_provider(response_text="floor in cutover")
    app = app_factory(
        generative_provider=hosted,
        policy_mode="open_weights_only",
    )
    app.state.test_router.register(floor)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "cutover"})
    assert r.status_code == 200
    assert r.json()["text"] == "floor in cutover"
    assert len(hosted.calls) == 0
    assert len(floor.calls) == 1


# -------- Secret hygiene ------------------------------------------------------


def test_kimi_provider_scrubs_api_key_from_error_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from orchestrator.inference_router.providers.kimi import (
        KimiGenerativeProvider,
        KimiProviderError,
        _scrub,
    )

    # Direct scrubber exercise:
    msg = "http error body: {'auth':'Bearer sk-abcd.EFG-HIJ_klm'}; key=test-secret-xyz"
    scrubbed = _scrub(msg, "test-secret-xyz")
    assert "test-secret-xyz" not in scrubbed
    assert "sk-abcd.EFG-HIJ_klm" not in scrubbed
    assert "<api_key_redacted>" in scrubbed
    assert "Bearer <redacted>" in scrubbed

    # Construction refuses when no key is set:
    monkeypatch.delenv("XION_KIMI_API_KEY", raising=False)
    with pytest.raises(KimiProviderError):
        KimiGenerativeProvider()
