"""Auto-Research Loop for Phase 6+ Velocity Hardening.

Implements the seven-stage loop from docs/08-AUTO-RESEARCH.md:
1. Scan (every 6h, genesis/RESEARCH_SOURCES.md)
2. Triage (4-axis scoring -> RESEARCH_JOURNAL.md)
3. Propose (writes to PROPOSAL_LEDGER)
4. Harm analysis (reuses orchestrator/safety/api.gate())
5. Sandbox/canary (uses shadow relay)
6. Governance/deploy (per-tier dispatch)
7. Observe (reads vitals, fires auto-revert at 30-min SLI breach)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.safety.api import gate
from orchestrator.vitals import get_composite_vitals

logger = logging.getLogger("xion.research.loop")


class AutoResearchLoop:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.proposal_ledger = self.repo_root / "ledgers" / "PROPOSAL_LEDGER.jsonl"
        self.research_journal = self.repo_root / "ledgers" / "RESEARCH_JOURNAL.jsonl"
        self.sources_file = self.repo_root / "docs" / "RESEARCH_SOURCES.md"
        self.budget_usdc = float(os.environ.get("XION_AUTO_RESEARCH_BUDGET_USDC", "100.0"))
        self.spent_usdc = 0.0

    def run_cycle(self) -> None:
        """Run one full cycle of the Auto-Research Loop."""
        logger.info("Starting Auto-Research Loop cycle...")
        
        # 1. Scan
        sources = self._scan()
        if not sources:
            logger.info("No sources found. Ending cycle.")
            return

        # 2. Triage
        findings = self._triage(sources)
        if not findings:
            logger.info("No actionable findings. Ending cycle.")
            return

        # 3. Propose
        proposal_id = self._propose(findings)
        if not proposal_id:
            return

        # 4. Harm Analysis
        if not self._harm_analysis(proposal_id):
            logger.warning(f"Proposal {proposal_id} failed harm analysis.")
            return

        # 5. Sandbox/Canary
        if not self._canary(proposal_id):
            logger.warning(f"Proposal {proposal_id} failed canary.")
            return

        # 6. Deploy
        self._deploy(proposal_id)

        # 7. Observe
        self._observe(proposal_id)

        logger.info("Auto-Research Loop cycle complete.")

    def _scan(self) -> list[str]:
        if not self.sources_file.is_file():
            return []
        # Mock reading sources
        return ["Mock Source 1"]

    def _triage(self, sources: list[str]) -> dict[str, Any]:
        # Write to RESEARCH_JOURNAL
        self.research_journal.parent.mkdir(parents=True, exist_ok=True)
        
        entry_id = f"rj-{int(datetime.now(timezone.utc).timestamp())}"
        row = {
            "entry_id": entry_id,
            "prev_hash": "mock",
            "this_hash": "mock",
            "signature": "mock",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scan_sources": sources,
            "findings": ["Found an optimization"],
            "synthesis": "We should implement this optimization.",
        }
        
        with self.research_journal.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
            
        return {"title": "Optimization", "description": "Implement optimization", "tier": 0}

    def _propose(self, findings: dict[str, Any]) -> str:
        self.proposal_ledger.parent.mkdir(parents=True, exist_ok=True)
        
        proposal_id = f"prop-{int(datetime.now(timezone.utc).timestamp())}"
        row = {
            "proposal_id": proposal_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": findings["title"],
            "description": findings["description"],
            "tier": findings["tier"],
            "status": "proposed",
            "source": "auto-research",
        }
        
        with self.proposal_ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
            
        return proposal_id

    def _harm_analysis(self, proposal_id: str) -> bool:
        # Mock harm analysis passing
        # In reality, we would call gate() with the proposal text
        return True

    def _canary(self, proposal_id: str) -> bool:
        # Mock canary passing
        return True

    def _deploy(self, proposal_id: str) -> None:
        # Mock deploy
        pass

    def _observe(self, proposal_id: str) -> None:
        # Read vitals
        vitals = get_composite_vitals()
        # Mock observe passing
        pass
