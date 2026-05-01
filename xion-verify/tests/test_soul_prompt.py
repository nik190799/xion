"""Tests for `xion-verify soul-prompt`."""

from __future__ import annotations

from click.testing import CliRunner

from xion_verify.cli import root as cli
from xion_verify.exit_codes import FAIL, OK


def test_soul_prompt_ok(synthetic_repo, monkeypatch):
    """A healthy repo passes."""
    monkeypatch.chdir(synthetic_repo)
    import hashlib
    path = synthetic_repo / "genesis" / "SOUL_PROMPT.md"
    content = path.read_bytes()
    new_hash = hashlib.sha256(content).hexdigest()

    import xion_verify.commands.soul_prompt
    original_get = xion_verify.commands.soul_prompt._get_pinned_hash
    xion_verify.commands.soul_prompt._get_pinned_hash = lambda: new_hash
    try:
        runner = CliRunner()
        result = runner.invoke(cli, ["soul-prompt"])
        if result.exit_code != OK:
            print(result.output)
        assert result.exit_code == OK
        assert "OK" in result.output
    finally:
        xion_verify.commands.soul_prompt._get_pinned_hash = original_get


def test_soul_prompt_missing(synthetic_repo, monkeypatch):
    """Missing file fails."""
    monkeypatch.chdir(synthetic_repo)
    (synthetic_repo / "genesis" / "SOUL_PROMPT.md").unlink()
    runner = CliRunner()
    result = runner.invoke(cli, ["soul-prompt"])
    assert result.exit_code == FAIL
    assert "FAIL" in result.output
    assert "not found" in result.output


def test_soul_prompt_hash_mismatch(synthetic_repo, monkeypatch):
    """Mutated file fails."""
    monkeypatch.chdir(synthetic_repo)
    path = synthetic_repo / "genesis" / "SOUL_PROMPT.md"
    path.write_text(path.read_text() + "\nmutated", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["soul-prompt"])
    assert result.exit_code == FAIL
    assert "FAIL" in result.output
    assert "hash mismatch" in result.output


def test_soul_prompt_missing_covenant_block(synthetic_repo, monkeypatch):
    """File without Covenant Block fails."""
    monkeypatch.chdir(synthetic_repo)
    path = synthetic_repo / "genesis" / "SOUL_PROMPT.md"
    content = path.read_text(encoding="utf-8")
    content = content.replace("## Covenant Block", "## Something Else")
    path.write_text(content, encoding="utf-8")

    # We also need to update the hash so it doesn't fail on hash mismatch first
    import hashlib
    new_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    # Mock the pinned hash
    import xion_verify.commands.soul_prompt
    original_get = xion_verify.commands.soul_prompt._get_pinned_hash
    xion_verify.commands.soul_prompt._get_pinned_hash = lambda: new_hash

    try:
        runner = CliRunner()
        result = runner.invoke(cli, ["soul-prompt"])
        assert result.exit_code == FAIL
        assert "FAIL" in result.output
        assert "does not declare the Covenant Block" in result.output
    finally:
        xion_verify.commands.soul_prompt._get_pinned_hash = original_get
