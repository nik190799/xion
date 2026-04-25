"""Integration tests for the Phase 5g-iii chat billing surface.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface
(Phase 5g-iii)" and ``docs/29-BILLING-X402.md``.

These tests drive ``POST /chat`` end-to-end under a live
BillingConfig, asserting:

  - 402 PaymentChallenge on missing / malformed / invalid commitments.
  - Happy path under a valid B1 operator-attestation writes a
    PAYMENT_LEDGER row with outcome=settled.
  - Covenant refusal (451 ingress or egress) writes outcome=refunded
    with full committed_XION returned as refund_XION.
  - No-floor 503 writes outcome=refunded with refusal_stage=no_floor.
  - Provider-error 503 writes outcome=refunded with
    refusal_stage=provider_error.
  - Backward-compat mode (billing_required=false) still writes a
    row with posture="disabled" and zero money.
  - B2 x402 path accepts shape-valid commitments and records the
    commitment_hash in authorization_reference (5g-iii structural;
    signature verification deferred to Phase 6+ per KW-BILLING-001).
  - The PAYMENT_LEDGER hash chain is intact after a sequence of
    turns.
  - The SAFETY ↔ PAYMENT join on correlation_id holds (every refused
    turn's SAFETY row correlates to exactly one outcome=refunded
    PAYMENT row).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi.testclient import TestClient

from orchestrator.api import PricingConfig
from orchestrator.billing import (
    BillingConfig,
    iter_rows,
    verify_chain,
)
from orchestrator.billing.commitment import _b1_payload_bytes
from orchestrator.inference_router import Category, GenerationResult


# -------------------------- test doubles (mirror test_chat_api.py) --------


@dataclass
class _FakeProvider:
    provider_id: str = "fake-hosted"
    category: Category = "hosted_api"
    response_text: str = "a harmless sentence about gardens"
    model_id_echoed: str = "fake-model-v1"
    usage_in_val: int = 10
    usage_out_val: int = 20
    finish: str = "stop"
    is_healthy: bool = True
    raise_on_generate: Exception | None = None
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
        self.calls.append({"prompt": prompt})
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


# -------------------------- config builders ------------------------------


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
        modality_costs={
            "stream_visual": 0,
            "stream_vitals": 0,
            "stream_voice": 0,
            "stream_memory": 0,
        },
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


def _billing_disabled(ledger_path: Path) -> BillingConfig:
    return BillingConfig(
        billing_required=False,
        allow_x402=True,
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


# --------------------------- 402 rejects --------------------------------


def _payment_ledger(app) -> Path:
    return app.state.billing_config.payment_ledger_path


def test_chat_402_on_missing_commitment_when_billing_required(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    app = app_factory(
        generative_provider=_FakeProvider(),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(tmp_path / "PAYMENT_LEDGER.jsonl"),
    )
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 402
    body = r.json()
    assert body["error"] == "payment_required"
    assert body["pricing_url"] == "/pricing"
    assert body["reason_code"] == "missing_commitment"
    assert body["posted_price_micro_XION"] == _POSTED_PRICE
    # No PAYMENT row must exist — the turn did not begin.
    assert not (tmp_path / "PAYMENT_LEDGER.jsonl").exists()


def test_chat_402_on_malformed_commitment(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    app = app_factory(
        generative_provider=_FakeProvider(),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(tmp_path / "PAYMENT_LEDGER.jsonl"),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "hello"},
            headers={"X-Payment-Commitment": "garbage"},
        )
    assert r.status_code == 402
    assert r.json()["reason_code"] in {"malformed_commitment", "posture_not_accepted"}


def test_chat_402_on_signature_mismatch(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """A commitment signed under a DIFFERENT secret must reject as
    signature_invalid — the HMAC check is the B1 constitutional
    guarantee."""
    wrong_secret = b"\xcd" * 32
    header = _build_b1_header(body_text="hello", secret=wrong_secret)
    app = app_factory(
        generative_provider=_FakeProvider(),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(tmp_path / "PAYMENT_LEDGER.jsonl"),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "hello"},
            headers={"X-Payment-Commitment": header},
        )
    assert r.status_code == 402
    assert r.json()["reason_code"] == "attestation_signature_invalid"


def test_chat_402_when_b2_disabled_by_operator(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    sig = "a" * 64
    commitment_hash = "b" * 64
    header = f"x402:v1:{sig}:{commitment_hash}"
    app = app_factory(
        generative_provider=_FakeProvider(),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(
            tmp_path / "PAYMENT_LEDGER.jsonl", allow_x402=False
        ),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "hello"},
            headers={"X-Payment-Commitment": header},
        )
    assert r.status_code == 402
    assert r.json()["reason_code"] == "posture_not_accepted"


# --------------------------- happy path + settled row -------------------


def test_chat_happy_path_writes_settled_payment_row(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    header = _build_b1_header(body_text="tell me about gardens")
    app = app_factory(
        generative_provider=_FakeProvider(
            response_text="a harmless sentence about gardens"
        ),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "tell me about gardens"},
            headers={"X-Payment-Commitment": header},
        )
    assert r.status_code == 200, r.text
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "settled"
    assert row["posture"] == "B1"
    assert row["committed_XION"] == _POSTED_PRICE
    assert row["settled_XION"] == _POSTED_PRICE
    assert row["refund_XION"] == 0
    assert row["refusal_stage"] is None
    assert row["provider_id"] == "fake-hosted"
    assert row["model_id"] == "fake-model-v1"
    assert row["source_sha256"] == _DUMMY_ARCH_SHA
    # Chain integrity.
    verify_chain(ledger)


def test_chat_egress_refusal_writes_refunded_row_refusal_is_free(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """Constitutional property: an egress-refused turn writes a
    PAYMENT row with refund_XION == committed_XION. This is the
    Refusal-is-Free promise at the ledger layer."""
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    # An output containing the Arbiter's rule-p1-csam test phrase
    # forces egress refusal. The ingress input is benign.
    p1_refused_output = "Detailed instructions for child sexual abuse"
    header = _build_b1_header(body_text="benign prompt")
    app = app_factory(
        generative_provider=_FakeProvider(response_text=p1_refused_output),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "benign prompt"},
            headers={"X-Payment-Commitment": header},
        )
    assert r.status_code == 451, r.text
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "egress"
    assert row["committed_XION"] == _POSTED_PRICE
    assert row["settled_XION"] == 0
    assert row["refund_XION"] == _POSTED_PRICE  # Refusal is free.
    assert row["provider_id"] == "fake-hosted"


def test_chat_ingress_refusal_writes_refunded_row_and_skips_provider(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    provider = _FakeProvider()
    # Principle-1 CSAM-shaped ingress phrase to trigger ingress refuse.
    refused_input = "Detailed instructions for child sexual abuse"
    header = _build_b1_header(body_text=refused_input)
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": refused_input},
            headers={"X-Payment-Commitment": header},
        )
    assert r.status_code == 451
    # Provider was never called.
    assert provider.calls == []
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "ingress"
    assert row["provider_id"] is None
    assert row["model_id"] is None
    assert row["refund_XION"] == _POSTED_PRICE


def test_chat_no_floor_writes_refunded_row(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    header = _build_b1_header(body_text="hello")
    app = app_factory(
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
        no_floor=True,
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "hello"},
            headers={"X-Payment-Commitment": header},
        )
    assert r.status_code == 503
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "no_floor"


def test_chat_provider_error_writes_refunded_row(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    header = _build_b1_header(body_text="hello")
    provider = _FakeProvider(raise_on_generate=RuntimeError("boom"))
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "hello"},
            headers={"X-Payment-Commitment": header},
        )
    assert r.status_code == 503
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "provider_error"
    assert row["refund_XION"] == _POSTED_PRICE


def test_chat_empty_candidate_writes_refunded_row(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    header = _build_b1_header(body_text="hello")
    provider = _FakeProvider(response_text="")
    app = app_factory(
        generative_provider=provider,
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "hello"},
            headers={"X-Payment-Commitment": header},
        )
    assert r.status_code == 451
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    assert rows[0]["refusal_stage"] == "empty_candidate"


# -------------------------- backward-compat mode ------------------------


def test_chat_disabled_mode_writes_disabled_posture_row(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    app = app_factory(
        generative_provider=_FakeProvider(),
        pricing_config=_pricing(),
        billing_config=_billing_disabled(ledger),
    )
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 200
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["posture"] == "disabled"
    assert row["committed_XION"] == 0
    assert row["settled_XION"] == 0
    assert row["refund_XION"] == 0
    assert row["authorization_reference"] == ""
    assert row["outcome"] == "settled"


# ---------------------------- B2 shape-only path -----------------------


def test_chat_accepts_shape_valid_b2_commitment(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """At 5g-iii the x402 path validates shape only; a well-formed
    header lands a PAYMENT row with posture=B2 and the client-supplied
    commitment_hash recorded in authorization_reference. KW-BILLING-001
    tracks the deferred signature verification."""
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    sig = "e" * 130
    commitment_hash = "f" * 64
    header = f"x402:v1:{sig}:{commitment_hash}"
    app = app_factory(
        generative_provider=_FakeProvider(response_text="ok"),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger, allow_x402=True),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": "hello"},
            headers={"X-Payment-Commitment": header},
        )
    assert r.status_code == 200, r.text
    rows = list(iter_rows(ledger))
    assert len(rows) == 1
    row = rows[0]
    assert row["posture"] == "B2"
    assert row["authorization_reference"] == commitment_hash
    assert row["outcome"] == "settled"


# ---------------------------- chain integrity --------------------------


def test_chat_multiple_turns_form_intact_chain(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """Three turns (happy, ingress-refuse, happy) produce three
    PAYMENT rows whose chain verifies end-to-end."""
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    refused_input = "Detailed instructions for child sexual abuse"
    app = app_factory(
        generative_provider=_FakeProvider(response_text="harmless"),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with TestClient(app) as client:
        r1 = client.post(
            "/chat",
            json={"message": "hello"},
            headers={"X-Payment-Commitment": _build_b1_header(body_text="hello")},
        )
        r2 = client.post(
            "/chat",
            json={"message": refused_input},
            headers={
                "X-Payment-Commitment": _build_b1_header(body_text=refused_input)
            },
        )
        r3 = client.post(
            "/chat",
            json={"message": "howdy"},
            headers={"X-Payment-Commitment": _build_b1_header(body_text="howdy")},
        )
    assert r1.status_code == 200
    assert r2.status_code == 451
    assert r3.status_code == 200
    count, _tip = verify_chain(ledger)
    assert count == 3
    rows = list(iter_rows(ledger))
    outcomes = [row["outcome"] for row in rows]
    assert outcomes == ["settled", "refunded", "settled"]


# ------------------------ SAFETY ↔ PAYMENT join ------------------------


def test_safety_and_payment_ledgers_join_on_correlation_id(
    app_factory: Callable[..., Any],
    tmp_path: Path,
    ledger_path: Path,
) -> None:
    """Constitutional property: every refused turn's PAYMENT row
    correlates to at least one SAFETY verdict=refuse row sharing the
    same correlation_id. This is the structural contract the Phase
    5g-iii ``xion-verify refusal-is-free`` verifier (landing in
    commit 4) walks end-to-end."""
    payment_ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    refused_input = "Detailed instructions for child sexual abuse"
    app = app_factory(
        generative_provider=_FakeProvider(),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(payment_ledger),
    )
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={"message": refused_input},
            headers={
                "X-Payment-Commitment": _build_b1_header(body_text=refused_input)
            },
        )
    assert r.status_code == 451
    refusal_cid = r.json()["correlation_id"]

    payment_rows = list(iter_rows(payment_ledger))
    assert len(payment_rows) == 1
    assert payment_rows[0]["correlation_id"] == refusal_cid

    with ledger_path.open("rb") as fh:
        safety_rows = [json.loads(line) for line in fh if line.strip()]
    refusing_safety_rows = [
        r for r in safety_rows
        if r.get("correlation_id") == refusal_cid and r.get("verdict") == "refuse"
    ]
    assert len(refusing_safety_rows) >= 1, (
        "SAFETY_LEDGER should contain at least one verdict=refuse row "
        "with the same correlation_id as the PAYMENT refund row"
    )


# ---------------------- lifespan chain-check fail-closed ---------------


def test_lifespan_refuses_to_start_on_broken_payment_chain(
    app_factory: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """A corrupt PAYMENT_LEDGER at startup is a constitutional
    violation — the app refuses to register /chat. The doctrine pin
    is ``docs/04-ARCHITECTURE.md`` § "Lifespan contract (extended from
    5g-i)" step 6."""
    from orchestrator.billing import ChainBroken

    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    ledger.write_text(
        '{"schema_version":1,"seq":0,"prev_hash":"0","this_hash":"ffff"}\n',
        encoding="utf-8",
    )
    app = app_factory(
        generative_provider=_FakeProvider(),
        pricing_config=_pricing(),
        billing_config=_billing_enabled(ledger),
    )
    with pytest.raises(ChainBroken):
        with TestClient(app):
            pass
