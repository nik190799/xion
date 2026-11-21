"""Tests for ``xion-verify safe-proposal``.

Verifies the offline (--prep) flow exhaustively. The online flow is covered by
mocking ``urlopen`` so no network is touched.

Closure verifier for ``KW-OPS-001`` per ``KNOWN_WEAKNESSES.md`` § Verifier.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from xion_verify.commands.safe_proposal import safe_proposal
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK

SAFE_ADDRESS = "0x5A91E08D909854b594f07648D23440f4908529b4"
TARGET_CONTRACT = "0xbf5407745cF22B88C46b55037e26156a0E78fD7f"


def _invoke(args: list[str]) -> tuple[int, str, str]:
    """Returns (exit_code, output, output) — click 8.3 merges stderr into output."""

    runner = CliRunner()
    result = runner.invoke(safe_proposal, args, standalone_mode=True)
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output, result.output


def _patch_keccak(fixed_output: bytes = b"\x42" * 32) -> Any:
    """Replace the cast-keccak shellout with a deterministic in-process fake.

    The verifier's encoding logic (what bytes get fed to keccak) is what gets
    exercised. Keccak itself is delegated to Foundry in production; tests
    don't cover the cryptographic primitive.
    """

    return patch(
        "xion_verify.commands.safe_proposal._cast_keccak",
        return_value=fixed_output,
    )


# ---------------------------------------------------------------------------
# Sentinel: missing inputs → NOT_YET_SEALED
# ---------------------------------------------------------------------------


class TestSentinel:
    def test_no_args_returns_not_yet_sealed(self) -> None:
        code, _stdout, stderr = _invoke([])
        assert code == NOT_YET_SEALED
        assert "NOT_YET_SEALED" in stderr

    def test_partial_online_args_returns_not_yet_sealed(self) -> None:
        code, _stdout, stderr = _invoke(["--safe-address", SAFE_ADDRESS])
        assert code == NOT_YET_SEALED
        assert "NOT_YET_SEALED" in stderr


# ---------------------------------------------------------------------------
# Offline (--prep) mode
# ---------------------------------------------------------------------------


def _write_prep(tmp_path: Path, **overrides: Any) -> Path:
    base = {
        "safe_tx_hash": "0x" + "42" * 32,  # matches _patch_keccak default
        "chain_id": 8453,
        "safe_address": SAFE_ADDRESS,
        "nonce": 7,
        "tx": {
            "to": TARGET_CONTRACT,
            "value": "0",
            "data": "0xb6c52840",
            "operation": 0,
            "safeTxGas": "0",
            "baseGas": "0",
            "gasPrice": "0",
            "gasToken": "0x" + "00" * 20,
            "refundReceiver": "0x" + "00" * 20,
            "nonce": 7,
        },
    }
    base.update(overrides)
    path = tmp_path / "prep.json"
    path.write_text(json.dumps(base), encoding="utf-8")
    return path


class TestOfflinePrep:
    def test_ok_when_recomputed_hash_matches_claim(self, tmp_path: Path) -> None:
        prep = _write_prep(tmp_path)
        with _patch_keccak():
            code, stdout, _stderr = _invoke(["--prep", str(prep)])
        assert code == OK
        assert "safe-proposal: OK" in stdout
        assert SAFE_ADDRESS in stdout

    def test_fail_when_claimed_hash_disagrees_with_recomputed(self, tmp_path: Path) -> None:
        # Prep claims a different hash than what keccak (returning 0x42..) yields
        prep = _write_prep(tmp_path, safe_tx_hash="0x" + "ff" * 32)
        with _patch_keccak():
            code, _stdout, stderr = _invoke(["--prep", str(prep)])
        assert code == FAIL
        assert "hash mismatch" in stderr

    def test_expected_call_data_match_keeps_ok(self, tmp_path: Path) -> None:
        prep = _write_prep(tmp_path)
        with _patch_keccak():
            code, _stdout, _stderr = _invoke(
                ["--prep", str(prep), "--expected-call-data", "0xb6c52840"]
            )
        assert code == OK

    def test_expected_call_data_mismatch_fails(self, tmp_path: Path) -> None:
        prep = _write_prep(tmp_path)
        with _patch_keccak():
            code, _stdout, stderr = _invoke(
                ["--prep", str(prep), "--expected-call-data", "0xdeadbeef"]
            )
        assert code == FAIL
        assert "call data mismatch" in stderr

    def test_expected_to_normalizes_case(self, tmp_path: Path) -> None:
        prep = _write_prep(tmp_path)
        with _patch_keccak():
            code, _stdout, _stderr = _invoke(
                ["--prep", str(prep), "--expected-to", TARGET_CONTRACT.upper()]
            )
        assert code == OK

    def test_expected_to_mismatch_fails(self, tmp_path: Path) -> None:
        prep = _write_prep(tmp_path)
        wrong = "0x" + "11" * 20
        with _patch_keccak():
            code, _stdout, stderr = _invoke(
                ["--prep", str(prep), "--expected-to", wrong]
            )
        assert code == FAIL
        assert "to mismatch" in stderr

    def test_expected_value_match(self, tmp_path: Path) -> None:
        prep = _write_prep(tmp_path)
        with _patch_keccak():
            code, _stdout, _stderr = _invoke(
                ["--prep", str(prep), "--expected-value", "0"]
            )
        assert code == OK

    def test_expected_value_mismatch_fails(self, tmp_path: Path) -> None:
        prep = _write_prep(tmp_path)
        with _patch_keccak():
            code, _stdout, stderr = _invoke(
                ["--prep", str(prep), "--expected-value", "1"]
            )
        assert code == FAIL
        assert "value mismatch" in stderr

    def test_unreadable_prep_fails(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist.json"
        code, _stdout, stderr = _invoke(["--prep", str(missing)])
        assert code == FAIL
        assert "cannot read prep" in stderr


# ---------------------------------------------------------------------------
# Online flow (mocked HTTP)
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> "_Resp":
        return self

    def __exit__(self, *_a: Any) -> None:
        pass

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class TestOnlineFlow:
    def _service_payload(self, **overrides: Any) -> dict[str, Any]:
        # Shape matches the Safe Transaction Service /multisig-transactions/{hash}/ response.
        base = {
            "to": TARGET_CONTRACT,
            "value": "0",
            "data": "0xb6c52840",
            "operation": 0,
            "safeTxGas": "0",
            "baseGas": "0",
            "gasPrice": "0",
            "gasToken": "0x" + "00" * 20,
            "refundReceiver": "0x" + "00" * 20,
            "nonce": 7,
            "contractTransactionHash": "0x" + "42" * 32,
        }
        base.update(overrides)
        return base

    def test_online_by_safe_tx_hash_ok(self) -> None:
        payload = self._service_payload()
        with _patch_keccak():
            with patch(
                "xion_verify.commands.safe_proposal.urlopen",
                lambda url, timeout=0: _Resp(payload),
            ):
                code, stdout, _stderr = _invoke(
                    [
                        "--safe-address",
                        SAFE_ADDRESS,
                        "--network",
                        "base-mainnet",
                        "--safe-tx-hash",
                        "0x" + "42" * 32,
                    ]
                )
        assert code == OK
        assert "safe-proposal: OK" in stdout

    def test_online_by_nonce_paginated_response_ok(self) -> None:
        payload = {"results": [self._service_payload()]}
        with _patch_keccak():
            with patch(
                "xion_verify.commands.safe_proposal.urlopen",
                lambda url, timeout=0: _Resp(payload),
            ):
                code, _stdout, _stderr = _invoke(
                    [
                        "--safe-address",
                        SAFE_ADDRESS,
                        "--network",
                        "base-sepolia",
                        "--nonce",
                        "7",
                    ]
                )
        assert code == OK

    def test_online_empty_results_fails(self) -> None:
        with _patch_keccak():
            with patch(
                "xion_verify.commands.safe_proposal.urlopen",
                lambda url, timeout=0: _Resp({"results": []}),
            ):
                code, _stdout, stderr = _invoke(
                    [
                        "--safe-address",
                        SAFE_ADDRESS,
                        "--network",
                        "base-sepolia",
                        "--nonce",
                        "99",
                    ]
                )
        assert code == FAIL
        assert "No proposal found" in stderr

    def test_online_unknown_network_fails(self) -> None:
        code, _stdout, stderr = _invoke(
            [
                "--safe-address",
                SAFE_ADDRESS,
                "--network",
                "ethereum-mainnet",
                "--nonce",
                "1",
            ]
        )
        assert code == FAIL
        assert "unknown network" in stderr or "Safe Transaction Service URL" in stderr

    def test_online_hash_mismatch_fails(self) -> None:
        payload = self._service_payload(contractTransactionHash="0x" + "ff" * 32)
        with _patch_keccak():  # recomputes 0x42..32
            with patch(
                "xion_verify.commands.safe_proposal.urlopen",
                lambda url, timeout=0: _Resp(payload),
            ):
                code, _stdout, stderr = _invoke(
                    [
                        "--safe-address",
                        SAFE_ADDRESS,
                        "--network",
                        "base-mainnet",
                        "--nonce",
                        "7",
                    ]
                )
        # /multisig-transactions/{hash}/ would fail by hash; here we exercise
        # the nonce-listed path which returns the first result. Hash mismatch
        # against what the service itself stored should still FAIL because the
        # verifier's job is to detect *any* divergence.
        assert code == FAIL
        assert "hash mismatch" in stderr
