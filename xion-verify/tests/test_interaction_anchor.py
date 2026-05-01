"""Tests for interaction_anchor verifier."""

import json
import sys
import urllib.request
from pathlib import Path
from unittest.mock import Mock

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


def test_verify_interaction_anchor_confirms_ao_batch(tmp_path: Path, monkeypatch, capsys):
    root = _write_request_anchor_with_ao_message(tmp_path)
    _write_receipt(tmp_path)

    monkeypatch.setenv("XION_AO_GATEWAY_URL", "http://localhost:4004")
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_with_batches([root]))

    res = verify_interaction_anchor(tmp_path, sys.stdout)

    assert res == 0
    assert "also confirmed on AO Core" in capsys.readouterr().out


def test_verify_interaction_anchor_fails_when_ao_message_missing_on_process(
    tmp_path: Path, monkeypatch, capsys
):
    _write_request_anchor_with_ao_message(tmp_path)
    _write_receipt(tmp_path)

    monkeypatch.setenv("XION_AO_GATEWAY_URL", "http://localhost:4004")
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_with_batches([]))

    res = verify_interaction_anchor(tmp_path, sys.stdout)

    assert res == 1
    assert "ao_message_id is set but batch_root_sha256 not found" in capsys.readouterr().out


def _write_request_anchor_with_ao_message(tmp_path: Path) -> str:
    anchor_path = tmp_path / "ledgers" / "ANCHOR_LEDGER.jsonl"
    anchor_path.parent.mkdir(parents=True)
    req_path = tmp_path / "REQUEST_LEDGER.jsonl"
    row = {"correlation_id": "c1", "request_arrived_utc_ns": 33000 * 1_000_000_000}
    req_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    from orchestrator.anchor.ledger import append
    from orchestrator.anchor.merkle import build_leaf, compute_root

    from xion_verify.commands.interaction_anchor import _sha256_canonical

    root = compute_root([build_leaf("c1", "request", _sha256_canonical(row))])
    append(
        path=anchor_path,
        period_start_unix=32400,
        period_end_unix=36000,
        ledger_kind="request",
        batch_root_sha256=root,
        batch_size=1,
        leaf_correlation_ids=["c1"],
        ao_message_id="ao-message-1",
    )
    return root


def _write_receipt(tmp_path: Path) -> None:
    receipt_path = tmp_path / "genesis" / "AO_DEPLOY_RECEIPT.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(
        json.dumps({"process_id": "proc-1", "signer_address": "owner-1"}),
        encoding="utf-8",
    )


def _urlopen_with_batches(batch_roots: list[str]):
    payload = json.dumps(
        {"Output": {"data": {"output": json.dumps([{"batch_root_sha256": r} for r in batch_roots])}}}
    ).encode("utf-8")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return payload

    return Mock(return_value=Response())
