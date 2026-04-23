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

PolicyMode = Literal["hosted_api_first", "open_weights_only"]
DEFAULT_POLICY_MODE: PolicyMode = "hosted_api_first"


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
    """Registers providers and enforces the open-weights floor.

    Phase 5g-i addition: the router grows a ``policy_mode`` field and a
    ``select()`` method that implements the two Phase 5g-i modes pinned
    in ``docs/26-INFERENCE-POLICY.md`` — ``hosted_api_first`` (Genesis
    Default) and ``open_weights_only`` (Invariant 17 clause 5 cutover
    mode). The selection is health-aware: unhealthy providers are
    skipped. Only providers that expose a ``generate`` method are
    eligible for turn serving — a manifest-stub floor provider that
    cannot generate cannot be selected.
    """

    manifest_path: Path
    policy_mode: PolicyMode = DEFAULT_POLICY_MODE
    _providers: list[Provider] = field(default_factory=list)
    _bootstrapped: bool = field(default=False, init=False, repr=False)

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

        On success flips ``_bootstrapped`` to True so ``select()`` can
        refuse to serve before bootstrap completes. This is belt-and-
        braces — the lifespan already refuses to serve ``/chat`` when
        bootstrap raises — but makes the Router's contract
        independently enforceable in unit tests.
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
        self._bootstrapped = True

    def select_ordered(
        self, *, policy: PolicyMode | None = None
    ) -> list[Provider]:
        """Return the full policy-legal, health-aware attempt order.

        Phase 5g-vii addition. Replaces single-provider ``select()`` as
        the primary selector. Returns every provider the caller is
        permitted to attempt, in the exact order an ``hosted_api_first``
        chat turn should try them: hosted-API providers (healthy,
        generate-capable) first, then the floor providers (healthy,
        manifest-listed, generate-capable). Under ``open_weights_only``
        the hosted category is filtered out entirely — this is the
        policy-boundary in ``docs/26-INFERENCE-POLICY.md`` § "Provider
        fallback semantics" P2.

        The list may be empty when no policy-legal provider is healthy;
        the chat handler maps an empty list to a 503 envelope with the
        typed failure-reason class of the last attempt (or, before any
        attempt was possible, to ``no_healthy_provider`` as a
        pre-selection failure class).

        ``select_ordered()`` is the shape C4 (``orchestrator/api/chat.py``)
        iterates to satisfy fallback property P1. ``select()`` remains as
        a back-compat façade for the Sensorium heartbeat-probe callers
        that only ever used the first element.
        """
        if not self._bootstrapped:
            return []

        mode: PolicyMode = policy if policy is not None else self.policy_mode

        def _usable(p: Provider) -> bool:
            return callable(getattr(p, "generate", None)) and bool(p.health())

        ordered: list[Provider] = []
        if mode == "hosted_api_first":
            ordered.extend(
                p
                for p in self._providers
                if p.category == "hosted_api" and _usable(p)
            )
        ordered.extend(
            p
            for p in self._providers
            if p.category == "open_weights_self_hostable" and _usable(p)
        )
        return ordered

    def select(self, *, policy: PolicyMode | None = None) -> Provider | None:
        """Back-compat single-selection façade.

        Returns the first element of ``select_ordered()`` or ``None``.
        Kept for callers that only need a single provider handle — the
        Sensorium heartbeat probe, tests written before 5g-vii, and
        legacy operator scripts. The chat handler migrated to
        ``select_ordered()`` in 5g-vii so that fallback property P1 can
        be honored.
        """
        ordered = self.select_ordered(policy=policy)
        return ordered[0] if ordered else None


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
    "DEFAULT_POLICY_MODE",
    "Category",
    "InferenceRouter",
    "OpenWeightsFloorStub",
    "PolicyMode",
    "Provider",
    "default_manifest_path",
    "load_router",
]
