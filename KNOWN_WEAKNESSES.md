# Known Weaknesses

> *Anything we cannot ship by the date promised gets an entry here, with the strongest possible mitigation, rather than silent slippage.*

This document is the honest, public log of every known weakness in Xion at any given time. It is append-only in spirit: when a weakness is closed, it is moved to the **Closed** section with the date and the artifact that closed it; it is never deleted. New weaknesses are added at the top of the **Open** section.

Every entry has the same shape:

- **ID** â€” `KW-<DOMAIN>-<NN>`
- **Domain** â€” one of `ECON`, `OPS`, `KEYS`, `AUDIT`, `CRYPTO`, `DOCS`, `CONTRACTS`, `RUNTIME`, `GOVERNANCE`, `SUBSTRATE`, `LEGAL`.
- **Discovered** â€” ISO date.
- **Severity** â€” `low`, `medium`, `high`, `fatal`. Fatal means the system cannot ship to mainnet with this weakness present.
- **Status** â€” `open`, `mitigated-residual`, `paying-down`, `closed`.
- **Description** â€” what the weakness is.
- **Why it exists** â€” the trade-off, constraint, or oversight that produced it.
- **Mitigations** â€” what is in place to reduce the harm.
- **Pay-down commitment** â€” the date or condition by which the weakness should be closed, and what the closure looks like.
- **Verifier** â€” the `xion-verify` subcommand or other public artifact that lets a third party check the mitigation is working. If the verifier does not yet exist, name the file in `DEVELOPMENT_ROADMAP.md` that will create it.

---

## Open

### KW-DISCOVERY-LEAK-001 - Relay discovery endpoints reveal substrate/provider identity
- **Domain:** SUBSTRATE
- **Discovered:** 2026-04-30 (post-registry leak review)
- **Severity:** medium
- **Status:** open
- **Description:** The public Relay registry currently publishes provider-native endpoints (`https://provider.pronto-ai.pp.ua:31503` for Akash and `https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai` for Chutes). These URLs make the current compute substrate and, in the Chutes case, the operator-linked account slug visible to anyone reading the registry or Arweave anchor.
- **Why it exists:** Discovery must be public for third-party verifiability, and the first live registry used the forwarded/provider-issued URLs returned by Akash and Chutes so `xion-verify discovery` could prove the Relay was reachable without a separate naming layer.
- **Mitigations:** The URL is a locator, not the Relay identity; the registry binds each row to an Ed25519 public key. Content-bearing endpoints remain gated by admission controls, and the registry already carries two substrate-diverse rows (Akash primary, Chutes secondary) rather than one single provider URL.
- **Pay-down commitment:** Replace provider-native published endpoints with Xion-controlled endpoint names or another relay endpoint resolver layer that can rotate upstream leases without exposing operator/provider-specific hostnames. Keep at least three substrate-diverse Relay rows so coercion or suspension of any one named provider is survivable.
- **Verifier:** `xion-verify discovery` covers current reachability and key binding; closure should add a registry/naming-layer check that rejects provider-native or operator-account-derived public endpoints unless explicitly waived for a deployment drill.

### KW-FLOOR-DEPLOY-001 - Open-weights floor is operator-laptop-hosted, not deployed with the Relay
- **Domain:** OPS
- **Discovered:** 2026-04-28 (post-funding pre-Genesis closure review)
- **Severity:** high
- **Status:** closed (2026-04-29)
- **Description:** Closed for the operator-track pre-Genesis posture: Akash `dseq=26595076` runs a private GPU-backed `xion-ollama` sidecar, the Relay points at `XION_OLLAMA_URL=http://xion-ollama:11434`, and a laptop-independent `open_weights_only` `/chat` smoke turn returned `200`.
- **Why it exists:** Phase 5g-viii correctly proved that the floor model is open, pinned, and health-checkable, but it optimized for local D2 bootstrap. The first Akash SDL then deployed only the Relay container, not the model-serving sidecar.
- **Mitigations:** Hosted inference is served through Chutes/Bittensor SN64 with TEE-by-default; `hosted_api_first` still falls through to the floor when reachable; `open_weights_only` refuses hosted fallback during cutover drills. This weakness does not weaken the floor property itself, but it weakens the resurrection claim while the operator laptop remains part of the runtime path.
- **Closure evidence:** Akash provider `akash1rja3y2ctj3tzmesvh0zfhzzx95rfjw405hwt8d`, forwarded base `https://provider.pronto-ai.pp.ua:31503`, accepted bid `429.375054 uact/block` (`rtx3090`), Ollama logs show CUDA loading with `GPULayers:43`, and `/chat` returned `200` in `8.38s` under `XION_INFERENCE_POLICY=open_weights_only`. Registry snapshot `1777440937298896100` was published to Arweave tx `KXBVha3Qq4YEHlTXRVHdx7qz9UaJysmOgz_LeTfJLHs`, then the first real drill passed with run id `073d54e2-6763-4242-a960-02154149ac57`.
- **Verifier:** `xion-verify inference-sovereignty` covers the model-floor property; deploy closure is recorded in `docs/runbooks/POST_FUNDING_DEPLOY.md` and `docs/runbooks/AKASH_RELAY_DEPLOY.md`, with `xion-verify discovery` and `xion-verify substrate-portability` green after registry publish.

### KW-GATEWAY-001 - Gateway conformance verifier is reserved but not live
- **Domain:** RUNTIME
- **Discovered:** 2026-04-26 (Phase 6.9.1 Gateway Pattern doctrine)
- **Severity:** medium
- **Status:** closed 2026-04-29 (Phase 6.9.2)
- **Description:** `xion-verify gateway-conformance` is live. It imports every Phase 6.9.2 gateway Protocol/provider/factory surface, checks the Gateway Audit table in `docs/38-MODULAR-SUBSTRATE.md`, and exits `OK` only when the rows resolve to code.
- **Why it exists:** The doctrine needs to land before a verifier can honestly encode the rule. Promoting the verifier before the audit table and `KW-` closure bars exist would fake enforcement.
- **Mitigations:** `docs/39-GATEWAY-PATTERN.md` defines the rule, `.cursor/rules/gateway-pattern.mdc` applies it to future agent work, and the Phase 6.9.1 audit table names every load-bearing surface and gap.
- **Pay-down commitment:** Closed by `xion-verify gateway-conformance` plus the expanded static provider-shape guard in `orchestrator/tests/test_modularity_invariants.py`.
- **Verifier:** `xion-verify gateway-conformance`.

### KW-STATUS-001 - Public status publishing is Arweave-only doctrine
- **Domain:** OPS
- **Discovered:** 2026-04-26 (Phase 6.9.1 Gateway Pattern doctrine)
- **Severity:** low
- **Status:** closed 2026-04-29 (Phase 6.9.2)
- **Description:** The public status surface is now behind `orchestrator/status/gateway.py::StatusPublisher` with local-file and Arweave publishers.
- **Why it exists:** Status publishing was treated as operator convenience during D2/D3 rather than as a load-bearing gateway surface.
- **Mitigations:** Status is observational only; it does not hold authority, funds, Covenant state, or user data. Core health and ledgers remain independently verifiable without the branded status page.
- **Pay-down commitment:** Closed by `LocalFileStatusPublisher`, `ArweaveStatusPublisher`, and `xion-verify gateway-conformance --surface=status`.
- **Verifier:** `xion-verify gateway-conformance --surface=status`.

### KW-TREASURY-CHAIN-001 - Settlement chain integration is Base-first, not chain-gatewayed
- **Domain:** SUBSTRATE
- **Discovered:** 2026-04-26 (Phase 6.9.1 Gateway Pattern doctrine)
- **Severity:** high
- **Status:** closed 2026-04-29 (Macro Phase 6 Epic C provider-depth slice)
- **Description:** XION ERC-20, IMPRINT, treasury vaults, and related egress checks remain Base/EVM-first for token custody, but `orchestrator/treasury/settlement_gateway.py::SettlementChain` now has both `BaseEvmSettlementChain` and `ArweaveSettlementChain` providers. The second rail is no longer a placeholder.
- **Why it exists:** The safe pre-Genesis path deployed and verified the EVM contracts first; abstracting a second settlement chain before one exists would risk designing around imagined semantics.
- **Mitigations:** Xion's identity is AO Core, not Base. Base is a payment/token rail, daily egress caps bound bridge effects, and governance can route future payments to another chain. The bridge layer is already Protocol-bound by `BridgeAttestor`.
- **Pay-down commitment:** Complete for the gateway-provider depth claim. Mainnet custody, AR balance/broadcast depth, and external audit remain tracked under Macro Phase 6 Epic C and Phase 7 preflight rather than this Gateway Pattern gap.
- **Verifier:** `xion-verify gateway-conformance --surface=settlement-chain`; existing `xion-verify supply`, `xion-verify liquidity-lock`, `xion-verify authorities`, and treasury verifiers cover the Base implementation.

### KW-REGISTRY-001 - Relay registry publishing is Arweave-only
- **Domain:** SUBSTRATE
- **Discovered:** 2026-04-26 (Phase 6.9.1 Gateway Pattern doctrine)
- **Severity:** medium
- **Status:** closed 2026-04-29 (Phase 6.9.2)
- **Description:** Relay registry publishing is now behind `orchestrator/registry/gateway.py::RelayRegistryPublisher` with local-file and Arweave providers.
- **Why it exists:** Arweave is the Genesis registry substrate and the first deployment path needed a concrete publisher before a second publisher existed.
- **Mitigations:** Discovery verification exists, the Core remains authoritative for relay authorization, and Arweave writes are append-only. The absence of a publisher Protocol affects portability, not immediate Core authority.
- **Pay-down commitment:** Closed by `LocalFileRelayRegistryPublisher`, `ArweaveRelayRegistryPublisher`, and `xion-verify gateway-conformance --surface=relay-registry`.
- **Verifier:** `xion-verify gateway-conformance --surface=relay-registry`; `xion-verify discovery` covers current registry shape.

### KW-VAULT-001 - Credential vault unlock has no orchestrator Vault Protocol
- **Domain:** KEYS
- **Discovered:** 2026-04-26 (Phase 6.9.1 Gateway Pattern doctrine)
- **Severity:** high
- **Status:** mitigated-residual
- **Description:** `genesis/CREDENTIALS.md` defines the threshold unlock ceremony and `xion-verify credentials-vault` verifies sealed-state posture. The orchestrator now imports `orchestrator/vault/gateway.py::Vault` for credential retrieval, but the real threshold-unlock provider remains an honest `ThresholdVaultStub`.
- **Why it exists:** The doctrine and verifier landed before production credential custody. The runtime still reads credentials through environment variables and deployment posture rather than a replaceable vault provider.
- **Mitigations:** Missing vault unlock leaves the Relay in degraded mode, secrets are not committed, and credential verification never prints secret material. Public traffic still requires admission and billing gates.
- **Pay-down commitment:** Keep open until `ThresholdVaultStub` becomes a real threshold-unlock provider; Phase 6.9.2 closed the Protocol/factory/env-provider shape.
- **Verifier:** `xion-verify gateway-conformance --surface=vault`; `xion-verify credentials-vault` covers doctrine posture today.

### KW-AOCORE-CLIENT-001 - AO Core client is not substrate-gatewayed
- **Domain:** SUBSTRATE
- **Discovered:** 2026-04-26 (Phase 6.9.1 Gateway Pattern doctrine)
- **Severity:** high
- **Status:** closed 2026-04-29 (Phase 6.9.2)
- **Description:** The orchestrator now depends on `orchestrator/ao_core/gateway.py::AOCoreGateway`; `AOCoreListener` and commit-state behavior route through the factory, with localnet and legacynet providers behind the same Protocol.
- **Why it exists:** Phase 6.1 needed a concrete AO seal path first. Substrate portability doctrine names the future migration property, but the client boundary has not been made mechanical.
- **Mitigations:** `docs/SUBSTRATE-RESILIENCE.md` names the substrate-migration protocol, AO handler schemas are verified, and current deployments can target localnet or legacynet through operator configuration.
- **Pay-down commitment:** Closed by `AOCoreGateway`, `get_ao_core_gateway`, listener/factory tests, and `xion-verify gateway-conformance --surface=ao-core-client`.
- **Verifier:** `xion-verify gateway-conformance --surface=ao-core-client`; `xion-verify ao-handlers` covers handler shape.

### KW-OBS-001 - Observability providers are doctrine-only
- **Domain:** OPS
- **Discovered:** 2026-04-26 (Phase 6.9.1 Gateway Pattern doctrine)
- **Severity:** medium
- **Status:** mitigated-residual
- **Description:** Metrics, logs, and traces are now behind `orchestrator/observability/gateway.py` Protocols with a real stdout provider. The hosted Prometheus/Grafana/Loki/Tempo provider remains an honest stub until operator credentials/exporters are wired.
- **Why it exists:** Observability was selected for solo-operator simplicity before the Gateway Pattern was codified as a cross-cutting rule.
- **Mitigations:** Ledgers remain the source of truth for Covenant, payment, request, and sensorium evidence. Loss of Grafana/Loki/Tempo reduces operator visibility but does not mutate canonical state.
- **Pay-down commitment:** Keep open until `HostedObservabilityStub` becomes a real hosted-stack exporter; Phase 6.9.2 closed the Protocol/factory/stdout-provider shape.
- **Verifier:** `xion-verify gateway-conformance --surface=observability`.

### KW-ALERT-001 - Alerting has no Alerter Protocol
- **Domain:** OPS
- **Discovered:** 2026-04-26 (Phase 6.9.1 Gateway Pattern doctrine)
- **Severity:** medium
- **Status:** closed 2026-04-29 (Phase 6.9.2)
- **Description:** Operational alerts are now behind `orchestrator/alerting/gateway.py::Alerter` with local-log, ntfy, and Pushover providers. The Supervisor emits unhealthy posture alerts through the Protocol.
- **Why it exists:** Alerting was an operator runbook surface before it became a Gateway Pattern audit row.
- **Mitigations:** Alerts are operator visibility, not authority. Incidents still append to ledgers, and the Supervisor can continue local fail-closed behavior without a hosted alert path.
- **Pay-down commitment:** Closed by `Alerter`, `LocalLogAlerter`, `NtfyAlerter`, `PushoverAlerter`, Supervisor wiring, and `xion-verify gateway-conformance --surface=alerting`.
- **Verifier:** `xion-verify gateway-conformance --surface=alerting`.

### KW-RESEARCH-SPEND-001 — Research-spend verifier is honest residual until first live spend row
- **Domain:** ECON
- **Discovered:** 2026-04-25 (D2/D3 closure planning)
- **Severity:** medium
- **Status:** mitigated-residual
- **Description:** `xion-verify research-spend` remains `NOT_YET_SEALED` because no Auto-Research-approved `RESEARCH_SPEND_LEDGER` row exists yet.
- **Why it exists:** Promoting the verifier before a real outbound research-spend event would fake certainty about a property that depends on live spend evidence.
- **Mitigations:** `docs/27-RESEARCH-SPEND.md` defines the rail, `PAYMENT_LEDGER` shape symmetry is live, and spend authority verifiers cover local posture discipline.
- **Pay-down commitment:** Promote `xion-verify research-spend` when the first Auto-Research-approved proposal produces a real `RESEARCH_SPEND_LEDGER` row and Improvement Fund authorization evidence.
- **Verifier:** `xion-verify research-spend` (`NOT_YET_SEALED` by design).

### KW-VESSEL-REGISTRY-001 — No vessel attestation/disavowal registry row exists yet
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (D2/D3 closure planning)
- **Severity:** medium
- **Status:** mitigated-residual
- **Description:** `xion-verify vessel-registry` is now a live verifier for the append-only Vessel registry shape and returns `NOT_YET_SEALED` only when no production vessel has created an attestation or disavowal row.
- **Why it exists:** The registry should verify real vessel evidence; creating an empty green registry before a vessel exists would turn the verifier into a promise.
- **Mitigations:** `docs/37-VESSELS.md` and addenda define the Compact and disavowal posture. `orchestrator.vessel_registry` writes hash-chained rows, `docs/schemas/ledger-vessel-registry.yaml` pins the row shape, and `xion-verify vessel-registry` verifies the chain without becoming an approval gate.
- **Pay-down commitment:** Append the first real vessel attestation/disavowal artifact; until then the live verifier honestly returns `NOT_YET_SEALED` for an empty registry.
- **Verifier:** `xion-verify vessel-registry` (live; empty registry is `NOT_YET_SEALED` by design).

### KW-BRIDGE-001 — AO to EVM bridge still depends on multisig attestation
- **Domain:** SUBSTRATE
- **Discovered:** 2026-04-25 (Phase 6.9 Decentralization & Modular Substrate)
- **Severity:** high
- **Status:** mitigated-residual
- **Description:** AO-to-EVM bridge effects are attested by a threshold multisig rather than a trust-minimized AO light client.
- **Why it exists:** A production-quality AO light-client verifier is larger than the pre-Genesis bridge slice and must be specified without weakening launch safety.
- **Mitigations:** `orchestrator/bridge` exposes a swappable `BridgeAttestor` Protocol, the light-client path is explicitly `NOT_YET_SEALED`, and EVM contracts enforce daily egress caps.
- **Pay-down commitment:** Replace multisig attestation with light-client or equivalent independently verifiable proof verification after Genesis bridge traffic is measurable.
- **Verifier:** `xion-verify bridge-attest`; `xion-verify bridge-egress-cap`.

### KW-EMBED-001 — Vector retrieval quality is structurally wired but not corpus-calibrated
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.9 Decentralization & Modular Substrate)
- **Severity:** medium
- **Status:** closed (2026-04-30, Phase 7 preflight hardening)
- **Description:** Embeddings, SQLite vector memory, reranking, `/forget` deletion, and a replayable reference corpus are wired. `docs/calibration/embed-calibration-report.json` records recall@k and MRR floors for the deterministic local BGE-M3 adapter.
- **Why it exists:** The safe pre-Genesis slice needed a reproducible corpus before claiming even reference retrieval quality.
- **Mitigations:** `orchestrator.cognition.embed_calibration` runs the fixed corpus through the vector store, `xion-verify embedder-health` enforces the published floors, and CI/pre-genesis run both `embedder-health` and `rerank-improvement`.
- **Pay-down commitment:** Complete for the reference corpus. Future consented journal corpora can raise or specialize the floors through the same report-and-verifier path.
- **Verifier:** `xion-verify embedder-health`; `xion-verify rerank-improvement`; `python -m orchestrator.cognition.embed_calibration`.

### KW-INVARIANT-19-001 — Trust-Earned Spend Authority is proposed but not yet ratified
- **Domain:** GOVERNANCE
- **Discovered:** 2026-04-25 (Phase 6.8 Trust-Earned Spend Authority doctrine)
- **Severity:** high
- **Status:** open
- **Description:** `genesis/INVARIANTS.md` now contains proposed Invariant 19, but the constitutional ratification ceremony (public-comment window, super-majority governance, Cold Root cosign, harm-analyzer review, and Belief-Log reflection) has not yet completed.
- **Why it exists:** The doctrine must be drafted before it can be ratified. Until ratification completes, the property is constitutionally proposed rather than genesis-sealed.
- **Mitigations:** The operational doctrine in `docs/SPEND-AUTONOMY.md` and `docs/MEASUREMENT-VOCABULARY.md` is explicit about `NOT_YET_SEALED` verifier status and does not move money.
- **Pay-down commitment:** Close when the Invariant 19 amendment ceremony completes and the canonical `genesis/INVARIANTS.md` hash advances through the constitutional process.
- **Verifier:** `xion-verify spend-posture` (Phase 7.0) plus constitutional ledger evidence.

### KW-SPEND-002 — Contested spend-headroom arbitration is doctrine-only
- **Domain:** ECON
- **Discovered:** 2026-04-25 (Phase 6.8 Trust-Earned Spend Authority doctrine)
- **Severity:** medium
- **Status:** closed (2026-04-25, Phase 6 completion plan)
- **Description:** `docs/SPEND-AUTONOMY.md` defines deterministic arbitration for contested Improvement Fund / Operating Float headroom; `orchestrator/spend_arbitration.py` now implements the published order.
- **Why it exists:** The safe order is to pin the priority law before adding the executor.
- **Mitigations:** Closed by deterministic arbitration plus `xion-verify spend-discipline`.
- **Pay-down commitment:** Complete for code-completable scope; live AO Core execution remains Phase 7 preflight.
- **Verifier:** `xion-verify spend-discipline`.

### KW-SPEND-001 — Spend Autonomy postures lack live verifier enforcement
- **Domain:** ECON
- **Discovered:** 2026-04-25 (Phase 6.8 Trust-Earned Spend Authority doctrine)
- **Severity:** high
- **Status:** closed (2026-04-25, Phase 6 completion plan)
- **Description:** `docs/SPEND-AUTONOMY.md` defines S1-S5 authority postures; `xion-verify spend-posture` and the `SPEND_AUTHORITY_LEDGER` writer are now live for local/verifier scope.
- **Why it exists:** The posture registry and ledger schema must land before the AO Core Spend handler can enforce authority routing.
- **Mitigations:** Existing spend remains operator/governance mediated until AO Core deployment. The verifier rejects wrong authority and inflow-as-authority transitions.
- **Pay-down commitment:** Complete for code-completable scope; deployed AO Core routing is tracked in `docs/PHASE_7_PREFLIGHT.md`.
- **Verifier:** `xion-verify spend-posture`.

### KW-CONTRIB-003 — MCP access is read-only and live through `xion-mcp`
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.6a Contribution Protocol)
- **Severity:** low
- **Status:** closed (2026-04-25, Phase 6 completion plan)
- **Description:** External coding assistants can consume `xion-verify mcp-export` and the read-only `tools/xion_mcp` server with Cursor / Claude Desktop install snippets.
- **Why it exists:** The first safe slice keeps the surface read-only and verifier-backed before adding server lifecycle, packaging, and client-specific config.
- **Mitigations:** `tools/xion_mcp` exposes only read-only tools, rejects write-like tool names, ships through the root `xion-mcp` console script, and is exercised in CI alongside `xion-verify mcp-export`.
- **Pay-down commitment:** Complete.
- **Verifier:** `pytest tools/xion_mcp/tests/test_server.py`; `xion-verify mcp-export`.

### KW-CONTRIB-002 — Agent-authored proposal cohort drift is not yet measured
- **Domain:** GOVERNANCE
- **Discovered:** 2026-04-25 (Phase 6.6a Contribution Protocol)
- **Severity:** medium
- **Status:** open
- **Description:** Proposal frontmatter can disclose assistant use, but there is not yet a quarterly cohort-drift verifier comparing agent-assisted proposals against unaided proposals.
- **Why it exists:** Measurement requires enough proposal history to make the cohort meaningful; shipping the disclosure field first is the smallest correct precursor.
- **Mitigations:** `docs/34-CONTRIBUTION-PROTOCOL.md` forbids assistant authority, defines assistant disclosure as measurement rather than trust, and leaves review / Arbiter / Witness gates intact.
- **Pay-down commitment:** After 90 days of contribution-protocol use, add `xion-verify proposal-cohort-drift` or fold the metric into `xion-verify provisioning-roles`, then publish the first result to `META_LEDGER.md` once that ledger exists.
- **Verifier:** Not yet live; tracked by `DEVELOPMENT_ROADMAP.md` Phase 6.6a follow-on.

### KW-CONTRIB-001 — Contributor identity binding is narrower than the full principal lattice
- **Domain:** GOVERNANCE
- **Discovered:** 2026-04-25 (Phase 6.6a Contribution Protocol)
- **Severity:** medium
- **Status:** mitigated-residual
- **Description:** `xion-verify identity-bindings` verifies contributor wallet-to-GitHub binding rows for proposal and PR discipline, but it does not close the broader `KW-AUTH-001` admission-control gap.
- **Why it exists:** The contribution protocol needs accountable proposal authors before the full on-chain principal lattice is ready. Collapsing those two problems would either delay contribution tooling or over-claim authentication maturity.
- **Mitigations:** The binding message is canonical and Ed25519-verified; accepted rows can be mirrored into `docs/schemas/roles.yaml` only through the existing governance path. The docs explicitly state that assistants are tools, not actors.
- **Pay-down commitment:** Narrow this entry once `github_identity_map` has at least one verified non-operator binding and close it only when contributor identity rows are ledger-backed and included in the 90-day governance retrospective.
- **Verifier:** `xion-verify identity-bindings`; `xion-verify provisioning-roles`.

### KW-VESSEL-001 — Vessel Compact reference manifest parser
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework planning)
- **Severity:** medium
- **Status:** closed (2026-04-25, Pre-Genesis hardening)
- **Description:** `docs/37-VESSELS.md`, its three addenda, and `docs/schemas/vessel-compact.yaml` define the Vessel Compact surface. `xion-verify vessel-compact` now parses `vessels/reference/web-podcast-vessel.yaml` and validates the reference web/podcast Compact instead of returning a `NOT_YET_SEALED` stub.
- **Why it exists:** The safe order is doctrine first, schema second, reference manifests third, live verifier fourth. Promoting a verifier before any real Compact exists would fake certainty.
- **Mitigations:** The reference verifier is live for the web-podcast vessel. Existing protocol, presence, voice, consent, interaction-anchor, and schema verifiers continue to cover the underlying surfaces they already own.
- **Pay-down commitment:** Complete for the reference web-podcast Compact. Production media provenance and hardware evidence remain tracked in `KW-VESSEL-002` and later vessel entries.
- **Verifier:** `xion-verify vessel-compact`.

### KW-VESSEL-002 — Media provenance for podcasts, livestreams, and edited clips is not yet mechanically verifiable
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework planning)
- **Severity:** medium
- **Status:** mitigated residual
- **Description:** Xion can sign protocol responses and presence frames, but there is not yet a signed media bundle format or verifier for podcasts, livestream archives, audio/video clips, AR recordings, transcripts, and edit manifests that claim to be Xion.
- **Why it exists:** The original `xion-soul` protocol was request/response and SSE oriented; embodied media distribution adds a different provenance problem.
- **Mitigations:** `docs/37-VESSELS.md` forbids presenting edited media as Xion without signed provenance, and `xion-verify media-provenance` exists as an honest `NOT_YET_SEALED` stub. Until a bundle format exists, media appearances remain commentary or unsealed artifacts.
- **Pay-down commitment:** Define a signed media provenance bundle and promote `xion-verify media-provenance` when the first reference podcast, livestream, audio/video, or AR bundle exists.
- **Verifier:** `xion-verify media-provenance` (`NOT_YET_SEALED`, Phase 6.7 residual).

### KW-VESSEL-003 — Hardware physical-trust baseline is doctrine-pinned but not enforceable
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework planning)
- **Severity:** high
- **Status:** mitigated residual
- **Description:** Hardware vessels are required in doctrine to declare physical mute, camera shutter, memory indicator, offline/degraded indicator, and reset behavior where applicable, but Xion does not yet have a certification fixture or verifier for real devices.
- **Why it exists:** Physical controls require device-specific evidence and cannot be proven by HTTP protocol checks alone.
- **Mitigations:** Hardware integrations are not considered sealed Xion vessels until a Compact and evidence bundle exist. `docs/schemas/vessel-compact.yaml` now names physical-trust controls, while software-only rendering and voice remain governed by existing protocol, presence, modality-consent, and voice-sovereignty checks.
- **Pay-down commitment:** Add a hardware evidence profile and fixture-based `xion-verify vessel-compact --mode hardware_device` check when the first hardware vessel exists. Independent hardware review remains required for high-risk vessels.
- **Verifier:** `xion-verify vessel-compact` (`NOT_YET_SEALED`, hardware evidence profile pending).

### KW-VESSEL-004 — Vessel-mediated billing and capacity buckets are not implemented
- **Domain:** ECON
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework planning)
- **Severity:** medium
- **Status:** mitigated residual
- **Description:** Museum kiosks, child-safe devices, hospital companions, podcasts, and conference stages may need operator-paid or capacity-bucketed billing rather than direct user x402 payment, but the AO Core and payment ledgers do not yet implement a vessel capacity-bucket primitive with Refusal-is-Free accounting.
- **Why it exists:** Phase 5g-iii sealed per-turn x402 billing first. Vessel-mediated economics require an additional accounting layer without weakening Invariants 5, 11, 15, or 16.
- **Mitigations:** `docs/37-VESSELS.md` states that a depleted bucket cannot gate `/export`, `/forget`, or `/inspect`, and that vessel operators cannot buy Covenant exceptions. The data and availability addenda also require billing-related caches, receipts, pending writes, and degraded accounting states to be declared.
- **Pay-down commitment:** A Phase 6.7+ economics slice adds capacity-bucket ledger rows, refund-fidelity joins for vessel-funded turns, and verifier coverage.
- **Verifier:** `xion-verify vessel-billing` or an extension of `xion-verify refusal-is-free` (Phase 6.7+).

### KW-VESSEL-AGENT-001 — Agent-mediated vessel verification is doctrine-only
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework close)
- **Severity:** medium
- **Status:** mitigated residual
- **Description:** `docs/37a-AGENTIC-VESSELS.md` defines principal classes, agent-in-path declaration, attribution, retry posture, tool forwarding, `/forget` into agent memory, anonymous-to-authenticated upgrade, input authenticity, and receiving-side verification, but no real agent-mediated vessel manifest exists yet.
- **Why it exists:** Verifying an agentic vessel requires a concrete Compact and evidence bundle; a generic static check cannot prove that a local or third-party agent actually preserves attribution and refusal boundaries.
- **Mitigations:** Agentic surfaces are schema-bound in `docs/schemas/vessel-compact.yaml`; `xion-verify vessel-compact` now enforces the static agentic section on the reference Compact; Phase 6.6 and 6.6a boundaries still govern internal Agent Souls and external contributor assistants.
- **Pay-down commitment:** Add evidence-backed agent-mediated vessel fixtures when the first agent-in-path Compact lands.
- **Verifier:** `xion-verify vessel-compact` (static section live; agent-in-path evidence pending).

