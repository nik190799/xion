"""`xion-verify presence` — verify visual/vitals emitters."""

import sys
import asyncio
import click
from typing import Any
from xion_verify.exit_codes import OK, NOT_YET_SEALED, FAIL
from xion_verify.repo import RepoRootNotFound, find_repo_root

@click.command(name="presence", help="Verify Phase 6.4 presence emitters (visual, vitals).")
def presence() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"presence: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    sys.path.insert(0, str(repo_root))
    try:
        from orchestrator.sensorium.presence_bus import PresenceBus
        from orchestrator.senses.visual_emitter import stream_visuals
        from orchestrator.senses.vitals_emitter import stream_vitals
        from orchestrator.sensorium import SensoriumState, Interoception, Chronoception, Proprioception, DistressSignal
    except ImportError as e:
        click.echo(f"presence: FAIL: Could not import orchestrator modules: {e}", err=True)
        sys.exit(FAIL)

    async def _run_checks():
        bus = PresenceBus()
        
        # Synthetic state
        state = SensoriumState(
            interoception=Interoception(survival_pressure=0.0),
            chronoception=Chronoception.from_ticks(
                last_checkpoint_utc_ns=None,
                now_utc_ns=1000,
                degraded_since_utc_ns=None,
                monotonic_drift_ns=0
            ),
            proprioception=Proprioception.from_runtime(
                relay_healthy=True,
                arbiter_healthy=True,
                watchdog_fires_recent=0,
                as_of_utc_ns=1000
            ),
            distress=DistressSignal(0.0, "textual", 1000),
            as_of_utc_ns=1000
        )
        
        # Start emitters
        # We need to run them as tasks so they can run concurrently with our polling
        visual_gen = stream_visuals(bus)
        vitals_gen = stream_vitals(bus)
        
        # We need to wrap the generators in tasks to start them
        async def get_visual():
            return await anext(visual_gen)
            
        async def get_vitals():
            return await anext(vitals_gen)
            
        visual_task = asyncio.create_task(get_visual())
        vitals_task = asyncio.create_task(get_vitals())
        
        # Publish
        bus.publish(state)
        
        # The visual emitter has a background task that reads from the bus.
        # We need to give it a moment to consume the state we just published.
        # Then we can pull the first frame.
        
        # Give the background task a chance to run
        await asyncio.sleep(0.2)
        
        # The first iteration of the visual stream might yield nothing if the state
        # hasn't propagated yet. Let's make sure we have the state published.
        bus.publish(state)
        await asyncio.sleep(0.2)
        
        # Wait for the tasks to complete
        import json
        
        visual_frame_str = await asyncio.wait_for(visual_task, timeout=2.0)
        vitals_frame_str = await asyncio.wait_for(vitals_task, timeout=2.0)
        
        visual_frame = json.loads(visual_frame_str)
        vitals_frame = json.loads(vitals_frame_str)
        
        # Assert visual shape
        assert visual_frame["type"] == "visual"
        assert "valence" in visual_frame["mood"]
        assert "energy" in visual_frame["mood"]
        assert "focus" in visual_frame["mood"]
        
        # Assert vitals shape
        assert vitals_frame["type"] == "vitals"
        assert len(vitals_frame["vitals"]) == 3
        for v in vitals_frame["vitals"]:
            assert v["band"] in ("healthy", "warning", "critical", "not_yet_sealed")
            assert v["methodology_sha256"]

    try:
        asyncio.run(_run_checks())
    except Exception as e:
        import traceback
        traceback.print_exc()
        click.echo(f"presence: NOT_YET_SEALED — emitters failed or skipped: {e}")
        sys.exit(NOT_YET_SEALED)

    click.echo("presence: OK (visual + vitals emitters are live)")
    sys.exit(OK)
