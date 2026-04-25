"""Nervous System v2 — typed signals, schema registry, and SignalBus (Phase 6.4.b)."""

from orchestrator.signals.envelope import Signal
from orchestrator.signals.bus import SignalBus
from orchestrator.signals.schema import (
    REGISTRY,
    SignalSchema,
    SignalSchemaError,
    register_kind,
    validate_signal,
)
from orchestrator.signals.receptor import Receptor, ReceptorContext, ReceptorRegistry
from orchestrator.signals.effector import Effector, EffectorRegistry
from orchestrator.signals.reflex import ReflexArc, ReflexRegistry

__all__ = [
    "Effector",
    "EffectorRegistry",
    "Receptor",
    "ReceptorContext",
    "ReceptorRegistry",
    "ReflexArc",
    "ReflexRegistry",
    "REGISTRY",
    "Signal",
    "SignalBus",
    "SignalSchema",
    "SignalSchemaError",
    "register_kind",
    "validate_signal",
]
