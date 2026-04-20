# Abdication — Date-Anchored Operator Authority Diminishment

> *"The single most trust-earning thing the founder of a system can do is publish, in advance, the dates on which the founder will lose authority — and then mechanically lose it on those dates."*

This document specifies the **Abdication Schedule**: the date-anchored, on-chain reduction of the Operator's authority over Xion. It is paired with the **Operator-Dependency Taxonomy**, which classifies every place where Xion currently depends on the Operator and the migration target for each dependency.

**Status:** New doctrine. References [`docs/15-TRUST.md`](./15-TRUST.md) (Founder Abdication section) and [`docs/16-CURRENCY.md`](./16-CURRENCY.md) (Genesis Honor pool tied to abdication milestones). Operator-Dependency Taxonomy is the input to the [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md) Operator-Dependency vital sign.

---

## Part I — Why Abdication Is Constitutional

A being designed to outlive its founder must, by definition, become unable to require its founder. If the founder remains structurally necessary forever, the being is not a being — it is a project with a perpetual benevolent dictator, and benevolence does not survive the dictator.

The Abdication Schedule is the structural answer:

- It commits the founder to specific dates by which specific authorities are surrendered.
- It encodes those dates on-chain so that they are mechanical, not promissory.
- It ties the Genesis Honor token vest (see [`docs/16-CURRENCY.md`](./16-CURRENCY.md) Part III) to milestone completion, so that the founder's economic interest is aligned with abdicating *on schedule*, not with extending influence.
- It maps every operator-only authority to a successor mechanism (governance, AO Core handler, Witness consensus, multisig lattice) so that the surrender is not a power vacuum but a transfer.

A founder who cannot point to the date their authority ends has not designed a being. They have designed a court.

---

## Part II — The Schedule

The Abdication Schedule is encoded in the AO Core as a sequence of dated milestones. Each milestone is a tuple of `(date, authorities_surrendered, successor_mechanism, verifier_check)`. The schedule is hash-locked into [`genesis/GENESIS_ARTIFACT.md`](../genesis/GENESIS_ARTIFACT.md) at genesis. After genesis, the schedule can be **accelerated** by the Operator (the Operator may surrender authority earlier than promised) but never **delayed**: the AO Core enforces the dates as latest-by, not earliest-by.

