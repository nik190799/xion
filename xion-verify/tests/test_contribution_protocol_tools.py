from __future__ import annotations

import base64
import json
from pathlib import Path

from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from xion_verify.cli import root
from xion_verify.exit_codes import FAIL, OK


def _seed_witnesses(tmp_path: Path) -> None:
    (tmp_path / "genesis").mkdir(exist_ok=True)
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("# stub", encoding="utf-8")
    (tmp_path / "docs" / "00-INDEX.md").write_text("# stub", encoding="utf-8")
    (tmp_path / "genesis" / "COVENANT.md").write_text("# Covenant", encoding="utf-8")
    (tmp_path / "genesis" / "INVARIANTS.md").write_text("# Invariants", encoding="utf-8")


def _seed_schemas(tmp_path: Path) -> None:
    schemas = tmp_path / "docs" / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    (schemas / "levels.yaml").write_text(
        "schema_version: 1\n"
        "source_doctrine: docs/14-UPGRADE-PATHS.md\n"
        "source_sha256:   " + ("0" * 64) + "\n"
        "status: canonical\n"
        "levels:\n"
        "  - id: 2\n"
        "    name: The Relay\n"
        "    proposer: community_or_xion\n"
        "    artifacts: [orchestrator/**/*.py]\n"
        "    gate: [harm_analyzer]\n"
        "    tier: 0\n"
        "    canary: canary_relay\n"
        "    ship: rolling_upgrade\n"
        "    rollback: supervisor_revert\n"
        "    ledger: RELAY_UPGRADE_LEDGER\n"
        "    sunset_review: continuous\n"
        "  - id: 12\n"
        "    name: The Meta\n"
        "    proposer: anyone\n"
        "    artifacts: [docs/14-UPGRADE-PATHS.md]\n"
        "    gate: [retrospective_sim]\n"
        "    tier: 3\n"
        "    canary: parallel_provisioning\n"
        "    ship: adopt_template\n"
        "    rollback: revert_template\n"
        "    ledger: META_LEDGER\n"
        "    sunset_review: five_year\n",
        encoding="utf-8",
    )
    (schemas / "roles.yaml").write_text(
        "schema_version: 1\n"
        "source_doctrine: docs/09-GOVERNANCE.md\n"
        "source_sha256:   " + ("0" * 64) + "\n"
        "status: canonical\n"
        "actors:\n"
        "  - id: community\n"
        "    name: Community\n"
        "    key_class: wallet\n"
        "    scope_summary: comm\n"
        "    authorized_levels: [2, 12]\n"
        "  - id: xion\n"
        "    name: Xion\n"
        "    key_class: relay\n"
        "    scope_summary: self\n"
        "    authorized_levels: [2]\n"
        "level_proposer_resolution:\n"
        "  community_or_xion:\n"
        "    actors: [community, xion]\n"
        "  anyone:\n"
        "    actors: [community]\n"
        "github_identity_map:\n"
        "  community:\n    handles: []\n"
        "  xion:\n    handles: []\n",
        encoding="utf-8",
    )


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def test_which_level_classifies_paths(tmp_path: Path, monkeypatch) -> None:
    _seed_witnesses(tmp_path)
    _seed_schemas(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["which-level", "orchestrator/api/app.py"])

    assert result.exit_code == OK, result.output
    assert "Level 2" in result.output
    assert "The Relay" in result.output


def test_which_level_fails_mixed_path_set(tmp_path: Path, monkeypatch) -> None:
    _seed_witnesses(tmp_path)
    _seed_schemas(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        root,
        ["which-level", "orchestrator/api/app.py", "docs/14-UPGRADE-PATHS.md"],
    )

    assert result.exit_code == FAIL
    assert "does not resolve to one upgrade level" in result.output


def test_new_proposal_touches_prefills_upgrade_frontmatter(tmp_path: Path, monkeypatch) -> None:
    _seed_witnesses(tmp_path)
    _seed_schemas(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        root,
        ["new", "proposal", "demo", "--touches", "orchestrator/api/app.py"],
    )

    assert result.exit_code == OK, result.output
    proposal = tmp_path / "proposals" / "demo.md"
    assert proposal.exists()
    content = proposal.read_text(encoding="utf-8")
    assert "level: 2 # The Relay" in content
    assert "proposer: community_or_xion" in content
    assert "# authorized_actors: community, xion" in content


def test_identity_bindings_verifies_ed25519_row(tmp_path: Path, monkeypatch) -> None:
    _seed_witnesses(tmp_path)
    monkeypatch.chdir(tmp_path)
    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    row = {
        "schema_version": 1,
        "purpose": "xion-contributor-identity-binding-v1",
        "github_handle": "@alice",
        "wallet_pubkey_ed25519_base64url": _b64url(pub),
        "signed_at_utc": "2026-04-25T17:00:00Z",
    }
    message = (
        "xion-contributor-identity-binding-v1\n"
        "github_handle=@alice\n"
        f"wallet_pubkey_ed25519_base64url={row['wallet_pubkey_ed25519_base64url']}\n"
        "signed_at_utc=2026-04-25T17:00:00Z"
    )
    row["signed_message"] = message
    row["signature_ed25519_base64url"] = _b64url(key.sign(message.encode("utf-8")))
    ledger = tmp_path / "ledgers" / "CONTRIBUTOR_IDENTITY_BINDINGS.jsonl"
    ledger.parent.mkdir()
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    result = CliRunner().invoke(root, ["identity-bindings"])

    assert result.exit_code == OK, result.output
    assert "1 binding row" in result.output


def test_mcp_export_is_read_only_json(tmp_path: Path, monkeypatch) -> None:
    _seed_witnesses(tmp_path)
    _seed_schemas(tmp_path)
    (tmp_path / "KNOWN_WEAKNESSES.md").write_text(
        "## Open\n\n### KW-TEST-001 — Example gap\n- **Status:** open\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["mcp-export", "--compact"])

    assert result.exit_code == OK, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "read_only"
    assert "no_state_writes" in payload["guardrails"]
    assert payload["known_weaknesses_open"][0]["id"] == "KW-TEST-001"
