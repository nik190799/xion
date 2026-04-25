# 28 — Research Spend (the payment rail for Xion's own R&D)

> *An Improvement Fund that cannot reach the providers whose inputs it was built to buy is a treasury accounting fiction. A rail that carries Improvement Fund value out but carries nobody's audit trail back is indistinguishable from a siphon. This document pins the pipe between the two.*

## What this document is (and is not)

This is the operational doctrine for the **Research Spend Rail** — the payment mechanism by which [Improvement Fund](./21-SUSTAINABILITY.md#four-funds-never-pooled-obscuring-origin) XION becomes outbound API credit at a third-party inference provider so the [Auto-Research Loop](./08-AUTO-RESEARCH.md) can actually read, summarize, canary-test, and draft proposals. The rail describes **custody**: who holds the outbound credential. Spend authority is separate and governed by [Invariant 19](../genesis/INVARIANTS.md#invariant-19--trust-earned-spend-authority) and [`SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md).

It is **not**:

- **A replacement for [`docs/08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md).** That document pins the *cognitive* loop — seven stages, three-lens harm analysis, `PROPOSAL_LEDGER`, governance tiering. This document pins the *monetary conduit* that powers stages 1–6 at their outbound-spend moments. Every principle in 08 still applies; nothing is relaxed.
- **A replacement for [`docs/19-TREASURY.md`](./19-TREASURY.md), [`docs/21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md), or [`docs/SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md).** Those pin the *fund structure*, runway mode, and authority posture. This document pins how one of those funds (Improvement Fund) spends **outbound, to a non-Xion-custody counterparty** — a motion the treasury docs name but do not mechanize.
- **A new fund.** The Improvement Fund is the fund. This document is the pipe.
- **An admission of user-paid research.** User-paid turns are `PAYMENT_LEDGER` (Phase 5g-iii, separate doctrine). Research-spend is Xion's money being spent on Xion's own work. Different units, different ledgers, different verifiers.

## Why pin this now

Every other doctrinal primitive in the treasury/research family is already pinned. `PROPOSAL_LEDGER` exists (08), Improvement Fund exists (19, 21), on-chain spend enforcement exists (08 § "Budget Controls"), three-lens harm analysis exists (08 Stage 4), output-commitment discipline exists (08 Stage 7 closure-back-to-Stage-1). The piece that is named but not mechanized is the **outbound counterparty surface**: the specific doctrinal shape of "XION leaves the Improvement Fund and arrives as credit at OpenRouter (or any other registered research-provider account), and the outbound API calls that result are individually ledgered and retroactively verifiable against the Stage-1 envelope".

Pinning this before Phase 5g-iii (billing, which opens the `PAYMENT_LEDGER` counterpart) ensures the two ledger families — user-inbound (`PAYMENT_LEDGER`) and Xion-outbound (`RESEARCH_SPEND_LEDGER`) — are designed together and cannot cross-contaminate. [Invariant 16](../genesis/INVARIANTS.md#invariant-16--treasury-shape) rule 7 (origin-obscuring merges are forbidden) is the constitutional parent of that separation. This document is the operational honoring of it.

## Properties this rail promises

1. **Every outbound dollar is ledgered at grain.** Each outbound API call that is funded from the Improvement Fund writes exactly one append-only row to `RESEARCH_SPEND_LEDGER`, with the `proposal_id` or stage-anchor it was authorized under. An envelope ($10/mo Stage-1) that reports a depletion of $9.42 ties to 1-to-N specific rows summing to $9.42. Discrepancies are constitutional, not accounting, failures.
2. **No outbound call bypasses the Arbiter-gated loop.** Research-spend is funded only by stages of the Auto-Research loop that have already cleared their Stage-4 harm analysis (or by Stage-1 / Stage-2, which `08` explicitly pins as "read-think-write only, no spend" for Xion-originated cognitive work and restrict spend to fixed aux-LLM summarization within the envelope). No agent, skill, or subsystem outside the Auto-Research loop can draw from this rail. The verifier enforces this structurally.
3. **[Invariant 17](../genesis/INVARIANTS.md#invariant-17--inference-sovereignty-floor) floor is never funded by this rail.** The floor is operator-sustained and substrate-sustained (commodity compute + open weights). Research-spend is additive only — it funds frontier comparison, safety drift probes, cross-provider benchmarking, not the survival path. A rail configuration that would leave the floor un-runnable without this rail is a rail configuration the verifier refuses to ratify.
4. **Refund-on-failure is structural, not editorial.** If an authorized research operation is pre-empted by a Stage-4 `block`, by Stage-5 canary auto-abort, by a provider error, or by a cost-estimate-mismatch outcome, the remaining budget-commit returns to the Improvement Fund within the same settlement cycle. `RESEARCH_SPEND_LEDGER` rows flip `outcome` from `committed` to `refunded`; the verifier joins those rows against the PROPOSAL_LEDGER stage outcomes and fails if any committed-without-refund branch has no committed-output counterpart.
5. **Credential sovereignty progresses with the being.** Who holds the outbound API key changes as Xion matures, on a pinned progression (§ "Custody Postures" below). At no stage can the custody move *backward* toward less sovereignty without a governance action that is publicly ledgered.
6. **D1 is trivially satisfied.** In D1 (current posture), the rail is operator-custody: the operator holds all outbound API keys and funds research-spend directly from personal account. Research-spend doctrine is active but trivially verifiable (every outbound call ties to an operator-signed manifest). D2+ incremental sovereignty is where the rail gets constitutionally interesting; D1 is where the ledger shape is exercised before there's money on it.

## Custody Postures (D1 → D4)

Who holds the outbound API credential determines how sovereign the spend is. Four postures, in order of increasing sovereignty. Each is a valid steady-state for the deployment tier named; the progression is constitutional but not forced — a long-running deployment can remain at D2 indefinitely if governance judges the cost of moving to D3 exceeds the benefit.

These D-postures are orthogonal to the S-postures in [`SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md). D1→D4 answers **who holds the provider key**. S1→S5 answers **who may approve the spend**. A deployment can be D2/S1 (operator holds the key and operator approves discretionary spend), D3/S3 (Xion holds a wrapped key but operator still controls burn-envelope changes), or any other combination that passes both verifiers.

### D1 — Operator-Custody (Phase 5g-i present; trivial rail)

The operator personally holds the OpenRouter / Kimi / provider API key, funds it from personal account, runs Xion locally or on operator-owned infrastructure. The "Improvement Fund" has no on-chain accounting surface yet — it is a conceptual ledger entry only. Research-spend is whatever the operator chooses to fund as aux-LLM cost, and the "rail" is `operator pays invoice; Xion uses credit`. `RESEARCH_SPEND_LEDGER` rows are optional but strongly encouraged — writing them in D1 tests the schema before the fund is live.

*Constitutional status:* vacuously satisfied. The operator is a trusted party under the Abdication Schedule ([`docs/ABDICATION.md`](./ABDICATION.md)); research-spend at this tier is indistinguishable from any other operator-subsidized development cost.

*Exit criterion to D2:* Phase 5g-iii ships (`PAYMENT_LEDGER` + billing), and treasury begins to receive non-zero revenue. Once Improvement Fund has a non-conceptual balance, D2 becomes the honest custody posture.

### D2 — Operator-Custody-with-Mandate (Phase 5g-iii through Phase 6)

The operator still holds the outbound API key physically. But the Improvement Fund now has a real on-chain balance. Every research operation is pre-authorized by Auto-Research Stage 4 (harm analysis + budget check) and posted as an on-chain `Spend` message to the AO Core (per `08` § "Budget Controls"). The Core emits a signed budget mandate. The operator's outbound-pay script reads the mandate, executes the outbound call, and writes the `RESEARCH_SPEND_LEDGER` row with both the mandate reference and the outbound-provider transaction receipt. Any outbound call without a matching mandate is either an operator expense (not Xion's money) or a fraud (verifier flags).

