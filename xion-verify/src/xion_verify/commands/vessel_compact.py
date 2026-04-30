"""`xion-verify vessel-compact` — reference Vessel Compact manifest checks."""

from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import Any

import click
import yaml

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_DEFAULT_MANIFEST = "vessels/reference/web-podcast-vessel.yaml"
_SCHEMA = "docs/schemas/vessel-compact.yaml"
_REQUIRED_ENDPOINTS = ("export", "forget", "inspect")
_REQUIRED_REFUSAL = ("covenant_flags", "http_451_semantics", "arbiter_explanation", "mode_rendering")
_REQUIRED_SURFACES = (
    "presence_emitter",
    "modality_consent",
    "pricing_decomposition",
    "disavowal_endpoint",
    "forget_endpoint",
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def check_vessel_compact(repo_root: Path, manifest_rel: str = _DEFAULT_MANIFEST) -> list[str]:
    schema_path = repo_root / _SCHEMA
    manifest_path = repo_root / manifest_rel
    if not schema_path.is_file():
        return [f"missing schema: {_SCHEMA}"]
    if not manifest_path.is_file():
        return [f"missing reference manifest: {manifest_rel}"]
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict) or not isinstance(manifest, dict):
        return ["schema and manifest must both be YAML mappings"]

    errors: list[str] = []
    required_fields = schema.get("manifest", {}).get("required_fields", [])
    for field in required_fields:
        if field not in manifest:
            errors.append(f"manifest missing required field: {field}")
    allowed_modes = set(schema.get("manifest", {}).get("vessel_mode", {}).get("allowed", []))
    if manifest.get("vessel_mode") not in allowed_modes:
        errors.append(f"invalid vessel_mode: {manifest.get('vessel_mode')!r}")
    allowed_capabilities = set(schema.get("manifest", {}).get("capabilities", {}).get("allowed", []))
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("capabilities must be a non-empty list")
    else:
        errors.extend(
            f"invalid capability: {capability!r}"
            for capability in capabilities
            if capability not in allowed_capabilities
        )
    errors.extend(_require_mapping_keys(manifest, "free_endpoints", _REQUIRED_ENDPOINTS))
    errors.extend(_require_mapping_keys(manifest, "refusal_visibility", _REQUIRED_REFUSAL))
    errors.extend(
        _require_mapping_keys(
            manifest,
            "local_storage",
            tuple(schema.get("manifest", {}).get("local_storage", {}).get("required_declarations", [])),
        )
    )
    errors.extend(
        _require_mapping_keys(
            manifest,
            "provenance",
            tuple(schema.get("manifest", {}).get("provenance", {}).get("required", [])),
        )
    )
    errors.extend(
        _require_mapping_keys(
            manifest,
            "degraded_behavior",
            tuple(schema.get("manifest", {}).get("degraded_behavior", {}).get("required", [])),
        )
    )
    errors.extend(
        _require_mapping_keys(
            manifest,
            "physical_trust_controls",
            tuple(schema.get("manifest", {}).get("physical_trust_controls", {}).get("mode_dependent", [])),
        )
    )
    errors.extend(
        _require_mapping_keys(
            manifest,
            "revocation",
            tuple(schema.get("manifest", {}).get("revocation", {}).get("required", [])),
        )
    )
    for surface in _REQUIRED_SURFACES:
        if not manifest.get(surface):
            errors.append(f"manifest missing required surface: {surface}")
    if manifest.get("forget_endpoint") != manifest.get("free_endpoints", {}).get("forget"):
        errors.append("forget_endpoint must match free_endpoints.forget")
    consent_scopes = manifest.get("consent_scopes")
    if not isinstance(consent_scopes, list) or not consent_scopes:
        errors.append("consent_scopes must be a non-empty list")
    else:
        scope_ids = {item.get("scope_id") for item in consent_scopes if isinstance(item, dict)}
        if not {"stream_voice", "stream_visual"} & scope_ids:
            errors.append("manifest must declare at least one stream_* consent scope")
    if manifest.get("refusal_visibility", {}).get("http_451_semantics") not in {"preserved", True}:
        errors.append("refusal_visibility.http_451_semantics must be preserved")
    if "hidden" in str(manifest.get("refusal_visibility", {})).lower():
        errors.append("refusal visibility may not be hidden")
    payment_allowed = set(schema.get("manifest", {}).get("payment_posture", {}).get("allowed", []))
    if manifest.get("payment_posture") not in payment_allowed:
        errors.append(f"invalid payment_posture: {manifest.get('payment_posture')!r}")
    covenant_hash = manifest.get("covenant", {}).get("covenant_hash")
    provenance_hash = manifest.get("provenance", {}).get("covenant_hash")
    if not isinstance(covenant_hash, str) or not _HEX64.match(covenant_hash):
        errors.append("covenant.covenant_hash must be a 64-character lowercase hex string")
    if provenance_hash != covenant_hash:
        errors.append("provenance.covenant_hash must match covenant.covenant_hash")
    doctrine_hash = schema.get("source_sha256")
    if manifest.get("source_sha256") != doctrine_hash:
        errors.append("source_sha256 must match docs/37-VESSELS.md pin in schema")
    errors.extend(_check_agentic_surface(schema, manifest))
    errors.extend(_check_data_taxonomy(schema, manifest))
    errors.extend(_check_availability_model(schema, manifest))
    return errors


def _require_mapping_keys(manifest: dict[str, Any], field: str, keys: tuple[str, ...]) -> list[str]:
    value = manifest.get(field)
    if not isinstance(value, dict):
        return [f"{field} must be a mapping"]
    return [f"{field} missing required key: {key}" for key in keys if key not in value]


