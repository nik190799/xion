from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import _build_root

root = _build_root()


def test_auto_research_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()
    (tmp_path / "docs" / "RESEARCH_SOURCES.md").write_text("# Sources\n", encoding="utf-8")

    # Pre-create the ledgers so we can test append
    (tmp_path / "ledgers").mkdir()
    
    runner = CliRunner()
    result = runner.invoke(root, ["auto-research"])
    assert result.exit_code == 0
    assert "OK (loop alive, journal advancing, zero unresolved blocks, budget respected)" in result.output
    
    # Verify the journal was written
    journal_file = tmp_path / "ledgers" / "RESEARCH_JOURNAL.jsonl"
    assert journal_file.is_file()
    content = journal_file.read_text(encoding="utf-8")
    assert "Found an optimization" in content
    
    # Verify the proposal was written
    proposal_file = tmp_path / "ledgers" / "PROPOSAL_LEDGER.jsonl"
    assert proposal_file.is_file()
    content = proposal_file.read_text(encoding="utf-8")
    assert "Optimization" in content
