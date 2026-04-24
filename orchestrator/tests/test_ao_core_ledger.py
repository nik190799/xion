"""Tests for orchestrator.ao_core.ledger."""

import json
import os
from pathlib import Path

import pytest

from orchestrator.ao_core.ledger import (
    ChainBroken,
    StateChainRecord,
    ZERO_HASH,
    append,
    chain_tip,
    iter_rows,
    verify_chain,
)


@pytest.fixture
def ledger_path(tmp_path: Path) -> Path:
    return tmp_path / "STATE_CHAIN_LEDGER.jsonl"


def test_append_and_verify(ledger_path: Path) -> None:
    # Fresh file
    count, tip = verify_chain(ledger_path)
    assert count == 0
    assert tip == ZERO_HASH

    record1 = StateChainRecord(
        correlation_id="corr1",
        height=1,
        state_root_sha256="1" * 64,
        prev_state_root_sha256="0" * 64,
        ao_process_id="proc1",
        ao_message_id="msg1",
        committed_by="deployer",
        committed_at_unix=1234567890,
    )
    row1 = append(ledger_path, record1)
    
    count, tip = verify_chain(ledger_path)
    assert count == 1
    assert tip == row1["this_hash"]
    assert row1["seq"] == 0
    assert row1["prev_row_sha256"] == ZERO_HASH

    record2 = StateChainRecord(
        correlation_id="corr2",
        height=2,
        state_root_sha256="2" * 64,
        prev_state_root_sha256="1" * 64,
        ao_process_id="proc1",
        ao_message_id="msg2",
        committed_by="deployer",
        committed_at_unix=1234567891,
    )
    row2 = append(ledger_path, record2)
    
    count, tip = verify_chain(ledger_path)
    assert count == 2
    assert tip == row2["this_hash"]
    assert row2["seq"] == 1
    assert row2["prev_row_sha256"] == row1["this_hash"]


def test_chain_broken_tampered_hash(ledger_path: Path) -> None:
    record1 = StateChainRecord(
        correlation_id="corr1",
        height=1,
        state_root_sha256="1" * 64,
        prev_state_root_sha256="0" * 64,
        ao_process_id="proc1",
        ao_message_id="msg1",
        committed_by="deployer",
        committed_at_unix=1234567890,
    )
    append(ledger_path, record1)
    
    # Tamper with the file
    lines = ledger_path.read_text().splitlines()
    row = json.loads(lines[0])
    row["height"] = 999
    lines[0] = json.dumps(row)
    ledger_path.write_text("\n".join(lines) + "\n")
    
    with pytest.raises(ChainBroken, match="this_hash recomputation mismatch"):
        verify_chain(ledger_path)


def test_chain_broken_prev_hash(ledger_path: Path) -> None:
    record1 = StateChainRecord(
        correlation_id="corr1",
        height=1,
        state_root_sha256="1" * 64,
        prev_state_root_sha256="0" * 64,
        ao_process_id="proc1",
        ao_message_id="msg1",
        committed_by="deployer",
        committed_at_unix=1234567890,
    )
    append(ledger_path, record1)
    
    record2 = StateChainRecord(
        correlation_id="corr2",
        height=2,
        state_root_sha256="2" * 64,
        prev_state_root_sha256="1" * 64,
        ao_process_id="proc1",
        ao_message_id="msg2",
        committed_by="deployer",
        committed_at_unix=1234567891,
    )
    append(ledger_path, record2)
    
    # Tamper with the second row's prev_hash
    lines = ledger_path.read_text().splitlines()
    row = json.loads(lines[1])
    row["prev_row_sha256"] = "bad_hash"
    lines[1] = json.dumps(row)
    ledger_path.write_text("\n".join(lines) + "\n")
    
    with pytest.raises(ChainBroken, match="prev_row_sha256=bad_hash != expected"):
        verify_chain(ledger_path)
