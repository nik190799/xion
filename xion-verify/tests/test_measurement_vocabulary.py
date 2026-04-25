from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from xion_verify.commands.measurement_vocabulary import measurement_vocabulary
from xion_verify.exit_codes import FAIL, OK


def _seed_repo(root: Path, *, forbidden_line: str | None = None, monthly_usd: bool = False) -> None:
    docs = root / "docs"
    genesis = root / "genesis"
    souls = genesis / "AGENT_SOULS"
    docs.mkdir()
    souls.mkdir(parents=True)
    (docs / "00-INDEX.md").write_text("# index\n", encoding="utf-8")
    (genesis / "GENESIS_ARTIFACT.md").write_text("# genesis\n", encoding="utf-8")
    (docs / "MEASUREMENT-VOCABULARY.md").write_text(
        "# Measurement Vocabulary\n\n"
        "- `runway_weeks`\n"
        "- `fraction_of_operating_float`\n"
        "- `fraction_of_improvement_fund`\n"
        "- `distance_to_reserve_floor`\n"
        "- `recurring_burn_ratio`\n",
        encoding="utf-8",
    )
    for name in (
        "SPEND-AUTONOMY.md",
        "19-TREASURY.md",
        "21-SUSTAINABILITY.md",
        "24-COGNITION.md",
        "27-RESEARCH-SPEND.md",
    ):
        body = (
            "# Doctrine\n\n"
            "Uses [`MEASUREMENT-VOCABULARY.md`](./MEASUREMENT-VOCABULARY.md), "
            "`runway_weeks`, and `distance_to_reserve_floor`.\n"
        )
        if forbidden_line and name == "SPEND-AUTONOMY.md":
            body += forbidden_line + "\n"
        (docs / name).write_text(body, encoding="utf-8")
    envelope = (
        "monthly_usd: 10\n  unit: USD"
        if monthly_usd
        else "monthly_envelope_fraction: 0.04\n  unit: fraction_of_improvement_fund"
    )
    (souls / "research-agent.yaml").write_text(
        "schema_version: 1\n"
        "agent_id: research-agent\n"
        "cost_envelope:\n"
        f"  {envelope}\n",
        encoding="utf-8",
    )


def test_measurement_vocabulary_positive_fixture(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(measurement_vocabulary, [])

    assert result.exit_code == OK, result.output
    assert "OK" in result.output


def test_measurement_vocabulary_rejects_forbidden_time_gate(
    tmp_path: Path, monkeypatch
) -> None:
    _seed_repo(tmp_path, forbidden_line="S2 unlocks after 90 days of clean operation.")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(measurement_vocabulary, [])

    assert result.exit_code == FAIL
    assert "elapsed-time authority gate" in result.output


def test_measurement_vocabulary_rejects_monthly_usd_agent_soul(
    tmp_path: Path, monkeypatch
) -> None:
    _seed_repo(tmp_path, monthly_usd=True)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(measurement_vocabulary, [])

    assert result.exit_code == FAIL
    assert "monthly_usd" in result.output
