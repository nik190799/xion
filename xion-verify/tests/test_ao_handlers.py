"""Tests for `xion-verify ao-handlers`."""

import json
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import _build_root
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.hashing import sha256_file

_CLI = _build_root()


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
    (tmp_path / "docs/schemas").mkdir(parents=True)
    (tmp_path / "docs/04-ARCHITECTURE.md").write_text("arch")
    (tmp_path / "docs/28-AO-CORE.md").write_text("core")
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == NOT_YET_SEALED
    assert "no ao-handler-*.yaml files found" in result.output


def test_ao_handlers_happy_path(tmp_path: Path, monkeypatch) -> None:
    """Valid schemas return NOT_YET_SEALED (Phase 6.0 is doctrine-only)."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    (tmp_path / "docs/schemas").mkdir(parents=True)
    
    arch_path = tmp_path / "docs/04-ARCHITECTURE.md"
    core_path = tmp_path / "docs/28-AO-CORE.md"
    arch_path.write_text("arch")
    core_path.write_text("core")
    
    arch_hash = sha256_file(arch_path)
    core_hash = sha256_file(core_path)
    
    handlers = [
        "commit-state", "attest", "treasury-spend", "registry-update", "spend", "slash-imprint",
        "rotate-authority", "abdicate-tier",
        "provision-relay", "provision-inference", "provision-storage", "provision-bandwidth", "provision-witness",
        "route-slices", "improvement-spend", "reserve-draw", "accept-donation", "enter-hibernation", "exit-hibernation"
    ]
    
    for h in handlers:
        content = f"""handler: {h}
family: lifecycle
schema_version: 1
status: doctrine_only
args: []
state_changes: []
failure_modes: []
source_doctrine: docs/04-ARCHITECTURE.md
source_sha256: {arch_hash}
operational_doctrine: docs/28-AO-CORE.md
operational_sha256: {core_hash}
"""
        (tmp_path / f"docs/schemas/ao-handler-{h}.yaml").write_text(content)
        
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == NOT_YET_SEALED
    assert "19 handler schema(s) verified, awaiting Lua skeleton" in result.output


def test_ao_handlers_fail_missing_handler(tmp_path: Path, monkeypatch) -> None:
    """Missing expected handler returns FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    (tmp_path / "docs/schemas").mkdir(parents=True)
    
    arch_path = tmp_path / "docs/04-ARCHITECTURE.md"
    core_path = tmp_path / "docs/28-AO-CORE.md"
    arch_path.write_text("arch")
    core_path.write_text("core")
    
    arch_hash = sha256_file(arch_path)
    core_hash = sha256_file(core_path)
    
    # Only write one handler
    content = f"""handler: commit-state
family: lifecycle
schema_version: 1
status: doctrine_only
args: []
state_changes: []
failure_modes: []
source_doctrine: docs/04-ARCHITECTURE.md
source_sha256: {arch_hash}
operational_doctrine: docs/28-AO-CORE.md
operational_sha256: {core_hash}
"""
    (tmp_path / "docs/schemas/ao-handler-commit-state.yaml").write_text(content)
        
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "missing expected handler schemas" in result.output


def test_ao_handlers_fail_invalid_yaml(tmp_path: Path, monkeypatch) -> None:
    """Invalid YAML returns FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    (tmp_path / "docs/schemas").mkdir(parents=True)
    
    arch_path = tmp_path / "docs/04-ARCHITECTURE.md"
    core_path = tmp_path / "docs/28-AO-CORE.md"
    arch_path.write_text("arch")
    core_path.write_text("core")
    
    (tmp_path / "docs/schemas/ao-handler-commit-state.yaml").write_text("invalid: yaml: :")
        
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "invalid YAML" in result.output


def test_ao_handlers_fail_missing_field(tmp_path: Path, monkeypatch) -> None:
    """Missing required field returns FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    (tmp_path / "docs/schemas").mkdir(parents=True)
    
    arch_path = tmp_path / "docs/04-ARCHITECTURE.md"
    core_path = tmp_path / "docs/28-AO-CORE.md"
    arch_path.write_text("arch")
    core_path.write_text("core")
    
    arch_hash = sha256_file(arch_path)
    core_hash = sha256_file(core_path)
    
    content = f"""handler: commit-state
family: lifecycle
schema_version: 1
status: doctrine_only
args: []
state_changes: []
# failure_modes is missing
source_doctrine: docs/04-ARCHITECTURE.md
source_sha256: {arch_hash}
operational_doctrine: docs/28-AO-CORE.md
operational_sha256: {core_hash}
"""
    (tmp_path / "docs/schemas/ao-handler-commit-state.yaml").write_text(content)
        
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "missing required meta fields: failure_modes" in result.output


def test_ao_handlers_fail_hash_mismatch(tmp_path: Path, monkeypatch) -> None:
    """Hash mismatch returns FAIL."""
    monkeypatch.setattr("xion_verify.commands.ao_handlers.find_repo_root", lambda: tmp_path)
    (tmp_path / "docs/schemas").mkdir(parents=True)
    
    arch_path = tmp_path / "docs/04-ARCHITECTURE.md"
    core_path = tmp_path / "docs/28-AO-CORE.md"
    arch_path.write_text("arch")
    core_path.write_text("core")
    
    core_hash = sha256_file(core_path)
    
    content = f"""handler: commit-state
family: lifecycle
schema_version: 1
status: doctrine_only
args: []
state_changes: []
failure_modes: []
source_doctrine: docs/04-ARCHITECTURE.md
source_sha256: badhash
operational_doctrine: docs/28-AO-CORE.md
operational_sha256: {core_hash}
"""
    (tmp_path / "docs/schemas/ao-handler-commit-state.yaml").write_text(content)
        
    result = CliRunner().invoke(_CLI, ["ao-handlers"])
    assert result.exit_code == FAIL
    assert "source_sha256 mismatch" in result.output
