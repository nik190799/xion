"""Verify the Phase 6.9 Chutes provider surface."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="inference-provider-chutes")
def inference_provider_chutes() -> None:
    try:
        repo = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"inference-provider-chutes: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    checks = [
        repo / "orchestrator/inference_router/providers/chutes.py",
        repo / "orchestrator/billing/providers/chutes_billing.py",
        repo / "orchestrator/treasury/topup.py",
    ]
    missing = [str(p.relative_to(repo)) for p in checks if not p.is_file()]
    if missing:
        click.echo(
            "inference-provider-chutes: FAIL: missing " + ", ".join(missing),
            err=True,
        )
        sys.exit(FAIL)

    provider_text = (repo / "orchestrator/inference_router/providers/chutes.py").read_text(encoding="utf-8")
    required_tokens = [
        "https://llm.chutes.ai/v1",
        "moonshotai/Kimi-K2.6-TEE",
        "confidential_compute",
        "intel_tdx_via_chutes",
        "InsufficientCreditsError",
    ]
    absent = [tok for tok in required_tokens if tok not in provider_text]
    if absent:
        click.echo(
            "inference-provider-chutes: FAIL: provider missing tokens "
            + ", ".join(absent),
            err=True,
        )
        sys.exit(FAIL)

    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    for token in ("XION_CHUTES_API_KEY", "XION_CHUTES_TEE_REQUIRED=true"):
        if token not in env_text:
            click.echo(f"inference-provider-chutes: FAIL: .env.example missing {token}", err=True)
            sys.exit(FAIL)

    click.echo("inference-provider-chutes: OK (Chutes provider + TEE defaults wired)")
    sys.exit(OK)


__all__ = ["inference_provider_chutes"]
