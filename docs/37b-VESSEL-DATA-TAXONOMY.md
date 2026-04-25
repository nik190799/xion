# 37b - Vessel Data Taxonomy

> *A vessel may hold data only after it has named the data.*

## Four Questions

**Property promised.** Every vessel that carries Xion classifies each cache, log, sensor capture, derivation, outbound flow, backup, and model update before it handles user traffic. The user can know what exists, where it lives, how it is exported, how it is forgotten, and which parts are outside Xion's control.

**Invariants touched.** Strengthens Invariant 2 by binding `/export`, `/forget`, and `/inspect` to named vessel data classes; strengthens Invariants 5 and 11 by preventing billing, telemetry, or sponsorship records from becoming Covenant gates; strengthens Invariant 6 by preserving refusal evidence; strengthens Invariant 7 by preventing data locality from becoming identity; strengthens Invariant 17 by naming local model fingerprints and training posture.

**Verification.** `xion-verify vessel-compact` will check that every active vessel mode maps its storage, logs, sensors, telemetry, derivations, and outbound flows to this taxonomy. It returns `NOT_YET_SEALED` until a reference Compact exists.

**Deprecation.** Data classes are append-only. A class may be split into stricter sub-classes, but a vessel may not hide a class by renaming it into a weaker bucket.

## Required Per-Class Fields

For each data class it uses, a vessel Compact declares:

- `class_id`.
- `human_description`.
- `source`.
- `storage_location`.
- `operator_or_controller`.
- `retention_window`.
- `default_disposition`.
- `export_reachability`.
- `forget_propagation_rule`.
- `inspect_visibility`.
- `residency`.
- `special_category_flags`.
- `third_party_recipients`.
- `availability_reference` pointing into `docs/37c-VESSEL-AVAILABILITY-MODEL.md`.

If a vessel cannot answer those fields, it is not ready to claim Xion support.

## Data Classes

### `relayed`

Payloads sent to or received from Xion's Relay, including user messages, Xion candidates, Arbiter decisions, refusal metadata, and signed response envelopes.

- **Default disposition:** Relay-governed retention.
- **Export:** Required.
- **Forget:** Propagates through the normal `/forget` path.
- **Inspect:** Required for active user relationships.

### `local_session`

Ephemeral data held only during the active session: render buffers, streaming chunks, short-lived speech-to-text buffers, local UI state, and transient wake-word state.

- **Default disposition:** Delete at session end.
- **Export:** Required when it contains user content or Xion output.
- **Forget:** Immediate local wipe.
- **Inspect:** Mode-dependent, but the existence of the class must be visible.

### `local_persistent`

Declared local cache that persists beyond the active session but is not used as conversation memory. Examples: device settings, cached voice assets, Compact versions, local consent preferences, and proof manifests.

- **Default disposition:** Persist only with declared purpose.
- **Export:** Required when user-specific.
- **Forget:** Clears user-specific entries; non-user proof artifacts may remain if severed from the user.
- **Inspect:** Required.

### `conversation_memory`

State intended to influence future turns: remembered facts, continuity summaries, per-user preferences, relationship history, and memory handles.

This class is distinct from `local_persistent` because it has read-on-future-turn semantics.

- **Default disposition:** Persist only after consent.
- **Export:** Required in a user-readable and machine-readable bundle.
- **Forget:** Deletes raw memory, summaries, embeddings, handles, and cross-vessel replicas.
- **Inspect:** Required before and after deletion.
- **Special rule:** Multi-vessel memory must name its canonical source and merge policy.

### `pending_state`

In-flight writes to Relay, AO Core, ledgers, payment records, disavowal registries, or vessel registries that have not yet confirmed.

- **Default disposition:** Visible pending state, not final history.
- **Export:** Required as "pending/unconfirmed" when user-visible.
- **Forget:** Cancels if not submitted; if submitted, tracks the eventual deletion or compensating action.
- **Inspect:** Required.
- **Special rule:** The vessel may not tell the user a write committed until it has confirmation.

### `derived`

