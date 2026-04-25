"""`xion-verify which-level` - explain upgrade-level classification for paths."""

from __future__ import annotations

import json
import sys

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.leveling import (
    classify_paths,
    level_by_id,
    load_level_schemas,
    resolve_authorized_actors,
    resolved_level_id,
)
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="which-level", help="Classify file paths against the 13 upgrade levels.")
@click.argument("paths", nargs=-1)
@click.option("--json", "as_json", is_flag=True, help="Emit a stable JSON object instead of text.")
def which_level(paths: tuple[str, ...], as_json: bool) -> None:
    """Show which upgrade level a proposed path set belongs to.

    With no paths, this command exits OK and prints a short usage hint so it can
    participate in `xion-verify all` without manufacturing a fake result.
    """
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"which-level: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    schemas = load_level_schemas(repo_root)
    if schemas is None:
        click.echo(
            "which-level: NOT_YET_SEALED - docs/schemas/levels.yaml or roles.yaml missing/invalid "
            "(see DEVELOPMENT_ROADMAP.md Phase 6.2)",
            err=True,
        )
        sys.exit(NOT_YET_SEALED)

    if not paths:
        payload = {
            "status": "ok",
            "message": "pass one or more paths to classify a proposed change",
            "example": "xion-verify which-level docs/14-UPGRADE-PATHS.md",
        }
        if as_json:
            click.echo(json.dumps(payload, sort_keys=True))
        else:
            click.echo("which-level: OK (pass one or more paths to classify a proposed change)")
        sys.exit(OK)

    classifications = classify_paths(paths, schemas.levels)
    mapped_levels = sorted({c.level_id for c in classifications if c.level_id is not None})
    unmapped = [c.path for c in classifications if c.level_id is None]
    resolved = resolved_level_id(classifications)

    status = "ok" if resolved is not None else "fail"
    level = level_by_id(schemas.levels, resolved) if resolved is not None else None
    proposer = level.get("proposer") if level else None
    authorized_actors = sorted(resolve_authorized_actors(resolved, schemas.levels, schemas.roles)) if resolved else []
    payload = {
        "status": status,
        "resolved_level": resolved,
        "resolved_name": level.get("name") if level else None,
        "proposer": proposer,
        "authorized_actors": authorized_actors,
        "tier": level.get("tier") if level else None,
        "gate": level.get("gate") if level else None,
        "ledger": level.get("ledger") if level else None,
        "mapped_levels": mapped_levels,
        "unmapped_paths": unmapped,
        "paths": [
            {"path": c.path, "level": c.level_id, "name": c.level_name}
            for c in classifications
        ],
    }

    if as_json:
        click.echo(json.dumps(payload, sort_keys=True))
    elif resolved is None:
        click.echo(
            "which-level: FAIL: path set does not resolve to one upgrade level "
            f"(mapped_levels={mapped_levels}, unmapped_paths={unmapped})",
            err=True,
        )
        for item in payload["paths"]:
            click.echo(f"  {item['path']}: {item['level'] if item['level'] is not None else 'unmapped'}")
    else:
        click.echo(f"which-level: OK (Level {resolved} - {level.get('name')})")
        click.echo(f"  proposer: {proposer}")
        click.echo(f"  authorized_actors: {', '.join(authorized_actors) if authorized_actors else 'none'}")
        click.echo(f"  tier: {level.get('tier')}")
        click.echo(f"  ledger: {level.get('ledger')}")
        for item in payload["paths"]:
            if item["level"] is None and resolved == 12:
                click.echo(f"  {item['path']}: unmapped -> Level 12 - {level.get('name')}")
            else:
                click.echo(f"  {item['path']}: Level {item['level']} - {item['name']}")

    sys.exit(OK if resolved is not None else FAIL)
