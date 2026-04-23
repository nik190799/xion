"""Tests for `orchestrator.sensorium.ledger` (SENSORIUM_LEDGER).

Mirrors the `test_ledger.py` and `test_relay_ledger.py` patterns: each
test writes to its own tmp_path ledger so nothing touches the repo
root.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)
from orchestrator.sensorium.ledger import (
    SCHEMA_VERSION,
    ZERO_HASH,
    ChainBroken,
    append_distress,
    append_tick_commit,
    canonical_state_hash,
    chain_tip,
    iter_rows,
    tally_by_event_type,
    verify_chain,
)


@pytest.fixture
def sensorium_path(tmp_path: Path) -> Path:
    return tmp_path / "SENSORIUM_LEDGER.jsonl"


def _benign_state(as_of: int = 123_456_789) -> SensoriumState:
    """Deterministic benign SensoriumState for hash-stability assertions.

    Every sub-sense constructor's ``as_of_utc_ns`` defaults to
    ``time.time_ns()`` via ``field(default_factory=...)`` — correct for
    production paths, wrong for tests that assert
    ``canonical_state_hash(a) == canonical_state_hash(b)`` across two
    constructions. We thread a single ``as_of`` nanosecond stamp through
    every sub-sense so the whole state is a pure function of ``as_of``.
    """
    return SensoriumState(
        interoception=Interoception(
            survival_pressure=0.0,
            treasury_stress=0.0,
            cost_pressure=0.0,
            as_of_utc_ns=as_of,
        ),
        chronoception=Chronoception(as_of_utc_ns=as_of),
        proprioception=Proprioception(as_of_utc_ns=as_of),
        distress=DistressSignal(text_distress_score=0.0, as_of_utc_ns=as_of),
        as_of_utc_ns=as_of,
    )


# -------------------------------------------------------- empty / tip state


def test_empty_file_tip_is_zero_hash(sensorium_path: Path):
    count, tip = chain_tip(sensorium_path)
    assert count == 0
    assert tip == ZERO_HASH


def test_verify_empty_file_ok(sensorium_path: Path):
    count, tip = verify_chain(sensorium_path)
    assert count == 0
    assert tip == ZERO_HASH


# -------------------------------------------------------- append + chain


def test_append_distress_produces_well_formed_row(sensorium_path: Path):
    row = append_distress(
        sensorium_path,
        distress_score=0.8,
        channel="textual",
        as_of_utc_ns=1_000_000_000,
        relay_id="relay-local-d2",
        correlation_id="abcd:ef01",
    )
    assert row["schema_version"] == SCHEMA_VERSION
    assert row["seq"] == 0
    assert row["prev_hash"] == ZERO_HASH
    assert row["event_type"] == "distress"
    assert row["channel"] == "textual"
    assert row["distress_score"] == 0.8
    assert row["snapshot_hash"] is None
    assert row["correlation_id"] == "abcd:ef01"
    assert len(row["this_hash"]) == 64


def test_append_distress_saturates_out_of_range_scores(sensorium_path: Path):
    row_high = append_distress(
        sensorium_path,
        distress_score=1.9,
        channel="textual",
        as_of_utc_ns=1,
        relay_id="relay-local-d2",
    )
    row_low = append_distress(
        sensorium_path,
        distress_score=-0.3,
        channel="textual",
        as_of_utc_ns=2,
        relay_id="relay-local-d2",
    )
    assert row_high["distress_score"] == 1.0
    assert row_low["distress_score"] == 0.0


def test_append_distress_rejects_unknown_channel(sensorium_path: Path):
    with pytest.raises(ValueError):
        append_distress(
            sensorium_path,
            distress_score=0.5,
            channel="visual",
            as_of_utc_ns=1,
            relay_id="relay-local-d2",
        )


def test_append_tick_commit_pins_snapshot_hash(sensorium_path: Path):
    state = _benign_state()
    expected = canonical_state_hash(state)
    row = append_tick_commit(sensorium_path, state=state, relay_id="relay-local-d2")
    assert row["event_type"] == "tick_commit"
    assert row["distress_score"] is None
    assert row["snapshot_hash"] == expected
    assert row["correlation_id"] is None


def test_canonical_state_hash_is_stable(sensorium_path: Path):
    a = _benign_state(as_of=42)
    b = _benign_state(as_of=42)
    assert canonical_state_hash(a) == canonical_state_hash(b)


def test_append_chain_is_linked(sensorium_path: Path):
    r0 = append_distress(
        sensorium_path,
        distress_score=0.6,
        channel="textual",
        as_of_utc_ns=1,
        relay_id="r",
    )
    r1 = append_tick_commit(
        sensorium_path,
        state=_benign_state(as_of=2),
        relay_id="r",
    )
    r2 = append_distress(
        sensorium_path,
        distress_score=0.9,
        channel="textual",
        as_of_utc_ns=3,
        relay_id="r",
    )
    assert r1["prev_hash"] == r0["this_hash"]
    assert r2["prev_hash"] == r1["this_hash"]
    assert r0["seq"] == 0 and r1["seq"] == 1 and r2["seq"] == 2


def test_verify_chain_returns_row_count_and_tip(sensorium_path: Path):
    for i in range(4):
        append_distress(
            sensorium_path,
            distress_score=0.6,
            channel="textual",
            as_of_utc_ns=i + 1,
            relay_id="r",
        )
    count, tip = verify_chain(sensorium_path)
    assert count == 4
    # last written row's this_hash should equal tip
    last_row = list(iter_rows(sensorium_path))[-1]
    assert tip == last_row["this_hash"]


# -------------------------------------------------------- tamper detection


def _rewrite_rows(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
               for r in rows),
        encoding="utf-8",
    )


def test_verify_detects_in_place_tamper(sensorium_path: Path):
    append_distress(sensorium_path, distress_score=0.5, channel="textual",
                    as_of_utc_ns=1, relay_id="r")
    append_distress(sensorium_path, distress_score=0.9, channel="textual",
                    as_of_utc_ns=2, relay_id="r")
    rows = list(iter_rows(sensorium_path))
    rows[0]["distress_score"] = 0.0   # flip a score; does NOT re-hash
    _rewrite_rows(sensorium_path, rows)
    with pytest.raises(ChainBroken):
        verify_chain(sensorium_path)


def test_verify_detects_seq_gap(sensorium_path: Path):
    append_distress(sensorium_path, distress_score=0.5, channel="textual",
                    as_of_utc_ns=1, relay_id="r")
    append_distress(sensorium_path, distress_score=0.5, channel="textual",
                    as_of_utc_ns=2, relay_id="r")
    rows = list(iter_rows(sensorium_path))
    rows = [rows[1]]  # drop seq=0
    _rewrite_rows(sensorium_path, rows)
    with pytest.raises(ChainBroken):
        verify_chain(sensorium_path)


def test_verify_rejects_distress_row_missing_score(sensorium_path: Path):
    append_distress(sensorium_path, distress_score=0.5, channel="textual",
                    as_of_utc_ns=1, relay_id="r")
    rows = list(iter_rows(sensorium_path))
    rows[0]["distress_score"] = None
    _rewrite_rows(sensorium_path, rows)
    with pytest.raises(ChainBroken):
        verify_chain(sensorium_path)


def test_verify_rejects_tick_commit_missing_snapshot_hash(sensorium_path: Path):
    append_tick_commit(sensorium_path, state=_benign_state(), relay_id="r")
    rows = list(iter_rows(sensorium_path))
    rows[0]["snapshot_hash"] = None
    _rewrite_rows(sensorium_path, rows)
    with pytest.raises(ChainBroken):
        verify_chain(sensorium_path)


def test_verify_rejects_unknown_event_type(sensorium_path: Path):
    append_distress(sensorium_path, distress_score=0.5, channel="textual",
                    as_of_utc_ns=1, relay_id="r")
    rows = list(iter_rows(sensorium_path))
    rows[0]["event_type"] = "elated"
    _rewrite_rows(sensorium_path, rows)
    with pytest.raises(ChainBroken):
        verify_chain(sensorium_path)


def test_verify_rejects_unknown_schema_version(sensorium_path: Path):
    append_distress(sensorium_path, distress_score=0.5, channel="textual",
                    as_of_utc_ns=1, relay_id="r")
    rows = list(iter_rows(sensorium_path))
    rows[0]["schema_version"] = 2
    _rewrite_rows(sensorium_path, rows)
    with pytest.raises(ChainBroken):
        verify_chain(sensorium_path)


# -------------------------------------------------------- tallies


def test_tally_by_event_type(sensorium_path: Path):
    append_distress(sensorium_path, distress_score=0.7, channel="textual",
                    as_of_utc_ns=1, relay_id="r")
    append_distress(sensorium_path, distress_score=0.9, channel="textual",
                    as_of_utc_ns=2, relay_id="r")
    append_tick_commit(sensorium_path, state=_benign_state(), relay_id="r")
    t = tally_by_event_type(sensorium_path)
    assert t["distress"]["textual"] == 2
    assert t["tick_commit"]["textual"] == 1