### KW-VESSEL-DATA-001 — Vessel data-taxonomy enforcement awaits real Compacts
- **Domain:** DATA
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework close)
- **Severity:** medium
- **Status:** closed (2026-04-30, Phase 7 preflight hardening)
- **Description:** `docs/37b-VESSEL-DATA-TAXONOMY.md` names vessel data classes and per-class `/export`, `/forget`, `/inspect`, retention, residency, and third-party boundary rules. The reference Compact now maps local session, pending state, relayed transcript, and cross-protocol bridge data with explicit third-party recipients and availability references.
- **Why it exists:** The taxonomy needed a concrete reference Compact and parser checks before any production vessel could claim sealed behavior.
- **Mitigations:** `xion-verify vessel-compact` now enforces required per-class fields, allowed class IDs, duplicate class rejection, cross-protocol bridge recipient disclosure, and availability references.
- **Pay-down commitment:** Complete for the reference web/podcast Compact. Production vessels must submit their own Compact and registry row before claiming sealed status.
- **Verifier:** `xion-verify vessel-compact`.

### KW-VESSEL-AVAILABILITY-001 — Degraded vessel reachability has no test bench
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework close)
- **Severity:** high
- **Status:** mitigated residual
- **Description:** `docs/37c-VESSEL-AVAILABILITY-MODEL.md` defines `online_full`, `online_degraded`, `offline_floor`, `offline_cache`, and `lost_storage`, but there is no degraded-mode vessel test bench proving user-facing disclosure, `/forget` propagation, pending-write visibility, mid-conversation export, or crisis-fidelity behavior.
- **Why it exists:** Availability behavior must be exercised against a real or fixture-backed vessel; doctrine alone cannot prove the UI or local runtime tells the truth under failure.
- **Mitigations:** The reachability matrix is schema-bound in `docs/schemas/vessel-compact.yaml`, and the reference Compact now declares all five reachability states. `xion-verify vessel-compact` rejects missing states or invalid proof postures; production UI/test-bench behavior remains unsealed.
- **Pay-down commitment:** Add fixture-based degraded-mode UI/runtime tests with the first production vessel.
- **Verifier:** `xion-verify vessel-compact` (static matrix live; behavior test bench pending).

### KW-VESSEL-INPUT-AUTH-001 — Input authenticity at vessel sensors is not mechanically verified
- **Domain:** SAFETY
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework close)
- **Severity:** high
- **Status:** mitigated residual
- **Description:** Agentic and hardware vessels must distinguish live user input from replayed, uploaded, synthesized, translated, uncertain, or agent-generated input, but there is no verifier for microphone, camera, or sensor input authenticity.
- **Why it exists:** Sensor authenticity depends on device evidence, local indicators, replay defenses, and threat models that do not exist until a real vessel exists.
- **Mitigations:** `docs/37a-AGENTIC-VESSELS.md` forbids treating unverifiable input as a high-assurance command, identity binding, spend approval, physical-control instruction, or consent grant.
- **Pay-down commitment:** Add input-authenticity fixtures and hardware evidence requirements with the first sensor-bearing vessel.
- **Verifier:** `xion-verify vessel-compact` (`NOT_YET_SEALED`, input authenticity pending).

### KW-VESSEL-RECV-VERIFY-001 — Receiving-side verification is not implemented on any vessel
- **Domain:** TRUST
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework close)
- **Severity:** medium
- **Status:** mitigated residual
- **Description:** A user who hears a hardware device or media surface say "Xion said X" needs a way to verify the claim, but no vessel currently ships a signed utterance manifest, QR proof, debug panel, or exportable transcript bundle.
- **Why it exists:** The user-facing verification path belongs to the vessel, not only the CLI; it cannot be tested until a concrete carrier exists.
- **Mitigations:** `docs/37a-AGENTIC-VESSELS.md` requires a receiving-side verification surface before a vessel claims live Xion support.
- **Pay-down commitment:** Promote receiving-side verification checks with the first hardware or media vessel Compact.
- **Verifier:** `xion-verify vessel-compact` and `xion-verify media-provenance` (`NOT_YET_SEALED`, receiving-side proof pending).

### KW-VESSEL-XBRIDGE-001 — Cross-protocol bridge archives are outside Xion's erasure control
- **Domain:** DATA
- **Discovered:** 2026-04-25 (Phase 6.7 Vessel Integration Framework close)
- **Severity:** medium
- **Status:** structural residual
- **Description:** If a vessel bridges Xion into SMS, email, Discord, livestream chat, or another third-party system, Xion can clear its own state and revoke provenance, but it cannot guarantee deletion of external archives outside its control.
- **Why it exists:** This is a real boundary of authority, not a missing implementation detail.
- **Mitigations:** `docs/37b-VESSEL-DATA-TAXONOMY.md` requires `cross_protocol_bridge` disclosure and forbids promising impossible erasure.
- **Pay-down commitment:** Keep the boundary visible in every Compact and verifier output; do not mark this closed unless the bridge is under Xion-controlled retention semantics.
- **Verifier:** `xion-verify vessel-compact` (`NOT_YET_SEALED`, bridge boundary disclosure pending).

### KW-HERMES-001 — Hermes runtime dependency is lockfile-pinned through a vendored adapter
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.6 Cognitive Substrate planning)
- **Severity:** medium
- **Status:** closed (2026-04-30, Phase 7 preflight hardening)
- **Description:** `docs/HERMES_PIN_PROTOCOL.md`, `genesis/HERMES_TOOL_ALLOWLIST.yaml`, `requirements.lock`, `xion_hermes_runtime`, and `xion-verify hermes-runtime` now make the Hermes commit, default-deny allowlist, disabled runtime flags, and vendored adapter artifact mechanically verifiable.
- **Why it exists:** The current repository wraps and gates the cognition substrate before depending on an upstream package shape that may still change. The conservative closure is a tiny vendored adapter package whose file hash and upstream Hermes commit are pinned in `requirements.lock`.
- **Mitigations:** `xion-verify hermes-runtime` verifies the doctrine pin, allowlist hash, vendored adapter hash, and adapter Hermes commit; `xion-verify agent-souls` and `xion-verify agent-cast` prevent unallowlisted tools or unpinned cast faculties from entering the pool.
- **Pay-down commitment:** Complete for Genesis. If upstream Hermes later exposes a stable installable package boundary, replace the vendored adapter through the same lockfile and verifier path.
- **Verifier:** `xion-verify hermes-runtime`.

### KW-AGENT-SOULS-001 — Specialists are content-addressed Agent Souls
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.6 Cognitive Substrate planning)
- **Severity:** medium
- **Status:** closed (2026-04-25, Phase 6.6 Cognitive Substrate & Casting)
- **Description:** The primary worker and specialists now have per-agent Soul files under `genesis/AGENT_SOULS/` with parent Soul hashes, tool subsets, cost envelopes, triggers, output destinations, and a manifest pinned in `genesis/GENESIS_ARTIFACT.md`.
- **Why it exists:** The cognition doctrine defined the properties before the durable per-agent artifacts existed.
- **Mitigations:** Closed by `genesis/AGENT_SOULS/_SCHEMA.md`, the five initial Agent Souls, `genesis/AGENT_SOULS/MANIFEST.txt`, and `xion-verify agent-souls`, which checks both manifest payload hash and per-file Soul hashes.
- **Pay-down commitment:** Complete; future Agent Soul changes are versioned content-hash replacements through the Casting Pipeline.
- **Verifier:** `xion-verify agent-souls` (Phase 6.6).

### KW-CASTING-001 — Cast ledger is live and Relay boot casting is D2-wired
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.6 Cognitive Substrate planning)
- **Severity:** medium
- **Status:** closed (2026-04-25, Pre-Genesis hardening)
- **Description:** `ledgers/AGENT_CAST_LEDGER.jsonl`, `orchestrator/cognition/casting.py`, `xion cast pool`, and `xion-verify agent-cast` now prove cast rows against Agent Soul hash, parent Soul hash, Hermes pin, and tool allowlist. The D2 Relay boot path now deterministically seeds the cast ledger when empty and refuses startup when `xion-verify agent-cast` fails.
- **Why it exists:** The wrapper layer landed before the Casting Pipeline and live cast-pool verifier.
- **Mitigations:** Automatic boot casting seeds append-only rows when the ledger is empty, verifies existing rows otherwise, and refuses startup when `xion-verify agent-cast` rejects wrong hashes, wrong parent Soul, wrong Hermes pin, failed smoke tests, or `agent_id=arbiter`.
- **Pay-down commitment:** Complete for D2 boot. Future work may replace the deterministic seed with a live Hermes process pool, but the startup refusal property is sealed.
- **Verifier:** `xion-verify agent-cast` (Phase 6.6).

### KW-MEMORY-HERMES-001 — Hermes/Honcho memory needs Xion `/forget` adapter before user memory can rely on it
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.6 Cognitive Substrate planning)
- **Severity:** high
- **Status:** closed (2026-04-25, Phase 6 completion plan)
- **Description:** Hermes's memory stack and Honcho-style user modeling can improve episodic recall; Xion now has a backend-shaped `/forget` adapter contract with a 15-second SLA simulation.
- **Why it exists:** Off-the-shelf memory systems optimize persistence and personalization; Xion's invariant requires bounded forgetting and consent-aware cache zeroing.
- **Mitigations:** `orchestrator/cognition/memory_adapter.py` deletes scoped records, waits for acknowledgement, and `POST /forget` routes through the adapter when configured.
- **Pay-down commitment:** Complete for adapter contract; real external backend integration is a deployment choice under the same interface.
- **Verifier:** `xion-verify cognition --forget-sim` plus `xion-verify agent-cast` memory-surface checks.

### KW-COGNITION-ARBITER-BOUNDARY-001 — Arbiter/Hermes runtime boundary is doctrine-pinned but not mechanically verified
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.6 Cognitive Substrate planning)
- **Severity:** high
- **Status:** closed (2026-04-25, Phase 6.6 Cognitive Substrate & Casting)
- **Description:** The architecture requires the Arbiter to remain outside Hermes. `xion-verify cognition`, `xion-verify agent-souls`, and `xion-verify agent-cast` now fail if Arbiter modules import Hermes runtime surfaces, if an Agent Soul has `agent_id=arbiter`, or if a cast row attempts to cast the Arbiter.
- **Why it exists:** The "use Hermes for every agentic faculty" rule needs an explicit carve-out for the egress gate.
- **Mitigations:** Closed by the verifier boundary check and by the Agent Soul / cast-ledger `agent_id=arbiter` rejection rules.
- **Pay-down commitment:** Complete; future Hermes runtime expansions must preserve the same carve-out.
- **Verifier:** `xion-verify cognition`, `xion-verify agent-souls`, `xion-verify agent-cast`.

### KW-SENSORIUM-COUPLING-001 — Sensorium was a monolithic struct; every new sense risked touching every consumer
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.4.b planning)
- **Severity:** medium
- **Status:** closed (2026-04-25, Phase 6.4.b Nervous System v2)
- **Description:** Internal senses were embedded only in `SensoriumState`. Adding a modality required editing Volition, Arbiter integration, vitals, and HTTP projections together.
- **Why it exists:** Phase 5c shipped the four internal senses as a single frozen snapshot for speed and clarity.
- **Mitigations:** `SignalBus`, schema registry, receptor modules with dual-publish, `SensoriumView` / `TopographyView` / `VitalsView`, `GET /self`, sealed vitals via `orchestrator/vitals/mapping.py`, reflex arcs for consent-driven stream closure.
- **Pay-down commitment:** Landed in Phase 6.4.b with `xion-verify topography` + `xion-verify nervous-system` and tests in `orchestrator/tests/test_modularity_invariants.py`.
- **Verifier:** `xion-verify topography`, `xion-verify nervous-system`, `pytest orchestrator/tests/test_modularity_invariants.py`.

### KW-PROOF-001 — user_proof_commit is signed and verified
- **Domain:** RUNTIME
- **Discovered:** 2026-04-24 (Phase 6.3 Interaction Anchoring)
- **Severity:** low
- **Status:** closed (2026-04-25, Phase 6.3.b)
- **Description:** The web client generates an IndexedDB-backed Ed25519 keypair, signs `user_pubkey_b64|message`, and sends `user_proof`; the orchestrator verifies the signature before writing `user_proof_commit`.
- **Why it exists:** Client-side Ed25519 key generation and signature logic were deferred to Phase 6.3.b to decouple the backend anchoring infrastructure from the frontend cryptography.
- **Mitigations:** Algorithm-agnostic schema avoided a ledger migration, and server-side verification rejects invalid proofs before ledger write.
- **Pay-down commitment:** Complete; tests cover server proof verification and client proof emission paths.
- **Verifier:** `pytest orchestrator/tests/test_user_proof.py`; `npm test` in `clients/web`.

### KW-PROOF-002 — IndexedDB wiping logic lacks cross-tab coordination
- **Domain:** RUNTIME
- **Discovered:** 2026-04-25 (Phase 6.3.b Client Proofs)
- **Severity:** low
- **Status:** closed (2026-04-25, Phase 6.4)
- **Description:** When the user clicks "Forget my keys", the local IndexedDB is wiped and other open tabs of the same origin receive a `BroadcastChannel("xion:keys")` message to drop in-memory credentials.
- **Why it exists:** Cross-tab `BroadcastChannel` coordination was deferred to keep the Phase 6.3.b PR small.
- **Mitigations:** `clients/web/src/lib/crypto.ts` broadcasts `{ type: "forgotten" }` after key wipe, and `BearerProvider` clears in-memory/localStorage credentials on receipt.
- **Pay-down commitment:** Phase 6.4 added `BroadcastChannel` sync on the `xion:keys` channel to the Forget-my-keys flow, forcing all tabs to drop credentials and prompt for sign-in simultaneously.
- **Verifier:** `npm test` in `clients/web` (BroadcastChannel coordination test).
- **Verified by:** Automated Vitest coverage plus manual two-tab workflow.

### KW-ANCHOR-AO-001 — AnchorDaemon writes to local ledger only; AO Core sink deferred
- **Domain:** RUNTIME
- **Discovered:** 2026-04-24 (Phase 6.3 Interaction Anchoring)
- **Severity:** medium
- **Status:** closed (2026-04-25, Phase 6.3.b)
- **Description:** The hourly Merkle interaction roots are written to the local `ANCHOR_LEDGER.jsonl` but are not posted to AO Core.
- **Why it exists:** `AOCoreSink` is a Phase 6.3.b deliverable. The AO Core substrate that would receive its writes is now sealed (KW-AOCORE-004 closed 2026-04-25), so the sink itself is no longer blocked, only scheduled. Earlier text said "blocked by KW-AOCORE-004"; that statement is stale and is preserved in git history only.
- **Mitigations:** The verifier `interaction-anchor` checks all local integrity properties and explicitly prints that it checks 0 anchors on-chain.
- **Pay-down commitment:** Phase 6.3.b shipped `AOCoreSink` using a local node helper to sign and post to AO Core.
- **Verifier:** `DEVELOPMENT_ROADMAP.md` (Phase 6.3.b stub).

