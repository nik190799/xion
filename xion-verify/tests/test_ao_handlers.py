"""Tests for `xion-verify ao-handlers`.

Covers the schema-doctrine branches (Phase 6.0 surface) and the deploy-receipt
+ gateway-round-trip branches (Phase 6.1 surface, with the `"dummy" in pid`
bypass removed).
"""

import json
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import _build_root
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.hashing import sha256_file

_CLI = _build_root()

_HANDLERS = (
    "commit-state", "attest", "treasury-spend", "registry-update", "spend", "slash-imprint",
    "rotate-authority", "abdicate-tier",
    "provision-relay", "provision-inference", "provision-storage", "provision-bandwidth", "provision-witness",
    "route-slices", "improvement-spend", "reserve-draw", "accept-donation", "enter-hibernation", "exit-hibernation",
)


def _seed_doctrine(tmp_path: Path) -> tuple[str, str]:
    """Write the two doctrine files and return their hashes."""
    schemas = tmp_path / "docs/schemas"
    schemas.mkdir(parents=True)
    arch_path = tmp_path / "docs/04-ARCHITECTURE.md"
    core_path = tmp_path / "docs/28-AO-CORE.md"
    arch_path.write_text("arch")
    core_path.write_text("core")
    return sha256_file(arch_path), sha256_file(core_path)


def _seed_full_schemas(tmp_path: Path) -> None:
    arch_hash, core_hash = _seed_doctrine(tmp_path)
    for h in _HANDLERS:
        content = (
            f"handler: {h}\n"
            "family: lifecycle\n"
            "schema_version: 1\n"
            "status: doctrine_only\n"
            "args: []\n"
            "state_changes: []\n"
            "failure_modes: []\n"
            "source_doctrine: docs/04-ARCHITECTURE.md\n"
            f"source_sha256: {arch_hash}\n"
            "operational_doctrine: docs/28-AO-CORE.md\n"
            f"operational_sha256: {core_hash}\n"
        )
        (tmp_path / f"docs/schemas/ao-handler-{h}.yaml").write_text(content)


def _seed_lua(tmp_path: Path, body: str = "-- xion ao core skeleton\n") -> Path:
    lua = tmp_path / "ao/core/main.lua"
    lua.parent.mkdir(parents=True, exist_ok=True)
    lua.write_text(body)
    return lua


def _write_receipt(tmp_path: Path, payload: dict) -> Path:
    receipt = tmp_path / "genesis" / "AO_DEPLOY_RECEIPT.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(payload))
    return receipt


def test_ao_handlers_not_yet_sealed_no_dir(tmp_path: Path, monkeypatch) -> None:
    """Missing docs/schemas/ returns NOT_YET_SEALED."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == NOT_YET_SEALED
    assert "NOT_YET_SEALED" in result.output


def test_ao_handlers_fail_missing_doctrine(tmp_path: Path, monkeypatch) -> None:
    """Missing doctrine files returns FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    (tmp_path / "docs/schemas").mkdir(parents=True)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "doctrine files not found" in result.output


def test_ao_handlers_not_yet_sealed_no_yaml(tmp_path: Path, monkeypatch) -> None:
    """Missing ao-handler-*.yaml files returns NOT_YET_SEALED."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _seed_doctrine(tmp_path)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == NOT_YET_SEALED
    assert "no ao-handler-*.yaml files found" in result.output


def test_ao_handlers_not_yet_sealed_no_lua(tmp_path: Path, monkeypatch) -> None:
    """Schemas valid but no ao/core/main.lua → NOT_YET_SEALED, awaiting Lua skeleton."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _seed_full_schemas(tmp_path)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == NOT_YET_SEALED
    assert "19 handler schema(s) verified, awaiting Lua skeleton" in result.output
    assert "ao/core/main.lua" in result.output


