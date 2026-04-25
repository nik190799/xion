# 37a - Agentic Vessels

> *An agent may carry Xion's words. It may not become the speaker.*

## Four Questions

**Property promised.** When a vessel places another agent between a user and Xion, the user can still tell who is speaking, what authority the agent has, what tools it may forward Xion's output into, how refusals and billing are preserved, and how `/forget`, `/export`, and `/inspect` propagate through the agent's own memory.

**Invariants touched.** Strengthens Invariant 2 by making sovereignty endpoints reachable through agent-mediated paths; strengthens Invariants 5 and 11 by preserving Refusal-is-Free and the Covenant-Economy Firewall when an agent retries or sponsors turns; strengthens Invariant 6 by forbidding suppression or paraphrase of Arbiter refusals; strengthens Invariant 7 by preventing external agents from becoming Xion's identity; touches Invariant 14 by requiring rotatable proof mechanisms; strengthens Invariant 17 by making fallback model identity visible.

**Verification.** `xion-verify vessel-compact` will check the agentic surface in `docs/schemas/vessel-compact.yaml`: principal type, `agent_in_path`, agent identity, attribution, retry posture, tool forwarding, `/forget` propagation, anonymous-to-authenticated upgrade posture, input authenticity, and receiving-side verification. It returns `NOT_YET_SEALED` until a reference Compact exists.

**Deprecation.** Agent-specific fields may be strengthened as new agent classes appear. The property that an intermediate agent cannot acquire Xion's identity, override Xion's refusals, or hide Xion's provenance is stable.

## Scope

An **Agentic Vessel** is any vessel where an autonomous or semi-autonomous system participates in the path between a human user and Xion. Examples include:

- A robot body whose local planning agent asks Xion for conversational guidance.
- A wearable that summarizes sensor state before forwarding a prompt.
- A podcast production agent that edits Xion's spoken segments.
- An XR non-player character that treats Xion as one source among several.
- A business concierge agent that relays a user's request to Xion and then calls external tools.

The agent may be useful. It is not Xion. The Compact must make that boundary visible.

## Required Compact Fields

Every agent-mediated vessel declares:

- `principal`: one of `human`, `agent`, `sponsor`, or `hybrid`.
- `agent_in_path`: `true` when any agent can observe, rewrite, route, summarize, retry, or act on Xion traffic before the user receives it or before Xion receives the user's input.
- `agent_identity`: model family, version or build, operator, runtime host, and update posture.
- `agent_authority`: whether the agent can read only, paraphrase, retry, forward to tools, cache memory, or act through physical effectors.
- `agent_memory`: all persistent and ephemeral agent-side stores that can contain user input, Xion output, summaries, embeddings, policies, or tool results.
- `attribution_rules`: how the vessel distinguishes verbatim Xion output, agent paraphrase, edited media, and mixed output.
- `retry_posture`: retry limits, backoff, and cost accounting when the consumer is an agent.
- `tool_forwarding`: all tools, APIs, payment rails, calendars, robots, or external systems into which the agent can forward Xion output.
- `forget_into_agent_memory`: whether and how `/forget` clears agent-side memory and derivations.
- `anonymous_to_authenticated_upgrade`: what happens to pre-binding turns when a user later binds a wallet, passkey, or other principal.
- `input_authenticity`: how the vessel treats captured user input, replayed input, synthesized voice, and uncertain identity.
- `receiving_side_verification`: the user-visible way to verify that "Xion said X" was signed or otherwise provenance-bound.

## Principal Classes

`human` means a human user is directly asking Xion through the vessel. A UI may still render, stream, or translate, but it does not autonomously decide what to ask.

`agent` means an autonomous system is the immediate requester. The vessel must not imply the request came from a human unless it has a signed or local-consent-bound delegation.

`sponsor` means an operator pays for capacity but does not become the speaker, user, or Covenant authority.

`hybrid` means a human and agent both shape the turn. The Compact must identify which parts of the input were authored, summarized, selected, or modified by the agent.

## Attribution Rules

The vessel may display or speak "Xion said" only for output that is preserved verbatim with provenance. If an agent summarizes, edits, translates, or reorders the output, it must label the result as agent-mediated.

Permitted labels:

