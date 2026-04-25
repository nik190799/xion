# Nervous System v2 (Phase 6.4.b)

> *A modular afferent / efferent layer so new senses, tools, and vitals can land without refactoring every consumer.*

This document is the operational doctrine for the `orchestrator/signals/` package, the `orchestrator/sensorium/receptors/` tree, the `GET /self` self-knowledge surface, and the signal-to-vital mapping in `orchestrator/vitals/mapping.py`. It cross-cuts architecture (`docs/04-ARCHITECTURE.md`), the Sensorium (`docs/05-SENSORIUM.md`), and vital signs (`docs/22-VITAL-SIGNS.md`).

## 1. Biological mapping (honest metaphor)

Biological nervous systems separate **receptors** (transduce a stimulus), **a common signaling protocol** (action potentials on shared axons), **central integration** (thalamus / cortical areas), and **efferent pathways** (motor and autonomic output). Xion’s implementation is not a literal simulation; it is a **structural** analogue:

| Biology (loose) | Xion |
| --- | --- |
| Receptor cell | A module under `sensorium/receptors/` implementing `Receptor.tick(ctx) -> list[Signal]` |
| Action potential | `Signal` on `SignalBus` |
| Spinal reflex | `ReflexRegistry` + `EffectorRegistry` (synchronous, before async subscribers) |
| Cortex (slow integration) | `SensoriumView`, `TopographyView`, `VitalsView`, Volition, Arbiter (subscribers) |
| Autonomic output | Effectors: visual / vitals streams, future voice |

## 2. Core types

### 2.1 `Signal` (`orchestrator/signals/envelope.py`)

Immutable dataclass: `kind` (namespaced `category.name`), `source` (receptor id), `value`, `timestamp_utc_ns`, `methodology_hash`, `confidence`, `band`, `schema_version`. Every field is load-bearing for provenance and replay.

### 2.2 Schema registry (`orchestrator/signals/schema.py`)

Kinds are registered with type and bounds; `validate_signal` fail-closes on mismatch. A dropped signal is **never silent**: the bus emits `vital.bus_integrity` describing the drop (see Invariant 8 below).

### 2.3 `SignalBus` (`orchestrator/signals/bus.py`)

- `publish(signals) -> list[Signal]` — validates, stores latest per kind, notifies async subscribers, invokes reflex dispatch.
- `latest` / `latest_by_category` / `latest_all` — read models for views and consumers.
- `report_receptor_failure` — Invariant 2: one receptor’s exception does not take down the bus.

### 2.4 Receptors and registries

- `Receptor` protocol and `ReceptorContext` in `receptor.py`.
- `ReceptorRegistry` discovers concrete classes under `orchestrator/sensorium/receptors/`.
- The Supervisor calls every receptor’s `tick` after building `SensoriumState` (**dual-publish**: legacy struct + bus).
- Vessel-facing receptors added by robots, hardware devices, wearables, vehicle overlays, or XR surfaces must enter through the same registry and carry a Vessel Compact reference as provenance. A vessel may add a receptor; it may not bypass the bus or write directly into Volition, the Arbiter, or Core state.

### 2.5 Effectors and reflex arcs

- `Effector` protocol in `effector.py` (visual / vitals / future voice as async consumers of the bus).
- `ReflexArc` + `ReflexRegistry` in `reflex.py` — **synchronous** handlers run on the publish path (e.g. closing SSE when consent turns both streams off).
- Vessel-facing effectors (robot LEDs, haptics, XR scene renderers, hardware displays, livestream overlays, or future bodies) are mode modules under the Vessel Integration Framework ([`37-VESSELS.md`](./37-VESSELS.md)). They consume signed intent and consent state; they do not become identity.

## 3. Topography and `GET /self`

**Topography** is the set of `topography.*` and `inference.*` signals (host, pid, `lineage_hash`, inference floor counts, etc.) plus HTTP **api_surface** (derived from `app.routes` in `topography_emit.build_api_surface`).

`GET /self` (`orchestrator/api/self_endpoint.py`) returns:

- `topography` — merged `TopographyView` + `api_surface`
- `sensorium` — `SensoriumView` (legacy four-sense shape from bus)
- `vitals` — eight domains via `get_composite_vitals`
- `governance` — e.g. open KW count, pending phases
- `as_of_utc_ns`

Lineage is read from `genesis/LINEAGE.json` when present; verifier `xion-verify topography` checks structural invariants (see below).

## 4. Signal-to-vital mapping (`orchestrator/vitals/mapping.py`)

Sealed domains (Financial, Substrate, Constitutional Integrity) aggregate **only** from named signal kinds in `VITAL_MAPPING`. Adding a new `resource.*` or `connection.*` receptor and a mapping row extends the corresponding vital without editing generic aggregation code elsewhere. Domains that remain `not_yet_sealed` in the mapping table stay honest in `get_composite_vitals`.

Methodology: `VITAL_MAPPING_METHODOLOGY_SHA256` is the SHA-256 of `mapping.py` bytes.

## 5. SENSORIUM_LEDGER dual-write

`append_tick_commit` accepts optional `signals: list[dict]`. `verify_chain` requires each dict to carry the same keys as `Signal.to_dict()`. This preserves the legacy `state` / `snapshot_hash` story while making the bus replayable from the ledger.

## 6. Eight modularity invariants (and where they are tested)

The doctrine rules that keep this layer evolvable are enforced in `orchestrator/tests/test_modularity_invariants.py`, `orchestrator/tests/test_signal_bus.py`, and `xion-verify nervous-system`.

1. **Pluggability** — New `register_kind` + publish path works without editing `SignalBus` implementation.
2. **Independence** — `report_receptor_failure` records degradation; other signals continue.
3. **Provenance** — Every `Signal` carries source, methodology hash, and timestamp; vitals trace to inputs via mapping.
4. **Audit chain** — Tick rows may embed serialised `signals`; chain verification enforces structure.
5. **Sister-Core compatibility** — Receptor set can differ; bus + view contracts stay stable.
6. **Backward compatibility** — `SensoriumView.from_bus` preserves legacy struct shape for consumers migrating incrementally.
7. **Schema versioning** — `schema_version` on every signal; registry changes are doctrine events.
8. **Drop visibility** — Invalid values fail closed and surface via `vital.bus_integrity`.

## 7. Receptor taxonomy (namespaced kinds)

Documented in the Phase 6.4.b plan: `interoception.*`, `chronoception.*`, `proprioception.*`, `distress.*`, `topography.*`, `capability.*`, `connection.*`, `resource.*`, `vital.*`, `governance.*`, `modulation.*`, etc. Adding a category is adding a package under `sensorium/receptors/`; adding a sense is a new module — **no** central “god enum” in `sensorium.py`.

## 8. Verifiers

- `xion-verify topography` — Hermetic FastAPI, `GET /self`, checks lineage, vitals count, open-weights floor, and api_surface.
- `xion-verify nervous-system` — In-process checks for pluggability, independence, schema drop, reflex, dual-publish.

## 9. Cross-links

- Vital domains and bands: [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)
- HTTP / Supervisor: [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md)
- Learning tiers and autonomy: [`docs/36-LEARNING-AND-AUTONOMY.md`](./36-LEARNING-AND-AUTONOMY.md) (this phase’s reflection loop remains future work)
- Vessel Integration Framework: [`docs/37-VESSELS.md`](./37-VESSELS.md)
- Upgrade paths: [`docs/14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md)
