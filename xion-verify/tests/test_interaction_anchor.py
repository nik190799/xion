"""Tests for interaction_anchor verifier."""

import json
from pathlib import Path
import sys
from xion_verify.commands.interaction_anchor import verify_interaction_anchor

def test_verify_interaction_anchor_empty(tmp_path: Path, capsys):
    # Missing anchor ledger returns OK
    res = verify_interaction_anchor(tmp_path, sys.stdout)
    assert res == 0

def test_verify_interaction_anchor_valid(tmp_path: Path, capsys):
    anchor_path = tmp_path / "ledgers" / "ANCHOR_LEDGER.jsonl"
    anchor_path.parent.mkdir(parents=True)
    req_path = tmp_path / "REQUEST_LEDGER.jsonl"
    
    row = {"correlation_id": "c1", "request_arrived_utc_ns": 33000 * 1_000_000_000, "final_outcome": "ok"}
    req_path.write_text(json.dumps(row) + "\n")
    
    from orchestrator.anchor.ledger import append
    from orchestrator.anchor.merkle import build_leaf, compute_root
    from xion_verify.commands.interaction_anchor import _sha256_canonical
    
    leaf_hash = build_leaf("c1", "request", _sha256_canonical(row))
    root = compute_root([leaf_hash])
    
    append(
        path=anchor_path,
        period_start_unix=32400,
        period_end_unix=36000,
        ledger_kind="request",
        batch_root_sha256=root,
        batch_size=1,
        leaf_correlation_ids=["c1"]
    )
    
    res = verify_interaction_anchor(tmp_path, sys.stdout)
    assert res == 0
    assert "1 anchors cross-checked" in capsys.readouterr().out

def test_verify_interaction_anchor_missing_source(tmp_path: Path, capsys):
    anchor_path = tmp_path / "ledgers" / "ANCHOR_LEDGER.jsonl"
    anchor_path.parent.mkdir(parents=True)
    
    from orchestrator.anchor.ledger import append
    append(
        path=anchor_path,
        period_start_unix=32400,
        period_end_unix=36000,
        ledger_kind="request",
        batch_root_sha256="a"*64,
        batch_size=1,
        leaf_correlation_ids=["c1"]
    )
    
    import sys
    res = verify_interaction_anchor(tmp_path, sys.stdout)
    assert res == 1
    assert "Source ledger request not found" in capsys.readouterr().out
