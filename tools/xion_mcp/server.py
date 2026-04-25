"""Minimal stdio MCP-compatible JSON-RPC server.

Only read-only tools are exposed. The server intentionally wraps existing
`xion-verify` facts instead of creating a second authority surface.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from xion_verify.commands.mcp_export import build_mcp_export_payload
from xion_verify.leveling import classify_path, load_level_schemas
from xion_verify.repo import find_repo_root

READ_ONLY_TOOLS: dict[str, dict[str, Any]] = {
    "mcp_export": {
        "description": "Return the read-only Xion facts bundle.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "which_level": {
        "description": "Classify a repository path using docs/schemas/levels.yaml.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    "covenant": {
        "description": "Return genesis/COVENANT.md text.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "invariants": {
        "description": "Return genesis/INVARIANTS.md text.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "soul": {
        "description": "Return genesis/SOUL.md text.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "unknowns": {
        "description": "Return genesis/UNKNOWNS.md text.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "links": {
        "description": "Return a structural pointer to the links verifier.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}

_WRITE_TOOL_HINTS = ("write", "commit", "sign", "pay", "submit", "propose", "delete", "mutate")


def handle_request(request: dict[str, Any], *, repo_root: Path | None = None) -> dict[str, Any]:
    rpc_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}
    root = repo_root or find_repo_root()
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "xion-mcp", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "tools": [
                    {"name": name, **descriptor} for name, descriptor in sorted(READ_ONLY_TOOLS.items())
                ]
            },
        }
    if method == "tools/call":
        tool_name = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        return _tool_response(rpc_id, tool_name, arguments, root)
    return _error(rpc_id, -32601, f"unknown method: {method}")


def _tool_response(rpc_id: Any, tool_name: str, arguments: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    if tool_name not in READ_ONLY_TOOLS or any(hint in tool_name for hint in _WRITE_TOOL_HINTS):
        return _error(rpc_id, -32602, f"tool is not read-only or not allowlisted: {tool_name}")
    if tool_name == "mcp_export":
        result: Any = build_mcp_export_payload(repo_root)
    elif tool_name == "which_level":
        schemas = load_level_schemas(repo_root)
        level_id = classify_path(str(arguments.get("path", "")), schemas.levels if schemas else {})
        result = {"path": str(arguments.get("path", "")), "level_id": level_id}
    elif tool_name == "links":
        result = {"command": "xion-verify links", "mode": "read_only"}
    else:
        result = _read_text(repo_root, _doc_for_tool(tool_name))
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {"content": [{"type": "text", "text": json.dumps(result, sort_keys=True)}]},
    }


def _doc_for_tool(tool_name: str) -> str:
    return {
        "covenant": "genesis/COVENANT.md",
        "invariants": "genesis/INVARIANTS.md",
        "soul": "genesis/SOUL.md",
        "unknowns": "genesis/UNKNOWNS.md",
    }[tool_name]


def _read_text(repo_root: Path, rel: str) -> dict[str, str]:
    path = repo_root / rel
    return {"path": rel, "text": path.read_text(encoding="utf-8") if path.is_file() else ""}


def _error(rpc_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle_request(json.loads(line))
        print(json.dumps(response, separators=(",", ":"), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
