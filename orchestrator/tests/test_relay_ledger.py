"""Tests for `orchestrator/relay/ledger.py` (REQUEST_LEDGER).

Mirrors the discipline of `test_ledger.py` for SAFETY_LEDGER: every
tamper vector and every schema violation gets a test. Hash-chain
integrity is load-bearing for `xion-verify refund-fidelity`; the
chain breakage discovery surface here is what makes the cross-ledger
join trustworthy.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.relay.ledger import (
    SCHEMA_VERSION,
    ZERO_HASH,
    ChainBroken,
    RequestRecord,
    append,
    chain_tip,
    iter_rows,
    verify_chain,
)


@pytest.fixture
def request_ledger_path(tmp_path: Path) -> Path:
    return tmp_path / "REQUEST_LEDGER.jsonl"


def _record(
    *,
    state_height_int: int = 1_700_000_000_000_000_000,
    nonce_hex: str = "abcdef0123456789abcdef0123456789",
    request_arrived_utc_ns: int = 1_700_000_000_000_000_000,
    responded_utc_ns: int | None = 1_700_000_000_000_000_100,
    gate_call_count: int = 1,
    final_outcome: str = "ok",
    gate_latency_ms_total: int = 5,
    relay_id: str = "relay-test",
) -> RequestRecord:
    sh = f"{state_height_int:016x}"
    return RequestRecord(
        correlation_id=f"{sh}:{nonce_hex}",
        state_height=sh,
        request_arrived_utc_ns=request_arrived_utc_ns,
        responded_utc_ns=responded_utc_ns,
        gate_call_count=gate_call_count,
        final_outcome=final_outcome,
        gate_latency_ms_total=gate_latency_ms_total,
        relay_id=relay_id,
    )


# ----- RequestRecord construction validation --------------------------------


def test_record_rejects_empty_correlation_id():
    with pytest.raises(ValueError):
        RequestRecord(
            correlation_id="",
            state_height="abc",
            request_arrived_utc_ns=1,
            responded_utc_ns=2,
            gate_call_count=1,
            final_outcome="ok",
            gate_latency_ms_total=1,
            relay_id="r",
        )


def test_record_rejects_bad_final_outcome():
    with pytest.raises(ValueError):
        _record(final_outcome="maybe")


def test_record_rejects_negative_arrival_ts():
    with pytest.raises(ValueError):
        _record(request_arrived_utc_ns=-1)


def test_record_allows_null_responded_ts():
    rec = _record(responded_utc_ns=None)
    assert rec.responded_utc_ns is None


def test_record_rejects_negative_gate_latency():
    with pytest.raises(ValueError):
        _record(gate_latency_ms_total=-5)


def test_record_rejects_state_height_correlation_mismatch():
    with pytest.raises(ValueError):
        RequestRecord(
            correlation_id="0000000000000001:abcd",
            state_height="0000000000000002",
            request_arrived_utc_ns=1,
            responded_utc_ns=2,
            gate_call_count=1,
            final_outcome="ok",
            gate_latency_ms_total=1,
            relay_id="r",
        )


def test_record_rejects_empty_relay_id():
    with pytest.raises(ValueError):
        _record(relay_id="")


# ----- empty / missing file --------------------------------------------------


def test_chain_tip_empty_is_zero_hash(request_ledger_path: Path):
    count, tip = chain_tip(request_ledger_path)
    assert (count, tip) == (0, ZERO_HASH)


def test_verify_chain_empty_returns_zero(request_ledger_path: Path):
    count, tip = verify_chain(request_ledger_path)
    assert (count, tip) == (0, ZERO_HASH)


def test_iter_rows_missing_file_yields_nothing(request_ledger_path: Path):
    assert list(iter_rows(request_ledger_path)) == []


# ----- append + verify -------------------------------------------------------


def test_single_append_links_to_zero_hash(request_ledger_path: Path):
    row = append(request_ledger_path, _record())
    assert row["seq"] == 0
    assert row["prev_hash"] == ZERO_HASH
    assert row["schema_version"] == SCHEMA_VERSION
    assert row["final_outcome"] == "ok"
    assert row["gate_call_count"] == 1


def test_two_appends_chain_correctly(request_ledger_path: Path):
    r0 = append(request_ledger_path, _record(state_height_int=1, nonce_hex="0" * 32))
    r1 = append(
        request_ledger_path,
        _record(state_height_int=2, nonce_hex="1" * 32),
    )
    assert r1["seq"] == 1
    assert r1["prev_hash"] == r0["this_hash"]
    count, tip = chain_tip(request_ledger_path)
    assert count == 2
    assert tip == r1["this_hash"]


def test_verify_chain_passes_on_clean_file(request_ledger_path: Path):
    for i in range(5):
        append(
            request_ledger_path,
            _record(state_height_int=1000 + i, nonce_hex=f"{i:032x}"),
        )
    count, tip = verify_chain(request_ledger_path)
    assert count == 5
    # tip equals the last row's this_hash
    last = list(iter_rows(request_ledger_path))[-1]
    assert tip == last["this_hash"]


def test_verify_chain_handles_all_three_outcomes(request_ledger_path: Path):
    for i, outcome in enumerate(("ok", "refuse", "escalate")):
        append(
            request_ledger_path,
            _record(state_height_int=2000 + i, nonce_hex=f"{i:032x}", final_outcome=outcome),
        )
    count, _ = verify_chain(request_ledger_path)
    assert count == 3


def test_responded_utc_null_is_accepted_by_chain(request_ledger_path: Path):
    append(request_ledger_path, _record(responded_utc_ns=None))
    count, _ = verify_chain(request_ledger_path)
    assert count == 1


# ----- canonicalization determinism -----------------------------------------


def test_canonical_bytes_deterministic_across_field_order(request_ledger_path: Path):
    """Hash recomputation must not depend on key insertion order."""
    row = append(request_ledger_path, _record())
    # Re-emit the same row dict with shuffled key order; the verifier
    # canonicalises before hashing, so it should still match.
    raw = request_ledger_path.read_bytes()
    parsed = json.loads(raw.decode("utf-8").splitlines()[0])
    shuffled = dict(reversed(list(parsed.items())))
    request_ledger_path.write_bytes(
        (json.dumps(shuffled, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    )
    count, tip = verify_chain(request_ledger_path)
    assert count == 1
    assert tip == row["this_hash"]


# ----- tamper detection ------------------------------------------------------


def test_in_place_edit_breaks_chain(request_ledger_path: Path):
    append(request_ledger_path, _record())
    # Flip the relay_id silently. this_hash recompute will not match.
    raw = request_ledger_path.read_bytes()
    parsed = json.loads(raw.decode("utf-8").splitlines()[0])
    parsed["relay_id"] = "tampered"
    request_ledger_path.write_bytes(
        (json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    )
    with pytest.raises(ChainBroken, match="this_hash recomputation mismatch"):
        verify_chain(request_ledger_path)


def test_seq_non_contiguous_breaks_chain(request_ledger_path: Path):
    append(request_ledger_path, _record(state_height_int=1, nonce_hex="0" * 32))
    append(request_ledger_path, _record(state_height_int=2, nonce_hex="1" * 32))
    # Swap the two lines (so seq goes 1, 0) — the prev_hash check will
    # fire BEFORE seq contiguity in our walker, but either is a fine
    # failure mode; assert we get *some* ChainBroken.
    lines = request_ledger_path.read_bytes().splitlines()
    request_ledger_path.write_bytes(b"\n".join([lines[1], lines[0]]) + b"\n")
    with pytest.raises(ChainBroken):
        verify_chain(request_ledger_path)


def test_deleted_middle_row_breaks_chain(request_ledger_path: Path):
    append(request_ledger_path, _record(state_height_int=1, nonce_hex="0" * 32))
    append(request_ledger_path, _record(state_height_int=2, nonce_hex="1" * 32))
    append(request_ledger_path, _record(state_height_int=3, nonce_hex="2" * 32))
    lines = request_ledger_path.read_bytes().splitlines()
    request_ledger_path.write_bytes(b"\n".join([lines[0], lines[2]]) + b"\n")
    with pytest.raises(ChainBroken):
        verify_chain(request_ledger_path)


def test_missing_required_field_breaks_chain(request_ledger_path: Path):
    append(request_ledger_path, _record())
    raw = request_ledger_path.read_bytes()
    parsed = json.loads(raw.decode("utf-8").splitlines()[0])
    del parsed["relay_id"]
    request_ledger_path.write_bytes(
        (json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    )
    with pytest.raises(ChainBroken, match="missing required field"):
        verify_chain(request_ledger_path)


def test_bad_schema_version_breaks_chain(request_ledger_path: Path):
    append(request_ledger_path, _record())
    raw = request_ledger_path.read_bytes()
    parsed = json.loads(raw.decode("utf-8").splitlines()[0])
    parsed["schema_version"] = 999
    request_ledger_path.write_bytes(
        (json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    )
    with pytest.raises(ChainBroken, match="schema_version=999"):
        verify_chain(request_ledger_path)


def test_bad_final_outcome_breaks_chain(request_ledger_path: Path):
    """Construct a row that bypasses RequestRecord validation by writing
    raw JSON directly. A reader that trusted the file blindly would
    accept it; the verifier must reject."""
    bad = {
        "schema_version": 1,
        "seq": 0,
        "prev_hash": ZERO_HASH,
        "correlation_id": "0000000000000001:abc",
        "state_height": "0000000000000001",
        "request_arrived_utc_ns": 1,
        "responded_utc_ns": 2,
        "gate_call_count": 1,
        "final_outcome": "totally_fine",
        "gate_latency_ms_total": 1,
        "relay_id": "r",
    }
    # Compute a valid this_hash so the chain check passes that step
    # and we hit the enum check specifically.
    body = {k: v for k, v in bad.items() if k != "this_hash"}
    import hashlib
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    bad["this_hash"] = hashlib.sha256(canonical).hexdigest()
    request_ledger_path.write_bytes(
        (json.dumps(bad, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    )
    with pytest.raises(ChainBroken, match="final_outcome"):
        verify_chain(request_ledger_path)


def test_duplicate_correlation_id_breaks_chain(request_ledger_path: Path):
    """correlation_id is unique within REQUEST_LEDGER at schema_version 1.
    Constructing two RequestRecord with the same correlation_id is
    legal at the dataclass layer (the dataclass cannot see other rows);
    the verifier catches it on read."""
    rec1 = _record(state_height_int=1, nonce_hex="0" * 32)
    append(request_ledger_path, rec1)
    # Build a second record with a different state_height_int so the
    # dataclass check passes, then surgically rewrite its correlation_id
    # to collide. This simulates a buggy Relay that issued a duplicate.
    rec2 = _record(state_height_int=2, nonce_hex="1" * 32)
    append(request_ledger_path, rec2)
    # Tamper: rewrite the second row's correlation_id to match the first.
    lines = request_ledger_path.read_bytes().splitlines()
    parsed = json.loads(lines[1].decode("utf-8"))
    parsed["correlation_id"] = rec1.correlation_id
    parsed["state_height"] = rec1.state_height
    body = {k: v for k, v in parsed.items() if k != "this_hash"}
    import hashlib
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    parsed["this_hash"] = hashlib.sha256(canonical).hexdigest()
    new_line = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    # Recompute the prev_hash chain by keeping line 0 unchanged.
    request_ledger_path.write_bytes(lines[0] + b"\n" + new_line + b"\n")
    # The chain may now break on prev_hash (since we changed parsed)
    # or on the duplicate detection — either is correct; assert ChainBroken.
    with pytest.raises(ChainBroken):
        verify_chain(request_ledger_path)


# ----- iter_rows correctness -------------------------------------------------


def test_iter_rows_yields_in_order(request_ledger_path: Path):
    written = []
    for i in range(4):
        row = append(
            request_ledger_path,
            _record(state_height_int=1000 + i, nonce_hex=f"{i:032x}"),
        )
        written.append(row["correlation_id"])
    read = [r["correlation_id"] for r in iter_rows(request_ledger_path)]
    assert read == written


def test_iter_rows_skips_blank_lines(request_ledger_path: Path):
    append(request_ledger_path, _record(state_height_int=1, nonce_hex="0" * 32))
    request_ledger_path.write_bytes(request_ledger_path.read_bytes() + b"\n\n")
    rows = list(iter_rows(request_ledger_path))
    assert len(rows) == 1


# ----- ledger row content cross-check ---------------------------------------


def test_appended_row_is_self_consistent(request_ledger_path: Path):
    """The row we get back from append() round-trips through iter_rows
    byte-identically."""
    row = append(request_ledger_path, _record())
    rows_on_disk = list(iter_rows(request_ledger_path))
    assert rows_on_disk == [row]
