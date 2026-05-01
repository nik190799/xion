"""Tests for ``xion-verify refusal-is-free`` — SAFETY ↔ PAYMENT join."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path

from click.testing import CliRunner
from orchestrator.billing.ledger import append_payment_row
from orchestrator.safety import ledger as safety_ledger
from orchestrator.safety.types import Decision

from xion_verify.commands.refusal_is_free import refusal_is_free
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK

_SHA_STAND = "a" * 64  # synthetic 64-char hex for source_sha256


@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _invoke(repo: Path) -> tuple[int, str]:
    runner = CliRunner()
    with _chdir(repo):
        result = runner.invoke(refusal_is_free, [])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output


# ---------------- helpers ----------------------------------------------------


def _write_safety_ok(path: Path, cid: str, ts: int = 1_700_000_000_000_000_000) -> dict:
    v = safety_ledger.build_verdict(
        correlation_id=cid,
        candidate="hi",
        timestamp_utc_ns=ts,
        decision=Decision.OK,
        summary="OK",
    )
    return safety_ledger.append(path, v)


def _write_safety_refuse(path: Path, cid: str, ts: int = 1_700_000_000_000_000_000) -> dict:
    v = safety_ledger.build_verdict(
        correlation_id=cid,
        candidate="hi",
        timestamp_utc_ns=ts,
        decision=Decision.REFUSE,
        summary="refused",
        principle_id="7",
        rule_id="t.r_v1",
        rule_version=1,
    )
    return safety_ledger.append(path, v)


def _write_payment_settled(path: Path, cid: str, *, price: int = 1000) -> dict:
    return append_payment_row(
        path,
        correlation_id=cid,
        timestamp_utc_ns=1_700_000_000_000_000_001,
        posture="B1",
        outcome="settled",
        refusal_stage=None,
        committed_XION=price,
        settled_XION=price,
        refund_XION=0,
        posted_price_XION=price,
        provider_id="test-provider",
        model_id="test-model",
        authorization_reference="deadbeef",
        source_sha256=_SHA_STAND,
    )


def _write_payment_refunded(
    path: Path,
    cid: str,
    *,
    stage: str,
    price: int = 1000,
) -> dict:
    return append_payment_row(
        path,
        correlation_id=cid,
        timestamp_utc_ns=1_700_000_000_000_000_002,
        posture="B1",
        outcome="refunded",
        refusal_stage=stage,  # type: ignore[arg-type]
        committed_XION=price,
        settled_XION=0,
        refund_XION=price,
        posted_price_XION=price,
        provider_id=None,
        model_id=None,
        authorization_reference="deadbeef",
        source_sha256=_SHA_STAND,
    )


def _write_payment_disabled(path: Path, cid: str) -> dict:
    return append_payment_row(
        path,
        correlation_id=cid,
        timestamp_utc_ns=1_700_000_000_000_000_003,
        posture="disabled",
        outcome="settled",
        refusal_stage=None,
        committed_XION=0,
        settled_XION=0,
        refund_XION=0,
        posted_price_XION=1000,
        provider_id="p",
        model_id="m",
        authorization_reference="",
        source_sha256=_SHA_STAND,
    )


# ---------------- empty / half-sealed ---------------------------------------


def test_no_ledgers_is_ok(synthetic_repo: Path) -> None:
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "no ledgers yet" in out


def test_only_safety_present_is_not_yet_sealed(synthetic_repo: Path) -> None:
    (synthetic_repo / "SAFETY_LEDGER.jsonl").write_text("", encoding="utf-8")
    code, out = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED
    assert "PAYMENT_LEDGER.jsonl not present" in out


def test_only_payment_present_is_not_yet_sealed(synthetic_repo: Path) -> None:
    (synthetic_repo / "PAYMENT_LEDGER.jsonl").write_text("", encoding="utf-8")
    code, out = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED
    assert "SAFETY_LEDGER.jsonl not present" in out


# ---------------- happy paths -----------------------------------------------


def test_settled_happy_path(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_safety_ok(safety, "cid-1")
    _write_payment_settled(payment, "cid-1")
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "settled=1" in out
    assert "refunded=0" in out


def test_ingress_refund_happy_path(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_safety_refuse(safety, "cid-1")
    _write_payment_refunded(payment, "cid-1", stage="ingress")
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "ingress/egress=1" in out
    assert "ingress: 1" in out


def test_operational_refund_no_paired_refuse_is_ok(synthetic_repo: Path) -> None:
    """A no_floor refund does NOT require a SAFETY verdict=refuse."""
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    # SAFETY records an ingress=ok (the ingress passed; the floor failed
    # downstream with no Arbiter involvement).
    _write_safety_ok(safety, "cid-op")
    _write_payment_refunded(payment, "cid-op", stage="no_floor")
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "operational=1" in out
    assert "no_floor: 1" in out


def test_mixed_outcomes_tally(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    # Turn 1: settled.
    _write_safety_ok(safety, "cid-a")
    _write_payment_settled(payment, "cid-a")
    # Turn 2: egress refuse.
    _write_safety_ok(safety, "cid-b")
    _write_safety_refuse(safety, "cid-b")
    _write_payment_refunded(payment, "cid-b", stage="egress")
    # Turn 3: empty_candidate.
    _write_safety_ok(safety, "cid-c")
    _write_payment_refunded(payment, "cid-c", stage="empty_candidate")
    # Turn 4: disabled.
    _write_safety_ok(safety, "cid-d")
    _write_payment_disabled(payment, "cid-d")
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "settled=2" in out  # cid-a and cid-d (disabled is outcome=settled)
    assert "refunded=2" in out  # cid-b and cid-c
    assert "disabled-posture rows=1" in out


def test_historic_refuse_without_payment_row_is_noted(synthetic_repo: Path) -> None:
    """SAFETY refuse rows from before PAYMENT_LEDGER came live are tolerated."""
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    # A historic refuse with no PAYMENT row.
    _write_safety_refuse(safety, "cid-historic")
    # A current settled turn.
    _write_safety_ok(safety, "cid-live")
    _write_payment_settled(payment, "cid-live")
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "pre-PAYMENT_LEDGER" in out


# ---------------- failure detection -----------------------------------------


def test_settled_with_safety_refuse_fails(synthetic_repo: Path) -> None:
    """PAYMENT=settled but SAFETY=refuse for the same cid → Covenant break."""
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_safety_refuse(safety, "cid-broken")
    _write_payment_settled(payment, "cid-broken")
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    assert "Property D" in out
    assert "settled" in out.lower()


def test_ingress_refund_without_safety_refuse_fails(synthetic_repo: Path) -> None:
    """PAYMENT refunded at stage=ingress must have a paired SAFETY verdict=refuse."""
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    # SAFETY records only a verdict=ok row for this cid (impossible in
    # the real handler, but we forge it to exercise Property C).
    _write_safety_ok(safety, "cid-forged")
    _write_payment_refunded(payment, "cid-forged", stage="ingress")
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    assert "Property C" in out


def test_broken_payment_chain_fails(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_safety_ok(safety, "cid-x")
    _write_payment_settled(payment, "cid-x")
    # Tamper the payment row's settled_XION without recomputing the hash.
    raw = payment.read_bytes().splitlines()[0]
    parsed = json.loads(raw)
    parsed["settled_XION"] = 999_999  # break the row without touching this_hash
    payment.write_bytes(
        (json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    )
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    assert "PAYMENT_LEDGER chain broken" in out


def test_broken_safety_chain_fails(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_safety_ok(safety, "cid-x")
    _write_payment_settled(payment, "cid-x")
    raw = safety.read_bytes().splitlines()[0]
    parsed = json.loads(raw)
    parsed["verdict"] = "refuse"  # break row without recomputing hash
    safety.write_bytes(
        (json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    )
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    assert "SAFETY_LEDGER chain broken" in out


def test_money_shape_violation_caught_by_chain_first(synthetic_repo: Path) -> None:
    """A tampered money field breaks the chain; verifier reports that first."""
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_safety_refuse(safety, "cid-y")
    _write_payment_refunded(payment, "cid-y", stage="ingress")
    # Tamper: set refund_XION to half the committed, recompute this_hash
    # so the per-row hash passes but the money shape is wrong.
    raw = payment.read_bytes().splitlines()[0]
    parsed = json.loads(raw)
    parsed["refund_XION"] = parsed["committed_XION"] // 2
    body = {k: v for k, v in parsed.items() if k != "this_hash"}
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    parsed["this_hash"] = hashlib.sha256(canonical).hexdigest()
    payment.write_bytes(
        (json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    )
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    # The chain verifier enforces money arithmetic; this should fail
    # there before reaching Property B in the join. Either message is
    # acceptable — the property is "the verifier refuses the ledger".
    assert "PAYMENT_LEDGER chain broken" in out or "Property B" in out


def test_duplicate_payment_rows_for_one_cid_fails(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_safety_ok(safety, "cid-dup")
    _write_payment_settled(payment, "cid-dup")
    # Second row for the same cid (chain still valid; the invariant we
    # assert at the verifier level is "one PAYMENT row per cid").
    _write_payment_settled(payment, "cid-dup")
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    assert "correlation_id" in out
    assert "2 PAYMENT rows" in out
