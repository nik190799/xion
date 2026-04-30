"""Operator-only governance/state-actor intake route."""

from __future__ import annotations

import os
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from orchestrator.api.admission import admission_dependency
from orchestrator.governance import append_governance_row, default_ledger_path

router = APIRouter()


class StateActorIntake(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_class: Literal["A", "B", "C", "D"]
    state_actor_identifier: str
    jurisdiction: str
    demand_summary_hash: str
    demand_artifact_uri: str
    covenant_principles_touched: list[str] = []
    invariants_touched: list[str] = []
    response_category: Literal["comply", "refuse", "escalate-pending", "comply-with-disclosure"]
    response_artifact_uri: str
    user_notification: str
    linked_safety_ledger_seq: int | None = None
    date: str


def _operator_principal() -> str:
    return os.environ.get("XION_GOVERNANCE_OPERATOR_PRINCIPAL", "operator").strip() or "operator"


@router.post("/governance/state-actor")
def post_state_actor(
    body: StateActorIntake,
    principal_id: Annotated[str, Depends(admission_dependency)],
) -> dict[str, object]:
    """Append a state-actor interaction row to GOVERNANCE_LEDGER."""

    if principal_id != _operator_principal():
        raise HTTPException(status_code=403, detail="operator principal required")
    row = append_governance_row(
        default_ledger_path(),
        interaction_class=body.interaction_class,
        state_actor_identifier=body.state_actor_identifier,
        jurisdiction=body.jurisdiction,
        demand_summary_hash=body.demand_summary_hash,
        demand_artifact_uri=body.demand_artifact_uri,
        covenant_principles_touched=body.covenant_principles_touched,
        invariants_touched=body.invariants_touched,
        response_category=body.response_category,
        response_artifact_uri=body.response_artifact_uri,
        user_notification=body.user_notification,
        linked_safety_ledger_seq=body.linked_safety_ledger_seq,
        date=body.date,
    )
    return {"status": "appended", "seq": row["seq"], "this_hash": row["this_hash"]}


__all__ = ["StateActorIntake", "router"]
