from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root


def test_new_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")

    runner = CliRunner()
    result = runner.invoke(root, ["new", "skill", "testskill"])
    assert result.exit_code == 0

    assert (tmp_path / "skills" / "testskill" / "__init__.py").exists()
    assert (tmp_path / "skills" / "testskill" / "skill.py").exists()
    assert (tmp_path / "tests" / "skills" / "test_testskill.py").exists()

    content = (tmp_path / "skills" / "testskill" / "__init__.py").read_text()
    assert "1. What property does this promise?" in content


def test_new_sense(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")

    runner = CliRunner()
    result = runner.invoke(root, ["new", "sense", "testsense"])
    assert result.exit_code == 0

    assert (tmp_path / "orchestrator" / "senses" / "testsense" / "__init__.py").exists()
    assert (tmp_path / "orchestrator" / "senses" / "testsense" / "sense.py").exists()
    assert (tmp_path / "orchestrator" / "tests" / "senses" / "test_testsense.py").exists()


def test_new_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")

    runner = CliRunner()
    result = runner.invoke(root, ["new", "provider", "testprovider"])
    assert result.exit_code == 0

    assert (tmp_path / "orchestrator" / "inference_router" / "providers" / "testprovider.py").exists()
    assert (tmp_path / "orchestrator" / "tests" / "inference_router" / "providers" / "test_testprovider.py").exists()


def test_new_verifier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")

    runner = CliRunner()
    result = runner.invoke(root, ["new", "verifier", "test-verifier"])
    assert result.exit_code == 0

    assert (tmp_path / "xion-verify" / "src" / "xion_verify" / "commands" / "test_verifier.py").exists()
    assert (tmp_path / "xion-verify" / "tests" / "test_test_verifier.py").exists()


def test_new_proposal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")

    runner = CliRunner()
    result = runner.invoke(root, ["new", "proposal", "test-proposal"])
    assert result.exit_code == 0

    assert (tmp_path / "proposals" / "test-proposal.md").exists()
