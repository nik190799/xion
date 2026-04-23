"""Tests for ``xion-verify api-tokens`` (Phase 5g-iv)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.commands.api_tokens import api_tokens
from xion_verify.exit_codes import FAIL, OK

_ADMISSION_ENV_VARS = (
    "XION_API_REQUIRE_BEARER",
    "XION_API_BEARER_TOKENS",
    "XION_API_RATE_BUDGET",
    "XION_API_RATE_WINDOW_S",
    "XION_API_HEALTH_RATE_BUDGET",
    "XION_API_HOST",
    "XION_API_PORT",
    "XION_TLS_CERT_PATH",
    "XION_TLS_KEY_PATH",
)

_GOOD_SECRET_HEX = (b"\xab" * 32).hex()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ADMISSION_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _invoke(args: list[str] | None = None) -> tuple[int, str]:
    runner = CliRunner()
    result = runner.invoke(api_tokens, args or [])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output


def test_compat_mode_loopback_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQUIRE_BEARER=false on loopback is the 5g-i backward-compat
    posture; the verifier reports OK with zero loaded tokens."""
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "false")
    code, out = _invoke()
    assert code == OK, out
    assert "bind=127.0.0.1:8000" in out
    assert "loopback (plaintext)" in out
    assert "tokens_loaded=0" in out


def test_require_bearer_with_token_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "true")
    monkeypatch.setenv(
        "XION_API_BEARER_TOKENS", f"alice:{_GOOD_SECRET_HEX}"
    )
    code, out = _invoke()
    assert code == OK, out
    assert "tokens_loaded=1" in out
    assert "secret-byte lengths observed: [32]" in out


def test_require_bearer_with_empty_tokens_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "true")
    code, out = _invoke()
    assert code == FAIL
    assert "require_bearer=true" in out


def test_short_secret_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    short_hex = (b"\xab" * 8).hex()  # 8 bytes < 16
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "true")
    monkeypatch.setenv("XION_API_BEARER_TOKENS", f"alice:{short_hex}")
    code, out = _invoke()
    assert code == FAIL
    assert "minimum is 16" in out


def test_bad_principal_charset_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "true")
    monkeypatch.setenv(
        "XION_API_BEARER_TOKENS", f"Alice!:{_GOOD_SECRET_HEX}"
    )
    code, out = _invoke()
    assert code == FAIL
    assert "does not match" in out


def test_non_loopback_without_tls_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "true")
    monkeypatch.setenv(
        "XION_API_BEARER_TOKENS", f"alice:{_GOOD_SECRET_HEX}"
    )
    monkeypatch.setenv("XION_API_HOST", "0.0.0.0")
    code, out = _invoke()
    assert code == FAIL
    assert "non-loopback" in out


def test_non_loopback_with_missing_cert_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "true")
    monkeypatch.setenv(
        "XION_API_BEARER_TOKENS", f"alice:{_GOOD_SECRET_HEX}"
    )
    monkeypatch.setenv("XION_API_HOST", "0.0.0.0")
    monkeypatch.setenv("XION_TLS_CERT_PATH", str(tmp_path / "missing.crt"))
    monkeypatch.setenv("XION_TLS_KEY_PATH", str(tmp_path / "missing.key"))
    code, out = _invoke()
    assert code == FAIL
    assert "tls_cert_path" in out


def test_non_loopback_with_existing_tls_ok(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cert = tmp_path / "fake.crt"
    key = tmp_path / "fake.key"
    cert.write_bytes(b"-----BEGIN CERTIFICATE-----\nx\n-----END CERTIFICATE-----\n")
    key.write_bytes(b"-----BEGIN PRIVATE KEY-----\nx\n-----END PRIVATE KEY-----\n")
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "true")
    monkeypatch.setenv(
        "XION_API_BEARER_TOKENS", f"alice:{_GOOD_SECRET_HEX}"
    )
    monkeypatch.setenv("XION_API_HOST", "example.org")
    monkeypatch.setenv("XION_API_PORT", "8443")
    monkeypatch.setenv("XION_TLS_CERT_PATH", str(cert))
    monkeypatch.setenv("XION_TLS_KEY_PATH", str(key))
    code, out = _invoke()
    assert code == OK, out
    assert "non-loopback (TLS)" in out
    assert "bind=example.org:8443" in out
    assert "tls_cert=" in out


def test_env_file_overlay_ok(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / "deploy.env"
    env_file.write_text(
        "# Phase 5g-iv deploy\n"
        "XION_API_REQUIRE_BEARER=true\n"
        f"XION_API_BEARER_TOKENS=alice:{_GOOD_SECRET_HEX}\n"
        "XION_API_RATE_BUDGET=120\n"
        "\n",
        encoding="utf-8",
    )
    code, out = _invoke(["--env-file", str(env_file)])
    assert code == OK, out
    assert "tokens_loaded=1" in out
    assert "rate_budget=120" in out
    assert "env-file overlay:" in out


def test_env_file_overlay_does_not_persist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The overlay must restore the prior process env after the verifier
    exits — otherwise a CI run that audits multiple env-files in
    sequence leaks values across audits."""
    import os as _os

    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "false")
    env_file = tmp_path / "deploy.env"
    env_file.write_text(
        "XION_API_REQUIRE_BEARER=true\n"
        f"XION_API_BEARER_TOKENS=alice:{_GOOD_SECRET_HEX}\n",
        encoding="utf-8",
    )
    code, _ = _invoke(["--env-file", str(env_file)])
    assert code == OK
    # The process env must have the original "false" value, not the overlaid "true".
    assert _os.environ["XION_API_REQUIRE_BEARER"] == "false"


def test_env_file_malformed_line_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / "broken.env"
    env_file.write_text("XION_API_REQUIRE_BEARER\n", encoding="utf-8")
    code, out = _invoke(["--env-file", str(env_file)])
    assert code == FAIL
    assert "not a key=value pair" in out


def test_env_file_ignores_unrelated_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unrelated keys in the env-file are silently ignored — the verifier
    audits admission-shape only and should not falsely reject because
    the operator's deploy file also carries pricing or billing knobs."""
    env_file = tmp_path / "deploy.env"
    env_file.write_text(
        "XION_API_REQUIRE_BEARER=false\n"
        "XION_PAYMENT_LEDGER=/tmp/PAYMENT_LEDGER.jsonl\n"
        "XION_BILLING_REQUIRED=true\n",
        encoding="utf-8",
    )
    code, _ = _invoke(["--env-file", str(env_file)])
    assert code == OK


def test_bad_port_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "false")
    monkeypatch.setenv("XION_API_PORT", "70000")
    code, out = _invoke()
    assert code == FAIL
    assert "api_port" in out


def test_bad_boolean_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XION_API_REQUIRE_BEARER", "maybe")
    code, out = _invoke()
    assert code == FAIL
    assert "boolean" in out