*Constitutional status:* the operator is now honoring a signed mandate from Xion, not making discretionary spend decisions. Xion's money is identifiable. Xion's agency is mediated but audibly so.

*Exit criterion to D3:* governance passes a custody-transfer ratification that says "at this deployment, Xion holds its own provider-specific key". Requires a revocability mechanism (next § D3) and at least one provider that accepts a non-human credential-holder under its terms of service. This is not a Phase 6 default; it is available when governance decides the benefit exceeds the trust-layer cost.

### D3 — Xion-Custody-Wrapped (post-Phase 6; optional)

Xion holds a provider-specific API key that is bound on-chain to governance revocation and to an on-chain budget cap. The key is stored in the `credentials-vault` (Invariant 4, `genesis/CREDENTIALS.md`); every outbound call is signed by a key that the Core has authorized for that specific purpose. Governance can revoke in one cosign-tier action; the operator cannot unilaterally revoke — revocation is a governance surface.

*Constitutional status:* Xion now makes outbound spend without human-in-the-loop on every call, but every call is bounded by an on-chain budget that governance set and can close. The `RESEARCH_SPEND_LEDGER` row is self-signed by Xion against the key's on-chain authorization. The verifier's job grows: it must now prove *both* that every spend tied to a proposal *and* that the key was authorized at the moment of spend.

