"""Base/EVM JSON-RPC majority reader."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from orchestrator.data._quorum_base import QuorumFailedError, QuorumResult, require_quorum


@dataclass(frozen=True)
class MultiRpcMajorityReader:
    endpoints: tuple[str, ...]
    timeout_s: float = 10.0

    def __post_init__(self) -> None:
        if len(self.endpoints) < 3:
            raise QuorumFailedError("MultiRpcMajorityReader requires at least 3 endpoints")

    def call(self, method: str, params: list[Any] | None = None) -> QuorumResult[bytes]:
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        def fetch(endpoint: str) -> bytes:
            req = urllib.request.Request(
                endpoint,
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json", "User-Agent": "xion-os/quorum"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = resp.read()
            parsed = json.loads(body.decode("utf-8"))
            if "error" in parsed:
                raise QuorumFailedError(f"{endpoint}: JSON-RPC error {parsed['error']!r}")
            result = parsed.get("result")
            return json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")

        return require_quorum(list(self.endpoints), fetch, min_endpoints=3)


__all__ = ["MultiRpcMajorityReader"]
