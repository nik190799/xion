from __future__ import annotations

import hashlib
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.exit_codes import FAIL, OK


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed_agent_soul_repo(tmp_path: Path, *, agent_id: str = "research-agent") -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "genesis" / "AGENT_SOULS").mkdir(parents=True)
    (tmp_path / "docs" / "00-INDEX.md").write_text("# index", encoding="utf-8")
    (tmp_path / "docs" / "HERMES_PIN_PROTOCOL.md").write_text("# Hermes", encoding="utf-8")
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("# artifact", encoding="utf-8")
    parent = tmp_path / "genesis" / "SOUL.md"
    parent.write_text("# Soul", encoding="utf-8")
    parent_hash = _sha(parent)
    allowlist = tmp_path / "genesis" / "HERMES_TOOL_ALLOWLIST.yaml"
    allowlist.write_text(
        "hermes_pin:\n"
        "  commit: abc123\n"
        "default_deny: true\n"
        "disabled_runtime_flags:\n"
        "  skill_self_improvement: false\n"
        "  autonomous_skill_creation: false\n"
        "  mcp_server_auto_discovery: false\n"
        "  user_model_export: false\n"
        "agent_tool_allowlist:\n"
        f"  {agent_id}:\n"
        "    allowed_tools: [hermes.tool.web_fetch]\n",
        encoding="utf-8",
    )
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text(
        f"hermes_agent_commit: abc123\nhermes_tool_allowlist_sha256: {_sha(allowlist)}\n",
        encoding="utf-8",
    )
    (tmp_path / "genesis" / "AGENT_SOULS" / "_SCHEMA.md").write_text("# schema", encoding="utf-8")
    soul = tmp_path / "genesis" / "AGENT_SOULS" / f"{agent_id}.yaml"
    soul.write_text(
        "schema_version: 1\n"
        f"agent_id: {agent_id}\n"
        "soul_version: 1\n"
        f"extends_soul_hash: {parent_hash}\n"
        "purpose: test\n"
        "trigger: {type: cron}\n"
        "allowed_tools: [hermes.tool.web_fetch]\n"
        "forbidden_tools: []\n"
        "mcp_servers_allowed: []\n"
        "cost_envelope: {monthly_usd: 1, bucket: test}\n"
        "output_destinations: [{type: ledger, name: TEST}]\n"
        "arbiter_class: test\n"
        "limits: {max_turn_depth: 0, max_wall_clock_s: 1, max_tokens_per_run: 1}\n"
        "deprecation_path: test\n",
        encoding="utf-8",
    )
    payload_hash = hashlib.sha256(
        (tmp_path / "genesis" / "AGENT_SOULS" / "_SCHEMA.md").read_bytes() + soul.read_bytes()
    ).hexdigest()
    (tmp_path / "genesis" / "AGENT_SOULS" / "MANIFEST.txt").write_text(
        f"manifest_payload_sha256: {payload_hash}\n",
        encoding="utf-8",
    )


def test_agent_souls_verifies_parent_hash_and_allowlist(tmp_path: Path, monkeypatch) -> None:
    _seed_agent_soul_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["agent-souls"])

    assert result.exit_code == OK, result.output
    assert "1 Agent Soul" in result.output


def test_agent_souls_rejects_arbiter_soul(tmp_path: Path, monkeypatch) -> None:
    _seed_agent_soul_repo(tmp_path, agent_id="arbiter")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["agent-souls"])

    assert result.exit_code == FAIL
    assert "arbiter must not be an Agent Soul" in result.output
