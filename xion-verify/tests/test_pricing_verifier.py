"""Tests for ``xion-verify pricing`` — promoted from NOT_YET_SEALED."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from xion_verify.commands.pricing import pricing
from xion_verify.exit_codes import FAIL, OK

_PRICING_ENV_VARS = (
    "XION_POSTED_PRICE_MICRO_XION",
    "XION_PRICE_SLICE_VARIABLE_COST",
    "XION_PRICE_SLICE_OVERHEAD",
    "XION_PRICE_SLICE_IMPROVEMENT",
    "XION_PRICE_SLICE_RESERVE",
    "XION_PRICE_SLICE_SMALL_BUFFER",
    "XION_PRICING_LAST_REVIEWED_UTC_NS",
    "XION_PRICING_REVISION_ID",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _PRICING_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _invoke() -> tuple[int, str]:
    runner = CliRunner()
    result = runner.invoke(pricing, [])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output


def test_genesis_defaults_ok() -> None:
    code, out = _invoke()
    assert code == OK
    assert "posted=1000 micro_XION" in out
    assert "'genesis-default-v1'" in out
    assert "sum                1.0000" in out


def test_slices_sum_mismatch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XION_PRICE_SLICE_VARIABLE_COST", "0.50")
    # Other slices stay at Genesis Default → sum = 0.50 + 0.44 + 0.08 + 0.05 + 0.03 = 1.10 → FAIL.
    code, out = _invoke()
    assert code == FAIL
    assert "Five-slice split must sum to 1.0" in out


def test_negative_posted_price_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XION_POSTED_PRICE_MICRO_XION", "-1")
    code, out = _invoke()
    assert code == FAIL
    assert "must be non-negative" in out


def test_empty_revision_id_falls_back_to_genesis(monkeypatch: pytest.MonkeyPatch) -> None:
    # Empty override falls back to the Genesis Default revision id,
    # which is non-empty, so load succeeds.
    monkeypatch.setenv("XION_PRICING_REVISION_ID", "   ")
    code, out = _invoke()
    assert code == OK
    assert "'genesis-default-v1'" in out


def test_operator_override_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XION_POSTED_PRICE_MICRO_XION", "2500")
    monkeypatch.setenv("XION_PRICE_SLICE_VARIABLE_COST", "0.30")
    monkeypatch.setenv("XION_PRICE_SLICE_OVERHEAD", "0.54")
    monkeypatch.setenv("XION_PRICE_SLICE_IMPROVEMENT", "0.08")
    monkeypatch.setenv("XION_PRICE_SLICE_RESERVE", "0.05")
    monkeypatch.setenv("XION_PRICE_SLICE_SMALL_BUFFER", "0.03")
    monkeypatch.setenv("XION_PRICING_REVISION_ID", "gov-tx-0xabc")
    code, out = _invoke()
    assert code == OK
    assert "posted=2500 micro_XION" in out
    assert "'gov-tx-0xabc'" in out


def test_malformed_slice_value_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XION_PRICE_SLICE_VARIABLE_COST", "not-a-float")
    code, out = _invoke()
    assert code == FAIL
    assert "must be a float" in out