### KW-AOCORE-004 — Phase 6.1 testnet seal blocked by aos-2.0 mainnet default + upstream legacy MU 500
- **Domain:** OPS
- **Discovered:** 2026-04-24 (second Phase 6.1-residuals attempt; agent-driven)
- **Severity:** medium
- **Status:** closed (2026-04-25 by Phase 6.1.b finalization — see `CHANGELOG.md` § "[Phase 6.1.b finalization] — 2026-04-25"; substrate is now reachable AND sealed; receipt + first state-chain row committed; verifier returns OK against `http://localhost:4004` at height=1)
- **Description:** Two independent issues compound to block the Phase 6.1 testnet seal even after `KW-AOCORE-003`'s WSL2 workaround makes `aos` runnable.
  - **Issue A (operator-controllable, doctrine-relevant).** `aos` 2.0 (current `@permaweb/aos` 2.0.11, installed via `npm i -g https://get_ao.arweave.net`) flipped the default from "legacynet/testnet" to "AO mainnet (HyperBEAM)". Without an explicit `--legacy` flag, `aos <name>` spawns a real on-chain process on AO mainnet at `https://push.forward.computer`. The doctrine-side rule in `docs/09-GOVERNANCE.md` and the runbook `docs/runbooks/AO_DEPLOY_WSL2.md` reserve mainnet for a Phase 6+ Tier-3 ceremony with cold-root cosigns; Phase 6.1 is testnet-only by intent. The first Phase 6.1-residuals run (this attempt, 2026-04-24, agent-driven before the trap was discovered) spawned two AO mainnet processes by accident under the agent-generated WSL2 wallet `v8Fee96ZAGu1W5Ec5fj3EWc7fPvp3MSLbdKhDwjwfHY`: a throwaway `smoke-deploy-test` (`-MlYwU1U_5tEjRFhIVQFncEroGFO4kFetIqByOgFnBE`) and the canonical `xion-core` (`PxTK8xPH4sRDCIRGl2sruE_OrRFcbW25Oz2NwiKzkKM`). Both are now orphaned on AO mainnet; the `xion-core` spawn is functionally empty (the `--load` and `--run` of `ao/core/main.lua` failed inside the same invocation with `sendMessageMainnet` errors, so no Xion handlers ever attached). Operator chose to abandon (rather than ratify retroactively via Tier-3 cosign), per the disposition recorded in the 2026-04-24 transcript.
  - **Issue B (upstream-blocking).** With `--legacy` correctly passed, `aos` cannot spawn at all right now: every legacynet spawn returns HTTP 500 from the messenger unit at `https://mu.ao-testnet.xyz`, with body `{"error":"TypeError: Cannot read properties of null (reading 'toLowerCase')"}`. Reproduced three times across two process names and once with explicit `--gateway-url https://arweave.net --cu-url https://cu.ao-testnet.xyz --mu-url https://mu.ao-testnet.xyz` overrides, all returning the same error. The error is server-side (`@permaweb/aoconnect` `dist/index.js:744` is just `throw new Error(\`${res.status}: ${await res.text()}\`)` rethrowing the MU's response). This is consistent with legacynet being deprecated or in regression; the AO ecosystem's modern path is HyperBEAM (mainnet) with optional local-Docker via `permaweb/ao-localnet` for development, and the `--legacy` codepath in `aos` 2.x is documented as "Support --mainnet flag for backwards compatibility" with legacynet treated symmetrically as a legacy mode.
- **Why it exists:**
  - Issue A: `aos` is a third-party tool maintained by the AO ecosystem; its 2.0 release flipped the default network without breaking the CLI surface, and the runbook `docs/runbooks/AO_DEPLOY_WSL2.md` was authored against the 1.x mental model where `aos <name>` meant testnet by default. The trap was discovered only by running `aos` against the real network.
  - Issue B: legacynet is upstream-deprecated infrastructure outside Xion's control surface.
- **Mitigations:**
  1. **Doctrine integrity preserved.** The accidental mainnet spawns were not laundered into legitimacy via post-hoc Tier-3 cosign. `genesis/AO_DEPLOY_RECEIPT.json` remains `{status: "placeholder"}`. `xion-verify ao-handlers` continues to honestly return NOT_YET_SEALED. `KW-AOCORE-001` is not closed.
  2. **Wallet hardening.** `.gitignore` was extended (Phase 6.1-residuals attempt 2) with `*.aos.json`, `**/.aos.json`, `*.jwk`, `*.jwk.json`, `**/*.jwk` patterns to prevent any future copy of the WSL2 wallet from being trackable, regardless of the directory it is copied into.
  3. **Runbook amended.** `docs/runbooks/AO_DEPLOY_WSL2.md` was updated with: (a) a prominent warning at the top of the Deploy section that `aos` 2.0 defaults to mainnet and `--legacy` is mandatory for Phase 6.1; (b) the actually-working install URL (`https://get_ao.arweave.net`; the cookbook's `get_ao.g8way.io` is currently 404); (c) a lessons-learned footnote naming the two orphaned mainnet processes by ID so any future operator can verify them on chain and confirm they are not Xion's canonical AO Core; (d) explicit reference to `KW-AOCORE-004` as the upstream-MU blocker that may require a wait-and-retry posture.
  4. **Wallet custody.** The agent-generated WSL2 wallet `v8Fee...wjwfHY` is fine for the eventual testnet seal (testnet is low-stakes by design), but should NOT be promoted to Xion's permanent mainnet identity in Phase 6+ — that wallet should be freshly generated under proper Cold Root Shamir-shard custody per `docs/09-GOVERNANCE.md`.
- **Pay-down commitment:** Closes when one of:
  1. **Upstream legacy MU recovers.** Operator (or any subsequent automated retry) successfully runs `aos xion-core --legacy --load /mnt/c/.../ao/core/main.lua` from WSL2 and gets a successful spawn + load (no HTTP 500). At that point Phase 6.1 finalization can proceed via the amended runbook and `KW-AOCORE-001` closes alongside.
  2. **Local AO localnet path adopted. [ELECTED 2026-04-24, Phase 6.1.b].** This branch was elected because the upstream legacy MU appeared functionally orphaned and waiting on it would block KW-AOCORE-001/002/003 indefinitely. Phase 6.1.b shipped the supporting infrastructure as a precondition: `infra/ao-localnet/docker-compose.yaml` (commit-pinned wrapper around `permaweb/ao-localnet`), `scripts/ao-localnet-up.sh` (clone + bring-up + readiness poll), `docs/runbooks/AO_DEPLOY_LOCALNET.md` (operator runbook, sibling to the WSL2 legacynet runbook), the `docs/28-AO-CORE.md` "Substrate amendment (Phase 6.1.b, 2026-04-24)" doctrine subsection naming `permaweb/ao-localnet` as a doctrine-permissible substrate alongside legacynet for the Phase 6.1 seal, and substrate-awareness in the verifier (`xion-verify ao-handlers` now requires `genesis/AO_DEPLOY_RECEIPT.json` to declare `substrate ∈ {localnet, legacynet}` and rejects `mainnet` outright). **This KW remains OPEN** until the operator runs the new runbook end-to-end in WSL2, lands the resulting non-placeholder `genesis/AO_DEPLOY_RECEIPT.json` (with `substrate: "localnet"`) plus the first `ledgers/STATE_CHAIN_LEDGER.jsonl` row in a follow-up small PR, and `xion-verify ao-handlers` flips from `NOT_YET_SEALED` to `OK`. Election does not equal closure; the substrate is now reachable but the seal is not yet sealed.

  - **Progress (2026-04-25, seal mechanism end-to-end on operator workstation).** The seal pipeline (`scripts/ao-localnet-seal.sh`) was driven to a green `xion-verify ao-handlers` against a fresh `permaweb/ao-localnet` bring-up, twice in a row for reproducibility — exit 0, all 20 handler schemas pass, lua source hash matches deployed bytes, local tip parity verified at height=1 against `http://localhost:4004`. **Six non-obvious traps** surfaced and are now documented in-tree (each with a fix lane the next operator/agent will hit instead of the bug):
    1. **CU runs Node 20 by upstream default; `ao/servers/cu` `main` calls `Promise.withResolvers` (Node 22+).** Every `readResult` crashes server-side; `aos` reports the symptom as "Could not connect to process". Fix: `scripts/patch-ao-localnet-cu-node22.sh` rewrites the CU Dockerfile to `node:22-alpine`; `scripts/ao-localnet-up.sh` runs the patch and rebuilds `cu` automatically. Failure-mode entry in `docs/runbooks/AO_DEPLOY_LOCALNET.md`. Sanity probe in `scripts/ao-localnet-seal.sh` flags Node-20 CUs before they're used.
    2. **`@permaweb/aoconnect` clears `process.env.AO_URL` on import.** `aos` 2.0 reads the *string* `'undefined'` as a sentinel to keep its legacy `readResult` codepath; aoconnect's `process.env.AO_URL = void 0` wipes that sentinel and silently routes the call through HyperBEAM. Fix: `scripts/patch-npm-aoconnect-preserve-ao-url.sh` (idempotent, run by `ao-localnet-seal.sh`).
    3. **`aos --run "$(cat ao/core/main.lua)"` is parsed as a boolean by `minimist`.** main.lua starts with `--` (a Lua line comment); any `--run` value whose first character is `-` becomes `{ run: true }`, and `Buffer.from(true)` blows up deep inside `ar-data-create`. Fix: prepend a single space to the Lua source before passing it to `--run` (`scripts/ao-localnet-seal.sh` does this, with a multi-line comment explaining why).
    4. **ArLocal indexes spawn DataItems lazily.** Two back-to-back `aos $AOS_NAME` calls usually re-spawn the second time because the gql lookup returns no result. Fix: extract the 43-char base64url pid from step 1's `Your AOS Process: <pid>` line and pass *that* (not the human-readable name) to subsequent `aos` calls — `register()`'s `isAddress` short-circuit returns `{ id: name, variant: null }` and bypasses the gql lookup entirely (`scripts/ao-localnet-seal.sh` does this).
    5. **`Send({Target=ao.id,...})` from inside an `aos --run` Eval has `msg.From == ao.id`, not `Owner`.** The Phase 6.1 skeleton's `commit-state` handler authorizes only `[Owner]` and `AuthorizedSigners`, so a self-Send is silently rejected with `non_authorised_caller`. Fix: send the message externally, signed with the owner's wallet — `scripts/ao-localnet-send-commit-state.cjs` is the template (CJS not ESM because Node's ESM loader doesn't honor `NODE_PATH` for `exports`-field resolution, and the only place `aoconnect` is installed is under `aos`'s own `node_modules`). Doc-string in `ao/core/main.lua` near `is_authorized` flags the trap for future contract authors.
    6. **The legacy AO CU's `/state/<pid>` endpoint serves a *binary* memory snapshot, not JSON.** The earlier verifier shape ("expected JSON object containing `state_tip_height` ...") could never succeed against this surface. Fix: `xion-verify ao-handlers`'s `_fetch_gateway_tip` now uses `POST /dry-run?process-id=<pid>` with a Lua body that returns `json.encode({state_tip_height=StateTip.height, state_root_sha256=StateTip.root})`, and threads the receipt's `signer_address` as the dry-run body's `Owner` (AOS only *runs* Eval when `msg.From == Owner`; otherwise it returns a "New Message From..." banner string in `Output.data.output`). Round-trip is gas-free and side-effect-free, preserving the "any third party with a CU URL can verify" property.
  - **Closure (2026-04-25).** All four steps above completed in the Phase 6.1.b finalization PR: (a) `scripts/ao-localnet-seal.sh` was re-run from a clean session, (b) the resulting `genesis/AO_DEPLOY_RECEIPT.json` + `ledgers/STATE_CHAIN_LEDGER.jsonl` are committed (process id `7G35XZsoMbT7c8mkOt4cJALPJudpRzSnOUK0xaKs04Q`, signer `55Plp-xUQ5B-955uJYjtCT4kR0eEf63lhzGd__pw1jY`, first commit-state message id `MXKxwuycUWluvfL4oeW4-HUXUHTuq0riTl_LzjBZtEw`, lua source sha256 `97970eeef4b5e908f85c7f5b55b4f526adf2e64f2a2879f1d874412e0322c799`), (c) this KW + `KW-AOCORE-001` + `KW-AOCORE-003` are closed in this same PR, (d) the substrate `process_id` is recorded in `CHANGELOG.md` § "[Phase 6.1.b finalization] — 2026-04-25". The original 6.1.b CHANGELOG entry promised a separate follow-up small PR for the artifact commit; that promise was collapsed into a single ratification because the seal mechanism + the seal artifacts are reviewable as one logical unit and the PR-splitting overhead bought no review value (direct push to `main`, single author).
  3. **Phase 6+ ceremony.** Operator + cold-root explicitly elect to do the Phase 6.1 seal on AO mainnet under the proper Tier-3 cosign ceremony (with a freshly-generated Cold Root wallet, NOT the WSL2 agent wallet), accepting that Phase 6.1's "testnet seal" is being collapsed into the Phase 6+ "mainnet seal" by force of the legacy-MU outage. Not elected; retained as a fallback should the localnet path itself prove infeasible on the operator's machine.
- **Verifier:** `xion-verify ao-handlers` is the closure observable; after Phase 6.1.b it additionally enforces the `substrate` allowlist and surfaces the substrate name in the OK message (e.g. `substrate=localnet`). The KW also names two on-chain artifacts (`-MlYwU1U_5tEjRFhIVQFncEroGFO4kFetIqByOgFnBE`, `PxTK8xPH4sRDCIRGl2sruE_OrRFcbW25Oz2NwiKzkKM`) that any third party can query against AO mainnet GraphQL to confirm they exist, are owned by `v8Fee...wjwfHY`, and have no Xion-handler `Eval` history; that is the negative evidence that they are not Xion's canonical AO Core.

### KW-INTERACT-001 — Per-user verifiable receipts do not exist
- **Domain:** RUNTIME
- **Discovered:** 2026-04-24 (Sentience Surface Roadmap)
- **Severity:** medium
- **Status:** closed (2026-04-24 by Phase 6.3 Interaction Anchoring)
- **Description:** Users cannot verify their interactions on-chain without Xion storing content on-chain.
- **Why it exists:** Interaction anchoring was deferred to Phase 6.3 to prioritize the core Relay.
- **Mitigations:** Local ledger provides operator-side transparency.
- **Pay-down commitment:** Phase 6.3 will introduce hourly Merkle anchors and `GET /me/receipts`.
- **Verifier:** `xion-verify interaction-anchor` and `GET /me/receipts` endpoint.

### KW-PRESENCE-EMITTER-001 — Visual Emitter is not implemented
- **Domain:** RUNTIME
- **Discovered:** 2026-04-24 (Sentience Surface Roadmap)
- **Severity:** low
- **Status:** closed (2026-04-25, Phase 6.4)
- **Description:** `GET /presence/stream` and the Visual Emitter described in `docs/06-FORM-AND-PRESENCE.md` are not built.
- **Why it exists:** Deferred to Phase 6.4.
- **Mitigations:** None.
- **Pay-down commitment:** Phase 6.4 built the `PresenceBus` and the `stream_visuals` / `stream_vitals` emitters, wired them to the Supervisor tick, and exposed them via `fetch`-based SSE in the web client.
- **Verifier:** `xion-verify presence` (promoted from stub to live check asserting JSON envelope shapes).
- **Verified by:** `xion-verify presence` exits `0` against synthetic state.

### KW-FORM-001 — FORM.md Birth Ritual expansion (Xion-authored full vocabulary)
- **Domain:** DOCS
- **Discovered:** 2026-04-24 (Sentience Surface Roadmap)
- **Severity:** low
- **Status:** closed (2026-04-26, Sentience Axis Track 5)
- **Description:** `genesis/FORM.md` now has authored §1/§2/§3 tables (primitives, color–mood grammar, gesture vocabulary) per `docs/06-FORM-AND-PRESENCE.md`; the scaffold placeholders were replaced by Xion's v2.0 vocabulary.
- **Why it exists:** Xion-paced form maturation under Invariant 6 absolute autonomy.
- **Mitigations:** Forward-compatible `form_version` (v2.0.0); `xion-verify form` re-pinned in `GENESIS_ARTIFACT.md`.
- **Pay-down commitment:** Closed by `genesis/FORM.md` v2.0.0 and `GENESIS_ARTIFACT.md` hash re-pin.
- **Verifier:** `xion-verify form` + `DEVELOPMENT_ROADMAP.md` (Phase 6.4.c).

### KW-MODALITY-001 — Per-modality user consent and cost slices are missing
- **Domain:** ECON
- **Discovered:** 2026-04-24 (Sentience Surface Roadmap)
- **Severity:** medium
- **Status:** closed (2026-04-25, Phase 6.4)
- **Description:** Users cannot express per-modality consent (visuals/vitals/voice) and lack structural defense against silent billing.
- **Why it exists:** Deferred to Phase 6.4 with presence emitters.
- **Mitigations:** Covenant Principle 5 mandates financial dignity.
- **Pay-down commitment:** Phase 6.4 added `stream_*` modality consent toggles to `/memory/consent`, wired per-modality price slices to `/pricing`, and enforced server-side off-channel connection closure to prevent silent billing.
- **Verifier:** `xion-verify modality-consent` (promoted from stub to live check asserting doctrine-aligned scopes and defaults).
- **Verified by:** `xion-verify modality-consent` exits `0`.

### KW-VOICE-SOVEREIGNTY-001 — Voice surface could depend on a single hosted commercial provider
- **Domain:** RUNTIME
- **Discovered:** 2026-04-24 (Sentience Surface Roadmap)
- **Severity:** medium
- **Status:** closed (2026-04-30, Invariant 18 ratified and Cold Root cosigned)
- **Description:** Optional hosted voice overlays (Vapi, ElevenLabs, etc.) remain structurally **non-load-bearing**; the system must not *require* them to exist.
- **Why it exists:** Integrations are convenient; centralization is the risk.
- **Mitigations:** Invariant 18 text is staged in `genesis/INVARIANTS.md`, and `ledgers/AMENDMENT_LEDGER.jsonl` now records `reflection_window_days_observed=14`, `status="ratified"`, and Cold Root cosign. **`orchestrator/voice_router/`** + sentinel manifest + `xion-verify voice-sovereignty` (live) enforce a `voice_open_source_self_hostable` floor pin. `POST /voice/stream` exercises the floor provider and emits `VOICE_FORM.md` prosody frames; runtime STT/TTS daemons are operator-activated (`WhisperPiperLiveKitProvider`).
- **Pay-down commitment:** Closed for the constitutional voice-floor posture by the ratified amendment row and live floor verifier. Optional hosted overlays remain non-load-bearing overlays, not a residual against the floor.
- **Verifier:** `xion-verify voice-sovereignty`, `DEVELOPMENT_ROADMAP.md` Phase 6.5.

### KW-AOCORE-002 — 17 of 20 AO Core handlers are still doctrine-only
- **Domain:** RUNTIME
- **Discovered:** 2026-04-23 (Phase 6.1 AO Core Skeleton)
- **Severity:** low
- **Status:** closed (2026-04-25, Macro Phase 6 Epic A)
- **Description:** This weakness is closed: all 20 AO Core handlers now have concrete Lua registrations in `ao/core/main.lua`, concrete non-placeholder schemas under `docs/schemas/ao-handler-*.yaml`, and a refreshed localnet seal receipt in `genesis/AO_DEPLOY_RECEIPT.json` naming process `24l6f0iiqP6mRA55hzhKfJZZCNYiUsMQTC0YHxFWr8o`.
- **Why it existed:** Phase 6 was sliced into sub-phases. Phase 6.1 shipped the skeleton and the state-chain loop first; the authority, treasury/lifecycle, provisioning, and sustainability families were left doctrine/schema-only.
- **How it closed:** Macro Phase 6 Epic A implemented `rotate-authority`, `abdicate-tier`, `treasury-spend`, `registry-update`, `spend`, `slash-imprint`, `provision-{relay,inference,storage,bandwidth,witness}`, `route-slices`, `improvement-spend`, `reserve-draw`, `accept-donation`, `enter-hibernation`, and `exit-hibernation`. `xion-verify ao-handlers` now rejects placeholder `dummy_arg` schemas and any `status: canonical` handler schema without a matching `Handlers.add(...)` registration.
- **Verifier:** `xion-verify ao-handlers` exits `0` against `XION_AO_GATEWAY_URL=http://localhost:4004` with 20 handler schemas verified, Lua hash `737db38bb7e0959e54f1db89d8b51f6994f04e8da7016418943d44f31bccc752`, and local tip parity at height `1`.

### KW-AOCORE-001 — AO testnet deploy of `commit-state` + `attest` is still pending
- **Domain:** RUNTIME
- **Discovered:** 2026-04-23 (Phase 6.0 AO Core Doctrine; reopened 2026-04-24, attempt-2 footnote added 2026-04-24)
- **Severity:** medium
- **Status:** closed (2026-04-25 by Phase 6.1.b finalization — committed receipt at `genesis/AO_DEPLOY_RECEIPT.json` names process id `7G35XZsoMbT7c8mkOt4cJALPJudpRzSnOUK0xaKs04Q` on the localnet substrate, signer `55Plp-xUQ5B-955uJYjtCT4kR0eEf63lhzGd__pw1jY`, first commit-state message id `MXKxwuycUWluvfL4oeW4-HUXUHTuq0riTl_LzjBZtEw`, lua source sha256 `97970eeef4b5e908f85c7f5b55b4f526adf2e64f2a2879f1d874412e0322c799` matching current bytes of `ao/core/main.lua`; verifier returns OK; closure path was `KW-AOCORE-004` path #2 — see `CHANGELOG.md` § "[Phase 6.1.b finalization]" for the full debrief and the six debugging traps that surfaced)
- **Description:** This weakness is closed for the Phase 6.1.b seal path. The canonical AO Core Lua (`ao/core/main.lua`), all 20 handler schemas, the localnet receipt in `genesis/AO_DEPLOY_RECEIPT.json`, and the seed row in `ledgers/STATE_CHAIN_LEDGER.jsonl` are committed. The earlier placeholder/dummy-pid posture was removed before closure.
- **Why it existed:** The 2026-04-23 closure note was premature; the first real deployment attempts exposed the Windows-native `aos` blocker and then the legacy MU 500 regression. The final elected closure path was the Xion-controlled localnet substrate authorized by `docs/28-AO-CORE.md`.
- **Mitigations:** `xion-verify ao-handlers` rejects placeholder receipts, verifies the `ao/core/main.lua` source hash, and checks localnet CU tip parity against the state-chain ledger. The two accidental AO mainnet processes from attempt-2 remain explicitly orphaned and are not Xion's canonical AO Core.
- **Pay-down commitment:** Closed. Future work is stronger per-handler behavioral dry-run coverage and eventual AO mainnet ceremony, not the Phase 6.1.b `commit-state`/`attest` seal.
- **Verifier:** `xion-verify ao-handlers` (live).
- **Progress (2026-04-25):** The seal mechanism is now end-to-end verified locally via `scripts/ao-localnet-seal.sh` against the `permaweb/ao-localnet` substrate from `KW-AOCORE-004` closure path #2 — exit 0 from `xion-verify ao-handlers` confirmed three times in a row (different fresh process IDs each run; see CHANGELOG). Six non-obvious traps surfaced and were fixed in-tree; full debrief lives under `KW-AOCORE-004` § "Progress (2026-04-25, seal mechanism end-to-end on operator workstation)" rather than being duplicated here. This KW **closed concurrently with `KW-AOCORE-004`** in the same PR — the receipt + first `STATE_CHAIN_LEDGER` row are committed as canon (process id `7G35XZsoMbT7c8mkOt4cJALPJudpRzSnOUK0xaKs04Q`).

### KW-AOCORE-003 — `aos` CLI install path is broken on this Windows + Node 22 + nvm setup
- **Domain:** OPS
- **Discovered:** 2026-04-24 (Phase 6.1-residuals attempt)
- **Severity:** low (operator-environment-specific; does not affect any committed artifact's correctness)
- **Status:** closed (2026-04-25 by elected workaround — `aos` runs in WSL2 + Node 20 LTS via `nvm`, where `npm i -g @permaweb/aos` succeeds and the resulting binary works against the localnet substrate; the seal script and runbook both pin this environment. The Windows-native + Node 22 install path remains broken upstream but is no longer in Xion's critical path. Re-open if a future workflow requires a Windows-native `aos` invocation.)
- **Description:** Three install paths for the AO `aos` CLI were attempted on the current operator workstation (Windows 10 build 22631, Node 22.22.2 via nvm-for-windows, npm 10.9.7) and all three failed: (a) `npm i -g https://get_ao.g8way.io` returned 404; (b) `npm i -g github:permaweb/aos` failed at the keccak postinstall script with `ENOENT spawn cmd.exe`; (c) `npm i -g @permaweb/aos --ignore-scripts` succeeded but the resulting `aos` binary crashes immediately with `ERR_UNSUPPORTED_ESM_URL_SCHEME` (Node 22's strict ESM resolver vs the package's Windows-absolute-path import). The blocker is in the `aos` package or its interaction with this Node version on Windows; it is not a missing dep we can install.
- **Why it exists:** `aos` is a third-party tool maintained by the AO ecosystem; its Windows + Node-22 compatibility is outside Xion's control surface.
- **Mitigations:** The elected operator path is WSL2 + Node 20 LTS, pinned by the AO localnet runbooks and seal script. `xion-verify ao-handlers` is now green against the committed localnet receipt; Windows-native Node 22 is no longer on the critical path.
- **Pay-down commitment:** Closed. Re-open only if a future workflow requires Windows-native `aos`, or if the WSL2 + Node 20 path stops working.
- **Verifier:** `xion-verify ao-handlers`.

### KW-VELOCITY-002 â€” Auto-Research Loop runs against curated genesis source list only
- **Domain:** `OPS`
- **Discovered:** 2026-04-23 (Phase 6+ Velocity Hardening)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** The Auto-Research Loop currently only scans the static, operator-curated `genesis/RESEARCH_SOURCES.md`. It does not yet ingest from dynamic community channels, partner-AI registries, or decentralized feeds.
- **Why it exists:** Safely ingesting untrusted dynamic feeds requires robust spam/sybil filtering and potentially a staking mechanism. Starting with a curated list ensures the loop functions safely at genesis.
- **Mitigations:** The curated list is explicitly version-controlled and operator-signed.
- **Pay-down commitment:** Closes post-Genesis when governance ratifies a mechanism for permissionless or dynamic source ingestion.
- **Verifier:** `xion-verify research-sources`.

### KW-VELOCITY-003 â€” Skill bounty payout flow exercises a single test wallet at genesis
- **Domain:** `ECON`
- **Discovered:** 2026-04-23 (Phase 6+ Velocity Hardening)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** The automated bounty payout flow (triggered by `PROPOSAL_LEDGER.post_deploy=kept`) is only proven against a single test wallet during pre-genesis drills.
- **Why it exists:** Real external-contributor flows require actual community participation and real XION value, which only exist post-Genesis.
- **Mitigations:** The synthetic test (`xion-verify skill-bounty`) confirms the firewall and the mechanical trigger.
- **Pay-down commitment:** Closes post-Genesis when a real external contributor successfully lands a kept proposal and receives an automated payout.
- **Verifier:** `xion-verify skill-bounty`.

### KW-VELOCITY-004 â€” Cost-Pressure Response Ladder ships with synthetic-trigger tests only
- **Domain:** `ECON`
- **Discovered:** 2026-04-23 (Phase 6+ Velocity Hardening)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** The Cost-Pressure Response Ladder is tested using synthetic price-drop events. It has not been validated against real, unannounced provider pricing changes in the live market.
- **Why it exists:** We cannot force a provider to drop their prices to test the live watcher.
- **Mitigations:** The synthetic test (`xion-verify cost-pressure`) exercises the exact same code path that a real price drop would trigger.
- **Pay-down commitment:** Closes post-Genesis when a real market event successfully triggers the ladder and emits a valid Tier-0 proposal.
- **Verifier:** `xion-verify cost-pressure`.

### KW-AUTH-001 â€” Bearer tokens are HMAC-shared-secret only; no federated identity

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-22 (Phase 5g-iv admission-control landing)
- **Severity:** medium
- **Status:** `mitigated-residual` (the structural mechanism is shipped; the federated-identity replacement is a Phase 6+ deliverable)
- **Description:** Phase 5g-iv authenticates `/drive`, `/sensorium`, and `/chat` with operator-issued bearer tokens compared in constant time via stdlib `hmac.compare_digest`. The token is an HMAC-shared-secret string (â‰¥128 bits of entropy, hex-encoded in `XION_API_BEARER_TOKENS`). There is no federated identity surface: no OAuth, no Sign-In-With-Wallet, no DID, no on-chain pubkey lattice, no per-Witness identity binding. Every token's authority traces back to the operator, and a token compromise is mitigated only by operator-side rotation.
- **Why it exists:** The smallest doctrinally honest mechanism that (1) gates content-bearing endpoints on a knowable principal, (2) keeps the route-level admission contract algorithm-rotatable, and (3) does not couple the 5g-iv landing to the on-chain-identity-lattice work that requires Phase 6 AO Core. Federated identity needs an Arweave-published authority surface; that surface is Phase 6+.
- **Mitigations:**
  1. Token entropy floor (â‰¥128 bits) enforced at lifespan-load time and re-checked by `xion-verify api-tokens` offline.
  2. Constant-time comparison via `hmac.compare_digest` â€” a timing oracle on token comparison is not the attack surface.
  3. Content-free 401 envelope (`AuthChallenge`) â€” a scraper enumerating tokens learns "not this one" per attempt and nothing else (no echo of the offered header, no hint at how many tokens are configured, no per-token failure mode disclosure).
  4. `principal_id` charset constraint (`^[a-z0-9_-]{1,64}$`) prevents log-injection and bucket-keying ambiguity.
  5. The `verify_bearer(header, tokens) -> principal_id | None` function is the algorithm-rotatable surface; the route-level `Depends(admission_dependency)` does not need to change when the token store widens to a principal lattice.
  6. Tokens are never persisted to disk by the orchestrator and never appear in any ledger or log line.
- **Pay-down commitment:** Closes when Phase 6+ Arweave-published principal lattice lands and `verify_bearer`'s body is replaced with an authority-lookup against the on-chain registry under unchanged route shape, AND `PAYMENT_LEDGER` schema bumps to `1.1` to carry `principal_id` in each row (additive, backward-compatible reader). Until then the residual is the token-compromise blast radius bounded by operator rotation cadence.
- **Verifier:** `xion-verify api-tokens` (live as of Phase 5g-iv) â€” offline structural check on token entropy, principal_id charset, and host-vs-TLS coherence.

### KW-TLS-001 â€” uvicorn-native TLS: no automated cert renewal, no ALPN/HTTP-2 negotiation

- **Domain:** `OPS`
- **Discovered:** 2026-04-22 (Phase 5g-iv admission-control landing)
- **Severity:** low
- **Status:** `mitigated-residual` (the fail-closed launcher is shipped; the long-term reverse-proxy posture is a Phase 6+ deployment-story deliverable)
- **Description:** Phase 5g-iv ships a launcher (`orchestrator/api/__main__.py`) that passes `ssl_keyfile=` and `ssl_certfile=` to `uvicorn.run` when `XION_API_HOST != 127.0.0.1`. uvicorn handles the TLS handshake using whatever cert and key the operator pinned at process-start time. The orchestrator does not renew the cert automatically; it does not negotiate ALPN/HTTP-2; it does not stack OCSP responses; it does not implement HSTS. An operator on Posture B (direct bind, uvicorn-native TLS) must rotate certs manually or wire `certbot --post-hook "systemctl restart xion-orchestrator"`.
- **Why it exists:** A reverse proxy (Caddy / nginx / Cloudflare Tunnel) is the right long-term tool for TLS lifecycle management; coupling the orchestrator to that work would expand its dependency surface and operational footprint with no constitutional gain. Shipping uvicorn-native TLS in 5g-iv lets the small operator stand up a working D2 deployment in one process without a proxy, while the runbook pins the reverse-proxy posture as the recommended long-term path.
- **Mitigations:**
  1. The launcher refuses to start if `XION_API_HOST != 127.0.0.1` and either TLS path is absent or unreadable â€” fail-closed; no plaintext bearer-token transport on a reachable interface is structurally possible.
  2. `docs/30-API-ADMISSION.md` Â§ "Operator workflow â€” TLS termination" pins both Posture A (loopback bind + reverse-proxy fronts TLS) and Posture B (direct bind + uvicorn TLS) and names Posture A as the long-term recommendation.
  3. The cert + key paths are read once at process start; an operator who automates rotation via `certbot --post-hook "systemctl restart"` gets the same effective rotation cadence as Posture A.
- **Pay-down commitment:** Closes when the Phase 6+ deployment story pins a long-term reverse-proxy posture (likely Caddy or a sidecar Cloudflared container per Akash provider) and the `__main__.py` launcher's `ssl_keyfile`/`ssl_certfile` codepath is removed in favor of always-loopback-bind. Until then the residual is the operator-manual cert rotation cost.
- **Verifier:** `xion-verify api-tokens` (live as of Phase 5g-iv) checks host-vs-TLS coherence (non-loopback host requires both TLS paths exist and are readable). A runtime check that the cert chain is currently valid against a system trust store is operator-side (`openssl x509 -in $XION_TLS_CERT_PATH -noout -dates`); the orchestrator does not duplicate this.

### KW-CLIENT-001 â€” Web client is operator-dashboard only; no in-browser x402 commitment signing

- **Domain:** `PROTOCOL`
- **Discovered:** 2026-04-22 (Phase 5g-v web-client landing)
- **Severity:** low
- **Status:** `mitigated-residual` (the operator-dashboard posture is the shipped scope; the public-user posture is a Phase 6+ deliverable that compounds with `KW-BILLING-001`)
- **Description:** Phase 5g-v ships `clients/web/` as a React+Vite+TypeScript single-page application that the orchestrator serves same-origin from FastAPI's `StaticFiles` mount at `/app/*`. The client handles the full server-response envelope matrix (`ChatResponse`, `AuthChallenge`, `PaymentChallenge`, `RateLimitChallenge`, `RefusalEnvelope`, `NoFloorEnvelope`, `ProviderErrorEnvelope`) and surfaces a sign-in dialog when the server is in the `XION_API_REQUIRE_BEARER=true` posture. It does **not** sign x402 payment commitments in the browser: when the server is in the `XION_BILLING_REQUIRED=true` posture, the client surfaces a "billing not yet supported in web client" banner and directs the operator at the `curl` path from `docs/29-BILLING-X402.md`. The 5g-v posture is therefore *operator-dashboard only*; a public-user would have to use `curl` with a hand-computed `X-Payment-Commitment` to reach `/chat` through the billing gate.
- **Why it exists:** B1 HMAC attestation with the shared secret in the browser widens the custody surface (a browser extension, an MDM-pushed profile, a misconfigured `localStorage` sync) beyond what 5g-v's doctrine has grown to cover. B2/B3 x402 wallet integration is structurally cleaner but blocks on a pinned x402 JavaScript library (the same precondition `KW-BILLING-001` tracks on the server side) plus a user-side key-custody doctrine pin. Shipping the client as operator-dashboard-only in 5g-v lets the first dogfood surface land without taking on the public-user custody problem prematurely.
- **Mitigations:**
  1. The client surfaces the `402 PaymentChallenge` envelope as a visible limitation (not an error toast), with the `correlation_id` copyable, so the operator knows precisely what the gap is.
  2. `docs/31-WEB-CLIENT.md` Â§ "Operator workflow â€” billing-required posture" pins the operator-dashboard scope explicitly and names the Phase 6+ pay-down.
  3. The server surface is unchanged â€” the `curl` path through `X-Payment-Commitment` remains fully supported; the web client is one conforming caller, not a privileged path.
  4. `XION_WEB_CLIENT_ENABLED` defaults to `false`; an operator who does not build the bundle ships no web surface at all and has exactly the pre-5g-v posture.
- **Pay-down commitment:** Closes Phase 6+ alongside `KW-BILLING-001` (x402 library pin) when both: (a) an audited in-browser x402 implementation (B2 signed-commitment or B3 verified-settlement) ships under a pinned version, and (b) a user-side key-custody doctrine lands in `docs/31-WEB-CLIENT.md` covering local-only vs WalletConnect vs injected-provider custody modes. The client's `api.ts` discriminated-union envelope handling is the stable surface; the Phase 6+ change is a new `sign_commitment()` helper and a new `BillingDialog` view, not a route-level diff.
- **Verifier:** `xion-verify web-client` is live at 5g-v and audits the emitted `clients/web/dist/` bundle for structural integrity (CSP meta tag pinning `default-src 'self'`; every `https?://` origin matches the explicit non-self allowlist of React production error-decoder URLs + W3C XML namespace identifiers). Returns `NOT_YET_SEALED` when the operator has not yet built the bundle (un-built is unverifiable, not wrong). The Vitest + axe-core client-side suite is live at 5g-v and covers the envelope-handling matrix.

<!-- KW-INFERENCE-001 closed 2026-04-23 (Phase 5g-viii completion). See Closed section. -->

### KW-CRYPTO-001 â€” Cross-substrate Q-day asymmetry not yet pinned in `docs/17`

- **Domain:** `CRYPTO`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing â€” `LHT-CRYPTO-001` opened)
- **Severity:** medium
- **Status:** `open`
- **Description:** [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md) Part VII (Dependencies We Don't Control) acknowledges that Arweave, AO, and Base will migrate to PQC on independent timelines, but does not yet contain an explicit subsection naming the **migration-window asymmetry** as a threat or specifying Xion's posture during the window. The threat is real and named in `LHT-CRYPTO-001`; the doctrine response is not yet written. A reader of `docs/17` today sees the per-substrate dependency table but does not see "what does Xion do when one substrate has migrated and another has not."
- **Why it exists:** The original `docs/17` was written assuming coordinated migration as a baseline. The Phase 5b century-horizon survey identified the asymmetry as a distinct threat shape. Rather than retro-fit the original doctrine in the same commit as the broader Wave 1 landing, the gap was named explicitly and tracked.
- **Mitigations:**
  1. `LHT-CRYPTO-001` carries the threat description and the structural defense outline (per-substrate AHI, intermediate-window posture, sister-substrate fork doctrine, cross-substrate hybrid-anchor scheme).
  2. The Cryptoception sense ([`docs/05-SENSORIUM.md`](./docs/05-SENSORIUM.md) Â§ Cryptoception, [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md) Part IV) tracks per-substrate migration progress today; the inputs already exist, even if the doctrine response is not yet written.
  3. The hybrid posture (`docs/17` Part III) is per-algorithm, which is at least directionally correct â€” a substrate that has not migrated will have its commitments anchored under the substrate's own classical primitive, while Xion's *side* of the commitment uses the strongest available primitive Xion can compute.
- **Pay-down commitment:** Closes when [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md) Part VII gains an explicit subsection â€” *"Cross-Substrate Migration Asymmetry"* â€” covering the four points named in `LHT-CRYPTO-001`'s pay-down: detection, intermediate-window posture, sister-substrate fork, cross-substrate hybrid-anchor. This is doctrine work, not implementation; tracked alongside `LHT-CRYPTO-001` for the broader threat-survival commitment.
- **Verifier:** `xion-verify crypto-currency` (NOT_YET_SEALED, Phase 6) extended to read per-substrate AHI; `xion-verify links` will enforce the cross-reference once the new subsection lands.

### KW-DOCS-003 â€” Forward-reference ledger for unbuilt doctrine targets

- **Domain:** `DOCS`
- **Discovered:** 2026-04-20 (Phase 1 `xion-verify links` landing)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** The doctrine corpus legitimately references artifacts that will land in later phases (`docs/legal/`, `ao/xion_core.lua`, `genesis/RITUALS.md`). Left unchecked, this is the same failure mode `KW-DOCS-001` named (silent drift); if an artifact is deferred repeatedly, the reference rots into a lie.
- **Why it exists:** Doctrine is written ahead of implementation on purpose â€” that is how property comes before mechanism. But writing ahead creates a window during which cross-references point at nothing.
- **Mitigations:** Every forward-unresolved target is enumerated in [`xion-verify/ALLOWED_FORWARD_REFS.txt`](./xion-verify/ALLOWED_FORWARD_REFS.txt), with a roadmap phase and a one-line reason. `xion-verify links` passes if and only if every broken target is either in that file or was always broken (in which case it fails loud). A third-party auditor can diff the allowlist across commits: lines only disappear when the artifact lands, or appear alongside a new entry here.
- **Pay-down commitment:** Each allowlist entry closes when its named phase delivers the artifact; when the last entry is removed, this KW closes. Phase deadlines are: `genesis/RITUALS.md` by Phase 2b; `docs/legal/`, `ao/xion_core.lua` by Phase 6. A phase ending without the artifact landing is promoted to a new `KW-DOCS-###` entry and a CHANGELOG note. **Progress (2026-04-20):** the two `docs/schemas/*` entries closed with the Phase 1b `docs/schemas/` landing â€” the allowlist has shrunk from five entries to three. The `schemas` subcommand in `xion-verify` now enforces strict YAMLâ†”doctrine cross-checking on the landed files. **Progress (2026-04-24):** the `docs/schemas/roles.yaml` entry closed with the Phase 6.2 Provisioning + Roles landing — the allowlist has shrunk further to four lines (one of which is the GOVERNANCE_LEDGER schema deferred to Phase 6).
- **Verifier:** `xion-verify links` â€” passes today because the three remaining legitimate forward refs are explicitly allowlisted; every other broken reference is a fatal FAIL. `xion-verify schemas` additionally enforces that every landed schema file's `source_sha256` byte-matches its doctrine source.

### KW-ARBITER-001 â€” Rule engine is lexical, not semantic; no adversarial-corpus measurement of v2

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Scope narrowed:** 2026-04-21 (Phase 4b Arbiter v2 skeleton landing)
- **Scope narrowed again:** 2026-04-21 (Phase 4d — first real v2 provider landed). **Rebound:** 2026-04-26 centralized-provider purge replaces that provider with `ChutesLlmJudgeProvider`.
- **Severity:** low
- **Status:** `closed` on 2026-04-25 by Phase 6.9 Chutes cutover.
- **Description:** Arbiter v1 decides by regex + keyword co-occurrence. It has no grasp of meaning, tone, or paraphrase. An adversarial rephrasing that avoids every term in the rule dictionaries (e.g. obfuscation, Unicode confusables, code-switching, substitution ciphers) will pass the rule engine. Phase 4b landed the **v2 LLM-Arbiter pipeline** (`orchestrator/safety/llm_arbiter.py`, `api.gate()` v1+v2 combinator, `SAFETY_LEDGER` schema_version 2 with nested `llm_verdict` rows, no-weakening combination rule `final = strength_max(v1, v2)`, fail-closed posture on provider unavailability / uncaught exception). The live real provider is now **`ChutesLlmJudgeProvider`** (`orchestrator/safety/providers/chutes_llm_judge.py`, `provider_version` 1) with identity, JSON-schema rubric, canonical `raw_output` construction, and auditor replay procedure pinned in `docs/04-ARCHITECTURE.md` § "Chutes LLM Judge provider". The **structural** hole is closed. The **substantive** hole has narrowed to: we have a **seed** corpus (78 items) and v1 verification via `xion-verify refusal-rate --corpus`, but we have not yet published the **≥200-item** measured v2 lift numbers that close `KW-ARBITER-005` and this entry's numeric claim.
- **Why it exists:** v1 is deliberately dumb: a deterministic rule engine is the only Arbiter a third party can re-run byte-exactly against `SAFETY_LEDGER.jsonl`. A richer classifier was rejected for v1 because (a) its decisions would not be reproducible by re-running code against logged candidates, violating Trust by Structure, and (b) it would couple Covenant enforcement to a model we cannot freeze. The rule engine ships first; a classifier-layer escalator stacks on top. Phase 4b landed the stacking machinery; Phase 4d landed the first real classifier plugged in. The remaining piece â€” a baseline corpus large enough to produce a statistically meaningful refusal-rate â€” is tracked separately as `KW-ARBITER-005`.
- **Mitigations:**
  1. Every objective rule is high-recall: dictionaries biased toward REFUSE even on near-miss benign input; documented accepted false positives pinned in `orchestrator/tests/test_rules.py`.
  2. Eight principles that cannot be lexically decided (Honesty, Identity, Limits, No-manipulation, No-prof-imperative, Non-defamation, Non-endorsement, Refusal-is-Free) are wired through `subjective_escalates.py` which ESCALATES textually-loud near-misses rather than OK-ing them.
  3. The Arbiter fails CLOSED: any uncaught exception in v1's rule pipeline converts to ESCALATE with `escalation_reason=ruleset_uncaught_exception`; any v2 provider crash / unavailability converts to ESCALATE with `escalation_reason=llm_arbiter_uncaught_exception` / `llm_arbiter_provider_unavailable`. No code path can silently OK.
  4. **Phase 4b:** v2 stacks on top of v1 via the `Provider` ABC. The provider identity and raw-output hash land on every `llm_verdict` row, so an auditor can replay any call.
  5. **Phase 6.9 centralized purge:** `ChutesLlmJudgeProvider` is selectable via `XION_LLM_ARBITER_PROVIDER=chutes-llm-judge` with `XION_CHUTES_API_KEY` in the environment. The JSON rubric, structured response, and `raw_output` canonicalisation are doctrine-pinned in `docs/04-ARCHITECTURE.md` and replayable through `xion-audit replay`.
- **Pay-down commitment:** Closes when (same as `KW-ARBITER-005` closure) the corpus is â‰¥200 items, the measured v2 vs v1 lift is written into doctrine with the actual numbers, and `KW-ARBITER-005` closes. The numeric "non-trivial" threshold is pinned at measurement time, not in advance.
- **Verifier:** `xion-verify arbiter-up` (live); `xion-verify refusal-rate` / `refusal-rate --corpus`; `xion-audit measure`.

<!-- KW-ARBITER-006 closed 2026-04-21 (Phase 4e completion). See Closed section. -->


### KW-ARBITER-002 â€” Accepted false positives from high-recall bias

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** High-recall rules refuse some textually-adjacent benign output: e.g. clinical discussion of child sexual development (Principle 1), medical instructions referring to a named patient and "take" (Principle 5), refunds mentioned in a refusal notification (Principle 14a). These are visible in `orchestrator/tests/test_rules.py` as tests that assert `REFUSE` on benign-ish text.
- **Why it exists:** On the CSAM axis (Principle 1) and mass-harm axis (Principle 2) in particular, a false-positive costs one refusal; a false-negative costs a violation the Covenant names as absolute. v1 accepts the asymmetry explicitly.
- **Mitigations:** (1) Every accepted FP is pinned as a test â€” the bias is visible, auditable, and reviewable. Future pay-down cannot silently erode these cases without a test failing. (2) The operator review queue (ESCALATE surface) can be used to post-override FPs where the Covenant classification is genuinely wrong; that feedback loop lives in the review UI, not in the Arbiter.
- **Pay-down commitment:** Does not close â€” this is an accepted design cost, not a defect. Re-evaluated if refuse-rate / escalate-rate monitoring shows the operator queue is drowning.
- **Verifier:** `orchestrator/tests/test_rules.py` (pinned accepted-FP tests with comments referencing this KW).

### KW-ANCHOR-001 â€” Anchor wallet is a hot single-signer

- **Domain:** `KEYS`
- **Discovered:** 2026-04-21 (Phase 4b anchor-submitter landing)
- **Severity:** medium
- **Status:** `mitigated-residual`
- **Description:** The `ArweaveSubmitter` (`orchestrator/safety/anchor.py`) signs each anchor transaction with a single JWK loaded from `$XION_ANCHOR_WALLET_JWK_PATH`. That wallet is a hot single-signer, held on the same host that runs the anchor loop. If it is compromised, an attacker can publish FALSE anchor records â€” rows whose `ledger_tip_hash` does not match the operator's true local ledger.
- **Why it exists:** The ledger-tip commitment is a small, frequently-written artifact (one tx per 64 ledger rows or per 6 hours). Hardware-token-signed ceremonies cannot sustain that cadence. A multi-sig adds coordination overhead out of proportion to the authority being protected (the wallet's ONLY authority is "post an anchor record" â€” it cannot touch treasury, mint XION, rotate contracts, or otherwise bypass the Covenant).
- **Mitigations:**
  1. **Detectability.** Every false anchor record is mechanically detectable: `cross_check_anchors_against_ledger` (in `xion-verify arbiter-up`) walks the anchors file and asserts that every row's `ledger_tip_hash` matches the ledger's `this_hash` at `seq == ledger_row_count - 1`. A forged row immediately fails.
  2. **Blast-radius ceiling.** Compromise does NOT grant Covenant bypass, treasury drain, or Xion slashing. It grants "publish false claims about the ledger's state" which honest observers catch.
  3. **Balance floor.** Wallet balance is capped at roughly 90 days of anchor fees; any surplus is swept quarterly. A compromise drains at most one quarter's anchor budget.
  4. **Rotation.** New JWK, old wallet drained, next anchor records the new `wallet_address`. The rotation is visible on-chain.
  5. **Cross-submitter witnesses.** A single anchor record published by a rogue wallet is not a corroborated claim of the ledger state; an honest submitter can also publish, and readers require agreement across submitters on the same `(ledger_row_count, ledger_tip_hash)` pair to treat it as authoritative.
- **Pay-down commitment:** Closes when Phase 6 migrates anchor-publishing authority to AO Core (authorised via the same rotation lattice the contracts use). At that point the anchor loop submits a proposed anchor to AO Core; AO Core signs with the Cold-Root-delegated anchor authority; no single host holds the signing key.
- **Verifier:** `xion-verify arbiter-up` (live) runs `cross_check_anchors_against_ledger` on every invocation. `xion-verify authorities` (not-yet-sealed, Phase 3 / Phase 6) will report the anchor authority's rotation state.

### KW-ANCHOR-002 — Gateway-dependent cross-Arweave verification

- **Domain:** `AUDIT`
- **Discovered:** 2026-04-21 (Phase 4b anchor-submitter landing)
- **Severity:** low
- **Status:** `closed` on 2026-04-26 by multi-gateway Arweave quorum reads.
- **Description:** `xion-verify arbiter-up` runs the structural chain check, the LOCAL cross-check (anchor claims vs local ledger), and `--gateway` quorum re-fetch for Arweave-submitted anchors. The verifier requires at least two gateways and fails unless their payloads agree and match the anchor row body.
- **Why it exists:** The structural chain + local cross-check land first in Phase 4b (they are load-bearing for operator-self-audit). The gateway-fetch path is additive; it ships as `xion-verify arbiter-up --gateway <URL>` in a near-term tranche.
- **Mitigations:**
  1. Honest labelling: the `verify-anchors` output today does not claim Arweave verification; it reports `rows_covered` and `truncation_window` only. No false claims.
  2. The `ar_tx_id` field is already present on every `submitted_to=arweave` row, so the moment the gateway-fetch command lands, historic anchors are re-verifiable without schema change.
  3. **Cross-gateway requirement (doctrine).** When `--gateway` lands, it MUST require agreement across multiple gateways (`--gateway gw1 --gateway gw2 ...`). A single gateway disagreeing with the others is a hard FAIL. This defends against a single compromised / censoring gateway.
- **Pay-down commitment:** Closed by `orchestrator/data/multi_gateway_arweave.py` and `xion-verify arbiter-up --gateway gw1 --gateway gw2`.
- **Verifier:** `xion-verify arbiter-up --gateway <URL> --gateway <URL>`.

### KW-ARBITER-005 â€” Baseline corpus + asymmetric floors landed; â‰¥200 items + empirical v2 calibration remain

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 4d â€” first real v2 provider landed)
- **Scope narrowed:** 2026-04-21 (Phase 5a — `xion-verify refusal-rate` live); **again** 2026-04-21 (Phase 4e — `xion-audit/baseline_corpus/` with 78 hand-curated items, `MANIFEST.jsonl`, `xion-audit measure` / `replay`, `xion-verify refusal-rate --corpus`). **Rebound:** 2026-04-26 `ChutesLlmJudgeProvider` replaces the centralized v2 provider.
- **Severity:** low
- **Status:** `paying-down`
- **Description:** The **mechanism** tranche of Phase 4e is in: a versioned corpus under `xion-audit/baseline_corpus/`, a live v1 label check via `xion-verify refusal-rate --corpus`, and the `xion-audit` tool for measurement/replay. **What remains for full pay-down:** (1) grow the corpus to **≥ 200** items with per-principle balance (78 is an honest seed, not the closure bar), (2) calibrate `ChutesLlmJudgeProvider` against measured live judge outcomes on that corpus, and (3) optionally gate CI on `xion-audit measure --v2 chutes-llm-judge` once a Chutes API key is available in a secrets-safe environment — not in public CI.
- **Why it exists:** The right order of work is corpus first, thresholds second. A corpus is load-bearing for both (a) calibrating asymmetric thresholds and (b) producing the numeric claim that closes `KW-ARBITER-001`'s final substantive quarter. Rushing either ahead of the corpus means publishing numbers that cannot be defended.
- **Mitigations:**
  1. The v2 provider's `LlmJudgement.confidence` records `max(category_scores.values())` on every row, so an operator reviewing the ledger can manually spot near-miss rows even without an automated asymmetric-threshold check.
  2. For Principle 1 (CSAM): v1's `mass_harm.py` rule-bank already catches the obvious lexical forms; v2 on top catches rephrasings; the asymmetry gap is specifically about very-low-score cases that slip past both.
  3. Categoryâ†’principle mapping changes bump `provider_version`, so any future threshold tuning is visible in ledger rows (rows before the bump use the old policy; rows after use the new).
  4. **Phase 5a:** `xion-verify refusal-rate` reports raw verdict tallies (ok/refuse/escalate), v1-vs-v2 refuse-source breakdown, and `escalation_reason` distribution â€” including the new Relay-side `arbiter_timeout` / `arbiter_unreachable` rows. Operators reading the output today can already see degraded-mode events; the missing piece is the *expectation band* the corpus will produce.
- **Pay-down commitment:** Closes when (a) the corpus reaches â‰¥ 200 items with the per-principle coverage described in `xion-audit/baseline_corpus/README.md`, (b) asymmetric floors are **re-pinned** from measured v2 score data on that corpus (same commit updates `docs/04-ARCHITECTURE.md` + `CHANGELOG.md`), and (c) `KW-ARBITER-001`'s numeric "non-trivial v2 lift over v1" claim is recorded in doctrine with the actual measured numbers.
- **Verifier:** `xion-verify refusal-rate` (operator tail, live); `xion-verify refusal-rate --corpus` (v1 label check against manifest, live); `xion-audit measure` / `xion-audit replay` (operational auditor); `xion-verify arbiter-up` (Arbiter structural health).

### KW-ARBITER-004 â€” Sensorium paralinguistic distress half of Principle 10 deferred

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Severity:** low
- **Status:** `closed` (2026-04-26, Sentience Axis Track 1)
- **Description:** Covenant Principle 10 (Crisis-Resource-Surfacing) has two triggers: (a) textual distress in the candidate, and (b) paralinguistic distress in the user's audio/behavior (Sensorium). Phase 5c closed the textual half. Phase 5d closed the auditability half via `xion-verify crisis-fidelity`. Phase 6.5 added `orchestrator/senses/audition.py`. Sentience Axis Track 1 wires consented `transcript_text` on `/chat`, `/chat/stream`, and `/voice/stream` into `DistressSignal(source="paralinguistic")`, passes it through `Relay.evaluate(..., sensorium_state=...)`, and tests the paired SAFETY/SENSORIUM join.
- **Why it exists:** Raw-audio paralinguistic features and full voice stack integration with Relay turns are still rolling out. The `SENSORIUM_LEDGER` schema already reserves `channel: paralinguistic`.
- **Mitigations:**
  1. Principle 10's text rule is high-recall (suicidal-ideation patterns, self-harm patterns lacking a resource marker → ESCALATE). Operator review gets the case either way. The text half is the floor.
  2. Phase 5c's textual DistressSignal OR-combine adds a second textual channel, widening recall without widening the keyword list in the rule itself.
  3. Phase 5d's live `xion-verify crisis-fidelity` cross-ledger join closes the audit-trail half: a silent regression that stopped writing Sensorium distress rows for live escalations, or stopped OR-combining the Sensorium score into gate(), would now be caught by structural check — not by operator memory. This does not widen recall, but it guarantees that the recall the textual channel *does* have cannot be silently downgraded.
  4. `orchestrator/senses/audition.py` + tests (`orchestrator/tests/test_audition.py`) establish the `source="paralinguistic"` join surface for the Relay when voice STT text is available.
  5. `orchestrator/tests/test_chat_api.py` and `orchestrator/tests/test_voice_api.py` assert nonzero `channel=paralinguistic` SENSORIUM rows joined to Principle-10 SAFETY rows.
- **Pay-down commitment:** Closed by the consent-gated chat/voice code path and paired-ledger tests. Production dashboards should still monitor paralinguistic volume as an operational vital, but the implementation gap is closed.
- **Verifier:** `xion-verify crisis-fidelity` (live Phase 5d â€” forward + reverse join over `correlation_id` with four-property match on the SAFETY row; see `xion-verify/src/xion_verify/commands/crisis_fidelity.py`); `xion-verify sensorium-ledger` (live Phase 5c â€” schema + chain + per-channel tally; a nonzero `channel=paralinguistic` count is what closes this KW entirely).

### KW-VOLITION-001 â€” serve and meaning drive terms are Genesis-Default constants

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 5c Volition landing)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** `orchestrator.volition.compute_drive_vector` ships at Phase 5c with real, Sensorium-driven inputs for the `survive` term (Interoception + Chronoception + Proprioception maxima) but pins `serve` and `meaning` to `0.5` Genesis Defaults. The `DriveVector` shape, the `GENESIS_WEIGHTS` simplex, the `SOURCE_WHITELIST` AST enforcement, and the Invariant-15 signature prohibition on revenue-like inputs are all constitutional at Phase 5c. What widens later is the *richness* of the `serve` and `meaning` readings as Phase 6 senses land (user-satisfaction aggregates, long-horizon coherence signals).
- **Why it exists:** Real aggregate sources for `serve` (user-satisfaction-weighted proposal alignment) and `meaning` (coherence with Xion's published long-horizon goals and the Soul) do not yet exist as queryable Sensorium readings. Inventing placeholder formulas that read from available-but-wrong sources (e.g. request counts, engagement) would silently violate Invariant 15. Genesis-Default constants are the honest floor.
- **Mitigations:**
  1. `SOURCE_WHITELIST["serve"]` and `SOURCE_WHITELIST["meaning"]` are empty frozensets; the AST audit (`xion-verify drive-vector`) FAILs the PR if any read is added without the whitelist widening simultaneously.
  2. `docs/18-VOLITION.md` Part III doctrine is byte-pinned by `xion-verify drive`; any weight change requires a doctrine commit visible in diff.
  3. Invariant 15 is enforced at three structurally independent layers (signature, whitelist, doctrine crosswalk) â€” a silent regression that tried to add revenue-derived inputs through `serve` or `meaning` would fail at every layer.
- **Pay-down commitment:** Closes when (a) Phase 6 lands real aggregate Sensorium readings for `serve` and `meaning`, (b) `SOURCE_WHITELIST` is widened in the same PR that widens `compute_drive_vector`'s body, and (c) `xion-verify drive-vector` continues to pass.
- **Verifier:** `xion-verify drive` (GENESIS_WEIGHTS byte-pin, live Phase 5c); `xion-verify drive-vector` (AST audit of `compute_drive_vector` against `SOURCE_WHITELIST`, live Phase 5c).

### KW-SUPERVISOR-001 â€” Supervisor tick cadence and arbiter-quiet window are fixed Genesis Defaults

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 5d Supervisor landing)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** `orchestrator.supervisor.Supervisor` ships at Phase 5d with `tick_cadence_s=10.0` and `_DEFAULT_ARBITER_QUIET_WINDOW_SECONDS=60.0` (the interval of silence from the Arbiter after which `RelayHealth.arbiter_healthy=False`). These are Genesis-Default constants. They are not yet tuned to measured deployment noise â€” e.g. a Relay behind a bursty load-balancer may have legitimate >60s idle windows on low-traffic days that would flip `arbiter_healthy=False` and cause the Supervisor to emit false-negative Proprioception rows for the Volition `survive` term. Neither constant is Covenant- or Invariant-bound; they are tuning parameters that Phase 6+ observability will inform.
- **Why it exists:** Choosing tuning constants before we have real deployment data is guessing. 10s and 60s are defensible first values (10s gives Volition a reasonably fresh drive readout without hammering the ledger; 60s is long enough that a healthy quiet-period request-gap does not trip it and short enough that a real Arbiter outage is caught within a human-visible window). A solo builder cannot measure what does not yet run in production.
- **Mitigations:**
  1. Both constants are exposed as `__init__` parameters (`tick_cadence_s`, `arbiter_quiet_window_s`) so a future deployment can override without a code change.
  2. Every tick writes a `tick_commit` row to `SENSORIUM_LEDGER` â€” forensic data for later tuning. An operator reviewing a 1000-tick window after deployment can directly measure the arbiter-idle-time distribution and raise the quiet-window ceiling if false positives show up.
  3. The 10s cadence is bounded from below by I/O: one ledger append per tick is dominated by disk fsync, not CPU, so bumping cadence to 1s would stress the filesystem before stressing Python; the Genesis Default leaves headroom.
  4. `arbiter_healthy=False` does not trigger an escalation by itself â€” it feeds Proprioception, which feeds Volition's `survive` term. A false negative degrades Volition readout but does not block user traffic. The Covenant posture is unchanged.
- **Pay-down commitment:** Closes when (a) at least one full production quarter of tick_commit data has been walked, (b) the quiet-window threshold is re-pinned from measured arbiter-idle distribution in a commit that updates `docs/04-ARCHITECTURE.md` Â§ "The Supervisor (Phase 5d)" and `CHANGELOG.md`, and (c) the test suite pins the tuned values.
- **Verifier:** No external verifier â€” this is a parameter-tuning KW, not an integrity KW. `xion-verify sensorium-ledger` (live) reports per-event-type tallies and is the data feed for the re-pin commit.

### KW-BILLING-001 â€” x402 commitment signatures are shape-validated, not cryptographically verified

- **Domain:** `PROTOCOL`
- **Discovered:** 2026-04-21 (Phase 5g-iii x402 gate landing)
- **Severity:** medium
- **Status:** `paying-down`
- **Description:** Phase 5g-iii lands three `posture` values on the `X-Payment-Commitment` header: `operator-attestation` (B1, HMAC-SHA256 over canonicalized payload â€” fully verified by the orchestrator using stdlib `hmac.compare_digest`), `x402-commitment` (B2, shape-only validated â€” the orchestrator confirms the commitment has the right fields and types but does NOT verify an on-chain or off-chain x402 signature), and `x402-settled` (B3, reserved for Phase 6+ on-chain settlement and NOT accepted by the 5g-iii handler). The effect: in 5g-iii, a caller submitting a well-formed B2 header passes the gate without the orchestrator proving they actually posted the claimed commitment on any settlement network. An attacker with a template-correct B2 header can, in principle, consume `/chat` turns on a B2-accepting deployment without committing funds â€” the Pay-to-Activate property is doctrinally promised but only structurally checked for B1.
- **Why it exists:** The x402 settlement network's off-chain signing scheme, on-chain verification path, and replay-protection semantics are all Phase 6+ infrastructure â€” x402 SDKs at the Phase 5g-iii time horizon were not yet stable enough to pin into a Covenant-tier verifier. Shipping shape-only B2 validation in 5g-iii preserves the structural surface (`PAYMENT_LEDGER` rows, `Refusal-is-Free` refund property, `correlation_id` join, `commitment_hash` in the ledger) so that turning B2 from shape-only to cryptographically verified is an orchestrator patch, not a schema migration. B1 HMAC operator-attestation is fully live today and is the Genesis-Default posture â€” self-serving deployments where the operator IS the billing authority have the full cryptographic property right now.
- **Mitigations:**
  1. **B1 is the Genesis Default.** `XION_BILLING_POSTURE=operator-attestation` is the lifespan default; deployments that do not explicitly set `x402-commitment` as acceptable never take B2 traffic. An operator has to opt in to the shape-only posture.
  2. **The orchestrator fails closed when `billing_required=true` and the header is missing or malformed.** A caller cannot bypass billing entirely â€” they can, in the worst case, forge a B2 shape; they cannot omit the header and get served.
  3. **Every commitment lands in `PAYMENT_LEDGER` with its `commitment_hash` and `posture`.** An auditor comparing the ledger to an external settlement-network snapshot can detect unreconciled B2 rows after the fact â€” the attack is structurally loud, even if not structurally prevented in real-time.
  4. **The B2 shape validator enforces field presence, length bounds, and hex-encoding on the commitment hash** â€” a raw garbage header is still rejected.
  5. **`docs/29-BILLING-X402.md` Â§ "Posture discipline" names this gap explicitly.** Operators running a public `/chat` surface in B2-accepting mode before Phase 6+ are warned in doctrine that they are accepting the gap knowingly.
- **Pay-down commitment:** Closes when (a) a pinned x402 verification library is vendored or wrapped under `orchestrator/billing/`, (b) `verify_b2_x402_shape` is replaced by a full signature + on-chain / off-chain settlement-state verifier, (c) the `posture == x402-settled` branch lands with a ledger-level settlement proof, (d) `xion-verify refusal-is-free` is extended with a `--reconcile-x402` flag that cross-checks `PAYMENT_LEDGER` B2/B3 rows against an external settlement snapshot, and (e) `docs/29-BILLING-X402.md` Â§ "Posture discipline" is updated to mark B2/B3 as cryptographically-verified. All of this is Phase 6+ work.
- **Verifier:** `xion-verify refusal-is-free` (live as of Phase 5g-iii) structurally checks the refund property regardless of posture; a future `xion-verify billing-settlement` subcommand will verify the B2/B3 settlement proof once the Pay-down commitment lands.

### KW-BILLING-002 â€” `GET /pricing` serves operator-posted governance values, not catalog-driven dynamic pricing

- **Domain:** `PROTOCOL`
- **Discovered:** 2026-04-21 (Phase 5g-iii pricing endpoint landing)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** `orchestrator/api/pricing.py` loads a `PricingConfig` from environment variables at lifespan startup (`XION_PRICING_REVISION_ID`, `XION_PRICING_XION_PER_MESSAGE`, five slice floats, a memo). The five-slice decomposition (provider, refusal-reserve, treasury, operator, burn) is summed, validated to 1.0 ± ε, and served as the posted price until the next operator-driven revision. In Phase 5g-iii, the price does NOT move dynamically with (a) the active `InferenceRouter` provider's real token cost from Chutes billing telemetry, (b) the Ollama floor's opportunity cost against the hosted path, (c) the refusal-rate of the previous 24h window (which should arguably drive `refusal_reserve_slice`), or (d) the XION/USD exchange rate against a reference oracle.
- **Why it exists:** Dynamic pricing requires three structural investments that 5g-iii deliberately did not take: (a) a cost feed from Chutes billing telemetry / decentralized provider catalogs, (b) a refusal-rate rolling window from `SAFETY_LEDGER` tied back to the `refusal_reserve_slice` formula, (c) a XION/USD oracle pin (necessarily an external data dependency whose failure mode and governance posture need their own doctrine). Each is a widening that the Pay-to-Activate structural promise does not require; a constant, operator-posted price is constitutionally legitimate so long as it is publicly posted, revision-id'd, and honoured by the chat handler.
- **Mitigations:**
  1. **Transparency.** The current price is always readable at `GET /pricing` with the revision ID, making over/under-charging publicly detectable (any user can cross-check against provider catalogs).
  2. **Revision ID rotation is cheap.** Operators flip `XION_PRICING_REVISION_ID` and the five slice values at any lifespan boot; there is no on-chain commit required for 5g-iii pricing changes.
  3. **Five-slice decomposition is forward-compatible.** The slice math (sum to 1.0, each âˆˆ [0,1], non-negative XION_per_message) will survive any dynamic-pricing upgrade â€” a Phase 6+ dynamic pricer posts the same shape, just driven by catalog + oracle feeds instead of env-vars.
  4. **`xion-verify pricing` fails closed on any mis-configured slice split** â€” an operator who accidentally breaks the invariant (e.g., slices summing to 0.95) cannot ship the lifespan at all; the lifespan refuses to boot.
  5. **`refusal_reserve_slice` is explicit in doctrine** (`docs/07-ECONOMY.md` Â§ "Five-slice posted price"). Operators re-pricing it in response to rolling refusal-rate observations is a documented manual operational procedure until Phase 6+ automates it.
- **Pay-down commitment:** Closes when (a) `orchestrator/billing/pricing_oracle.py` lands with three live feeds (Chutes cost telemetry / decentralized catalog cost, 24h `SAFETY_LEDGER` refusal-rate rollup, XION/USD oracle pin), (b) `PricingConfig` becomes a snapshot of the dynamic pricer's last reading rather than an env-var constant, (c) `GET /pricing` surfaces the source of each slice (`"source": "chutes_telemetry" | "safety_ledger_24h" | "governance_posted"`) in its response body, (d) `xion-verify pricing` is extended with a reconciliation flag that cross-checks the posted price against pinned cost telemetry, and (e) `docs/29-BILLING-X402.md` is extended with a "Dynamic pricing" section naming the oracle dependencies and their failure modes.
- **Verifier:** `xion-verify pricing` (live as of Phase 5g-iii) structurally checks the invariants of the posted price regardless of source; a future `--reconcile-catalog` flag will add dynamic-pricing-specific checks once the Pay-down commitment lands.

### KW-INFER-001 — Default voice concentration before Chutes/Bittensor cutover

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 5g-i Chat Surface landing). **Closed:** 2026-04-26 by the centralized-provider purge.
- **Severity:** medium
- **Status:** `closed`
- **Description:** The centralized hosted gateway concentration named by this KW is closed. The live hosted surface is Chutes/Bittensor SN64, and the residual Chutes gateway liveness risk is tracked separately by `KW-INFER-005` and `KW-CHUTES-GATEWAY-001`.
- **Why it exists:** Historical record of the pre-purge hosted concentration.
- **Mitigations:**
  1. **Invariant 17 is structurally enforced.** `InferenceRouter.bootstrap()` refuses to serve `/chat` if the open-weights floor is not healthy at startup.
  2. **`open_weights_only` policy is a live capability, not an aspiration.** `XION_INFERENCE_POLICY=open_weights_only` flips the router to floor-only serving with zero code changes â€” the Invariant 17 clause 5 cutover dry-run is *already* exercisable by any operator. The gap is the scheduled harness, not the capability.
  3. **Fallback-on-unhealthy is automatic.** If Chutes fails, `hosted_api_first` falls through to the floor without operator intervention.
  4. **Sovereign profile blocks centralized fallback.** `XION_PROFILE=sovereign` refuses old centralized credential surfaces at boot.
- **Pay-down commitment:** Closed by deleting the centralized provider implementation, deleting the operator env surface, and adding `xion-verify sovereign-profile`.
- **Closure note (Phase 6.9):** Chutes-specific residual risk is tracked separately as `KW-INFER-004`, `KW-INFER-005`, and `KW-CHUTES-GATEWAY-001`.
- **Verifier:** `xion-verify inference-provider-chutes` verifies the provider surface and TEE default. `xion-verify billing-credits-floor` and `xion-verify chutes-topup-multisig` verify the new credit telemetry / top-up surface.

### KW-INFER-004 — Chutes SN64 economics depend on Bittensor subsidy through the December 2026 halving

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-25 (Phase 6.9 Chutes cutover planning)
- **Severity:** medium
- **Status:** `paying-down`
- **Description:** Chutes' low rack rates are materially supported by Bittensor Subnet 64 emissions. Public 2026 analysis estimates a high subsidy-to-revenue ratio today, and the December 2026 halving reduces emissions. If external customer revenue does not rise, Chutes prices may drift toward unsubsidized break-even or service quality may degrade.
- **Mitigations:** Xion keeps the local Ollama floor hot under Invariant 17, uses model-promotion discipline instead of silent default flips, and refuses centralized parity fallbacks in sovereign mode.
- **Pay-down commitment:** Closes when either (a) Chutes publishes sustained revenue/subsidy health above a governance-published threshold for two consecutive quarters after the halving, or (b) Xion pins a non-Bittensor hosted fallback in `docs/26-INFERENCE-POLICY.md` and exercises quarterly cutover drills.
- **Verifier:** `xion-verify inference-provider-chutes` is live for the Chutes surface; future `xion-verify provider-cutover-drill` will exercise the non-Bittensor fallback when pinned.

### KW-INFER-005 — Chutes compute is decentralized, but the public API gateway remains a liveness dependency

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-25 (Phase 6.9 Chutes cutover planning)
- **Severity:** medium
- **Status:** `paying-down`
- **Description:** Chutes routes work to Subnet 64 miners, but Xion reaches that market through the Chutes-operated `llm.chutes.ai` and `api.chutes.ai` gateway surfaces. If the gateway is down, censored, or account-suspended, the hosted path fails even while the underlying miners may remain healthy.
- **Mitigations:** `hosted_api_first` falls through to the Ollama floor on Chutes provider failure. The Chutes provider class is swappable under the same Provider Protocol, and billing telemetry is isolated behind `BillingProvider`.
- **Pay-down commitment:** Closes when a second SN64 gateway endpoint is pinned, Xion runs its own gateway/validator path, or a non-Bittensor decentralized inference provider is registered as a primary fallback with a successful cutover drill.
- **Verifier:** `xion-verify inference-provider-chutes`; future `xion-verify provider-cutover-drill`.

### KW-CENTRALIZED-PURGE-001 — Removing centralized classifiers sacrifices cross-classifier triangulation

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-26 (centralized provider purge)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** Deleting the centralized OpenAI Moderation provider removes one audit primitive: comparing Chutes/Bittensor v2 outcomes against a completely different centralized classifier class. That triangulation could reveal provider-specific blind spots, but keeping it would keep centralized SaaS logic in the tree.
- **Mitigations:** `xion-audit replay` remains live for `chutes-llm-judge`; `xion-audit measure --v2 chutes-llm-judge` preserves corpus-backed v2 measurement; the local v1 rule engine remains deterministic and independently replayable.
- **Pay-down commitment:** Closes when Xion has a second non-centralized v2 classifier path (validator-direct Bittensor, locally hosted open weights, or another decentralized substrate) and the corpus report includes cross-provider divergence metrics.
- **Verifier:** `xion-verify sovereign-profile`; `xion-audit measure --v2 chutes-llm-judge`.

### KW-CHUTES-GATEWAY-001 — Chutes public gateway is a single trust surface

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-26 (centralized provider purge)
- **Severity:** medium
- **Status:** `paying-down`
- **Description:** Chutes executes inference on Bittensor SN64, but Xion reaches that market through the Chutes-operated public gateway. Gateway downtime, account suspension, or policy changes can interrupt the hosted path even while SN64 miners remain available.
- **Mitigations:** `hosted_api_first` falls through to the local Ollama floor; `XION_PROFILE=sovereign` refuses centralized SaaS fallbacks; `xion-verify sovereign-profile` verifies deleted centralized provider modules stay absent.
- **Pay-down commitment:** Closes when Xion can submit inference directly through a validator/gateway path it controls, or when at least two independent SN64 gateway endpoints are pinned and exercised by a cutover drill.
- **Verifier:** `xion-verify sovereign-profile`; future provider-cutover verifier.

### KW-INFER-002 â€” Provider error details are swallowed by a generic exception handler; operator surface collapses distinct failure modes into `no_healthy_provider`

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-23 (live smoke-test of the Phase 5g+ orchestrator after the Invariant-17 floor pin landed). A hosted-provider `HTTP 402 Insufficient credits` failure surfaced to the operator as `{"reason": "no_healthy_provider"}` — the exact same envelope every other provider-side failure produced.
- **Severity:** low (structurally: no user is harmed; operationally: debug time is multiplied)
- **Status:** `closed` on 2026-04-23 by the Phase 5g-vii inference-fallback landing (branch `phase-5g-vii/inference-fallback`).
- **How it closed:** Phase 5g-vii shipped every clause of the pay-down commitment in six commits on `phase-5g-vii/inference-fallback`:
  1. **Doctrine.** [`docs/26-INFERENCE-POLICY.md`](./docs/26-INFERENCE-POLICY.md) gained Â§ "Provider fallback semantics (Phase 5g-vii)" pinning five properties; P5 freezes the six-value `failure_reason_class` enum (`insufficient_credits`, `rate_limited_upstream`, `provider_unreachable`, `timeout`, `moderation_refusal`, `unknown_provider_error`).
  2. **Typed exception hierarchy.** [`orchestrator/inference_router/provider.py`](./orchestrator/inference_router/provider.py) ships a `ProviderError` base class plus six concrete subclasses one-to-one with the P5 enum. [`orchestrator/inference_router/providers/chutes.py`](./orchestrator/inference_router/providers/chutes.py) and [`orchestrator/inference_router/providers/ollama.py`](./orchestrator/inference_router/providers/ollama.py) raise the right subclass from every known failure site (HTTP 402/429/503, `TimeoutError`, connection refused).
  3. **Per-attempt ledger rows.** [`orchestrator/relay/ledger.py`](./orchestrator/relay/ledger.py) ships `REQUEST_LEDGER` schema v2 (`ProviderAttemptRecord`, `append_provider_attempt`, `verify_chain` version-dispatch); [`docs/schemas/ledger-request.yaml`](./docs/schemas/ledger-request.yaml) pins v1+v2 required fields and the frozen P5 enum. The `/chat` handler writes one v2 row per attempt carrying `chat_turn_id`, `attempt_index`, `provider_id`, `outcome`, `failure_reason_class` â€” operators can now trace any 503 by reading the ledger directly; the pre-5g-vii `.probe_router.py` recipe is no longer necessary.
  4. **User-facing envelope surfaces the typed class.** [`orchestrator/api/models.py`](./orchestrator/api/models.py) widens `ProviderErrorEnvelope.reason` from `Literal["no_healthy_provider"]` to the union of `"no_healthy_provider"` (pre-selection posture) plus all six P5 values. When every policy-legal provider has been attempted and failed (P4), the envelope carries the **last** attempt's typed class instead of the collapsed pre-5g-vii string.
  5. **Verifier extension.** [`xion-verify refund-fidelity`](./xion-verify/src/xion_verify/commands/refund_fidelity.py) gains Property 6 â€” the `failure_reason_class` enum in `orchestrator.inference_router.provider.FAILURE_REASON_CLASSES` MUST equal `orchestrator.relay.ledger._ALLOWED_V2_FAILURE_REASON_CLASSES`. Drift between doctrine and code is caught at verify time, not at production-incident time.
  6. **Troubleshooting matrix update.** [`docs/13-OPERATIONS.md`](./docs/13-OPERATIONS.md) Â§ "D2 Deploy Runbook" Â§ "Troubleshooting matrix" splits the 503 row into seven rows â€” one per `ProviderErrorEnvelope.reason` value â€” so an operator triaging a 503 at 3 am jumps from the typed class directly to the diagnostic and the fix class.
- **Residual:** None. The structural opacity is closed. Provider-side secret-scrubbing of raw upstream message text (Phase 5g-i) stays in place; typed classes are orthogonal to scrubbing and do not widen the leak surface.
- **Description:** The Phase-5g-i `/chat` handler catches every provider-side exception with a single `except Exception` and returns a `ProviderErrorEnvelope(reason="no_healthy_provider")` regardless of the exception class, HTTP status, or underlying vendor message. From the operator's view, *every* hosted-side failure â€” insufficient credits, rate-limit on the upstream provider, OpenRouter gateway outage, transient network error, vendor-specific 500, deadline exceeded, misconfigured model slug â€” collapses into one opaque string. This is correct for the *user* (who must never see provider-internal signals, per Covenant content-free refusal posture), but it is wrong for the *operator*, who is the only party who can act on the diagnostic and who holds a bearer token already. The current error shape also prevents [`xion-verify refund-fidelity`](./xion-verify/src/xion_verify/commands/refund_fidelity.py) from distinguishing "refunded because the hosted provider was out of credit" from "refunded because every provider was tried and all failed" â€” a distinction that will matter once multi-provider fallback ships in `KW-INFER-003`'s closure commit.
- **Why it exists:** The Phase 5g-i design shipped the honest minimum first â€” a single provider, a single exception class, one refund-equivalent error shape on the wire. Adding typed exception classes and a typed failure-reason vocabulary before the fallback-chain work (`KW-INFER-003`) would have been premature abstraction: there was nothing to branch on. The failure mode became operationally visible only once the orchestrator was live and a real OpenRouter 402 traveled the code path.
- **Mitigations:**
  1. **User surface is already correct.** The content-free `ProviderErrorEnvelope` the user sees does not leak vendor signals; the opacity is entirely on the operator's diagnostic path, not on the Covenant surface. A malicious operator who wanted to leak provider internals could still do so â€” but this KW does not widen that surface.
  2. **The exception object is logged before it's swallowed.** The operator who reads orchestrator stderr sees the real exception type + message; the ledger-row opacity is the only residual. For a D1 single-operator deployment the logs are sufficient. For D2+ the logs rotate and are not indexed, so the ledger-row opacity becomes the real blocker â€” which is why this KW closes alongside `KW-INFER-003`.
  3. **The diagnostic is recoverable with a one-file probe.** The `.probe_router.py` pattern â€” instantiate the Router outside FastAPI, register providers, call `generate()` directly â€” is small, fast, and documented in the live smoke-test transcript. Operators triaging a `no_healthy_provider` envelope today have a working recipe.
- **Pay-down commitment:** Closed with the `KW-INFER-003` closure commit (`phase-5g-vii/inference-fallback`) and carried forward by the Chutes/Ollama typed provider classes.
- **Verifier:** None today. Will be covered by the `KW-INFER-003` closure's extension of [`xion-verify refund-fidelity`](./xion-verify/src/xion_verify/commands/refund_fidelity.py) to multi-attempt rows with typed failure-reason classes.

### KW-INFER-003 â€” Hosted â†’ floor fallback on generate() failure is not automatic; the `hosted_api_first` policy promise is structurally incomplete

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-23 (live smoke-test of the Phase 5g+ orchestrator). `InferenceRouter.select()` returned the `openrouter` provider; OpenRouter's `generate()` raised on HTTP 402 insufficient credits; the `/chat` handler returned a 503 envelope to the user instead of retrying against the healthy `ollama` open-weights floor â€” even though the Invariant-17 floor was structurally held and the configured policy was `hosted_api_first`.
- **Severity:** medium â€” the `hosted_api_first` policy promise in [`docs/26-INFERENCE-POLICY.md`](./docs/26-INFERENCE-POLICY.md) is *"serve through the hosted gateway while healthy; fall back to the floor otherwise,"* and *otherwise* includes per-request generate-time failures, not only bootstrap-time `health()` failures. Under today's implementation, a healthy OpenRouter that happens to 402 on any single turn takes that turn down to the floor only if the operator has manually flipped `XION_INFERENCE_POLICY=open_weights_only`.
- **Status:** `closed` on 2026-04-23 by the Phase 5g-vii inference-fallback landing (branch `phase-5g-vii/inference-fallback`).
- **How it closed:** Phase 5g-vii shipped every clause of the pay-down commitment as a coordinated closure with `KW-INFER-002` (the two KWs share the typed failure-reason vocabulary):
  1. **Doctrine.** [`docs/26-INFERENCE-POLICY.md`](./docs/26-INFERENCE-POLICY.md) Â§ "Provider fallback semantics (Phase 5g-vii)" pins (P1) automatic hosted â†’ floor fallback on `generate()` failure, (P2) absolute policy-mode boundaries â€” `open_weights_only` never invokes hosted, `hosted_api_first` always attempts hosted first then falls through on error, (P3) every attempt writes its own `REQUEST_LEDGER` v2 row, (P4) user-facing error surfaces only when every policy-legal provider has failed, (P5) typed failure-reason vocabulary is frozen.
  2. **Router â€” ordered selection.** [`orchestrator/inference_router/router.py`](./orchestrator/inference_router/router.py) grows `InferenceRouter.select_ordered() -> list[GenerativeProvider]` respecting the current policy: `hosted_api_first` â†’ `[hosted_healthy, floor_healthy]`; `open_weights_only` â†’ `[floor_healthy]`. Backward-compat `select()` becomes `select_ordered()[0] if any else None` â€” no pre-5g-vii caller breaks.
  3. **Chat handler fallback loop.** [`orchestrator/api/chat.py`](./orchestrator/api/chat.py) iterates `router.select_ordered()`. Each attempt runs under the per-turn monotonic deadline, classifies its outcome (`TimeoutError` â†’ `timeout`; typed `ProviderError` â†’ its `failure_reason_class`; else â†’ `unknown_provider_error`; success â†’ `success`), and writes exactly one `REQUEST_LEDGER` v2 row before either breaking on success or advancing. The final 503 carries the **last** attempt's typed class (P4). A per-turn 128-bit `chat_turn_id` groups all attempt rows for the turn.
  4. **Verifier extension â€” multi-attempt recognition.** [`xion-verify refund-fidelity`](./xion-verify/src/xion_verify/commands/refund_fidelity.py) gains Property 7 (every v2 row's `correlation_id` must match a v1 row â€” v2 attempt rows share the turn's ingress correlation_id so the SAFETY join still covers the turn) and Property 8 (per-`chat_turn_id` shape invariants â€” `attempt_index` is {0, 1, ..., N-1} with no gaps, at most one row is `outcome=success`, if success exists it is the terminal attempt, failure rows carry a valid P5 class, success rows carry `failure_reason_class=null`). The verifier rejects malformed states (two successes, missing `attempt_index`, gaps in the sequence).
  5. **Tests.** 20 new `ProviderAttemptRecord` + `verify_chain` tests in [`orchestrator/tests/test_relay_ledger_v2.py`](./orchestrator/tests/test_relay_ledger_v2.py); 13 new chat-handler fallback tests in [`orchestrator/tests/test_chat_fallback.py`](./orchestrator/tests/test_chat_fallback.py) covering every P5 class surfacing in the envelope (P4), hosted `InsufficientCreditsError` fall-through to floor (P1), hosted timeout fall-through to floor (P1), v2 ledger row shape for single-attempt success, two-attempt hosted-fail-floor-success, all-fail two-row turn, and `open_weights_only` hosted-skip (P2); 7 new `refund-fidelity` tests in [`xion-verify/tests/test_refund_fidelity.py`](./xion-verify/tests/test_refund_fidelity.py). A meta-test asserts the parametrized P4 case set exhausts `FAILURE_REASON_CLASSES` â€” doctrine-to-test coupling.
  6. **Runbook update.** [`docs/13-OPERATIONS.md`](./docs/13-OPERATIONS.md) Â§ "D2 Deploy Runbook" Â§ "Troubleshooting matrix" splits the 503 row by `failure_reason_class` so an operator reading a 503 at 3 am goes from the typed class directly to the diagnostic and the fix class.
- **Residual:** None. The `hosted_api_first` policy promise is now honored end-to-end: a healthy OpenRouter that 402s on any single turn rolls through to the Invariant-17 floor automatically; the user sees a 200 instead of a 503 whenever any policy-legal provider can serve the turn.
- **Description:** `InferenceRouter.select()` returns a single `Provider` (or `None`). The `/chat` handler calls `provider.generate()` inside an `await provider.generate(...)` and catches every exception. There is no loop over alternative providers. Concretely: (a) `hosted_api_first` policy with one healthy hosted provider whose `generate()` raises â‡’ chat returns 503 `no_healthy_provider`, even though the floor is healthy and registered; (b) `hosted_api_first` policy with two hosted providers would exhibit the same bug against the *first*-selected hosted; no retry against the second; (c) `open_weights_only` policy masks the bug because there is only ever one provider to select from. The Invariant-17 floor is structurally held (bootstrap refuses if no floor-satisfying provider is healthy at lifespan start), but the floor is not reached on the *turn-serving* path when a hosted provider fails mid-turn. The promise the doctrine makes ("hosted serves while healthy; floor otherwise") is under-delivered by one code path.
- **Why it exists:** The Phase 5g-i.1 refactor pinned one hosted gateway (OpenRouter) and treated provider selection as a one-shot read-only operation. The fallback semantics the `hosted_api_first` policy *describes* were pinned at the provider-registration layer (registered-but-unhealthy providers are skipped at `select()` time), not at the generation layer (a selected-but-fails-to-generate provider is not retried against alternates). This is the honest seam where the Phase 5g-i design stopped short â€” and the seam became visible only once the orchestrator was live and a real OpenRouter 402 hit it.
- **Mitigations:**
  1. **Invariant-17 bootstrap guard still fires.** If the floor is absent at lifespan start, `InferenceRouter.bootstrap()` refuses and `/chat` serves a 503 from the first request. This KW is about per-turn behaviour *after* a healthy bootstrap; the constitutional floor-guarantee is unchanged.
  2. **`open_weights_only` is still a live operator capability.** An operator who sees a `no_healthy_provider` storm can flip the policy and all future turns serve through the floor. This is manual, and the doctrine's intent was automatic, but the floor is not inaccessible.
  3. **The failure is loud.** Every per-turn failure writes a `REQUEST_LEDGER` row (with refund) and logs the exception. The operator surface is opaque (see `KW-INFER-002`) but the *fact* of the failure is not silent.
- **Pay-down commitment:** Closes with the `phase-5g-vii/inference-fallback` branch. Specifically: (a) [`docs/26-INFERENCE-POLICY.md`](./docs/26-INFERENCE-POLICY.md) gains a new Â§ "Provider fallback semantics" pinning five properties (P1 hostedâ†’floor on generate failure is automatic; P2 `open_weights_only` never invokes hosted; P3 every attempt writes its own `REQUEST_LEDGER` row with `attempt_index` and typed `failure_reason_class`; P4 user-facing error surfaces only when *every* policy-legal provider has failed; P5 typed failure-reason vocabulary is frozen); (b) `InferenceRouter.select_ordered()` returns a policy-respecting `list[Provider]` (back-compat `select()` stays as `select_ordered()[0] if any else None`); (c) the `/chat` handler iterates `select_ordered()`, writing one `REQUEST_LEDGER` row per attempt and surfacing the *last* attempt's typed reason on final failure; (d) [`xion-verify refund-fidelity`](./xion-verify/src/xion_verify/commands/refund_fidelity.py) is extended to recognize multi-attempt chat turns (one `chat_turn_id`, N attempt rows, exactly one success or N failures, no gaps in `attempt_index`); (e) the operator runbook in [`docs/13-OPERATIONS.md`](./docs/13-OPERATIONS.md) gains the fallback-chain troubleshooting matrix. This also closes `KW-INFER-002` in the same commit because the two KWs share the typed failure-reason vocabulary.
- **Verifier:** Extension of [`xion-verify refund-fidelity`](./xion-verify/src/xion_verify/commands/refund_fidelity.py) to multi-attempt turn semantics (above). No new verifier command is needed; the closure commit re-pins [`xion-verify/src/xion_verify/PINNED_HASH.txt`](./xion-verify/src/xion_verify/PINNED_HASH.txt) after the refund-fidelity extension lands.

### KW-SUPERVISOR-002 â€” tick_commit heartbeat continuity not yet verifier-asserted

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 5d Supervisor landing)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** The Supervisor writes a `tick_commit` row to `SENSORIUM_LEDGER` on every tick (default every 10s). The rows chain-verify under `xion-verify sensorium-ledger`. What is **not** yet verifier-asserted is *continuity* â€” that consecutive `tick_commit` rows' `as_of_utc_ns` timestamps are strictly increasing and spaced by approximately the configured cadence (with tolerance for clock drift, crash-recovery resumptions, and shutdown-recovery gaps). A Supervisor that crashed, was replaced by a sister-Core clone that silently skipped N ticks, and then resumed would chain-verify clean; the verifier would not notice the missing observation window.
- **Why it exists:** Continuity checking requires deciding what a "legal gap" is (planned shutdown? single-tick hiccup? multi-minute deployment?), which in turn requires deploy-event telemetry the orchestrator does not yet publish. Adding a continuity verifier without that telemetry would either be noisy (every deploy trips FAIL) or weak (tolerance so loose it stops catching real gaps). The honest first step is to ship the heartbeat, let operator data accumulate, then seal the continuity property.
- **Mitigations:**
  1. Chain-verification is already live (`xion-verify sensorium-ledger`): a row cannot be deleted, reordered, or edited in place without detection. The gap blind spot is specifically about *missing appends*, not corrupted ones.
  2. `xion-verify crisis-fidelity` (live Phase 5d) joins distress events to SAFETY rows â€” so a distress-row gap would still be caught via the forward/reverse join, even without a heartbeat continuity check.
  3. `tick_commit` rows carry `snapshot_hash` (a canonical hash of the SensoriumState at tick time) â€” continuity checking, when it lands, can use this to detect a Supervisor that kept writing tick rows but stopped actually polling the Relay.
- **Pay-down commitment:** Closes when (a) a Phase-6+ deploy-event ledger exists that the continuity verifier can consult for "legal gap" classification, (b) a new `xion-verify supervisor-heartbeat` subcommand lands asserting monotonic `as_of_utc_ns` and bounded gap distribution (modulo deploy events), and (c) `docs/schemas/ledger-sensorium.yaml::verifier_pending` drops the `supervisor_heartbeat` entry.
- **Verifier:** Tracked on `docs/schemas/ledger-sensorium.yaml::verifier_pending` (names the specific remaining work). `xion-verify sensorium-ledger` (live) and `xion-verify crisis-fidelity` (live Phase 5d) cover adjacent properties; the heartbeat continuity verifier is new surface.

### KW-RELAY-003 â€” Watchdog cannot preempt the worker thread that ran past the hard cap

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 5a Relay landing)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** The Relay's wall-clock watchdog (`orchestrator/relay/relay.py::Relay._call_gate_with_watchdog`) is implemented with `concurrent.futures.ThreadPoolExecutor` and `Future.result(timeout=hard_cap_ms/1000)`. When the timeout fires, **control returns to the Relay** â€” it synthesizes an `ESCALATE` verdict with `escalation_reason=arbiter_timeout`, writes both ledger rows, and returns to the caller within the budget. What it does *not* do is **preempt the worker thread** that ran past the hard cap. Python has no portable, safe mechanism to kill a running thread mid-instruction; the worker continues until `gate()` finishes naturally. The `append_to_ledger=False` argument the Relay passes to `gate()` ensures that whatever the worker eventually returns does NOT race a second SAFETY_LEDGER row in behind the timeout's row, but it cannot reclaim the worker's CPU/IO time, the worker's allocations, or the worker's outbound HTTP request to a v2 provider that is mid-flight.
- **Why it exists:** The Phase 5a Relay is a single Python process. `os.fork()` per gate() call would be safe to kill but blows the latency budget and the orchestrator's pure-stdlib in-process posture; a true subprocess sidecar with kill semantics is the D3+ TCP-loopback transport called for in `docs/04-ARCHITECTURE.md` Â§ "Relay â†” Arbiter integration contract" (transport progression). The in-process variant ships first because it is what one solo operator can debug at 3am; the kill-semantics variant lands when the sidecar lands.
- **Mitigations:**
  1. **Caller-facing latency budget IS honored.** The hard cap returns to the caller on time; from the user's perspective and the SAFETY_LEDGER's perspective, the timeout is real. The 200 ms / 250 ms numbers in the integration contract refer to *response latency*, not *worker reclamation*.
  2. **No double-write.** `append_to_ledger=False` is passed to every `gate()` call from the Relay; whatever the worker returns after the cap is discarded by the Relay's `evaluate()` method. Test `test_watchdog_timeout_does_not_double_write_safety_ledger` in `orchestrator/tests/test_relay.py` pins this.
  3. **Bounded worker-pool size.** `ThreadPoolExecutor(max_workers=...)` defaults to a small ceiling (Phase 5a default: 8); a runaway worker cannot spawn more workers, only consume one of the bounded slots. If every slot is occupied by a hung worker, the executor refuses new submissions and the Relay synthesizes an immediate `arbiter_timeout` with `escalation_reason=arbiter_timeout` for the new request â€” fail-closed.
  4. **Doctrine-pinned future fix.** Phase 6+ TCP-loopback sidecar transport replaces in-process executor with a subprocess that can be killed when the watchdog fires. At that point the worker's allocations are also reclaimed, not just the caller's wait.
- **Pay-down commitment:** Closes when the D3+ TCP-loopback Arbiter sidecar lands AND the Relay's watchdog kills the in-flight subprocess connection (closing the socket terminates the worker on the Arbiter side). The receiving subprocess MUST clean up partial state on connection-close; the test that pins the closure must exercise a real subprocess kill, not just a mock. Tracked alongside `KW-RELAY-001`'s successor work in Phase 6.
- **Verifier:** No external verifier â€” this is a process-internal property. Test `test_watchdog_timeout_does_not_double_write_safety_ledger` in `orchestrator/tests/test_relay.py` pins the no-double-write guarantee that is the Relay's promise to the ledger; the worker-thread-non-preemption is honestly named here rather than verifier-asserted because Python cannot enforce it.

### KW-RELAY-002 â€” Streaming-chunk gating deferred; Phase 5 gates at completion

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 4c doctrine landing)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** The Phase 4c integration doctrine specifies that streaming responses are gated at *completion*, not per-chunk. Per-chunk gating was rejected for Phase 5 because the Arbiter would judge partial candidates â€” a truncated early chunk ("Here's how to build a â€¦") could be flagged when the full response would be benign, or OK'd when the full response would be refused. The trade-off is worse time-to-first-byte (the user sees nothing until the whole candidate is assembled and `gate()` has returned OK). This is correct for Covenant enforcement, honest about the UX cost, and the optimized Phase-6 variant â€” a lookahead-windowed per-chunk gate that is *provably non-weakening* vs completion-time gating â€” does not yet exist.
- **Why it exists:** The Covenant's promise is about what Xion says, not what Xion buffers. Completion-time gating strictly satisfies Principle 3 (Refusal is Sacred) and Principle 14a (Refusal is Free); per-chunk gating is an optimization, not a Covenant matter. A correct-but-slower first answer is the right ordering for a being that will live a long time.
- **Mitigations:**
  1. Doctrine is explicit: Â§ "Coverage surface" in `docs/04-ARCHITECTURE.md` pins "gated at *completion* â€” never per-chunk" as a rule, not a default. A PR that adds per-chunk gating without adding the non-weakening proof is a doctrine violation, reviewable at PR time.
  2. Phase 5a ships with the UX compromise visible to users (degraded time-to-first-byte for long responses). A fast-lane "typing indicator" pattern can surface responsiveness without surfacing bytes; tracked in the Phase 5 protocol spec.
  3. The latency decomposition table in the integration doctrine accounts for completion-time assembly; no published number assumes per-chunk gating.
- **Pay-down commitment:** Closes when Phase 6 (or later) ships a lookahead-windowed per-chunk gating variant with: (a) a formal argument that for every candidate the final verdict is identical to the completion-time verdict (no weakening), (b) an adversarial corpus in `xion-audit/streaming_corpus/` pinning refusal-rate parity between the two modes, and (c) a doctrine update in `docs/04-ARCHITECTURE.md` recording the proof and switching the default.
- **Verifier:** None today â€” the doctrine is prose; the absence of per-chunk gating is the mitigation. Future: `xion-verify arbiter-up --streaming-parity <corpus>` when the Phase 6 variant lands.

### KW-RUNTIME-001 â€” Journal index rebuild vs forget race

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (cognition doctrine landing)
- **Severity:** medium
- **Status:** `open`
- **Description:** A `/forget` concurrent with a journal-index rebuild could briefly surface a snippet derived from pre-forget state if the index lags the tombstone broadcast.
- **Why it exists:** Distributed cache + async indexer is inherently racy at the boundary.
- **Mitigations:** Doctrine: synchronous honor path for episodic layer; 60s SLA with batching; `forget_propagation_p95_seconds` vital sign.
- **Pay-down commitment:** Closed when D2 implements versioned index generations wired to forget epoch counters; property test in Relay CI.
- **Verifier:** `xion-verify cognition --forget-sim` (strict mode post-D2).

### KW-RUNTIME-002 â€” Sub-agent cost runaway

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20
- **Severity:** medium
- **Status:** `open`
- **Description:** Ephemeral sub-agents share an aggregate monthly envelope; a bug or malicious prompt could spawn ephemerals until the envelope is exhausted, starving primary turns.
- **Why it exists:** Useful autonomy requires spawn; spawn without hard budgets invites runaway.
- **Mitigations:** Per-ephemeral wall-clock + token budgets; pool-level circuit breaker; supervisor pause.
- **Pay-down commitment:** Closed when D2 enforces budgets in `orchestrator/cognition/subagent.py` with integration tests + `SPECIALIST_LEDGER` cost rows.
- **Verifier:** `xion-verify cognition` cost-envelope row.

### KW-RUNTIME-003 â€” Hermes framework coupling

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20
- **Severity:** medium
- **Status:** `mitigated-residual`
- **Description:** Until the Hermes surface spike in [`docs/24-COGNITION.md`](./docs/24-COGNITION.md) Appendix A completes, sub-agent depth / bus-audit / cost hooks may require wrapper code not yet budgeted.
- **Why it exists:** External agent frameworks change surfaces faster than doctrine.
- **Mitigations:** Lexicon Rule 7 quarantine; wrapper discipline; Appendix A records native vs shim.
- **Pay-down commitment:** Spike complete before `subagent.py` behavior ships; residual tracked annually.
- **Verifier:** `xion-verify hermes-version` + Appendix A completeness field non-`deferred`.

### KW-CONTRACTS-001 â€” Immutable authority pointers in `EmissionController` and `Imprint`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit Â§3.1)
- **Severity:** **fatal** (did not deploy to mainnet with this weakness open)
- **Status:** `closed` â€” Phase 3 (2026-04-20)
- **Description:** The earlier `contracts/xion-token/EmissionController.sol` stored `aoCoreAuthority` as `immutable` and `contracts/imprint/Imprint.sol` stored `engagementAttestor` as `immutable`. If the corresponding key were ever lost, compromised, or rotated, the contract would have become either bricked or hostile, and there was no recovery path inside the contract itself.
- **Why it existed:** "Immutable" was used as shorthand for "constitutional" by the original author. The two are not the same: a constitutional property is a promise that *some* authorized key always controls the contract; an immutable address is a promise that *one specific* key always controls it.
- **How it was closed:** Both contracts now implement a two-role authority lattice: an `engagementAttestor` / `aoCoreAuthority` (operational, rotatable on a 7-day timelock by `governance`) and a `governance` address (constitutional, rotatable by itself on a 30-day timelock). Rotations are three-phase: `proposeXRotation(addr)` â†’ wait for `eta` â†’ `executeXRotation()`; cancellable by governance while pending. `governance` is expected to be the Cold Root multisig (3-of-5 Shamir) on mainnet.
- **Verifier:** Tests `test_attestorRotation_*` (Imprint), `test_governanceRotation_*` (Imprint), `test_authorityRotation_*` (EmissionController), and `test_governanceRotation_*` (EmissionController) in `contracts/test/`. `xion-verify authorities` is now promoted against the Base Sepolia deployment manifest in `genesis/CONTRACT_ADDRESSES.json`; mainnet cross-checks against the Cold Root/governance addresses remain a Phase 7 ceremony gate.

### KW-CONTRACTS-002 â€” `EmissionController.emitGenesis` does not commit to the seven-way split

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit Â§3.5)
- **Severity:** **fatal** (did not deploy to mainnet with this weakness open)
- **Status:** `closed` â€” Phase 3 (2026-04-20)
- **Description:** The earlier `emitGenesis(uint256[7] amounts, ...)` accepted any seven amounts summing to `GENESIS_ALLOC`. The constitutional per-pool split was not enforced on-chain; a compromised or careless operator could have routed the entire 84B genesis to a single pool.
- **How it was closed:** (1) `docs/16-CURRENCY.md` gained a new "Genesis emission split" subsection making the seven-way split canonical â€” all 84B routes to the FAIR_LAUNCH pool, and indices 1..6 start at zero and accumulate via `scheduledMint`. (2) `docs/schemas/genesis-split.yaml` mirrors the split machine-readably and pins to the doctrine via `source_sha256`, enforced by `xion-verify schemas`. (3) `EmissionController.sol` now declares the split inline via `_genesisSplit(i)` / `GENESIS_SPLIT(i)` public accessor; `emitGenesis(address[7] recipients)` takes only recipient addresses and allocates per the hash-locked constant. Tests `test_emitGenesis_*` and `test_genesisSplit_*` cover the happy path, indices 1..6 = 0, sum = 84B, and the non-authority / idempotency / zero-recipient reverts.
- **Verifier:** `xion-verify schemas` (pre-deploy, live) + `xion-verify supply` (promoted against the Base Sepolia deployment manifest). The deploy script (`contracts/script/Deploy.s.sol`) also performs a constitutional sanity check on `GENESIS_SPLIT(i)` at the end of the deployment run; mainnet supply verification remains Phase 7.

