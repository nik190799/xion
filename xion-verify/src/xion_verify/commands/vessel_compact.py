"""`xion-verify vessel-compact` — reference Vessel Compact manifest checks."""

from __future__ import annotations

import sys
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
    errors.extend(_require_mapping_keys(manifest, "free_endpoints", _REQUIRED_ENDPOINTS))
    errors.extend(_require_mapping_keys(manifest, "refusal_visibility", _REQUIRED_REFUSAL))
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
    return errors


def _require_mapping_keys(manifest: dict[str, Any], field: str, keys: tuple[str, ...]) -> list[str]:
    value = manifest.get(field)
    if not isinstance(value, dict):
        return [f"{field} must be a mapping"]
    return [f"{field} missing required key: {key}" for key in keys if key not in value]


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
