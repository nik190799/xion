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
   `docs/28-AO-CORE.md`. The expected handler set (20 handlers across 4
   families: 19 from Phase 6.0, plus `anchor-interaction-batch` from Phase
   6.3) must be exactly present — no missing, no extras.

2. Skeleton. `ao/core/main.lua` exists.

3. Receipt. `genesis/AO_DEPLOY_RECEIPT.json` exists, parses, and either:
   - declares itself a placeholder via `"status": "placeholder"` —
     return NOT_YET_SEALED with a remediation message naming exactly what
     a real receipt requires; or
   - is a real receipt: assert it has `process_id`, `signer_address`,
     `lua_source_sha256`, `aos_version`, and `substrate` (Phase 6.1.b).
     `substrate` MUST be one of `{legacynet, localnet}`; any other value
     (notably `mainnet`) FAILs at this phase per docs/09-GOVERNANCE.md.
     Recompute sha256(`ao/core/main.lua`) and require equality with
     `lua_source_sha256` (catches a divergent Lua at the same PID).

4. Gateway round-trip. Read the AO compute unit's view of the process
   state at `${XION_AO_GATEWAY_URL}/state/${process_id}` (default
   `https://cu.ao-testnet.xyz` — operator sets it to
   `http://localhost:4004` for the localnet substrate per
   `infra/ao-localnet/`). Compare its reported state-tip height + root
   with the latest row of `ledgers/STATE_CHAIN_LEDGER.jsonl`. Mismatch is
   FAIL. Network unreachable / unparseable response is NOT_YET_SEALED —
   never fake-green on a network outage. The OK message includes the
   substrate name so a third-party reviewer can see which CU witnessed
   the seal.

