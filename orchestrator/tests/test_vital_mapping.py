"""Vital domain sealing via :mod:`orchestrator.vitals.mapping` (Block P)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import orchestrator.vitals.mapping as mapping_mod
from orchestrator.sensorium.receptors._util import sense_signal
from orchestrator.signals.bus import SignalBus
from orchestrator.vitals import get_composite_vitals
from orchestrator.vitals.mapping import (
    VITAL_MAPPING,
    VITAL_MAPPING_METHODOLOGY_SHA256,
    aggregate_domain,
)


def test_methodology_hash_tracks_file_bytes() -> None:
    p = Path(mapping_mod.__file__).resolve()
    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    assert expected == VITAL_MAPPING_METHODOLOGY_SHA256


def test_sealed_domains_aggregate_from_synthetic_bus() -> None:
    bus = SignalBus()
    bus.publish(
        [
            sense_signal(
                kind="interoception.cost_pressure",
                receptor_id="a",
                value=0.0,
                methodology_hash="1" * 64,
            ),
            sense_signal(
                kind="resource.cost_runway_days",
                receptor_id="a",
                value=400.0,
                methodology_hash="1" * 64,
            ),
            sense_signal(
                kind="proprioception.relay_health",
                receptor_id="a",
                value=True,
                methodology_hash="1" * 64,
            ),
            sense_signal(
                kind="proprioception.arbiter_health",
                receptor_id="a",
                value=True,
                methodology_hash="1" * 64,
            ),
            sense_signal(
                kind="connection.ao_core_health",
                receptor_id="a",
                value=True,
                methodology_hash="1" * 64,
            ),
            sense_signal(
                kind="resource.disk_remaining_pct",
                receptor_id="a",
                value=1.0,
                methodology_hash="1" * 64,
            ),
            sense_signal(
                kind="topography.soul_prompt_sha_drift",
                receptor_id="a",
                value=0.0,
                methodology_hash="1" * 64,
            ),
            sense_signal(
                kind="chronoception.time_in_degraded_mode_s",
                receptor_id="a",
                value=0.0,
                methodology_hash="1" * 64,
            ),
            sense_signal(
                kind="topography.constitution_doc_hash_drift",
                receptor_id="a",
                value=0.0,
                methodology_hash="1" * 64,
            ),
        ]
    )
    fin = aggregate_domain("Financial Vitality", bus)
    sub = aggregate_domain("Substrate Vitality", bus)
    con = aggregate_domain("Constitutional Integrity", bus)
    assert fin is not None
    assert sub is not None
    assert con is not None
    assert fin[1] in ("healthy", "warning", "critical")


def test_not_yet_sealed_domains_honest_in_mapping() -> None:
    nys = {n for n, s in VITAL_MAPPING.items() if s == "not_yet_sealed"}
    assert nys == {
        "Behavioral Fidelity",
        "Relational Trust",
        "Service Usefulness",
        "Evolutionary Health",
        "Structural Decentralization",
    }


def test_get_composite_includes_eight_domains() -> None:
    bus = SignalBus()
    d = [x.name for x in get_composite_vitals(bus=bus)]
    assert len(d) == 8