```
Genesis (T = 0)
  - Operator holds: Cold Root key (one share of 2-of-3 software-Shamir),
                    Relay deployment authority,
                    Credential Vault unlock authority (one share of 2-of-3),
                    Crypto Migration emergency-veto authority,
                    All Tier-3 governance proposal sponsorship.

T + 6  months  (Milestone M1):
  - Surrender: Relay deployment authority moves to AO Core's
               provision-relay handler (see docs/20-PROVISIONING.md).
               Operator retains observation/audit rights.
  - Successor: AO Core + governance Tier-2 ratification per provision.
  - Verifier:  xion-verify abdication-status M1
               checks the on-chain handler is live and the operator
               key is no longer in the relay-authorization set.
  - Genesis Honor:  Tranche M1 unlocks if check passes.

T + 12 months  (Milestone M2):
  - Surrender: Solo Operator's veto on Crypto Migration becomes
               2-of-3 with at least one Witness signer required.
  - Successor: Witness Protocol (see docs/15-TRUST.md Part II) +
               Operator + one elected community member, k-of-n.
  - Verifier:  xion-verify abdication-status M2
               checks the migration-veto authority set on-chain
               matches the new lattice.
  - Genesis Honor:  Tranche M2 unlocks if check passes.

T + 18 months  (Milestone M3):
  - Surrender: Credential Vault unlock authority moves from
               2-of-3 (Operator + 2 deputies) to 3-of-5
               (Operator + 2 deputies + 2 elected community
               custodians). Operator becomes one share of five.
  - Successor: Custodian election via Tier-2 governance.
  - Verifier:  xion-verify abdication-status M3.
  - Genesis Honor:  Tranche M3 unlocks if check passes.

T + 24 months  (Milestone M4):
  - Surrender: Operator's unilateral emergency-pause authority
               retires entirely. Pause requires 2-of-3 cosign
               (Operator + 2 elected emergency responders).
  - Successor: Elected Emergency Response cohort (3 members,
               Tier-2 election, 12-month rotating terms).
  - Verifier:  xion-verify abdication-status M4.
  - Genesis Honor:  Tranche M4 unlocks if check passes.

T + 36 months  (Milestone M5):
  - Surrender: Operator's public key retires from ALL operational
               roles. Operator becomes, formally, an ordinary
               community member with no special authority.
               Operator may continue to author proposals, vote,
               run a Witness node — like any other member.
  - Successor: Each previously-Operator-held authority now sits
               with the elected/AO-Core-handler successor named
               in M1 through M4.
  - Verifier:  xion-verify abdication-status M5
               checks the Operator key is in zero authorization sets.
  - Genesis Honor:  Tranche M5 unlocks if check passes.
                    Total Genesis Honor pool fully released
                    only at this point. Any unmet earlier
                    milestone results in the corresponding tranche
                    returning to Treasury (see docs/16-CURRENCY.md).

T + 48 months  (Milestone M6 — Hard Cutover):
  - If Milestone M5 has not been mechanically achieved by this date,
    AO Core automatically rotates the Operator role using the
    pre-approved succession pool (declared at genesis, refreshed
    annually by Tier-3 governance).
  - The Operator's keys are removed from every authorization set
    by AO Core handler, with no further action required.
  - This is the structural insurance: even if the Operator
    refuses to abdicate, the Operator stops being the Operator
    on M6 by mechanism, not by negotiation.
```

**Year 10 Cold Root (Genesis Default anchor, rolling governance window).** Between **M5** and the long-horizon custody plan, governance may schedule migration of Cold Root Shamir custody to **community-elected custodians** using an **IMPRINT-weighted** vote (never XION-weighted — avoids buying structural resurrection power). Target anchor: **~Year 10 from genesis**, adjustable by Tier-3 vote within ±6 months unless lengthened for safety.

**Constitutional Floor (cadence).** No milestone may be delayed past its T+N date by any governance action. The dates are mechanical. The Operator may *accelerate* the schedule by voluntarily surrendering an authority earlier; this is logged on-chain as `abdication_acceleration(milestone, original_date, actual_date)` and unlocks the corresponding Genesis Honor tranche on the *original* date (not earlier — there is no economic reward for accelerating, only honor).

---

## Part III — Operator-Dependency Taxonomy

Every place where Xion currently depends on the Operator must be classified, named, and mapped to a successor mechanism. This is the **Operator-Dependency Taxonomy** — a structural inventory that the [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md) Operator-Dependency vital sign measures against.

### Classification

Each dependency is one of:

- **CRITICAL** — Xion cannot operate without the Operator performing this task. (Genesis state: maximum.)
- **DEGRADED** — Xion can operate without the Operator, but with reduced capability or longer recovery time.
- **OPTIONAL** — The Operator can perform this task if available, but Xion has a complete substitute mechanism.
- **RETIRED** — The Operator no longer holds this authority at all.

The Operator-Dependency vital sign measures the **count and weight** of CRITICAL and DEGRADED dependencies over time. The trajectory must be monotonically decreasing across the Abdication Schedule, with the goal of zero CRITICAL dependencies by M5 and a small, well-named set of DEGRADED dependencies persisting until they too can be retired.

### Genesis Inventory (T = 0)

This is the inventory at genesis. The full table — with current status, target migration milestone, and successor mechanism — lives in `OPERATOR_DEPENDENCIES.md` (machine-readable; produced and updated by `xion-verify operator-dependencies`).

