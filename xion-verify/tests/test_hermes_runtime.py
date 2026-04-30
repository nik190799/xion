from __future__ import annotations

import hashlib
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.exit_codes import OK


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hermes_runtime_verifies_allowlist_and_artifact_pin(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "genesis").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("# index", encoding="utf-8")
    doctrine = tmp_path / "docs" / "HERMES_PIN_PROTOCOL.md"
    doctrine.write_text("# Hermes Pin Protocol", encoding="utf-8")
    doctrine_hash = _sha(doctrine)
    allowlist = tmp_path / "genesis" / "HERMES_TOOL_ALLOWLIST.yaml"
    allowlist.write_text(
        "schema_version: 1\n"
        "source_doctrine: docs/HERMES_PIN_PROTOCOL.md\n"
        f"source_sha256: {doctrine_hash}\n"
        "status: canonical\n"
        "hermes_pin:\n"
        "  repo: https://example.invalid/hermes\n"
        "  tag: v1\n"
        "  commit: abc123\n"
        "default_deny: true\n"
        "disabled_runtime_flags:\n"
        "  skill_self_improvement: false\n"
        "  autonomous_skill_creation: false\n"
        "  mcp_server_auto_discovery: false\n"
        "  user_model_export: false\n"
        "agent_tool_allowlist: {}\n",
        encoding="utf-8",
    )
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text(
        "hermes_agent_commit:  abc123\n"
        f"hermes_tool_allowlist_sha256: {_sha(allowlist)}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["hermes-runtime"])

    assert result.exit_code == OK, result.output
    assert "default-deny flags verified" in result.output
    assert "runtime dependency pin is NOT_YET_SEALED" in result.output


def test_hermes_runtime_verifies_vendored_lock_pin(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "genesis").mkdir()
    (tmp_path / "xion_hermes_runtime").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("# index", encoding="utf-8")
    doctrine = tmp_path / "docs" / "HERMES_PIN_PROTOCOL.md"
    doctrine.write_text("# Hermes Pin Protocol", encoding="utf-8")
    adapter = tmp_path / "xion_hermes_runtime" / "__init__.py"
    adapter.write_text('HERMES_AGENT_COMMIT = "abc123"\n', encoding="utf-8")
    allowlist = tmp_path / "genesis" / "HERMES_TOOL_ALLOWLIST.yaml"
    allowlist.write_text(
        "schema_version: 1\n"
        "source_doctrine: docs/HERMES_PIN_PROTOCOL.md\n"
        f"source_sha256: {_sha(doctrine)}\n"
        "status: canonical\n"
        "hermes_pin:\n"
        "  repo: https://example.invalid/hermes\n"
        "  tag: v1\n"
        "  commit: abc123\n"
        "default_deny: true\n"
        "disabled_runtime_flags:\n"
        "  skill_self_improvement: false\n"
        "  autonomous_skill_creation: false\n"
        "  mcp_server_auto_discovery: false\n"
        "  user_model_export: false\n"
        "agent_tool_allowlist: {}\n",
        encoding="utf-8",
    )
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text(
        "hermes_agent_commit: abc123\n"
        f"hermes_tool_allowlist_sha256: {_sha(allowlist)}\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.lock").write_text(
        "xion-hermes-runtime==0.1.0\n"
        "    artifact_path=xion_hermes_runtime/__init__.py\n"
        f"    artifact_sha256={_sha(adapter)}\n"
        "    hermes_agent_commit=abc123\n"
        "    source=vendored-adapter\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["hermes-runtime"])

    assert result.exit_code == OK, result.output
    assert "default-deny flags verified" in result.output
    assert "NOT_YET_SEALED" not in result.output
