"""Chutes deployment wrapper for the Xion Relay.

This file is intentionally a thin deployment adapter. The Relay runtime remains
`xion-orchestrator-api`; Chutes cords only proxy public health/pricing/self
checks to the local process so the deployment can be registered and warmed by
the Chutes platform.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
from typing import Any

import httpx
from chutes.chute import Chute, NodeSelector
from chutes.image import Image


RELAY_PORT = int(os.getenv("XION_CHUTES_RELAY_PORT", "8000"))
RELAY_BASE_URL = f"http://127.0.0.1:{RELAY_PORT}"


image = (
    Image(
        username="nikhilkadalge",
        name="xion-relay",
        tag="pre-genesis-d3-2",
        readme="Xion pre-genesis Relay runtime image for D3 discovery verification.",
    )
    .from_base("parachutes/python:3.12")
    .add("pyproject.toml", "/app/pyproject.toml")
    .add("README.md", "/app/README.md")
    .add("orchestrator", "/app/orchestrator")
    .set_workdir("/app")
    .run_command(
        "python -m pip install --user --no-cache-dir '.[api]' chutes httpx"
    )
    .with_env("XION_API_HOST", "127.0.0.1")
    .with_env("XION_API_PORT", str(RELAY_PORT))
    .with_env("XION_API_WORKERS", "1")
    .with_env("XION_BILLING_REQUIRED", "false")
    .with_env("XION_API_REQUIRE_BEARER", "false")
)


chute = Chute(
    username="nikhilkadalge",
    name="xion-relay-pre-genesis-d3",
    tagline="Xion pre-genesis Relay on Chutes",
    readme="Xion Relay deployment adapter for D3 discovery verification.",
    image=image,
    node_selector=NodeSelector(gpu_count=1, min_vram_gb_per_gpu=16),
    concurrency=4,
    max_instances=1,
    shutdown_after_seconds=300,
    allow_external_egress=True,
)


async def _wait_for_relay() -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        for _ in range(60):
            try:
                response = await client.get(f"{RELAY_BASE_URL}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1)
    raise RuntimeError("xion-orchestrator-api did not become healthy within 60s")


async def _get_json(path: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{RELAY_BASE_URL}{path}")
        response.raise_for_status()
        return response.json()


@chute.on_startup()
async def start_relay(self: Chute) -> None:
    env = os.environ.copy()
    env.setdefault("XION_API_HOST", "127.0.0.1")
    env.setdefault("XION_API_PORT", str(RELAY_PORT))
    env.setdefault("XION_API_WORKERS", "1")
    env.setdefault("XION_BILLING_REQUIRED", "false")
    env.setdefault("XION_API_REQUIRE_BEARER", "false")
    proc = subprocess.Popen(["python", "-m", "orchestrator.api"], env=env)
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


@chute.cord(public_api_path="/pricing", public_api_method="GET")
async def pricing(self: Chute) -> dict[str, Any]:
    return await _get_json("/pricing")


@chute.cord(public_api_path="/self", public_api_method="GET")
async def self_endpoint(self: Chute) -> dict[str, Any]:
    return await _get_json("/self")