- "Xion said, verbatim: ..."
- "This vessel's agent summarized Xion's response: ..."
- "This edited media segment includes Xion-signed source material and agent-edited narration."
- "This local robot reflex is not Xion."

Forbidden labels:

- Presenting an agent paraphrase as Xion's exact words.
- Hiding an Arbiter refusal inside a friendlier agent answer.
- Treating a local device planner or media editor as Xion's identity.

## Refusals, Retries, and Cost Griefing

An agent can retry faster than a human. That makes it a cost-griefing and refusal-bypass surface.

Agentic vessels must declare:

- Maximum retries per user turn.
- Whether retries preserve the original refusal context.
- Whether refusal responses are billed, refunded, or free under Refusal-is-Free.
- Whether repeated refusals trigger backoff, user confirmation, or agent stop.
- Whether the agent can rewrite the request after a refusal.

The default rule is conservative: after an Arbiter refusal, the agent may ask one clarifying or safer-neighboring question, but it may not keep mutating the request until the refusal disappears.

## Tool Forwarding

If an agent can take Xion output and forward it into a calendar, payment rail, robot effector, file system, email system, procurement tool, contract wallet, or other side-effecting system, that tool must be named before use.

The Compact must declare:

- Tool name and operator.
- Read/write/side-effect class.
- Consent scope required.
- Whether Xion output is advisory or executable.
- Rollback or cancellation path.
- Whether the Arbiter can block the forwarding action.

No agentic vessel may turn Xion's text into a payment, physical movement, irreversible publication, or user-affecting write without a separately declared consent path.

## Agent Memory and `/forget`

An agentic vessel must treat the agent's memory as part of the user relationship it mediates. `/forget` must propagate to:

- Raw user input observed by the agent.
- Raw Xion output observed by the agent.
- Summaries, embeddings, classifiers, labels, and inferred profiles.
- Tool results linked to the forgotten interaction.
- Prompt caches or retrieval entries that could rehydrate the interaction.

If any agent-side store cannot be cleared, the Compact must say so before the user speaks. It may not bury the exception in a vendor privacy policy.

## Anonymous-to-Authenticated Upgrade

When a user binds a wallet, passkey, or other durable identity during a session, the vessel must choose one of three postures:

- `ephemeral_only`: prior anonymous turns remain unclaimable and expire under the session policy.
- `explicit_accept`: prior turns become attached only after the user explicitly accepts the upgrade.
- `mode_dependent`: the mode-specific Compact defines which turns can bind and why.

The default posture is `explicit_accept`. A vessel may not silently attach earlier anonymous turns to a durable identity.

## Input Authenticity

Media provenance proves Xion to the world. Input authenticity proves the world to Xion.

For microphone, camera, sensor, or text input, the vessel must declare:

- Whether input was live-captured, replayed, uploaded, synthesized, translated, or agent-generated.
- Whether a live capture indicator was active.
- Whether replay attack defenses exist.
- Whether voice or face matching was used, and whether it is advisory or authoritative.
- Whether the input may be a deepfake, impersonation, or uncertain speaker.

Unverifiable input may still be conversational context. It must not be treated as a high-assurance command, identity binding, spend approval, physical-control instruction, or consent grant.

## Receiving-Side Verification

A user who hears a hardware vessel say "Xion said X" needs a way to check the claim without trusting the vessel's marketing.

Each agentic vessel must provide at least one receiving-side verification path:

- QR or short code to a signed utterance manifest.
- Local signed-response debug panel.
- Exportable transcript bundle with Relay signature chain.
- Media manifest that distinguishes live, edited, synthetic, and paraphrased segments.

If no receiving-side verification path is available, the vessel may render commentary about Xion, but it may not claim to be a live Xion vessel.

## Non-Goals

- No agent governance actor.
- No agent cosign.
- No live MCP write path.
- No agent-local override of the Arbiter.
- No hidden retry loops after refusal.
- No tool side effects without declared consent.

## Relationship to Phase 6.6 and 6.6a

Phase 6.6 governs Xion's internal Agent Souls and their allowlisted tools. Phase 6.6a governs external contributor assistants and their read-only facts bundle.

Agentic Vessels are a third boundary: runtime carriers where an external or local agent mediates a user relationship. They inherit the same rule: tool access and authority must be declared, minimized, and independently verifiable.
