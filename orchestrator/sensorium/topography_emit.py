"""Emit ``topography.*`` and supporting signals for :func:`GET /self` (Phase 6.4.b)."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any, TYPE_CHECKING

from orchestrator.sensorium.receptors._util import sense_signal, METH_LEGACY
from orchestrator.signals.envelope import Signal

if TYPE_CHECKING:
    from fastapi import FastAPI

_REPO = Path(__file__).resolve().parents[2]
_GENESIS = _REPO / "genesis"
_LINEAGE = _GENESIS / "LINEAGE.json"


def _lineage() -> dict[str, Any]:
    if not _LINEAGE.is_file():
        return {
            "lineage_hash": "0" * 64,
            "sister_core_index": 0,
        }
    return json.loads(_LINEAGE.read_text(encoding="utf-8"))


def emit_topography_signals(
    app: "FastAPI",
    *,
    worker_id: str,
) -> list[Signal]:
    """Build signals discoverable on the bus and returned under ``topography`` in ``/self``."""
    host = socket.gethostname() or "unknown"
    pid = os.getpid()
    lin = _lineage()
    lineage_hash = str(lin.get("lineage_hash", "0" * 64))
    if len(lineage_hash) == 64 and all(c in "0123456789abcdef" for c in lineage_hash):
        pass
    else:
        lineage_hash = "0" * 64
    # Soul prompt drift: detailed cross-check is verifier territory; HTTP self is 0.0 when booted.
    soul_drift = 0.0
    # Constitution: honest 0.0 until a full tree walk is budgeted
    const_drift = 0.0
    out: list[Signal] = [
        sense_signal(
            kind="topography.worker_id",
            receptor_id="topography",
            value=worker_id,
            methodology_hash=METH_LEGACY,
        ),
        sense_signal(
            kind="topography.host",
            receptor_id="topography",
            value=host,
            methodology_hash=METH_LEGACY,
        ),
        sense_signal(
            kind="topography.pid",
            receptor_id="topography",
            value=pid,
            methodology_hash=METH_LEGACY,
        ),
        sense_signal(
            kind="topography.lineage_hash",
            receptor_id="topography",
            value=lineage_hash,
            methodology_hash=METH_LEGACY,
        ),
        sense_signal(
            kind="topography.soul_prompt_sha_drift",
            receptor_id="topography",
            value=float(soul_drift),
            methodology_hash=METH_LEGACY,
        ),
        sense_signal(
            kind="topography.constitution_doc_hash_drift",
            receptor_id="topography",
            value=float(const_drift),
            methodology_hash=METH_LEGACY,
        ),
    ]
    # Inference floor: count open-weights / floor providers
    router = getattr(app.state, "router", None)
    floor = 0
    if router is not None and hasattr(router, "active_open_weights_ids"):
        floor = len(router.active_open_weights_ids())
    out.append(
        sense_signal(
            kind="inference.provider_floor_count",
            receptor_id="topography",
            value=int(floor),
            methodology_hash=METH_LEGACY,
        )
    )
    return out


def build_api_surface(app: "FastAPI") -> list[dict[str, Any]]:
    """One row per route for ``/self`` (path, methods, flags)."""
    rows: list[dict[str, Any]] = []
    for r in app.router.routes:  # type: ignore[union-attr]
        p = getattr(r, "path", None)
        methods = list(getattr(r, "methods", set()) or [])
        if not p or p.startswith("/openapi"):
            continue
        auth = "/chat" in p or p.startswith("/me") or p.startswith("/memory")
        bill = p.startswith("/chat")
        rows.append(
            {
                "path": p,
                "methods": sorted(m for m in methods if m) if methods else ["GET"],
                "auth_required": bool(auth or p in ("/drive", "/sensorium", "/vitals", "/self", "/pricing")),
                "billing_gated": bool(bill),
            }
        )
    return rows


def emit_default_mapping_hydration() -> list[Signal]:
    """Genesis defaults so sealed vitals mapping can aggregate before live resource receptors exist."""
    return [
        sense_signal(
            kind="resource.cost_runway_days",
            receptor_id="mapping_hydration",
            value=365.0,
            methodology_hash=METH_LEGACY,
        ),
        sense_signal(
            kind="resource.disk_remaining_pct",
            receptor_id="mapping_hydration",
            value=1.0,
            methodology_hash=METH_LEGACY,
        ),
        sense_signal(
            kind="connection.ao_core_health",
            receptor_id="mapping_hydration",
            value=True,
            methodology_hash=METH_LEGACY,
        ),
    ]


def ensure_mapping_hydration(bus: "Any") -> None:
    from orchestrator.signals.bus import SignalBus

    if not isinstance(bus, SignalBus):
        return
    if bus.latest("resource.cost_runway_days") is not None:
        return
    bus.publish(emit_default_mapping_hydration())