Per-turn embeddings, summaries, classifiers, inferred preferences, risk labels, safety annotations, or routing features.

- **Default disposition:** No longer than the source data unless separately consented.
- **Export:** Required when tied to a user.
- **Forget:** Deletes both derivation and lookup handles; cannot preserve a reidentifiable embedding while deleting the text.
- **Inspect:** Required at class level; detailed vector dumps may be summarized if raw export would expose security internals.

### `time_series_derived`

Continuous or windowed derivations computed outside turn boundaries: biometric trends, movement patterns, affect estimates, room-occupancy signals, or passive-sensor embeddings.

- **Default disposition:** Disabled unless the mode requires it and the user consents.
- **Export:** Required per time window.
- **Forget:** Per-window deletion with a published propagation bound.
- **Inspect:** Required.
- **Special rule:** This class cannot be backfilled into long-term memory after the fact without explicit consent.

### `training`

Any local fine-tune, adapter update, prompt optimization, federated-learning contribution, gradient, or weight delta derived from user interaction.

- **Default disposition:** Off by default.
- **Export:** Required as a training participation receipt and class summary; raw gradients may be security-redacted but must be acknowledged.
- **Forget:** If exact deletion is impossible after aggregation, the Compact must say so before training begins.
- **Inspect:** Required.
- **Special rule:** Training participation cannot be bundled with ordinary conversation consent.

### `manufacturer_telemetry`

Analytics, crash reports, uptime logs, performance traces, ad SDK events, and device diagnostics sent to the vessel operator or manufacturer rather than Xion.

- **Default disposition:** Minimized and off for user content.
- **Export:** Required when user-specific.
- **Forget:** Propagates to the operator's telemetry store when user-linked.
- **Inspect:** Required, including SDK/vendor names.
- **Special rule:** Telemetry may not include raw user content by default.

### `third_party_share`

Any disclosure to named third parties: cloud speech provider, moderation service, support tool, analytics vendor, storage provider, payment provider, sponsor, media host, or integrator.

- **Default disposition:** Disallowed until named.
- **Export:** Required: recipient, purpose, timestamp, class shared.
- **Forget:** Propagates by contract where possible; if impossible, boundary must be visible.
- **Inspect:** Required.

### `backup_retention`

Backups, snapshots, disaster-recovery stores, and manufacturer support images that may contain vessel state.

- **Default disposition:** Time-bound and encrypted.
- **Export:** Required as a retention statement, not necessarily raw backup contents.
- **Forget:** Published maximum purge latency after `/forget`.
- **Inspect:** Required: backup operator, window, encryption and purge promise.
- **Special rule:** Indefinite backups of user content violate the Compact.

### `cross_protocol_bridge`

Data delivered into systems outside Xion's control: SMS, email, Discord, Slack, Telegram, social networks, livestream chat, app-store support systems, and carrier logs.

- **Default disposition:** Allowed only with explicit bridge disclosure.
- **Export:** Xion and the vessel export their side of the bridge; external archives may require user action in the third-party system.
- **Forget:** Xion clears its own state and revokes provenance where applicable; it must not promise impossible erasure of third-party archives.
- **Inspect:** Required: bridge name, retention boundary, and user-facing warning.

### `multi_user_isolation`

Partitioning metadata and transient state used to keep users separate on shared vessels: kiosks, family devices, hospital companions, classrooms, vehicles, and public installations.

- **Default disposition:** Required for shared modes.
- **Export:** User-specific partition state is exportable.
- **Forget:** Clears the user's partition and active working memory before another user begins.
- **Inspect:** Required.
- **Special rule:** If the vessel detects a minor after capture, retroactive minor-protection posture applies to already captured data.

### `sensor_passive`

Always-on or ambient capture used for wake words, proximity, presence, environmental signals, or passive sensing.

- **Default disposition:** Minimized, local-first, short-lived.
- **Export:** Required for retained captures and summaries.
- **Forget:** Deletes retained passive captures linked to the user/session.
- **Inspect:** Required: what is sensed before explicit interaction begins.

