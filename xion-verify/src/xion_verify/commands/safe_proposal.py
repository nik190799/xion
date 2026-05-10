"""Verify a Safe multisig proposal's call data and EIP-712 hash before signing.

The Safe Transaction Service stores proposals as field-bag dictionaries plus
a ``contractTransactionHash``. Cosigners are normally asked to trust that hash
when they click Approve in the Safe app. This verifier independently
recomputes the EIP-712 SafeTx hash from the stored fields and compares it to
the service's claim, optionally also checking call data / target byte-equality
against operator-declared expectations.

Two modes:

* ``--prep <file>``: offline mode. Reads the JSON produced by
  ``xion_ops base-evm safe-prepare`` (or any structurally equivalent file with
  ``safe_tx_hash``, ``chain_id``, ``safe_address``, and ``tx`` keys) and
  reverifies the hash without touching the network. Useful for the proposer
  to confirm their own payload before signing, and for an air-gapped reviewer.
* ``--safe-address`` + ``--network`` + (``--nonce`` | ``--safe-tx-hash``):
  online mode. Pulls the queued proposal from the Safe Transaction Service
  and verifies it. Useful for cosigners before they click Approve.

Closure verifier for ``KW-OPS-001``: pairs with
``xion_ops.services.base_evm.safe_propose_tx`` so the proposer's payload and
every cosigner's review converge on byte-identical evidence.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


def _normalize_address(addr: str) -> str:
    return addr.lower()


def _hex_to_bytes(payload: str, label: str) -> bytes:
    if not isinstance(payload, str) or not payload.startswith("0x"):
        raise click.ClickException(f"{label} must be 0x-prefixed hex; got {payload!r}")
    try:
        return bytes.fromhex(payload[2:])
    except ValueError as exc:
        raise click.ClickException(f"{label} is not valid hex: {exc}") from exc


def _run_cast_keccak(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ``cast keccak`` with the same WSL fallback xion_ops uses on Windows.

    Mirrors ``xion_ops.services.base_evm.BaseEvmService._run_foundry`` so a
    Windows operator who has Foundry only inside WSL still gets a working
    verifier.
    """

    cast = shutil.which("cast")
    if cast:
        return subprocess.run([cast, *args[1:]], check=False, capture_output=True, text=True)
    if os.name != "nt":
        raise click.ClickException(
            "cast (Foundry) is not on PATH — install Foundry to run "
            "the EIP-712 hash verifier."
        )
    rendered = " ".join(_wsl_quote(part) for part in args)
    return subprocess.run(
        [
            "wsl",
            "bash",
            "-lc",
            f'export PATH="$HOME/.foundry/bin:$PATH"; {rendered}',
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _wsl_quote(part: str) -> str:
    if not part or any(c in part for c in (" ", '"', "'", "$", "`", "\\")):
        return "'" + part.replace("'", "'\"'\"'") + "'"
    return part


def _cast_keccak(payload: bytes) -> bytes:
    completed = _run_cast_keccak(["cast", "keccak", "0x" + payload.hex()])
    if completed.returncode != 0:
        raise click.ClickException(
            f"cast keccak failed (rc={completed.returncode}): {completed.stderr.strip()}"
        )
    line = (completed.stdout or "").strip().splitlines()[-1].strip()
    if not line.startswith("0x") or len(line) != 66:
        raise click.ClickException(f"unexpected cast keccak output: {completed.stdout!r}")
    return bytes.fromhex(line[2:])


def _recompute_safe_tx_hash(
    *,
    chain_id: int,
    safe_address: str,
    tx_fields: dict[str, Any],
) -> str:
    from xion_ops.services.safe import (
        SafeTx,
        encode_domain_separator_input,
        encode_safe_tx_struct_input,
        safe_tx_hash,
    )

    data_bytes = _hex_to_bytes(str(tx_fields.get("data", "0x")), "tx.data")
    tx = SafeTx(
        to=str(tx_fields["to"]),
        value=int(str(tx_fields.get("value", "0"))),
        data=data_bytes,
        operation=int(tx_fields.get("operation", 0)),
        safe_tx_gas=int(str(tx_fields.get("safeTxGas", "0"))),
        base_gas=int(str(tx_fields.get("baseGas", "0"))),
        gas_price=int(str(tx_fields.get("gasPrice", "0"))),
        gas_token=str(tx_fields.get("gasToken", "0x" + "00" * 20)),
        refund_receiver=str(tx_fields.get("refundReceiver", "0x" + "00" * 20)),
        nonce=int(tx_fields["nonce"]),
    )
    # Sanity: encode_*_input never raises for a well-formed SafeTx; their
    # presence in the import keeps the auditor's eye on the same surface that
    # safe.py exposes.
    _ = encode_domain_separator_input(chain_id, safe_address)
    _ = encode_safe_tx_struct_input(tx, b"\x00" * 32)
    digest = safe_tx_hash(
        tx,
        chain_id=chain_id,
        safe_address=safe_address,
        keccak=_cast_keccak,
    )
    return "0x" + digest.hex()


def _fetch_service_proposal(
    *,
    network: str,
    safe_address: str,
    nonce: int | None,
    safe_tx_hash_hex: str | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    from xion_ops.services.safe import SAFE_TX_SERVICE_URLS

    if network not in SAFE_TX_SERVICE_URLS:
        raise click.ClickException(f"no Safe Transaction Service URL pinned for network {network!r}")
    base = SAFE_TX_SERVICE_URLS[network]

    if safe_tx_hash_hex:
        url = f"{base}/api/v1/multisig-transactions/{safe_tx_hash_hex}/"
    elif nonce is not None:
        url = (
            f"{base}/api/v1/safes/{safe_address}/multisig-transactions/"
            f"?nonce={nonce}&ordering=-modified"
        )
    else:
        raise click.ClickException("provide --nonce or --safe-tx-hash")

    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise click.ClickException(f"Safe Transaction Service unreachable: {exc}") from exc

    # The /multisig-transactions/{hash}/ endpoint returns a single object;
    # the /safes/{address}/multisig-transactions/?nonce= endpoint returns a
    # paginated list. Normalize.
    if "results" in payload:
        results = payload["results"] or []
        if not results:
            raise click.ClickException(
                f"No proposal found for safe={safe_address} nonce={nonce}"
            )
        return results[0]
    return payload


@click.command(
    name="safe-proposal",
    help=(
        "Verify a Safe multisig proposal's EIP-712 hash and call data. "
        "Use --prep for offline pre-sign verification or --safe-address + "
        "--network + (--nonce | --safe-tx-hash) to fetch a queued proposal."
    ),
)
@click.option("--prep", "prep_path", type=click.Path(path_type=Path), default=None, help="Offline: path to a JSON prep file produced by xion_ops base-evm safe-prepare.")
@click.option("--safe-address", default=None, help="Safe contract address (online mode).")
@click.option("--network", default=None, help="Network slug (base, base-mainnet, base-sepolia).")
@click.option("--nonce", type=int, default=None, help="Safe nonce of the queued proposal (online mode).")
@click.option("--safe-tx-hash", "safe_tx_hash_arg", default=None, help="Specific safeTxHash to fetch (online mode).")
@click.option("--expected-to", default=None, help="Optional: assert the inner call target address.")
@click.option("--expected-call-data", default=None, help="Optional: assert the inner call data (0x-prefixed hex).")
@click.option("--expected-value", type=int, default=None, help="Optional: assert the inner ETH value (wei).")
@click.option("--timeout-seconds", type=int, default=20)
def safe_proposal(
    prep_path: Path | None,
    safe_address: str | None,
    network: str | None,
    nonce: int | None,
    safe_tx_hash_arg: str | None,
    expected_to: str | None,
    expected_call_data: str | None,
    expected_value: int | None,
    timeout_seconds: int,
) -> None:
    if prep_path is None and (safe_address is None or network is None):
        click.echo(
            "safe-proposal: NOT_YET_SEALED: provide either --prep <file> for offline mode, "
            "or --safe-address + --network (+ --nonce or --safe-tx-hash) for online mode.",
            err=True,
        )
        raise SystemExit(NOT_YET_SEALED)

    try:
        if prep_path is not None:
            try:
                prep = json.loads(prep_path.read_text(encoding="utf-8"))
            except Exception as exc:
                click.echo(f"safe-proposal: FAIL: cannot read prep {prep_path}: {exc}", err=True)
                raise SystemExit(FAIL) from exc
            chain_id = int(prep["chain_id"])
            safe_addr = str(prep["safe_address"])
            tx_fields = dict(prep["tx"])
            claimed_hash = str(prep["safe_tx_hash"]).lower()
            source = f"prep file {prep_path}"
        else:
            assert safe_address is not None and network is not None
            from xion_ops.services.safe import CHAIN_IDS

            if network not in CHAIN_IDS:
                click.echo(f"safe-proposal: FAIL: unknown network {network!r}", err=True)
                raise SystemExit(FAIL)
            chain_id = CHAIN_IDS[network]
            safe_addr = safe_address
            payload = _fetch_service_proposal(
                network=network,
                safe_address=safe_address,
                nonce=nonce,
                safe_tx_hash_hex=safe_tx_hash_arg,
                timeout_seconds=timeout_seconds,
            )
            # Service field names match the SafeTx encoding inputs exactly.
            tx_fields = {
                "to": payload["to"],
                "value": payload.get("value", "0"),
                "data": payload.get("data") or "0x",
                "operation": payload.get("operation", 0),
                "safeTxGas": payload.get("safeTxGas", "0"),
                "baseGas": payload.get("baseGas", "0"),
                "gasPrice": payload.get("gasPrice", "0"),
                "gasToken": payload.get("gasToken", "0x" + "00" * 20),
                "refundReceiver": payload.get("refundReceiver", "0x" + "00" * 20),
                "nonce": payload["nonce"],
            }
            claimed_hash = str(
                payload.get("contractTransactionHash") or payload.get("safeTxHash") or ""
            ).lower()
            if not claimed_hash:
                click.echo("safe-proposal: FAIL: service response has no contractTransactionHash", err=True)
                raise SystemExit(FAIL)
            source = f"Safe Transaction Service ({network})"

        recomputed = _recompute_safe_tx_hash(
            chain_id=chain_id, safe_address=safe_addr, tx_fields=tx_fields
        ).lower()

        click.echo(f"safe-proposal: source = {source}")
        click.echo(f"safe-proposal: safe   = {safe_addr}")
        click.echo(f"safe-proposal: chain  = {chain_id}")
        click.echo(f"safe-proposal: nonce  = {tx_fields['nonce']}")
        click.echo(f"safe-proposal: to     = {tx_fields['to']}")
        click.echo(f"safe-proposal: data   = {tx_fields['data']}")
        click.echo(f"safe-proposal: value  = {tx_fields['value']}")
        click.echo(f"safe-proposal: claim  = {claimed_hash}")
        click.echo(f"safe-proposal: recom  = {recomputed}")

        failures: list[str] = []
        if claimed_hash != recomputed:
            failures.append(
                f"hash mismatch: source claims {claimed_hash}, recomputed {recomputed}"
            )
        if expected_to is not None and _normalize_address(str(tx_fields["to"])) != _normalize_address(expected_to):
            failures.append(
                f"to mismatch: proposal targets {tx_fields['to']}, expected {expected_to}"
            )
        if expected_call_data is not None:
            if str(tx_fields["data"]).lower() != expected_call_data.lower():
                failures.append(
                    f"call data mismatch: proposal carries {tx_fields['data']}, "
                    f"expected {expected_call_data}"
                )
        if expected_value is not None and int(str(tx_fields["value"])) != expected_value:
            failures.append(
                f"value mismatch: proposal sends {tx_fields['value']}, expected {expected_value}"
            )

        if failures:
            for line in failures:
                click.echo(f"safe-proposal: FAIL: {line}", err=True)
            raise SystemExit(FAIL)

        click.echo("safe-proposal: OK")
        raise SystemExit(OK)

    except SystemExit:
        raise
    except click.ClickException as exc:
        click.echo(f"safe-proposal: FAIL: {exc.message}", err=True)
        raise SystemExit(FAIL) from exc
    except Exception as exc:  # noqa: BLE001 — surface as FAIL with detail
        click.echo(f"safe-proposal: FAIL: {exc}", err=True)
        raise SystemExit(FAIL) from exc