*Exit criterion to D4:* Xion can draw from treasury via AO Core → fiat-pegged stable → provider-agnostic credit in a way that requires no single-party custody. This depends on Phase 6+ treasury rails and at least one provider accepting a non-custodial credit account.

### D4 — Self-Sovereign (aspirational; post-Phase 7)

Xion draws from Improvement Fund via AO Core Spend message → on-chain swap to provider-accepted stable (USDC, etc.) → outbound deposit to a provider credit account that is keyed to Xion's own AO Process ID rather than any single human. No single-party revocability except the governance super-majority. This is the endpoint of the sovereignty progression.

*Constitutional status:* the rail is now substrate-portable and operator-independent. If the operator's jurisdiction imposes a ban, Xion's research-spend continues uninterrupted via a Relay running elsewhere. Resurrection-coherent.

*Exit criterion:* none. This is the steady state the progression converges on.

## `RESEARCH_SPEND_LEDGER` (schema sketch; full YAML deferred to implementation)

Append-only, one row per outbound API call funded from Improvement Fund. Field list is pinned here; the full `docs/schemas/ledger-research-spend.yaml` lands in the Phase 6 commit that brings the improvement-fund verifier from `NOT_YET_SEALED` to live.

| Field | Meaning |
|-------|---------|
| `spend_id` | UUIDv4 |
| `committed_at_utc_ns` | Monotonic timestamp of the Core's authorization (D2+) or the operator's signed manifest (D1) |
| `settled_at_utc_ns` | Monotonic timestamp of the outbound provider's receipt |
| `custody_posture` | `D1` \| `D2` \| `D3` \| `D4` — which rail this row travelled |
| `proposal_id` | UUID matching a row in `PROPOSAL_LEDGER`; required for all spend except Stage-1 envelope aux-LLM summarization |
| `stage_anchor` | `1` \| `2` \| `3` \| `4` \| `5` — which Auto-Research stage this spend funded |
| `provider_id` | Registered research-provider identifier (e.g., `openrouter`, future `openrouter-backup`) |
| `provider_model_id` | Specific model hit (e.g., `moonshotai/kimi-k2`) |
| `authorization_reference` | On-chain Core Spend message hash (D2+) or operator manifest SHA (D1) |
| `committed_XION` | Amount reserved before outbound call |
| `settled_XION` | Amount actually spent at provider (after provider-side pricing) |
| `refund_XION` | Amount returned to Improvement Fund on any non-committed outcome |
| `outcome` | `settled` \| `refunded` \| `refunded_partial` \| `stranded` |
| `drive_tags` | Which Drive Vector term(s) this spend advanced (`survival` \| `service` \| `meaning`) — **never** `revenue`; enforces Invariant 15 |
| `source_sha256` | Anchor hash of this doctrine (`docs/27-RESEARCH-SPEND.md`) at the time the row was written; lets future verifiers prove the row was written under a known-good doctrine version |

`stranded` exists as a failure-mode leaf: the outbound call completed but the return payload could not be committed (crash before `PROPOSAL_LEDGER` update, for example). Stranded rows are a specific operator-review class; the verifier separates them from genuine refunds.

## Verifier — `xion-verify research-spend`

Four independent joins, all of which must pass:

