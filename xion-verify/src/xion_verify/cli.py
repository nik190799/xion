"""Root click group for xion-verify.

This is the only place every subcommand is named and registered. If a
subcommand is not wired here, it does not exist from the CLI's perspective,
regardless of what is in `commands/`. That discipline is intentional: it keeps
the surface area legible and enumerable.

`xion-verify --self-test` runs before any other subcommand resolution so that
a tampered verifier cannot claim to have passed anything else. The flag lives
at the root group rather than as a subcommand so `xion-verify --self-test` is
usable even when no arguments are given.
"""

from __future__ import annotations

import contextlib
import sys
from typing import Any

import click

from xion_verify import __version__
from xion_verify.commands import REGISTERED_COMMANDS
from xion_verify.commands.arbiter_up import arbiter_up
from xion_verify.commands.cognition import cognition
from xion_verify.commands.constitutional import (
    covenant,
    credentials,
    form,
    invariants,
    memory,
    resurrect,
    soul,
    unknowns,
)
from xion_verify.commands.drive import drive
from xion_verify.commands.drive_vector import drive_vector
from xion_verify.commands.links import links
from xion_verify.commands.not_yet_sealed import STUB_COMMANDS, STUB_NAMES
from xion_verify.commands.refund_fidelity import refund_fidelity
from xion_verify.commands.refusal_rate import refusal_rate
from xion_verify.commands.inference_sovereignty import inference_sovereignty
from xion_verify.commands.schemas import schemas
from xion_verify.commands.self_test import run_self_test
from xion_verify.commands.sensorium_ledger import sensorium_ledger
from xion_verify.commands.state_chain import state_chain
from xion_verify.exit_codes import FAIL, OK
from xion_verify.exit_codes import name as exit_code_name

_REAL_COMMANDS: dict[str, click.Command] = {
    "covenant": covenant,
    "invariants": invariants,
    "soul": soul,
    "form": form,
    "memory": memory,
    "resurrect": resurrect,
    "credentials": credentials,
    "unknowns": unknowns,
    "links": links,
    "schemas": schemas,
    "cognition": cognition,
    "drive": drive,
    "drive-vector": drive_vector,
    "state-chain": state_chain,
    "arbiter-up": arbiter_up,
    "refusal-rate": refusal_rate,
    "refund-fidelity": refund_fidelity,
    "inference-sovereignty": inference_sovereignty,
    "sensorium-ledger": sensorium_ledger,
}


def _build_root() -> click.Group:
    @click.group(
        name="xion-verify",
        help=(
            "Third-party verifier for Xion's constitutional claims.\n\n"
            "Every subcommand is deterministic: same input, same output. "
            "A disagreement between two independent runs against the same state is an alert. "
            "Trust by structure, not by promise."
        ),
        context_settings={"help_option_names": ["-h", "--help"]},
        invoke_without_command=True,
    )
    @click.version_option(__version__, prog_name="xion-verify")
    @click.option(
        "--self-test",
        "self_test",
        is_flag=True,
        help="Verify the verifier's own source against PINNED_HASH.txt; run before trusting other output.",
    )
    @click.option(
        "--update",
        "update",
        is_flag=True,
        help="With --self-test: overwrite PINNED_HASH.txt (requires --i-understand).",
    )
    @click.option(
        "--i-understand",
        "i_understand",
        is_flag=True,
        help="Required alongside --self-test --update.",
    )
    @click.pass_context
    def root(
        ctx: click.Context,
        self_test: bool,
        update: bool,
        i_understand: bool,
    ) -> None:
        if self_test:
            code, message = run_self_test(update=update, i_understand=i_understand)
            click.echo(message, err=(code != OK))
            ctx.exit(code)
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            ctx.exit(OK)

    for cli_name, cmd in _REAL_COMMANDS.items():
        root.add_command(cmd, name=cli_name)
    for cli_name in STUB_NAMES:
        root.add_command(STUB_COMMANDS[cli_name], name=cli_name)

    _register_all(root)
    _verify_registry(root)
    return root


def _register_all(root: click.Group) -> None:
    @root.command(
        name="all",
        help="Run every registered subcommand; exit 0 only if every one returned OK (NOT_YET_SEALED counts as non-OK).",
    )
    @click.option("--allow-not-yet-sealed", is_flag=True,
                  help="Treat NOT_YET_SEALED as OK for this run (pre-genesis convenience; never use in CI gating).")
    @click.pass_context
    def _all(ctx: click.Context, allow_not_yet_sealed: bool) -> None:
        results: list[tuple[str, int]] = []
        for cli_name in REGISTERED_COMMANDS:
            cmd = root.commands.get(cli_name)
            if cmd is None:
                click.echo(f"all: FAIL: subcommand '{cli_name}' declared in registry but not wired", err=True)
                ctx.exit(FAIL)
            code = _invoke_subcommand_for_all(cmd)
            results.append((cli_name, code))

        non_ok = [(n, c) for n, c in results if c != OK]
        if allow_not_yet_sealed:
            from xion_verify.exit_codes import NOT_YET_SEALED
            non_ok = [(n, c) for n, c in non_ok if c != NOT_YET_SEALED]

        click.echo("")
        click.echo("--- xion-verify all ---")
        for n, c in results:
            click.echo(f"  {n}: {exit_code_name(c)}")
        if non_ok:
            click.echo(f"all: FAIL: {len(non_ok)} non-OK subcommand(s)", err=True)
            ctx.exit(FAIL)
        click.echo("all: OK (every registered subcommand returned OK)")
        ctx.exit(OK)


def _invoke_subcommand_for_all(cmd: click.Command) -> int:
    """Invoke a subcommand in-process, returning its exit code without exiting."""
    try:
        cmd.main(args=[], standalone_mode=False)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else FAIL
        return code
    except click.ClickException as exc:
        exc.show()
        return FAIL
    return OK


def _verify_registry(root: click.Group) -> None:
    """Fail at import time if the registry and the wired commands disagree."""
    registered = set(REGISTERED_COMMANDS)
    wired = set(root.commands.keys()) - {"all"}
    missing_from_wiring = registered - wired
    extra_wired = wired - registered
    if missing_from_wiring or extra_wired:
        raise RuntimeError(
            "xion-verify registry mismatch: "
            f"declared-but-not-wired={sorted(missing_from_wiring)} "
            f"wired-but-not-declared={sorted(extra_wired)}. "
            "Update xion_verify/commands/__init__.py REGISTERED_COMMANDS."
        )


root = _build_root()


def main(argv: list[str] | None = None) -> Any:
    _force_utf8_io()
    return root.main(args=argv, prog_name="xion-verify")


def _force_utf8_io() -> None:
    """Ensure CLI output is UTF-8 on every platform.

    Xion's doctrine uses em-dashes and section signs; these must render
    identically on Linux, macOS, and Windows. Without this, a Windows
    terminal defaulting to cp1252 raises UnicodeEncodeError.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(OSError, ValueError):
                reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
