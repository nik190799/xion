"""Deterministic contested-headroom spend arbitration."""

from __future__ import annotations

from dataclasses import dataclass

_DRIVE_RANK = {"survival": 0, "service": 1, "meaning": 2}


@dataclass(frozen=True)
class SpendProposal:
    proposal_seq: int
    proposal_id: str
    drive_term: str
    ladder_step_position: int
    reversibility_risk: int
    verifier_closure_value: int
    recurring_burn_ratio: float

    def sort_key(self) -> tuple[int, int, int, int, float, int]:
        return (
            _DRIVE_RANK.get(self.drive_term, 99),
            self.ladder_step_position,
            self.reversibility_risk,
            -self.verifier_closure_value,
            self.recurring_burn_ratio,
            self.proposal_seq,
        )


def arbitrate_contested_headroom(proposals: list[SpendProposal] | tuple[SpendProposal, ...]) -> SpendProposal:
    if not proposals:
        raise ValueError("at least one proposal is required")
    return sorted(proposals, key=lambda proposal: proposal.sort_key())[0]


__all__ = ["SpendProposal", "arbitrate_contested_headroom"]