The previous version of this command bypassed step 4 whenever
`"dummy" in process_id`. That bypass is gone. A receipt that is honestly
a placeholder is honestly NOT_YET_SEALED; a receipt that claims a real PID
must survive the gateway round-trip.
"""

from __future__ import annotations

import json
import os
import re
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
_ALLOWED_STATUSES: frozenset[str] = frozenset({"canonical", "doctrine_only", "underspecified"})

_EXPECTED_HANDLERS: frozenset[str] = frozenset({
    # Phase 6.0 lifecycle (7) — including anchor-interaction-batch added in Phase 6.3.
    "commit-state", "attest", "treasury-spend", "registry-update", "spend", "slash-imprint",
    "anchor-interaction-batch",
    # Phase 6.0 authority (2)
    "rotate-authority", "abdicate-tier",
    # Phase 6.0 provisioning (5)
    "provision-relay", "provision-inference", "provision-storage", "provision-bandwidth", "provision-witness",
    # Phase 6.0 sustainability (6)
    "route-slices", "improvement-spend", "reserve-draw", "accept-donation", "enter-hibernation", "exit-hibernation",
})

_DEFAULT_GATEWAY = "https://cu.ao-testnet.xyz"
_GATEWAY_TIMEOUT_S = 10.0

_REAL_RECEIPT_REQUIRED: tuple[str, ...] = (
    "process_id",
    "signer_address",
    "lua_source_sha256",
    "aos_version",
    "substrate",
)

# Phase 6.1.b allowlist. `mainnet` is intentionally excluded at this phase per
# `docs/09-GOVERNANCE.md` (Tier-3 cosign ceremony obligation). A receipt that
# declares any other value FAILs immediately.
_ALLOWED_SUBSTRATES: frozenset[str] = frozenset({"legacynet", "localnet"})


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

    status = data["status"]
    if status not in _ALLOWED_STATUSES:
        return _fail(
            label,
            f"status must be one of {sorted(_ALLOWED_STATUSES)}; got {status!r}",
        )

    if data["handler"] != path.stem.replace("ao-handler-", ""):
        return _fail(
            label,
            f"handler field {data['handler']!r} does not match filename {path.name!r}",
        )

    args = data["args"]
    if isinstance(args, list):
        arg_names = {arg.get("name") for arg in args if isinstance(arg, dict)}
        if "dummy_arg" in arg_names:
            return _fail(label, "schema still contains placeholder dummy_arg")

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


def _read_schema_status(path: Path) -> str | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    status = data.get("status")
    return status if isinstance(status, str) else None


def _registered_lua_handlers(lua_path: Path) -> set[str]:
    try:
        source = lua_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    return set(re.findall(r'Handlers\.add\(\s*"([^"]+)"', source))


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


# Lua expression sent via the CU's /dry-run endpoint. Returns a JSON string
# encoding the AO process's authoritative StateTip — height + root in the same
# shape the verifier wants. Using dry-run (a side-effect-free Eval) means the
# verifier can prove tip parity *without* signing a transaction or paying gas,
# which preserves the "any third party with a CU URL can verify" property.
_STATE_TIP_DRYRUN_LUA = (
    'return require("json").encode({'
    'state_tip_height = StateTip and StateTip.height or -1, '
    'state_root_sha256 = StateTip and StateTip.root or ""'
    "})"
)


def _fetch_gateway_tip(gateway_url: str, process_id: str, owner_address: str) -> tuple[int | None, tuple[int, str] | None, str | None]:
    """Read the AO compute unit's view of the process state via /dry-run.

    Returns (exit_code_hint, (height, root) | None, message). exit_code_hint is
    NOT_YET_SEALED on network/parse failure (never fake-green), OK otherwise.

    The legacy AO CU exposes the process *memory* under /state/<pid> (a binary
    blob — useful for snapshots, not for tip parity), but the structured query
    surface is /dry-run?process-id=<pid>: POST a minimal Eval message body and
    receive `{ Output: { data: { output: <lua-return-string>, ... } }, ... }`.
    We send a tiny `return json.encode({state_tip_height=..., state_root_sha256=...})`
    expression and parse the inner string. This matches how aoconnect's `dryrun()`
    helper queries process state and is the same surface the orchestrator uses.

    The `owner_address` MUST match the process's stored Owner. AOS's default Eval
    handler only *executes* the Data when `msg.From == Owner`; otherwise it falls
    through to the generic message-printer and the response carries a "New Message
    From <pid>: Action = Eval" banner string in `Output.data.output` instead of
    the Lua return value. The CU populates `From` from the dry-run body's `Owner`
    field (no signature is required because dry-run is side-effect-free), so
    passing the owner here is both necessary and sufficient. The verifier reads
    `owner_address` from the receipt's `signer_address` field — which any third
    party reviewing the receipt has access to — so this preserves the trust model.
    """
    url = f"{gateway_url.rstrip('/')}/dry-run?process-id={process_id}"
    body_obj = {
        "Id": "1234",
        # See docstring: must equal the process's Owner so AOS evaluates Data
        # rather than handing it to the default banner-printer.
        "Owner": owner_address,
        "Target": process_id,
        "Anchor": "0",
        "Tags": [{"name": "Action", "value": "Eval"}],
        "Data": _STATE_TIP_DRYRUN_LUA,
    }
    body_bytes = json.dumps(body_obj).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body_bytes,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "xion-verify",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_GATEWAY_TIMEOUT_S) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        return NOT_YET_SEALED, None, f"AO CU /dry-run unreachable at {url}: {exc.reason}"
    except TimeoutError as exc:
        return NOT_YET_SEALED, None, f"AO CU /dry-run timeout at {url}: {exc}"
    except OSError as exc:
        return NOT_YET_SEALED, None, f"AO CU /dry-run socket error at {url}: {exc}"

    try:
        outer = json.loads(raw.decode("utf-8", errors="replace"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return NOT_YET_SEALED, None, f"AO CU /dry-run response not JSON at {url}: {exc}"

    if not isinstance(outer, dict):
        return NOT_YET_SEALED, None, f"AO CU /dry-run response not a JSON object at {url}: {str(outer)[:200]!r}"

    output = outer.get("Output")
    if not isinstance(output, dict):
        return NOT_YET_SEALED, None, f"AO CU /dry-run response missing Output at {url}: {str(outer)[:200]!r}"

    data = output.get("data")
    inner_json: str | None = None
    if isinstance(data, dict):
        candidate = data.get("output")
        if isinstance(candidate, str):
            inner_json = candidate
    elif isinstance(data, str):
        inner_json = data

    if inner_json is None:
        return NOT_YET_SEALED, None, f"AO CU /dry-run Output.data missing string `output` at {url}: {str(output)[:200]!r}"

    try:
        inner = json.loads(inner_json)
    except json.JSONDecodeError as exc:
        return NOT_YET_SEALED, None, f"AO CU /dry-run inner Lua return is not JSON at {url}: {exc} (got {inner_json[:200]!r})"

    if not isinstance(inner, dict):
        return NOT_YET_SEALED, None, f"AO CU /dry-run inner JSON not an object at {url}: {str(inner)[:200]!r}"

    height = inner.get("state_tip_height")
    root = inner.get("state_root_sha256")

    if not isinstance(height, int) or not isinstance(root, str) or len(root) != 64:
        return (
            NOT_YET_SEALED,
            None,
            (
                f"AO CU /dry-run state shape unrecognized at {url}; "
                "expected `state_tip_height` (int) and `state_root_sha256` (64-char hex). "
                f"Got: {inner!r}"
            ),
        )

    if height < 0:
        return (
            NOT_YET_SEALED,
            None,
            f"AO CU /dry-run reports StateTip uninitialized at {url} (height={height}); "
            "the process likely never received its first commit-state.",
        )

    return OK, (height, root), None


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

    substrate = receipt["substrate"]
    if substrate not in _ALLOWED_SUBSTRATES:
        return (
            FAIL,
            (
                f"ao-handlers: FAIL: AO_DEPLOY_RECEIPT.json `substrate` field has invalid value {substrate!r}. "
                f"Allowed at Phase 6.1: {sorted(_ALLOWED_SUBSTRATES)}. "
                "`mainnet` is forbidden at this phase per docs/09-GOVERNANCE.md (Tier-3 cosign ceremony obligation; "
                "see docs/28-AO-CORE.md § 'Substrate amendment (Phase 6.1.b)')."
            ),
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
    code_hint, gateway_tip, msg = _fetch_gateway_tip(
        gateway_url,
        receipt["process_id"],
        receipt["signer_address"],
    )
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
            f"substrate={substrate}, local tip parity verified against {gateway_url} at height={local_height})"
        ),
    )


@click.command(name="ao-handlers")
def verify_ao_handlers() -> None:
    """Verify AO Core handler schemas, Lua skeleton, and live deploy parity."""
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"ao-handlers: FAIL: {exc}", err=True)
        raise click.exceptions.Exit(FAIL) from exc

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
    live_handlers: set[str] = set()
    worst_code = OK
    messages: list[str] = []

    for path in yaml_files:
        code, msg = _check_one_schema(path, repo_root, arch_hash, core_hash)
        messages.append(msg)
        if code != OK:
            worst_code = max(worst_code, code)
        handler_name = path.stem.replace("ao-handler-", "")
        found_handlers.add(handler_name)
        if _read_schema_status(path) == "canonical":
            live_handlers.add(handler_name)

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

    lua_main = repo_root / "ao" / "core" / "main.lua"
    if lua_main.is_file() and live_handlers:
        registered_handlers = _registered_lua_handlers(lua_main)
        missing_live = live_handlers - registered_handlers
        if missing_live:
            click.echo(
                "ao-handlers: FAIL: canonical handler schemas missing Lua registrations: "
                f"{sorted(missing_live)}",
                err=True,
            )
            raise click.exceptions.Exit(FAIL)

    final_code, final_message = _check_receipt_and_gateway(repo_root, len(yaml_files))
    click.echo(final_message, err=(final_code == FAIL))
    raise click.exceptions.Exit(final_code)
