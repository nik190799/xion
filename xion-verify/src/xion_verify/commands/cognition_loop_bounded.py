"""Verify cognition loop budgets and tool-call surface wiring."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK


@click.command(name="cognition-loop-bounded")
def cognition_loop_bounded() -> None:
    try:
        from orchestrator.cognition.loop import DEFAULT_BUDGET, _chat_tools

        if DEFAULT_BUDGET.delegation_depth != 1:
            raise RuntimeError("delegation depth is not pinned to 1")
        if DEFAULT_BUDGET.iteration_count != 3 or DEFAULT_BUDGET.tool_rounds != 3:
            raise RuntimeError("iteration/tool-round budgets are not pinned to 3")
        if DEFAULT_BUDGET.reasoning_tokens != 4096 or DEFAULT_BUDGET.wall_clock_s != 8.0:
            raise RuntimeError("reasoning/wall-clock budgets drifted")
        tools = _chat_tools()
        names = {tool.get("function", {}).get("name") for tool in tools}
        required = {"read_constitution", "query_journal", "query_sensorium", "read_ledger", "run_verifier"}
        if not required <= names:
            raise RuntimeError(f"missing native tool schemas: {sorted(required - names)}")
    except Exception as exc:
        click.echo(f"cognition-loop-bounded: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo("cognition-loop-bounded: OK (budgets + tool schemas)")
    sys.exit(OK)


__all__ = ["cognition_loop_bounded"]
