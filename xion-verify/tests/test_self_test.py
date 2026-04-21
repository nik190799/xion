"""Tests for `xion-verify --self-test`.

Property under test: the self-test computes a deterministic tree hash of the
package's Python sources, comparing to PINNED_HASH.txt. A mismatch returns
`TAMPERED`.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from xion_verify.cli import root as cli_root
from xion_verify.commands.self_test import compute_self_hash, pin_path, run_self_test
from xion_verify.exit_codes import FAIL, OK, TAMPERED


def test_compute_self_hash_is_deterministic() -> None:
    first = compute_self_hash()
    second = compute_self_hash()
    assert first == second
    assert len(first) == 64


def test_pin_matches_computed_hash() -> None:
    """The committed PINNED_HASH.txt must match the installed source."""
    pp = pin_path()
    assert pp.is_file(), f"Expected pin file at {pp}"
    expected = pp.read_text(encoding="utf-8").strip()
    actual = compute_self_hash()
    assert expected == actual, (
        f"Pin drift: PINNED_HASH.txt={expected} vs computed={actual}. "
        "Regenerate via: xion-verify --self-test --update --i-understand"
    )


def test_self_test_cli_ok() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_root, ["--self-test"])
    assert result.exit_code == OK, result.output


def test_update_without_i_understand_fails(monkeypatch, tmp_path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli_root, ["--self-test", "--update"])
    assert result.exit_code == FAIL


def test_tampered_pin_is_detected(monkeypatch) -> None:
    pp = pin_path()
    real = pp.read_text(encoding="utf-8")
    pp.write_text("0" * 64 + "\n", encoding="utf-8")
    try:
        code, msg = run_self_test(update=False, i_understand=False)
        assert code == TAMPERED
        assert "TAMPERED" in msg
    finally:
        pp.write_text(real, encoding="utf-8")


@pytest.mark.skip(reason="missing-pin path requires isolated package copy; covered manually")
def test_missing_pin_reports_tampered() -> None:  # pragma: no cover
    pass
