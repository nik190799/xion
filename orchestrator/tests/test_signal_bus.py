"""Tests for :class:`~orchestrator.signals.bus.SignalBus` (Phase 6.4.b / Block K)."""

from __future__ import annotations

import asyncio

from orchestrator.sensorium.receptors._util import sense_signal
from orchestrator.signals.bus import SignalBus
from orchestrator.signals.schema import SignalSchema, register_kind


def test_publish_subscribe_latest_roundtrip():
    bus = SignalBus()
    s = sense_signal(
        kind="interoception.cost_pressure",
        receptor_id="t",
        value=0.25,
        methodology_hash="1" * 64,
    )
    got: list[str] = []

    async def _run() -> None:
        async def _sub() -> None:
            async for sig in bus.subscribe("interoception.*"):
                got.append(sig.kind)
                break

        task = asyncio.create_task(_sub())
        await asyncio.sleep(0.05)
        pub = bus.publish([s])
        assert len(pub) == 1
        await asyncio.wait_for(task, timeout=2.0)

    asyncio.run(_run())
    assert bus.latest("interoception.cost_pressure") is not None
    assert got == ["interoception.cost_pressure"]


def test_latest_by_category():
    bus = SignalBus()
    bus.publish(
        [
            sense_signal(
                kind="interoception.cost_pressure",
                receptor_id="a",
                value=0.1,
                methodology_hash="2" * 64,
            ),
            sense_signal(
                kind="chronoception.monotonic_drift_ns",
                receptor_id="b",
                value=0,
                methodology_hash="2" * 64,
            ),
        ]
    )
    inter = bus.latest_by_category("interoception")
    assert "interoception.cost_pressure" in inter
    assert "chronoception.monotonic_drift_ns" not in inter


def test_schema_drop_emits_bus_integrity():
    bad = sense_signal(
        kind="interoception.cost_pressure",
        receptor_id="x",
        value=50.0,
        methodology_hash="3" * 64,
    )
    bus = SignalBus()
    bus.publish([bad])
    assert bus.latest("interoception.cost_pressure") is None
    bi = bus.latest("vital.bus_integrity")
    assert bi is not None
    assert "drop" in str(bi.value).lower() or "drop" in str(bi.value)


def test_pluggability_register_kind_without_editing_bus():
    register_kind(SignalSchema("test.signal_bus.plug", "str", None, None, 1))
    bus = SignalBus()
    s = sense_signal(
        kind="test.signal_bus.plug",
        receptor_id="r",
        value="hello",
        methodology_hash="4" * 64,
    )
    bus.publish([s])
    assert bus.latest("test.signal_bus.plug") is not None