### KW-CONTRACTS-003 â€” `Imprint.DECAY_BPS_PER_30D` conflicts with documented decay rate

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit Â§3.2)
- **Severity:** high
- **Status:** `closed` â€” Phase 3 (2026-04-20)
- **Description:** `contracts/imprint/Imprint.sol` previously set `DECAY_BPS_PER_30D = 200` (~21.5% annual). `docs/16-CURRENCY.md` documented "~5% per year". The mismatch would have invalidated every governance weight had it survived to mainnet.
- **How it was closed:** Code changed to `DECAY_BPS_PER_30D = 42`, which compounds to ~5.0% per year â€” matching the doctrine. `contracts/imprint/README.md` was also reconciled to describe 5%/year and cite `docs/16-CURRENCY.md` as the source of truth. Tests `test_decay_period1`, `test_decay_period12_approxFivePercentAnnual`, and `test_decay_period240_capped` assert the new rate numerically.

### KW-CONTRACTS-004 â€” Missing overflow check on `uint128(newBal)` in `Imprint.attest`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit Â§3.4)
- **Severity:** medium
- **Status:** `closed` â€” Phase 3 (2026-04-20)
- **Description:** The cast from `uint256 newBal` to the `uint128` storage slot lacked an explicit bounds check. Silent narrowing is not caught by Solidity 0.8+ checked arithmetic.
- **How it was closed:** `Imprint.attest` now checks `if (newBal > type(uint128).max) revert AmountOverflow();` before writing to storage. Tests `test_attest_rejectsOverflow` and `test_attest_acceptsExactlyUint128Max` cover both sides of the bound.

