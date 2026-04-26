"""`xion-verify benchmark` — local BENCHMARK_LEDGER readout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_LEDGER = "ledgers/BENCHMARK_LEDGER.jsonl"


def _verify(path: Path) -> tuple[int, str]:
    if not path.is_file():
        return NOT_YET_SEALED, f"{_LEDGER} not found"
    try:
        from orchestrator.benchmark.runner import verify_benchmark_chain

        count, tip = verify_benchmark_chain(path)
    except Exception as exc:
        return FAIL, str(exc)
    if count == 0:
        return NOT_YET_SEALED, f"{_LEDGER} contains no rows"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest = rows[-1]
    return OK, (
        f"rows={count} tip={tip} latest_suite={latest.get('suite_id')} "
        f"tasks={latest.get('task_count')} p95_latency_ms={latest.get('p95_latency_ms')}"
    )


@click.command(name="benchmark", help="Hermes peer-benchmark readout from BENCHMARK_LEDGER.")
def benchmark() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"benchmark: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    code, message = _verify(repo_root / _LEDGER)
    if code == OK:
        click.echo(f"benchmark: OK ({message})")
    elif code == NOT_YET_SEALED:
        click.echo(f"benchmark: NOT_YET_SEALED — {message}")
    else:
        click.echo(f"benchmark: FAIL: {message}", err=True)
    sys.exit(code)


__all__ = ["benchmark"]
