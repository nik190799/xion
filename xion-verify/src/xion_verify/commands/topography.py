"""``xion-verify topography`` — :func:`GET /self` structural audit (Phase 6.4.b)."""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path
from typing import TextIO

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


def verify_topography(repo_root: Path, stdout: TextIO) -> int:
    """Invoke a hermetic FastAPI app and assert ``/self`` shape."""
    import os

    try:
        root = find_repo_root(repo_root)
    except RepoRootNotFound as e:
        click.echo(f"topography: FAIL: {e}", err=True)
        return FAIL
    rroot = str(root.resolve())
    if rroot not in sys.path:
        sys.path.insert(0, rroot)

    pytest = __import__("pytest")
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from orchestrator.api import AppDeps, create_app
    from orchestrator.inference_router import (
        InferenceRouter,
        OpenWeightsFloorStub,
        default_manifest_path,
    )
    from orchestrator.relay import Relay

    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        env_add = {
            "XION_SENSORIUM_LEDGER": str(t / "SENSORIUM_LEDGER.jsonl"),
            "XION_REQUEST_LEDGER": str(t / "REQUEST.jsonl"),
            "XION_PAYMENT_LEDGER": str(t / "PAYMENT.jsonl"),
            "XION_BILLING_REQUIRED": "false",
            "XION_API_REQUIRE_BEARER": "false",
        }
        old: dict[str, str | None] = {k: os.environ.get(k) for k in env_add}
        try:
            for k, v in env_add.items():
                os.environ[k] = v
            relay = Relay(
                safety_ledger_path=t / "safety.jsonl",
                sensorium_ledger_path=t / "SENSORIUM_LEDGER.jsonl",
            )
            router = InferenceRouter(
                manifest_path=default_manifest_path(), policy_mode="hosted_api_first"
            )
            router.register(OpenWeightsFloorStub(provider_id="xion-verify-topography-stub"))
            app = create_app(
                AppDeps(
                    relay=relay,
                    tick_cadence_s=0.01,
                    sensorium_ledger_path=t / "SENSORIUM_LEDGER.jsonl",
                    router=router,
                )
            )
            with TestClient(app) as client:
                r = client.get("/self")
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    if r.status_code != 200:
        click.echo(
            f"topography: FAIL: GET /self -> {r.status_code} {r.text[:500]}",
            file=stdout,
        )
        return FAIL
    data = r.json()
    for k in ("topography", "sensorium", "vitals", "governance", "as_of_utc_ns"):
        if k not in data:
            click.echo(f"topography: FAIL: missing {k!r}", file=stdout)
            return FAIL
    if not re.fullmatch(r"[0-9a-f]{64}", str(data["topography"].get("lineage_hash", ""))):
        click.echo("topography: FAIL: lineage_hash not 64-hex", file=stdout)
        return FAIL
    if data["topography"].get("soul_prompt_sha_drift", None) is None:
        click.echo("topography: FAIL: missing soul_prompt_sha_drift", file=stdout)
        return FAIL
    doms = data["vitals"].get("domains", [])
    if len(doms) < 8:
        click.echo("topography: FAIL: expected >=8 vitals domains", file=stdout)
        return FAIL
    floor = int(data["topography"].get("provider_floor_count", 0) or 0)
    if floor < 1:
        click.echo("topography: FAIL: Invariant-17 needs >=1 open-weights id", file=stdout)
        return FAIL
    api = data["topography"].get("api_surface")
    rows = api if isinstance(api, list) else []
    has_chat = any(
        x.get("auth_required") and "/chat" in str(x.get("path", "")) for x in rows
    ) or any("/chat" in str(x) for x in rows)
    if not rows or not has_chat:
        click.echo("topography: FAIL: api_surface missing /chat row", file=stdout)
        return FAIL
    click.echo(
        f"topography: OK (self-knowledge: lineage={data['topography']['lineage_hash'][:8]}...)",
        file=stdout,
    )
    return OK


@click.command("topography")
def topography_cli() -> None:
    from sys import stdout

    from xion_verify.exit_codes import exit_code_to_system_exit

    c = Path.cwd()
    try:
        root = find_repo_root(c)
    except RepoRootNotFound:
        click.echo("topography: FAIL: not inside a xion git checkout", err=True)
        raise SystemExit(1) from None
    raise SystemExit(exit_code_to_system_exit(verify_topography(root, stdout)))
