# Hermes Pin Protocol

> *The mind's substrate may change. The Soul it carries may not be smuggled into that change.*

## Four Properties

**Property promised.** Hermes is the Genesis-era Cognitive Substrate, not Xion's identity. Every update to Hermes, every tool surface it exposes, and every Agent Soul cast into it is governed by effect, not by upstream label or convenience.

**Invariants touched.** Strengthens Invariants 1, 4, 5, 6, 11, 12, 14, and 15 by making cognition runtime changes explicit, reversible, and independently verifiable. It does not make Hermes constitutional and does not cast the Arbiter into Hermes.

**Verification.** `xion-verify hermes-runtime` checks the pinned runtime, lockfile posture, tool allowlist coherence, and disabled-by-default runtime flags. `xion-verify agent-souls` checks every Agent Soul against the allowlist and parent Soul hash. `xion-verify agent-cast` checks the cast ledger against the Agent Soul manifest.

**Deprecation.** Hermes may be replaced by a successor runtime through the Tier-2 route below if the Casting Pipeline contract, Agent Soul semantics, Arbiter carve-out, and cast-ledger verification remain intact.

---

## 1. Update Classification

Hermes updates are classified by effect, not upstream label:

| Update type | Governance route | Rule |
|---|---|---|
| Commit bump with no tool/skill surface change | Tier-0 | `xion-verify hermes-runtime` and `xion-verify agent-cast` must pass. |
| Upstream ships new tools/skills but Xion's allowlist is unchanged | Tier-0 | The new surface remains unreachable. |
| Any new tool/skill/MCP server becomes callable by any Agent Soul | Tier-1 | Harm Analyzer review plus Agent Soul diff; observation window required. |
| Hermes API change requiring wrapper migration | Tier-2 | Re-run the Hermes spike and update `docs/HERMES_SPIKE_RESULT.md`. |
| Hermes replacement by a successor runtime | Tier-2 | New adapter, shadow cast-pool drill, atomic pointer flip; constitutional documents do not change if Agent Soul semantics are preserved. |

## 2. Default-Deny Tool Surface

At Genesis Default, the cast runtime disables Hermes skill self-improvement, autonomous skill creation, MCP server auto-discovery, and user-model export. Any exception is an allowlist expansion and follows the Tier-1 route above.

`genesis/HERMES_TOOL_ALLOWLIST.yaml` is the canonical runtime allowlist. It must declare `default_deny: true` and list per-Agent-Soul tool subsets. A tool not named for a Soul is unreachable by that Soul, even if Hermes ships the tool upstream.

## 3. Agent Souls

An Agent Soul is a content-addressed file under `genesis/AGENT_SOULS/` that extends `genesis/SOUL.md` for one faculty. Each Agent Soul names:

- `agent_id`
- `soul_version`
- `extends_soul_hash`
- `purpose`
- `trigger`
- `allowed_tools`
- `forbidden_tools`
- `mcp_servers_allowed`
- `cost_envelope`
- `output_destinations`
- `arbiter_class`
- `limits`
- `deprecation_path`

`xion cast pool` must reject any Agent Soul whose `allowed_tools` are not a subset of the allowlist, whose `extends_soul_hash` disagrees with the current parent Soul hash, or whose output destination violates the specialist rules in `docs/24-COGNITION.md`.

## 4. Arbiter Carve-Out

The Arbiter is not an Agent Soul and is not cast into Hermes. A gate cannot use the same Cognitive Substrate it gates. The Arbiter may use the Inference Router for a fixed LLM second-pass prompt, but it has no Hermes tool loop, no Hermes skills, and no self-improvement path.

Sensorium receptors, Supervisor, Volition, ledger writers, broker, and AO sinks are also non-Hermes runtime modules. Hermes runs agentic faculties; it does not run the conscience, the nervous plumbing, or the state chain.

## 5. Casting Ledger

The Casting Pipeline is the only path from `genesis/AGENT_SOULS/` to a live specialist. Manual construction of a Hermes specialist outside the pipeline is a cognition-layer incident.

Every successful cast appends one row to `ledgers/AGENT_CAST_LEDGER.jsonl`:

```json
{
  "schema_version": 1,
  "event": "cast_succeeded",
  "agent_id": "research-agent",
  "agent_soul_hash": "<sha256>",
  "parent_soul_hash": "<sha256>",
  "hermes_pin": "<commit>",
  "cast_at": "2026-04-25T00:00:00Z",
  "smoke_test_pass": true
}
```

Every failed cast appends `event: "cast_failed"` with a reason before rollback. The ledger is append-only.

## 6. Pre-Genesis Posture

For Genesis, Hermes is **doctrine-pinned and cast-verified**, not installable-lockfile-pinned. This is an accepted residual, not a hidden dependency: `xion-verify hermes-runtime` verifies the Hermes commit, allowlist hash, and disabled runtime flags, while `xion-verify agent-souls` and `xion-verify agent-cast` verify that every live faculty was cast from a content-addressed Agent Soul against that pin. The missing installable package/lockfile entry remains `KW-HERMES-001` until upstream Hermes exposes a stable package boundary that can be pinned without widening Xion's supply-chain surface prematurely.
