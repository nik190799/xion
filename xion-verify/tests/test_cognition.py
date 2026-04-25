from __future__ import annotations

import hashlib
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.exit_codes import FAIL


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cognition_rejects_arbiter_importing_hermes(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "genesis" / "AGENT_SOULS").mkdir(parents=True)
    (tmp_path / "ledgers").mkdir()
    (tmp_path / "orchestrator" / "safety").mkdir(parents=True)
    (tmp_path / "docs" / "00-INDEX.md").write_text("# index", encoding="utf-8")
    (tmp_path / "docs" / "24-COGNITION.md").write_text("# cognition", encoding="utf-8")
    doctrine = tmp_path / "docs" / "HERMES_PIN_PROTOCOL.md"
    doctrine.write_text("# Hermes", encoding="utf-8")
    (tmp_path / "genesis" / "UNKNOWNS.md").write_text("# unknowns", encoding="utf-8")
    parent = tmp_path / "genesis" / "SOUL.md"
    parent.write_text("# Soul", encoding="utf-8")
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
        "agent_tool_allowlist:\n"
        "  research-agent:\n"
        "    allowed_tools: [hermes.tool.web_fetch]\n",
        encoding="utf-8",
    )
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text(
        f"hermes_agent_commit: abc123\nhermes_tool_allowlist_sha256: {_sha(allowlist)}\n",
        encoding="utf-8",
    )
    schema = tmp_path / "genesis" / "AGENT_SOULS" / "_SCHEMA.md"
    schema.write_text("# schema", encoding="utf-8")
    soul = tmp_path / "genesis" / "AGENT_SOULS" / "research-agent.yaml"
    soul.write_text(
        "schema_version: 1\n"
        "agent_id: research-agent\n"
        "soul_version: 1\n"
        f"extends_soul_hash: {_sha(parent)}\n"
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
    manifest_hash = hashlib.sha256(schema.read_bytes() + soul.read_bytes()).hexdigest()
    (tmp_path / "genesis" / "AGENT_SOULS" / "MANIFEST.txt").write_text(
        f"manifest_payload_sha256: {manifest_hash}\n",
        encoding="utf-8",
    )
    (tmp_path / "ledgers" / "AGENT_CAST_LEDGER.jsonl").write_text("# seed\n", encoding="utf-8")
    (tmp_path / "orchestrator" / "safety" / "api.py").write_text(
        "from orchestrator.cognition.hermes.daemon import DaemonWrapper\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["cognition"])

    assert result.exit_code == FAIL
    assert "forbidden Arbiter/Hermes boundary import" in result.output
