"""Treasury top-up actions (Phase 6.9)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class TopUpRequest:
    provider_id: str
    amount_tao: float
    payment_address: str
    reason: str
    runway_inference_credits_days: float | None


@dataclass(frozen=True)
class SpendProposal:
    action_id: str
    provider_id: str
    amount_tao: float
    destination_address: str
    approver_class_required: Literal["operator_multisig", "xion_hotkey_inside_cap"]
    unsigned_extrinsic: str
    created_utc_ns: int
    reason: str


class ChutesTopUp:
    """Compose a TAO transfer proposal to the Chutes payment address.

    This class does not sign or broadcast. At S1, the returned proposal
    is an operator co-sign artifact. S3+ auto-top-up uses the same shape
    under a posture-gated cap, but remains NOT_YET_SEALED in Phase 6.9.
    """

    provider_id = "chutes"

    def propose(
        self,
        request: TopUpRequest,
        *,
        active_spend_posture: str = "S1_operator_all",
    ) -> SpendProposal:
        if request.provider_id != self.provider_id:
            raise ValueError("ChutesTopUp only handles provider_id='chutes'")
        if request.amount_tao <= 0:
            raise ValueError("amount_tao must be positive")
        if not request.payment_address:
            raise ValueError("payment_address must be non-empty")
        approver: Literal["operator_multisig", "xion_hotkey_inside_cap"]
        if active_spend_posture in {"S1_operator_all", "S2_operator_strategic"}:
            approver = "operator_multisig"
        else:
            approver = "xion_hotkey_inside_cap"
        payload = {
            "chain": "bittensor",
            "method": "balances.transfer_allow_death",
            "destination": request.payment_address,
            "amount_tao": request.amount_tao,
            "provider_id": request.provider_id,
            "reason": request.reason,
        }
        return SpendProposal(
            action_id=f"chutes-topup:{int(time.time())}",
            provider_id=request.provider_id,
            amount_tao=request.amount_tao,
            destination_address=request.payment_address,
            approver_class_required=approver,
            unsigned_extrinsic=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            created_utc_ns=time.time_ns(),
            reason=request.reason,
        )


__all__ = ["ChutesTopUp", "SpendProposal", "TopUpRequest"]
