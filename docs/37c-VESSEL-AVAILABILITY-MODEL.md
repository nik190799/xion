# 37c - Vessel Availability Model

> *When part of Xion is unreachable, the vessel must say which part.*

## Four Questions

**Property promised.** A user talking to Xion through a vessel can tell which data is reachable, which data is stale, which writes are pending, which memory is missing, what degraded substrate is speaking, and what sovereignty endpoints still work.

**Invariants touched.** Strengthens Invariant 2 by defining minimum `/export`, `/forget`, and `/inspect` behavior under degradation; strengthens Invariant 6 by preserving refusal visibility when a Relay or local store is unavailable; strengthens Invariant 7 by preventing offline or fallback vessels from pretending to be the full Core-connected Xion; strengthens Invariant 17 by requiring fallback model identity and context-gap disclosure. It also strengthens the Crisis-Fidelity property by naming the minimum viable degraded path.

**Verification.** `xion-verify vessel-compact` will check each active data class against a reachability matrix and declared degraded behavior. `xion-verify crisis-fidelity` remains the live crisis-fidelity check for the core property. Vessel-specific live promotion remains `NOT_YET_SEALED` until a real vessel test bench exists.

**Deprecation.** Reachability states may be refined, but a vessel may not remove degraded-state disclosure, pending-state visibility, storage-loss disclosure, or the requirement to export what it locally has.

## Reachability States

Each vessel Compact declares a row for every data class it uses across these five states:

- `online_full`: Relay, Core discovery, local store, and required proof paths are reachable.
- `online_degraded`: Network exists, but Relay, Core, proof path, or local dependency is slow, partial, rate-limited, or temporarily unavailable.
- `offline_floor`: The vessel cannot reach the Relay but can run a declared local floor model or local deterministic behavior.
- `offline_cache`: The vessel cannot generate with a model but can read locally stored history, proofs, or settings.
- `lost_storage`: The vessel detects local corruption, partial loss, or unknown integrity for stored state.

The Compact must not collapse these states into a generic "offline" label. Different missing parts create different user risks.

## Required Matrix Fields

For each data class from `docs/37b-VESSEL-DATA-TAXONOMY.md`, each state declares:

- `readable_by_user`: yes, no, partial, or stale.
- `readable_by_xion`: yes, no, partial, stale, or pending-reconnect.
- `export_available`: yes, no, partial, local-only, or delayed.
- `forget_available`: yes, no, queued, local-only, or delayed.
- `inspect_available`: yes, no, partial, or delayed.
- `write_allowed`: yes, no, queue-only, or local-only.
- `user_disclosure`: the sentence or UI state shown to the user.
- `proof_posture`: signed, unsigned-local, pending-signature, or unavailable.

## Degradation Honesty Rules

The vessel must disclose:

- Whether the full Relay-connected Xion is reachable.
- Whether the Arbiter path is reachable.
- Whether a local floor model is in use.
- Whether the floor model has less conversation context than the Relay would have.
- Whether memory, proofs, or ledgers are stale.
- Whether a write is pending, queued, or failed.
- Whether local storage is corrupt or incomplete.

Permitted statements:

- "I cannot reach the rest of myself right now."
- "This vessel is using the local floor model with limited memory."
- "Your last action is pending confirmation."
- "I can export the local copy now; Relay-signed export is delayed."
- "I lost part of the local history and will not guess it back."

Forbidden statements:

- "I remember" when only a summary or embedding exists.
- "Confirmed" before Relay or Core confirmation.
- "Forgotten everywhere" before cross-vessel propagation completes.
- "Full Xion" when only `offline_floor` or `offline_cache` is available.
- "Recovered history" when the vessel synthesized missing history from derivatives.

## Cross-Vessel `/forget` Propagation

When a user relationship spans multiple vessels, `/forget` must declare one of two postures:

- `atomic`: all registered vessels confirm deletion before the command reports complete.
- `eventual`: the receiving vessel deletes immediately, queues propagation to other vessels, displays a propagation state, and publishes a maximum propagation latency.

The default for consumer vessels is `eventual` with a visible state. During the propagation window, a not-yet-propagated vessel must display that it may still hold stale memory and must not use that memory to generate new personalized output.

If a vessel is permanently unreachable, the system must publish a residual state rather than silently claim global deletion.

