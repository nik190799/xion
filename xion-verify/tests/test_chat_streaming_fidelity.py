"""Tests for ``xion-verify chat-streaming-fidelity`` (Phase 5g-ii Commit 5)."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

from click.testing import CliRunner
from orchestrator.billing.ledger import append_payment_row
from orchestrator.safety import ledger as safety_ledger
from orchestrator.safety.types import Decision

from xion_verify.commands.chat_streaming_fidelity import chat_streaming_fidelity
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


_SHA_STAND = "a" * 64


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
        result = runner.invoke(chat_streaming_fidelity, [])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output


# ---------------- helpers ----------------------------------------------------


def _sid(i: int) -> str:
    """Build a 32-hex stream_id. The index lands at the tail so each
    id is unique and obviously synthetic."""
    return f"{i:032x}"


def _write_stream_settled(
    path: Path,
    cid: str,
    sid: str,
    *,
    price: int = 1000,
) -> dict:
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
        stream_id=sid,
    )


def _write_stream_refunded(
    path: Path,
    cid: str,
    sid: str,
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
        provider_id="test-provider",
        model_id="test-model",
        authorization_reference="deadbeef",
        source_sha256=_SHA_STAND,
        stream_id=sid,
    )


def _write_stream_cancelled(
    path: Path,
    cid: str,
    sid: str,
    *,
    price: int = 1000,
) -> dict:
    return append_payment_row(
        path,
        correlation_id=cid,
        timestamp_utc_ns=1_700_000_000_000_000_003,
        posture="B1",
        outcome="cancelled",
        refusal_stage=None,
        committed_XION=price,
        settled_XION=0,
        refund_XION=price,
        posted_price_XION=price,
        provider_id="test-provider",
        model_id="test-model",
        authorization_reference="deadbeef",
        source_sha256=_SHA_STAND,
        stream_id=sid,
    )


def _write_nonstream_settled(path: Path, cid: str) -> dict:
    return append_payment_row(
        path,
        correlation_id=cid,
        timestamp_utc_ns=1_700_000_000_000_000_004,
        posture="B1",
        outcome="settled",
        refusal_stage=None,
        committed_XION=1000,
        settled_XION=1000,
        refund_XION=0,
        posted_price_XION=1000,
        provider_id="test-provider",
        model_id="test-model",
        authorization_reference="deadbeef",
        source_sha256=_SHA_STAND,
    )


def _write_safety_ok(path: Path, cid: str, ts: int = 1_700_000_000_000_000_000) -> dict:
    v = safety_ledger.build_verdict(
        correlation_id=cid,
        candidate="hi",
        timestamp_utc_ns=ts,
        decision=Decision.OK,
        summary="OK",
    )
    return safety_ledger.append(path, v)


def _write_safety_refuse(
    path: Path,
    cid: str,
    ts: int = 1_700_000_000_000_000_005,
) -> dict:
    v = safety_ledger.build_verdict(
        correlation_id=cid,
        candidate="refused content",
        timestamp_utc_ns=ts,
        decision=Decision.REFUSE,
        summary="refuse",
        principle_id="7",
        rule_id="t.r_v1",
        rule_version=1,
    )
    return safety_ledger.append(path, v)


# ---------------- empty / half-sealed ---------------------------------------


def test_no_payment_ledger_is_not_yet_sealed(synthetic_repo: Path) -> None:
    code, out = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED
    assert "no PAYMENT_LEDGER on disk yet" in out


def test_payment_present_but_no_stream_rows_is_not_yet_sealed(
    synthetic_repo: Path,
) -> None:
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_nonstream_settled(payment, "cid-1")
    code, out = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED
    assert "none carry stream_id" in out


# ---------------- happy paths -----------------------------------------------


def test_streamed_settled_happy_path(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    sid = _sid(1)
    _write_safety_ok(safety, "cid-1")
    _write_stream_settled(payment, "cid-1", sid)
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "settled=1" in out
    assert "1 stream_id(s)" in out


def test_streamed_egress_refuse_with_paired_safety(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    sid = _sid(2)
    _write_safety_ok(safety, "cid-2")
    _write_safety_refuse(safety, "cid-2")
    _write_stream_refunded(payment, "cid-2", sid, stage="egress")
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "refunded=1" in out
    assert "egress: 1" in out


def test_streamed_cancelled_no_paired_egress(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    sid = _sid(3)
    _write_safety_ok(safety, "cid-3")
    _write_stream_cancelled(payment, "cid-3", sid)
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "cancelled=1" in out


def test_mixed_streams_and_nonstreams_tally(synthetic_repo: Path) -> None:
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_safety_ok(safety, "cid-stream-a")
    _write_stream_settled(payment, "cid-stream-a", _sid(10))
    _write_safety_ok(safety, "cid-stream-b")
    _write_stream_cancelled(payment, "cid-stream-b", _sid(11))
    _write_safety_ok(safety, "cid-nonstream-a")
    _write_nonstream_settled(payment, "cid-nonstream-a")
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "2 streaming PAYMENT row(s)" in out
    assert "settled=1" in out
    assert "cancelled=1" in out


# ---------------- failure detection -----------------------------------------


def test_cancelled_with_paired_egress_refuse_fails(synthetic_repo: Path) -> None:
    """A cancelled stream with a paired SAFETY verdict=refuse stage=egress
    row is impossible by construction — egress moderation cannot run on
    a cancelled stream. The verifier must flag this."""
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    sid = _sid(20)
    _write_safety_ok(safety, "cid-bad")
    _write_safety_refuse(safety, "cid-bad")
    _write_stream_cancelled(payment, "cid-bad", sid)
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    assert "Property E" in out or "cancel-without-paired-refuse" in out


def test_egress_refund_without_paired_egress_fails(synthetic_repo: Path) -> None:
    """An outcome=refunded + refusal_stage=egress PAYMENT row with no
    paired SAFETY verdict=refuse stage=egress row is a retroactive-
    refusal bug."""
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    sid = _sid(21)
    _write_safety_ok(safety, "cid-bad")
    _write_stream_refunded(payment, "cid-bad", sid, stage="egress")
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    assert "Property F" in out or "egress-refuse-with-paired-refuse" in out


def test_broken_payment_chain_fails(synthetic_repo: Path) -> None:
    """A tampered PAYMENT_LEDGER must FAIL before the stream-level
    walk begins."""
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_stream_settled(payment, "cid-1", _sid(30))
    with payment.open("rb+") as fh:
        raw = fh.read()
    mangled = raw.replace(b'"committed_XION":1000', b'"committed_XION":9999')
    payment.write_bytes(mangled)
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    assert "PAYMENT_LEDGER chain broken" in out


def test_non_hex_stream_id_caught_by_chain_verifier(synthetic_repo: Path) -> None:
    """A hand-forged row with a malformed stream_id breaks the hash
    chain (the chain verifier rejects it before our walk sees it)."""
    payment = synthetic_repo / "PAYMENT_LEDGER.jsonl"
    _write_stream_settled(payment, "cid-1", _sid(40))
    import json
    lines = payment.read_bytes().splitlines()
    row = json.loads(lines[0])
    row["stream_id"] = "ZZ" * 16  # invalid hex
    lines[0] = json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payment.write_bytes(b"\n".join(lines) + b"\n")
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
