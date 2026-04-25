"""Voice Router (Phase 6.5) — Invariant 18 floor enforcement.

Mirrors `orchestrator/inference_router/router.py` for voice categories.
Doctrine: `docs/proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

VoiceCategory = Literal["voice_hosted_api", "voice_open_source_self_hostable", "unknown"]
VoicePolicyMode = Literal["voice_hosted_api_first", "voice_open_source_only"]
DEFAULT_VOICE_POLICY_MODE: VoicePolicyMode = "voice_hosted_api_first"


@runtime_checkable
class VoiceProvider(Protocol):
    """STT/TTS/turn-taking provider (self-hosted or hosted API)."""

    provider_id: str
    category: VoiceCategory

    def health(self) -> bool: ...


@dataclass
class VoiceRouter:
    """Registers voice providers and enforces the open-source floor."""

    manifest_path: Path
    policy_mode: VoicePolicyMode = DEFAULT_VOICE_POLICY_MODE
    _providers: list[VoiceProvider] = field(default_factory=list)
    _bootstrapped: bool = field(default=False, init=False, repr=False)

    def register(self, p: VoiceProvider) -> None:
        self._providers.append(p)

    def _manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def active_floor_ids(self) -> frozenset[str]:
        m = self._manifest()
        return frozenset(x["id"] for x in m.get("voice_open_source", []))

    def bootstrap(self) -> None:
        """Refuse if no healthy `voice_open_source_self_hostable` floor provider.

        Invariant 18 requires ≥1 floor provider matching manifest id with
        health() True. Mirrors InferenceRouter.bootstrap.
        """
        m = self._manifest()
        allowed_ids = {x["id"] for x in m.get("voice_open_source", [])}
        floor_ok = any(
            p.provider_id in allowed_ids
            and p.category == "voice_open_source_self_hostable"
            and p.health()
            for p in self._providers
        )
        if not floor_ok:
            raise RuntimeError(
                "Voice Router bootstrap refused: Invariant 18 floor not satisfied "
                f"(no healthy voice_open_source_self_hostable provider for ids {sorted(allowed_ids)})."
            )
        self._bootstrapped = True

    @property
    def bootstrapped(self) -> bool:
        return self._bootstrapped

    def select_floor(self) -> VoiceProvider | None:
        """Return a healthy floor provider, or None."""
        if not self._bootstrapped:
            return None
        allowed = self.active_floor_ids()
        for p in self._providers:
            if (
                p.provider_id in allowed
                and p.category == "voice_open_source_self_hostable"
                and p.health()
            ):
                return p
        return None


@dataclass
class VoiceFloorStub:
    """CI / development: manifest id with healthy static surface."""

    provider_id: str
    category: VoiceCategory = "voice_open_source_self_hostable"

    def health(self) -> bool:
        return True


def default_manifest_path() -> Path:
    env = os.environ.get("XION_VOICE_OPEN_SOURCE_MANIFEST", "").strip()
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    return here.parent / "voice_open_source_manifest.json"


def load_voice_router(*, providers: list[VoiceProvider] | None = None) -> VoiceRouter:
    r = VoiceRouter(manifest_path=default_manifest_path())
    for p in providers or ():
        r.register(p)
    return r


__all__ = [
    "DEFAULT_VOICE_POLICY_MODE",
    "VoiceCategory",
    "VoiceFloorStub",
    "VoicePolicyMode",
    "VoiceProvider",
    "VoiceRouter",
    "default_manifest_path",
    "load_voice_router",
]
