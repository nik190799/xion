#!/usr/bin/env python3
"""scripts/level_discipline.py — per-PR level-discipline gate.

Run by .github/workflows/level-discipline.yml on every pull request. Reads the
same docs/schemas/roles.yaml + docs/schemas/levels.yaml that the verifier
xion-verify provisioning-roles consumes for its 90-day retrospective, but
applied to a single PR diff (BASE_REF -> HEAD_REF) instead of a window.

Property promised. The PR satisfies BOTH:

  (1) every touched path classifies to the same upgrade level (the disjoint-
      surface discipline from docs/14-UPGRADE-PATHS.md);
  (2) the PR initiator (env: PR_AUTHOR) is in the github_identity_map for an
      actor whose authorized_levels includes the resolved level.

Exit codes:

  0   PR is conformant (or the PR's authorized_actors set is permissive in
      the community-tier sense and PR_AUTHOR did not match — accepted with a
      WARN line; this is intentional and matches the verifier's posture).
  1   PR violates one of the two properties.

Inputs (env):
  PR_AUTHOR  GitHub login of the PR creator (github.event.pull_request.user.login).
  BASE_REF   Base SHA the PR is targeting (github.event.pull_request.base.sha).
  HEAD_REF   Head SHA of the PR (github.event.pull_request.head.sha).

Stdlib only + PyYAML. No GitHub API calls.

Honest residuals:
  - Pre-Genesis the only well-known GitHub identity in the allowlist is the
    operator's. Community / integrator / xion / witness handle lists are
    intentionally empty; for those tiers an unmatched PR_AUTHOR is accepted
    with a WARN line (`community-tier-unverifiable`). The CI gate's job is
    to catch operator-tier-and-above paths landed by unauthorized identities,
    not to police community-tier paths.
  - A path that does not match any artifact glob is treated as Level 12
    (The Meta) for classification purposes; the PR fails fast if such a path
    is mixed with any other-level path (cross-level violation).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    sys.stderr.write(
        "level-discipline: FAIL: PyYAML is required. "
        "The workflow installs it; if running locally, `pip install pyyaml`.\n"
    )
    sys.exit(1)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_ROLES_PATH = _REPO_ROOT / "docs" / "schemas" / "roles.yaml"
_LEVELS_PATH = _REPO_ROOT / "docs" / "schemas" / "levels.yaml"


def _git_diff_paths(base: str, head: str) -> list[str]:
    """Return the POSIX-form paths changed between base..head."""
    proc = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(
            f"level-discipline: FAIL: git diff {base}..{head} failed: {proc.stderr.strip()}\n"
        )
        sys.exit(1)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _file_exists_at_ref(rel_path: str, ref: str) -> bool:
    """True iff `rel_path` exists in the git tree at `ref`."""
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{rel_path}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _classify_path(path: str, levels: dict[str, Any]) -> int | None:
    posix = PurePosixPath(path)
    for level in levels.get("levels", []):
        for pattern in level.get("artifacts") or []:
            if not isinstance(pattern, str) or not pattern:
                continue
            if "*" not in pattern and "?" not in pattern and "[" not in pattern:
                if path == pattern or path.startswith(pattern.rstrip("/") + "/"):
                    return int(level["id"])
                continue
            if posix.match(pattern):
                return int(level["id"])
    return None


def _resolve_authorized_actors(level_id: int, levels: dict, roles: dict) -> set[str]:
    proposer_string: str | None = None
    for lvl in levels.get("levels", []):
        if int(lvl["id"]) == level_id:
            proposer_string = lvl.get("proposer")
            break
    if not proposer_string:
        return set()
    bucket = roles.get("level_proposer_resolution", {}).get(proposer_string, {})
    return set(bucket.get("actors", []))


def _initiator_authorized(initiator: str, authorized_actors: set[str], roles: dict) -> tuple[bool, str]:
    handle_norm = initiator.lstrip("@").lower() if initiator else ""
    identity_map = roles.get("github_identity_map", {})
    for actor_id in authorized_actors:
        for handle in identity_map.get(actor_id, {}).get("handles") or []:
            if handle.lstrip("@").lower() == handle_norm:
                return True, actor_id
    permissive_actors = {"community", "integrator", "xion", "witness"}
    if authorized_actors & permissive_actors:
        return True, "community-tier-unverifiable"
    return False, "no-matching-actor"


def main() -> int:
    pr_author = os.environ.get("PR_AUTHOR", "").strip()
    base_ref = os.environ.get("BASE_REF", "").strip()
    head_ref = os.environ.get("HEAD_REF", "").strip()
    if not pr_author or not base_ref or not head_ref:
        sys.stderr.write(
            "level-discipline: FAIL: PR_AUTHOR, BASE_REF, and HEAD_REF must all be set in env\n"
        )
        return 1

    if not _ROLES_PATH.is_file() or not _LEVELS_PATH.is_file():
        sys.stderr.write(
            "level-discipline: FAIL: docs/schemas/roles.yaml or docs/schemas/levels.yaml missing\n"
        )
        return 1

    # Bootstrap mode. If docs/schemas/roles.yaml does not exist at BASE_REF,
    # this PR is introducing the gate itself. Doctrine principle: gates apply
    # forward, never retroactively, and a gate cannot be required to govern
    # the very PR that introduces it. Emit a NOTE and pass.
    if not _file_exists_at_ref("docs/schemas/roles.yaml", base_ref):
        print(
            "level-discipline: NOTE: docs/schemas/roles.yaml does not exist at BASE_REF; "
            "this PR is introducing the gate. Bootstrap mode: pass without assertion. "
            "Subsequent PRs will be fully gated."
        )
        print("level-discipline: OK (bootstrap)")
        return 0

    roles = yaml.safe_load(_ROLES_PATH.read_text(encoding="utf-8")) or {}
    levels = yaml.safe_load(_LEVELS_PATH.read_text(encoding="utf-8")) or {}

    paths = _git_diff_paths(base_ref, head_ref)
    if not paths:
        print("level-discipline: OK (PR touches zero files; vacuously true)")
        return 0

    classified = [(p, _classify_path(p, levels)) for p in paths]
    mapped = [(p, lvl) for p, lvl in classified if lvl is not None]
    unmapped = [p for p, lvl in classified if lvl is None]
    unique_levels = {lvl for _, lvl in mapped}

    if len(unique_levels) > 1:
        sample = "; ".join(f"L{lvl}={p}" for p, lvl in mapped[:10])
        more = "; ..." if len(mapped) > 10 else ""
        sys.stderr.write(
            f"level-discipline: FAIL: PR straddles levels {sorted(unique_levels)}\n"
            f"  paths (first 10): {sample}{more}\n"
            f"  remediation: split this PR into one PR per level, per docs/14-UPGRADE-PATHS.md disjoint-surface discipline\n"
        )
        return 1

    if not unique_levels:
        # All paths are unmapped → treat as Level 12 / The Meta.
        level_id = 12
        print(
            f"level-discipline: NOTE: all {len(paths)} touched path(s) are unmapped; "
            "classifying as Level 12 (The Meta)"
        )
    else:
        level_id = next(iter(unique_levels))

    if unmapped and unique_levels and 12 not in unique_levels:
        sys.stderr.write(
            f"level-discipline: FAIL: PR mixes Level {level_id} paths with {len(unmapped)} unmapped path(s); "
            "an unmapped path is implicitly Level 12 / The Meta which conflicts with the explicit level. "
            "Either add the unmapped paths to docs/schemas/levels.yaml, or split this PR.\n"
            f"  unmapped (first 5): {unmapped[:5]}\n"
        )
        return 1

    authorized_actors = _resolve_authorized_actors(level_id, levels, roles)
    if not authorized_actors:
        sys.stderr.write(
            f"level-discipline: FAIL: Level {level_id}'s `proposer:` string in levels.yaml does not "
            "resolve via roles.yaml.level_proposer_resolution. Doctrine drift; fix the schema.\n"
        )
        return 1

    ok, resolved = _initiator_authorized(pr_author, authorized_actors, roles)
    if not ok:
        sys.stderr.write(
            f"level-discipline: FAIL: PR initiator '{pr_author}' is not authorized for Level {level_id}\n"
            f"  authorized actors: {sorted(authorized_actors)}\n"
            f"  remediation: either route this PR through an authorized initiator, "
            "or add '{pr_author}' to docs/schemas/roles.yaml github_identity_map under the appropriate actor "
            "(itself a Level 7 / The Governance change requiring Tier-2 cosign).\n"
        )
        return 1

    if resolved == "community-tier-unverifiable":
        print(
            f"level-discipline: WARN: Level {level_id} merge by '{pr_author}' "
            "accepted as community-tier-unverifiable (wallet-to-handle binding deferred to Phase 6+)"
        )
        print(f"level-discipline: OK (Level {level_id}, community-tier permissive)")
        return 0

    print(
        f"level-discipline: OK (Level {level_id}, initiator '{pr_author}' resolved to actor '{resolved}', "
        f"{len(paths)} path(s) all conformant)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
