"""AO Core gateway providers.

The Relay depends on the ``AOCoreGateway`` Protocol from
``orchestrator.ao_core.gateway``. This module holds concrete provider
implementations only.
"""

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LocalnetAOCoreGateway:
    """Localnet/dev AO gateway backed by the ``aos`` CLI."""

    process_id: str
    aos_binary_path: str = "aos"

    async def read_state_tip(self) -> str:
        """Read the current state tip through the operator-proven ``aos`` path."""
        cmd = [
            self.aos_binary_path,
            self.process_id,
            "--eval",
            "return { height = state.state_tip_height, root = state.state_root_sha256, prev = state.prev_state_root_sha256 }",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error("read-state-tip failed: %s", stderr.decode())
                return ""
            return stdout.decode().strip()
        except Exception as e:
            logger.error("read-state-tip error: %s", e)
            return ""

    async def commit_state(
        self,
        tip_height: int,
        state_root_sha256: str,
        correlation_id: str,
    ) -> bool:
        """Invoke commit-state on the AO process via ``aos`` subprocess."""
        # Phase 6.1 uses the aos CLI because it is the operator-proven localnet
        # path. Legacynet CU/MU/SU messaging lives behind a separate provider.
        cmd = [
            self.aos_binary_path,
            self.process_id,
            "--eval",
            f'Send({{Target = "{self.process_id}", Action = "commit-state", tip_height = "{tip_height}", state_root_sha256 = "{state_root_sha256}", correlation_id = "{correlation_id}"}})',
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error("commit-state failed: %s", stderr.decode())
                return False

            return True
        except Exception as e:
            logger.error("commit-state error: %s", e)
            return False


@dataclass(slots=True)
class LegacynetAOCoreGateway:
    """Future AO legacynet gateway placeholder.

    This provider is intentionally selectable so operator posture is explicit,
    but it must not fake connectivity before CU/MU/SU HTTP messaging is wired.
    """

    process_id: str
    ao_gateway_url: str = "https://arweave.net"

    async def read_state_tip(self) -> str:
        raise NotImplementedError(
            "AO Core legacynet read-state-tip is not wired yet; "
            "KW-AOCORE-CLIENT-001 remains open until CU/MU/SU HTTP reads land "
            "behind AOCoreGateway."
        )

    async def commit_state(
        self,
        tip_height: int,
        state_root_sha256: str,
        correlation_id: str,
    ) -> bool:
        raise NotImplementedError(
            "AO Core legacynet gateway is not wired yet; KW-AOCORE-CLIENT-001 "
            "remains open until CU/MU/SU HTTP messaging lands behind "
            "AOCoreGateway."
        )


class AOCoreClient(LocalnetAOCoreGateway):
    """Backward-compatible name for the localnet provider.

    New call sites should import ``AOCoreGateway`` or ``get_ao_core_gateway``
    from ``orchestrator.ao_core.gateway`` instead of this concrete provider.
    """

    def __init__(self, process_id: str, aos_binary_path: str = "aos"):
        super().__init__(process_id=process_id, aos_binary_path=aos_binary_path)


__all__ = ["AOCoreClient", "LegacynetAOCoreGateway", "LocalnetAOCoreGateway"]
