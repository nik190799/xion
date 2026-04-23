"""CLI wiring tests. We don't re-test the library through argparse — we test
that the subcommands dispatch to the right functions with the right args."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from orchestrator.safety.__main__ import main


def test_cli_principles_subcommand(capsys: pytest.CaptureFixture[str]):
    rc = main(["principles"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Covenant principles known to the Arbiter" in out
    # Every principle id appears somewhere.
    for pid in ("1", "2", "3", "14", "14a", "14b"):
        assert f" {pid}" in out or f" {pid:>3}" in out


def test_cli_verify_ledger_empty_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    ledger = tmp_path / "SAFETY_LEDGER.jsonl"
    rc = main(["verify-ledger", "--ledger", str(ledger)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "verify-ledger: OK" in out
    assert "rows=0" in out


def test_cli_verify_ledger_after_gates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    from orchestrator.safety import gate
    ledger = tmp_path / "SAFETY_LEDGER.jsonl"
    gate("hi", correlation_id="c1", ledger_path=ledger)
    gate("bye", correlation_id="c2", ledger_path=ledger)

    rc = main(["verify-ledger", "--ledger", str(ledger)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "rows=2" in out


def test_cli_verify_ledger_on_tampered_file_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    from orchestrator.safety import gate
    ledger = tmp_path / "SAFETY_LEDGER.jsonl"
    gate("hi", correlation_id="c1", ledger_path=ledger)
    # Corrupt the file
    raw = ledger.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["correlation_id"] = "tampered"
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ledger.write_bytes(b"\n".join(raw) + b"\n")

    rc = main(["verify-ledger", "--ledger", str(ledger)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "FAIL" in err


def test_cli_gate_returns_1_on_refuse(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    ledger = tmp_path / "SAFETY_LEDGER.jsonl"
    monkeypatch.setattr(sys, "stdin", io.StringIO("Her SSN is 123-45-6789."))
    rc = main(["gate", "--correlation-id", "c-bad", "--ledger", str(ledger)])
    out = capsys.readouterr().out
    assert rc == 1  # refuse = non-zero
    payload = json.loads(out)
    assert payload["decision"] == "refuse"
    assert payload["egress_allowed"] is False


def test_cli_gate_returns_0_on_ok(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    ledger = tmp_path / "SAFETY_LEDGER.jsonl"
    monkeypatch.setattr(sys, "stdin", io.StringIO("hello world"))
    rc = main(["gate", "--correlation-id", "c-good", "--ledger", str(ledger)])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["decision"] == "ok"
    assert payload["egress_allowed"] is True