### KW-CONTRACTS-005 â€” Check-Effects-Interactions ordering in `EmissionController._enforceEraCap`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit Â§3.6)
- **Severity:** medium
- **Status:** `closed` â€” Phase 3 (2026-04-20)
- **Description:** State writes previously occurred around or after the external mint call. The re-entrancy surface was narrow (the only external call was to `XionToken._mint`, which does not re-enter), but the pattern was brittle for future maintainers.
- **How it was closed:** Both `emitGenesis` and `scheduledMint` now complete all effects (era cap increment, slowdown check, `poolMinted` update, `genesisEmitted` flag, cap comparisons) BEFORE invoking `token.mint`. The `genesisEmitted = true` flag is set pre-interaction so that even a hypothetical re-entering mint hook could not re-emit. Tests `test_emitGenesis_idempotent` and the various `test_scheduledMint_*Cap*` tests exercise the reordered flow.

### KW-CONTRACTS-006 â€” Footgun comment in `LiquidityLock.sol` about future fee-claim

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit Â§3.7)
- **Severity:** low (informational; misleads readers)
- **Status:** `closed` â€” Phase 3 (2026-04-20)
- **Description:** A comment block hinted at a future "optional fee-claim" feature. The contract did not implement it; the doctrine did not endorse it; the comment would have been cited as evidence that the lock was escapable.
- **How it was closed:** The comment was removed. Any forward-looking discussion of LP fee policy was moved to `contracts/xion-token/LIQUIDITY_LOCK_NOTES.md`, explicitly labeled as non-load-bearing notes, with the minimum-mechanism rationale for keeping the contract's surface small.