def test_ao_handlers_not_yet_sealed_no_receipt(tmp_path: Path, monkeypatch) -> None:
    """Schemas + Lua present but no receipt → NOT_YET_SEALED awaiting receipt."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _seed_full_schemas(tmp_path)
    _seed_lua(tmp_path)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == NOT_YET_SEALED
    assert "awaiting genesis/AO_DEPLOY_RECEIPT.json" in result.output


def test_ao_handlers_not_yet_sealed_placeholder_receipt(tmp_path: Path, monkeypatch) -> None:
    """Placeholder receipt → NOT_YET_SEALED with the new precise remediation string.

    This is the central honesty property: the previous bypass returned OK on
    'dummy' PIDs without any network round-trip. The replacement returns
    NOT_YET_SEALED and names exactly what a real receipt requires.
    """
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _seed_full_schemas(tmp_path)
    _seed_lua(tmp_path)
    _write_receipt(tmp_path, {
        "status": "placeholder",
        "process_id": "ao_testnet_dummy_pid_1234567890",
        "signer_address": None,
        "lua_source_sha256": None,
        "aos_version": None,
    })
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == NOT_YET_SEALED
    assert "AO_DEPLOY_RECEIPT.json is a placeholder" in result.output
    assert "lua_source_sha256" in result.output
    assert "STATE_CHAIN_LEDGER" in result.output
    assert "KW-AOCORE-001" in result.output


def test_ao_handlers_fail_invalid_receipt_json(tmp_path: Path, monkeypatch) -> None:
    """Malformed receipt JSON → FAIL (never silently NOT_YET_SEALED)."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _seed_full_schemas(tmp_path)
    _seed_lua(tmp_path)
    receipt = tmp_path / "genesis" / "AO_DEPLOY_RECEIPT.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text("{not: valid json")
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "cannot parse genesis/AO_DEPLOY_RECEIPT.json" in result.output


def test_ao_handlers_fail_real_receipt_missing_required_fields(tmp_path: Path, monkeypatch) -> None:
    """Non-placeholder receipt missing required fields → FAIL with explicit list."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _seed_full_schemas(tmp_path)
    _seed_lua(tmp_path)
    _write_receipt(tmp_path, {
        "process_id": "real_pid_abc",
        # signer_address, lua_source_sha256, aos_version intentionally missing
    })
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "missing required fields for a non-placeholder receipt" in result.output
    assert "signer_address" in result.output
    assert "lua_source_sha256" in result.output
    assert "aos_version" in result.output


def test_ao_handlers_fail_lua_hash_mismatch(tmp_path: Path, monkeypatch) -> None:
    """Real receipt whose lua_source_sha256 disagrees with current bytes → FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _seed_full_schemas(tmp_path)
    _seed_lua(tmp_path, "-- the bytes that are actually on disk\n")
    _write_receipt(tmp_path, {
        "process_id": "real_pid_abc",
        "signer_address": "addr_xyz",
        "lua_source_sha256": "0" * 64,
        "aos_version": "v2.0.1",
    })
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "lua_source_sha256 in AO_DEPLOY_RECEIPT.json does not match current ao/core/main.lua bytes" in result.output


def test_ao_handlers_not_yet_sealed_real_receipt_no_ledger(tmp_path: Path, monkeypatch) -> None:
    """Real receipt + lua hash matches but no STATE_CHAIN_LEDGER row → NOT_YET_SEALED."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _seed_full_schemas(tmp_path)
    lua = _seed_lua(tmp_path)
    _write_receipt(tmp_path, {
        "process_id": "real_pid_abc",
        "signer_address": "addr_xyz",
        "lua_source_sha256": sha256_file(lua),
        "aos_version": "v2.0.1",
    })
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == NOT_YET_SEALED
    assert "awaiting first row in ledgers/STATE_CHAIN_LEDGER.jsonl" in result.output


def _seed_ledger_row(tmp_path: Path, height: int, root: str) -> None:
    ledger = tmp_path / "ledgers" / "STATE_CHAIN_LEDGER.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema_version": 1,
        "seq": 0,
        "height": height,
        "state_root_sha256": root,
        "this_hash": "x" * 64,
        "prev_row_sha256": "0" * 64,
        "prev_state_root_sha256": "0" * 64,
        "correlation_id": "test",
        "ao_process_id": "real_pid_abc",
        "ao_message_id": "msg_1",
        "committed_by": "addr_xyz",
        "committed_at_unix": 0,
    }
    ledger.write_text(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def test_ao_handlers_not_yet_sealed_gateway_unreachable(tmp_path: Path, monkeypatch) -> None:
    """Real receipt + ledger row but gateway unreachable → NOT_YET_SEALED, never fake-green."""
    from xion_verify.exit_codes import NOT_YET_SEALED as NYS
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "xion_verify.commands.ao_handlers._fetch_gateway_tip",
        lambda gw, pid: (NYS, None, "AO gateway unreachable at https://test.invalid: name resolution failure"),
    )
    _seed_full_schemas(tmp_path)
    lua = _seed_lua(tmp_path)
    _write_receipt(tmp_path, {
        "process_id": "real_pid_abc",
        "signer_address": "addr_xyz",
        "lua_source_sha256": sha256_file(lua),
        "aos_version": "v2.0.1",
    })
    _seed_ledger_row(tmp_path, height=1, root="a" * 64)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == NOT_YET_SEALED
    assert "AO gateway unreachable" in result.output
    assert "cannot prove tip parity offline" in result.output


def test_ao_handlers_fail_tip_parity_mismatch(tmp_path: Path, monkeypatch) -> None:
    """Real receipt + ledger row + gateway responds with a different tip → FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "xion_verify.commands.ao_handlers._fetch_gateway_tip",
        lambda gw, pid: (OK, (2, "b" * 64), None),
    )
    _seed_full_schemas(tmp_path)
    lua = _seed_lua(tmp_path)
    _write_receipt(tmp_path, {
        "process_id": "real_pid_abc",
        "signer_address": "addr_xyz",
        "lua_source_sha256": sha256_file(lua),
        "aos_version": "v2.0.1",
    })
    _seed_ledger_row(tmp_path, height=1, root="a" * 64)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "local STATE_CHAIN_LEDGER tip does not match AO gateway view" in result.output


