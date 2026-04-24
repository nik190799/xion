"""Async wrapper around `ao` HTTP API for the Relay to invoke `commit-state`."""

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

class AOCoreClient:
    def __init__(self, process_id: str, aos_binary_path: str = "aos"):
        self.process_id = process_id
        self.aos_binary_path = aos_binary_path

    async def commit_state(
        self,
        tip_height: int,
        state_root_sha256: str,
        correlation_id: str,
    ) -> bool:
        """Invoke commit-state on the AO process via `aos` CLI subprocess."""
        # For Phase 6.1 we use the aos CLI to send messages to the process
        # In a real deployment, we would use the AO HTTP API (CU/MU/SU) directly
        # but the aos CLI is the recommended way to interact with AO Mainnet testnet
        cmd = [
            self.aos_binary_path,
            self.process_id,
            "--eval",
            f'Send({{Target = "{self.process_id}", Action = "commit-state", tip_height = "{tip_height}", state_root_sha256 = "{state_root_sha256}", correlation_id = "{correlation_id}"}})'
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"commit-state failed: {stderr.decode()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"commit-state error: {e}")
            return False

__all__ = ["AOCoreClient"]
