"""Verify cognition tool resolver and in-process MCP bridge."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK


@click.command(name="tool-resolver-mcp")
def tool_resolver_mcp() -> None:
    try:
        from orchestrator.tools import McpToolResolver, PythonToolResolver

        py = PythonToolResolver()
        py_names = {spec.name for spec in py.list_tools()}
        required = {"read_constitution", "query_journal", "query_sensorium", "read_ledger", "run_verifier"}
        if not required <= py_names:
            raise RuntimeError(f"python resolver missing tools: {sorted(required - py_names)}")
        mcp = McpToolResolver()
        mcp_names = {spec.name for spec in mcp.list_tools()}
        if not {"covenant", "invariants", "soul", "unknowns"} <= mcp_names:
            raise RuntimeError("mcp resolver did not expose constitutional tools")
        result = mcp.call_tool("covenant", {})
        if result.is_error or "COVENANT" not in str(result.content).upper():
            raise RuntimeError("mcp covenant tool did not return covenant text")
    except Exception as exc:
        click.echo(f"tool-resolver-mcp: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo("tool-resolver-mcp: OK (python + MCP resolvers)")
    sys.exit(OK)


__all__ = ["tool_resolver_mcp"]
