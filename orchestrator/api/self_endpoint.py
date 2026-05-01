"""GET /self — self-knowledge surface (Phase 6.4.b)."""

from __future__ import annotations

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from orchestrator.api.admission import admission_dependency
from orchestrator.api.models import SelfResponse
from orchestrator.runtime import default_worker_id
from orchestrator.sensorium.nervous_views import (
    GovernanceView,
    SensoriumView,
    TopographyView,
    VitalsView,
)
from orchestrator.sensorium.topography_emit import (
    build_api_surface,
    emit_topography_signals,
    ensure_mapping_hydration,
)

router = APIRouter()


@router.get("/self", response_model=SelfResponse)
def get_self(
    req: Request,
    principal_id: Annotated[str, Depends(admission_dependency)],
) -> dict[str, Any]:
    _ = principal_id
    worker_id = default_worker_id()
    bus = req.app.state.signal_bus
    ensure_mapping_hydration(bus)
    extras = emit_topography_signals(req.app, worker_id=worker_id)
    bus.publish(extras)

    sup = getattr(req.app.state, "supervisor", None)
    st = sup.latest_snapshot() if sup is not None else None

    api_surface = build_api_surface(req.app)
    body: dict[str, Any] = {
        "topography": {
            **TopographyView.from_bus(bus),
            "api_surface": api_surface,
        },
        "sensorium": SensoriumView.to_dict_from_bus(bus),
        "vitals": VitalsView.from_bus(bus, state=st),
        "governance": GovernanceView.from_bus(bus),
        "as_of_utc_ns": time.time_ns(),
    }
    SelfResponse.model_validate(body)
    return body
