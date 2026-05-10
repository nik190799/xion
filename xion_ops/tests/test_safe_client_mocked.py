"""Offline tests for ``xion_ops.services.safe``.

The cryptographic primitive (keccak-256) is *intentionally* not exercised here.
We delegate that to Foundry's ``cast keccak`` in production. What this suite
does verify, byte-for-byte, is the EIP-712 / SafeTx encoding logic — every
sequence of bytes that gets fed to keccak. End-to-end correctness against a
real Safe deployment lands in step A5 (live Sepolia dry-run).

Closes KW-OPS-001 ``offline tests for payload construction``.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from xion_ops.services.safe import (
    DOMAIN_SEPARATOR_TYPEHASH,
    OPERATION_CALL,
    OPERATION_DELEGATECALL,
    SAFE_TX_TYPEHASH,
    ProposedSafeTx,
    SafeError,
    SafeTx,
    SafeTxServiceClient,
    domain_separator,
    encode_domain_separator_input,
    encode_safe_tx_struct_input,
    make_cast_keccak,
    safe_tx_hash,
)

# Canonical addresses used across fixtures. The Safe address is the real
# Base mainnet Warm-tier Safe; the others are illustrative only.
SAFE_ADDRESS = "0x5A91E08D909854b594f07648D23440f4908529b4"
TARGET_CONTRACT = "0xbf5407745cF22B88C46b55037e26156a0E78fD7f"
ZERO_ADDR = "0x" + "00" * 20


def _hexword(value: int) -> bytes:
    return value.to_bytes(32, "big")


def _addrword(addr: str) -> bytes:
    return bytes(12) + bytes.fromhex(addr[2:])


# ---------------------------------------------------------------------------
# Encoding primitives
# ---------------------------------------------------------------------------


class TestUint256AndAddressEncoding:
    def test_address_word_left_pads_12_bytes(self) -> None:
        from xion_ops.services.safe import _address_word

        word = _address_word(TARGET_CONTRACT)
        assert len(word) == 32
        assert word[:12] == bytes(12)
        assert word[12:].hex() == TARGET_CONTRACT.lower()[2:]

    def test_uint256_packs_big_endian(self) -> None:
        from xion_ops.services.safe import _uint256

        assert _uint256(0) == bytes(32)
        assert _uint256(1) == bytes(31) + b"\x01"
        max_val = 2**256 - 1
        assert _uint256(max_val) == b"\xff" * 32

    def test_uint256_rejects_overflow(self) -> None:
        from xion_ops.services.safe import _uint256

        with pytest.raises(SafeError, match="uint256 out of range"):
            _uint256(2**256)
        with pytest.raises(SafeError, match="uint256 out of range"):
            _uint256(-1)

    def test_address_validation(self) -> None:
        with pytest.raises(SafeError, match="20-byte hex address"):
            SafeTx(to="not-an-address", value=0, data=b"")
        with pytest.raises(SafeError, match="20-byte hex address"):
            SafeTx(to="0x" + "00" * 19, value=0, data=b"")  # too short
        with pytest.raises(SafeError, match="not valid hex"):
            SafeTx(to="0x" + "ZZ" * 20, value=0, data=b"")


# ---------------------------------------------------------------------------
# EIP-712 envelope structure
# ---------------------------------------------------------------------------


class TestDomainSeparatorEncoding:
    def test_input_bytes_match_solidity_abi_encode(self) -> None:
        chain_id = 8453  # Base mainnet
        encoded = encode_domain_separator_input(chain_id, SAFE_ADDRESS)
        assert len(encoded) == 32 + 32 + 32
        assert encoded[:32] == DOMAIN_SEPARATOR_TYPEHASH
        assert encoded[32:64] == _hexword(chain_id)
        assert encoded[64:] == _addrword(SAFE_ADDRESS)

    def test_calls_keccak_exactly_once_with_encoded_input(self) -> None:
        chain_id = 84532  # Base Sepolia
        keccak = MagicMock(return_value=b"\xde" * 32)
        sep = domain_separator(chain_id, SAFE_ADDRESS, keccak)
        keccak.assert_called_once()
        (call_input,), _ = keccak.call_args
        assert call_input == encode_domain_separator_input(chain_id, SAFE_ADDRESS)
        assert sep == b"\xde" * 32


class TestSafeTxStructEncoding:
    def _sample(self) -> SafeTx:
        # Encode a registerVault(uint256,address) call: 0xb6c52840 selector
        # plus chain_id 8453 and a vault address. Selector here is illustrative
        # — the real selector for MasterTreasury.registerVault is computed by
        # cast/forge; we don't need the real one to test encoding logic.
        selector = bytes.fromhex("b6c52840")
        chain_id_arg = _hexword(8453)
        vault_arg = _addrword(TARGET_CONTRACT)
        call_data = selector + chain_id_arg + vault_arg
        return SafeTx(
            to=TARGET_CONTRACT,
            value=0,
            data=call_data,
            operation=OPERATION_CALL,
            safe_tx_gas=0,
            base_gas=0,
            gas_price=0,
            gas_token=ZERO_ADDR,
            refund_receiver=ZERO_ADDR,
            nonce=42,
        )

    def test_struct_input_layout_matches_typehash_order(self) -> None:
        tx = self._sample()
        data_hash = b"\xab" * 32
        encoded = encode_safe_tx_struct_input(tx, data_hash)
        # 11 words: typehash + 10 fields = 11 * 32 = 352 bytes
        assert len(encoded) == 11 * 32
        assert encoded[0:32] == SAFE_TX_TYPEHASH
        assert encoded[32:64] == _addrword(tx.to)
        assert encoded[64:96] == _hexword(tx.value)
        assert encoded[96:128] == data_hash
        assert encoded[128:160] == _hexword(tx.operation)
        assert encoded[160:192] == _hexword(tx.safe_tx_gas)
        assert encoded[192:224] == _hexword(tx.base_gas)
        assert encoded[224:256] == _hexword(tx.gas_price)
        assert encoded[256:288] == _addrword(tx.gas_token)
        assert encoded[288:320] == _addrword(tx.refund_receiver)
        assert encoded[320:352] == _hexword(tx.nonce)

    def test_data_hash_must_be_32_bytes(self) -> None:
        tx = self._sample()
        with pytest.raises(SafeError, match="data_hash must be 32 bytes"):
            encode_safe_tx_struct_input(tx, b"\x00" * 31)

    def test_delegatecall_operation_accepted_call_otherwise(self) -> None:
        # operation = 1 (DELEGATECALL) is permitted.
        SafeTx(to=TARGET_CONTRACT, value=0, data=b"", operation=OPERATION_DELEGATECALL)
        # Anything else is rejected up-front.
        with pytest.raises(SafeError, match="operation must be 0"):
            SafeTx(to=TARGET_CONTRACT, value=0, data=b"", operation=2)


class TestSafeTxHashEnvelope:
    """Verify that the EIP-712 envelope feeds keccak in the right order with
    the right bytes. We capture every keccak call and assert byte-equality.
    """

    def test_four_keccak_calls_in_canonical_order(self) -> None:
        tx = SafeTx(
            to=TARGET_CONTRACT,
            value=0,
            data=b"\xde\xad\xbe\xef",
            operation=OPERATION_CALL,
            nonce=7,
        )
        chain_id = 8453

        # Deterministic keccak: returns a tag-prefixed 32-byte digest derived
        # from the call index, so the test can verify both the inputs and
        # which output gets passed back into a later call.
        calls: list[bytes] = []
        outputs = [
            b"\x01" * 32,  # data_hash
            b"\x02" * 32,  # struct_hash
            b"\x03" * 32,  # domain separator
            b"\x04" * 32,  # final safeTxHash
        ]

        def fake_keccak(payload: bytes) -> bytes:
            calls.append(payload)
            return outputs[len(calls) - 1]

        result = safe_tx_hash(
            tx,
            chain_id=chain_id,
            safe_address=SAFE_ADDRESS,
            keccak=fake_keccak,
        )

        assert len(calls) == 4
        # Call 1: keccak(data)
        assert calls[0] == tx.data
        # Call 2: struct_input = TYPEHASH || ... || data_hash || ...
        assert calls[1] == encode_safe_tx_struct_input(tx, outputs[0])
        # Call 3: domain separator input
        assert calls[2] == encode_domain_separator_input(chain_id, SAFE_ADDRESS)
        # Call 4: 0x1901 || domainSep || structHash
        assert calls[3] == b"\x19\x01" + outputs[2] + outputs[1]
        # Output threaded through to the final call
        assert result == outputs[3]

    def test_empty_data_still_hashed(self) -> None:
        tx = SafeTx(to=TARGET_CONTRACT, value=0, data=b"")
        captured: list[bytes] = []

        def fake_keccak(payload: bytes) -> bytes:
            captured.append(payload)
            return bytes(32)

        safe_tx_hash(tx, chain_id=8453, safe_address=SAFE_ADDRESS, keccak=fake_keccak)
        # First call must hash the empty data, not be skipped.
        assert captured[0] == b""


# ---------------------------------------------------------------------------
# Cast keccak adapter
# ---------------------------------------------------------------------------


class TestCastKeccakAdapter:
    def test_passes_0x_hex_and_parses_stdout(self) -> None:
        captured_args: list[list[str]] = []

        class _Result:
            stdout = "0x" + "ab" * 32

        def fake_run(args: list[str]) -> Any:
            captured_args.append(args)
            return _Result()

        keccak = make_cast_keccak(fake_run)
        out = keccak(b"\xde\xad")
        assert captured_args == [["cast", "keccak", "0xdead"]]
        assert out == b"\xab" * 32

    def test_strips_leading_log_lines(self) -> None:
        # Some shells (notably WSL) prepend rc-file noise; the adapter must
        # take the last line.
        class _Result:
            stdout = "loaded /etc/profile\n0x" + "cd" * 32 + "\n"

        keccak = make_cast_keccak(lambda _args: _Result())
        assert keccak(b"") == b"\xcd" * 32

    def test_rejects_garbled_output(self) -> None:
        class _Result:
            stdout = "command not found"

        keccak = make_cast_keccak(lambda _args: _Result())
        with pytest.raises(SafeError, match="unexpected cast keccak"):
            keccak(b"\x00")


# ---------------------------------------------------------------------------
# Safe Transaction Service HTTP client
# ---------------------------------------------------------------------------


class TestSafeTxServiceClient:
    def test_resolves_known_network_to_pinned_url(self) -> None:
        c = SafeTxServiceClient(network="base-sepolia")
        assert c.api_base == "https://safe-transaction-base-sepolia.safe.global"
        c2 = SafeTxServiceClient(network="base-mainnet")
        assert c2.api_base == "https://safe-transaction-base.safe.global"

    def test_unknown_network_rejected(self) -> None:
        with pytest.raises(SafeError, match="no Safe Transaction Service URL"):
            SafeTxServiceClient(network="ethereum-mainnet")

    def test_propose_validates_inputs(self) -> None:
        c = SafeTxServiceClient(network="base-sepolia")
        tx = SafeTx(to=TARGET_CONTRACT, value=0, data=b"", nonce=1)

        with pytest.raises(SafeError, match="safe_tx_hash_hex must be"):
            c.propose(
                safe_address=SAFE_ADDRESS,
                safe_tx=tx,
                safe_tx_hash_hex="0xabc",  # wrong length
                sender=TARGET_CONTRACT,
                signature="0x" + "00" * 65,
            )
        with pytest.raises(SafeError, match="signature must be 0x-prefixed"):
            c.propose(
                safe_address=SAFE_ADDRESS,
                safe_tx=tx,
                safe_tx_hash_hex="0x" + "12" * 32,
                sender=TARGET_CONTRACT,
                signature="abc",
            )

    def test_propose_posts_canonical_safe_service_body(self) -> None:
        c = SafeTxServiceClient(network="base-sepolia")
        call_data = bytes.fromhex("b6c528400000000000000000000000000000000000000000000000000000000000002105")
        tx = SafeTx(
            to=TARGET_CONTRACT,
            value=0,
            data=call_data,
            nonce=42,
            safe_tx_gas=0,
            base_gas=0,
            gas_price=0,
        )
        safe_tx_hash_hex = "0x" + "12" * 32
        sender = "0xEBDDDf598b5b53C91ff185501d7b182ae5d6B88A"
        signature = "0x" + "ab" * 65

        captured: dict[str, Any] = {}

        class _Resp:
            def __enter__(self) -> "_Resp":
                return self

            def __exit__(self, *_a: Any) -> None:
                pass

            def read(self) -> bytes:
                return b'{"contractTransactionHash":"' + safe_tx_hash_hex.encode() + b'"}'

        def fake_urlopen(req: Any, timeout: int = 0) -> _Resp:
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))
            captured["headers"] = dict(req.headers)
            captured["timeout"] = timeout
            return _Resp()

        with patch("xion_ops.services.safe.urlopen", fake_urlopen):
            result = c.propose(
                safe_address=SAFE_ADDRESS,
                safe_tx=tx,
                safe_tx_hash_hex=safe_tx_hash_hex,
                sender=sender,
                signature=signature,
            )

        assert isinstance(result, ProposedSafeTx)
        assert result.safe_tx_hash == safe_tx_hash_hex
        assert result.nonce == 42
        assert (
            captured["url"]
            == f"https://safe-transaction-base-sepolia.safe.global/api/v1/safes/{SAFE_ADDRESS}/multisig-transactions/"
        )
        body = captured["body"]
        # Service expects integer-as-string for the uint256 fields.
        assert body["value"] == "0"
        assert body["safeTxGas"] == "0"
        assert body["baseGas"] == "0"
        assert body["gasPrice"] == "0"
        # nonce is an int in the service spec (not a string)
        assert body["nonce"] == 42
        # 0x-prefixed hex for data
        assert body["data"] == "0x" + call_data.hex()
        # Address fields preserved
        assert body["to"] == TARGET_CONTRACT
        assert body["sender"] == sender
        assert body["contractTransactionHash"] == safe_tx_hash_hex
        assert body["signature"] == signature
        # Origin defaulted
        assert body["origin"] == "xion-ops/safe.py"
        # Header is set (urllib lowercases header keys)
        assert any(k.lower() == "content-type" for k in captured["headers"])

    def test_propose_surfaces_http_error_body(self) -> None:
        from urllib.error import HTTPError
        from io import BytesIO

        c = SafeTxServiceClient(network="base-sepolia")
        tx = SafeTx(to=TARGET_CONTRACT, value=0, data=b"", nonce=1)

        def fake_urlopen(req: Any, timeout: int = 0) -> None:
            err = HTTPError(
                req.full_url,
                422,
                "Unprocessable",
                hdrs=None,  # type: ignore[arg-type]
                fp=BytesIO(b'{"signature":"invalid"}'),
            )
            raise err

        with patch("xion_ops.services.safe.urlopen", fake_urlopen):
            with pytest.raises(SafeError, match="422"):
                c.propose(
                    safe_address=SAFE_ADDRESS,
                    safe_tx=tx,
                    safe_tx_hash_hex="0x" + "12" * 32,
                    sender=TARGET_CONTRACT,
                    signature="0x" + "00" * 65,
                )

    def test_fetch_next_nonce_parses_service_payload(self) -> None:
        c = SafeTxServiceClient(network="base-sepolia")

        class _Resp:
            def __enter__(self) -> "_Resp":
                return self

            def __exit__(self, *_a: Any) -> None:
                pass

            def read(self) -> bytes:
                return b'{"nonce": 17, "threshold": 2}'

        with patch("xion_ops.services.safe.urlopen", lambda _u, timeout=0: _Resp()):
            assert c.fetch_next_nonce(SAFE_ADDRESS) == 17

    def test_fetch_next_nonce_accepts_string_nonce(self) -> None:
        # The Safe Transaction Service's /api/v1/safes/{address}/ endpoint
        # returns nonce as a JSON string in production (observed against
        # base-mainnet Warm Safe 2026-05-10).
        c = SafeTxServiceClient(network="base-mainnet")

        class _Resp:
            def __enter__(self) -> "_Resp":
                return self

            def __exit__(self, *_a: Any) -> None:
                pass

            def read(self) -> bytes:
                return b'{"nonce": "42", "threshold": 2, "owners": []}'

        with patch("xion_ops.services.safe.urlopen", lambda _u, timeout=0: _Resp()):
            assert c.fetch_next_nonce(SAFE_ADDRESS) == 42

    def test_fetch_next_nonce_rejects_garbled_string(self) -> None:
        c = SafeTxServiceClient(network="base-sepolia")

        class _Resp:
            def __enter__(self) -> "_Resp":
                return self

            def __exit__(self, *_a: Any) -> None:
                pass

            def read(self) -> bytes:
                return b'{"nonce": "not-a-number"}'

        with patch("xion_ops.services.safe.urlopen", lambda _u, timeout=0: _Resp()):
            with pytest.raises(SafeError, match="non-integer nonce string"):
                c.fetch_next_nonce(SAFE_ADDRESS)

    def test_fetch_next_nonce_rejects_missing_field(self) -> None:
        c = SafeTxServiceClient(network="base-sepolia")

        class _Resp:
            def __enter__(self) -> "_Resp":
                return self

            def __exit__(self, *_a: Any) -> None:
                pass

            def read(self) -> bytes:
                return b'{"threshold": 2}'

        with patch("xion_ops.services.safe.urlopen", lambda _u, timeout=0: _Resp()):
            with pytest.raises(SafeError, match="unexpected nonce shape"):
                c.fetch_next_nonce(SAFE_ADDRESS)


# ---------------------------------------------------------------------------
# Pinned typehash constants (canary against silent rotation of Safe constants)
# ---------------------------------------------------------------------------


class TestPinnedConstants:
    """If these ever change, every operator who built call data against the
    old typehash would generate proposals nobody can sign. The constants are
    only allowed to move when the project explicitly migrates the Safe to a
    different version, which is a doctrinal change recorded in CHANGELOG.
    """

    def test_safe_tx_typehash_v1_3_plus(self) -> None:
        assert SAFE_TX_TYPEHASH.hex() == "bb8310d486368db6bd6f849402fdd73ad53d316b5a4b2644ad6efe0f941286d8"

    def test_domain_separator_typehash_v1_3_plus(self) -> None:
        assert (
            DOMAIN_SEPARATOR_TYPEHASH.hex()
            == "47e79534a245952e8b16893a336b85a3d9ea9fa8c573f3d803afb92a79469218"
        )


# ---------------------------------------------------------------------------
# BaseEvmService wiring (A2) — verify the stub-replacement routes correctly
# ---------------------------------------------------------------------------


class TestBaseEvmServiceWiring:
    """Verify that ``BaseEvmService.safe_compute_tx_hash`` /
    ``safe_propose_tx`` thread inputs through to ``safe.py`` correctly,
    auto-fetch nonces, and surface failures as ``DeploymentResult.ok=False``
    instead of raising.
    """

    def _service(self, tmp_path: Any) -> Any:
        from xion_ops.services.base_evm import BaseEvmService

        return BaseEvmService(repo_root=tmp_path)

    def test_safe_compute_tx_hash_uses_chain_id_and_keccak(self, tmp_path: Any) -> None:
        from xion_ops.services.base_evm import BaseEvmService
        from xion_ops.types import CommandResult

        svc = BaseEvmService(repo_root=tmp_path)

        # Stub _run_foundry to act as cast keccak. Returns a deterministic
        # 32-byte digest derived from input length so we can assert routing.
        def fake_run(cmd: list[str], cwd: Any = None) -> CommandResult:
            assert cmd[0:2] == ["cast", "keccak"]
            payload_hex = cmd[2]
            assert payload_hex.startswith("0x")
            tag = (len(payload_hex) % 256).to_bytes(1, "big")
            return CommandResult(command=tuple(cmd), returncode=0, stdout="0x" + (tag * 32).hex(), stderr="")

        svc._run_foundry = fake_run  # type: ignore[assignment]

        # Stub the Safe service nonce fetch.
        from xion_ops.services import safe as safe_mod

        def fake_fetch_next_nonce(self: Any, addr: str, *, timeout_seconds: int = 15) -> int:
            return 99

        with patch.object(safe_mod.SafeTxServiceClient, "fetch_next_nonce", fake_fetch_next_nonce):
            result = svc.safe_compute_tx_hash(
                network="base-mainnet",
                safe_address=SAFE_ADDRESS,
                to=TARGET_CONTRACT,
                data=b"\xb6\xc5\x28\x40",
            )

        assert result["chain_id"] == 8453
        assert result["nonce"] == 99
        assert result["safe_tx_hash"].startswith("0x")
        assert len(result["safe_tx_hash"]) == 66
        assert result["tx"]["nonce"] == 99
        assert result["tx"]["data"] == "0xb6c52840"

    def test_safe_compute_tx_hash_rejects_unknown_network(self, tmp_path: Any) -> None:
        from xion_ops.exceptions import OpsError

        svc = self._service(tmp_path)
        with pytest.raises(OpsError, match="unsupported network for Safe"):
            svc.safe_compute_tx_hash(
                network="ethereum-mainnet",
                safe_address=SAFE_ADDRESS,
                to=TARGET_CONTRACT,
                data=b"",
            )

    def test_safe_propose_tx_returns_ok_false_on_service_rejection(self, tmp_path: Any) -> None:
        from xion_ops.types import CommandResult

        svc = self._service(tmp_path)

        def fake_run(cmd: list[str], cwd: Any = None) -> CommandResult:
            return CommandResult(command=tuple(cmd), returncode=0, stdout="0x" + ("ab" * 32), stderr="")

        svc._run_foundry = fake_run  # type: ignore[assignment]

        from xion_ops.services import safe as safe_mod

        def fake_fetch_next_nonce(self: Any, addr: str, *, timeout_seconds: int = 15) -> int:
            return 5

        def fake_propose(self: Any, **_kwargs: Any) -> Any:
            raise safe_mod.SafeError("Safe Transaction Service rejected proposal (422): bad sig")

        with patch.object(safe_mod.SafeTxServiceClient, "fetch_next_nonce", fake_fetch_next_nonce):
            with patch.object(safe_mod.SafeTxServiceClient, "propose", fake_propose):
                result = svc.safe_propose_tx(
                    network="base-sepolia",
                    safe_address=SAFE_ADDRESS,
                    to=TARGET_CONTRACT,
                    data=b"",
                    sender=TARGET_CONTRACT,
                    signature="0x" + "00" * 65,
                )

        assert result.ok is False
        assert result.id == "safe-propose"
        assert "rejected proposal" in result.details["error"]
        # The prep payload is preserved for operator debugging
        assert result.details["chain_id"] == 84532
        assert result.details["nonce"] == 5

    def test_safe_propose_tx_returns_ok_true_with_service_payload(self, tmp_path: Any) -> None:
        from xion_ops.services import safe as safe_mod
        from xion_ops.types import CommandResult

        svc = self._service(tmp_path)

        def fake_run(cmd: list[str], cwd: Any = None) -> CommandResult:
            return CommandResult(command=tuple(cmd), returncode=0, stdout="0x" + ("cd" * 32), stderr="")

        svc._run_foundry = fake_run  # type: ignore[assignment]

        def fake_fetch_next_nonce(self: Any, addr: str, *, timeout_seconds: int = 15) -> int:
            return 12

        captured: dict[str, Any] = {}

        def fake_propose(
            self: Any,
            *,
            safe_address: str,
            safe_tx: Any,
            safe_tx_hash_hex: str,
            sender: str,
            signature: str,
            origin: str | None = "xion-ops/safe.py",
            timeout_seconds: int = 30,
        ) -> Any:
            captured["safe_tx_hash_hex"] = safe_tx_hash_hex
            captured["nonce"] = safe_tx.nonce
            return safe_mod.ProposedSafeTx(
                safe_address=safe_address,
                safe_tx_hash=safe_tx_hash_hex,
                nonce=safe_tx.nonce,
                api_url="https://x/y/",
                response={"safeTxHash": safe_tx_hash_hex, "nonce": safe_tx.nonce},
            )

        with patch.object(safe_mod.SafeTxServiceClient, "fetch_next_nonce", fake_fetch_next_nonce):
            with patch.object(safe_mod.SafeTxServiceClient, "propose", fake_propose):
                result = svc.safe_propose_tx(
                    network="base-mainnet",
                    safe_address=SAFE_ADDRESS,
                    to=TARGET_CONTRACT,
                    data=b"\xde\xad",
                    sender=TARGET_CONTRACT,
                    signature="0x" + "11" * 65,
                )

        assert result.ok is True
        assert result.id.startswith("0x")
        assert result.details["chain_id"] == 8453
        assert result.details["nonce"] == 12
        assert captured["nonce"] == 12
        assert captured["safe_tx_hash_hex"] == result.id
