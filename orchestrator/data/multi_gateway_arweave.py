"""Arweave multi-gateway reader."""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from urllib.parse import quote, urljoin

from orchestrator.data._quorum_base import QuorumFailedError, QuorumResult, require_quorum


@dataclass(frozen=True)
class MultiGatewayArweaveReader:
    gateways: tuple[str, ...]
    timeout_s: float = 10.0

    def __post_init__(self) -> None:
        if len(self.gateways) < 2:
            raise QuorumFailedError("MultiGatewayArweaveReader requires at least 2 gateways")

    def tx_data(self, tx_id: str) -> QuorumResult[bytes]:
        safe_tx = quote(tx_id, safe="")

        def fetch(gateway: str) -> bytes:
            base = gateway if gateway.endswith("/") else gateway + "/"
            url = urljoin(base, f"tx/{safe_tx}/data")
            req = urllib.request.Request(url, headers={"User-Agent": "xion-os/quorum"})
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.read()

        return require_quorum(list(self.gateways), fetch, min_endpoints=2)


__all__ = ["MultiGatewayArweaveReader"]