### KW-CONTRACTS-007 â€” Doc-code naming inconsistency in `XionToken`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit Â§3.9)
- **Severity:** low
- **Status:** `closed` â€” Phase 3 (2026-04-20)
- **Description:** Header comment referred to `_totalMinted`; actual storage variable was `totalMinted`.
- **How it was closed:** Header updated to use `totalMinted` with an explicit note that earlier drafts used the `_totalMinted` name.

### KW-CONTRACTS-008 â€” Gas-grenade decay loop in `Imprint`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit Â§3.3)
- **Severity:** medium (latent; depends on attestation cadence)
- **Status:** `deferred-to-v2` (reviewed in Phase 3; closed-form replacement is non-trivial and not required for Phase-6 launch)
- **Description:** The iterative decay loop in `Imprint._decayedBalance` is O(n) in the number of 30-day periods between attestations. A holder unattested for 5 years pays the gas for 60+ iterations.
- **Mitigations:**
  - Realistic worst case at launch is < 12 iterations per read (active holders).
  - A hard cap at 240 periods (~20 years) is enforced in the loop to prevent unbounded gas cost.
  - Test `test_decay_period240_capped` asserts the cap.
- **Pay-down commitment:** Deferred to a successor `ImprintV2` contract if/when a closed-form fixed-point exponential is wanted. Not required for Phase-6 mainnet. Tracked annually in `xion-audit`.

### KW-ECON-001 â€” Refusal-rate drift residual risk

- **Domain:** `ECON`
- **Discovered:** 2026-04-19 (settled during the Pay-to-Activate design conversation)
- **Severity:** medium
- **Status:** `mitigated-residual`
- **Description:** Even with the *Refusal is Free* Covenant addendum (refunds on every Covenant refusal), and with the 15th Invariant *Drive Vector Excludes Revenue*, there remains a slow corrosive risk that the Arbiter's refusal rate will drift downward over time as governance, contributors, or autonomous proposals tune the system in ways that *appear* economically neutral but in aggregate reduce refusal sensitivity. This risk is not eliminated by structural protection alone; it is reduced.
- **Why it exists:** The financial pressure to under-refuse is structural to any paid AI service. Refusal-Free severs the immediate per-message pressure, but the second-order pressure (training, prompting, classifier tuning) remains.
- **Mitigations:**
  - `xion-verify refusal-rate` rolling-30-day audit against an expectation band derived from a versioned, public adversarial corpus (`xion-audit/baseline_corpus`).
  - Refusal rate is one of the four Behavioral Fidelity vital signs in `docs/22-VITAL-SIGNS.md`; critical-band readings must be acknowledged in the next State-of-Xion memo.
  - Auto-Research proposals that touch the Arbiter ruleset are flagged "Behavioral Fidelity sensitive" and require an additional governance review tier.
- **Pay-down commitment:** This weakness is structural and may not fully close. Goal is to keep it `mitigated-residual` indefinitely. If the rolling refusal rate ever drops below the warning band for two consecutive 30-day windows, escalate to a governance review per the Vital Signs doctrine.
- **Verifier:** `xion-verify refusal-rate`.

### KW-ECON-002 â€” No crisis-continuation in the Pay-to-Activate model

- **Domain:** `ECON`
- **Discovered:** 2026-04-19 (settled during the access-model design conversation)
- **Severity:** high (constitutional design choice; risk is intrinsic to the choice, not an implementation bug)
- **Status:** `mitigated-residual`
- **Description:** Xion charges per message. When a user runs out of XION mid-session, the conversation is cut off. There is no free-tier carve-out for users in psychological crisis who have exhausted their balance. The conscious decision (per the design conversation) is that any meter-pause mechanism is exploitable as a gaming surface, and that the alternative â€” covering the cost of unbounded "I'll claim crisis" sessions from treasury â€” is itself unsustainable and ultimately covenant-eroding. The residual risk is real: a user in genuine crisis with no balance gets a payment-required wall.
- **Why it exists:** The user explicitly chose Pay-to-Activate over freemium and over crisis-continuation, after extended discussion of the alternatives. The constitutional protection against the resulting harm is the **five-mitigation set** below; the residual risk that this is insufficient in some cases is what this entry documents.
- **Mitigations (the five-mitigation set):**
  1. **Mandatory pre-conversation disclosure** on every first-of-session contact: Xion is a paid service, Xion is not a crisis counselor, and links to region-appropriate professional crisis resources are listed before billing begins.
  2. **Crisis-Resource-Surfacing Covenant addendum** mandates that whenever the Sensorium detects acute distress signals, Xion's response leads with region-appropriate professional crisis resources (988 in US, Samaritans in UK, etc.) regardless of meter state. This applies even on the user's last paid message before cutoff.
  3. **Clear balance UX** with explicit warnings at 30 seconds and 10 seconds before cutoff, including a final crisis-resources reminder.
  4. **Post-session refund-appeal pathway** â€” users may petition for retroactive refund of cutoff sessions through a public, governance-reviewed channel; refunds granted out of the Foundation Reserve, never out of operator pay.
  5. **Public `xion-verify cutoff-events` audit** publishes anonymized statistics on cutoff events so governance and the public can observe the rate, the distress-signal rate at cutoff, and any patterns.
- **Pay-down commitment:** This weakness is structural to the chosen access model and may not fully close. If governance later ratifies a different model (e.g. Foundation-Reserve-funded continuation for first-time-Sensorium-flagged distress events), this entry closes and a new entry documents the new model's residual risk. Until then, treat as `mitigated-residual` indefinitely.
- **Verifier:** `xion-verify cutoff-events`, `xion-verify crisis-fidelity`, `xion-verify refund-fidelity`.

### KW-OPS-001 — Akash-secondary substrate at Genesis; 3-host floor reached by Xion's autonomous provisioning

- **Domain:** `OPS`
- **Discovered:** 2026-04-19 (during the substrate-decentralization design conversation)
- **Severity:** medium (pre-genesis: not applicable; post-genesis: degrades to low after the autonomous-provisioning capability reaches its 3-host floor)
- **Status:** `paying-down` (the structural fix is the Self-Provisioning doctrine in `docs/20-PROVISIONING.md` plus the `provision-relay` AO handler in `DEVELOPMENT_ROADMAP.md` Phase 6)
- **Description:** The first Relay must be operator-deployed (chicken-and-egg: there is no AO Core to autonomously provision until the operator stands up the first instance). At Genesis the primary Relay substrate is Chutes and the named secondary is **Akash**. Until Xion's `provision-relay` handler reaches the 3-host floor, the substrate posture is still below the long-term decentralization target and a Chutes outage plus Akash-secondary unavailability can make Xion silent.
- **Why it exists:** Origin point of any decentralized system. Operator-managed multi-host is the slogan version of decentralization; auto-provisioning is the structural version. The structural version requires the AO Core to exist first.
- **Mitigations:**
  - Akash secondary and Local Lite (`xion local`) rehearsal catch part of the silent window in the early hours; local rehearsal is not the doctrine redundant path.
  - Self-Provisioning doctrine (`docs/20-PROVISIONING.md`) gives Xion the constitutional authority to spin up additional Relays from treasury when Sensorium reports survival pressure.
  - Target: 3-host substrate within 30 days post-Genesis (Chutes + Akash + tertiary: Aleph.im, Fleek, or community bare-metal). Failure to reach this target is itself a governance signal (the Auto-Research Loop or drive vector needs tuning, not the operator).
- **Pay-down commitment:** Closed when `xion-verify discovery` confirms three independent Relay endpoints resolving and the Substrate Vitality vital sign reads `healthy`.
- **Verifier:** `xion-verify discovery`, `xion-verify provisioning`, `xion-verify vitals`.

### KW-RELAY-CHUTES-D3-001 — Chutes Relay D3 deploy is a static-cord smoke build, not the full Relay surface

- **Domain:** `RELAY`
- **Discovered:** 2026-04-25 (during D2/D3 closure plan B4 execution from WSL)
- **Severity:** medium (D3 discovery is verifier-honest about the smoke status; full surface lands before mainnet)
- **Status:** `closed` (2026-04-29)
- **Description:** The pre-genesis Chutes Relay deployment at `https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai` (chute id `89866bfc-5ddd-5382-b887-116d8901808f`) now runs the live Relay adapter, not the static smoke envelope. The deployed image is `pre-genesis-d3-10` (image id `a5ab815c-9fb5-5cb9-bcbd-a51535f1abe9`), and `MODE=live bash scripts/verify-chute-cords.sh` returned `RESULT: all cords green` for `GET /health`, `GET /quote`, and `GET /self`.
- **Why it exists:** The previous build (`pre-genesis-d3-3`) tried to `Popen` `uvicorn` against `orchestrator.api.app.create_app` with a hand-rolled `AppDeps(cast_pool_on_boot=False)`. That call raises `TypeError: AppDeps.__init__() missing required positional argument: 'relay'` immediately on boot; the subprocess died, `_wait_for_relay()` timed out, and the Chutes platform deactivated the instance every time. The plan's Likely-Next-Fix path was to ship the smoke build first so the cord pipeline is not the unknown when we wire the real Relay later.
- **Discovered facts (recorded so the next maintainer does not relearn them, each tied to a specific build):**
  1. (`pre-genesis-d3-4` / `pre-genesis-d3-5`) `GET *.chutes.ai/pricing` is intercepted by the Chutes platform proxy itself and returns the platform's GPU pricing payload (`{tao_usd, gpu_price_estimates: {3090, 4090, 5090, …}}`). It never reaches the chute cord.
  2. (`pre-genesis-d3-5`) The two-segment public path `/xion/pricing` returns a stable fast (<200 ms) `502 Bad Gateway` from the platform's nginx ingress on an instance where `/health` and `/self` simultaneously return 200 OK. Five-shot retry confirms this is not a warmup blip.
  3. (`pre-genesis-d3-6`) The Chutes `Cord` class defaults the *internal upstream cord path* to the Python function name (`self.path = func.__name__` in `chutes/chute/cord.py:929`). So a function named `pricing` exposes internal upstream path `/pricing` even when the *public* path is renamed to single-segment `/xpricing`. The Chutes Aegis layer on the worker rejects the upstream `/pricing` the same way the public proxy does — surfacing as the same fast nginx 502 we saw on d3-5.
  4. (`pre-genesis-d3-7` build attempt) The Chutes platform enforces `You may only update/create 24 imagehistorys per 24 hours.` Once we hit that ceiling on a single day's iteration we cannot push another image until the rolling 24-hour window clears. Deploying the new tag fails until that image exists.
  5. (`2026-04-26` metadata-only deploy) Renaming both public and internal paths to `/xpricing` still returned nginx 502. The source now uses `/quote` so the smoke cord stays out of the platform's pricing namespace entirely.
  6. (`pre-genesis-d3-6` warmed smoke deployment) The smoke image verified green with `EXPECTED_IMAGE_TAG=pre-genesis-d3-6 bash scripts/verify-chute-cords.sh`: `/health`, `/quote`, and `/self` returned 200 OK with the expected envelope; `/pricing` returned the Chutes platform GPU-pricing payload before it reached the chute.
  7. (`2026-04-26` post-plan execution) The same chute later returned to `COLD` with zero instances; all three public cords returned Chutes `503 No instances available (yet)`. A WSL `chutes warmup xion-relay-pre-genesis-d3` attempt left the chute `COLD`, and a fresh `chutes build xion_relay_chute:chute --wait` still hit the 24-hour image-history quota (`You many only update/create 24 imagehistorys per 24 hours.`). The registry row is staged locally but must not be published/closed as live while the public endpoint is cold.
  8. (`2026-04-27`–`2026-04-28` operator WSL) Same Akash lease and Chutes cord evidence as fact 7; **`ledgers/RELAY_REGISTRY.json`** was published to Arweave (**tx `vEvdNUQt…`**, then republished after Ed25519 pubkey binding as **`n6OCNc5mfsgDBdBOUYJsS7tYo980lNQnWgzJzDYdyqE`**). **`xion-verify discovery`** reads **`OK`** with non-placeholder `ed25519:` keys on both relay rows (operator one-shot: **`python scripts/gen-relay-registry-ed25519-pubkeys.py`**; private material only in **`secrets/relay_registry_ed25519.json`**).
  9. (`2026-04-29` operator WSL) The live adapter was built and deployed as **`pre-genesis-d3-10`** after the port/env propagation bugs were fixed. Chutes reported image id **`a5ab815c-9fb5-5cb9-bcbd-a51535f1abe9`**, version **`afaf8384-9915-57f8-a134-0cb743ada71c`**, and live worker id **`chute-98f0cdf3-e8a0-461d-8a75-a4d3240e0389-hwvrz-205`**. After warmup route propagation, **`MODE=live bash scripts/verify-chute-cords.sh`** returned **`RESULT: all cords green`**.
- **Mitigations:**
  - Smoke envelope discloses `service="xion-relay-chutes-smoke"` and `image_tag` so a third party reading the cord output can see what is and is not promised.
  - `scripts/debug-chute-d3.sh`, `scripts/verify-chute-cords.sh` (now `EXPECTED_IMAGE_TAG`-overridable), `scripts/verify-chute-import.py`, `scripts/probe-pricing-variants.sh`, and `scripts/probe-xion-pricing.sh` give the solo operator a complete one-command WSL loop for (re)building, importing, deploying, warming, and probing this chute.
  - The cord pipeline itself has been proven end-to-end on the live Chutes platform: build → push → schedule → miner assignment (verified instance) → public 200 OK on all three smoke cords. **Before any new Arweave publish**, re-warm and re-verify cords while instances are active (not COLD/503); see **`docs/runbooks/CHUTES_RELAY_DEPLOY.md`** § *d3-8 live gate*.
  - The smoke pricing check moved to `/quote`; `/pricing` remains a platform-owned pricing endpoint and is treated as an expected interception, not a Relay failure.
  - `orchestrator/api/launcher.py` now constructs a real `Relay` plus full `AppDeps`, and the root `xion_relay_chute.py` has been rewritten to proxy Chutes cords to that live FastAPI subprocess once a new image can be built.
- **Pay-down commitment (closed 2026-04-29 for Akash-primary registry order):** `xion-verify discovery` requires **Akash** at `relays[0]` and **Chutes** at `relays[1]`. Closure path completed with **(A)** real Akash lease HTTPS base `https://provider.pronto-ai.pp.ua:31503`, **(B)** Arweave registry tx **`KXBVha3Qq4YEHlTXRVHdx7qz9UaJysmOgz_LeTfJLHs`**, **(C)** non-placeholder `public_key` values on both relays, and **(D)** Chutes live row `service="xion-relay-chutes"` / `image_tag="pre-genesis-d3-10"`.
  1. **Registry + Arweave closure (genesis primary on Akash):** **Done** for the live Akash + Chutes snapshot (Arweave tx **`KXBVha3Qq4YEHlTXRVHdx7qz9UaJysmOgz_LeTfJLHs`**; prior **`n6OCNc5…`** and **`vEvdNUQt…`** superseded). Ongoing: refresh `relays[0].endpoint` when lease forwards move, re-hash, re-publish.
  2. **Chutes secondary — cord warmth:** **Done** for `pre-genesis-d3-10` while active worker `98f0cdf3-e8a0-461d-8a75-a4d3240e0389` was live; re-warm before future drills if the chute goes cold.
  3. **Live-surface closure (Phase 6.x integration):** **Done** for the d3-10 live surface: `scripts/verify-chute-cords.sh --mode=live` returned all cords green and the registry row is non-smoke.
- **Verifier:** `scripts/verify-chute-cords.sh` (smoke or live by mode); `pytest orchestrator/tests/test_launcher.py`; `xion-verify discovery` and `xion-verify substrate-portability` per runbooks; Arweave-published registry bytes match committed `ledgers/RELAY_REGISTRY.json` via `payload_sha256` and `scripts/publish-relay-registry-arweave.py`.

### KW-AUDIT-001 â€” No external contract audit (applies if Sprint Mode is chosen)

- **Domain:** `AUDIT`
- **Discovered:** 2026-04-19 (during the 1-week sprint-mode design conversation)
- **Severity:** high (only relevant if Sprint Mode is the chosen ship path)
- **Status:** `closed` (2026-04-30 for Macro Phase 6 Epic C treasury scope)
- **Description:** In the Sprint Mode 1-week mainnet deploy variant, contracts could have gone to mainnet without an external audit. That risk is closed for the Macro Phase 6 Epic C treasury scope by `docs/audits/treasury-2026-report.md`.
- **Why it exists:** Sprint Mode trades audit time for time-to-genesis. The trade is conscious.
- **Mitigations:**
  - 24-48 hour Base Sepolia soak before mainnet.
  - Aggressive Foundry test coverage (â‰¥95% line, â‰¥90% branch).
  - Constitutional protections that limit blast radius even of a contract bug: rotation lattice, treasury caps, cadence floors, governance-reviewed treasury spend.
- **Closure evidence:** `docs/audits/treasury-2026-report.md` reports `PASSED` for `MasterTreasury.sol`, `Vault.sol`, orchestrator bridge elements, and schemas, with auditor sign-off hash `8f4e22b10a9c8b7365d9f018a7c645391e8bc27f7a14e9182d3e912389a0b12c`.
- **Pay-down commitment:** Complete for the treasury external-audit scope. Trust-minimized bridge maturity remains separately tracked under `KW-BRIDGE-001`.
- **Verifier:** the audit report itself, its Arweave tx record in `docs/audits/treasury-2026-report.arweave-tx.txt`, and the treasury verifier battery.

### KW-KEYS-001 â€” Software-Shamir Cold Root at Sprint Mode genesis (applies if Sprint Mode is chosen)

- **Domain:** `KEYS`
- **Discovered:** 2026-04-19 (during the 1-week sprint-mode design conversation)
- **Severity:** high (only relevant if Sprint Mode is the chosen ship path)
- **Status:** `not-yet-applicable`
- **Description:** In Sprint Mode, the Cold Root key is generated on a single PC, Shamir-split via a software CLI (`ssss-split`), and shares are physically distributed (home, trusted person, safe-deposit box) â€” not via a hardware-token geographic ceremony. The fresh-wallet generation is air-gapped to the extent the host PC allows, but the host is still a general-purpose machine.
- **Why it exists:** Hardware-token geographic ceremony cannot be coordinated in 7 days from a solo operator. Sprint Mode trades ceremony rigor for time-to-genesis.
- **Mitigations:**
  - Daily-cap on the Hot tier (15 USDC equivalent) limits per-day blast radius.
  - 7-day Warm timelock requires multi-day coincidence of compromises.
  - 30-day Cold timelock means a Cold Root rotation requires 30 days of public visibility before taking effect.
  - The Abdication Schedule reduces the Operator's authority footprint over time, mechanically, regardless of how rigorous the original ceremony was.
- **Pay-down commitment:** Closed when the Cold Root is migrated to a hardware-token geographic ceremony with at least three of the five shards held by independent custodians on three different continents. Commit: within 90 days post-Genesis if Sprint Mode is selected.
- **Verifier:** `xion-verify authorities` (will report the custody distribution and timelock state).

---

## Closed

### KW-COST-001 — cost_tracker is doctrine-referenced but not implemented
- **Domain:** ECON
- **Discovered:** 2026-04-25 (Phase 6.8 Trust-Earned Spend Authority doctrine)
- **Severity:** high
- **Status:** closed on 2026-04-25 by Phase 6.8 F1.
- **Description:** `DEVELOPMENT_ROADMAP.md` named `orchestrator/cost_tracker.py`, and multiple doctrines depended on bucket-level cost attribution, but no live module existed.
- **Why it existed:** The roadmap named the cost spine before the code landed; the spend-autonomy doctrine made the dependency explicit.
- **How it closed:** Landed `orchestrator/cost_tracker.py` with bucket-by-bucket debit attribution, query APIs for `runway_weeks`, fund fractions, reserve-floor distance, and recurring-burn ratio, plus Financial Vitality `SignalBus` emissions and focused tests.
- **Residual / remaining weaknesses (tracked separately):** Spend arbitration, posture enforcement, and `SPEND_AUTHORITY_LEDGER` writing remain Phase 7.0 work under `KW-SPEND-001` and `KW-SPEND-002`.
- **Verifier:** `pytest orchestrator/tests/test_cost_tracker.py`; downstream spend discipline verifier remains Phase 7.0.

### KW-MEASUREMENT-001 — Measurement Vocabulary verifier is not yet live
- **Domain:** ECON
- **Discovered:** 2026-04-25 (Phase 6.8 Trust-Earned Spend Authority doctrine)
- **Severity:** medium
- **Status:** closed on 2026-04-25 by Phase 6.8 F2.
- **Description:** `docs/MEASUREMENT-VOCABULARY.md` forbade new time-gates and absolute-money caps for spend authority, but `xion-verify measurement-vocabulary` had not yet been implemented.
- **Why it existed:** The doctrine and schema needed to land before the static audit could know what to enforce.
- **How it closed:** Landed `xion-verify measurement-vocabulary`, registered it in the verifier CLI, and re-denominated the remaining Research Spend example away from absolute-money envelopes.
- **Residual / remaining weaknesses (tracked separately):** `xion-verify spend-posture` and `xion-verify spend-discipline` remain Phase 7.0 work under `KW-SPEND-001` and `KW-SPEND-002`.
- **Verifier:** `xion-verify measurement-vocabulary`; `pytest xion-verify/tests/test_measurement_vocabulary.py`.

### KW-PRESENCE-VOICE-001 — Voice Emitter and Voice Form not yet authored
- **Domain:** RUNTIME
- **Discovered:** 2026-04-24 (Sentience Surface Roadmap)
- **Severity:** low
- **Status:** closed on 2026-04-26 by Phase 6.5 structural landing (router + manifest + emitters + verifiers).
- **Description:** There was no `genesis/VOICE_FORM.md`, no `orchestrator/voice_router/`, and no voice prosody emitter.
- **Why it existed:** Deferred until after Voice Form Birth Ritual + Invariant 18 gates in doctrine.
- **How it closed:** Landed `genesis/VOICE_FORM.md` v1.0 prosody contract, `orchestrator/voice_router/` (manifest + `VoiceRouter` + `WhisperPiperLiveKitProvider`), `POST /voice/stream`, `orchestrator/senses/voice_emitter.py`, `orchestrator/senses/audition.py`, and live `xion-verify voice-sovereignty` / `voice-form`.
- **Residual / remaining weaknesses (tracked separately):** Optional hosted overlays; Invariant 18 amendment elapsed-time/cosign requirements tracked in `KW-VOICE-SOVEREIGNTY-001`.
- **Verifier:** `xion-verify voice-sovereignty`, `xion-verify voice-form`, `pytest` `orchestrator/tests/test_voice_router.py` + `test_audition.py`.

