"""Verify Arbiter deterministic safety-path pins."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="arbiter-determinism")
def arbiter_determinism() -> None:
    try:
        repo = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"arbiter-determinism: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    path = repo / "orchestrator/safety/providers/chutes_llm_judge.py"
    if not path.is_file():
        click.echo("arbiter-determinism: FAIL: Chutes LLM judge provider missing", err=True)
        sys.exit(FAIL)
    text = path.read_text(encoding="utf-8")
    required = [
        "temperature=0",
        "top_p=1",
        "seed=_SEED",
        'reasoning_effort="high"',
        "response_format=_JSON_SCHEMA",
        "deepseek-ai/DeepSeek-V3.2",
    ]
    missing = [token for token in required if token not in text]
    if missing:
        click.echo(
            "arbiter-determinism: FAIL: missing deterministic pins "
            + ", ".join(missing),
            err=True,
        )
        sys.exit(FAIL)
    click.echo("arbiter-determinism: OK (Chutes judge pins deterministic safety path)")
    sys.exit(OK)


__all__ = ["arbiter_determinism"]
