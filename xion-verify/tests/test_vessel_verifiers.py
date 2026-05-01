from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from click.testing import CliRunner
from orchestrator.vessel_registry.ledger import append_attestation

from xion_verify.cli import root
from xion_verify.commands import REGISTERED_COMMANDS
from xion_verify.commands.vessel_compact import check_vessel_compact
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _schema() -> dict:
    schema_path = _repo_root() / "docs" / "schemas" / "vessel-compact.yaml"
    return yaml.safe_load(schema_path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_vessel_residual_stub_commands_are_honest_not_yet_sealed() -> None:
    runner = CliRunner()

    result = runner.invoke(root, ["media-provenance"])

    assert result.exit_code == NOT_YET_SEALED, result.output
    assert "NOT_YET_SEALED" in result.output
    assert "Phase 6.7" in result.output


def test_vessel_registry_is_live_but_empty_until_first_row(tmp_path: Path, monkeypatch) -> None:
    _seed_repo_marker(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["vessel-registry"])

    assert result.exit_code == NOT_YET_SEALED, result.output
    assert "registry verifier is live" in result.output


def test_vessel_registry_accepts_valid_attestation_chain(tmp_path: Path, monkeypatch) -> None:
    _seed_repo_marker(tmp_path)
    compact = tmp_path / "vessels" / "reference" / "web-podcast-vessel.yaml"
    compact.parent.mkdir(parents=True)
    compact.write_text("vessel_id: web-podcast-reference\n", encoding="utf-8")
    ledger = tmp_path / "ledgers" / "VESSEL_REGISTRY.jsonl"
    append_attestation(ledger, "web-podcast-reference", compact)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["vessel-registry"])

    assert result.exit_code == OK, result.output
    assert "hash chain verified" in result.output


def test_vessel_registry_rejects_broken_chain(tmp_path: Path, monkeypatch) -> None:
    _seed_repo_marker(tmp_path)
    compact = tmp_path / "vessels" / "reference" / "web-podcast-vessel.yaml"
    compact.parent.mkdir(parents=True)
    compact.write_text("vessel_id: web-podcast-reference\n", encoding="utf-8")
    ledger = tmp_path / "ledgers" / "VESSEL_REGISTRY.jsonl"
    row = append_attestation(ledger, "web-podcast-reference", compact)
    ledger.write_text(
        ledger.read_text(encoding="utf-8").replace(row.compact_sha256, "0" * 64),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(root, ["vessel-registry"])

    assert result.exit_code == FAIL
    assert "row_hash mismatch" in result.output


def test_vessel_compact_reference_manifest_is_live() -> None:
    result = CliRunner().invoke(root, ["vessel-compact"])

    assert result.exit_code == OK, result.output
    assert "web-podcast-vessel.yaml" in result.output


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
    assert schema["status"] == "canonical"

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


def test_vessel_compact_rejects_missing_forget_endpoint(tmp_path: Path) -> None:
    _write_minimal_manifest(tmp_path, remove="forget_endpoint")

    errors = check_vessel_compact(tmp_path, "vessels/reference/bad.yaml")

    assert any("forget_endpoint" in err for err in errors)


def test_vessel_compact_rejects_weakened_consent_scope(tmp_path: Path) -> None:
    _write_minimal_manifest(tmp_path, consent_scopes=[])

    errors = check_vessel_compact(tmp_path, "vessels/reference/bad.yaml")

    assert any("consent_scopes" in err for err in errors)


def test_vessel_compact_rejects_hidden_refusal(tmp_path: Path) -> None:
    _write_minimal_manifest(tmp_path, refusal={"http_451_semantics": "hidden"})

    errors = check_vessel_compact(tmp_path, "vessels/reference/bad.yaml")

    assert any("451" in err or "hidden" in err for err in errors)


def test_vessel_compact_rejects_missing_presence_emitter(tmp_path: Path) -> None:
    _write_minimal_manifest(tmp_path, remove="presence_emitter")

    errors = check_vessel_compact(tmp_path, "vessels/reference/bad.yaml")

    assert any("presence_emitter" in err for err in errors)


def test_vessel_compact_rejects_unknown_data_class(tmp_path: Path) -> None:
    _write_minimal_manifest(tmp_path)
    path = tmp_path / "vessels" / "reference" / "bad.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["data_taxonomy"][0]["class_id"] = "made_up"
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    errors = check_vessel_compact(tmp_path, "vessels/reference/bad.yaml")

    assert any("invalid data_taxonomy" in err for err in errors)


def test_vessel_compact_rejects_missing_availability_state(tmp_path: Path) -> None:
    _write_minimal_manifest(tmp_path)
    path = tmp_path / "vessels" / "reference" / "bad.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["availability_model"]["reachability_matrix"].pop("lost_storage")
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    errors = check_vessel_compact(tmp_path, "vessels/reference/bad.yaml")

    assert any("lost_storage" in err for err in errors)


def _write_minimal_manifest(
    root: Path,
    *,
    remove: str | None = None,
    consent_scopes: list | None = None,
    refusal: dict | None = None,
) -> None:
    schemas = root / "docs" / "schemas"
    manifest_dir = root / "vessels" / "reference"
    schemas.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    schema = _schema()
    (schemas / "vessel-compact.yaml").write_text(yaml.safe_dump(schema), encoding="utf-8")
    manifest = yaml.safe_load((_repo_root() / "vessels" / "reference" / "web-podcast-vessel.yaml").read_text(encoding="utf-8"))
    if consent_scopes is not None:
        manifest["consent_scopes"] = consent_scopes
    if refusal is not None:
        manifest["refusal_visibility"].update(refusal)
    if remove is not None:
        manifest.pop(remove, None)
    (manifest_dir / "bad.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")


def _seed_repo_marker(root: Path) -> None:
    (root / "docs").mkdir()
    (root / "genesis").mkdir()
    (root / "docs" / "00-INDEX.md").write_text("# index", encoding="utf-8")
    (root / "genesis" / "GENESIS_ARTIFACT.md").write_text("# artifact", encoding="utf-8")
