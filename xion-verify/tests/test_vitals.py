from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root


def test_vitals_not_yet_sealed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")

    # Needs orchestrator.vitals
    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent.parent))

    runner = CliRunner()
    result = runner.invoke(root, ["vitals"])
    assert result.exit_code == 2
    assert "NOT_YET_SEALED" in result.output
