"""`xion-verify ao-handlers` — AO Core handler set doctrine + deploy verification.

Property promised. The verifier returns OK only when every claim Xion makes
about its AO Core is independently checkable by anyone with an Arweave gateway
URL and the committed receipt. There is no code path that returns OK without
a real network round-trip against an AO compute unit.

Layered checks (each must pass for the next to be evaluated):

1. Doctrine. For every `ao-handler-*.yaml` file under `docs/schemas/`:
   parses as YAML, has the required meta fields, `family` is one of
   `{lifecycle, authority, provisioning, sustainability}`, `source_sha256`
   matches `docs/04-ARCHITECTURE.md`, `operational_sha256` matches
   `docs/28-AO-CORE.md`. The expected handler set (19 handlers across 4
   families) must be exactly present — no missing, no extras.

2. Skeleton. `ao/core/main.lua` exists.

3. Receipt. `genesis/AO_DEPLOY_RECEIPT.json` exists, parses, and either:
   - declares itself a placeholder via `"status": "placeholder"` —
     return NOT_YET_SEALED with a remediation message naming exactly what
     a real receipt requires; or
   - is a real receipt: assert it has `process_id`, `signer_address`,
     `lua_source_sha256`, `aos_version`. Recompute
     sha256(`ao/core/main.lua`) and require equality with
     `lua_source_sha256` (catches a divergent Lua at the same PID).

4. Gateway round-trip. Read the AO compute unit's view of the process
   state at `${XION_AO_GATEWAY_URL}/state/${process_id}` (default
   `https://cu.ao-testnet.xyz`). Compare its reported state-tip height +
   root with the latest row of `ledgers/STATE_CHAIN_LEDGER.jsonl`.
   Mismatch is FAIL. Network unreachable / unparseable response is
   NOT_YET_SEALED — never fake-green on a network outage.

The previous version of this command bypassed step 4 whenever
`"dummy" in process_id`. That bypass is gone. A receipt that is honestly
a placeholder is honestly NOT_YET_SEALED; a receipt that claims a real PID
must survive the gateway round-trip.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import click
import yaml

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.hashing import sha256_file
from xion_verify.repo import RepoRootNotFound, find_repo_root

_SCHEMAS_DIRNAME = "docs/schemas"
_REQUIRED_META: tuple[str, ...] = (
    "handler",
    "family",
    "schema_version",
    "status",
    "args",
    "state_changes",
    "failure_modes",
    "source_doctrine",
    "source_sha256",
    "operational_doctrine",
    "operational_sha256",
)
_ALLOWED_FAMILIES: frozenset[str] = frozenset({"lifecycle", "authority", "provisioning", "sustainability"})

_EXPECTED_HANDLERS: frozenset[str] = frozenset({
    "commit-state", "attest", "treasury-spend", "registry-update", "spend", "slash-imprint",
    "rotate-authority", "abdicate-tier",
    "provision-relay", "provision-inference", "provision-storage", "provision-bandwidth", "provision-witness",
    "route-slices", "improvement-spend", "reserve-draw", "accept-donation", "enter-hibernation", "exit-hibernation"
})

_DEFAULT_GATEWAY = "https://cu.ao-testnet.xyz"
_GATEWAY_TIMEOUT_S = 10.0

_REAL_RECEIPT_REQUIRED: tuple[str, ...] = (
    "process_id",
    "signer_address",
    "lua_source_sha256",
    "aos_version",
)


def _fail(label: str, message: str) -> tuple[int, str]:
    return FAIL, f"{label}: FAIL: {message}"


def _check_one_schema(path: Path, repo_root: Path, arch_hash: str, core_hash: str) -> tuple[int, str]:
    label = f"ao-handlers[{path.relative_to(repo_root).as_posix()}]"

    try:
        raw = path.read_bytes()
    except OSError as exc:
        return _fail(label, f"cannot read: {exc}")

    try:
        data: Any = yaml.safe_load(raw.decode("utf-8"))
    except yaml.YAMLError as exc:
        return _fail(label, f"invalid YAML: {exc}")
    except UnicodeDecodeError as exc:
        return _fail(label, f"not valid UTF-8: {exc}")

    if not isinstance(data, dict):
        return _fail(label, "top-level YAML value must be a mapping")

    missing = [f for f in _REQUIRED_META if f not in data]
    if missing:
        return _fail(label, f"missing required meta fields: {', '.join(missing)}")

    family = data["family"]
    if family not in _ALLOWED_FAMILIES:
        return _fail(
            label,
            f"family must be one of {sorted(_ALLOWED_FAMILIES)}; got {family!r}",
        )

    if data["source_sha256"] != arch_hash:
        return _fail(
            label,
            f"source_sha256 mismatch for docs/04-ARCHITECTURE.md\n"
            f"  expected: {arch_hash}\n"
            f"  actual:   {data['source_sha256']}",
        )

    if data["operational_sha256"] != core_hash:
        return _fail(
            label,
            f"operational_sha256 mismatch for docs/28-AO-CORE.md\n"
            f"  expected: {core_hash}\n"
            f"  actual:   {data['operational_sha256']}",
        )

    return OK, f"{label}: OK"


def _read_latest_ledger_tip(ledger_path: Path) -> tuple[int, str] | None:
    """Return (height, state_root_sha256) of the last row, or None if empty/absent."""
    if not ledger_path.is_file():
        return None
    last: dict[str, Any] | None = None
    with ledger_path.open("rb") as fh:
        for raw_line in fh:
            line = raw_line.rstrip(b"\n").rstrip(b"\r")
            if not line:
                continue
            try:
                last = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
    if last is None:
        return None
    height = last.get("height")
    root = last.get("state_root_sha256")
    if not isinstance(height, int) or not isinstance(root, str):
        return None
    return height, root


def _fetch_gateway_tip(gateway_url: str, process_id: str) -> tuple[int | None, tuple[int, str] | None, str | None]:
    """Read the AO compute unit's view of the process state.

    Returns (exit_code_hint, (height, root) | None, message). exit_code_hint is
    NOT_YET_SEALED on network/parse failure (never fake-green), OK otherwise.
    """
    url = f"{gateway_url.rstrip('/')}/state/{process_id}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "xion-verify"})
    try:
        with urllib.request.urlopen(req, timeout=_GATEWAY_TIMEOUT_S) as resp:
            body = resp.read()
            content_type = resp.headers.get("Content-Type", "")
    except urllib.error.URLError as exc:
        return NOT_YET_SEALED, None, f"AO gateway unreachable at {url}: {exc.reason}"
    except TimeoutError as exc:
        return NOT_YET_SEALED, None, f"AO gateway timeout at {url}: {exc}"
    except OSError as exc:
        return NOT_YET_SEALED, None, f"AO gateway socket error at {url}: {exc}"

    try:
        text = body.decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return NOT_YET_SEALED, None, f"AO gateway response not decodable: {exc}"

    parsed: Any = None
    if "json" in content_type.lower() or text.lstrip().startswith(("{", "[")):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None

    if isinstance(parsed, dict):
        height = parsed.get("state_tip_height")
        if height is None:
            height = parsed.get("height")
        root = parsed.get("state_root_sha256")
        if root is None:
            root = parsed.get("root")
        if isinstance(height, int) and isinstance(root, str) and len(root) == 64:
            return OK, (height, root), None

    return (
        NOT_YET_SEALED,
        None,
        (
            f"AO gateway response shape unrecognized at {url}; "
            f"expected JSON object containing `state_tip_height` (int) and `state_root_sha256` (64-char hex). "
            f"Got: {text[:200]!r}"
        ),
    )


def _check_receipt_and_gateway(repo_root: Path, schema_count: int) -> tuple[int, str]:
    lua_main = repo_root / "ao" / "core" / "main.lua"
    if not lua_main.is_file():
        return (
            NOT_YET_SEALED,
            f"ao-handlers: NOT_YET_SEALED ({schema_count} handler schema(s) verified, awaiting Lua skeleton: ao/core/main.lua)",
        )

    receipt_path = repo_root / "genesis" / "AO_DEPLOY_RECEIPT.json"
    if not receipt_path.is_file():
        return (
            NOT_YET_SEALED,
            f"ao-handlers: NOT_YET_SEALED ({schema_count} handler schema(s) verified, Lua skeleton present, awaiting genesis/AO_DEPLOY_RECEIPT.json)",
        )

    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return FAIL, f"ao-handlers: FAIL: cannot parse genesis/AO_DEPLOY_RECEIPT.json: {exc}"

    if not isinstance(receipt, dict):
        return FAIL, "ao-handlers: FAIL: genesis/AO_DEPLOY_RECEIPT.json must be a JSON object"

    if receipt.get("status") == "placeholder":
        return (
            NOT_YET_SEALED,
            (
                f"ao-handlers: NOT_YET_SEALED ({schema_count} handler schema(s) verified, Lua skeleton present, "
                "AO_DEPLOY_RECEIPT.json is a placeholder). "
                "To promote: perform a real `aos` testnet deploy of `ao/core/main.lua`, replace the receipt with "
                "{status:'live', process_id, signer_address, lua_source_sha256, aos_version, timestamp, network}, "
                "and seed `ledgers/STATE_CHAIN_LEDGER.jsonl` with the first commit-state round-trip. "
                "See KW-AOCORE-001."
            ),
        )

    missing = [f for f in _REAL_RECEIPT_REQUIRED if f not in receipt or receipt.get(f) in (None, "")]
    if missing:
        return (
            FAIL,
            f"ao-handlers: FAIL: AO_DEPLOY_RECEIPT.json missing required fields for a non-placeholder receipt: "
            f"{sorted(missing)}. Either fill them or set `status: 'placeholder'`.",
        )

    expected_lua_hash = sha256_file(lua_main)
    if receipt["lua_source_sha256"] != expected_lua_hash:
        return (
            FAIL,
            (
                "ao-handlers: FAIL: lua_source_sha256 in AO_DEPLOY_RECEIPT.json does not match current ao/core/main.lua bytes\n"
                f"  receipt: {receipt['lua_source_sha256']}\n"
                f"  current: {expected_lua_hash}\n"
                "  Either redeploy and re-issue the receipt, or revert ao/core/main.lua to the deployed bytes."
            ),
        )

    ledger_path = repo_root / "ledgers" / "STATE_CHAIN_LEDGER.jsonl"
    local_tip = _read_latest_ledger_tip(ledger_path)
    if local_tip is None:
        return (
            NOT_YET_SEALED,
            (
                f"ao-handlers: NOT_YET_SEALED ({schema_count} handler schema(s) verified, real receipt present, "
                f"awaiting first row in ledgers/STATE_CHAIN_LEDGER.jsonl. "
                "Send a `commit-state` message via `aos` and let the orchestrator's STATE_CHAIN_LEDGER writer record it."
            ),
        )
    local_height, local_root = local_tip

    gateway_url = os.environ.get("XION_AO_GATEWAY_URL", _DEFAULT_GATEWAY)
    code_hint, gateway_tip, msg = _fetch_gateway_tip(gateway_url, receipt["process_id"])
    if gateway_tip is None:
        return code_hint, f"ao-handlers: NOT_YET_SEALED ({msg}; cannot prove tip parity offline)"

    gateway_height, gateway_root = gateway_tip
    if gateway_height != local_height or gateway_root != local_root:
        return (
            FAIL,
            (
                "ao-handlers: FAIL: local STATE_CHAIN_LEDGER tip does not match AO gateway view\n"
                f"  ledger: height={local_height}, root={local_root}\n"
                f"  gateway: height={gateway_height}, root={gateway_root}\n"
                "  Either re-run `commit-state` to bring the chain forward, or rewind the local ledger to match."
            ),
        )

    return (
        OK,
        (
            f"ao-handlers: OK ({schema_count} handler schema(s) verified, Lua skeleton matches deployed hash, "
            f"local tip parity verified against {gateway_url} at height={local_height})"
        ),
    )


@click.command(name="ao-handlers")
def verify_ao_handlers() -> None:
    """Verify AO Core handler schemas, Lua skeleton, and live deploy parity."""
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"ao-handlers: FAIL: {exc}", err=True)
        raise click.exceptions.Exit(FAIL)

    schemas_dir = repo_root / _SCHEMAS_DIRNAME
    if not schemas_dir.is_dir():
        click.echo(f"ao-handlers: NOT_YET_SEALED: {schemas_dir} not found")
        raise click.exceptions.Exit(NOT_YET_SEALED)

    arch_path = repo_root / "docs/04-ARCHITECTURE.md"
    core_path = repo_root / "docs/28-AO-CORE.md"

    if not arch_path.is_file() or not core_path.is_file():
        click.echo("ao-handlers: FAIL: doctrine files not found", err=True)
        raise click.exceptions.Exit(FAIL)

    arch_hash = sha256_file(arch_path)
    core_hash = sha256_file(core_path)

    yaml_files = sorted(schemas_dir.glob("ao-handler-*.yaml"))
    if not yaml_files:
        click.echo("ao-handlers: NOT_YET_SEALED: no ao-handler-*.yaml files found")
        raise click.exceptions.Exit(NOT_YET_SEALED)

    found_handlers: set[str] = set()
    worst_code = OK
    messages: list[str] = []

    for path in yaml_files:
        code, msg = _check_one_schema(path, repo_root, arch_hash, core_hash)
        messages.append(msg)
        if code != OK:
            worst_code = max(worst_code, code)
        found_handlers.add(path.stem.replace("ao-handler-", ""))

    missing_handlers = _EXPECTED_HANDLERS - found_handlers
    if missing_handlers:
        worst_code = FAIL
        messages.append(f"ao-handlers: FAIL: missing expected handler schemas: {sorted(missing_handlers)}")

    extra_handlers = found_handlers - _EXPECTED_HANDLERS
    if extra_handlers:
        worst_code = FAIL
        messages.append(f"ao-handlers: FAIL: unexpected handler schemas found: {sorted(extra_handlers)}")

    for msg in messages:
        click.echo(msg, err=(worst_code == FAIL and "FAIL" in msg))

    if worst_code != OK:
        click.echo(f"ao-handlers: FAIL ({len(yaml_files)} handler schema(s) checked)", err=True)
        raise click.exceptions.Exit(worst_code)

    final_code, final_message = _check_receipt_and_gateway(repo_root, len(yaml_files))
    click.echo(final_message, err=(final_code == FAIL))
    raise click.exceptions.Exit(final_code)
