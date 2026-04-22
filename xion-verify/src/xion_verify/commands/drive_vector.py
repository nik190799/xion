"""`xion-verify drive-vector` — Invariant 15 (Drive Vector Excludes Revenue).

Two complementary checks, both live as of Phase 5c:

  1. Static doctrine audit. `docs/08-AUTO-RESEARCH.md` must declare the
     `payback_horizon` enum as `survival | service | meaning` and must
     NOT contain any variant that says `revenue`, `money`, `price`, etc.
     This is the same check that shipped pre-5c.

  2. Live module audit. `orchestrator.volition.compute_drive_vector`'s
     signature is walked by ast: NO parameter name may match the
     forbidden revenue-ish set (`revenue`, `fees`, `rebates`, `price`,
     `balance`, `tips`, `donations`, `engagement`). The function's body
     is walked for attribute reads off the `state` parameter, and every
     `state.<a>.<b>` read must be listed in
     `orchestrator.volition.SOURCE_WHITELIST["survive" | "serve" |
     "meaning"]`. A silent refactor that tried to read, say,
     `state.interoception.treasury_stress` into the survive term would
     fail this check, because `treasury_stress` is not whitelisted.

The `--strict` flag is retained for backward compatibility but is now a
no-op: the live audit runs unconditionally (there is no longer a
NOT_YET_SEALED path for this verifier).
"""

from __future__ import annotations

import ast
import inspect
import re
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_PROHIBITED_SUBSTRINGS: tuple[str, ...] = (
    "payback_horizon: revenue",
    "payback_horizon: Revenue",
    "payback_horizon: money",
    "payback_horizon: price",
)

_REQUIRED_PAYBACK_HORIZON_ENUM = re.compile(
    r"payback_horizon:\s*survival\s*\|\s*service\s*\|\s*meaning"
)

# Parameter names that would, by their mere presence, breach Invariant 15.
# The drive vector is defined precisely by what it does NOT read; if a
# future PR adds one of these as a kwarg to compute_drive_vector, we
# refuse it at CI time regardless of what the function body does with it.
_FORBIDDEN_PARAM_NAMES: frozenset[str] = frozenset({
    "revenue",
    "fees",
    "rebates",
    "price",
    "balance",
    "tips",
    "donations",
    "engagement",
})


def _audit_proposal_doctrine(repo_root: Path) -> list[str]:
    errors: list[str] = []
    path = repo_root / "docs" / "08-AUTO-RESEARCH.md"
    if not path.is_file():
        return [f"missing doctrine: {path}"]
    text = path.read_text(encoding="utf-8")
    for bad in _PROHIBITED_SUBSTRINGS:
        if bad in text:
            errors.append(f"docs/08-AUTO-RESEARCH.md contains forbidden fragment: {bad!r}")
    if "payback_horizon" not in text:
        errors.append("docs/08-AUTO-RESEARCH.md missing payback_horizon in proposal schema")
    if not _REQUIRED_PAYBACK_HORIZON_ENUM.search(text):
        errors.append(
            "docs/08-AUTO-RESEARCH.md does not declare payback_horizon enum as 'survival | service | meaning'"
        )
    return errors


def _audit_compute_drive_vector_signature(func: object) -> list[str]:
    """Assert no parameter of `compute_drive_vector` is in the forbidden
    revenue-ish set. `inspect.signature` reads the live object; a decorator
    that hides the signature would be caught as a separate failure in
    `_audit_compute_drive_vector_ast`."""
    errors: list[str] = []
    try:
        sig = inspect.signature(func)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        return [f"could not introspect compute_drive_vector signature: {type(exc).__name__}: {exc}"]
    for param_name in sig.parameters:
        if param_name.lower() in _FORBIDDEN_PARAM_NAMES:
            errors.append(
                f"compute_drive_vector has forbidden parameter name {param_name!r} "
                "(Invariant 15: drive vector must not read revenue-like inputs)"
            )
    return errors


