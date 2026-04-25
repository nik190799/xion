"""``xion-verify nervous-system`` — modularity invariants (Phase 6.4.b)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


def verify_nervous_system(repo_root: Path, stdout: TextIO) -> int:
    """Programmatic checks for modularity invariants (pluggability, independence, etc.)."""
    try:
        root = find_repo_root(repo_root)
    except RepoRootNotFound as e:
        click.echo(f"nervous-system: FAIL: {e}", err=True)
        return FAIL
    rroot = str(root.resolve())
    if rroot not in sys.path:
        sys.path.insert(0, rroot)

    from orchestrator.sensorium import (
        Chronoception,
        DistressSignal,
        Interoception,
        Proprioception,
        SensoriumState,
    )
    from orchestrator.sensorium.receptors._util import sense_signal
    from orchestrator.sensorium.receptors.interoception import InteroceptionCostPressure
    from orchestrator.signals.bus import SignalBus
    from orchestrator.signals.effector import EffectorRegistry
    from orchestrator.signals.receptor import ReceptorContext
    from orchestrator.signals.reflex import ReflexArc, ReflexRegistry
    from orchestrator.signals.schema import SignalSchema, register_kind

    # 1 Pluggability: new kind without editing bus
    register_kind(SignalSchema("test.nervous.plug", "float", 0.0, 1.0, 1))
    bus = SignalBus()
    s = sense_signal(
        kind="test.nervous.plug",
        receptor_id="inv_test",
        value=0.5,
        methodology_hash="0" * 64,
    )
    bus.publish([s])
    if bus.latest("test.nervous.plug") is None:
        click.echo("nervous-system: FAIL: pluggability (publish)", file=stdout)
        return FAIL

    # 2 Independence: receptor failure path
    bus2 = SignalBus()
    bus2.report_receptor_failure("fake", RuntimeError("boom"))
    if not bus2.receptor_error_log:
        click.echo("nervous-system: FAIL: independence (degraded log)", file=stdout)
        return FAIL

    # 8 Drop visibility: invalid value for cost_pressure
    bad = sense_signal(
        kind="interoception.cost_pressure",
        receptor_id="x",
        value=99.0,
        methodology_hash="0" * 64,
    )
    b3 = SignalBus()
    b3.publish([bad])
    if b3.latest("interoception.cost_pressure") is not None:
        click.echo("nervous-system: FAIL: schema fail-closed drop", file=stdout)
        return FAIL
    if b3.latest("vital.bus_integrity") is None:
        click.echo("nervous-system: FAIL: drop visibility (bus_integrity)", file=stdout)
        return FAIL

    # Reflex synchrony (dispatch before async subscribers)
    seen: list[str] = []

    def _on_reflex(_a, sig) -> None:  # type: ignore[no-untyped-def]
        seen.append(sig.kind)

    eff = EffectorRegistry()
    eff.register_reflex_handler(_on_reflex)
    rr = ReflexRegistry()
    rr.bind_effectors(eff)
    rr.register(
        ReflexArc(
            arc_id="t",
            trigger_kind_pattern="test.nervous.plug",
            predicate=lambda _x: True,
            effector_id="e",
            methodology_hash="0" * 64,
        )
    )
    b4 = SignalBus(reflex_registry=rr)
    b4.publish(
        [
            sense_signal(
                kind="test.nervous.plug",
                receptor_id="r",
                value=0.1,
                methodology_hash="0" * 64,
            )
        ]
    )
    if "test.nervous.plug" not in seen:
        click.echo("nervous-system: FAIL: reflex dispatch", file=stdout)
        return FAIL

    st = SensoriumState(
        interoception=Interoception.from_placeholders(treasury_stress=0.0, cost_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(0.0, "textual"),
    )
    ctx = ReceptorContext(state=st)
    sigs = InteroceptionCostPressure().tick(ctx)
    if not sigs:
        click.echo("nervous-system: FAIL: dual-publish receptor", file=stdout)
        return FAIL

    click.echo(
        "nervous-system: OK (pluggability, independence, schema drop, reflex, dual-publish)",
        file=stdout,
    )
    return OK


@click.command("nervous-system")
def nervous_system_cli() -> None:
    from sys import stdout

    from xion_verify.exit_codes import exit_code_to_system_exit

    c = Path.cwd()
    try:
        root = find_repo_root(c)
    except RepoRootNotFound:
        click.echo("nervous-system: FAIL: not inside a xion git checkout", err=True)
        raise SystemExit(1) from None
    raise SystemExit(exit_code_to_system_exit(verify_nervous_system(root, stdout)))
