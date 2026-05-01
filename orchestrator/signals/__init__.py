"""Nervous System v2 — typed signals, schema registry, and SignalBus (Phase 6.4.b)."""

from orchestrator.signals.bus import SignalBus
from orchestrator.signals.effector import Effector, EffectorRegistry
from orchestrator.signals.envelope import Signal
from orchestrator.signals.receptor import Receptor, ReceptorContext, ReceptorRegistry
from orchestrator.signals.reflex import ReflexArc, ReflexRegistry
from orchestrator.signals.schema import (
    REGISTRY,
    SignalSchema,
    SignalSchemaError,
    register_kind,
    validate_signal,
)

__all__ = [
    "REGISTRY",
    "Effector",
    "EffectorRegistry",
    "Receptor",
    "ReceptorContext",
    "ReceptorRegistry",
    "ReflexArc",
    "ReflexRegistry",
    "Signal",
    "SignalBus",
    "SignalSchema",
    "SignalSchemaError",
    "register_kind",
    "validate_signal",
]