def _collect_chained_attribute_reads(
    module_path: Path, func_names: tuple[str, ...], root_param: str
) -> tuple[list[str], dict[str, set[str]]]:
    """Walk `module_path`'s AST and return, per function name in
    `func_names`, the set of `<a>.<b>` chains observed as attribute reads
    off `root_param` (typically `state`).

    Returns `(errors, reads_by_func)`. If the module won't parse, the
    errors list explains why and `reads_by_func` is empty.
    """
    errors: list[str] = []
    reads_by_func: dict[str, set[str]] = {name: set() for name in func_names}
    try:
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    except SyntaxError as exc:
        return [f"could not parse {module_path}: {exc}"], reads_by_func

    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for name in func_names:
        if name not in funcs:
            errors.append(f"{module_path.name} does not define function {name!r}")
            continue
        for node in ast.walk(funcs[name]):
            # Match `state.<a>.<b>` (two-level attribute chain rooted at
            # the state parameter). Anything deeper is flattened to its
            # two-level prefix; the whitelist is keyed at that depth.
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Attribute)
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == root_param
            ):
                sense = node.value.attr  # e.g. "interoception"
                field = node.attr         # e.g. "survival_pressure"
                reads_by_func[name].add(f"{sense}.{field}")
    return errors, reads_by_func


def _audit_compute_drive_vector_ast(repo_root: Path) -> list[str]:
    """Live AST check against `orchestrator.volition.SOURCE_WHITELIST`.

    We parse `orchestrator/volition.py` from disk (not the compiled
    `__code__` of the imported function) so the check is reproducible
    across bytecode cache states and so auditors can trivially re-run it
    by inspection."""
    errors: list[str] = []
    vol_path = repo_root / "orchestrator" / "volition.py"
    if not vol_path.is_file():
        return [f"missing module: {vol_path}"]

    try:
        from orchestrator.volition import (
            SOURCE_WHITELIST,
            compute_drive_vector,
        )
    except ImportError as exc:
        return [f"cannot import orchestrator.volition: {type(exc).__name__}: {exc}"]

    errors.extend(_audit_compute_drive_vector_signature(compute_drive_vector))

    # `compute_drive_vector` delegates survive-term reads to
    # `_survive_from_state`; serve / meaning are Genesis-default
    # constants at Phase 5c. The survive whitelist is therefore the
    # only set with non-empty expectations today.
    parse_errs, reads = _collect_chained_attribute_reads(
        vol_path,
        func_names=("compute_drive_vector", "_survive_from_state"),
        root_param="state",
    )
    errors.extend(parse_errs)

    allowed_anywhere: set[str] = set()
    for term_reads in SOURCE_WHITELIST.values():
        allowed_anywhere.update(term_reads)

    for func_name, observed in reads.items():
        illegal = observed - allowed_anywhere
        for bad in sorted(illegal):
            errors.append(
                f"orchestrator/volition.py::{func_name} reads state.{bad} which is not in "
                f"SOURCE_WHITELIST (any term); widening the whitelist requires a doctrine edit"
            )

    # Additional structural check: every entry in the "survive" whitelist
    # that is read by ANY of the audited functions must appear in the
    # observed set, OR the whitelist entry must be removed. This catches
    # the reverse drift (whitelist widens but code never uses it — honest
    # narrowing opportunity).
    survive_observed = reads.get("_survive_from_state", set()) | reads.get(
        "compute_drive_vector", set()
    )
    survive_allowed = SOURCE_WHITELIST.get("survive", frozenset())
    dead_whitelist = survive_allowed - survive_observed
    for dead in sorted(dead_whitelist):
        errors.append(
            f"SOURCE_WHITELIST['survive'] includes state.{dead} but no audited function "
            "reads it; either wire the read or narrow the whitelist"
        )

    return errors


@click.command(
    name="drive-vector",
    help="Invariant 15: static doctrine audit + live AST audit of compute_drive_vector (Phase 5c).",
)
@click.option(
    "--strict",
    is_flag=True,
    help="(No-op as of Phase 5c; the live audit now runs unconditionally.)",
)
def drive_vector(strict: bool) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"drive-vector: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    errs: list[str] = []
    errs.extend(_audit_proposal_doctrine(repo_root))
    errs.extend(_audit_compute_drive_vector_ast(repo_root))
    if errs:
        for e in errs:
            click.echo(f"drive-vector: FAIL: {e}", err=True)
        sys.exit(FAIL)

    click.echo(
        "drive-vector: OK (doctrine + live AST audit pass; "
        "compute_drive_vector body stays inside SOURCE_WHITELIST)"
    )
    sys.exit(OK)
