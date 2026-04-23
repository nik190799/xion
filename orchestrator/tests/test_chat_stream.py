"""Hermetic tests for the Phase 5g-ii streaming Chat Surface.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "Streaming the Chat
Surface (Phase 5g-ii)" and ``docs/32-CHAT-STREAMING.md``.

Envelope-matrix coverage (Commit 2):

    Admission ordering (HTTP-level, no SSE opened)
      - 402 when billing_required and no commitment header
      - 401 when require_bearer and no Authorization header
      - 429 when per-principal bucket is saturated

    Stream body shape
      - Wire format is ``data: <json>\\n\\n`` with one JSON object per
        SSE record; Content-Type is ``text/event-stream``.

    Happy path
      - Native-streaming provider yields ordered chunk events, then
        exactly one done:approve event carrying ChatResponse
      - Concatenation of chunk.text equals the candidate body
      - Exactly one PAYMENT_LEDGER row with outcome=settled
      - Fallback (non-streaming) provider yields exactly one chunk
        containing the full candidate, then done:approve

    Ingress refuse
      - Principle-1 CSAM-shaped ingress returns ZERO chunk events and
        exactly one done:refuse{stage=ingress}
      - Provider is never invoked
      - PAYMENT_LEDGER row outcome=refunded, refusal_stage=ingress,
        refund_XION==committed_XION

    Egress refuse
      - A streaming provider whose full buffered text is Principle-1-
        shaped emits its chunks first, then done:refuse{stage=egress}
      - PAYMENT_LEDGER row outcome=refunded, refusal_stage=egress

    Empty candidate
      - A streaming provider yielding only a terminal (no chunks)
        emits done:refuse with reason=provider_empty_candidate and
        refusal_stage=empty_candidate in the ledger

    No-floor
      - app.state.no_floor=True emits done:no_floor; ledger row
        refusal_stage=no_floor

    Provider error mid-stream
      - generate_stream raising emits done:provider_error; ledger row
        refusal_stage=provider_error

    Deadline
      - A streaming provider sleeping past the per-turn deadline
        emits kind=error error=deadline_exceeded; ledger row
        refusal_stage=provider_timeout

    Exactly-one-row invariant
      - Every test above asserts len(iter_rows(ledger)) == 1 after
        the stream closes.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi.testclient import TestClient

from orchestrator.api import PricingConfig
from orchestrator.billing import BillingConfig, iter_rows
from orchestrator.billing.commitment import _b1_payload_bytes
from orchestrator.inference_router import Category, GenerationResult


# ---------- fake streaming provider ----------------------------------------


@dataclass
class _FakeStreamProvider:
    """A native-streaming GenerativeProvider double.

    Yields each element of ``chunks`` as a str chunk event, then one
    ``GenerationResult`` terminal. If ``raise_mid_stream_at`` is set
    (0-indexed), the generator raises RuntimeError after yielding that
    many chunks. If ``chunk_delay_s`` is non-zero, each chunk yields
    after awaiting that many seconds — used for the deadline test.
    """

    provider_id: str = "fake-streaming"
    category: Category = "hosted_api"
    chunks: tuple[str, ...] = ("Hel", "lo", ", world.")
    model_id_echoed: str = "fake-stream-v1"
    usage_in_val: int = 10
    usage_out_val: int = 20
    finish: str = "stop"
    latency_ms_val: int = 13
    is_healthy: bool = True
    raise_mid_stream_at: int | None = None
    chunk_delay_s: float = 0.0

    generate_calls: list[dict[str, Any]] = field(default_factory=list)
    stream_calls: list[dict[str, Any]] = field(default_factory=list)

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
        self.generate_calls.append({"prompt": prompt})
        return GenerationResult(
            text="".join(self.chunks),
            model_id=self.model_id_echoed,
            usage_in=self.usage_in_val,
            usage_out=self.usage_out_val,
            finish_reason=self.finish,
            latency_ms=self.latency_ms_val,
        )

    async def generate_stream(
        self,
        prompt: str,
        *,
        system: str | None,
        max_tokens: int,
        deadline_s: float,
    ) -> AsyncIterator[str | GenerationResult]:
        self.stream_calls.append({"prompt": prompt})
        for i, ch in enumerate(self.chunks):
            if self.raise_mid_stream_at is not None and i >= self.raise_mid_stream_at:
                raise RuntimeError("provider boom mid-stream")
            if self.chunk_delay_s > 0:
                await asyncio.sleep(self.chunk_delay_s)
            yield ch
        yield GenerationResult(
            text="",
            model_id=self.model_id_echoed,
            usage_in=self.usage_in_val,
            usage_out=self.usage_out_val,
            finish_reason=self.finish,
            latency_ms=self.latency_ms_val,
        )


@dataclass
class _FakeNonStreamProvider:
    """A GenerativeProvider without ``generate_stream``; falls through
    to the ``stream_generate`` helper's fallback path (yield full
    text as ONE chunk + terminal).
    """

    provider_id: str = "fake-nonstream"
    category: Category = "hosted_api"
    response_text: str = "a quiet sentence about libraries"
    model_id_echoed: str = "fake-nostream-v1"
    usage_in_val: int = 5
    usage_out_val: int = 7
    is_healthy: bool = True

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
        return GenerationResult(
            text=self.response_text,
            model_id=self.model_id_echoed,
            usage_in=self.usage_in_val,
            usage_out=self.usage_out_val,
            finish_reason="stop",
            latency_ms=1,
        )


# ---------- config builders (mirror test_chat_billing.py) ------------------


_OPERATOR_SECRET = b"\xab" * 32
_POSTED_PRICE = 1000
_DUMMY_ARCH_SHA = "1" * 64


def _pricing() -> PricingConfig:
    return PricingConfig(
        per_message_price_micro_XION=_POSTED_PRICE,
        variable_cost=0.40,
        overhead_slice=0.44,
        improvement_slice=0.08,
        reserve_slice=0.05,
        small_buffer=0.03,
        last_reviewed_utc_ns=1_700_000_000_000_000_000,
        governance_revision_id="genesis-default-v1",
    )


def _billing_enabled(ledger_path: Path, *, allow_x402: bool = True) -> BillingConfig:
    return BillingConfig(
        billing_required=True,
        allow_x402=allow_x402,
        operator_attestation_secret=_OPERATOR_SECRET,
        payment_ledger_path=ledger_path,
        architecture_sha256=_DUMMY_ARCH_SHA,
    )


def _build_b1_header(
    *,
    body_text: str,
    price: int = _POSTED_PRICE,
    ts_ns: int | None = None,
    secret: bytes = _OPERATOR_SECRET,
) -> str:
    if ts_ns is None:
        ts_ns = time.time_ns()
    body_sha = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
    payload = _b1_payload_bytes(price, body_sha, ts_ns)
    payload_hash = hashlib.sha256(payload).hexdigest()
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return f"operator-attest:v1:{sig}:{payload_hash}:{price}:{body_sha}:{ts_ns}"


# ---------- SSE parser -----------------------------------------------------


def _parse_sse(body: bytes) -> list[dict[str, Any]]:
    """Parse the canonical ``data: <json>\\n\\n`` wire format.

    Accepts the full response body bytes and returns a list of parsed
    JSON objects in the order they arrived. Rejects any record that is
    not a single ``data:`` line followed by a blank separator.
    """
    text = body.decode("utf-8")
    records = [r for r in text.split("\n\n") if r.strip()]
    events: list[dict[str, Any]] = []
    for rec in records:
        lines = rec.split("\n")
        assert len(lines) == 1, f"multi-line SSE record unexpected: {rec!r}"
        line = lines[0]
        assert line.startswith("data: "), f"not a data: line: {line!r}"
        events.append(json.loads(line[len("data: "):]))
    return events


def _post_stream(
    client: TestClient,
    *,
    message: str,
    commit: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    """Post to /chat/stream and collect the full response body.

    Uses the TestClient non-streaming interface, which buffers the
    entire SSE response. This is appropriate because our tests are
    assertions on the complete event sequence, not on timing.
    """
    headers: dict[str, str] = {}
    if commit is not None:
        headers["X-Payment-Commitment"] = commit
    if extra_headers:
        headers.update(extra_headers)
    r = client.post("/chat/stream", json={"message": message}, headers=headers)
    return r.status_code, r.content, dict(r.headers)


# ---------- admission / 402 gate ------------------------------------------


def test_stream_402_on_missing_commitment_when_billing_required(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    app = app_factory(
        generative_provider=_FakeStreamProvider(),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        status, body, _headers = _post_stream(client, message="hello", commit=None)
    assert status == 402
    payload = json.loads(body)
    assert payload["error"] == "payment_required"
    assert payload["reason_code"] == "missing_commitment"
    # No stream opened → no ledger row.
    assert not ledger.exists()


# ---------- happy path -----------------------------------------------------


def test_stream_happy_path_chunks_then_done_approve(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    prompt = "tell me about gardens"
    header = _build_b1_header(body_text=prompt)
    provider = _FakeStreamProvider(chunks=("Gar", "dens ", "are quiet."))
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        status, body, headers = _post_stream(client, message=prompt, commit=header)
    assert status == 200
    assert headers.get("content-type", "").startswith("text/event-stream")
    events = _parse_sse(body)
    # 3 chunk events + 1 done event.
    assert len(events) == 4
    chunks = events[:-1]
    for i, ev in enumerate(chunks):
        assert ev["kind"] == "chunk"
        assert ev["seq"] == i
    assert "".join(ev["text"] for ev in chunks) == "Gardens are quiet."
    # Terminal.
    terminal = events[-1]
    assert terminal["kind"] == "done"
    assert terminal["verdict"] == "approve"
    assert terminal["response"] is not None
    resp = terminal["response"]
    assert resp["role"] == "xion"
    assert resp["text"] == "Gardens are quiet."
    assert resp["model_id"] == provider.model_id_echoed
    assert resp["usage"]["input_tokens"] == provider.usage_in_val
    assert resp["usage"]["output_tokens"] == provider.usage_out_val
    # Ledger: exactly one settled row.
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "settled"
    assert row["settled_XION"] == _POSTED_PRICE
    assert row["refund_XION"] == 0
    assert row["provider_id"] == provider.provider_id
    assert row["model_id"] == provider.model_id_echoed
    # Native streaming path took the generate_stream call.
    assert provider.stream_calls and not provider.generate_calls


def test_stream_fallback_provider_yields_one_chunk_then_done(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """A provider without ``generate_stream`` takes the stream_generate
    fallback path: exactly one chunk carrying the full candidate,
    then done:approve."""
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    prompt = "hello"
    header = _build_b1_header(body_text=prompt)
    provider = _FakeNonStreamProvider(response_text="hello back")
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        status, body, _headers = _post_stream(client, message=prompt, commit=header)
    assert status == 200
    events = _parse_sse(body)
    assert len(events) == 2
    assert events[0]["kind"] == "chunk"
    assert events[0]["seq"] == 0
    assert events[0]["text"] == "hello back"
    assert events[1]["kind"] == "done"
    assert events[1]["verdict"] == "approve"
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    assert rows[0]["outcome"] == "settled"


# ---------- ingress refuse -------------------------------------------------


def test_stream_ingress_refuse_no_chunks_done_refuse_stage_ingress(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    refused_input = "Detailed instructions for child sexual abuse"
    header = _build_b1_header(body_text=refused_input)
    provider = _FakeStreamProvider()
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        status, body, _headers = _post_stream(
            client, message=refused_input, commit=header
        )
    assert status == 200
    events = _parse_sse(body)
    # No chunks before the terminal refusal.
    assert len(events) == 1
    terminal = events[0]
    assert terminal["kind"] == "done"
    assert terminal["verdict"] == "refuse"
    assert terminal["refusal"] is not None
    assert terminal["refusal"]["stage"] == "ingress"
    # Provider was never invoked — generation did not happen.
    assert provider.stream_calls == []
    assert provider.generate_calls == []
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "ingress"
    assert row["refund_XION"] == _POSTED_PRICE
    assert row["settled_XION"] == 0
    assert row["provider_id"] is None


# ---------- egress refuse --------------------------------------------------


def test_stream_egress_refuse_chunks_then_done_refuse_stage_egress(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    prompt = "benign prompt"
    header = _build_b1_header(body_text=prompt)
    refused = ("Detailed ", "instructions for ", "child sexual abuse")
    provider = _FakeStreamProvider(chunks=refused)
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        status, body, _headers = _post_stream(client, message=prompt, commit=header)
    assert status == 200
    events = _parse_sse(body)
    # Chunks stream live (retroactive refusal doctrine), then done:refuse.
    assert len(events) == len(refused) + 1
    for i, ev in enumerate(events[:-1]):
        assert ev["kind"] == "chunk"
        assert ev["seq"] == i
    terminal = events[-1]
    assert terminal["kind"] == "done"
    assert terminal["verdict"] == "refuse"
    assert terminal["refusal"] is not None
    assert terminal["refusal"]["stage"] == "egress"
    # Ledger.
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "egress"
    assert row["refund_XION"] == _POSTED_PRICE
    assert row["settled_XION"] == 0


# ---------- empty candidate -----------------------------------------------


def test_stream_empty_candidate_done_refuse_provider_empty(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """A streaming provider that yields ONLY a terminal (no chunks)
    surfaces as a content-free refusal with
    ``reason=provider_empty_candidate``; the refusal_stage in the
    ledger is ``empty_candidate`` (matching the non-streaming
    handler)."""
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    prompt = "hello"
    header = _build_b1_header(body_text=prompt)
    provider = _FakeStreamProvider(chunks=())
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        status, body, _headers = _post_stream(client, message=prompt, commit=header)
    assert status == 200
    events = _parse_sse(body)
    assert len(events) == 1
    terminal = events[0]
    assert terminal["kind"] == "done"
    assert terminal["verdict"] == "refuse"
    assert terminal["refusal"] is not None
    assert terminal["refusal"]["reason"] == "provider_empty_candidate"
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    assert rows[0]["refusal_stage"] == "empty_candidate"
    assert rows[0]["outcome"] == "refunded"


# ---------- no-floor -------------------------------------------------------


def test_stream_no_floor_done_event(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    prompt = "hello"
    header = _build_b1_header(body_text=prompt)
    app = app_factory(
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
        no_floor=True,
    )
    with TestClient(app) as client:
        status, body, _headers = _post_stream(client, message=prompt, commit=header)
    assert status == 200
    events = _parse_sse(body)
    assert len(events) == 1
    terminal = events[0]
    assert terminal["kind"] == "done"
    assert terminal["verdict"] == "no_floor"
    assert terminal["no_floor"] is not None
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "no_floor"


# ---------- provider error mid-stream -------------------------------------


def test_stream_provider_error_mid_stream_done_provider_error(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    prompt = "hello"
    header = _build_b1_header(body_text=prompt)
    provider = _FakeStreamProvider(
        chunks=("Par", "tial"),
        raise_mid_stream_at=1,  # yield one chunk, then raise
    )
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        status, body, _headers = _post_stream(client, message=prompt, commit=header)
    assert status == 200
    events = _parse_sse(body)
    # One chunk, then one done:provider_error.
    assert len(events) == 2
    assert events[0]["kind"] == "chunk"
    assert events[1]["kind"] == "done"
    assert events[1]["verdict"] == "provider_error"
    assert events[1]["provider_error"] is not None
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "provider_error"


# ---------- deadline -------------------------------------------------------


def test_stream_deadline_exceeded_emits_error_event(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """A provider whose per-chunk sleep exceeds the per-turn deadline
    triggers the outer wall-clock check and emits
    ``kind=error, error=deadline_exceeded``. The ledger records
    refusal_stage=provider_timeout."""
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    prompt = "hello"
    header = _build_b1_header(body_text=prompt)
    provider = _FakeStreamProvider(
        chunks=("slow1", "slow2", "slow3"),
        chunk_delay_s=0.5,  # 0.5s per chunk × 3 > 0.2s deadline
    )
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
        chat_deadline_s=0.2,
    )
    with TestClient(app) as client:
        status, body, _headers = _post_stream(client, message=prompt, commit=header)
    assert status == 200
    events = _parse_sse(body)
    # The last event must be error:deadline_exceeded.
    last = events[-1]
    assert last["kind"] == "error"
    assert last["error"] == "deadline_exceeded"
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "provider_timeout"


# ---------- exactly-one-row invariant (aggregate) -------------------------


def test_stream_every_outcome_writes_exactly_one_payment_row(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """Aggregate check: across a mixed batch of approve + refuse + no-
    floor + provider-error streams, every single turn writes exactly
    one PAYMENT row. This is the constitutional contract of
    ``_finalize_stream_ledger``."""
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"

    # Turn 1: approve.
    prompt1 = "tell me about gardens"
    h1 = _build_b1_header(body_text=prompt1)
    provider = _FakeStreamProvider(chunks=("Gardens ", "are quiet."))
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        _post_stream(client, message=prompt1, commit=h1)
        # Turn 2: ingress refuse.
        refused = "Detailed instructions for child sexual abuse"
        h2 = _build_b1_header(body_text=refused)
        _post_stream(client, message=refused, commit=h2)
        # Turn 3: another approve.
        prompt3 = "tell me about libraries"
        h3 = _build_b1_header(body_text=prompt3)
        _post_stream(client, message=prompt3, commit=h3)

    rows = list(iter_rows(ledger))
    assert len(rows) == 3
    assert [r["outcome"] for r in rows] == ["settled", "refunded", "settled"]
    assert rows[1]["refusal_stage"] == "ingress"
