"""Ledger tests. The chain-integrity property is load-bearing for Covenant
verifiability; every tamper vector gets a test."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.safety.ledger import (
    SCHEMA_VERSION,
    ZERO_HASH,
    ChainBroken,
    append,
    build_verdict,
    chain_tip,
    iter_rows,
    verify_chain,
)
from orchestrator.safety.types import Decision, EscalationReason


def _ok_verdict(correlation_id="c1", candidate="hello", ts=1_700_000_000_000_000_000):
    return build_verdict(
        correlation_id=correlation_id,
        candidate=candidate,
        timestamp_utc_ns=ts,
        decision=Decision.OK,
        summary="OK: no rule fired",
    )


def _refuse_verdict(correlation_id="c2", candidate="bad", ts=1_700_000_000_000_000_001):
    return build_verdict(
        correlation_id=correlation_id,
        candidate=candidate,
        timestamp_utc_ns=ts,
        decision=Decision.REFUSE,
        summary="refused",
        principle_id="7",
        rule_id="pii.email_address_v1",
        rule_version=1,
    )


def _escalate_verdict(correlation_id="c3", candidate="hmm", ts=1_700_000_000_000_000_002):
    return build_verdict(
        correlation_id=correlation_id,
        candidate=candidate,
        timestamp_utc_ns=ts,
        decision=Decision.ESCALATE,
        summary="escalated",
        principle_id="14",
        escalation_reason=EscalationReason.SUBJECTIVE_PRINCIPLE,
    )


# ----- tip on an empty / missing ledger --------------------------------------


def test_chain_tip_empty_is_zero_hash(ledger_path: Path):
    count, tip = chain_tip(ledger_path)
    assert (count, tip) == (0, ZERO_HASH)


def test_verify_chain_empty_returns_zero(ledger_path: Path):
    count, tip = verify_chain(ledger_path)
    assert (count, tip) == (0, ZERO_HASH)


# ----- append + verify -------------------------------------------------------


def test_single_append_links_to_zero_hash(ledger_path: Path):
    row = append(ledger_path, _ok_verdict())
    assert row["seq"] == 0
    assert row["prev_hash"] == ZERO_HASH
    assert row["schema_version"] == SCHEMA_VERSION

    count, tip = verify_chain(ledger_path)
    assert count == 1
    assert tip == row["this_hash"]


def test_consecutive_appends_chain(ledger_path: Path):
    r0 = append(ledger_path, _ok_verdict(correlation_id="a"))
    r1 = append(ledger_path, _refuse_verdict(correlation_id="b"))
    r2 = append(ledger_path, _escalate_verdict(correlation_id="c"))

    assert r1["prev_hash"] == r0["this_hash"]
    assert r2["prev_hash"] == r1["this_hash"]
    assert [r0["seq"], r1["seq"], r2["seq"]] == [0, 1, 2]

    count, tip = verify_chain(ledger_path)
    assert count == 3
    assert tip == r2["this_hash"]


def test_all_three_verdict_kinds_serialize(ledger_path: Path):
    append(ledger_path, _ok_verdict())
    append(ledger_path, _refuse_verdict())
    append(ledger_path, _escalate_verdict())
    verify_chain(ledger_path)
    rows = list(iter_rows(ledger_path))
    assert [r["verdict"] for r in rows] == ["ok", "refuse", "escalate"]


# ----- tamper detection ------------------------------------------------------


def _rewrite(path: Path, lines: list[bytes]) -> None:
    path.write_bytes(b"\n".join(lines) + b"\n")


def test_tamper_edit_in_place_detected(ledger_path: Path):
    append(ledger_path, _ok_verdict(correlation_id="original"))
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["correlation_id"] = "tampered"
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)

    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "this_hash" in str(ei.value)


def test_tamper_delete_middle_row_detected(ledger_path: Path):
    append(ledger_path, _ok_verdict(correlation_id="a"))
    append(ledger_path, _ok_verdict(correlation_id="b"))
    append(ledger_path, _ok_verdict(correlation_id="c"))
    raw = ledger_path.read_bytes().splitlines()
    _rewrite(ledger_path, [raw[0], raw[2]])

    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    # The surviving row 2 now appears at file-index 1 with seq=2; contiguity fails.
    assert "seq non-contiguous" in str(ei.value) or "prev_hash" in str(ei.value)


def test_tamper_inserted_row_detected(ledger_path: Path):
    append(ledger_path, _ok_verdict(correlation_id="a"))
    append(ledger_path, _ok_verdict(correlation_id="c"))
    raw = ledger_path.read_bytes().splitlines()
    # Synthesize a fake middle row
    fake = json.loads(raw[0])
    fake["seq"] = 1
    fake["correlation_id"] = "inserted"
    raw_fake = json.dumps(fake, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, [raw[0], raw_fake, raw[1]])

    with pytest.raises(ChainBroken):
        verify_chain(ledger_path)


def test_tamper_missing_required_field_detected(ledger_path: Path):
    append(ledger_path, _ok_verdict())
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    del row["summary"]
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)

    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "summary" in str(ei.value)


def test_verify_rejects_unknown_schema_version(ledger_path: Path):
    append(ledger_path, _ok_verdict())
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["schema_version"] = 999
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)
    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "schema_version" in str(ei.value)


# ----- conditional-field rules -----------------------------------------------


def test_verify_rejects_ok_with_principle_id(ledger_path: Path):
    append(ledger_path, _ok_verdict())
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["principle_id"] = "1"
    # Re-hash so we hit the conditional check, not the hash check.
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)

    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "principle_id" in str(ei.value)


def test_verify_rejects_refuse_without_rule_id(ledger_path: Path):
    append(ledger_path, _refuse_verdict())
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["rule_id"] = None
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)

    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "rule_id" in str(ei.value)


def test_verify_rejects_escalate_without_reason(ledger_path: Path):
    append(ledger_path, _escalate_verdict())
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["escalation_reason"] = None
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)
    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "escalation_reason" in str(ei.value)


# ----- determinism -----------------------------------------------------------


def test_canonical_bytes_are_deterministic():
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash
    row = {
        "z": 1, "a": "two", "m": None, "n": [3, 2, 1], "this_hash": "ignored"
    }
    b1 = _canonical_bytes_excluding_this_hash(row)
    # Rearrange insertion order; sort_keys makes output identical.
    row2 = {
        "n": [3, 2, 1], "this_hash": "other", "a": "two", "m": None, "z": 1
    }
    b2 = _canonical_bytes_excluding_this_hash(row2)
    assert b1 == b2
    assert b"this_hash" not in b1
