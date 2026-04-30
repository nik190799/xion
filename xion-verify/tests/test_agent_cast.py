from __future__ import annotations

import hashlib
import json
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.exit_codes import OK


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed_cast_repo(tmp_path: Path, *, write_row: bool) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "genesis" / "AGENT_SOULS").mkdir(parents=True)
    (tmp_path / "ledgers").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("# index", encoding="utf-8")
    doctrine = tmp_path / "docs" / "HERMES_PIN_PROTOCOL.md"
    doctrine.write_text("# Hermes", encoding="utf-8")
    parent = tmp_path / "genesis" / "SOUL.md"
    parent.write_text("# Soul", encoding="utf-8")
    parent_hash = _sha(parent)
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
    manifest_hash = hashlib.sha256(schema.read_bytes() + soul.read_bytes()).hexdigest()
    (tmp_path / "genesis" / "AGENT_SOULS" / "MANIFEST.txt").write_text(
        f"manifest_payload_sha256: {manifest_hash}\n"
        f"genesis/AGENT_SOULS/_SCHEMA.md sha256: {_sha(schema)}\n"
        f"genesis/AGENT_SOULS/research-agent.yaml sha256: {_sha(soul)}\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "ledgers" / "AGENT_CAST_LEDGER.jsonl"
    ledger.write_text("# seed\n", encoding="utf-8")
    if write_row:
        row = {
            "schema_version": 1,
            "event": "cast_succeeded",
            "agent_id": "research-agent",
            "agent_soul_hash": _sha(soul),
            "parent_soul_hash": parent_hash,
            "hermes_pin": "abc123",
            "cast_at": "2026-04-25T17:00:00Z",
            "smoke_test_pass": True,
        }
        ledger.write_text("# seed\n" + json.dumps(row) + "\n", encoding="utf-8")


def test_agent_cast_accepts_seeded_empty_ledger(tmp_path: Path, monkeypatch) -> None:
    _seed_cast_repo(tmp_path, write_row=False)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["agent-cast"])

    assert result.exit_code == OK, result.output
    assert "0 cast row" in result.output
    assert "no live cast rows yet" in result.output


def test_agent_cast_verifies_cast_row(tmp_path: Path, monkeypatch) -> None:
    _seed_cast_repo(tmp_path, write_row=True)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["agent-cast"])

    assert result.exit_code == OK, result.output
    assert "1 cast row" in result.output
