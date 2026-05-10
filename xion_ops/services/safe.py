"""Safe (Gnosis Safe) Transaction Service client and EIP-712 SafeTx builder.

Closes the boundary surface of KW-OPS-001: ``BaseEvmService.safe_propose_tx``
delegates here instead of raising ``NotImplementedError``. The module is
deliberately small and dependency-free:

* HTTP via stdlib ``urllib.request`` (same pattern as ``base_evm._rpc``).
* Keccak-256 via an injectable callable. The default factory shells out to
  Foundry's ``cast keccak``; offline tests inject a fake that asserts encoding
  bytes against precomputed fixtures.
* No private keys touch this module. Cosigner signing happens through the
  Safe app or ``cast wallet sign``; this module only constructs unsigned
  SafeTx payloads and POSTs them to the Safe Transaction Service so cosigners
  can review.

Spec references:

* EIP-712: https://eips.ethereum.org/EIPS/eip-712
* Safe ``GnosisSafe.encodeTransactionData`` and ``getTransactionHash``:
  https://github.com/safe-global/safe-smart-account/blob/v1.4.1/contracts/Safe.sol
* Safe Transaction Service API:
  https://safe-transaction-base.safe.global/  (Base mainnet)
  https://safe-transaction-base-sepolia.safe.global/  (Base Sepolia)

Type-hash constants below are pinned from Safe v1.3+ audited source. Treat any
on-chain Safe whose version disagrees as out of scope for this module — the
Warm-tier Safe at 0x5A91...29b4 is Safe v1.4.1, which uses these constants.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

KeccakFn = Callable[[bytes], bytes]

# keccak256("EIP712Domain(uint256 chainId,address verifyingContract)")
# Pinned from Safe v1.3+ source (Safe.sol:DOMAIN_SEPARATOR_TYPEHASH).
DOMAIN_SEPARATOR_TYPEHASH: bytes = bytes.fromhex(
    "47e79534a245952e8b16893a336b85a3d9ea9fa8c573f3d803afb92a79469218"
)

# keccak256(
#   "SafeTx(address to,uint256 value,bytes data,uint8 operation,"
#   "uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,"
#   "address gasToken,address refundReceiver,uint256 nonce)"
# )
# Pinned from Safe v1.3+ source (Safe.sol:SAFE_TX_TYPEHASH).
SAFE_TX_TYPEHASH: bytes = bytes.fromhex(
    "bb8310d486368db6bd6f849402fdd73ad53d316b5a4b2644ad6efe0f941286d8"
)

# Operation enum from Safe.sol: 0 = CALL, 1 = DELEGATECALL.
OPERATION_CALL = 0
OPERATION_DELEGATECALL = 1

# Safe Transaction Service base URLs by network slug.
#
# Safe migrated their service from per-network ``safe-transaction-*.safe.global``
# subdomains to a single ``api.safe.global/tx-service/{shortcode}`` host with a
# 308 permanent redirect from the legacy URLs. GET requests follow the redirect
# transparently in urllib, but POST does not (per RFC), so the propose path must
# target the new canonical URL directly. Repin here when Safe migrates again;
# the legacy URLs are kept as commented references for auditability.
#
#   legacy base mainnet    : https://safe-transaction-base.safe.global
#   legacy base sepolia    : https://safe-transaction-base-sepolia.safe.global
SAFE_TX_SERVICE_URLS: Mapping[str, str] = {
    "base": "https://api.safe.global/tx-service/base",
    "base-mainnet": "https://api.safe.global/tx-service/base",
    "base-sepolia": "https://api.safe.global/tx-service/basesep",
}

CHAIN_IDS: Mapping[str, int] = {
    "base": 8453,
    "base-mainnet": 8453,
    "base-sepolia": 84532,
}


class SafeError(Exception):
    """Operational failure constructing or transmitting a Safe transaction."""


@dataclass(frozen=True)
class SafeTx:
    """An unsigned Safe transaction payload.

    Field names and types track ``Safe.sol`` exactly so an auditor can read
    encode_safe_tx_data side-by-side with the Solidity source.
    """

    to: str
    value: int
    data: bytes
    operation: int = OPERATION_CALL
    safe_tx_gas: int = 0
    base_gas: int = 0
    gas_price: int = 0
    gas_token: str = "0x" + "00" * 20
    refund_receiver: str = "0x" + "00" * 20
    nonce: int = 0

    def __post_init__(self) -> None:
        if self.operation not in (OPERATION_CALL, OPERATION_DELEGATECALL):
            raise SafeError(f"operation must be 0 (CALL) or 1 (DELEGATECALL); got {self.operation}")
        for label, addr in (("to", self.to), ("gas_token", self.gas_token), ("refund_receiver", self.refund_receiver)):
            _require_address(label, addr)
        for label, val in (
            ("value", self.value),
            ("safe_tx_gas", self.safe_tx_gas),
            ("base_gas", self.base_gas),
            ("gas_price", self.gas_price),
            ("nonce", self.nonce),
        ):
            if val < 0 or val.bit_length() > 256:
                raise SafeError(f"{label} must fit in uint256; got {val}")


@dataclass(frozen=True)
class ProposedSafeTx:
    """Result of a successful Safe Transaction Service proposal."""

    safe_address: str
    safe_tx_hash: str  # 0x-prefixed hex
    nonce: int
    api_url: str
    response: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Encoding primitives (deterministic, fully testable in pure Python)
# ---------------------------------------------------------------------------


def _require_address(label: str, addr: str) -> None:
    if not isinstance(addr, str) or not addr.startswith("0x") or len(addr) != 42:
        raise SafeError(f"{label} must be a 0x-prefixed 20-byte hex address; got {addr!r}")
    try:
        int(addr, 16)
    except ValueError as exc:
        raise SafeError(f"{label} is not valid hex: {addr!r}") from exc


def _uint256(value: int) -> bytes:
    if value < 0 or value.bit_length() > 256:
        raise SafeError(f"uint256 out of range: {value}")
    return value.to_bytes(32, "big")


def _address_word(addr: str) -> bytes:
    """ABI-encode an address as a 32-byte left-padded word."""
    return bytes(12) + bytes.fromhex(addr[2:])


def encode_domain_separator_input(chain_id: int, safe_address: str) -> bytes:
    """abi.encode(DOMAIN_SEPARATOR_TYPEHASH, chainId, this) — input to keccak."""
    _require_address("safe_address", safe_address)
    return DOMAIN_SEPARATOR_TYPEHASH + _uint256(chain_id) + _address_word(safe_address)


def domain_separator(chain_id: int, safe_address: str, keccak: KeccakFn) -> bytes:
    return keccak(encode_domain_separator_input(chain_id, safe_address))


def encode_safe_tx_struct_input(safe_tx: SafeTx, data_hash: bytes) -> bytes:
    """abi.encode of the SafeTx struct fields per SAFE_TX_TYPEHASH order."""
    if len(data_hash) != 32:
        raise SafeError(f"data_hash must be 32 bytes; got {len(data_hash)}")
    return (
        SAFE_TX_TYPEHASH
        + _address_word(safe_tx.to)
        + _uint256(safe_tx.value)
        + data_hash
        + _uint256(safe_tx.operation)
        + _uint256(safe_tx.safe_tx_gas)
        + _uint256(safe_tx.base_gas)
        + _uint256(safe_tx.gas_price)
        + _address_word(safe_tx.gas_token)
        + _address_word(safe_tx.refund_receiver)
        + _uint256(safe_tx.nonce)
    )


def safe_tx_hash(
    safe_tx: SafeTx,
    *,
    chain_id: int,
    safe_address: str,
    keccak: KeccakFn,
) -> bytes:
    """Compute the EIP-712 Safe transaction hash a cosigner is asked to sign.

    Equivalent to ``Safe.getTransactionHash(...)`` on-chain.
    """

    data_hash = keccak(safe_tx.data)
    struct_hash = keccak(encode_safe_tx_struct_input(safe_tx, data_hash))
    sep = domain_separator(chain_id, safe_address, keccak)
    # EIP-712 envelope: 0x19 0x01 || domainSeparator || structHash
    return keccak(b"\x19\x01" + sep + struct_hash)


# ---------------------------------------------------------------------------
# Keccak default factory (Foundry cast)
# ---------------------------------------------------------------------------


def make_cast_keccak(run_foundry: Callable[[list[str]], Any]) -> KeccakFn:
    """Produce a keccak callable that delegates to Foundry's ``cast keccak``.

    ``run_foundry`` is the project's existing ``BaseEvmService._run_foundry``
    bound method; it returns a ``CommandResult`` with a ``stdout`` attribute.
    Reusing it gives Windows/WSL fallback for free.
    """

    def keccak(payload: bytes) -> bytes:
        hex_in = "0x" + payload.hex()
        result = run_foundry(["cast", "keccak", hex_in])
        out = (getattr(result, "stdout", "") or "").strip()
        # ``cast keccak`` prints a single 0x-prefixed 32-byte hash on stdout.
        line = out.splitlines()[-1].strip() if out else ""
        if not line.startswith("0x") or len(line) != 66:
            raise SafeError(f"unexpected cast keccak output: {out!r}")
        return bytes.fromhex(line[2:])

    return keccak


# ---------------------------------------------------------------------------
# Safe Transaction Service HTTP client
# ---------------------------------------------------------------------------


@dataclass
class SafeTxServiceClient:
    """Thin client for the Safe Transaction Service REST API.

    No signing happens here. ``propose`` accepts an already-computed
    ``safe_tx_hash`` plus the proposer's signature (produced offline by
    ``cast wallet sign`` or the Safe app) and POSTs the multisig transaction
    so other cosigners can review and approve through the Safe app.
    """

    network: str
    api_base: str = ""

    def __post_init__(self) -> None:
        if not self.api_base:
            try:
                self.api_base = SAFE_TX_SERVICE_URLS[self.network]
            except KeyError as exc:
                raise SafeError(
                    f"no Safe Transaction Service URL pinned for network {self.network!r}"
                ) from exc

    def propose(
        self,
        *,
        safe_address: str,
        safe_tx: SafeTx,
        safe_tx_hash_hex: str,
        sender: str,
        signature: str,
        origin: str | None = "xion-ops/safe.py",
        timeout_seconds: int = 30,
    ) -> ProposedSafeTx:
        """POST /api/v1/safes/{address}/multisig-transactions/.

        The Safe Transaction Service requires the proposer to be a Safe owner
        and the signature to cover ``safe_tx_hash_hex``. The service rejects
        bad sigs, so this method's success is meaningful evidence that the
        encoded payload matches what was signed.
        """

        _require_address("safe_address", safe_address)
        _require_address("sender", sender)
        if not safe_tx_hash_hex.startswith("0x") or len(safe_tx_hash_hex) != 66:
            raise SafeError(f"safe_tx_hash_hex must be 0x-prefixed 32-byte hex; got {safe_tx_hash_hex!r}")
        if not signature.startswith("0x"):
            raise SafeError("signature must be 0x-prefixed hex")

        body: dict[str, Any] = {
            "to": safe_tx.to,
            "value": str(safe_tx.value),
            "data": "0x" + safe_tx.data.hex(),
            "operation": safe_tx.operation,
            "gasToken": safe_tx.gas_token,
            "safeTxGas": str(safe_tx.safe_tx_gas),
            "baseGas": str(safe_tx.base_gas),
            "gasPrice": str(safe_tx.gas_price),
            "refundReceiver": safe_tx.refund_receiver,
            "nonce": safe_tx.nonce,
            "contractTransactionHash": safe_tx_hash_hex,
            "sender": sender,
            "signature": signature,
        }
        if origin:
            body["origin"] = origin

        url = f"{self.api_base}/api/v1/safes/{safe_address}/multisig-transactions/"
        request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "xion-ops-safe/0.1",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8") or "{}"
                payload = json.loads(raw) if raw.strip() else {}
        except HTTPError as exc:  # 4xx/5xx
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            raise SafeError(f"Safe Transaction Service rejected proposal ({exc.code}): {detail}") from exc
        except URLError as exc:
            raise SafeError(f"Safe Transaction Service unreachable: {exc}") from exc

        return ProposedSafeTx(
            safe_address=safe_address,
            safe_tx_hash=safe_tx_hash_hex,
            nonce=safe_tx.nonce,
            api_url=url,
            response=payload,
        )

    def confirm(
        self,
        *,
        safe_tx_hash_hex: str,
        signature: str,
        timeout_seconds: int = 30,
    ) -> Mapping[str, Any]:
        """POST /api/v1/multisig-transactions/{safe_tx_hash}/confirmations/.

        Adds a cosigner signature to an already-proposed Safe transaction.
        The Safe Transaction Service verifies the signature recovers to one of
        the Safe's owners; bad sigs are rejected with HTTP 422. Threshold is
        reached when enough valid confirmations accumulate.

        This is the *cosigner*-side endpoint — strictly distinct from
        :py:meth:`propose` (which both creates the proposal and contributes
        the proposer's first signature).
        """

        if not safe_tx_hash_hex.startswith("0x") or len(safe_tx_hash_hex) != 66:
            raise SafeError(f"safe_tx_hash_hex must be 0x-prefixed 32-byte hex; got {safe_tx_hash_hex!r}")
        if not signature.startswith("0x"):
            raise SafeError("signature must be 0x-prefixed hex")

        url = f"{self.api_base}/api/v1/multisig-transactions/{safe_tx_hash_hex}/confirmations/"
        request = Request(
            url,
            data=json.dumps({"signature": signature}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "xion-ops-safe/0.1",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8") or "{}"
                return json.loads(raw) if raw.strip() else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            raise SafeError(f"Safe Transaction Service rejected confirmation ({exc.code}): {detail}") from exc
        except URLError as exc:
            raise SafeError(f"Safe Transaction Service unreachable: {exc}") from exc

    def fetch_next_nonce(self, safe_address: str, *, timeout_seconds: int = 15) -> int:
        """Return the next pending nonce for ``safe_address`` from the service.

        Falls back to the on-chain ``nonce()`` only if the operator has reason
        to bypass the service; this method is the recommended path because the
        service tracks queued-but-unexecuted proposals.
        """

        _require_address("safe_address", safe_address)
        url = f"{self.api_base}/api/v1/safes/{safe_address}/"
        try:
            with urlopen(url, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError) as exc:
            raise SafeError(f"Safe Transaction Service unreachable for nonce lookup: {exc}") from exc
        nonce = payload.get("nonce")
        if isinstance(nonce, int):
            return nonce
        if isinstance(nonce, str):
            try:
                return int(nonce)
            except ValueError as exc:
                raise SafeError(f"non-integer nonce string in service response: {payload!r}") from exc
        raise SafeError(f"unexpected nonce shape in service response: {payload!r}")
