# Agent Souls Schema

> *An agentic faculty is born from a Soul file, not from runtime convenience.*

## Four Properties

**Property promised.** Every Hermes-cast faculty is defined by a content-addressed Agent Soul before it is instantiated. A live faculty must be traceable back to exactly one Agent Soul, one parent Soul hash, and one Hermes pin.

**Invariants touched.** Strengthens Invariants 1, 4, 5, 6, 11, 12, 14, and 15. It preserves the Arbiter carve-out: the Arbiter is not an Agent Soul and cannot appear in this directory.

**Verification.** `xion-verify agent-souls` parses every `*.yaml` file in this directory, recomputes `extends_soul_hash` against `genesis/SOUL.md`, checks each tool subset against `genesis/HERMES_TOOL_ALLOWLIST.yaml`, and rejects `agent_id: arbiter`.

**Deprecation.** An Agent Soul is replaced by a new versioned file hash. Runtime migration happens through the Casting Pipeline and is recorded in `ledgers/AGENT_CAST_LEDGER.jsonl`; historical hashes remain auditable.

---

## Required Fields

Each `genesis/AGENT_SOULS/<agent_id>.yaml` file must contain:

```yaml
schema_version: 1
agent_id: research-agent
soul_version: 1
extends_soul_hash: "<sha256 of genesis/SOUL.md at authoring>"
purpose: "What this faculty exists to do."
trigger: {type: cron, schedule: "0 * * * *"}
allowed_tools: []
forbidden_tools: []
mcp_servers_allowed: []
cost_envelope: {monthly_usd: 10, bucket: cognition/specialist/research}
output_destinations: []
arbiter_class: low_risk_specialist_append
limits: {max_turn_depth: 0, max_wall_clock_s: 300, max_tokens_per_run: 8000}
deprecation_path: "How this Soul is paused, replaced, or retired."
```

Additional `property_promised`, `invariants_touched`, `verification`, and `deprecation` fields may duplicate the human-readable four Properties for machine readers.