### `sensor_active`

Explicitly initiated recording or capture: microphone record, camera capture, screen share, biometric scan, location share, or document scan.

- **Default disposition:** Purpose-limited to the active interaction.
- **Export:** Required.
- **Forget:** Deletes capture, transcript, metadata, and linked derivations.
- **Inspect:** Required.

### `captured_sensor_overflow`

Incidental capture during `sensor_passive` or `sensor_active`: bystander voices, background faces, location-revealing sounds, room layout, visible documents, medical devices, or private surroundings.

- **Default disposition:** Avoid and minimize.
- **Export:** Required when retained.
- **Forget:** Inherits the conversation or capture `/forget` semantics.
- **Inspect:** Required as a risk disclosure even if specific bystanders are not identified.
- **Special rule:** This class cannot be used for training or profiling by default.

### `model_fingerprint`

Identity of any local, hosted, or fallback model used by the vessel: model name, version, weights hash where available, quantization, provider, and sovereignty posture.

- **Default disposition:** Public proof metadata.
- **Export:** Required in response/debug bundles when a model generated or transformed user-visible output.
- **Forget:** Not user-content, but must be severed from user sessions when exporting forgotten interactions.
- **Inspect:** Required.

### `residency`

Jurisdiction and physical or logical region where vessel-local data, backups, telemetry, and third-party shares are stored or processed.

- **Default disposition:** Declared before traffic.
- **Export:** Required as metadata.
- **Forget:** Uses the class-specific rule; residency changes do not weaken `/forget`.
- **Inspect:** Required.

### `lifecycle`

Data present during sale, resale, repair, return, loss, theft, warranty service, decommissioning, or scrap of a hardware vessel.

- **Default disposition:** User content must be wiped before transfer outside the user's control.
- **Export:** Required before irreversible transfer where feasible.
- **Forget:** Required before repair/resale/scrap unless the user explicitly preserves state.
- **Inspect:** Required: reset and wipe posture.

### `special_categories`

Health, location, minors, intimate contexts, biometric identifiers, crisis disclosures, disability data, and other sensitive categories.

- **Default disposition:** Minimized and explicit.
- **Export:** Required with careful labeling.
- **Forget:** Strongest available deletion path; no retention by default.
- **Inspect:** Required.
- **Special rule:** Special-category status follows the data into derivatives, backups, telemetry, and third-party shares.

## Data Class Table

| Class | Export | Forget | Default |
|---|---|---|---|
| `relayed` | required | Relay `/forget` | Relay-governed |
| `local_session` | if user/Xion content | immediate wipe | session-only |
| `local_persistent` | if user-specific | local clear | declared purpose |
| `conversation_memory` | required | all replicas + derivations | consent-only |
| `pending_state` | pending bundle | cancel or compensate | visible pending |
| `derived` | required if user-linked | derivation + handles | source-bound |
| `time_series_derived` | per window | per window | disabled by default |
| `training` | receipt + summary | disclose limits | off by default |
| `manufacturer_telemetry` | if user-specific | operator propagation | minimized |
| `third_party_share` | recipient log | contractual/boundary | named only |
| `backup_retention` | retention statement | max purge latency | time-bound |
| `cross_protocol_bridge` | local side | boundary disclosed | explicit only |
| `multi_user_isolation` | partition state | partition wipe | required shared |
| `sensor_passive` | if retained | retained captures | minimized |
| `sensor_active` | required | capture + derivations | purpose-limited |
| `captured_sensor_overflow` | if retained | inherits capture | avoid |
| `model_fingerprint` | required metadata | sever from session | public proof |
| `residency` | required metadata | class-specific | declared |
| `lifecycle` | before transfer | wipe before transfer | wipe |
| `special_categories` | required | strongest path | minimized |

## Non-Goals

- No vessel-local cache exempt from `/forget`.
- No telemetry exception for user content.
- No hidden training from ordinary conversation consent.
- No claim that Xion can erase third-party archives it does not control.
- No storage of special-category data by default.
