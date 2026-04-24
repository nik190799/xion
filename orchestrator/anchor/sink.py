"""AnchorSink ABC for submitting anchor records.

Mirroring the `orchestrator/safety/anchor.py` pattern from Phase 4b, this
abstracts where anchor records actually go. In Phase 6.3, they only go to
the local ledger. In Phase 6.3.b, they will also post to AO Core.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from orchestrator.anchor.ledger import AnchorRecord, append


@dataclass(frozen=True)
class AnchorReceipt:
    """What the sink gives back."""
    kind: Literal["local_only", "ao_core"]
    ao_message_id: str | None = None


class AnchorSink(ABC):
    """Abstract destination for an AnchorRecord."""
    
    @abstractmethod
    def submit(
        self,
        period_start_unix: int,
        period_end_unix: int,
        ledger_kind: str,
        batch_root_sha256: str,
        batch_size: int,
        leaf_correlation_ids: list[str],
    ) -> AnchorReceipt:
        """Publishes the anchor batch and writes the ANCHOR_LEDGER row.
        
        The implementation MUST call `ledger.append` and return the receipt.
        """
        pass


class LocalLedgerSink(AnchorSink):
    """Phase 6.3 sink: writes to ANCHOR_LEDGER locally, no network."""
    
    def __init__(self, ledger_path: str):
        self.ledger_path = ledger_path

    def submit(
        self,
        period_start_unix: int,
        period_end_unix: int,
        ledger_kind: str,
        batch_root_sha256: str,
        batch_size: int,
        leaf_correlation_ids: list[str],
    ) -> AnchorReceipt:
        append(
            path=self.ledger_path,
            period_start_unix=period_start_unix,
            period_end_unix=period_end_unix,
            ledger_kind=ledger_kind,
            batch_root_sha256=batch_root_sha256,
            batch_size=batch_size,
            leaf_correlation_ids=leaf_correlation_ids,
            ao_message_id=None,
        )
        return AnchorReceipt(kind="local_only")
