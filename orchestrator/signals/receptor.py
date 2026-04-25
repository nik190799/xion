from __future__ import annotations

import importlib
import inspect
import pkgutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from orchestrator.sensorium.sensorium import SensoriumState
from orchestrator.signals.envelope import Signal


@dataclass
class ReceptorContext:
    """Context passed to each receptor on tick."""

    state: SensoriumState
    extra: dict[str, Any] | None = None


@runtime_checkable
class Receptor(Protocol):
    receptor_id: str
    signal_kinds: frozenset[str]
    cadence_hint_s: float
    methodology_hash: str

    def tick(self, ctx: ReceptorContext) -> list[Signal]: ...


def _import_submodules(package_name: str) -> None:
    try:
        pkg = importlib.import_module(package_name)
    except ImportError:
        return
    if not hasattr(pkg, "__path__"):
        return
    for _finder, name, ispkg in pkgutil.walk_packages(
        pkg.__path__,  # type: ignore[attr-defined]
        prefix=package_name + ".",
    ):
        if ispkg or name.rsplit(".", 1)[-1].startswith("_"):
            continue
        try:
            importlib.import_module(name)
        except Exception:  # noqa: BLE001
            continue


def discover_receptors(repo_root: Path | None = None) -> list[type[Receptor]]:
    """Import every module under `orchestrator.sensorium.receptors` and
    return concrete Receptor class types.
    """
    if repo_root is not None and str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    _import_submodules("orchestrator.sensorium.receptors")
    out: list[type[Receptor]] = []
    for mod_name, mod in list(sys.modules.items()):
        if not mod_name.startswith("orchestrator.sensorium.receptors."):
            continue
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if obj is Receptor or obj is Protocol:
                continue
            if not hasattr(obj, "receptor_id"):
                continue
            if "Protocol" in getattr(obj, "__name__", ""):
                continue
            if inspect.isabstract(obj):
                continue
            # Protocol structural check: has tick
            if not hasattr(obj, "tick"):
                continue
            out.append(obj)  # type: ignore[arg-type]
    return out


class ReceptorRegistry:
    def __init__(self, classes: list[type[Receptor]] | None = None) -> None:
        self._classes = classes
        if self._classes is None:
            self._classes = [c for c in discover_receptors() if c not in (Receptor,)]
        self._instances: list[Receptor] = [cls() for cls in self._classes]  # type: ignore[misc]

    def instances(self) -> list[Receptor]:
        return list(self._instances)
