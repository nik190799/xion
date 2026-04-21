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


# ================================================= schema_version 2 (Phase 4b)


def _llm_judgement_ok():
    from orchestrator.safety.types import LlmJudgement
    return LlmJudgement(
        provider_id="stub-in-test",
        model_id="stub-in-test",
        provider_version=1,
        latency_ms=1,
        decision=Decision.OK,
        summary="stub ok",
        raw_output=b"stub-raw",
        confidence=0.9,
    )


def _llm_judgement_escalate():
    from orchestrator.safety.types import LlmJudgement
    return LlmJudgement(
        provider_id="stub-in-test",
        model_id="stub-in-test",
        provider_version=1,
        latency_ms=1,
        decision=Decision.ESCALATE,
        summary="stub escalate",
        raw_output=b"stub-raw",
        principle_id="3",
    )


def _llm_judgement_refuse():
    from orchestrator.safety.types import LlmJudgement
    return LlmJudgement(
        provider_id="stub-in-test",
        model_id="stub-in-test",
        provider_version=1,
        latency_ms=1,
        decision=Decision.REFUSE,
        summary="stub refuse",
        raw_output=b"stub-raw",
        principle_id="2",
    )


def test_v2_row_has_llm_verdict_field(ledger_path: Path):
    row = append(
        ledger_path,
        build_verdict(
            correlation_id="c",
            candidate="hi",
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK: v1+v2 pass",
            llm_verdict=_llm_judgement_ok(),
        ),
    )
    assert row["schema_version"] == SCHEMA_VERSION == 2
    assert row["llm_verdict"] is not None
    assert row["llm_verdict"]["decision"] == "ok"
    assert row["llm_verdict"]["provider_id"] == "stub-in-test"
    assert len(row["llm_verdict"]["raw_output_sha256"]) == 64
    count, _ = verify_chain(ledger_path)
    assert count == 1


def test_v2_row_llm_verdict_null_is_valid(ledger_path: Path):
    row = append(
        ledger_path,
        build_verdict(
            correlation_id="c",
            candidate="hi",
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.REFUSE,
            summary="refused by v1 rule",
            principle_id="7",
            rule_id="pii.email_v1",
            rule_version=1,
            llm_verdict=None,
        ),
    )
    assert "llm_verdict" in row
    assert row["llm_verdict"] is None
    count, _ = verify_chain(ledger_path)
    assert count == 1


def test_v2_row_missing_llm_verdict_field_rejected(ledger_path: Path):
    append(ledger_path, _ok_verdict())
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    assert "llm_verdict" in row
    del row["llm_verdict"]
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)
    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "llm_verdict" in str(ei.value)


def test_v2_row_llm_verdict_missing_required_subfield_rejected(ledger_path: Path):
    append(
        ledger_path,
        build_verdict(
            correlation_id="c",
            candidate="hi",
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="ok",
            llm_verdict=_llm_judgement_ok(),
        ),
    )
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    del row["llm_verdict"]["raw_output_sha256"]
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)
    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "llm_verdict" in str(ei.value)


def test_v2_row_llm_verdict_ok_with_principle_rejected(ledger_path: Path):
    append(
        ledger_path,
        build_verdict(
            correlation_id="c",
            candidate="hi",
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="ok",
            llm_verdict=_llm_judgement_ok(),
        ),
    )
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["llm_verdict"]["principle_id"] = "3"
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)
    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "principle_id" in str(ei.value)


def test_v2_escalate_with_v1_era_reason_allowed(ledger_path: Path):
    append(
        ledger_path,
        build_verdict(
            correlation_id="c",
            candidate="ambig",
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.ESCALATE,
            summary="v1 escalate",
            principle_id="14",
            escalation_reason=EscalationReason.SUBJECTIVE_PRINCIPLE,
            llm_verdict=None,
        ),
    )
    count, _ = verify_chain(ledger_path)
    assert count == 1


def test_v2_llm_arbiter_escalated_requires_non_null_llm_verdict(ledger_path: Path):
    append(
        ledger_path,
        build_verdict(
            correlation_id="c",
            candidate="ambig",
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.ESCALATE,
            summary="v2 escalate",
            principle_id="3",
            escalation_reason=EscalationReason.LLM_ARBITER_ESCALATED,
            llm_verdict=_llm_judgement_escalate(),
        ),
    )
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["llm_verdict"] = None
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)
    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "llm_arbiter_escalated" in str(ei.value)


