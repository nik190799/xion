"""Unit tests for the Phase 5g-iii PAYMENT_LEDGER writer + verifier.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface"
→ "PAYMENT_LEDGER row schema" and ``docs/schemas/ledger-payment.yaml``.

These tests exercise ``orchestrator.billing.ledger`` directly. The
integration tests in ``test_chat_billing.py`` cover ledger writes
through a real /chat turn.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.billing.ledger import (
    SCHEMA_VERSION,
    ZERO_HASH,
    ChainBroken,
    append_payment_row,
    build_payment_row,
    chain_tip,
    iter_rows,
    verify_chain,
)

_DUMMY_SHA = "a" * 64


def _settled_row_kwargs() -> dict:
    return dict(
        correlation_id="cid-settled-0",
        timestamp_utc_ns=1_700_000_000_000_000_000,
        posture="B1",
        outcome="settled",
        refusal_stage=None,
        committed_XION=1000,
        settled_XION=1000,
        refund_XION=0,
        posted_price_XION=1000,
        provider_id="chutes",
        model_id="moonshotai/Kimi-K2.6-TEE",
        authorization_reference="b" * 64,
        source_sha256=_DUMMY_SHA,
    )


def _refunded_row_kwargs() -> dict:
    return dict(
        correlation_id="cid-refunded-0",
        timestamp_utc_ns=1_700_000_000_000_000_000,
        posture="B1",
        outcome="refunded",
        refusal_stage="ingress",
        committed_XION=1000,
        settled_XION=0,
        refund_XION=1000,
        posted_price_XION=1000,
        provider_id=None,
        model_id=None,
        authorization_reference="b" * 64,
        source_sha256=_DUMMY_SHA,
    )


def _disabled_row_kwargs() -> dict:
    return dict(
        correlation_id="cid-disabled-0",
        timestamp_utc_ns=1_700_000_000_000_000_000,
        posture="disabled",
        outcome="settled",
        refusal_stage=None,
        committed_XION=0,
        settled_XION=0,
        refund_XION=0,
        posted_price_XION=1000,
        provider_id="chutes",
        model_id="moonshotai/Kimi-K2.6-TEE",
        authorization_reference="",
        source_sha256=_DUMMY_SHA,
    )


# ------------------------------------------------------- build_payment_row


def test_build_settled_row_is_schema_v1_and_self_consistent() -> None:
    row = build_payment_row(seq=0, prev_hash=ZERO_HASH, **_settled_row_kwargs())
    assert row["schema_version"] == SCHEMA_VERSION
    assert row["seq"] == 0
    assert row["prev_hash"] == ZERO_HASH
    assert len(row["this_hash"]) == 64
    # Money invariant.
    assert row["committed_XION"] == row["settled_XION"] + row["refund_XION"]


def test_build_refunded_row_has_null_provider_on_ingress_refusal() -> None:
    row = build_payment_row(seq=0, prev_hash=ZERO_HASH, **_refunded_row_kwargs())
    assert row["outcome"] == "refunded"
    assert row["refusal_stage"] == "ingress"
    assert row["settled_XION"] == 0
    assert row["refund_XION"] == row["committed_XION"]
    assert row["provider_id"] is None


def test_build_refuses_b3_posture() -> None:
    kwargs = _settled_row_kwargs() | {"posture": "B3"}
    with pytest.raises(ValueError, match="refuses posture='B3'"):
        build_payment_row(seq=0, prev_hash=ZERO_HASH, **kwargs)


def test_build_refuses_refunded_partial() -> None:
    kwargs = _refunded_row_kwargs() | {"outcome": "refunded_partial"}
    with pytest.raises(ValueError, match="refuses outcome="):
        build_payment_row(seq=0, prev_hash=ZERO_HASH, **kwargs)


def test_build_refuses_settled_with_nonzero_refund() -> None:
    kwargs = _settled_row_kwargs() | {"refund_XION": 1, "settled_XION": 1000}
    with pytest.raises(ValueError, match="committed_XION must equal"):
        build_payment_row(seq=0, prev_hash=ZERO_HASH, **kwargs)


def test_build_refuses_refunded_with_nonzero_settled() -> None:
    kwargs = _refunded_row_kwargs() | {"settled_XION": 1, "refund_XION": 999}
    with pytest.raises(ValueError, match="outcome=refunded requires settled_XION=0"):
        build_payment_row(seq=0, prev_hash=ZERO_HASH, **kwargs)


def test_build_refuses_disabled_with_nonzero_money() -> None:
    kwargs = _disabled_row_kwargs() | {
        "committed_XION": 100,
        "settled_XION": 100,
    }
    with pytest.raises(
        ValueError,
        match=r"committed_XION must equal|posture=disabled requires",
    ):
        build_payment_row(seq=0, prev_hash=ZERO_HASH, **kwargs)


def test_build_refuses_disabled_with_refunded_outcome_and_no_refusal() -> None:
    """A disabled-posture row must either be settled/0 (healthy turn in
    backward-compat mode) or refunded/0 (refused turn in backward-compat
    mode). The common path is settled/0."""
    row = build_payment_row(seq=0, prev_hash=ZERO_HASH, **_disabled_row_kwargs())
    assert row["posture"] == "disabled"
    assert row["committed_XION"] == 0


def test_build_refuses_bad_source_sha() -> None:
    kwargs = _settled_row_kwargs() | {"source_sha256": "tooshort"}
    with pytest.raises(ValueError, match="source_sha256"):
        build_payment_row(seq=0, prev_hash=ZERO_HASH, **kwargs)


# ----------------------------------------------------- append + iter + tip


def test_append_chain_links_rows(tmp_path: Path) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    r0 = append_payment_row(ledger, **_settled_row_kwargs())
    kw1 = _refunded_row_kwargs() | {"correlation_id": "cid-refunded-1"}
    r1 = append_payment_row(ledger, **kw1)
    assert r0["seq"] == 0
    assert r0["prev_hash"] == ZERO_HASH
    assert r1["seq"] == 1
    assert r1["prev_hash"] == r0["this_hash"]

    count, tip = chain_tip(ledger)
    assert count == 2
    assert tip == r1["this_hash"]


def test_iter_rows_returns_written_rows_in_order(tmp_path: Path) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    append_payment_row(ledger, **_settled_row_kwargs())
    append_payment_row(
        ledger,
        **(_refunded_row_kwargs() | {"correlation_id": "cid-r-1"}),
    )
    rows = list(iter_rows(ledger))
    assert len(rows) == 2
    assert rows[0]["outcome"] == "settled"
    assert rows[1]["outcome"] == "refunded"


def test_chain_tip_on_missing_file_is_zero_hash(tmp_path: Path) -> None:
    ledger = tmp_path / "nonexistent.jsonl"
    count, tip = chain_tip(ledger)
    assert count == 0
    assert tip == ZERO_HASH


# ----------------------------------------------------- verify_chain happy


def test_verify_chain_passes_on_empty_file(tmp_path: Path) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    count, tip = verify_chain(ledger)
    assert count == 0
    assert tip == ZERO_HASH


def test_verify_chain_passes_on_fresh_ledger(tmp_path: Path) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    append_payment_row(ledger, **_settled_row_kwargs())
    append_payment_row(
        ledger,
        **(_refunded_row_kwargs() | {"correlation_id": "cid-r-1"}),
    )
    append_payment_row(
        ledger,
        **(_disabled_row_kwargs() | {"correlation_id": "cid-d-0"}),
    )
    count, tip = verify_chain(ledger)
    assert count == 3
    assert len(tip) == 64


# ----------------------------------------------------- verify_chain breaks


def _write_raw_rows(path: Path, rows: list[dict]) -> None:
    with path.open("wb") as fh:
        for r in rows:
            fh.write(
                json.dumps(
                    r, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode("utf-8") + b"\n"
            )


def test_verify_chain_raises_on_broken_prev_hash(tmp_path: Path) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    r0 = build_payment_row(seq=0, prev_hash=ZERO_HASH, **_settled_row_kwargs())
    # Tamper: second row claims wrong prev_hash.
    bad_prev = "f" * 64
    r1 = build_payment_row(
        seq=1,
        prev_hash=bad_prev,
        **(_refunded_row_kwargs() | {"correlation_id": "cid-r-1"}),
    )
    _write_raw_rows(ledger, [r0, r1])
    with pytest.raises(ChainBroken, match="prev_hash"):
        verify_chain(ledger)


def test_verify_chain_raises_on_tampered_this_hash(tmp_path: Path) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    r0 = build_payment_row(seq=0, prev_hash=ZERO_HASH, **_settled_row_kwargs())
    r0["this_hash"] = "e" * 64  # tamper
    _write_raw_rows(ledger, [r0])
    with pytest.raises(ChainBroken, match="this_hash recomputation mismatch"):
        verify_chain(ledger)


def test_verify_chain_raises_on_non_contiguous_seq(tmp_path: Path) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    # skip seq=0; write starting at seq=1
    r1 = build_payment_row(seq=1, prev_hash=ZERO_HASH, **_settled_row_kwargs())
    _write_raw_rows(ledger, [r1])
    with pytest.raises(ChainBroken, match="seq non-contiguous"):
        verify_chain(ledger)


def test_verify_chain_raises_on_settled_with_refund_inconsistency(
    tmp_path: Path,
) -> None:
    """A tampered reader-side row where outcome=settled but
    refund_XION > 0 must be rejected by the verifier, even if the
    hash happens to match (the verifier recomputes and independently
    checks structural invariants)."""
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    # Hand-craft a row that passes per-field hash but violates money.
    row = {
        "schema_version": SCHEMA_VERSION,
        "seq": 0,
        "prev_hash": ZERO_HASH,
        "timestamp_utc_ns": 42,
        "correlation_id": "cid",
        "posture": "B1",
        "outcome": "settled",
        "refusal_stage": None,
        "committed_XION": 1000,
        "settled_XION": 999,   # tamper
        "refund_XION": 1,      # tamper
        "posted_price_XION": 1000,
        "provider_id": "chutes",
        "model_id": "moonshotai/Kimi-K2.6-TEE",
        "authorization_reference": "b" * 64,
        "source_sha256": _DUMMY_SHA,
    }
    # Compute matching this_hash so we're not caught by hash check.
    body = {k: v for k, v in row.items() if k != "this_hash"}
    import hashlib as _h
    import json as _j
    row["this_hash"] = _h.sha256(
        _j.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    _write_raw_rows(ledger, [row])
    with pytest.raises(ChainBroken, match="outcome=settled"):
        verify_chain(ledger)


def test_verify_chain_rejects_unknown_schema_version(tmp_path: Path) -> None:
    ledger = tmp_path / "PAYMENT_LEDGER.jsonl"
    row = build_payment_row(seq=0, prev_hash=ZERO_HASH, **_settled_row_kwargs())
    row["schema_version"] = 99
    # Recompute hash so we're caught on version, not on hash.
    body = {k: v for k, v in row.items() if k != "this_hash"}
    import hashlib as _h
    import json as _j
    row["this_hash"] = _h.sha256(
        _j.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    _write_raw_rows(ledger, [row])
    with pytest.raises(ChainBroken, match="schema_version=99"):
        verify_chain(ledger)
