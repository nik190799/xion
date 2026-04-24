"""Cost-Pressure Response Ladder for Phase 6+ Velocity Hardening.

Implements the ladder doctrine from docs/21-SUSTAINABILITY.md:
- Provider-pricing watcher
- Threshold-trip handler that emits Tier-0 proposals
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("xion.sustainability.ladder")


@dataclass
class PriceSnapshot:
    provider: str
    model: str
    input_cpm: float  # cost per million tokens
    output_cpm: float
    timestamp: float


class CostPressureLadder:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.proposal_ledger = self.repo_root / "ledgers" / "PROPOSAL_LEDGER.jsonl"
        self.baseline_prices = {
            "openai": {"gpt-4": {"input_cpm": 30.0, "output_cpm": 60.0}},
            "anthropic": {"claude-3-opus": {"input_cpm": 15.0, "output_cpm": 75.0}},
        }

    def check_prices(self, current_prices: list[PriceSnapshot]) -> None:
        """Evaluate current prices against baseline and emit proposals if needed."""
        for snap in current_prices:
            baseline = self.baseline_prices.get(snap.provider, {}).get(snap.model)
            if not baseline:
                continue

            # If price drops by more than 20%, emit a Tier-0 proposal to switch or re-route
            if snap.input_cpm <= baseline["input_cpm"] * 0.8:
                self._emit_proposal(
                    title=f"Cost-Pressure: Route to {snap.model} due to price drop",
                    description=f"{snap.provider} {snap.model} input price dropped to {snap.input_cpm} CPM.",
                    tier=0,
                )

    def _emit_proposal(self, title: str, description: str, tier: int) -> None:
        """Write a proposal to PROPOSAL_LEDGER."""
        # Ensure directory exists
        self.proposal_ledger.parent.mkdir(parents=True, exist_ok=True)
        
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "description": description,
            "tier": tier,
            "status": "proposed",
            "source": "cost-pressure-ladder",
        }
        
        with self.proposal_ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
            
        logger.info(f"Emitted Tier-{tier} proposal: {title}")
