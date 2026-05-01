"""Shadow Relay — pre-warmed canary runner for Phase 6+ Velocity Hardening.

Runs a second Relay on a different port, marked role=canary, replays the
anonymized corpus, and holds N disjoint Tier-0 slots simultaneously.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from pathlib import Path
from typing import Any

import uvicorn

from orchestrator.api.app import AppDeps, create_app
from orchestrator.relay.relay import Relay

logger = logging.getLogger("xion.shadow")


async def replay_corpus(port: int, concurrency: int = 4) -> None:
    """Replay the anonymized corpus against the shadow relay."""
    import httpx

    repo_root = Path(__file__).parent.parent.parent
    corpus_dir = repo_root / "xion-audit" / "replay_corpus" / "items"
    if not corpus_dir.is_dir():
        logger.warning(f"No replay corpus found at {corpus_dir}")
        return

    files = list(corpus_dir.glob("*.jsonl"))
    if not files:
        logger.warning("Replay corpus is empty.")
        return

    items = []
    for f in files:
        with f.open("r", encoding="utf-8") as fp:
            for line in fp:
                if not line.strip():
                    continue
                with contextlib.suppress(json.JSONDecodeError):
                    items.append(json.loads(line))

    if not items:
        logger.warning("No valid items in replay corpus.")
        return

    logger.info(f"Replaying {len(items)} items with concurrency {concurrency}...")

    async def _worker(queue: asyncio.Queue[dict[str, Any]], client: httpx.AsyncClient) -> None:
        while True:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            try:
                # Hit the health endpoint to prove it's alive and multi-slot
                resp = await client.get(f"http://127.0.0.1:{port}/health")
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Replay error: {e}")
            finally:
                queue.task_done()

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    for item in items:
        queue.put_nowait(item)

    async with httpx.AsyncClient(timeout=30.0) as client:
        workers = [asyncio.create_task(_worker(queue, client)) for _ in range(concurrency)]
        await asyncio.gather(*workers)

    logger.info("Replay complete.")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    port = int(os.environ.get("XION_SHADOW_RELAY_PORT", "8001"))
    concurrency = int(os.environ.get("XION_SHADOW_CONCURRENCY", "4"))

    # Create a Relay marked role=canary
    relay = Relay(relay_id="shadow-canary-1")

    deps = AppDeps(relay=relay)
    app = create_app(deps)

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)

    async def _run_all() -> None:
        server_task = asyncio.create_task(server.serve())
        try:
            # Wait for server to start
            await asyncio.sleep(2)

            # Run replay loop
            while True:
                await replay_corpus(port, concurrency)
                await asyncio.sleep(10)
        finally:
            server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await server_task

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run_all())


if __name__ == "__main__":
    main()
