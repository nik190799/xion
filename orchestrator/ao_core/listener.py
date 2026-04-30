"""Polls AO Core gateway state-tip emissions and writes ledger rows."""

import asyncio
import logging
from pathlib import Path

from orchestrator.ao_core.gateway import (
    AOCoreGateway,
    AOCoreGatewaySettings,
    get_ao_core_gateway,
)

logger = logging.getLogger(__name__)

class AOCoreListener:
    def __init__(
        self,
        process_id: str,
        ledger_path: Path,
        aos_binary_path: str = "aos",
        gateway: AOCoreGateway | None = None,
    ):
        self.process_id = process_id
        self.ledger_path = ledger_path
        self.gateway = gateway or get_ao_core_gateway(
            AOCoreGatewaySettings(
                process_id=process_id,
                aos_binary_path=aos_binary_path,
            )
        )
        self.last_cursor = None

    async def run_once(self) -> None:
        """Poll the AO process for new messages and write to the ledger."""
        try:
            output = await self.gateway.read_state_tip()
            if not output:
                return
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