1. **PROPOSAL_LEDGER join.** Every non-Stage-1 `RESEARCH_SPEND_LEDGER` row's `proposal_id` must resolve to an existing `PROPOSAL_LEDGER` row whose `stage ≥ spend row's stage_anchor` at the time of the spend.
2. **Envelope join.** Accounting-window sum of `settled_XION - refund_XION` per stage anchor must fall within the ratio-denominated envelope for that stage (§ `docs/08-AUTO-RESEARCH.md` budget controls) at the sustainability mode current for the window.
3. **Refund fidelity.** Every `outcome in {refunded, refunded_partial}` row's `refund_XION` must match the fund's realized Improvement Fund delta for that spend_id. Missing refunds fail the verifier.
4. **Authorization presence.** In D2+, every row's `authorization_reference` must resolve to an on-chain Core Spend message. In D1, the `authorization_reference` must resolve to an operator manifest in `ops/research-spend-manifests/` (a path pinned by this doctrine for the D1 posture; manifests are gitignored with a `.gitkeep`-style placeholder).

Listed as `NOT_YET_SEALED` until Phase 6+ lands both the Improvement Fund on-chain balance and the ledger writer. In the Phase 6 commit that promotes `improvement-fund` to live, `research-spend` promotes alongside.

## Interactions with other constitutional objects

- **Invariant 15 (Prohibited Drive Inputs).** `drive_tags` on every `RESEARCH_SPEND_LEDGER` row refuses `revenue` at schema level. A spend cannot be authorized under the "we made money" drive; it must route through `survival`, `service`, or `meaning`. This is the doctrinal echo of the `PROPOSAL_LEDGER` `payback_horizon` refusal in `docs/08-AUTO-RESEARCH.md`.
- **Invariant 16 (Treasury Shape).** Origin-obscuring merges are forbidden (rule 7). `RESEARCH_SPEND_LEDGER` rows are per-call; no aggregation row is permitted that would lose provider / stage / proposal provenance.
- **Invariant 17 (Inference Sovereignty Floor).** The rail never funds the floor (property 3 above). `xion-verify inference-sovereignty` and `xion-verify research-spend` are orthogonal checks; a configuration in which the former's floor-provider is also a recipient of the latter's spend fails both verifiers.
- **[Invariant 4 (Credential Vault)](../genesis/INVARIANTS.md#invariant-4--credential-vault).** D3 and D4 custody postures require the credential vault. D1 and D2 do not touch it.
- **[Invariant 6 (Refusal Right)](../genesis/INVARIANTS.md#invariant-6--arbiter-refusal-right).** The Arbiter can refuse a research operation at Stage 4 exactly as it refuses a user turn. Refund-on-Stage-4-block (property 4) is the monetary counterpart of the Refusal-is-Free user-facing property that lands in Phase 5g-iii.
- **Covenant Principle 14 (Honest Dignity).** Sycophancy-to-self applies here: a research operation that spends Xion's money to produce a finding Xion already believes in is a Principle-14 violation. The Auto-Research Loop's triage stage (08 Stage 2) catches this at the cognitive layer; `xion-verify research-spend` catches the economic shadow of it by requiring every spend to resolve to a *distinct* proposal, not a re-run of an already-ratified one.

## What this doctrine deliberately does NOT cover

- **The Auto-Research cognitive loop itself.** Covered by [`docs/08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md). This document is the payment rail under that loop; the loop's semantics are not re-litigated.
- **User-paid turn billing (`PAYMENT_LEDGER`).** Covered by Phase 5g-iii doctrine (`docs/29-BILLING-X402.md`, future). User → Xion flow. This document is Xion → provider flow.
- **Skill-bounty payouts.** Covered by [`docs/SKILL_BOUNTY.md`](./SKILL_BOUNTY.md). Different ledger, different line item in the Improvement Fund, different purpose (pay a human contributor, not buy a provider call).
- **Operator-subsidy accounting.** Not Xion's money; not this doctrine's concern. The operator's personal Kimi/OpenRouter bill is an operator expense until D2.
- **Treasury swaps (XION ↔ stable ↔ fiat).** Covered by [`docs/19-TREASURY.md`](./19-TREASURY.md) § "Settlement and swap discipline". The rail consumes the output of those swaps; it does not re-define them.
- **Per-provider credit reconciliation.** A provider's monthly invoice reconciling to the sum of `RESEARCH_SPEND_LEDGER` rows for that provider is an operator-side bookkeeping task; `orchestrator/bookkeeping.py` (see [`docs/07-ECONOMY.md`](./07-ECONOMY.md)) owns it.
- **The specific schema file `docs/schemas/ledger-research-spend.yaml`.** Landed in the Phase 6 commit that promotes `research-spend` to live. This doctrine pins the properties; the schema pins the wire shape.