def _check_agentic_surface(schema: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    surface = manifest.get("agentic_surface")
    if not isinstance(surface, dict):
        return ["agentic_surface must be a mapping"]
    for field in schema.get("agentic_surface", {}).get("required_fields", []):
        if field not in surface:
            errors.append(f"agentic_surface missing required field: {field}")
    principal_allowed = set(schema.get("agentic_surface", {}).get("principal", {}).get("allowed", []))
    if surface.get("principal") not in principal_allowed:
        errors.append(f"invalid agentic_surface.principal: {surface.get('principal')!r}")
    upgrade_allowed = set(
        schema.get("agentic_surface", {}).get("anonymous_to_authenticated_upgrade", {}).get("allowed", [])
    )
    if surface.get("anonymous_to_authenticated_upgrade") not in upgrade_allowed:
        errors.append(
            "invalid agentic_surface.anonymous_to_authenticated_upgrade: "
            f"{surface.get('anonymous_to_authenticated_upgrade')!r}"
        )
    input_auth = surface.get("input_authenticity")
    if not isinstance(input_auth, dict):
        errors.append("agentic_surface.input_authenticity must be a mapping")
    else:
        capture_allowed = {
            item.strip()
            for item in schema.get("agentic_surface", {})
            .get("input_authenticity", {})
            .get("fields", {})
            .get("capture_origin", "")
            .split("|")
        }
        if input_auth.get("capture_origin") not in capture_allowed:
            errors.append(
                f"invalid agentic_surface.input_authenticity.capture_origin: {input_auth.get('capture_origin')!r}"
            )
    verification_allowed = set(
        schema.get("agentic_surface", {}).get("receiving_side_verification", {}).get("allowed_paths", [])
    )
    if surface.get("receiving_side_verification") not in verification_allowed:
        errors.append(
            f"invalid agentic_surface.receiving_side_verification: {surface.get('receiving_side_verification')!r}"
        )
    if surface.get("agent_in_path") is True and surface.get("agent_identity") in {None, "", "none"}:
        errors.append("agentic_surface.agent_identity is required when agent_in_path is true")
    return errors


def _check_data_taxonomy(schema: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    entries = manifest.get("data_taxonomy")
    if not isinstance(entries, list) or not entries:
        return ["data_taxonomy must be a non-empty list"]
    errors: list[str] = []
    allowed_classes = set(schema.get("data_taxonomy", {}).get("classes", []))
    required = tuple(schema.get("data_taxonomy", {}).get("required_per_class_fields", []))
    availability_states = set(schema.get("availability_model", {}).get("reachability_states", []))
    seen: set[str] = set()
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"data_taxonomy[{idx}] must be a mapping")
            continue
        missing = [field for field in required if field not in entry]
        if missing:
            errors.append(f"data_taxonomy[{idx}] missing required fields: {', '.join(missing)}")
        class_id = entry.get("class_id")
        if class_id not in allowed_classes:
            errors.append(f"invalid data_taxonomy[{idx}].class_id: {class_id!r}")
        elif class_id in seen:
            errors.append(f"duplicate data_taxonomy class_id: {class_id}")
        else:
            seen.add(class_id)
        if entry.get("availability_reference") not in availability_states:
            errors.append(
                f"invalid data_taxonomy[{idx}].availability_reference: {entry.get('availability_reference')!r}"
            )
        if entry.get("class_id") == "cross_protocol_bridge" and not entry.get("third_party_recipients"):
            errors.append("cross_protocol_bridge data class must declare third_party_recipients")
    return errors


def _check_availability_model(schema: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    model = manifest.get("availability_model")
    if not isinstance(model, dict):
        return ["availability_model must be a mapping"]
    errors: list[str] = []
    for field in schema.get("availability_model", {}).get("required_declarations", []):
        if field not in model:
            errors.append(f"availability_model missing required declaration: {field}")
    matrix = model.get("reachability_matrix")
    if not isinstance(matrix, dict):
        return errors + ["availability_model.reachability_matrix must be a mapping"]
    required_fields = tuple(schema.get("availability_model", {}).get("required_matrix_fields", []))
    proof_allowed = set(schema.get("availability_model", {}).get("proof_posture_allowed", []))
    for state in schema.get("availability_model", {}).get("reachability_states", []):
        row = matrix.get(state)
        if not isinstance(row, dict):
            errors.append(f"availability_model.reachability_matrix missing state: {state}")
            continue
        missing = [field for field in required_fields if field not in row]
        if missing:
            errors.append(f"availability_model.reachability_matrix.{state} missing fields: {', '.join(missing)}")
        if row.get("proof_posture") not in proof_allowed:
            errors.append(
                f"invalid availability_model.reachability_matrix.{state}.proof_posture: {row.get('proof_posture')!r}"
            )
    return errors


@click.command(name="vessel-compact", help="Verify reference Vessel Compact manifests.")
@click.option("--manifest", default=_DEFAULT_MANIFEST, show_default=True, help="Manifest path relative to repo root.")
def vessel_compact(manifest: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"vessel-compact: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    errors = check_vessel_compact(repo_root, manifest)
    if errors:
        for error in errors:
            click.echo(f"vessel-compact: FAIL: {error}", err=True)
        sys.exit(FAIL)
    click.echo(f"vessel-compact: OK ({manifest} satisfies reference Compact checks)")
    sys.exit(OK)


__all__ = ["check_vessel_compact", "vessel_compact"]
