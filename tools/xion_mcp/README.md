# xion-mcp

Read-only MCP wrapper for Xion contribution facts.

## Property

Expose the same verifier-backed facts as `xion-verify mcp-export` without
granting assistants any write authority.

## Run

```bash
python -m tools.xion_mcp.server
```

The server speaks newline-delimited JSON-RPC over stdio. It exposes only
read-only tools: `mcp_export`, `which_level`, `links`, `covenant`, `invariants`,
`soul`, and `unknowns`.
