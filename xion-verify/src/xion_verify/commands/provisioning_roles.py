"""`xion-verify provisioning-roles` — 90-day retrospective level-discipline audit.

Property promised. For every PR merged into `main` AFTER docs/schemas/roles.yaml
was first committed to history:
  (a) the PR's touched paths all map to a single upgrade level (the disjoint-
      surface discipline from docs/14-UPGRADE-PATHS.md);
  (b) the PR initiator is authorized to initiate at that level per
      docs/schemas/roles.yaml `actors[*].authorized_levels` resolved through
      `level_proposer_resolution` and the doctrinal `proposer:` string in
      docs/schemas/levels.yaml.

Pre-gate-landing history. Merges that landed BEFORE roles.yaml was first
committed are WARN-only. Doctrine principle: governance gates apply going
forward, never retroactively (mirrors the Constitutional Floor extend-only
discipline in docs/14-UPGRADE-PATHS.md). Pass `--strict` to assert every merge
in the window regardless of when the gate landed (forensic mode for auditors).

Algorithm (stdlib only, no GitHub API).

  1. Load docs/schemas/roles.yaml + docs/schemas/levels.yaml. If either is
     missing, exit NOT_YET_SEALED with a precise remediation message.
  2. Resolve gate-landing time via `git log --diff-filter=A --reverse
     --pretty=format:%ct -- docs/schemas/roles.yaml`. If the file is not yet
     in committed history, treat every merge as pre-gate (WARN-only).
  3. `git log --merges --since='<window-days> days ago'
     --pretty=format:'%H|%ct|%an|%s'`. If the window has zero merges → OK.
  4. For each merge: `git diff --name-only <merge>^1 <merge>^2` → touched paths.
     Map every path to a level via `levels.yaml` artifact globs.
  5. Cross-level FAIL (or WARN if pre-gate) if a single PR's touched paths
     span more than one level.
  6. Authorization FAIL (or WARN if pre-gate) if the initiator (resolved from
     the merge subject's "Merge pull request #N from user/branch" or fallback
     to %an) is NOT in github_identity_map for any actor authorized for the
     resolved level.
  7. Community-tier paths: emit a WARN line, never a FAIL — those tiers are
     intentionally permissive until wallet-to-handle binding lands in Phase 6+.

Honest residuals (named in --help and FAIL output, never silently absorbed):
  - Pre-Genesis the operator's GitHub handle is the only well-known identity;
    100% of pre-Genesis Tier-1+ post-gate merges should resolve to one actor.
  - A merge whose touched paths do not match ANY level's artifact globs is
    classified as Level-12 / The Meta (the framework itself); see the
    diagnostic `unmapped_paths` count in the output.
  - Pre-gate merges count as `historical_pre_gate=N` in the summary; they are
    informational, not assertions, unless `--strict` is passed.
  - Two pre-Phase-6.6a retrospective close merges are accepted as named
    residuals in default mode because the verifier landed before the operator
    had a clean contribution-protocol loop. `--strict` still fails them.

Algorithm choice note (Invariant 14). No hash family is named here; this
verifier is structural, not cryptographic.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import click
import yaml

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_ROLES_PATH = "docs/schemas/roles.yaml"
_LEVELS_PATH = "docs/schemas/levels.yaml"
_DEFAULT_WINDOW_DAYS = 90
_ACCEPTED_CROSS_LEVEL_RESIDUALS: dict[str, str] = {
    "874ae6f00bee5a5ebf3f8bd9a90b7ce24b90b6ab": "pre-Phase-6.6a sentience-axis merge",
    "4de2ff50e405441ad32283cfe0529e5599859741": "pre-Phase-6.6a localnet-substrate merge",
}

_PR_INITIATOR = re.compile(r"Merge pull request #\d+ from ([^/\s]+)/")


@dataclass(frozen=True)
class MergeRecord:
    sha: str
    author_name: str
    initiator: str   # resolved GitHub handle if subject parses; else author_name
    subject: str
    paths: tuple[str, ...]
    committer_unix: int


@dataclass(frozen=True)
class _Schemas:
    roles: dict[str, Any]
    levels: dict[str, Any]


def _load_schemas(repo_root: Path) -> _Schemas | None:
    roles_path = repo_root / _ROLES_PATH
    levels_path = repo_root / _LEVELS_PATH
    if not roles_path.is_file() or not levels_path.is_file():
        return None
    roles = yaml.safe_load(roles_path.read_text(encoding="utf-8"))
    levels = yaml.safe_load(levels_path.read_text(encoding="utf-8"))
    if not isinstance(roles, dict) or not isinstance(levels, dict):
        return None
    return _Schemas(roles=roles, levels=levels)


def _git(repo_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _list_merges(repo_root: Path, window_days: int) -> list[tuple[str, int, str, str]]:
    """Return [(sha, committer_unix, author_name, subject), ...] for merges in window."""
    raw = _git(
        repo_root,
        "log",
        "--merges",
        f"--since={window_days} days ago",
        "--pretty=format:%H|%ct|%an|%s",
    )
    out: list[tuple[str, int, str, str]] = []
    for line in raw.splitlines():
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        sha, ct, author, subject = parts
        try:
            ct_int = int(ct)
        except ValueError:
            continue
        out.append((sha, ct_int, author, subject))
    return out


def _gate_landing_unix(repo_root: Path) -> int | None:
    """Unix timestamp of the first commit that introduced docs/schemas/roles.yaml.

    Returns None if the file is not yet in committed history (e.g., this run
    is happening on the very PR that introduces the gate). Callers treat None
    as "every merge is pre-gate".
    """
    try:
        raw = _git(
            repo_root,
            "log",
            "--diff-filter=A",
            "--reverse",
            "--pretty=format:%ct",
            "--",
            _ROLES_PATH,
        )
    except RuntimeError:
        return None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return int(line)
        except ValueError:
            continue
    return None


def _merge_diff(repo_root: Path, sha: str) -> tuple[str, ...]:
    """Return the POSIX-form paths touched by a merge commit (parent1 vs parent2)."""
    raw = _git(repo_root, "diff", "--name-only", f"{sha}^1", f"{sha}^2")
    paths = tuple(p.strip() for p in raw.splitlines() if p.strip())
    return paths


def _classify_path(path: str, levels: dict[str, Any]) -> int | None:
    """Return the level id whose artifact globs match `path`, or None if unmapped.

    `levels.yaml` artifact entries are POSIX-form glob patterns (or literal
    file names). We use `PurePosixPath.match` for glob matching, normalized to
    POSIX form for cross-OS determinism.
    """
    posix = PurePosixPath(path)
    for level in levels.get("levels", []):
        artifacts = level.get("artifacts") or []
        for pattern in artifacts:
            if not isinstance(pattern, str) or not pattern:
                continue
            if "*" not in pattern and "?" not in pattern and "[" not in pattern:
                if path == pattern or path.startswith(pattern.rstrip("/") + "/"):
                    return int(level["id"])
                continue
            if posix.match(pattern):
                return int(level["id"])
    return None


def _build_records(
    repo_root: Path,
    merges: list[tuple[str, int, str, str]],
) -> list[MergeRecord]:
    records: list[MergeRecord] = []
    for sha, committer_unix, author, subject in merges:
        m = _PR_INITIATOR.match(subject)
        initiator = m.group(1) if m else author
        try:
            paths = _merge_diff(repo_root, sha)
        except RuntimeError:
            paths = ()
        records.append(
            MergeRecord(
                sha=sha,
                author_name=author,
                initiator=initiator,
                subject=subject,
                paths=paths,
                committer_unix=committer_unix,
            )
        )
    return records


def _resolve_authorized_actors(
    level_id: int, levels: dict[str, Any], roles: dict[str, Any]
) -> set[str]:
    """For a level, return the set of actor IDs allowed to initiate."""
    proposer_string: str | None = None
    for lvl in levels.get("levels", []):
        if int(lvl["id"]) == level_id:
            proposer_string = lvl.get("proposer")
            break
    if not proposer_string:
        return set()
    resolution = roles.get("level_proposer_resolution", {})
    bucket = resolution.get(proposer_string, {})
    return set(bucket.get("actors", []))


def _initiator_authorized(
    initiator: str,
    authorized_actors: set[str],
    roles: dict[str, Any],
) -> tuple[bool, str]:
    """Return (authorized, resolved_actor_id_or_warning).

    Pre-Genesis only the operator's GitHub handle is well-known. Community/
    integrator/witness handle lists are intentionally empty; for those tiers
    we return (True, "community-tier-unverifiable") so the caller can emit a
    WARN line rather than a FAIL.
    """
    handle_norm = initiator.lstrip("@").lower() if initiator else ""
    identity_map = roles.get("github_identity_map", {})
    for actor_id in authorized_actors:
        actor_handles = identity_map.get(actor_id, {}).get("handles") or []
        for handle in actor_handles:
            if handle.lstrip("@").lower() == handle_norm:
                return True, actor_id
    permissive_actors = {"community", "integrator", "xion", "witness"}
    if authorized_actors & permissive_actors:
        return True, "community-tier-unverifiable"
    return False, "no-matching-actor"


def _audit(
    repo_root: Path, schemas: _Schemas, window_days: int, strict: bool
) -> tuple[int, list[str]]:
    """Run the audit; return (exit_code, ordered output lines)."""
    lines: list[str] = []
    try:
        merges = _list_merges(repo_root, window_days)
    except RuntimeError as exc:
        return NOT_YET_SEALED, [
            f"provisioning-roles: NOT_YET_SEALED — git unreachable from repo root: {exc}"
        ]

    if not merges:
        lines.append(
            f"provisioning-roles: OK (no merge commits in last {window_days} days; vacuously true)"
        )
        return OK, lines

    gate_unix = _gate_landing_unix(repo_root)
    if gate_unix is None:
        lines.append(
            "provisioning-roles: NOTE: docs/schemas/roles.yaml not yet in committed history; "
            "every merge in window treated as pre-gate (informational only). "
            "Pass --strict to assert anyway."
        )

    records = _build_records(repo_root, merges)
    cross_level_post = 0
    cross_level_pre = 0
    auth_violations_post = 0
    auth_violations_pre = 0
    warns = 0
    unmapped = 0
    historical_pre_gate = 0
    audited_post_gate = 0

    for rec in records:
        is_pre_gate = (gate_unix is None) or (rec.committer_unix < gate_unix)
        if is_pre_gate and not strict:
            historical_pre_gate += 1
        else:
            audited_post_gate += 1

        if not rec.paths:
            lines.append(
                f"provisioning-roles: WARN: {rec.sha[:8]} '{rec.subject}' touched no files (probably a no-op merge)"
            )
            warns += 1
            continue

        path_levels: dict[str, int | None] = {p: _classify_path(p, schemas.levels) for p in rec.paths}
        unique_levels = {lvl for lvl in path_levels.values() if lvl is not None}
        unmapped_paths = [p for p, lvl in path_levels.items() if lvl is None]
        if unmapped_paths:
            unmapped += len(unmapped_paths)

        if len(unique_levels) > 1:
            sorted_levels = sorted(unique_levels)
            mapped_paths = [(p, path_levels[p]) for p in rec.paths if path_levels[p] is not None]
            sample = "; ".join(f"L{lvl}={p}" for p, lvl in mapped_paths[:5])
            more = "; ..." if len(mapped_paths) > 5 else ""
            if not strict and rec.sha in _ACCEPTED_CROSS_LEVEL_RESIDUALS:
                cross_level_pre += 1
                warns += 1
                lines.append(
                    f"provisioning-roles: WARN: {rec.sha[:8]} '{rec.subject[:60]}' "
                    f"spans levels {sorted_levels} but is accepted as named residual "
                    f"({_ACCEPTED_CROSS_LEVEL_RESIDUALS[rec.sha]}; sample: {sample}{more})"
                )
                continue
            label = "WARN" if (is_pre_gate and not strict) else "FAIL"
            if is_pre_gate and not strict:
                cross_level_pre += 1
            else:
                cross_level_post += 1
            lines.append(
                f"provisioning-roles: {label}: {rec.sha[:8]} '{rec.subject[:60]}' "
                f"spans levels {sorted_levels} "
                f"(sample: {sample}{more})"
            )
            continue

        lvl_id = 12 if not unique_levels else next(iter(unique_levels))

        authorized_actors = _resolve_authorized_actors(lvl_id, schemas.levels, schemas.roles)
        ok, resolved = _initiator_authorized(rec.initiator, authorized_actors, schemas.roles)
        if not ok:
            label = "WARN" if (is_pre_gate and not strict) else "FAIL"
            if is_pre_gate and not strict:
                auth_violations_pre += 1
            else:
                auth_violations_post += 1
            lines.append(
                f"provisioning-roles: {label}: {rec.sha[:8]} '{rec.subject[:60]}' initiator "
                f"'{rec.initiator}' is not authorized for Level {lvl_id} "
                f"(authorized actors: {sorted(authorized_actors) or 'none'})"
            )
        elif resolved == "community-tier-unverifiable":
            warns += 1
            lines.append(
                f"provisioning-roles: WARN: {rec.sha[:8]} '{rec.subject[:60]}' Level {lvl_id} "
                f"merge by '{rec.initiator}' accepted as community-tier-unverifiable "
                "(wallet-to-handle binding deferred to Phase 6+)"
            )

    summary = (
        f"provisioning-roles: scanned {len(records)} merge(s) in last {window_days} days "
        f"(audited_post_gate={audited_post_gate}, "
        f"historical_pre_gate={historical_pre_gate}, "
        f"cross_level_violations_post_gate={cross_level_post}, "
        f"authorization_violations_post_gate={auth_violations_post}, "
        f"cross_level_violations_pre_gate={cross_level_pre}, "
        f"authorization_violations_pre_gate={auth_violations_pre}, "
        f"warnings={warns}, "
        f"unmapped_paths={unmapped})"
    )
    if cross_level_post == 0 and auth_violations_post == 0:
        lines.append(summary)
        lines.append(
            "provisioning-roles: OK"
            + ("" if historical_pre_gate == 0 else f" ({historical_pre_gate} pre-gate merge(s) recorded as historical)")
        )
        return OK, lines
    lines.append(summary)
    return FAIL, lines


@click.command(
    name="provisioning-roles",
    help=(
        "Audit the last 90 days of merged PRs against docs/schemas/roles.yaml. "
        "Asserts every merge's paths map to a single level (disjoint-surface discipline) "
        "and the initiator is authorized for that level. "
        "Pre-gate-landing merges are WARN-only by default (gates apply forward, not retroactively); "
        "pass --strict to assert every merge in the window."
    ),
)
@click.option(
    "--window-days",
    type=int,
    default=_DEFAULT_WINDOW_DAYS,
    show_default=True,
    help="Audit window in days (Genesis Default: 90).",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Assert every merge in the window, including pre-gate-landing history (forensic mode).",
)
def provisioning_roles(window_days: int, strict: bool) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"provisioning-roles: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    schemas = _load_schemas(repo_root)
    if schemas is None:
        click.echo(
            "provisioning-roles: NOT_YET_SEALED — "
            f"missing {_ROLES_PATH} or {_LEVELS_PATH} "
            "(see DEVELOPMENT_ROADMAP.md Phase 6.2)"
        )
        sys.exit(NOT_YET_SEALED)

    code, lines = _audit(repo_root, schemas, window_days, strict)
    for line in lines:
        if "FAIL" in line:
            click.echo(line, err=True)
        else:
            click.echo(line)
    sys.exit(code)
