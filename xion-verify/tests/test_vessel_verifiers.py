from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.commands import REGISTERED_COMMANDS
from xion_verify.exit_codes import NOT_YET_SEALED, OK


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _schema() -> dict:
    schema_path = _repo_root() / "docs" / "schemas" / "vessel-compact.yaml"
    return yaml.safe_load(schema_path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_vessel_stub_commands_are_honest_not_yet_sealed() -> None:
    runner = CliRunner()

    for command in ("vessel-compact", "media-provenance", "vessel-registry"):
        result = runner.invoke(root, [command])

        assert result.exit_code == NOT_YET_SEALED, result.output
        assert "NOT_YET_SEALED" in result.output
        assert "Phase 6.7" in result.output


def test_vessel_commands_are_registered_and_visible_in_help() -> None:
    result = CliRunner().invoke(root, ["--help"])

    assert result.exit_code == OK, result.output
    for command in ("vessel-compact", "media-provenance", "vessel-registry"):
        assert command in REGISTERED_COMMANDS
        assert command in result.output


def test_vessel_schema_pins_all_source_doctrines() -> None:
    schema = _schema()
    repo = _repo_root()

    assert schema["schema_id"] == "vessel-compact"
    assert schema["status"] == "doctrine_only"

    sources = {item["path"]: item["source_sha256"] for item in schema["source_doctrines"]}
    expected_paths = {
        "docs/37-VESSELS.md",
        "docs/37a-AGENTIC-VESSELS.md",
        "docs/37b-VESSEL-DATA-TAXONOMY.md",
        "docs/37c-VESSEL-AVAILABILITY-MODEL.md",
    }
    assert set(sources) == expected_paths

    for rel_path, expected_hash in sources.items():
        assert _sha256(repo / rel_path) == expected_hash


def test_vessel_schema_names_agentic_data_and_availability_blocks() -> None:
    schema = _schema()

    assert "agentic_surface" in schema
    assert "data_taxonomy" in schema
    assert "availability_model" in schema

    assert "agent_in_path" in schema["agentic_surface"]["required_fields"]
    assert "receiving_side_verification" in schema["agentic_surface"]["required_fields"]

    data_classes = set(schema["data_taxonomy"]["classes"])
    assert "conversation_memory" in data_classes
    assert "pending_state" in data_classes
    assert "captured_sensor_overflow" in data_classes
    assert "cross_protocol_bridge" in data_classes

    states = schema["availability_model"]["reachability_states"]
    assert states == [
        "online_full",
        "online_degraded",
        "offline_floor",
        "offline_cache",
        "lost_storage",
    ]
    assert "reachability_matrix" in schema["availability_model"]["required_declarations"]


def test_vessel_schema_passes_xion_verify_schemas() -> None:
    result = CliRunner().invoke(root, ["schemas"])

    assert result.exit_code == OK, result.output
    assert "vessel-compact.yaml" in result.output
