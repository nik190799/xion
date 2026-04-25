"""In-process MCP resolver backed by tools.xion_mcp.server."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orchestrator.tools.resolver import ToolResult, ToolSpec


def _repo_root() -> Path:
    for base in [Path.cwd(), *Path.cwd().parents]:
        if (base / "tools" / "xion_mcp" / "server.py").is_file():
            return base
    return Path.cwd()


@dataclass
class McpToolResolver:
    resolver_id: str = "mcp-resolver"
    repo_root: Path = field(default_factory=_repo_root)

    def list_tools(self) -> list[ToolSpec]:
        from tools.xion_mcp.server import handle_request

        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, repo_root=self.repo_root)
        tools = response.get("result", {}).get("tools", [])
        return [
            ToolSpec(
                name=str(tool["name"]),
                description=str(tool.get("description") or ""),
                input_schema=dict(tool.get("inputSchema") or {"type": "object"}),
            )
            for tool in tools
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        from tools.xion_mcp.server import handle_request

        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            repo_root=self.repo_root,
        )
        if "error" in response:
            return ToolResult(name=name, content=response["error"], is_error=True)
        content = response.get("result", {}).get("content", [])
        if content and isinstance(content[0], dict):
            text = str(content[0].get("text") or "")
            try:
                return ToolResult(name=name, content=json.loads(text))
            except json.JSONDecodeError:
                return ToolResult(name=name, content=text)
        return ToolResult(name=name, content=response.get("result"))


__all__ = ["McpToolResolver"]
