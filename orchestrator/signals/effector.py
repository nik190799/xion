from __future__ import annotations

import importlib
import inspect
import os
import pkgutil
import sys
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from orchestrator.signals.bus import SignalBus
    from orchestrator.signals.reflex import ReflexArc, ReflexRegistry

from orchestrator.signals.envelope import Signal


@runtime_checkable
class Effector(Protocol):
    effector_id: str
    consumed_kinds: frozenset[str]
    output_channel: str
    def run(self, bus: "SignalBus") -> AsyncIterator[bytes]: ...  # noqa: E704


@dataclass
class _ReflexState:
    last_consent: dict[str, bool] | None = None
    on_off_channel: Callable[[], None] | None = None


class EffectorRegistry:
    def __init__(self) -> None:
        self._on_reflex_handlers: list[Callable[["ReflexArc", Signal], None]] = []
        self._reflex_state = _ReflexState()

    def on_reflex(self, arc: "ReflexArc", signal: Signal) -> None:
        for h in self._on_reflex_handlers:
            h(arc, signal)

    def register_reflex_handler(self, fn: Callable[["ReflexArc", Signal], None]) -> None:
        self._on_reflex_handlers.append(fn)

    def set_off_channel_hook(self, fn: Callable[[], None] | None) -> None:
        self._reflex_state.on_off_channel = fn


def discover_effectors(repo_root: Path | None = None) -> list[type[Effector]]:
    if repo_root is not None and str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    base = "orchestrator.senses.effectors"
    try:
        pkg = importlib.import_module(base)
    except ImportError:
        return []
    out: list[type[Effector]] = []
    for m in pkgutil.iter_modules(
        [str(Path(pkg.__file__).parent)],  # type: ignore[arg-type]
    ):
        if m.ispkg and m.name not in ("__pycache__",):
            try:
                importlib.import_module(f"{base}.{m.name}")
            except Exception:  # noqa: BLE001
                continue
    for mod_name, mod in list(sys.modules.items()):
        if not mod_name.startswith("orchestrator.senses.effectors."):
            continue
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if not hasattr(obj, "effector_id") or not hasattr(obj, "run"):
                continue
            if "Protocol" in getattr(obj, "__name__", ""):
                continue
            out.append(obj)  # type: ignore[arg-type]
    return out
