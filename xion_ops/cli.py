"""Click CLI for xion-ops."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlparse

import click

from xion_ops.env import load_repo_env, upsert_repo_env
from xion_ops.registry import deployer_names, get_deployer, get_service, service_names
from xion_ops.types import DeployContext


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


@akash_group.command(name="mint-act")
@click.argument("uakt_amount", type=int)
def akash_mint_act(uakt_amount: int) -> None:
    service = get_service("akash")
    result = service.mint_act(uakt_amount)  # type: ignore[attr-defined]
    click.echo(result.stdout)


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
def akash_lease_status(dseq: str, provider: str) -> None:
    service = get_service("akash")
    status = service.lease_status(dseq, provider)  # type: ignore[attr-defined]
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


@chutes_group.command(name="verify-cords")
@click.argument("url", required=False)
def chutes_verify_cords(url: str | None) -> None:
    result = get_service("chutes").verify_cords(url)  # type: ignore[attr-defined]
    click.echo(json.dumps(result.__dict__, indent=2, sort_keys=True))


@chutes_group.command(name="verify-import")
@click.argument("module_path", default="xion_relay_chute.py")
def chutes_verify_import(module_path: str) -> None:
    result = get_service("chutes").verify_import(module_path)  # type: ignore[attr-defined]
    click.echo(json.dumps(result.__dict__, indent=2, sort_keys=True))


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
@click.option("--network", default="base")
@click.option("--script", default="treasury/script/Deploy.s.sol:DeployTreasury")
def base_evm_deploy_treasury(network: str, script: str) -> None:
    result = get_service("base-evm").deploy_treasury(network, script)  # type: ignore[attr-defined]
    click.echo(json.dumps(result.__dict__, indent=2, sort_keys=True))


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


@main.group(name="deploy")
def deploy_group() -> None:
    """End-to-end deployment workflows."""


@deploy_group.command(name="relay-akash")
@click.option("--sdl-path", default="infra/akash/relay-deployment.yaml")
@click.option("--prefer-provider", default=None)
def deploy_relay_akash(sdl_path: str, prefer_provider: str | None) -> None:
    params: dict[str, object] = {"sdl_path": sdl_path}
    if prefer_provider:
        params["prefer_provider"] = prefer_provider
    _run_deployer("relay-akash", params)


@deploy_group.command(name="relay-chutes")
@click.option("--module-path", default="xion_relay_chute.py")
def deploy_relay_chutes(module_path: str) -> None:
    _run_deployer("relay-chutes", {"module_path": module_path})


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


def _run_deployer(name: str, params: dict[str, object]) -> None:
    deployer = get_deployer(name)
    record = deployer.run(DeployContext(repo_root=Path("."), params=params))
    click.echo(json.dumps(record.to_dict(), indent=2, sort_keys=True))
    if not record.result.ok or not record.verify.ok:
        raise click.exceptions.Exit(1)


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