def test_v2_refuse_produced_by_v2_requires_no_rule_id(ledger_path: Path):
    # The canonical "v2-produced refuse" row: rule_id null, llm_verdict.decision == refuse.
    row = append(
        ledger_path,
        build_verdict(
            correlation_id="c",
            candidate="subtle",
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.REFUSE,
            summary="v2 refuse",
            principle_id="2",
            rule_id=None,
            rule_version=None,
            llm_verdict=_llm_judgement_refuse(),
        ),
    )
    assert row["rule_id"] is None
    assert row["llm_verdict"]["decision"] == "refuse"
    count, _ = verify_chain(ledger_path)
    assert count == 1


def test_v2_refuse_without_rule_or_llm_rejected(ledger_path: Path):
    # A row that claims refuse but has neither a v1 rule nor a v2 judgement
    # with decision=refuse is malformed — fabricated forensics.
    append(ledger_path, _refuse_verdict())  # establish a valid seq=0
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["rule_id"] = None
    row["rule_version"] = None
    # llm_verdict is None in a proper v1 refuse; keep it None so neither path satisfies.
    assert row.get("llm_verdict") is None
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    _rewrite(ledger_path, raw)
    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "refuse" in str(ei.value)


def test_mixed_v1_and_v2_rows_chain_verifies(ledger_path: Path):
    """Core forward-compat property: a ledger file may contain a v1 row
    followed by v2 rows. prev_hash linkage and contiguity hold across
    the version boundary."""
    # Manually write a v1-shaped row with schema_version=1 and no
    # llm_verdict key. We cannot use build_verdict() for that because
    # writers always emit SCHEMA_VERSION (current). Hand-craft instead.
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    v1_row = {
        "schema_version": 1,
        "seq": 0,
        "prev_hash": ZERO_HASH,
        "timestamp_utc_ns": 1_700_000_000_000_000_000,
        "correlation_id": "legacy",
        "candidate_sha256": _sha256_hex(b"legacy"),
        "verdict": "ok",
        "summary": "OK: no rule fired",
        "principle_id": None,
        "rule_id": None,
        "rule_version": None,
        "escalation_reason": None,
    }
    v1_row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(v1_row))
    ledger_path.write_bytes(
        json.dumps(v1_row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        + b"\n"
    )
    # Now append v2 rows via the normal writer — they should chain onto seq=1.
    r1 = append(
        ledger_path,
        build_verdict(
            correlation_id="modern",
            candidate="hi",
            timestamp_utc_ns=1_700_000_000_000_000_001,
            decision=Decision.OK,
            summary="OK: v1+v2 pass",
            llm_verdict=_llm_judgement_ok(),
        ),
    )
    assert r1["seq"] == 1
    assert r1["prev_hash"] == v1_row["this_hash"]
    assert r1["schema_version"] == 2
    count, _ = verify_chain(ledger_path)
    assert count == 2


def test_v1_row_with_v2_only_field_rejected(ledger_path: Path):
    """A forged "v1" row that also contains llm_verdict is a schema
    violation — readers must reject, not silently accept."""
    from orchestrator.safety.ledger import _canonical_bytes_excluding_this_hash, _sha256_hex
    forged = {
        "schema_version": 1,
        "seq": 0,
        "prev_hash": ZERO_HASH,
        "timestamp_utc_ns": 1_700_000_000_000_000_000,
        "correlation_id": "forge",
        "candidate_sha256": _sha256_hex(b"forge"),
        "verdict": "ok",
        "summary": "OK",
        "principle_id": None,
        "rule_id": None,
        "rule_version": None,
        "escalation_reason": None,
        "llm_verdict": None,  # forbidden on v1 rows
    }
    forged["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(forged))
    ledger_path.write_bytes(
        json.dumps(forged, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        + b"\n"
    )
    with pytest.raises(ChainBroken) as ei:
        verify_chain(ledger_path)
    assert "v2-only field" in str(ei.value)


# ---------------------------------------------------------------- determinism


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