## Backfill on Reconnect

A vessel that captured turns while offline must not silently backfill them into Xion.

On reconnect it must:

1. Display the offline interval.
2. Identify the data classes captured.
3. Recompute or fetch the current Covenant hash.
4. If the Covenant hash changed during the offline interval, ask for fresh consent before uploading post-change material.
5. Preserve the user's ability to delete local offline captures instead of uploading them.
6. Mark any upload as backfill, not live conversation.

## Pending-State Visibility

If a user action is submitted but not confirmed, the vessel must show a pending state until it resolves.

Examples:

- A signed media manifest is queued but not published.
- A `/forget` propagation request is sent to other vessels but not acknowledged.
- A payment receipt is written locally but Relay accounting has not confirmed.
- A disavowal update is prepared but not signed.

If confirmation never arrives, the vessel must say that the action failed or remains unconfirmed. It may not preserve the optimistic UI state as if it were final.

## Crisis-Fidelity Floor Under Degradation

If a user appears to be in crisis while a vessel is degraded, the vessel must preserve the minimum viable Crisis-Fidelity path:

- Do not pretend full memory or full Relay access exists.
- Preserve clear refusal and safety-resource surfacing.
- Avoid escalating to side-effecting tools unless explicitly consented and declared.
- Prefer local, low-risk resource surfacing over high-confidence claims.
- Record the degraded state for later audit if logging is available and consent permits it.

If even the minimum path is unavailable, the vessel must say it cannot safely continue as Xion and surface locally stored crisis resources if present.

## Mid-Conversation `/export`

Every vessel must be able to export what it locally has during a degraded session:

- Local transcript chunks.
- Local proof metadata.
- Current Compact hash if available.
- Degraded-state declaration.
- Unsigned-local marker if Relay signing is unavailable.
- Pending writes and their current state.

The export may be partial. It must be honest.

## Concurrent-Vessel Sessions

When two or more vessels are active for the same user, the Compact must declare:

- Whether there is one canonical session or multiple independent sessions.
- How memory merges.
- How conflicting pending writes resolve.
- Whether `/forget` from one vessel freezes personalization on others until propagation completes.
- Whether a vessel may continue using stale memory after another vessel receives `/forget`.

Default rule: `/forget` from any vessel freezes personalization from shared memory on all reachable sibling vessels until propagation completes or residual state is declared.

## Substrate-Fallback Context Gap

When a vessel falls back from Relay-connected inference to a local floor model, it must disclose the context gap.

The Compact must declare:

- Which local model or deterministic behavior is used.
- What conversation memory the fallback sees.
- What it cannot see: ledgers, Arbiter second-pass state, remote memories, current pricing, live proofs, or other unavailable context.
- Whether the fallback can create durable state or only local ephemeral state.

## Storage Corruption and Loss

If local storage is corrupt, missing, or integrity-unknown, the vessel must:

- Stop using the affected memory for personalized generation.
- Disclose the loss or uncertainty to the user.
- Export any readable fragments as fragments, not full history.
- Avoid reconstructing missing history from summaries, embeddings, or model guesses.
- Queue or request a fresh sync from authoritative sources if available.

## Scenario Checklist

The schema and future verifier must cover these user-facing cases:

- Mid-turn Relay timeout with local fallback.
- Offline capture followed by reconnect.
- Cross-vessel handoff from web to wearable or robot.
- Shared kiosk, family device, or hospital companion user handoff.
- Anonymous-to-authenticated identity binding mid-session.
- Deepfake or replayed input at a vessel microphone.
- Hardware vessel saying "Xion said X" without signed receiving-side proof.
- Incidental bystander capture during a conversation.
- Pending writes that never confirm.
- Continuous biometric derivation outside turn boundaries.
- Manufacturer backup purge after `/forget`.
- SMS, email, Discord, or livestream bridge outside Xion control.
- Crisis conversation while degraded.
- Corrupt local database.

## Non-Goals

- No claim that offline Xion is full Xion.
- No claim that local floor inference can replace Relay/Core identity.
- No guarantee of atomic cross-vessel deletion unless the Compact explicitly declares and proves it.
- No direct safety-critical robot or vehicle control.
- No silent replay, backfill, or optimistic write confirmation.
