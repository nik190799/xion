from __future__ import annotations

from click.testing import CliRunner

from xion_verify.commands.sovereign_profile import sovereign_profile


def test_sovereign_profile_ok(monkeypatch) -> None:
    monkeypatch.setenv("XION_PROFILE", "sovereign")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("XION_OPENROUTER_API_KEY", raising=False)
    result = CliRunner().invoke(sovereign_profile)
    assert result.exit_code == 0
    assert "sovereign-profile: OK" in result.output


def test_sovereign_profile_fails_on_openai_key(monkeypatch) -> None:
    monkeypatch.setenv("XION_PROFILE", "sovereign")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    result = CliRunner().invoke(sovereign_profile)
    assert result.exit_code == 1
    assert "OPENAI_API_KEY must be unset" in result.output


def test_sovereign_profile_fails_on_short_rpc_quorum(monkeypatch) -> None:
    monkeypatch.setenv("XION_PROFILE", "sovereign")
    monkeypatch.setenv("XION_BASE_RPC_URLS", "https://a,https://b")
    result = CliRunner().invoke(sovereign_profile)
    assert result.exit_code == 1
    assert "at least 3 endpoints" in result.output
