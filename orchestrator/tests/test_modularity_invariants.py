"""Eight modularity invariants (Phase 6.4.b doctrine) — programmatic checks."""

from __future__ import annotations

import ast
from pathlib import Path

from orchestrator.relay import Relay
from orchestrator.sensorium.ledger import append_tick_commit, verify_chain
from orchestrator.sensorium.receptors._util import sense_signal
from orchestrator.signals.bus import SignalBus
from orchestrator.signals.receptor import ReceptorRegistry
from orchestrator.signals.schema import SignalSchema, register_kind
from orchestrator.supervisor import Supervisor


def _relay(tmp_path: Path) -> Relay:
    from orchestrator.safety import ledger as safety_ledger
    from orchestrator.safety.types import Decision, Verdict

    def _ok_gate(candidate: str, **kw) -> Verdict:  # type: ignore[no-untyped-def]
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="ok",
        )

    return Relay(
        relay_id="relay-inv-test",
        safety_ledger_path=tmp_path / "SAFETY.jsonl",
        request_ledger_path=tmp_path / "REQ.jsonl",
        sensorium_ledger_path=tmp_path / "SENSORIUM.jsonl",
        gate_fn=_ok_gate,
    )


def test_inv1_pluggability_new_kind():
    register_kind(SignalSchema("test.inv.plug", "float", 0.0, 1.0, 1))
    bus = SignalBus()
    s = sense_signal(
        kind="test.inv.plug", receptor_id="r", value=0.2, methodology_hash="a" * 64
    )
    assert bus.publish([s])
    assert bus.latest("test.inv.plug") is not None


def test_inv2_independence_receptor_failure_logged():
    bus = SignalBus()
    bus.report_receptor_failure("r1", ValueError("x"))
    assert any("r1" in e for e in bus.receptor_error_log)


def test_inv3_provenance_fields_on_signal():
    s = sense_signal(
        kind="interoception.cost_pressure",
        receptor_id="rid",
        value=0.3,
        methodology_hash="b" * 64,
    )
    for k in (
        "kind",
        "source",
        "value",
        "timestamp_utc_ns",
        "methodology_hash",
        "confidence",
        "schema_version",
    ):
        assert getattr(s, k) is not None or k == "value"


def test_inv4_ledger_accepts_signal_payload(tmp_path: Path):
    led = tmp_path / "CHAIN.jsonl"
    st = Supervisor(
        relay=_relay(tmp_path), sensorium_ledger_path=led, tick_cadence_s=0.1
    ).tick_once()
    sigs = [
        sense_signal(
            kind="interoception.cost_pressure",
            receptor_id="t",
            value=float(st.interoception.cost_pressure),
            methodology_hash="c" * 64,
        )
    ]
    row = append_tick_commit(
        led,
        state=st,
        relay_id="r",
        signals=[x.to_dict() for x in sigs],
    )
    assert row.get("signals")
    n, _tip = verify_chain(led)
    assert n >= 1


def test_inv5_receptor_registry_discovers_modules():
    reg = ReceptorRegistry()
    ids = {x.receptor_id for x in reg.instances()}
    assert len(ids) >= 1


def test_inv6_sensorium_view_shape_from_bus():
    from orchestrator.sensorium.nervous_views import SensoriumView

    bus = SignalBus()
    bus.publish(
        [
            sense_signal(
                kind="interoception.cost_pressure",
                receptor_id="z",
                value=0.4,
                methodology_hash="d" * 64,
            )
        ]
    )
    d = SensoriumView.from_bus(bus)
    assert "interoception" in d
    assert "cost_pressure" in d["interoception"]


def test_inv7_schema_version_on_envelope():
    s = sense_signal(
        kind="interoception.cost_pressure",
        receptor_id="z",
        value=0.1,
        methodology_hash="e" * 64,
    )
    assert s.schema_version == 1


def test_inv8_drop_not_silent():
    bus = SignalBus()
    bad = sense_signal(
        kind="interoception.cost_pressure",
        receptor_id="z",
        value=9.0,
        methodology_hash="f" * 64,
    )
    bus.publish([bad])
    assert bus.latest("vital.bus_integrity") is not None


def test_gateway_provider_modules_match_protocol_shape():
    """Provider modules expose the minimum Gateway Pattern surface.

    This is intentionally static and no-network. Runtime conformance belongs to
    `xion-verify gateway-conformance`; this guard prevents obvious drift such as
    adding a provider without `provider_id` or the gateway's required methods.
    """

    repo = Path(__file__).resolve().parents[2]
    checks = {
        "orchestrator/inference_router/providers": {
            "attrs": {"provider_id", "category"},
            "methods": {"health", "generate"},
        },
        "orchestrator/billing/providers": {
            "attrs": {"provider_id"},
            "methods": {"balance", "recent_payments", "forecast_runway"},
        },
        "orchestrator/embeddings/providers": {
            "attrs": {"provider_id", "model_id"},
            "methods": {"health", "embed"},
        },
        "orchestrator/safety/providers": {
            "attrs": {"provider_id", "model_id", "provider_version"},
            "methods": {"enabled", "judge"},
        },
        "orchestrator/voice_router/providers": {
            "attrs": {"provider_id", "category"},
            "methods": {"health"},
        },
    }

    failures: list[str] = []
    for provider_dir, requirements in checks.items():
        for path in sorted((repo / provider_dir).glob("*.py")):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            concrete_classes = [
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef)
                and not node.name.endswith("Error")
                and not node.name.endswith("Exception")
            ]
            if not concrete_classes:
                failures.append(f"{path}: no concrete provider class")
                continue

            if not any(
                _class_satisfies_gateway_shape(
                    cls,
                    attrs=requirements["attrs"],
                    methods=requirements["methods"],
                )
                for cls in concrete_classes
            ):
                failures.append(
                    f"{path}: no class exposes attrs={sorted(requirements['attrs'])} "
                    f"methods={sorted(requirements['methods'])}"
                )

    assert not failures, "\n".join(failures)


def _class_satisfies_gateway_shape(
    cls: ast.ClassDef,
    *,
    attrs: set[str],
    methods: set[str],
) -> bool:
    names = {
        node.target.id
        for node in cls.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    names.update(
        node.targets[0].id
        for node in cls.body
        if isinstance(node, ast.Assign)
        and node.targets
        and isinstance(node.targets[0], ast.Name)
    )
    names.update(
        node.name
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return attrs.issubset(names) and methods.issubset(names)
