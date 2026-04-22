"""Inference Router (Phase 5 minimal implementation).

`docs/18-VOLITION.md` and Invariant 17 in `genesis/INVARIANTS.md` are the
doctrine anchors. This module is deliberately small: it registers a
category taxonomy, loads the floor manifest, and enforces
`bootstrap()` — the property that Xion may not start primary-worker
routing with zero `open_weights_self_hostable` providers.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

Category = Literal["hosted_api", "open_weights_self_hostable", "unknown"]


@runtime_checkable
class Provider(Protocol):
    """Inference provider (hosted API, self-hosted open weights, or stub)."""

    provider_id: str
    category: Category

    def health(self) -> bool: ...


@dataclass
class _ManifestOpenWeights:
    ows: list[dict[str, Any]]


@dataclass
class InferenceRouter:
    """Registers providers and enforces the open-weights floor."""

    manifest_path: Path
    _providers: list[Provider] = field(default_factory=list)

    def register(self, p: Provider) -> None:
        self._providers.append(p)

    def _manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def active_open_weights_ids(self) -> frozenset[str]:
        m = self._manifest()
        return frozenset(x["id"] for x in m.get("open_weights", []))

    def bootstrap(self) -> None:
        """Refuse to complete if the open-weights floor is unsatisfied.

        A floor-satisfying provider is one whose `category` is
        `open_weights_self_hostable`, whose `id` is listed in
        `open_weights_manifest.json`, and whose `health()` is True.
        """
        m = self._manifest()
        allowed_ids = {x["id"] for x in m.get("open_weights", [])}
        floor_ok = any(
            p.provider_id in allowed_ids
            and p.category == "open_weights_self_hostable"
            and p.health()
            for p in self._providers
        )
        if not floor_ok:
            raise RuntimeError(
                "Inference Router bootstrap refused: Invariant 17 open-weights "
                "floor not satisfied (no healthy open_weights_self_hostable provider "
                f"matching manifest ids {sorted(allowed_ids)})."
            )


@dataclass
class OpenWeightsFloorStub:
    """Development / CI stub: manifest id + healthy local surface."""

    provider_id: str
    category: Category = "open_weights_self_hostable"

    def health(self) -> bool:
        return True


def default_manifest_path() -> Path:
    env = os.environ.get("XION_OPEN_WEIGHTS_MANIFEST", "").strip()
    if env:
        return Path(env)
    # Repo-relative default when running from a checkout.
    here = Path(__file__).resolve()
    return here.parent / "open_weights_manifest.json"


def load_router(*, providers: list[Provider] | None = None) -> InferenceRouter:
    r = InferenceRouter(manifest_path=default_manifest_path())
    for p in providers or ():
        r.register(p)
    return r


__all__ = [
    "Category",
    "InferenceRouter",
    "OpenWeightsFloorStub",
    "Provider",
    "default_manifest_path",
    "load_router",
]
