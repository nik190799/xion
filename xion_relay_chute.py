"""Repo-root Chutes deployment module for the live Xion Relay surface.

The Chutes CLI in this environment only accepts a top-level module reference
(``xion_relay_chute:chute``), so the deployable object stays self-contained
here.

What this module promises (Four Questions, per The-Xion-Builder):

- *Property*: a public Chutes deployment exists for chute id
  ``89866bfc-5ddd-5382-b887-116d8901808f`` whose three cords (``GET /health``,
  ``GET /quote``, ``GET /self``) proxy the live in-process FastAPI Relay.
  ``/quote`` maps to the Relay's local ``/pricing`` endpoint because
  ``/pricing`` is intercepted by the Chutes platform proxy itself.
- *Invariants touched*: strengthens Invariant 17 by booting through the
  production API lifespan, which wires the Chutes hosted provider and local
  Ollama floor from environment when available. No constitutional state is
  mutated by this adapter.
- *Verification*: ``scripts/debug-chute-d3.sh`` exercises the public
  endpoints; ``scripts/verify-chute-cords.sh --mode=live`` asserts the live
  Relay response shape before the registry row is promoted.
- *Deprecation*: replaced by a native Chutes ASGI entrypoint if the platform
  supports it cleanly. Until then the subprocess boundary keeps the Chutes
  cord runtime and the FastAPI app lifecycle isolated.

Why this shape now: the d3-6 smoke image proved the Chutes cord pipeline
end-to-end. This d3-7 shape returns to the full Relay subprocess, but points
at ``python -m orchestrator.api`` so ``AppDeps`` is constructed with a real
``Relay`` through ``orchestrator.api.launcher`` rather than a hand-rolled
partial object.
"""

from __future__ import annotations

import asyncio
import signal
import subprocess
from typing import Any

import httpx
from chutes.chute import Chute, NodeSelector
from chutes.image import Image


SERVICE_NAME = "xion-relay-chutes"
IMAGE_TAG = "pre-genesis-d3-7"
RELAY_PORT = 8000
RELAY_BASE_URL = f"http://127.0.0.1:{RELAY_PORT}"
RELAY_BOOT_TIMEOUT_S = 180

# Three routing facts the D3-4 / D3-5 / D3-6 builds proved against the
# live Chutes platform, recorded so the next maintainer does not relearn
# them:
#
# 1. ``GET /pricing`` on ``*.chutes.ai`` is intercepted by the Chutes
#    platform proxy itself — it returns the platform's GPU pricing payload
#    ({"tao_usd":..., "gpu_price_estimates":{...}}) before the request
#    ever reaches a chute cord.  We saw this on a live ``pre-genesis-d3-5``
#    instance with ``/health`` and ``/self`` simultaneously returning the
#    chute's own envelope.
# 2. The two-segment public path ``/xion/pricing`` consistently returns a
#    fast (<200 ms) ``502 Bad Gateway`` from the platform's nginx ingress.
# 3. Even with the public path moved to single-segment ``/xpricing`` on
#    the d3-6 build, requests still 502'd in <200 ms.  The cause is that
#    the Chutes ``Cord`` defaults the *internal* upstream path to the
#    Python function name (``self.path = func.__name__``), so a function
#    named ``pricing`` exposes internal path ``/pricing`` even when the
#    public path is renamed.  The Chutes Aegis layer on the worker
#    rejects the upstream ``/pricing`` path the same way the public proxy
#    does, surfacing as a fast nginx 502.
#
# A follow-up metadata-only deploy proved ``/xpricing`` still 502s even
# after the internal path is also ``/xpricing``. The working rule is
# therefore stricter: keep the Chutes-deployed smoke cord out of the
# platform's pricing namespace entirely. ``/quote`` is the B4 smoke path;
# the in-process FastAPI Relay (when the full surface lands) still serves
# ``/pricing`` locally.
# ``/health`` and ``/self`` are not reserved and route straight through,
# so they keep their canonical Relay paths.


image = (
    Image(
        username="nikhilkadalge",
        name="xion-relay",
        tag=IMAGE_TAG,
        readme=(
            "Xion pre-genesis Relay runtime image — D3 cord smoke build. "
            "Static cord responses only; full Relay subprocess returns in a "
            "follow-up build."
        ),
    )
    .from_base("parachutes/python:3.12")
    .add("pyproject.toml", "/app/pyproject.toml")
    .add("README.md", "/app/README.md")
    .add("orchestrator", "/app/orchestrator")
    .add("docs", "/app/docs")
    .set_workdir("/app")
    .run_command(
        "python -m pip install --user --no-cache-dir '.[api]' chutes httpx"
    )
    .with_env("XION_CHUTE_SERVICE", SERVICE_NAME)
    .with_env("XION_CHUTE_IMAGE_TAG", IMAGE_TAG)
    .with_env("XION_API_HOST", "127.0.0.1")
    .with_env("XION_API_PORT", str(RELAY_PORT))
    .with_env("XION_API_WORKERS", "1")
    .with_env("XION_API_REQUIRE_BEARER", "false")
    .with_env("XION_BILLING_REQUIRED", "true")
    .with_env("XION_BILLING_ALLOW_X402", "true")
)


chute = Chute(
    username="nikhilkadalge",
    name="xion-relay-pre-genesis-d3",
    tagline="Xion pre-genesis Relay on Chutes",
    readme=(
        "Xion Relay deployment adapter for D3 discovery verification. "
        "This build boots the live FastAPI Relay subprocess and proxies "
        "public Chutes cords to /health, /pricing, and /self locally."
    ),
    image=image,
    node_selector=NodeSelector(gpu_count=1, min_vram_gb_per_gpu=16),
    concurrency=4,
    max_instances=1,
    shutdown_after_seconds=300,
    allow_external_egress=True,
)


async def _wait_for_relay() -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        for _ in range(RELAY_BOOT_TIMEOUT_S):
            try:
                response = await client.get(f"{RELAY_BASE_URL}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1)
    raise RuntimeError(
        f"xion-orchestrator-api did not become healthy within {RELAY_BOOT_TIMEOUT_S}s"
    )


async def _get_json(path: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{RELAY_BASE_URL}{path}")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        return {"status": "ok", "value": data}


@chute.on_startup()
async def start_relay(self: Chute) -> None:
    proc = subprocess.Popen(["python", "-m", "orchestrator.api"])
    self.state.xion_relay_proc = proc
    await _wait_for_relay()


@chute.on_shutdown()
async def stop_relay(self: Chute) -> None:
    proc = getattr(self.state, "xion_relay_proc", None)
    if proc is None or proc.poll() is not None:
        return
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@chute.cord(public_api_path="/health", public_api_method="GET")
async def health(self: Chute) -> dict[str, Any]:
    return await _get_json("/health")


@chute.cord(public_api_path="/quote", public_api_method="GET")
async def quote(self: Chute) -> dict[str, Any]:
    return await _get_json("/pricing")


@chute.cord(public_api_path="/self", public_api_method="GET")
async def self_endpoint(self: Chute) -> dict[str, Any]:
    return await _get_json("/self")


__all__ = ["chute"]