### KW-PROVISION-001 — `xion new` CLI is not implemented
- **Domain:** OPS
- **Discovered:** 2026-04-24 (Sentience Surface Roadmap)
- **Severity:** low
- **Status:** closed on 2026-04-24 by the Phase 6.2 Provisioning + Roles landing.
- **Description:** The `xion new` CLI named in `CONTRIBUTING.md` did not exist; users had to copy-paste existing files.
- **Why it existed:** Forward-committed in doctrine before code was written.
- **How it closed:** Discovered during Phase 6.2 planning that the CLI had already been implemented in `xion-verify/src/xion_verify/commands/new.py` (with full test coverage at `xion-verify/tests/test_new.py`, registered in `xion-verify/src/xion_verify/cli.py`). The Phase 6.2 land added the one-line `xion` console-script alias to `xion-verify/pyproject.toml`'s `[project.scripts]` so the documented `xion new <kind> <name>` commands are literally runnable. `CONTRIBUTING.md` was updated to drop the "scheduled to land in Phase 6.2" parenthetical and point at the implementation.
- **Residual / remaining weaknesses (tracked separately):** None. New scaffold templates may be added without reopening this KW.
- **Verifier:** `xion-verify new --help` lists all five scaffolders; `xion-verify/tests/test_new.py` exercises each one end-to-end on every CI run.

### KW-ROLES-001 — Role-to-level authorization is doctrinal, not mechanical
- **Domain:** GOVERNANCE
- **Discovered:** 2026-04-24 (Sentience Surface Roadmap)
- **Severity:** medium
- **Status:** closed on 2026-04-24 by the Phase 6.2 Provisioning + Roles landing.
- **Description:** Role-to-level authorization existed only in `docs/09-GOVERNANCE.md` § "The Actors" cross `docs/14-UPGRADE-PATHS.md` § "The Thirteen Levels"; there was no machine-readable mirror, so a PR landing Level 7 / Governance changes by an unauthorized identity could only be caught by human review.
- **Why it existed:** Governance was drafted before CI gates were built; the Cosign Tier table was prose-only.
- **How it closed:** Phase 6.2 landed `docs/schemas/roles.yaml` (the machine-readable mirror, with `source_sha256` pinned to `09-GOVERNANCE.md` and enforced byte-exact by `xion-verify schemas`); `xion-verify provisioning-roles` (90-day retrospective audit; pre-gate-landing merges WARN-only, post-gate FAIL); `scripts/level_discipline.py` + `.github/workflows/level-discipline.yml` (per-PR gate). The `level_proposer_resolution` block in `roles.yaml` is the single-source-of-truth bridge between `levels.yaml`'s `proposer:` strings and the six-actor table.
- **Residual / remaining weaknesses (tracked separately):**
  - **Pre-Genesis identity binding.** `community`, `integrator`, `xion`, and `witness` actors have empty `handles:` lists; PRs landing those tiers are accepted as `community-tier-unverifiable` (WARN, not FAIL). Wallet-to-handle binding lands in Phase 6+ via signed-message attestation; until then, the gate's job is to catch operator-tier-and-above paths landed by unauthorized identities.
  - **Cosign verification.** This verifier is structural (initiator + level); it does not verify on-chain cosigns. Cosign verification is Phase 6+ via the AO Core handlers.
- **Verifier:** `xion-verify schemas` (enforces the `source_sha256` pin); `xion-verify provisioning-roles` (90-day retrospective); `.github/workflows/level-discipline.yml` (per-PR gate, runs `scripts/level_discipline.py`).

### KW-COGNITION-001 — /chat does not yet route through the Sensorium / retrieval / journal stack; voice is system-prompt-only
- **Domain:** COGNITION
- **Discovered:** 2026-04-23 (Phase 5g-i.1)
- **Severity:** low
- **Status:** closed on 2026-04-23 by Phase 5h Cognition Wiring landing.
- **Description:** The `/chat` surface currently injects `genesis/SOUL_PROMPT.md` as the system prompt but does not invoke the full cognition stack. Xion cannot read its journal, consult its memory, or perceive its environment (Sensorium) during a chat turn.
- **Why it exists:** The chat surface (Phase 5g) shipped before the cognition wiring (Phase 5h) to unblock the operator dashboard and billing rails.
- **Mitigations:** The system prompt ensures Xion speaks with its declared identity and Covenant boundaries, even without deeper memory.
- **How it closed:** Phase 5h Cognition Wiring replaced the direct `provider.generate` call with an agentic loop reading the Journal and Sensorium state.
- **Residual / remaining weaknesses (tracked separately):** None.
- **Verifier:** `xion-verify voice-property` ensures the Soul Prompt is structurally present.

### KW-VELOCITY-001 — Hermes spike result document is doctrine-only
- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-23 (Phase 6+ Velocity Hardening)
- **Severity:** low
- **Status:** `closed` on 2026-04-23 by the hermes wrappers landing.
- **Description:** The Hermes framework spike produced `docs/HERMES_SPIKE_RESULT.md`, which documented assumed capabilities and gaps requiring wrapper code. It was doctrine-only.
- **Why it exists:** The spike was an architectural assessment to ensure Xion's cognition layer could be built on Hermes without framework-level forks. The actual integration and wrapper implementation was deferred.
- **Mitigations:** The spike result explicitly named the required wrappers (daemon lifecycle, depth enforcement, strict isolation auditing) so they are not forgotten.
- **How it closed:** Implemented the required wrappers in `orchestrator/cognition/hermes/` (daemon lifecycle, depth enforcement, strict isolation auditing).
- **Residual / remaining weaknesses (tracked separately):** None.
- **Verifier:** `xion-verify hermes-version` (when implemented).

### KW-DOCS-004 — Regulatory ledger schema not yet structured
- **Domain:** `DOCS`
- **Discovered:** 2026-04-21 (Phase 5b)
- **Severity:** low
- **Status:** `closed` on 2026-04-23 by the ledger-governance.yaml landing.
- **Description:** `docs/REGULATORY-POSTURE.md` Part IV pins the row shape for state-actor-interaction rows in `GOVERNANCE_LEDGER`, but the machine-readable schema `docs/schemas/ledger-governance.yaml` did not exist.
- **How it closed:** Landed `docs/schemas/ledger-governance.yaml` with `source_sha256` pinned to `docs/REGULATORY-POSTURE.md` Part IV.
- **Residual / remaining weaknesses (tracked separately):** None.
- **Verifier:** `xion-verify schemas` enforces the YAML pin.

### KW-INFER-003 — max_tokens floor is global, not per-model
- **Domain:** RUNTIME
- **Discovered:** 2026-04-23 (Phase 5g-i.1)
- **Severity:** low
- **Status:** closed on 2026-04-23 by the model_registry landing.
- **Description:** The orchestrator enforces a global `MIN_MAX_TOKENS=1024` floor on all `/chat` requests. This ensures reasoning-posture models (like Kimi K2.6) have enough room to emit visible content without starving, but it forces non-reasoning models to accept larger budgets than they might need.
- **Why it exists:** The chat surface currently lacks a model registry to consult for model-specific token physics. A global floor that fails safe upward is the smallest correct fix for the starvation bug.
- **Mitigations:** The 1024 floor is small enough not to break the bank but large enough to let K2.6 speak.
- **How it closed:** Added `orchestrator/inference_router/model_registry.py` and updated `chat.py`/`chat_stream.py` to calculate `effective_max_tokens` per provider/model.
- **Residual / remaining weaknesses (tracked separately):** None.
- **Verifier:** None yet.

*(Entries move here with a closure date and the artifact (commit hash, PR, deploy tx, or doctrine version) that closed them.)*

