"""Polls (or subscribes to) the AO process for new state-tip emissions and STATE_REJECTIONs, writes ledger rows."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from orchestrator.ao_core.ledger import StateChainRecord, append

logger = logging.getLogger(__name__)

class AOCoreListener:
    def __init__(self, process_id: str, ledger_path: Path, aos_binary_path: str = "aos"):
        self.process_id = process_id
        self.ledger_path = ledger_path
        self.aos_binary_path = aos_binary_path
        self.last_cursor = None

    async def run_once(self) -> None:
        """Poll the AO process for new messages and write to the ledger."""
        # Query the AO process for its state
        # In a real deployment, this would use the AO HTTP API (CU) to read the process state
        # and fetch the latest STATE_TIP_EMISSION messages.
        # For Phase 6.1, we simulate reading the state via aos CLI
        
        cmd = [
            self.aos_binary_path,
            self.process_id,
            "--eval",
            "return { height = state.state_tip_height, root = state.state_root_sha256, prev = state.prev_state_root_sha256 }"
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"listener failed: {stderr.decode()}")
                return

            # Parse the Lua output (very naive parsing for the skeleton)
            output = stdout.decode().strip()
            # Expected output format from aos: { height = 1, root = "...", prev = "..." }
            
            # This is a stub implementation for the skeleton
            # In a real deployment, we would parse the JSON/Lua table properly
            # and write the StateChainRecord to the ledger
            
            # Example record write:
            # record = StateChainRecord(
            #     correlation_id="...",
            #     height=1,
            #     state_root_sha256="...",
            #     prev_state_root_sha256="...",
            #     ao_process_id=self.process_id,
            #     ao_message_id="...",
            #     committed_by="...",
            #     committed_at_unix=int(time.time()),
            # )
            # append(self.ledger_path, record)
            
        except Exception as e:
            logger.error(f"listener error: {e}")

    async def loop(self, interval_seconds: float = 10.0) -> None:
        """Supervisor-friendly loop."""
        logger.info(f"Starting AO Core listener loop for process {self.process_id}")
        while True:
            await self.run_once()
            await asyncio.sleep(interval_seconds)

__all__ = ["AOCoreListener"]
