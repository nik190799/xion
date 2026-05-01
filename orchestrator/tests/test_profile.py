from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest


def test_sovereign_profile_is_frozen_and_disallows_centralized(monkeypatch) -> None:
    from orchestrator.profile import current_profile

    monkeypatch.setenv("XION_PROFILE", "sovereign")
    profile = current_profile()
    assert profile.name == "sovereign"
    assert profile.allows_centralized_fallbacks is False
    with pytest.raises(FrozenInstanceError):
        profile.allows_centralized_fallbacks = True  # type: ignore[misc]


def test_sovereign_refuses_centralized_env(monkeypatch) -> None:
    from orchestrator.api.lifespan import _enforce_sovereign_profile

    monkeypatch.setenv("XION_PROFILE", "sovereign")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        _enforce_sovereign_profile()


def test_sovereign_refuses_short_base_rpc_quorum(monkeypatch) -> None:
    from orchestrator.api.lifespan import _enforce_sovereign_profile

    monkeypatch.setenv("XION_PROFILE", "sovereign")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("XION_OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("XION_BASE_RPC_URLS", "https://a,https://b")
    with pytest.raises(RuntimeError, match="at least 3"):
        _enforce_sovereign_profile()