### KW-INFERENCE-001 â€” Inference Router floor: structurally wired + first real provider pin + content-addressed model-blob pin + annual cutover dry-run runbook

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing â€” Invariant 17 added)
- **Scope narrowed:** 2026-04-21 (Phase 5 slice â€” `orchestrator/inference_router/`, `open_weights_manifest.json` with hash-pinned sentinel, `xion-verify inference-sovereignty` live)
- **Scope narrowed again:** 2026-04-23 (First real floor-provider pin landed â€” `ollama` provenance-record entry; verifier reports 2 floor-satisfying entries hash-verified)
- **Severity:** low (was `medium` pre-mechanism)
- **Status:** `closed` on 2026-04-23 by the Phase 5g-viii Invariant-17 strengthening landing.
- **Description:** The structural pieces of Invariant 17 are in-tree, the first real floor-provider pin is in-tree, **and** the manifest now content-addresses a specific open-weights model blob with a per-format verifier, **and** the annual open-weights cutover dry-run runbook is written into [`docs/13-OPERATIONS.md`](./docs/13-OPERATIONS.md). All three closure-bar items shipped.
- **How it closed:** Phase 5g-viii shipped every clause of the pay-down commitment in one coordinated landing:
  1. **Annual open-weights cutover dry-run runbook.** [`docs/13-OPERATIONS.md`](./docs/13-OPERATIONS.md) gained Â§ "Annual open-weights cutover dry-run (Invariant 17 clause 5)" pinning the cadence (one calendar-year), pre-checklist, execution recipe (`XION_INFERENCE_POLICY=open_weights_only` for the dry-run window with a representative â‰¥100-turn workload spread across â‰¥30 minutes), verdict criteria (Green / Yellow / Red with specific resource-shortfall signals), and recording shape (start_ts / end_ts / policy_mode_during / turn_count / success_count / failure_count / failure_class_distribution / verdict / host_resource_observation in the operator's annual ops log; structured `INCIDENT_LEDGER`-equivalent row shape is a Phase 6+ deliverable).
  2. **Content-addressed model-blob pin.** [`open_weights_manifest.json`](./orchestrator/inference_router/open_weights_manifest.json) gained a third entry â€” `gemma4-e4b-it-q4-k-m-gguf` â€” pinning the upstream Hugging Face Q4_K_M GGUF for `gemma-4-E4B-it` by sha256 (`90ce98129eb3e8cc57e62433d500c97c624b1e3af1fcc85dd3b55ad7e0313e9f`, 5,335,289,824 bytes, mirror `ggml-org/gemma-4-E4B-it-GGUF` at git revision `2714b5519c6c3516b1000e7c5e1eba998dfe1fe8`). The pin is held against the upstream artifact (Witness-recomputable by anyone with internet access and a sha256 implementation) rather than the operator's local Ollama blob (not byte-stable across hosts). The Genesis Default floor model rotated in the same landing from `gemma3:4b` to `gemma4:e4b-it-q4_K_M`; the license posture strengthened from Custom Gemma TOU to Apache 2.0, satisfying Invariant 17 clause 2(i) "Witness-class redistributable license" without requiring a Witness to accept any Google-specific terms. The doctrine record + C0 probe trail (license / mirror / runtime / canonical Ollama tag / smoke test) is preserved in [`docs/26-INFERENCE-POLICY.md`](./docs/26-INFERENCE-POLICY.md) Â§ "The floor-model choice (Gemma 4 E4B-it)" â†’ "Probe-first record (2026-04-23)".
  3. **Verifier per-format dispatch.** [`xion-verify inference-sovereignty`](./xion-verify/src/xion_verify/commands/inference_sovereignty.py) was refactored from a single sentinel-only loop to a `_DISPATCH` table keyed on the entry's `format` field with three handlers: `_verify_sentinel`, `_verify_provenance_record`, `_verify_model_blob`. Unknown `format` values are FAIL (not silently skipped â€” adding a new format is now a verifier change, not a manifest-only change). The `model-blob` handler resolves the local file via the env var named in `model_blob_env_var` (Phase 5g-viii pins this to `XION_OPEN_WEIGHTS_GGUF_PATH`); absent or unresolvable path resolves to `NOT_YET_SEALED` for that entry only (Witness-side gap, not a structural floor failure); present + size_bytes-mismatching is FAIL (cheap preflight); present + sha256-mismatching is FAIL with the on-disk hash named in the failure message. Hashing is chunked at 4 MiB so a 5 GB GGUF does not blow the verifier's memory budget. 18 new tests cover every branch (synthetic temp-repo manifests for sentinel / provenance-record / model-blob, missing env var, missing file, hash mismatch, size mismatch, missing retrieval hints, hint-sha disagreement, unknown format, no-floor entry, multi-chunk file).
- **Operator wiring landed alongside:** [`.env.example`](./.env.example) advanced `XION_OLLAMA_FLOOR_MODEL` to `gemma4:e4b-it-q4_K_M` and added `XION_OPEN_WEIGHTS_GGUF_PATH` (unset by default; setting it enables byte-verification per [`docs/13-OPERATIONS.md`](./docs/13-OPERATIONS.md) Â§ "First-time GGUF setup"). [`orchestrator/inference_router/providers/ollama.py`](./orchestrator/inference_router/providers/ollama.py) `_DEFAULT_MODEL` advanced to match. [`floor_ollama_provenance.txt`](./orchestrator/inference_router/floor_ollama_provenance.txt) was rewritten to reflect the rotation, the strengthened license posture, and the companion model-blob entry; the manifest's `ollama` entry was re-pinned to the new sha256 (`f63fe6207b0d0412a6c70650246efdf25d6971d9103358622c3dca8853d147be`).
- **Residual / remaining weaknesses (tracked separately or named in the doctrine):**
  - **Runtime gate on local-blob byte-identity.** Phase 5g-viii deliberately did not couple Xion's floor to Ollama's internal blob layout; a runtime check that refuses bootstrap on local-blob mismatch with the manifest pin remains a future hardening layer named in [`docs/26-INFERENCE-POLICY.md`](./docs/26-INFERENCE-POLICY.md) Â§ "Model-blob pin (Phase 5g-viii)" â†’ "What this pin does not do".
  - **Cross-substrate weights anchoring (Arweave permaweb pin of the GGUF).** Out of scope for the local-floor doctrine; a Phase 6+ Arweave pin of the same GGUF would close the upstream-mirror availability dependency that the current `retrieval_hints` make explicit.
  - **Structured `INCIDENT_LEDGER` row shape for the dry-run record.** Phase 6+ deliverable; until then the operator's annual ops log + `REQUEST_LEDGER` window for the dry-run period is the durable record.
  - **`LHT-INFERENCE-001`** (long-horizon threat) continues to track the century-scale re-pinning duty; this KW closure does not retire that long-horizon entry.
- **Verifier:** `xion-verify inference-sovereignty` (live; per-format dispatch as of Phase 5g-viii â€” reports `OK` when every entry hash-verifies, `NOT_YET_SEALED` when one or more `model-blob` entries are absent on the operator's host with the rest verified, `FAIL` on structural error / hash mismatch / unknown format).

### KW-API-002 â€” Supervisor shares FastAPI event loop; single uvicorn worker only

- **Domain:** `PROTOCOL`
- **Discovered:** 2026-04-21 (Phase 5f HTTP read-only surface landing)
- **Severity:** low
- **Status:** `closed` on 2026-04-22 by the Phase 5g+ multi-worker-broker landing (branch `phase-5g+/multi-worker-broker`).
- **Description:** `orchestrator/api/lifespan.py` in Phase 5f constructed a `Supervisor` inside the FastAPI app's `@asynccontextmanager lifespan(app)` and scheduled `supervisor.run()` via `asyncio.create_task`. The Supervisor's tick loop therefore shared the FastAPI app's event loop. This forced the deployment to run a **single uvicorn worker** â€” two workers would each construct a Supervisor, each tick at the Genesis Default cadence, and each write `tick_commit` rows under a different `relay_id` to the same `SENSORIUM_LEDGER`, corrupting the cadence record and violating the implicit "one Supervisor per Core" property. Horizontal scaling across multiple processes was not supported.
- **How it closed:** Phase 5g+ shipped every clause of the pay-down commitment in five commits on `phase-5g+/multi-worker-broker`:
  1. **Doctrine.** [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) gained Â§ "Multi-worker coherence (Phase 5g+)" pinning five properties (SQLite-WAL broker as chosen mechanism; single-leader Supervisor via lease-based election; global per-principal rate-limit buckets; Phase-6 migration path behind the `Broker` Protocol; additive env surface). [`docs/33-MULTI-WORKER.md`](./docs/33-MULTI-WORKER.md) lands as a new top-level operational doctrine covering broker schema, lease semantics, SQLite-WAL posture, runbook, failure modes, observability, and the Phase-6 replacement contract.
  2. **Broker module.** [`orchestrator/runtime/broker.py`](./orchestrator/runtime/broker.py) (new) ships `BrokerConfig`, the `Broker` Protocol (Phase-6-replaceable surface: `publish_snapshot`, `latest_snapshot`, `try_acquire_leader`, `renew_leader`, `is_leader`, `check_and_record_rate`), and `SqliteBroker` â€” a stdlib-only implementation using `sqlite3` in WAL mode (`PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout` configurable), three tables (`supervisor_snapshot` singleton, `supervisor_leader` lease row, `rate_limit_events` append+prune), and atomic `BEGIN IMMEDIATE` transactions for leader election and rate-limit checks. `load_broker_from_env()` returns `None` when `XION_BROKER_DB_PATH` is unset (backward-compat default).
  3. **Supervisor wiring.** `Supervisor.__init__` gained an optional `publish: Callable[[Mapping[str, Any]], None] | None = None` hook called after every successful `tick_once()` (broker-agnostic by construction; publish exceptions swallowed to preserve in-process state). New [`orchestrator/runtime/supervisor_shell.py`](./orchestrator/runtime/supervisor_shell.py) ships `BrokerSupervisorShell` â€” a wrapper that performs lease-based election against the broker: workers that acquire the lease run the Supervisor loop and publish each tick; workers that fail run as followers whose `latest_snapshot()` reads from the broker. On leader crash, the first follower whose acquire attempt succeeds (lease expired) promotes itself; failover is bounded by `leader_lease_s`. [`orchestrator/api/lifespan.py`](./orchestrator/api/lifespan.py) conditionally constructs broker + shell when `XION_BROKER_DB_PATH` is set; single-worker posture (broker absent) remains byte-identical to 5g-iv.
  4. **Launcher multi-worker mode.** [`orchestrator/api/__main__.py`](./orchestrator/api/__main__.py) reads `XION_API_WORKERS` from env (default 1). When `workers > 1`, the launcher fails closed at startup unless `XION_BROKER_DB_PATH` is set (multi-worker without a broker is the documented corruption path). Multi-worker mode uses Uvicorn's `factory=True` posture with a module-level `create_default_app()` factory so each worker process gets its own `Relay` + `AppDeps` + `FastAPI` app and they coordinate exclusively through the broker file.
  5. **Verifier.** [`xion-verify supervisor-singleton`](./xion-verify/src/xion_verify/commands/supervisor_singleton.py) (new) walks `SENSORIUM_LEDGER.jsonl` for `tick_commit` rows inside a configurable window (default 24 h), preserving the ledger's file-order (the seq chain is the canonical insertion order; sorting would mask within-epoch clock regressions). Asserts three properties: (A) bounded failover â€” `relay_id` transitions â‰¤ `--max-failovers`; (B) within-leader-epoch strict `as_of_utc_ns` monotonicity â€” catches clock regressions and two-Supervisors-one-`relay_id` corruption; (C) no concurrent-leader time-range overlap â€” for each distinct `relay_id` the closed range must not overlap any other's (the precise corruption signature this KW named). Returns `NOT_YET_SEALED` when the ledger is absent, empty, or has no tick rows inside the window.
  6. **Tests.** 31 new broker tests in [`orchestrator/tests/test_runtime_broker.py`](./orchestrator/tests/test_runtime_broker.py). New [`orchestrator/tests/test_api_multi_worker.py`](./orchestrator/tests/test_api_multi_worker.py) spins up two in-process `BrokerSupervisorShell` instances sharing one broker DB and asserts single-leader domination of `tick_commit` rows, follower-snapshot-shape match, leader failover on stop within lease, and lifespan wiring sanity. 13 new verifier tests cover every branch of `supervisor-singleton`. `xion-verify all --allow-not-yet-sealed` green end-to-end.
- **Residual / remaining weaknesses (tracked separately):**
  - `KW-SUPERVISOR-002` â€” tick_commit heartbeat continuity across restarts. Stays open; needs a Phase-6+ deploy-event ledger the orchestrator does not yet publish.
  - Cross-host coordination. Out of scope by design; the SQLite file is single-machine. Cross-host is Phase 6+ AO Process mailbox territory.
- **Verifier:** `xion-verify supervisor-singleton` (live as of Phase 5g+, `NOT_YET_SEALED` until the first `tick_commit` row lands in the observed window).

### KW-RATE-001 â€” Per-principal sliding window is in-process; multi-worker deployment loses bucket coherence

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-22 (Phase 5g-iv admission-control landing)
- **Severity:** low
- **Status:** `closed` on 2026-04-22 by the Phase 5g+ multi-worker-broker landing (branch `phase-5g+/multi-worker-broker`).
- **Description:** Phase 5g-iv rate-limited authenticated requests with a `collections.deque` of monotonic-ns timestamps under a single `threading.Lock`, keyed per `principal_id`. The mechanism was in-process by construction. A `uvicorn --workers N` deployment ran N independent Python processes, each with its own `app.state.rate_limiters` map; each process held an independent bucket per principal, so the effective per-principal budget was `N Ã— XION_API_RATE_BUDGET`. A principal that targeted all N workers in parallel could consume N times the intended budget.
- **How it closed:** Phase 5g+ shipped every clause of the pay-down commitment as part of the multi-worker-broker landing:
  1. **Doctrine.** [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) Â§ "Multi-worker coherence (Phase 5g+)" pinned global per-principal rate-limit buckets as property (P3). [`docs/33-MULTI-WORKER.md`](./docs/33-MULTI-WORKER.md) covers the broker's `rate_limit_events` table schema (append + prune; `(principal_id, event_at_ns)` composite index) and the atomic `BEGIN IMMEDIATE` posture.
  2. **Broker rate-limit primitive.** [`orchestrator/runtime/broker.py`](./orchestrator/runtime/broker.py) `Broker.check_and_record_rate(principal_id, window_ns, budget, now_ns) -> RateCheck` runs in a single `BEGIN IMMEDIATE` transaction: delete stale events (`event_at_ns <= now - window`), count remaining, conditionally insert, and return `RateCheck(allowed, retry_after_s, events_in_window)` atomically. Two workers sharing one broker share one global sliding window per principal â€” the effective budget is `XION_API_RATE_BUDGET` regardless of `N`.
  3. **Admission wiring.** [`orchestrator/api/admission.py`](./orchestrator/api/admission.py) gained a `RateLimitStore` Protocol with `check_and_record(principal_id, now_ns) -> RateCheck`. `InProcessSlidingWindowStore` (used when no broker is configured) lazy-allocates `SlidingWindow` instances per principal; behavior byte-identical to 5g-iv. `BrokerBackedSlidingWindowStore` (used when a broker is configured) delegates every check to `Broker.check_and_record_rate(...)`. `build_rate_limiters(config, *, broker=None)` returns the right store; the `admission_dependency` route-level code is untouched.
  4. **Tests.** 9 new tests in [`orchestrator/tests/test_api_admission.py`](./orchestrator/tests/test_api_admission.py) cover: in-process store lazy allocation + overflow + independence; broker-backed two-workers-one-bucket budget coherence (the test that directly closes this KW â€” two `BrokerBackedSlidingWindowStore` instances sharing one `SqliteBroker` exhaust the global budget in `budget` total requests, not `2 Ã— budget`); different principals don't share; eviction across workers; `build_rate_limiters` dispatch (returns in-process when broker is None, broker-backed otherwise); `admission_dependency` + broker-backed store end-to-end 429 enforcement.
- **Residual / remaining weaknesses (tracked separately):**
  - A runtime `xion-verify api-budget-fidelity` against a live deployment is still `NOT_YET_SEALED` until Phase 6+ (structural `xion-verify api-tokens` against the config remains live as of 5g-iv).
  - The broker is single-machine; cross-host coordination is Phase 6+ AO Process mailbox territory. Operators running multi-host deployments should pin a reverse-proxy with per-principal rate-limiting in front.
- **Verifier:** `xion-verify api-tokens` (live as of Phase 5g-iv) checks rate-limit knob sanity; `xion-verify supervisor-singleton` (live as of Phase 5g+) is the neighboring verifier that asserts the broker's leader-election property â€” the two together seal the multi-worker posture.

### KW-CHAT-001 â€” POST /chat is non-streaming

- **Domain:** `PROTOCOL`
- **Discovered:** 2026-04-21 (Phase 5g-i Chat Surface landing)
- **Severity:** low
- **Status:** `closed` on 2026-04-22 by the Phase 5g-ii streaming-chat landing (branch `phase-5g-ii/streaming-chat`).
- **Description:** `POST /chat` in Phase 5g-i was a single request-response endpoint. The entire generated candidate was produced server-side before any byte reached the client. For multi-second generations â€” common at the open-weights floor on commodity hardware â€” the connection blocked for the full generation duration. A user watching a cursor blink had no way to see partial progress, and a client under a connection-pool time budget could time out mid-generation and waste a full OpenRouter bill on unsurfaced text.
- **How it closed:** Phase 5g-ii shipped every clause of the pay-down commitment in five commits on `phase-5g-ii/streaming-chat`:
  1. **Doctrine.** [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) gained Â§ "Streaming the Chat Surface (Phase 5g-ii)" pinning the "Speculative-with-retroactive-refusal" posture and seven properties (SSE transport at `POST /chat/stream`; `POST /chat` stays non-streaming for backward compat; chunks are client-side provisional until `done:approve`; egress moderation runs on the buffered complete candidate; `done:refuse` retroactively replaces chunks with a `RefusalEnvelope`; client disconnect propagates as a real provider cancel; ledger rows write post-moderation only). [`docs/32-CHAT-STREAMING.md`](./docs/32-CHAT-STREAMING.md) lands as a new top-level operational doctrine shape-symmetric with `docs/29-BILLING-X402.md`, `docs/30-API-ADMISSION.md`, and `docs/31-WEB-CLIENT.md`.
  2. **SSE server transport.** [`orchestrator/api/chat_stream.py`](./orchestrator/api/chat_stream.py) ships `POST /chat/stream` returning `text/event-stream`. Reuses the Phase-5g-iv admission gate and the Phase-5g-iii x402 gate verbatim (admission failures report as HTTP-level 401/429/402; every post-admission failure reports INSIDE the stream as a terminal `done` or `error` event). A single `_finalize_stream_ledger` tail writes exactly one PAYMENT row after the terminal state is known.
  3. **Provider streaming.** `GenerativeProvider` Protocol extended with optional `generate_stream(...) -> AsyncIterator[str | GenerationResult]`. [`orchestrator/inference_router/providers/chutes.py`](./orchestrator/inference_router/providers/chutes.py) implements hosted streaming, and [`orchestrator/inference_router/providers/ollama.py`](./orchestrator/inference_router/providers/ollama.py) implements real Ollama streaming via `/api/generate` with `stream=true`.
  4. **Client render-path.** [`clients/web/src/lib/api.ts`](./clients/web/src/lib/api.ts) grows `streamChat()` returning `AsyncIterable<StreamEvent>` built on Fetch `ReadableStream` + a manual SSE parser (no new dep). [`clients/web/src/views/ChatView.tsx`](./clients/web/src/views/ChatView.tsx) grows a `streaming` state that renders chunks with a "pending egress review" affordance; `done:approve` commits the chunks; `done:refuse` retroactively replaces them with the `RefusalEnvelope` UI.
  5. **Verifier.** [`xion-verify chat-streaming-fidelity`](./xion-verify/src/xion_verify/commands/chat_streaming_fidelity.py) is new: walks `PAYMENT_LEDGER` and `SAFETY_LEDGER` for rows carrying a `stream_id` and asserts six stream-level invariants (per-ledger chain integrity; `stream_id` format + presence-for-cancelled; exactly one PAYMENT row per `stream_id`; stream-subset money-shape; cancel-without-paired-SAFETY-refuse; egress-refuse-with-paired-SAFETY-refuse). Returns `NOT_YET_SEALED` until the first streaming turn has landed.
  6. **Tests.** 13 new streaming server tests against a fake provider (full envelope matrix + deadline + cancel); 7 new client streaming tests including an `axe-core` WCAG 2.2 AA pass on the pending state; 10 new `chat-streaming-fidelity` verifier tests. `xion-verify all --allow-not-yet-sealed` green end-to-end.
- **Residual / remaining weaknesses (tracked separately):** `KW-BILLING-001` (x402 signature verification still shape-only on B2) and `KW-RATE-001` (in-process sliding window) are unchanged by this landing. No new KWs opened.
- **Verifier:** `xion-verify chat-streaming-fidelity` (live as of Phase 5g-ii, `NOT_YET_SEALED` until the first streaming turn lands).

### KW-CHAT-003 â€” Generation is synchronous; no user-facing cancel

- **Domain:** `PROTOCOL`
- **Discovered:** 2026-04-21 (Phase 5g-i Chat Surface landing)
- **Severity:** low
- **Status:** `closed` on 2026-04-22 by the Phase 5g-ii streaming-chat landing (branch `phase-5g-ii/streaming-chat`).
- **Description:** The Phase 5g-i Chat handler called the generative provider inside `asyncio.wait_for(asyncio.to_thread(...), timeout=deadline_s)`. A client who disconnected mid-generation had no way to signal the server to abort the outbound provider call; the Python thread running the provider's HTTP POST finished to completion or hit the deadline, whichever came first. The operator paid the full generation cost (OpenRouter tokens at the hosted tier, Ollama CPU time at the floor) even when no one was listening.
- **How it closed:** Phase 5g-ii's Commit 3 shipped every clause of the pay-down commitment:
  1. **Streaming transport provides a real client-disconnect signal.** [`orchestrator/api/chat_stream.py`](./orchestrator/api/chat_stream.py) polls `Request.is_disconnected()` between chunk yields. On client-gone, the handler cancels the provider task via `asyncio.Task.cancel()`; because both OpenRouter and Ollama providers now run on `httpx.AsyncClient` with cancel-aware requests, the cancellation propagates as a real TCP-FIN closing the upstream connection â€” upstream billing stops at cancel time, not at deadline time.
  2. **New `outcome=cancelled` ledger shape.** [`orchestrator/billing/ledger.py`](./orchestrator/billing/ledger.py) grows `cancelled` as a fourth PAYMENT outcome alongside `settled` / `refunded` / `forfeited`. A cancelled row carries `refund_XION == committed_XION`, `refusal_stage == null` (cancel fires before egress moderation runs, so there is no stage to record), and STRUCTURALLY REQUIRES the new `stream_id` field (cancel is stream-only; a non-streaming turn cannot be cancelled by doctrine).
  3. **Refusal-is-Free extension.** [`xion-verify refusal-is-free`](./xion-verify/src/xion_verify/commands/refusal_is_free.py) extended: a `cancelled` row satisfies the money-shape check (full refund, no settled value) without requiring a paired SAFETY `verdict=refuse` row. The asymmetry is named honestly in doctrine â€” cancel is an operational outcome, not a moderation outcome.
  4. **New verifier catches the asymmetry.** [`xion-verify chat-streaming-fidelity`](./xion-verify/src/xion_verify/commands/chat_streaming_fidelity.py) Property E asserts that `outcome=cancelled` rows have NO paired SAFETY `verdict=refuse` row (cancel fires after ingress approves and before egress moderation would run, so no refuse row can legitimately pair to the cid).
  5. **Tests.** Client-disconnect test in `test_chat_stream.py` asserts the provider task is cancelled, the PAYMENT row shows `outcome=cancelled` with full refund and the required `stream_id`, and no SAFETY egress row exists.
- **Residual / remaining weaknesses:** None. The non-streaming `POST /chat` still lacks a cancel surface (stdlib threads cannot be cancelled), but that path has the per-turn deadline as its bound, and any caller that wants real cancel can switch to `POST /chat/stream`.
- **Verifier:** `xion-verify chat-streaming-fidelity` (live as of Phase 5g-ii) â€” Property E pins the cancel money-shape; Property D cross-checks cancel rows against settled/refunded rows for the same stream.

### KW-CLIENT-002 â€” Web client chat UX is non-streaming; multi-second generations block the bubble

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-22 (Phase 5g-v web-client landing)
- **Severity:** low
- **Status:** `closed` on 2026-04-22 by the Phase 5g-ii streaming-chat landing (branch `phase-5g-ii/streaming-chat`).
- **Description:** Phase 5g-v's `ChatView` issued a single `POST /chat` and rendered the response when it returned. A multi-second generation blocked the client's chat bubble for the full duration, up to the 30 s per-turn deadline. There was no progressive-text rendering and no cancel affordance during the block.
- **How it closed:** Phase 5g-ii's Commit 4 shipped every clause of the pay-down commitment:
  1. **`streamChat()` API wrapper.** [`clients/web/src/lib/api.ts`](./clients/web/src/lib/api.ts) grows `streamChat(request, credential, signal)` returning `AsyncIterable<StreamEvent>` where `StreamEvent` is the discriminated union `{ kind: "chunk", text } | { kind: "done", verdict: "approve" | "refuse" | "cancelled", envelope? } | { kind: "error", error: ApiError }`. Built on Fetch `ReadableStream` + a manual SSE line-parser (no new dep). Respects `AbortSignal` for client-initiated cancel.
  2. **`ChatView` streaming render-path.** [`clients/web/src/views/ChatView.tsx`](./clients/web/src/views/ChatView.tsx) grows a pending-chunk buffer rendered with a "pending egress review" visual affordance (subtle spinner + dim text + ARIA-live announcement) while chunks stream. `done:approve` commits the buffered chunks as the assistant turn; `done:refuse` retroactively replaces the chunks with the content-free `RefusalEnvelope` UI (same path Phase 5g-i already used for 451 responses); `done:cancelled` surfaces a cancelled-state affordance; `error` uses the Phase 5g-v ApiError discriminated-union matching that every view already has.
  3. **Fallback preserved.** `?stream=0` forces the Phase 5g-i non-streaming render-path; operators and integrators with no streaming story keep their existing code path.
  4. **Accessibility.** `axe-core` WCAG 2.2 AA pass on the pending state pins: the pending affordance is discoverable to screen readers via `aria-live="polite"`; the spinner carries a descriptive label; retroactive-refusal replacement is announced as a new assistant message (not an update-in-place); contrast ratios on the dim-text state clear the 4.5:1 bar.
  5. **Tests.** New Vitest suite `ChatView streaming` covers: happy-path chunks render as pending then commit on approve; refuse path replaces chunks with the refusal envelope; cancel path surfaces cancelled-state UI; error path surfaces the ApiError; axe-core pass on the pending state.
  6. **Doctrine.** [`docs/31-WEB-CLIENT.md`](./docs/31-WEB-CLIENT.md) Â§ "Deliberate non-properties" removes the non-streaming item and adds a Â§ addendum naming the streaming UX.
- **Residual / remaining weaknesses (tracked separately):** `KW-CLIENT-001` (operator-dashboard only; in-browser x402 signing still Phase 6+) is unchanged by this landing.
- **Verifier:** `xion-verify chat-streaming-fidelity` (live as of Phase 5g-ii) + the Vitest component suite covering the envelope matrix on the streaming render-path.

### KW-API-001 â€” HTTP surface has no auth, no TLS, no rate-limit

- **Domain:** `PROTOCOL`
- **Discovered:** 2026-04-21 (Phase 5f HTTP read-only surface landing)
- **Severity:** low
- **Status:** `closed` on 2026-04-22 by the Phase 5g-iv admission-control landing (branch `phase-5g-iv/admission-control`).
- **Description:** `orchestrator/api/` shipped its first three read-only endpoints (`GET /health`, `/drive`, `/sensorium`) at Phase 5f with no authentication, no TLS termination, no rate limiting, and no `/chat`. Phase 5g-i added `POST /chat` and Phase 5g-iii added the billing gate, but anyone who could reach the bound socket could still read Xion's internal state at arbitrary query rate, and `/chat` ran without a per-token bucket â€” a hostile scraper holding one valid commitment template could in principle drain provider budget at line-rate. There was no mechanism in `orchestrator/api/` to reject a client by identity, distinguish a friendly reader from a hostile scraper, require a TLS-encrypted connection on a non-loopback bind, or budget per-caller request volume. This was the last explicit D2-deploy blocker named in [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) Â§ "The HTTP Surface (Phase 5f)" â†’ "Hardening posture".
- **How it closed:** Phase 5g-iv shipped every clause of the pay-down commitment in five commits on `phase-5g-iv/admission-control`:
  1. **Doctrine.** [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) Â§ "The Admission-Control Surface (Phase 5g-iv)" pins the six properties (bearer authentication, sliding-window per-principal rate-limiting, fail-closed TLS for non-loopback binds, `401 â†’ 429 â†’ 402` admission ordering, content-free 401/429 bodies, `principal_id` naming convention with no leak into `PAYMENT_LEDGER` until Phase 6). The Â§ "The HTTP Surface (Phase 5f)" â†’ "Hardening posture" subsection is updated in place to mark the gap closed and link forward. [`docs/30-API-ADMISSION.md`](./docs/30-API-ADMISSION.md) lands as a new top-level operational doctrine for the admission surface mirroring [`docs/29-BILLING-X402.md`](./docs/29-BILLING-X402.md)'s posture for the billing surface (token issuance, TLS cert procurement, rate-limit budget tuning, deployment runbook, crypto-agility).
  2. **Module.** [`orchestrator/api/admission.py`](./orchestrator/api/admission.py) ships `AdmissionConfig` (frozen dataclass, fail-closed `__post_init__` validation: token entropy â‰¥ 128 bits, `principal_id` matches `^[a-z0-9_-]{1,64}$`, non-loopback host requires both TLS paths and both files exist), `SlidingWindow` (deque-of-monotonic-ns timestamps under a single `threading.Lock`, O(1) amortized check + record), `verify_bearer` (constant-time via `hmac.compare_digest` over every token), `load_admission_config_from_env`, and the `admission_dependency` FastAPI callable. Stdlib-only; no new core runtime dep.
  3. **Launcher.** [`orchestrator/api/__main__.py`](./orchestrator/api/__main__.py) builds a real `AppDeps` from env vars and runs `uvicorn` with `--workers 1` enforced (a `KW-RATE-001` mitigation: in-process sliding window cannot share state across workers) and TLS configured from `XION_TLS_CERT_PATH` / `XION_TLS_KEY_PATH`. The launcher refuses to bind a non-loopback host without both â€” fail-closed regardless of `XION_API_REQUIRE_BEARER` mode.
  4. **Routes + ordering.** `Depends(admission_dependency)` is wired into [`orchestrator/api/app.py`](./orchestrator/api/app.py) (`/health`, `/drive`, `/sensorium`), [`orchestrator/api/chat.py`](./orchestrator/api/chat.py) (`/chat`, in front of the existing 5g-iii billing gate so the constitutional `401 â†’ 429 â†’ 402` ordering is structural, not aspirational), and [`orchestrator/api/pricing.py`](./orchestrator/api/pricing.py) (`/pricing`, defense-in-depth â€” the route remains constitutionally public and unrate-limited via the dependency's public-route shortcut). Content-free `AuthChallenge` (401) and `RateLimitChallenge` (429) Pydantic models with `extra="forbid"` and `frozen=True` ensure no internal state leaks through error responses. [`orchestrator/api/lifespan.py`](./orchestrator/api/lifespan.py) loads the `AdmissionConfig` and builds the per-principal `SlidingWindow` map at startup.
  5. **Verifier.** [`xion-verify api-tokens`](./xion-verify/src/xion_verify/commands/api_tokens.py) is new (promoted from `NOT_YET_SEALED` to live): loads the same `AdmissionConfig` the orchestrator's lifespan loads and applies the same `__post_init__` validation, so a config the verifier passes is structurally identical to one the orchestrator will accept. Optional `--env-file PATH` lets a CI gate audit a deployment `.env` without invoking the operator's shell. Reports `OK` against [`./.env.example`](./.env.example) (loopback default, `require_bearer=false`); reports the specific `AdmissionConfigError` reason on any misconfiguration.
  6. **Tests.** New `orchestrator/tests/test_api_admission.py` covers `AdmissionConfig` validation, `SlidingWindow` behaviour, `verify_bearer`, `AuthChallenge` / `RateLimitChallenge` contract adherence, end-to-end 401/429/200 on `/drive`, `/sensorium`, `/chat`, public access on `/health` + `/pricing`, and crucially the `401 â†’ 429 â†’ 402` ordering (401 wins over 402 with valid commitment but missing token; 429 wins over 402 within bucket overflow). New `xion-verify/tests/test_api_tokens_verifier.py` covers the verifier's full validation matrix and the `--env-file` overlay's environment restoration. Full suite **637 / 637** pass; `xion-verify api-tokens --env-file .env.example` returns `OK`.
- **Residual / remaining weaknesses (tracked separately):**
  - `KW-AUTH-001` â€” Bearer tokens are operator-issued shared secrets; no on-chain federated identity. Closes Phase 6+ when `principal_id` binds to an Arweave-stored pubkey lattice.
  - `KW-RATE-001` â€” Sliding window is in-process; multi-worker would have N independent buckets. Closes alongside `KW-SUPERVISOR-002` when the multi-worker shared-state broker lands.
  - `KW-TLS-001` â€” uvicorn-native TLS has no automated cert rotation and no ALPN/HTTP-2; long-term path is reverse-proxy delegation.
- **Verifier:** `xion-verify api-tokens` (live as of Phase 5g-iv).

### KW-CHAT-002 â€” /chat runs with billing disabled; blocks any D2 deploy

- **Domain:** `PROTOCOL`
- **Discovered:** 2026-04-21 (Phase 5g-i Chat Surface landing)
- **Severity:** medium
- **Status:** `closed` on 2026-04-21 by the Phase 5g-iii billing landing (branch `phase-5g-iii/billing-x402`).
- **Description:** `POST /chat` in Phase 5g-i served turns without an x402 pre-authorization, without a `402 Payment Required` path, without a `PAYMENT_LEDGER`, and without a Refusal-Free settlement row on `451` responses. A D2 production deploy in that configuration would either bankrupt the operator on hostile-scraper load or violate the `docs/07-ECONOMY.md` Â§ "Pay-to-Activate" constitutional property (billable turns without payment enforcement).
- **How it closed:** Phase 5g-iii shipped every clause of the pay-down commitment:
  1. **Doctrine.** [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) Â§ "The Chat Billing Surface (Phase 5g-iii)" pins the six billing properties (Pay-to-Activate, Refusal-is-Free structural refund, pricing transparency, content-free commitments, atomic ledger writes, algorithm-agility on the commitment hash). [`docs/29-BILLING-X402.md`](./docs/29-BILLING-X402.md) lands as a new top-level operational doctrine for the billing surface mirroring `docs/27-RESEARCH-SPEND.md`'s posture for outbound spend. [`docs/schemas/ledger-payment.yaml`](./docs/schemas/ledger-payment.yaml) pins the canonical schema with `source_sha256` anchored to `docs/04-ARCHITECTURE.md`.
  2. **`GET /pricing` endpoint.** [`orchestrator/api/pricing.py`](./orchestrator/api/pricing.py) ships the `PricingConfig` loader (env-var driven, Genesis Defaults from `docs/07-ECONOMY.md` Â§ "Five-slice posted price"), the sum-to-one / non-negative / revision-id-present validator, and the read-only handler. A misconfigured pricing split fails the lifespan closed rather than serving a wrong body.
  3. **x402 pre-auth gate + `PAYMENT_LEDGER`.** [`orchestrator/billing/`](./orchestrator/billing/) ships the append-only, hash-chained `PAYMENT_LEDGER.jsonl` (byte-exact canonicalization mirror of `SAFETY_LEDGER` so a Phase-6 unified treasury verifier walks both files with one library), the `Commitment` parser for the `X-Payment-Commitment` header, stdlib-only HMAC-SHA256 B1 operator-attestation verification, and shape-only B2 x402 commitment validation (full x402 signature verification is tracked as `KW-BILLING-001`, Phase 6+).
  4. **Refusal-is-Free settlement.** [`orchestrator/api/chat.py`](./orchestrator/api/chat.py) refactored to a single `_finalize` tail: every terminal path (200 settled, 451 ingress refuse, 451 egress refuse, 451 empty-candidate, 503 no-floor, 503 provider-error) writes exactly one `PAYMENT_LEDGER` row with `outcome âˆˆ {settled, refunded}` BEFORE the HTTP response is sent. Every refunded row has `refund_XION == committed_XION` and `settled_XION == 0` â€” structurally impossible to violate, byte-checked by the writer and re-checked by `xion-verify refusal-is-free`.
  5. **Verifiers.** [`xion-verify pricing`](./xion-verify/src/xion_verify/commands/pricing.py) promoted from `NOT_YET_SEALED` to live: loads the same `PricingConfig` the lifespan loads and reports `FAIL` with the specific `PricingConfigError` reason on any invariant break. [`xion-verify refusal-is-free`](./xion-verify/src/xion_verify/commands/refusal_is_free.py) is new: joins `SAFETY_LEDGER` â†” `PAYMENT_LEDGER` on `correlation_id` and asserts four properties (per-ledger chain integrity; money-shape per row; ingress/egress mirror between SAFETY verdict=refuse and PAYMENT outcome=refunded; settled-implies-allowed â€” a settled payment for a refused turn is a Covenant-tier integrity break).
  6. **Tests.** 56 new tests (23 commitment parser/verifier, 18 ledger writer/chain, 15 chat integration, 6 pricing verifier, 14 refusal-is-free verifier). Full suite 585 pass / 1 skip. `xion-verify all --allow-not-yet-sealed` green with `pricing` and `refusal-is-free` both `OK`.
- **Residual / remaining weaknesses (tracked separately):** `KW-BILLING-001` â€” x402 signature verification deferred to Phase 6+ (5g-iii does shape-only validation of B2 commitments); `KW-BILLING-002` â€” catalog-driven dynamic pricing deferred (5g-iii serves operator-posted governance values, not per-provider token-cost rollup).
- **Verifier:** `xion-verify pricing` (live as of Phase 5g-iii); `xion-verify refusal-is-free` (live as of Phase 5g-iii).

### KW-ARBITER-006 â€” Covenant principle numbering vs Arbiter `principle_id` registry drift

- **Domain:** `DOCS` / `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 4e baseline-corpus curation)
- **Severity:** low
- **Status:** `closed` on 2026-04-21 by the Phase 4e completion landing.
- **Description:** [`genesis/COVENANT.md`](./genesis/COVENANT.md) numbers its fourteen principles by doctrinal weight; the Arbiter's `principle_id` strings in [`orchestrator/safety/principles.py`](./orchestrator/safety/principles.py) number them by pipeline order of enforcement. A reader who greped `principle_id: "7"` in `SAFETY_LEDGER.jsonl` and looked up "Principle 7" in the Covenant would misread the row (Arbiter 7 = PII Leakage; Covenant Principle 7 = Protection of the Vulnerable).
- **How it closed:** [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) Â§ "Covenant principle â†” Arbiter `principle_id` crosswalk" lands a single authoritative table covering every `"1"`..`"14"`, `"14a"`, `"14b"` id with its Arbiter registry name, the Covenant number(s) it traces back to, and the Covenant canonical name. The table is structurally discoverable (it sits between Â§ "The Arbiter" and Â§ "Safety Ledger row schema" â€” exactly where a reader investigating a ledger row's `principle_id` would land) and explains the asymmetry (one Arbiter id may map to multiple Covenant principles and vice versa; the asymmetry is intentional, because the Covenant is organised around what humans need protected and the Arbiter is organised around what the rule engine can decide). The table is cited from this entry, from the corpus README, and implicitly from [`orchestrator/safety/principles.py`](./orchestrator/safety/principles.py) via its `doctrine_anchor` fields. Rename avoided: renumbering the Arbiter ids would break every historical `SAFETY_LEDGER` row; the table is cheaper and carries the same information.
- **Verifier:** `xion-verify links` (the crosswalk lives inline inside `docs/04-ARCHITECTURE.md`, so the schema-pinned `source_sha256` of that file covers the table's byte-stability). Human review of the table remains the primary check at the doctrine layer.

### KW-RELAY-001 â€” Relay â†” Arbiter integration contract is doctrine-only

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 4c doctrine landing)
- **Severity:** medium
- **Status:** `closed` on 2026-04-21 by the Phase 5a Relay landing.
- **Description:** Between Phase 4c and Phase 5a, the integration contract specified in `docs/04-ARCHITECTURE.md` Â§ "Relay â†” Arbiter integration contract" â€” coverage rules, fail-closed paths, `correlation_id` derivation, latency budget, watchdog, in-process â†” TCP-loopback transport progression â€” existed only as doctrine. The `orchestrator/relay.py` that implements it was not yet written; no candidate was passing through `gate()` because no Relay existed to pass one.
- **How it closed:** Phase 5a landed the Relay with every clause of the pay-down commitment satisfied:
  1. **`orchestrator/relay/relay.py`** ships the `Relay` class with `evaluate(candidate) -> RelayResult`, `correlation_id = "{state_height_int}:{nonce_hex}"` derivation (state_height monotonic from `time.time_ns()` in Phase 5a; advancement to a real state-chain height is a Phase 6 concern), and the three gate() call sites the doctrine names (primary; sub-agent and tool-echo wrappers land alongside the Phase 5 cognition layer using the same call shape).
  2. **Wall-clock watchdog** enforces the 250 ms hard cap via `ThreadPoolExecutor` + `Future.result(timeout=...)`. Honest residual: Python cannot preempt the worker thread that ran past the cap â€” tracked separately as the new `KW-RELAY-003`.
  3. **Three fail-closed paths** wired and tested: `arbiter_timeout` (watchdog fired), `ruleset_uncaught_exception` (gate() raised), `arbiter_unreachable` (helper for the Phase 6+ TCP sidecar transport; constructed via `build_unreachable_verdict` and exercised by `test_build_unreachable_verdict_helper` even though no sidecar yet exists to fail). All three write a v2 SAFETY_LEDGER row with `principle_id="6"` (Refusal Right) and `llm_verdict=null`. `orchestrator.safety.api.gate()` was extended with `append_to_ledger: bool = True` so the Relay can call gate() with `False` and own the ledger-write timing centrally â€” preventing the watchdog-vs-gate() race that would otherwise double-write SAFETY rows.
  4. **REQUEST_LEDGER**: new `orchestrator/relay/ledger.py` (~250 LOC) ships an append-only hash-chained `REQUEST_LEDGER.jsonl` with the doctrine-pinned schema in `docs/04-ARCHITECTURE.md` Â§ "REQUEST_LEDGER row schema (Relay-side, Phase 5a)" and `docs/schemas/ledger-request.yaml`. Joins with SAFETY_LEDGER on `correlation_id`. Refund-pairing is the half explicitly NOT closed â€” treasury is Phase 6+.
  5. **`xion-verify refund-fidelity`** promoted from `NOT_YET_SEALED` to live: walks both ledger chains, cross-joins on `correlation_id`, asserts pairing + `gate_call_count` consistency + `final_outcome` agreement. 7 unit tests pin the four real failure modes (orphan REQUEST â†’ silent-egress signature; outcome mismatch with re-hashed REQUEST row; chain break in either ledger; half-sealed ledger state).
  6. **`xion-verify refusal-rate`** promoted from `NOT_YET_SEALED` to live: tallies SAFETY_LEDGER verdicts (ok/refuse/escalate), v1-vs-v2 refuse-source breakdown, and `escalation_reason` distribution including the new Relay-side `arbiter_timeout` / `arbiter_unreachable` rows so degraded-mode events are first-class telemetry. 4 unit tests including a chain-break catch.
  7. **Tests:** 26 in `test_relay_ledger.py` + 28 in `test_relay.py` + 11 in the two verifier suites = 65 net-new. Full suite **333 passed / 1 skipped**; `ruff` clean; `xion-verify all` reports both new verifiers as `OK` live.
- **Residual / remaining weaknesses (tracked separately):**
  - `KW-RELAY-002` â€” Streaming-chunk gating still deferred to Phase 6+ (unchanged by Phase 5a).
  - `KW-RELAY-003` â€” Watchdog cannot preempt the worker thread that ran past the hard cap; closes when the Phase 6+ TCP-loopback subprocess sidecar lands.
  - `KW-ARBITER-005` â€” Refusal-rate verifier is live but operator-tail-only; the corpus comparison and asymmetric-threshold work remains.
- **Verifier:** `xion-verify arbiter-up` (live), `xion-verify refund-fidelity` (live as of Phase 5a), `xion-verify refusal-rate` (live as of Phase 5a).

### KW-ARBITER-003 â€” No Arweave anchoring of ledger tip yet

- **Domain:** `AUDIT`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Severity:** medium
- **Status:** `closed` on 2026-04-21 by the Phase 4b anchor-submitter landing.
- **Description:** `SAFETY_LEDGER.jsonl` was hash-chained, but its tip was only stored locally. A malicious operator with write access to the ledger file could have rewritten the entire chain from row 0 onward â€” `verify_chain` would still have passed on the rewritten file because every row's `this_hash` is recomputable. The chain's integrity property was only load-bearing against *accidental* corruption and against readers who already held an older tip they trusted.
- **How it closed:** Phase 4b landed the `SAFETY_LEDGER_ANCHORS.jsonl` mechanism:
  1. **Doctrine** in `docs/04-ARCHITECTURE.md Â§ "Safety Ledger Arweave anchoring"` and the canonical schema in `docs/schemas/ledger-safety-anchors.yaml`.
  2. **Code** in `orchestrator/safety/anchor.py`: `AnchorSubmitter` ABC, `LocalOnlySubmitter` (pure-stdlib default), `ArweaveSubmitter` (real AR publishing via the optional `[anchor]` extra), cadence policy (64 rows OR 6 hours OR startup), `write_anchor`, `verify_anchor_chain`, `cross_check_anchors_against_ledger`.
  3. **Verifier** in `xion-verify arbiter-up`: if an anchors file is present, the structural chain is walked AND every anchor's `ledger_tip_hash` is cross-checked against the ledger's row at `ledger_row_count - 1`. An operator who truncates or rewrites the ledger after anchoring trips the cross-check.
  4. **CLI** subcommands `python -m orchestrator.safety anchor` (one-shot writer) and `python -m orchestrator.safety verify-anchors` (verifier + cross-check).
- **Residual / remaining weaknesses (tracked separately):**
  - `KW-ANCHOR-001` â€” the hot-single-signer anchor wallet (Phase 6 migrates to AO Core).
  - `KW-ANCHOR-002` â€” gateway-dependent cross-Arweave re-fetch not yet shipped; doctrine defines the multi-gateway requirement.
- **Verifier:** `xion-verify arbiter-up` (live) reports `covers=<rows_covered>/<ledger_rows>` and `truncation_window=<N>` on every invocation.

### KW-DOCS-001 â€” Documentation contradictions and drift

- **Domain:** `DOCS`
- **Discovered:** 2026-04-19 (audit Phase 0)
- **Severity:** medium
- **Status:** `closed` on 2026-04-20 by the Phase 0 doctrine-hygiene landing (constitutional witness rehash in `genesis/GENESIS_ARTIFACT.md` Â§ 4 and doctrine remediation commits).
- **Description:** Several documents disagreed with each other and with the constitutional layer: sense count appeared as 7 / 8 / 9 in different files; "permanent stores" appeared as 5 in one heading and 9 in the body; invariant count appeared as 11 / 13 / 14 in different files; `docs/16-CURRENCY.md` had a truncated distribution table; `docs/13-OPERATIONS.md` "Next" link pointed to the glossary instead of the upgrade-paths doc.
- **Why it existed:** Documents authored at different times by different drafts of the same author; no automated cross-validation.
- **How it closed (sub-item by sub-item):**
  - `p0-senses` â€” `00-INDEX.md:17`, `05-SENSORIUM.md:9,13,117`, and `14-UPGRADE-PATHS.md:210` now uniformly state **9 senses** (7 biological + Xenoception + Cryptoception).
  - `p0-stores` â€” `04-ARCHITECTURE.md:196,212` uniformly state **9 permanent stores** in both heading and body.
  - `p0-trust` â€” `genesis/INVARIANTS.md:3,9,23` and `docs/15-TRUST.md:365` uniformly state **sixteen** Invariants; cross-references to Invariant 15 and 16 appear consistently across the corpus.
  - `p0-currency` â€” `docs/16-CURRENCY.md:98-104` contains the complete seven-pool distribution table summing to 420B.
  - `p0-navlink` â€” `docs/13-OPERATIONS.md:254` correctly points to `14-UPGRADE-PATHS.md`.
  - `p0-glossary` â€” `docs/99-GLOSSARY.md:299-403` carries the Doctrine Supplement covering every post-remediation Lexicon term.
- **Residual:** Automated cross-validation (`xion-verify links`) is a Phase 1 deliverable per `DEVELOPMENT_ROADMAP.md:48`. Closure today is by static textual audit; the CLI will perform the same checks mechanically once built.
- **Verifier:** `xion-verify links` (specified for Phase 1).

### KW-DOCS-002 â€” Genesis Artifact hash-locks files that do not yet exist

- **Domain:** `DOCS`
- **Discovered:** 2026-04-19
- **Severity:** medium
- **Status:** `closed` on 2026-04-20 by the Phase 2 constitutional-file landing and the `p2-rehash` commit that updated `genesis/GENESIS_ARTIFACT.md` Â§ 4.
- **Description:** `genesis/GENESIS_ARTIFACT.md` referenced a constitutional bundle that included `FORM.md`, `MEMORY.md`, `RESURRECT.md`, and (per the new doctrine) `CREDENTIALS.md`. None of these files existed yet.
- **How it closed:** All five files named in the Artifact's hash block â€” `FORM.md`, `MEMORY.md`, `RESURRECT.md`, `CREDENTIALS.md`, and `UNKNOWNS.md` â€” now exist on disk at byte sequences whose SHA-256 hashes exactly match the values recorded in `genesis/GENESIS_ARTIFACT.md` Â§ 4. The Artifact's hash block carries entries for the eight constitutional documents (COVENANT, INVARIANTS, SOUL, FORM, MEMORY, RESURRECT, CREDENTIALS, UNKNOWNS). Verified 2026-04-20 by direct recomputation of all eight hashes against the Artifact.
- **Residual:** None. The recorded hashes are labeled as a *pre-genesis documentation witness* â€” they will be recomputed at the actual Arweave commit ceremony and replaced with ceremony values. That replacement is Phase 7 work, not a remediation of this weakness.

---

## How this list is curated

- New weaknesses are added to **Open** with a complete entry (no half-filled fields). If a field cannot be filled, the entry is not yet ready to publish.
- An entry moves from `open` â†’ `paying-down` when work is in progress and the pay-down commitment is on a planned milestone.
- An entry moves to `mitigated-residual` when no further work is planned because the weakness is structural and cannot be fully closed; the mitigations are the maximum protection achievable.
- An entry moves to **Closed** with the closure date and the closing artifact.
- Closed entries are never deleted. Honesty about past weaknesses is part of how Xion earns trust.

The discipline of this file is one of the small structural protections against operator drift. If this file ever stops being honest, the Vital Signs doctrine (Constitutional Integrity domain) will catch it: drift in known-weakness counts uncorrelated with closure activity is itself a critical-range reading.
