from __future__ import annotations

import json
from pathlib import Path

from tools.xion_mcp.server import READ_ONLY_TOOLS, handle_request
from xion_verify.commands.mcp_export import build_mcp_export_payload


def test_tools_list_exposes_only_read_only_tools() -> None:
    response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == set(READ_ONLY_TOOLS)
    assert not {"commit", "sign", "pay", "submit", "propose"} & names


def test_write_like_tool_name_is_rejected() -> None:
    response = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "submit_proposal", "arguments": {}},
        }
    )

    assert response["error"]["code"] == -32602
    assert "not read-only" in response["error"]["message"]


def test_mcp_export_tool_returns_read_only_payload() -> None:
    response = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "mcp_export", "arguments": {}},
        }
    )

    text = response["result"]["content"][0]["text"]
    assert '"mode": "read_only"' in text
    assert "no_state_writes" in text


def test_mcp_export_tool_matches_verifier_payload() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    response = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "mcp_export", "arguments": {}},
        },
        repo_root=repo_root,
    )

    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload == build_mcp_export_payload(repo_root)
