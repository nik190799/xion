"""Tests for the ANCHOR_LEDGER."""

import json
from pathlib import Path

import pytest

from orchestrator.anchor.ledger import (
    SCHEMA_VERSION,
    ZERO_HASH,
    AnchorRecord,
    ChainBrokenError,
    append,
    chain_tip,
    verify_chain,
)


def test_append_and_verify_chain(tmp_path: Path):
    ledger_path = tmp_path / "ANCHOR_LEDGER.jsonl"

    # Empty tip
    seq, tip_hash = chain_tip(ledger_path)
    assert seq == 0
    assert tip_hash == ZERO_HASH

    # Append row 1
    rec1 = append(
        path=ledger_path,
        period_start_unix=1000,
        period_end_unix=2000,
        ledger_kind="request",
        batch_root_sha256="a"*64,
        batch_size=2,
        leaf_correlation_ids=["c1", "c2"]
    )

    assert rec1.seq == 0
    assert rec1.schema_version == SCHEMA_VERSION
    assert rec1.prev_hash == ZERO_HASH
    assert len(rec1.this_hash) == 64

    recs = verify_chain(ledger_path)
    assert len(recs) == 1
    assert recs[0].this_hash == rec1.this_hash

    # Append row 2
    rec2 = append(
        path=ledger_path,
        period_start_unix=2000,
        period_end_unix=3000,
        ledger_kind="payment",
        batch_root_sha256="b"*64,
        batch_size=1,
        leaf_correlation_ids=["c3"]
    )

    assert rec2.seq == 1
    assert rec2.prev_hash == rec1.this_hash

    recs = verify_chain(ledger_path)
    assert len(recs) == 2

def test_tamper_prev_hash(tmp_path: Path):
    ledger_path = tmp_path / "ANCHOR_LEDGER.jsonl"
    append(ledger_path, 100, 200, "request", "a"*64, 1, ["c1"])
    append(ledger_path, 200, 300, "request", "b"*64, 1, ["c2"])

    lines = ledger_path.read_text().splitlines()
    row2 = json.loads(lines[1])
    row2["prev_hash"] = ZERO_HASH
    lines[1] = json.dumps(row2)
    ledger_path.write_text("\n".join(lines) + "\n")

    with pytest.raises(ChainBrokenError, match="prev_hash mismatch"):
        verify_chain(ledger_path)

def test_tamper_this_hash(tmp_path: Path):
    ledger_path = tmp_path / "ANCHOR_LEDGER.jsonl"
    append(ledger_path, 100, 200, "request", "a"*64, 1, ["c1"])

    lines = ledger_path.read_text().splitlines()
    row1 = json.loads(lines[0])
    row1["batch_size"] = 99
    lines[0] = json.dumps(row1)
    ledger_path.write_text("\n".join(lines) + "\n")

    with pytest.raises(ChainBrokenError, match="Invalid record"):
        verify_chain(ledger_path)

def test_invalid_construction():
    with pytest.raises(ValueError, match="must be strictly sorted"):
        AnchorRecord(1, 0, "a"*64, "b"*64, 100, 200, "request", "c"*64, 2, ["z", "a"])
