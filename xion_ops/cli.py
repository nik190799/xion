"""Click CLI for xion-ops."""

from __future__ import annotations

import json
from pathlib import Path

import click

from xion_ops.registry import deployer_names, get_deployer, get_service, service_names
from xion_ops.types import DeployContext


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main() -> None:
    """Operator automation for Xion services."""


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


def balances(service_name: str | None = None):
    names = [service_name] if service_name else service_names()
    reports = []
    for name in names:
        reports.extend(get_service(name).balances())
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
def deploy_relay_akash(sdl_path: str) -> None:
    _run_deployer("relay-akash", {"sdl_path": sdl_path})


@deploy_group.command(name="relay-chutes")
@click.option("--module-path", default="xion_relay_chute.py")
def deploy_relay_chutes(module_path: str) -> None:
    _run_deployer("relay-chutes", {"module_path": module_path})


@deploy_group.command(name="base-contracts")
@click.option("--network", default="base-sepolia")
@click.option("--mode", default="full")
def deploy_base_contracts(network: str, mode: str) -> None:
    _run_deployer("base-contracts", {"network": network, "mode": mode})


def _run_deployer(name: str, params: dict[str, object]) -> None:
    deployer = get_deployer(name)
    record = deployer.run(DeployContext(repo_root=Path("."), params=params))
    click.echo(json.dumps(record.to_dict(), indent=2, sort_keys=True))
    if not record.result.ok or not record.verify.ok:
        raise click.exceptions.Exit(1)


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

