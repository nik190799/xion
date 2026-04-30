from __future__ import annotations

import json
from pathlib import Path

from orchestrator.sustainability.ladder import CostPressureLadder


def _proposal_rows(repo_root: Path) -> list[dict[str, object]]:
    path = repo_root / "ledgers" / "PROPOSAL_LEDGER.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_substrate_vitality_trip_emits_tier3_proposal(tmp_path: Path) -> None:
    ladder = CostPressureLadder(tmp_path)

    ladder.check_substrate_pressure("arweave-storage", cost_ratio=1.0, vitality_band="critical")

    rows = _proposal_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["tier"] == 3
    assert rows[0]["title"] == "Cost-Pressure: Substrate-cutover for arweave-storage"
    assert "vitality_band=critical" in str(rows[0]["description"])
    assert "do not execute autonomous migration" in str(rows[0]["description"])


def test_substrate_cost_ratio_trip_emits_tier3_proposal(tmp_path: Path) -> None:
    ladder = CostPressureLadder(tmp_path)

    ladder.check_substrate_pressure("base-settlement", cost_ratio=1.5, vitality_band="healthy")

    rows = _proposal_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["tier"] == 3
    assert rows[0]["title"] == "Cost-Pressure: Substrate-cutover for base-settlement"
    assert "cost_ratio=1.5 >= 1.5" in str(rows[0]["description"])


def test_substrate_pressure_below_threshold_does_not_emit(tmp_path: Path) -> None:
    ladder = CostPressureLadder(tmp_path)

    ladder.check_substrate_pressure("ao-compute", cost_ratio=1.49, vitality_band="warning")

    assert _proposal_rows(tmp_path) == []