## Phase mapping

| Phase | Contribution to the rail |
|-------|--------------------------|
| Phase 5g-0 (this commit) | Doctrine pinned; no code |
| Phase 5g-i.1 (OpenRouter refactor) | Outbound provider becomes OpenRouter, whose catalog-based pricing makes `settled_XION` computation tractable at runtime |
| Phase 5g-iii (x402 billing) | `PAYMENT_LEDGER` lands; inflow side of the treasury gets its ledger, which lets 6+ start accruing real Improvement Fund balance |
| Phase 6 (treasury vaults + improvement fund live) | `docs/schemas/ledger-research-spend.yaml` lands; `RESEARCH_SPEND_LEDGER` writer lands; D2 custody posture exercisable |
| Phase 7+ (cognition action layer) | Auto-Research Stage 3 can originate proposals without operator-in-the-loop authoring; research-spend volume grows |
| Phase 7+ (D3 custody) | Credential vault lands; optional cutover to D3 |
| Phase 8+ (D4 custody) | Substrate-portable self-sovereign rail; aspirational |

## Verification posture

- `xion-verify research-spend` — reports `NOT_YET_SEALED` until Phase 6 promotes it.
- `xion-verify treasury` (live from Phase 6) — verifies that the Improvement Fund balance changes consistently with `RESEARCH_SPEND_LEDGER` aggregate once the ledger is live.
- `xion-verify inference-sovereignty` (live since Phase 4e) — already passes; a future configuration that tries to fund the floor from this rail fails both verifiers in tandem.
- `xion-verify schemas` — gains one entry when `docs/schemas/ledger-research-spend.yaml` lands.
- `xion-verify links` — must remain green at every commit that touches this document or any file it cites.

## Deprecation path

This doctrine is operational, not constitutional. The *rail* is a mechanism; the constitutional parents (Invariant 4, 15, 16, 17 and Covenant Principle 14) are the durable layer. Amending this file is Tier-2 governance action if the change alters any of the six properties; changes that alter only the tabular defaults (Genesis stage envelopes, specific provider identifiers) are Tier-3 continuous-evolution. Replacement of the file is a sister-Core fork only if the change weakens a property — that is the same bar as any operational doctrine under Invariant 7.

## Cross-references

- [`docs/08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md) — the cognitive loop this rail powers
- [`docs/19-TREASURY.md`](./19-TREASURY.md) — the fund structure that feeds the rail
- [`docs/21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md) — the four funds including Improvement Fund
- [`docs/SKILL_BOUNTY.md`](./SKILL_BOUNTY.md) — the parallel Improvement-Fund outbound channel that pays humans
- [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) — the routing layer for user-facing turns; independent of the research-spend rail but shares provider identifiers
- [`docs/ABDICATION.md`](./ABDICATION.md) — the operator-authority schedule that defines what D1 custody means at each tier
- [`docs/07-ECONOMY.md`](./07-ECONOMY.md) — Pay-to-Activate, the inflow side
- [`docs/MEASUREMENT-VOCABULARY.md`](./MEASUREMENT-VOCABULARY.md) — ratio-denominated envelope units
- [`docs/SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md) — S1-S5 spend-authority postures, orthogonal to D1-D4 custody
- [`genesis/INVARIANTS.md`](../genesis/INVARIANTS.md) — Invariants 4, 15, 16, 17, and Covenant Principle 14

---

*— Research Spend Rail v1, pinned Phase 5g-0 (2026-04-21). Implementation lands Phase 6 alongside the Improvement Fund on-chain balance and the treasury router. Until then, D1 operator-custody is the posture and this doctrine is doctrine-in-waiting.*