def test_ao_handlers_ok_full_round_trip(tmp_path: Path, monkeypatch) -> None:
    """Real receipt + ledger row + gateway tip matches → OK.

    This is the only path that returns OK. Compare to the previous version
    where `"dummy" in pid` returned OK without any of this.
    """
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "xion_verify.commands.ao_handlers._fetch_gateway_tip",
        lambda gw, pid: (OK, (1, "a" * 64), None),
    )
    _seed_full_schemas(tmp_path)
    lua = _seed_lua(tmp_path)
    _write_receipt(tmp_path, {
        "process_id": "real_pid_abc",
        "signer_address": "addr_xyz",
        "lua_source_sha256": sha256_file(lua),
        "aos_version": "v2.0.1",
    })
    _seed_ledger_row(tmp_path, height=1, root="a" * 64)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == OK
    assert "local tip parity verified" in result.output
    assert "height=1" in result.output


def test_ao_handlers_fail_missing_handler(tmp_path: Path, monkeypatch) -> None:
    """Missing expected handler returns FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    arch_hash, core_hash = _seed_doctrine(tmp_path)
    content = (
        "handler: commit-state\n"
        "family: lifecycle\n"
        "schema_version: 1\n"
        "status: doctrine_only\n"
        "args: []\n"
        "state_changes: []\n"
        "failure_modes: []\n"
        "source_doctrine: docs/04-ARCHITECTURE.md\n"
        f"source_sha256: {arch_hash}\n"
        "operational_doctrine: docs/28-AO-CORE.md\n"
        f"operational_sha256: {core_hash}\n"
    )
    (tmp_path / "docs/schemas/ao-handler-commit-state.yaml").write_text(content)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "missing expected handler schemas" in result.output


def test_ao_handlers_fail_invalid_yaml(tmp_path: Path, monkeypatch) -> None:
    """Invalid YAML returns FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _seed_doctrine(tmp_path)
    (tmp_path / "docs/schemas/ao-handler-commit-state.yaml").write_text("invalid: yaml: :")
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "invalid YAML" in result.output


def test_ao_handlers_fail_missing_field(tmp_path: Path, monkeypatch) -> None:
    """Missing required field returns FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    arch_hash, core_hash = _seed_doctrine(tmp_path)
    content = (
        "handler: commit-state\n"
        "family: lifecycle\n"
        "schema_version: 1\n"
        "status: doctrine_only\n"
        "args: []\n"
        "state_changes: []\n"
        "# failure_modes intentionally missing\n"
        "source_doctrine: docs/04-ARCHITECTURE.md\n"
        f"source_sha256: {arch_hash}\n"
        "operational_doctrine: docs/28-AO-CORE.md\n"
        f"operational_sha256: {core_hash}\n"
    )
    (tmp_path / "docs/schemas/ao-handler-commit-state.yaml").write_text(content)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "missing required meta fields: failure_modes" in result.output


def test_ao_handlers_fail_hash_mismatch(tmp_path: Path, monkeypatch) -> None:
    """Hash mismatch returns FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    _, core_hash = _seed_doctrine(tmp_path)
    content = (
        "handler: commit-state\n"
        "family: lifecycle\n"
        "schema_version: 1\n"
        "status: doctrine_only\n"
        "args: []\n"
        "state_changes: []\n"
        "failure_modes: []\n"
        "source_doctrine: docs/04-ARCHITECTURE.md\n"
        "source_sha256: badhash\n"
        "operational_doctrine: docs/28-AO-CORE.md\n"
        f"operational_sha256: {core_hash}\n"
    )
    (tmp_path / "docs/schemas/ao-handler-commit-state.yaml").write_text(content)
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "source_sha256 mismatch" in result.output
