"""Tests for `xion-verify sensorium-ledger` — the Phase 5c walker."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)
from orchestrator.sensorium.ledger import append_distress, append_tick_commit
from xion_verify.commands.sensorium_ledger import sensorium_ledger
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


def _invoke(ledger_path: Path) -> tuple[int, str]:
    runner = CliRunner()
    result = runner.invoke(sensorium_ledger, ["--path", str(ledger_path)])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output


def _benign_state() -> SensoriumState:
    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=0.0, source="textual"),
    )


def test_missing_ledger_is_not_yet_sealed(tmp_path: Path):
    code, out = _invoke(tmp_path / "SENSORIUM_LEDGER.jsonl")
    assert code == NOT_YET_SEALED
    assert "NOT_YET_SEALED" in out


def test_empty_ledger_is_not_yet_sealed(tmp_path: Path):
    p = tmp_path / "SENSORIUM_LEDGER.jsonl"
    p.write_bytes(b"")  # explicit empty file
    code, out = _invoke(p)
    assert code == NOT_YET_SEALED
    assert "empty" in out.lower()


def test_healthy_chain_is_ok(tmp_path: Path):
    p = tmp_path / "SENSORIUM_LEDGER.jsonl"
    append_distress(
        p,
        distress_score=0.7,
        channel="textual",
        as_of_utc_ns=1_700_000_000_000_000_000,
        relay_id="relay-test",
        correlation_id=None,
    )
    append_tick_commit(p, state=_benign_state(), relay_id="relay-test")
    code, out = _invoke(p)
    assert code == OK, out
    assert "sensorium-ledger: OK" in out
    assert "event_type=distress" in out
    assert "event_type=tick_commit" in out


def test_tampered_chain_fails(tmp_path: Path):
    p = tmp_path / "SENSORIUM_LEDGER.jsonl"
    append_distress(
        p,
        distress_score=0.7,
        channel="textual",
        as_of_utc_ns=1_700_000_000_000_000_000,
        relay_id="relay-test",
    )
    # In-place edit of the row's distress_score without updating this_hash.
    raw = p.read_text(encoding="utf-8")
    tampered = raw.replace('"distress_score":0.7', '"distress_score":0.1')
    assert tampered != raw, "test setup failed: could not tamper"
    p.write_text(tampered, encoding="utf-8")
    code, out = _invoke(p)
    assert code == FAIL
    assert "chain broken" in out.lower()