| Dependency | Genesis Class | Target Class by | Successor Mechanism |
|---|---|---|---|
| Cold Root key custody (1 of 2-of-3 software-Shamir) | CRITICAL | M3 → DEGRADED, M5 → OPTIONAL | 3-of-5 distributed custodians |
| Relay deployment | CRITICAL | M1 → RETIRED | `provision-relay` AO handler |
| Credential Vault unlock | CRITICAL | M3 → DEGRADED | 3-of-5 custodian lattice |
| Crypto Migration veto | CRITICAL | M2 → DEGRADED | k-of-n Witness lattice |
| Tier-3 proposal sponsorship | CRITICAL | M5 → RETIRED | Any IMPRINT-eligible member |
| Emergency pause | CRITICAL | M4 → DEGRADED | Elected Emergency Response cohort |
| Akash deployment account funding | CRITICAL | M1 → DEGRADED, M3 → OPTIONAL | AO Core treasury → `provision-relay` flow |
| Vapi/Twilio commercial agreement signature | CRITICAL | M2 → DEGRADED | Foundation legal entity (post-genesis +6mo) |
| LLM provider API account ownership | CRITICAL | M1 → DEGRADED | Foundation entity + per-provider rotation |
| Domain name registration & DNS | CRITICAL | M1 → DEGRADED, M2 → OPTIONAL | Multi-jurisdictional Foundation custody + ENS/Handshake fallback |
| Cloudflare account (if used) | CRITICAL | (must be RETIRED before genesis) | Direct Akash / multi-PoP / Tor onion + IPNS |
| TLS certificate management | CRITICAL | M1 → DEGRADED | ACME automation + Foundation backup |
| GitHub repository ownership | CRITICAL | M2 → DEGRADED | Foundation org + Arweave-mirrored authoritative copy |
| Code signing key (release artifacts) | CRITICAL | M2 → DEGRADED | 3-of-5 release-signers cohort |
| Genesis Honor pool authorial decisions | CRITICAL | M5 → RETIRED | Schedule fully published; no further decisions to make |
| Public dashboard hosting | DEGRADED | OPTIONAL by M3 | Multi-mirror + IPFS + Arweave snapshot |
| Initial Witness recruitment | CRITICAL | OPTIONAL by M2 | Permissionless Witness join via published bond |
| Hardware token custody for Cold Root | CRITICAL (post-V1) | DEGRADED by M3, OPTIONAL by M5 | Multi-jurisdictional custodian distribution |
| Operator Discord/Telegram/community presence | DEGRADED | OPTIONAL by M2 | Community moderators (elected) |
| Bug-report intake | CRITICAL | OPTIONAL by M2 | Public ledger + bounty intake handler |

### Discovery Discipline

The taxonomy is **append-only and auto-updated**. Any change to Xion's substrate that introduces a new Operator dependency must be captured by `xion-verify operator-dependencies discover` and surfaced in the next Trust Scorecard refresh. Failing to capture is itself logged as a `KW-OPS-*` known weakness ([`KNOWN_WEAKNESSES.md`](../KNOWN_WEAKNESSES.md)).

The full enumeration methodology — how `xion-verify` walks the substrate to find dependencies — is part of the methodology hash published with each release (see [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)).

---

## Part IV — Verification

### Per-milestone

`xion-verify abdication-status M<n>` checks:

1. The on-chain authority set for each authority surrendered at M<n> matches the `successor_mechanism` declared.
2. The Operator's public key is *not* in any authorization set it was supposed to leave.
3. The Genesis Honor tranche for M<n> has either unlocked (milestone met) or returned to Treasury (milestone missed).
4. The methodology hash matches the genesis-locked Abdication Schedule hash.

If any check fails, `xion-verify` returns a hard failure and the failure surfaces on the public dashboard until resolved.

### Schedule integrity

`xion-verify abdication-schedule` confirms:

- The schedule hash on-chain matches the schedule hash in [`genesis/GENESIS_ARTIFACT.md`](../genesis/GENESIS_ARTIFACT.md).
- Milestone dates are unchanged from genesis (no delay possible).
- All `abdication_acceleration` events on-chain are well-formed and correctly tied Genesis Honor tranches to original dates.

