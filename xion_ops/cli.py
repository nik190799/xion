"""Click CLI for xion-ops."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

import click

from xion_ops.env import load_repo_env, upsert_repo_env
from xion_ops.registry import get_deployer, get_service, service_names
from xion_ops.services.chutes import DEFAULT_CHUTE_REF
from xion_ops.types import DeployContext


def _read_chutes_bearer_file(path: Path) -> str:
    """First non-empty line as raw token, or parse ``CHUTES_API_KEY=value`` / ``XION_CHUTES_API_KEY=value``."""

    raw = path.read_text(encoding="utf-8").strip().splitlines()
    for line in raw:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        upper = s.upper()
        if upper.startswith("CHUTES_API_KEY="):
            return s.split("=", 1)[1].strip().strip('"').strip("'")
        if upper.startswith("XION_CHUTES_API_KEY="):
            return s.split("=", 1)[1].strip().strip('"').strip("'")
        return s.strip().strip('"').strip("'")
    raise click.BadParameter(f"empty or missing token lines: {path}")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main() -> None:
    """Operator automation for Xion services."""

    load_repo_env(Path("."))


@main.command(name="balances")
@click.option("--service", "service_name", type=click.Choice(service_names()), default=None)
@click.option("--json-output", is_flag=True)
def balances_cmd(service_name: str | None, json_output: bool) -> None:
    """Check every declared funding target."""

    reports = balances(service_name)
    if json_output:
        click.echo(json.dumps([_report_to_dict(report) for report in reports], indent=2, sort_keys=True))
    else:
        render_balance_table(reports)
    if any(report.status != "ok" for report in reports):
        raise click.exceptions.Exit(1)


def balances(service_name: str | None = None, *, repo_root: Path | str = "."):
    names = [service_name] if service_name else service_names()
    reports = []
    for name in names:
        reports.extend(get_service(name, repo_root=repo_root).balances())
    return reports


def render_balance_table(reports) -> None:
    click.echo("service\twallet\tnetwork\tbalance\ttarget\tstatus")
    for report in reports:
        balance = "unknown" if report.balance is None else f"{report.balance:g}"
        click.echo(
            f"{report.wallet.service}\t{report.wallet.id}\t{report.wallet.network}\t"
            f"{balance} {report.wallet.currency}\t{report.wallet.target:g}\t{report.status}"
        )


@main.group(name="akash")
def akash_group() -> None:
    """Akash operations."""


@akash_group.command(name="preflight")
def akash_preflight() -> None:
    render_balance_table(get_service("akash").balances())


@akash_group.command(name="cert-ensure")
def akash_cert_ensure() -> None:
    """Run client cert generate + publish when none is on-chain (idempotent)."""

    get_service("akash").ensure_client_cert_published()  # type: ignore[attr-defined]
    click.echo("akash cert-ensure: OK")


@akash_group.command(name="deployment-list")
@click.option("--state", default=None, help="Filter: active | closed")
@click.option("--json-output", is_flag=True)
def akash_deployment_list(state: str | None, json_output: bool) -> None:
    svc = get_service("akash")
    payload = svc.query_deployment_list(state=state)  # type: ignore[attr-defined]
    click.echo(json.dumps(payload, indent=2 if json_output else None, sort_keys=True))


@akash_group.command(name="deployment-get")
@click.argument("dseq")
@click.option("--json-output", is_flag=True)
def akash_deployment_get(dseq: str, json_output: bool) -> None:
    svc = get_service("akash")
    payload = svc.query_deployment_get(dseq)  # type: ignore[attr-defined]
    click.echo(json.dumps(payload, indent=2 if json_output else None, sort_keys=True))


@akash_group.command(name="lease-list")
@click.option("--dseq", default=None)
@click.option("--state", default=None)
@click.option("--json-output", is_flag=True)
def akash_lease_list(dseq: str | None, state: str | None, json_output: bool) -> None:
    svc = get_service("akash")
    payload = svc.query_market_lease_list(dseq=dseq, state=state)  # type: ignore[attr-defined]
    click.echo(json.dumps(payload, indent=2 if json_output else None, sort_keys=True))


@akash_group.command(name="tx")
@click.argument("tx_hash")
@click.option("--json-output", is_flag=True)
def akash_tx_lookup(tx_hash: str, json_output: bool) -> None:
    svc = get_service("akash")
    payload = svc.query_tx(tx_hash)  # type: ignore[attr-defined]
    click.echo(json.dumps(payload, indent=2 if json_output else None, sort_keys=True))


@akash_group.command(name="deployment-update")
@click.argument("dseq")
@click.argument("sdl_path", type=click.Path(exists=True, dir_okay=False))
def akash_deployment_update(dseq: str, sdl_path: str) -> None:
    svc = get_service("akash")
    result = svc.update_deployment(sdl_path, dseq)  # type: ignore[attr-defined]
    click.echo(result.stdout)


@akash_group.command(name="send-manifest")
@click.argument("sdl_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("dseq")
@click.argument("provider")
def akash_send_manifest(sdl_path: str, dseq: str, provider: str) -> None:
    svc = get_service("akash")
    result = svc.send_manifest(sdl_path, dseq, provider)  # type: ignore[attr-defined]
    click.echo(result.stdout)
    if result.returncode != 0:
        raise click.exceptions.Exit(result.returncode)


@akash_group.command(name="mint-act")
@click.argument("uakt_amount", type=int)
@click.option(
    "--wait-ledger",
    is_flag=True,
    help="After mint tx, poll until BME ledger rows are ledger_record_status_executed.",
)
def akash_mint_act(uakt_amount: int, wait_ledger: bool) -> None:
    service = get_service("akash")
    result = service.mint_act(uakt_amount)  # type: ignore[attr-defined]
    click.echo(result.stdout)
    if wait_ledger:
        ok = service.wait_for_ledger_executed()  # type: ignore[attr-defined]
        click.echo(json.dumps({"bme_ledger_all_executed": ok}, indent=2, sort_keys=True))
        if not ok:
            raise click.exceptions.Exit(1)


@akash_group.command(name="deploy")
@click.option("--sdl-path", default="infra/akash/relay-deployment.yaml")
@click.option("--prefer-provider", default=None)
@click.option("--exclude-provider", multiple=True)
def akash_deploy(sdl_path: str, prefer_provider: str | None, exclude_provider: tuple[str, ...]) -> None:
    service = get_service("akash")
    result = service.deploy_relay(  # type: ignore[attr-defined]
        sdl_path,
        prefer_provider=prefer_provider,
        rejected_providers=set(exclude_provider),
    )
    click.echo(json.dumps(result.__dict__, indent=2, sort_keys=True))
    if not result.ok:
        raise click.exceptions.Exit(1)


@akash_group.command(name="health-smoke")
@click.argument("url")
def akash_health_smoke(url: str) -> None:
    ok = get_service("akash").health_smoke(url)  # type: ignore[attr-defined]
    click.echo("ok" if ok else "failed")
    if not ok:
        raise click.exceptions.Exit(1)


@akash_group.command(name="lease-status")
@click.argument("dseq")
@click.argument("provider")
@click.option("--service-name", default="xion-relay", show_default=True)
def akash_lease_status(dseq: str, provider: str, service_name: str) -> None:
    service = get_service("akash")
    status = service.lease_status(dseq, provider, service_name=service_name)  # type: ignore[attr-defined]
    click.echo(json.dumps(status.raw, indent=2, sort_keys=True))


@akash_group.command(name="lease-logs")
@click.argument("dseq")
@click.argument("provider")
@click.option("--service-name", default="xion-relay")
@click.option("--tail", default=120, type=int)
def akash_lease_logs(dseq: str, provider: str, service_name: str, tail: int) -> None:
    service = get_service("akash")
    click.echo(service.lease_logs(dseq, provider, service=service_name, tail=tail))  # type: ignore[attr-defined]


@akash_group.command(name="close")
@click.argument("dseq")
def akash_close(dseq: str) -> None:
    service = get_service("akash")
    click.echo(service.close_deployment(dseq).stdout)  # type: ignore[attr-defined]


@main.group(name="arweave")
def arweave_group() -> None:
    """Arweave operations."""


@arweave_group.command(name="balances")
def arweave_balances() -> None:
    render_balance_table(get_service("arweave").balances())


@arweave_group.command(name="publish-file")
@click.argument("path")
def arweave_publish_file(path: str) -> None:
    tx = get_service("arweave").publish_file(path)  # type: ignore[attr-defined]
    click.echo(json.dumps(tx.__dict__, indent=2, sort_keys=True))


@arweave_group.command(name="publish-relay-registry")
@click.argument("path", required=False)
def arweave_publish_relay_registry(path: str | None) -> None:
    tx = get_service("arweave").publish_relay_registry(path or "ledgers/RELAY_REGISTRY.json")  # type: ignore[attr-defined]
    click.echo(json.dumps(tx.__dict__, indent=2, sort_keys=True))


@arweave_group.command(name="publish-treasury-audit")
@click.argument("path", required=False)
def arweave_publish_treasury_audit(path: str | None) -> None:
    tx = get_service("arweave").publish_treasury_audit(path or "docs/audits/treasury-2026-report.md")  # type: ignore[attr-defined]
    click.echo(json.dumps(tx.__dict__, indent=2, sort_keys=True))


@arweave_group.command(name="publish-genesis-artifact")
@click.argument("path", required=False)
def arweave_publish_genesis(path: str | None) -> None:
    tx = get_service("arweave").publish_genesis_artifact(path or "genesis/GENESIS_ARTIFACT.md")  # type: ignore[attr-defined]
    click.echo(json.dumps(tx.__dict__, indent=2, sort_keys=True))


@main.group(name="chutes")
def chutes_group() -> None:
    """Chutes operations."""


@chutes_group.command(name="balances")
def chutes_balances() -> None:
    render_balance_table(get_service("chutes").balances())


@chutes_group.command(name="health")
@click.argument("url", required=False)
def chutes_health(url: str | None) -> None:
    health = get_service("chutes").health(url)  # type: ignore[arg-type]
    click.echo(json.dumps(health.__dict__, indent=2, sort_keys=True))


@chutes_group.command(name="warmup")
@click.argument("url", required=False)
@click.option(
    "--bearer-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Bearer token file (same as verify-cords).",
)
@click.option("--max-wait", type=float, default=None, help="Cap in seconds (default env or 600).")
@click.option("--interval", type=float, default=None, help="Seconds between probes (default env or 15).")
@click.option(
    "--platform-slug",
    default=None,
    help="Runs `chutes warmup <slug>` once before polling (cold miners); overrides env slug.",
)
@click.option("--allow-failure", is_flag=True, help="Always exit 0 (for scripted JSON scraping).")
def chutes_warmup(
    url: str | None,
    bearer_file: Path | None,
    max_wait: float | None,
    interval: float | None,
    platform_slug: str | None,
    allow_failure: bool,
) -> None:
    token = _read_chutes_bearer_file(bearer_file) if bearer_file else None
    if token:
        os.environ.setdefault("CHUTES_API_KEY", token)
    svc = get_service("chutes")
    raw_slug = platform_slug.strip() if isinstance(platform_slug, str) else None
    result = svc.warmup_until_cords_green(  # type: ignore[attr-defined]
        url,
        max_wait_seconds=max_wait,
        interval_seconds=interval,
        platform_warmup_slug=raw_slug or None,
    )
    click.echo(json.dumps(asdict(result), indent=2, sort_keys=True, default=str))
    if not result.ok and not allow_failure:
        raise click.exceptions.Exit(1)


@chutes_group.command(name="verify-cords")
@click.argument("url", required=False)
@click.option(
    "--bearer-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional path to first-line Bearer token OR .env-format CHUTES_API_KEY=... "
    "(for hosts where repo `.env` is absent from the operator shell).",
)
@click.option(
    "--allow-failure",
    is_flag=True,
    help="Do not exit non-zero when cords fail (default: exit 1 unless each path returns 2xx).",
)
def chutes_verify_cords(url: str | None, bearer_file: Path | None, allow_failure: bool) -> None:
    token = _read_chutes_bearer_file(bearer_file) if bearer_file else None
    if token:
        os.environ.setdefault("CHUTES_API_KEY", token)
    result = get_service("chutes").verify_cords(url)  # type: ignore[attr-defined]
    click.echo(json.dumps(asdict(result), indent=2, sort_keys=True, default=str))
    if not result.ok and not allow_failure:
        raise click.exceptions.Exit(1)


@chutes_group.command(name="verify-import")
@click.argument("module_path", default="xion_relay_chute.py")
def chutes_verify_import(module_path: str) -> None:
    result = get_service("chutes").verify_import(module_path)  # type: ignore[attr-defined]
    click.echo(json.dumps(result.__dict__, indent=2, sort_keys=True))


@chutes_group.command(name="chutes-get")
@click.argument("name_or_id")
@click.option("--json-output", is_flag=True, help="Print stdout/stderr as JSON (captures upstream Rich/JSON mix).")
def chutes_managed_get_cmd(name_or_id: str, json_output: bool) -> None:
    """Run ``chutes chutes get <name_or_id>`` (miner/instance visibility)."""

    svc = get_service("chutes")
    result = svc.chutes_chutes_get(name_or_id)  # type: ignore[attr-defined]
    payload = {"ok": result.ok, "id": result.id, **(result.details or {})}
    if json_output:
        click.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        click.echo(payload.get("stdout") or "")
        if payload.get("stderr"):
            click.echo(payload["stderr"], err=True)
    if not result.ok:
        raise click.exceptions.Exit(1)


@chutes_group.command(name="images-list")
@click.option("--limit", default=25, show_default=True, type=int)
@click.option("--page", default=0, show_default=True, type=int)
@click.option("--json-output", is_flag=True)
def chutes_images_list_cmd(limit: int, page: int, json_output: bool) -> None:
    """Run ``chutes images list`` (includes recent builds; check image-history quota)."""

    svc = get_service("chutes")
    result = svc.chutes_images_list(limit=limit, page=page)  # type: ignore[attr-defined]
    if json_output:
        click.echo(json.dumps({"ok": result.ok, **(result.details or {})}, indent=2, sort_keys=True))
    else:
        click.echo((result.details or {}).get("stdout") or "")
        if (result.details or {}).get("stderr"):
            click.echo((result.details or {})["stderr"], err=True)
    if not result.ok:
        raise click.exceptions.Exit(1)


@main.group(name="base-evm")
def base_evm_group() -> None:
    """Base EVM operations."""


@base_evm_group.command(name="balances")
def base_evm_balances() -> None:
    render_balance_table(get_service("base-evm").balances())


@base_evm_group.command(name="wait-for-funding")
@click.argument("address")
@click.argument("target_eth", type=float)
@click.argument("network")
def base_evm_wait(address: str, target_eth: float, network: str) -> None:
    ok = get_service("base-evm").wait_for_funding(address, target_eth, network)  # type: ignore[attr-defined]
    click.echo("ok" if ok else "timeout")
    if not ok:
        raise click.exceptions.Exit(1)


@base_evm_group.command(name="deploy-treasury")
@click.option("--network", default="base-sepolia", show_default=True)
@click.option("--script", default="treasury/script/Deploy.s.sol:DeployTreasury")
def base_evm_deploy_treasury(network: str, script: str) -> None:
    result = get_service("base-evm").deploy_treasury(network, script)  # type: ignore[attr-defined]
    click.echo(json.dumps(asdict(result), indent=2, sort_keys=True, default=str))
    if not result.ok:
        raise click.exceptions.Exit(code=1)


@base_evm_group.command("preflight-treasury")
@click.option("--network", default="base-sepolia", show_default=True)
def base_evm_preflight_treasury(network: str) -> None:
    """Fail fast when deploy signer or constructor env is missing (before forge broadcast)."""

    issues = get_service("base-evm").treasury_deploy_preflight_issues(network)  # type: ignore[attr-defined]
    for line in issues:
        click.echo(f"ISSUE: {line}", err=True)
    if issues:
        raise click.exceptions.Exit(code=1)
    click.echo(f"base-evm preflight-treasury ({network}): OK")


@base_evm_group.command(name="prepare-sepolia-env")
def base_evm_prepare_sepolia_env() -> None:
    deployer = "0xEBDDDf598b5b53C91ff185501d7b182ae5d6B88A"
    upsert_repo_env(
        Path("."),
        {
            "XION_TREASURY_GOVERNANCE": deployer,
            "XION_AO_CORE_AUTHORITY": deployer,
            "XION_BRIDGE_CAP_BPS": "1000",
        },
        preserve_existing=False,
    )
    click.echo("base-evm prepare-sepolia-env: OK (non-secret deploy env written)")


@base_evm_group.command(name="pin-deployment")
@click.option("--manifest", default="genesis/TREASURY_VAULTS.json")
@click.option("--address", required=True)
@click.option("--tx", "tx_hash", required=True)
@click.option("--block", "block_number", required=True, type=int)
def base_evm_pin_deployment(manifest: str, address: str, tx_hash: str, block_number: int) -> None:
    get_service("base-evm").pin_treasury_deployment(  # type: ignore[attr-defined]
        manifest,
        address=address,
        tx=tx_hash,
        block=block_number,
    )
    click.echo("base-evm pin-deployment: OK")


@base_evm_group.command(name="rotation-rehearsal")
@click.option("--network", default="base-sepolia")
@click.option("--master-treasury", required=True)
@click.option("--count", default=3, type=int)
def base_evm_rotation_rehearsal(network: str, master_treasury: str, count: int) -> None:
    rows = get_service("base-evm").rotation_rehearsal(  # type: ignore[attr-defined]
        network=network,
        master_treasury=master_treasury,
        count=count,
    )
    click.echo(json.dumps(rows, indent=2, sort_keys=True))


@base_evm_group.command(name="deploy-vault")
@click.option("--network", default="base")
@click.argument("cast_args", nargs=-1)
def base_evm_deploy_vault(network: str, cast_args: tuple[str, ...]) -> None:
    result = get_service("base-evm").deploy_vault(network, *cast_args)  # type: ignore[attr-defined]
    click.echo(json.dumps(result.__dict__, indent=2, sort_keys=True))


@base_evm_group.command(name="cast-send")
@click.option("--network", default="base")
@click.argument("cast_args", nargs=-1)
def base_evm_cast_send(network: str, cast_args: tuple[str, ...]) -> None:
    click.echo(get_service("base-evm").cast_send(*cast_args, network=network).stdout)  # type: ignore[attr-defined]


@base_evm_group.command(name="cast-call")
@click.option("--network", default="base")
@click.argument("cast_args", nargs=-1)
def base_evm_cast_call(network: str, cast_args: tuple[str, ...]) -> None:
    click.echo(get_service("base-evm").cast_call(*cast_args, network=network).stdout)  # type: ignore[attr-defined]


@base_evm_group.command(name="safe-prepare")
@click.option("--network", required=True, type=click.Choice(["base", "base-mainnet", "base-sepolia"]))
@click.option("--safe-address", required=True, help="Safe contract address.")
@click.option("--to", required=True, help="Inner call target address.")
@click.option("--data", default="0x", help="Inner call data (0x-prefixed hex). Defaults to 0x.")
@click.option("--value", default=0, type=int, help="Inner ETH value (wei).")
@click.option("--operation", default=0, type=click.IntRange(0, 1), help="0=CALL, 1=DELEGATECALL.")
@click.option("--nonce", default=None, type=int, help="Override Safe nonce; default fetches from service.")
@click.option("--out", "out_path", default=None, type=click.Path(),
              help="Optional path to write the prep JSON for cosigners and verifiers.")
def base_evm_safe_prepare(
    network: str,
    safe_address: str,
    to: str,
    data: str,
    value: int,
    operation: int,
    nonce: int | None,
    out_path: str | None,
) -> None:
    """Build a SafeTx and compute its EIP-712 hash without signing.

    Pipe the output to ``cast wallet sign --data -`` (or the Safe app) to
    produce a proposer signature, then pass it to ``safe-propose``.
    """

    if not data.startswith("0x"):
        raise click.ClickException("--data must be 0x-prefixed hex")
    data_bytes = bytes.fromhex(data[2:]) if data != "0x" else b""

    prep = get_service("base-evm").safe_compute_tx_hash(  # type: ignore[attr-defined]
        network=network,
        safe_address=safe_address,
        to=to,
        data=data_bytes,
        value=value,
        operation=operation,
        nonce=nonce,
    )
    rendered = json.dumps(prep, indent=2, sort_keys=True)
    click.echo(rendered)
    if out_path:
        Path(out_path).write_text(rendered + "\n", encoding="utf-8")


@base_evm_group.command(name="safe-propose")
@click.option("--network", required=True, type=click.Choice(["base", "base-mainnet", "base-sepolia"]))
@click.option("--safe-address", required=True)
@click.option("--to", required=True)
@click.option("--data", default="0x")
@click.option("--value", default=0, type=int)
@click.option("--operation", default=0, type=click.IntRange(0, 1))
@click.option("--nonce", default=None, type=int)
@click.option("--sender", required=True, help="Safe owner address proposing the tx (must match the signature).")
@click.option("--signature", required=True, help="0x-prefixed EIP-712 signature over the safeTxHash.")
def base_evm_safe_propose(
    network: str,
    safe_address: str,
    to: str,
    data: str,
    value: int,
    operation: int,
    nonce: int | None,
    sender: str,
    signature: str,
) -> None:
    """Submit a signed SafeTx to the Safe Transaction Service.

    Cosigners review and approve through the Safe app at safe.global.
    """

    if not data.startswith("0x"):
        raise click.ClickException("--data must be 0x-prefixed hex")
    data_bytes = bytes.fromhex(data[2:]) if data != "0x" else b""

    result = get_service("base-evm").safe_propose_tx(  # type: ignore[attr-defined]
        network=network,
        safe_address=safe_address,
        to=to,
        data=data_bytes,
        value=value,
        operation=operation,
        nonce=nonce,
        sender=sender,
        signature=signature,
    )
    click.echo(json.dumps(result.__dict__, indent=2, sort_keys=True, default=str))
    if not result.ok:
        raise click.exceptions.Exit(1)


@base_evm_group.command(name="safe-confirm")
@click.option("--network", required=True, type=click.Choice(["base", "base-mainnet", "base-sepolia"]))
@click.option("--safe-tx-hash", "safe_tx_hash_hex", required=True, help="0x-prefixed safeTxHash of the queued proposal.")
@click.option("--signature", required=True, help="0x-prefixed cosigner ECDSA signature over the safeTxHash (produced via 'cast wallet sign --no-hash').")
def base_evm_safe_confirm(
    network: str,
    safe_tx_hash_hex: str,
    signature: str,
) -> None:
    """Add a cosigner signature to an already-proposed SafeTx.

    Strictly distinct from ``safe-propose``: that one creates the proposal
    plus contributes the proposer's first signature; this one adds an
    additional cosigner signature against an existing proposal so the Safe
    can reach its threshold without going through the Safe app UI.

    Cosigner workflow (paper backup or hot key alike):

        1. cosigner runs `cast wallet sign --no-hash --private-key <pk> <safeTxHash>`
        2. they paste the resulting 0x-signature into `--signature` here
        3. xion_ops base-evm safe-confirm posts it; service rejects bad sigs
    """

    result = get_service("base-evm").safe_confirm_tx(  # type: ignore[attr-defined]
        network=network,
        safe_tx_hash_hex=safe_tx_hash_hex,
        signature=signature,
    )
    click.echo(json.dumps(result.__dict__, indent=2, sort_keys=True, default=str))
    if not result.ok:
        raise click.exceptions.Exit(1)


@base_evm_group.command(name="register-vault")
@click.option("--network", required=True, type=click.Choice(["base", "base-mainnet", "base-sepolia"]))
@click.option("--master-treasury", required=True, help="MasterTreasury contract address.")
@click.option("--chain-id", required=True, type=int, help="Chain ID being registered (e.g. 8453 for Base mainnet).")
@click.option("--vault-address", required=True, help="Per-chain Vault contract address to register.")
@click.option("--safe-address", default=None, help="Required for mainnet (governance Safe). Sepolia uses cast_send via EOA.")
@click.option("--out", "out_path", default=None, type=click.Path(),
              help="On mainnet: write the prep JSON for cosigners and the safe-proposal verifier.")
def base_evm_register_vault(
    network: str,
    master_treasury: str,
    chain_id: int,
    vault_address: str,
    safe_address: str | None,
    out_path: str | None,
) -> None:
    """Register a per-chain Vault on a MasterTreasury via the right authority path.

    Sepolia uses a direct ``cast send`` because the testnet governance is an
    EOA. Mainnet builds a Safe proposal because the Warm Safe is the only
    authorized governance — the operator collects threshold cosigs through
    the Safe app and executes from there.
    """

    svc = get_service("base-evm")

    # Build registerVault(uint256,address) call data deterministically.
    # Selector: keccak("registerVault(uint256,address)")[0:4]. The selector
    # is independent of arguments and is computable offline once; we shell
    # out via cast keccak through the existing safe.make_cast_keccak path
    # so the operator's PATH determines which cast is invoked.
    from xion_ops.services import safe as _safe

    keccak = _safe.make_cast_keccak(svc._run_foundry)  # type: ignore[attr-defined]
    selector = keccak(b"registerVault(uint256,address)")[:4]
    chain_word = chain_id.to_bytes(32, "big")
    if not vault_address.startswith("0x") or len(vault_address) != 42:
        raise click.ClickException("--vault-address must be 0x-prefixed 20-byte hex")
    vault_word = bytes(12) + bytes.fromhex(vault_address[2:])
    call_data = selector + chain_word + vault_word

    if network == "base-sepolia":
        # Direct broadcast through the Sepolia EOA governance.
        result = svc.cast_send(  # type: ignore[attr-defined]
            master_treasury,
            "registerVault(uint256,address)",
            str(chain_id),
            vault_address,
            network=network,
        )
        click.echo(result.stdout)
        return

    # Mainnet: build a Safe proposal payload for cosigner review.
    if not safe_address:
        raise click.ClickException(
            "--safe-address is required on mainnet (governance Safe). "
            "Sepolia uses cast_send via the rehearsal EOA."
        )
    prep = svc.safe_compute_tx_hash(  # type: ignore[attr-defined]
        network=network,
        safe_address=safe_address,
        to=master_treasury,
        data=call_data,
    )
    prep["call_summary"] = {
        "function": "registerVault(uint256,address)",
        "args": [chain_id, vault_address],
        "expected_call_data": "0x" + call_data.hex(),
    }
    rendered = json.dumps(prep, indent=2, sort_keys=True)
    click.echo(rendered)
    if out_path:
        Path(out_path).write_text(rendered + "\n", encoding="utf-8")
    click.echo(
        "\nNext steps:\n"
        f"  1. xion-verify safe-proposal --prep {out_path or '<stdin>'} "
        f"--expected-to {master_treasury} --expected-call-data 0x{call_data.hex()}\n"
        "  2. cast wallet sign --data <prep file or stdin>  # via Cold Root or Warm Safe owner\n"
        "  3. xion_ops base-evm safe-propose --network "
        f"{network} --safe-address {safe_address} --to {master_treasury} "
        f"--data 0x{call_data.hex()} --sender <owner> --signature <0x...>\n"
        "  4. Cosigners review through Safe app and execute when threshold reached.",
        err=True,
    )


@main.group(name="deploy")
def deploy_group() -> None:
    """End-to-end deployment workflows."""


@deploy_group.command(name="relay-akash")
@click.option("--sdl-path", default="infra/akash/relay-deployment.yaml")
@click.option("--prefer-provider", default=None)
@click.option("--exclude-provider", multiple=True, help="Skip these provider addresses during bid selection.")
@click.option(
    "--no-publish-registry",
    is_flag=True,
    help="Skip Arweave relay-registry publish after a successful lease.",
)
def deploy_relay_akash(
    sdl_path: str,
    prefer_provider: str | None,
    exclude_provider: tuple[str, ...],
    no_publish_registry: bool,
) -> None:
    params: dict[str, object] = {
        "sdl_path": sdl_path,
        "publish_registry": not no_publish_registry,
    }
    if prefer_provider:
        params["prefer_provider"] = prefer_provider
    if exclude_provider:
        params["rejected_providers"] = set(exclude_provider)
    _run_deployer("relay-akash", params)


@deploy_group.command(name="relay-chutes")
@click.option(
    "--module-path",
    default=DEFAULT_CHUTE_REF,
    show_default=True,
    help="Chutes ref `module:chute` (e.g. xion_relay_chute:chute); *.py normalized to `:chute`.",
)
@click.option(
    "--build-wait",
    is_flag=True,
    help="Run `chutes build <ref> --wait` before deploy (official Chutes happy path).",
)
@click.option(
    "--accept-fee",
    is_flag=True,
    help="Pass --accept-fee to `chutes deploy` (required for stale metadata on updates).",
)
@click.option(
    "--public",
    is_flag=True,
    help="Pass --public to upstream `chutes build`/`deploy` (requires deploy permissions).",
)
@click.option("--debug", is_flag=True, help="Pass --debug to upstream chutes CLI for build/deploy.")
@click.option("--logo", default=None, help="Optional --logo path for build/deploy.")
@click.option("--config-path", default=None, help="Optional --config-path for upstream chutes CLI.")
@click.option(
    "--include-cwd",
    is_flag=True,
    help="Pass --include-cwd to `chutes build` (only meaningful with --build-wait).",
)
@click.option("--warmup-max-wait", type=float, default=None)
@click.option("--warmup-interval", type=float, default=None)
@click.option(
    "--platform-warmup-slug",
    default=None,
    help="Optional `chutes warmup <slug>` before HTTP polls; overrides XION_CHUTES_WARMUP_SLUG.",
)
@click.option(
    "--no-publish-registry",
    is_flag=True,
    help="Warm and verify cords but skip relay-registry publication.",
)
def deploy_relay_chutes(
    module_path: str,
    build_wait: bool,
    accept_fee: bool,
    public: bool,
    debug: bool,
    logo: str | None,
    config_path: str | None,
    include_cwd: bool,
    warmup_max_wait: float | None,
    warmup_interval: float | None,
    platform_warmup_slug: str | None,
    no_publish_registry: bool,
) -> None:
    params: dict[str, object] = {
        "module_path": module_path,
        "accept_fee": accept_fee,
        "publish_registry": not no_publish_registry,
        "build_wait": build_wait,
        "public": public,
        "debug": debug,
        "include_cwd": include_cwd,
    }
    if logo:
        params["logo"] = logo
    if config_path:
        params["config_path"] = config_path
    if warmup_max_wait is not None:
        params["warmup_max_wait_seconds"] = warmup_max_wait
    if warmup_interval is not None:
        params["warmup_interval_seconds"] = warmup_interval
    if platform_warmup_slug:
        params["platform_warmup_slug"] = platform_warmup_slug
    _run_deployer("relay-chutes", params)


@deploy_group.command(name="base-contracts")
@click.option("--network", default="base-sepolia")
@click.option("--mode", default="full")
def deploy_base_contracts(network: str, mode: str) -> None:
    _run_deployer("base-contracts", {"network": network, "mode": mode})


@main.group(name="registry")
def registry_group() -> None:
    """Relay registry operations."""


@registry_group.command(name="update-akash-row")
@click.option("--endpoint", required=True)
@click.option("--image-tag", required=True)
@click.option("--instance-class", default="cpu-only")
@click.option("--path", "registry_path", default="ledgers/RELAY_REGISTRY.json")
def registry_update_akash_row(endpoint: str, image_tag: str, instance_class: str, registry_path: str) -> None:
    path = Path(registry_path)
    _update_akash_registry_row(path, endpoint=endpoint, image_tag=image_tag, instance_class=instance_class)
    click.echo("registry update-akash-row: OK")


@registry_group.command(name="update-chutes-row")
@click.option("--endpoint", required=True, help="Public HTTPS relay base (*.chutes.ai).")
@click.option("--chute-id", "chute_id", required=True)
@click.option("--image-id", "image_id", required=True)
@click.option("--image-tag", "image_tag", required=True)
@click.option("--instance-id", "instance_id", default="", help="Warm worker/instance id when known.")
@click.option("--relay-id", "relay_id", default="", help="Override relays[1].relay_id.")
@click.option("--service", default="", help='Override relays[1].service (default "xion-relay-chutes").')
@click.option("--path", "registry_path", default="ledgers/RELAY_REGISTRY.json")
def registry_update_chutes_row(
    endpoint: str,
    chute_id: str,
    image_id: str,
    image_tag: str,
    instance_id: str,
    relay_id: str,
    service: str,
    registry_path: str,
) -> None:
    """Patch ``relays[1]`` for substrate ``chutes`` (genesis ordering)."""

    path = Path(registry_path)
    _update_chutes_registry_row(
        path,
        endpoint=endpoint,
        chute_id=chute_id,
        image_id=image_id,
        image_tag=image_tag,
        instance_id=instance_id.strip(),
        relay_id=relay_id.strip(),
        service=service.strip(),
    )
    click.echo("registry update-chutes-row: OK")


def _run_deployer(name: str, params: dict[str, object]) -> None:
    deployer = get_deployer(name)
    record = deployer.run(DeployContext(repo_root=Path("."), params=params))
    click.echo(json.dumps(record.to_dict(), indent=2, sort_keys=True))
    if not record.result.ok or not record.verify.ok:
        raise click.exceptions.Exit(1)


def _update_chutes_registry_row(
    path: Path,
    *,
    endpoint: str,
    chute_id: str,
    image_id: str,
    image_tag: str,
    instance_id: str,
    relay_id: str,
    service: str,
) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or "placeholder" in endpoint.lower():
        raise click.ClickException(f"invalid Chutes endpoint for registry: {endpoint}")
    payload_obj = json.loads(path.read_text(encoding="utf-8"))
    relays = payload_obj.get("relays")
    if not isinstance(relays, list) or len(relays) < 2 or not isinstance(relays[1], dict):
        raise click.ClickException("registry must contain relays[1] dict for secondary Chutes row")
    row = relays[1]
    if row.get("substrate") and row.get("substrate") != "chutes":
        raise click.ClickException(f"relays[1].substrate must be chutes, got {row.get('substrate')!r}")
    row["endpoint"] = endpoint.rstrip("/")
    row["substrate"] = "chutes"
    row["chute_id"] = chute_id
    row["image_id"] = image_id
    row["image_tag"] = image_tag
    if instance_id:
        row["instance_id"] = instance_id
    if relay_id:
        row["relay_id"] = relay_id
    if service:
        row["service"] = service
    row["last_seen_utc_ns"] = time.time_ns()
    payload_obj["as_of_utc_ns"] = time.time_ns()
    body = {key: value for key, value in payload_obj.items() if key != "payload_sha256"}
    payload_obj["payload_sha256"] = _sha256_json(body)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload_obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _update_akash_registry_row(path: Path, *, endpoint: str, image_tag: str, instance_class: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.port or "placeholder" in endpoint.lower():
        raise click.ClickException(f"invalid Akash endpoint for registry: {endpoint}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    relays = payload.get("relays")
    if not isinstance(relays, list) or not relays or not isinstance(relays[0], dict):
        raise click.ClickException("registry must contain relays[0]")
    relays[0]["endpoint"] = endpoint.rstrip("/")
    relays[0]["image_tag"] = image_tag
    relays[0]["instance_class"] = instance_class
    relays[0]["last_seen_utc_ns"] = time.time_ns()
    payload["as_of_utc_ns"] = time.time_ns()
    body = {key: value for key, value in payload.items() if key != "payload_sha256"}
    payload["payload_sha256"] = _sha256_json(body)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _sha256_json(payload: dict[str, object]) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _report_to_dict(report) -> dict[str, object]:
    return {
        "service": report.wallet.service,
        "wallet": report.wallet.id,
        "address": report.wallet.address,
        "network": report.wallet.network,
        "currency": report.wallet.currency,
        "balance": report.balance,
        "target": report.wallet.target,
        "status": report.status,
        "message": report.message,
    }


if __name__ == "__main__":
    main()