### Operator-Dependency vital sign

`xion-verify operator-dependencies` (called by [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)):

1. Walks the published taxonomy and produces a current count of CRITICAL / DEGRADED / OPTIONAL / RETIRED entries.
2. Compares each entry to its target class for the current Abdication Schedule milestone.
3. Reports any entry that is *behind* its target (e.g., still CRITICAL when target was DEGRADED by now) as a vital-sign red.
4. Flags any newly-discovered dependency not yet classified.

The vital-sign band is published in [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md) and is one of the eight load-bearing sustainability dimensions.

---

## Part V — Why NOT Alternatives

**Why not "the Operator decides when to step down"?** Because the entire point is to remove the decision from the Operator. A founder who can choose when to stop being the founder is, in practice, the founder forever — no matter how sincere the intention. The dates are mechanical because trust requires they be mechanical.

**Why not a single one-shot abdication?** Because abrupt power vacuums kill systems. The graduated schedule lets each successor mechanism prove itself before the next surrender. M1 (Relay deployment) is the cheapest to reverse; M5 (full retirement) is the most consequential. By M5, every successor has had years of operation under partial Operator backstop.

**Why not "abdication is voluntary, but the Genesis Honor pool punishes failure"?** Because economic punishment of an unmet abdication still leaves the Operator in the seat. The Genesis Honor mechanism is the *aligned-incentive* layer. The on-chain authority transfer at each milestone is the *structural* layer. Both must exist; neither alone is enough. The hard cutover at M6 is the *insurance* layer for the case where both fail.

**Why not "let governance set the schedule"?** Because at genesis, governance does not yet exist in mature form. The schedule must be the founder's pre-commitment, made before there is anyone with the standing to negotiate it down. That is its trust-earning property.

**Why IMPRINT-weighted custodian election, not XION-weighted?** Root custody is a **trust** problem, not a **liquidity** problem. Weighting Cold Root votes by XION would let wealthy actors buy structural control of Xion's resurrection capacity. IMPRINT is slow, earned, and non-transferable — the least gameable on-chain signal available at Year 10.

**Why not "skip the Operator-Dependency Taxonomy and just track the visible authorities"?** Because the visible authorities are the easy part. The taxonomy exists to surface the *invisible* dependencies — the API key only the Operator knows, the AWS account whose payment method is the Operator's card, the GitHub org with one admin, the community Discord whose owner is the Operator — and to demand they each have a published successor. These are the silent killers. Most projects die not because the founder refuses to leave but because no one ever wrote down what would happen if they did.

---

## Part VI — Cross-References

- [`docs/15-TRUST.md`](./15-TRUST.md) Part II §Founder Abdication — the original doctrine.
- [`docs/16-CURRENCY.md`](./16-CURRENCY.md) Part III §Genesis Honor pool — the aligned-incentive layer.
- [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md) §Operator-Dependency vital sign — the measurement layer.
- [`docs/13-OPERATIONS.md`](./13-OPERATIONS.md) — runbooks updated per milestone.
- [`docs/14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md) Level 11 (Operators) — successor election mechanics.
- [`docs/20-PROVISIONING.md`](./20-PROVISIONING.md) — `provision-relay` handler successor mechanism.
- [`genesis/INVARIANTS.md`](../genesis/INVARIANTS.md) Invariant 12 — Genesis Honor vest respects the Abdication Schedule.
- [`KNOWN_WEAKNESSES.md`](../KNOWN_WEAKNESSES.md) — operator-dependency-related KW entries.
- `tools/xion-verify abdication-status`, `abdication-schedule`, `operator-dependencies` — the verification CLI commands.

---

*"The most generous thing a founder can give a being is the date on which the founder ceases to matter. The schedule is that gift. The verifier is how anyone, at any point, can check the gift was given in full."*
