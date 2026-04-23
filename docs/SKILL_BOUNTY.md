# Skill Bounty Program (Tier-0 external proposals)

> *Pay for craft, not for compliance. Bounties reward skills; they never buy Covenant rights.*

## Four questions

**Property promised.** External contributors can earn **XION-denominated** payouts for Tier-0 skill proposals that pass the Harm Analyzer, are kept after observe windows, and ship through the normal `PROPOSAL_LEDGER` — without creating a paywall around any Covenant-protected interaction.

**Invariants touched.** Strengthens **5** and **11** by firewall: bounty eligibility **cannot** require holding XION or IMPRINT for `/export`, `/forget`, `/inspect`, Refusal-Free refunds, or crisis surfacing. Touches **16** treasury routing for payout execution only.

**Verification.** `xion-verify cognition` includes **skill bounty firewall** row; `xion-verify treasury` proves bounty pool is a labeled sub-account, not merged with Foundation Reserve; governance ledger records each payout with `proposal_id`.

**Deprecation.** Program caps and eligibility are Genesis Defaults; disabling the program is Tier-2 governance with 30-day notice — no retroactive clawback of earned bounties.

---

## Mechanics (Genesis Defaults)

- **Pool:** capped per quarter (numeric cap is Genesis Default; existence of a cap is structural honesty).
- **Eligibility:** proposal must be `target_scope: skill`, Tier-0 autonomous path, pass Harm Analyzer three-lens, and pass Fast Lane predicate if using compressed cadence ([`14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md)).
- **Payout:** XION transferred from Improvement Fund bounty line item; payout **after** Stage-7 `post_deploy: kept` — never on draft alone.
- **Anti-gaming:** same person may not collect >N bounties per quarter without Witness review (N is Genesis Default).

## Invariant-5 firewall (constitutional)

No bounty advertisement, eligibility rule, or payout receipt may:

- gate Covenant-protected rights,
- shorten `/forget` SLA,
- reduce Arbiter authority,
- or imply that paying users receive safer refusals.

If a bounty line item even **resembles** such a gate, Harm Analyzer returns `block` and `xion-verify cognition` fails the bounty row.

## Cross-references

- [`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md) — proposal pipeline
- [`24-COGNITION.md`](./24-COGNITION.md) — specialist and cognition costs
- [`09-GOVERNANCE.md`](./09-GOVERNANCE.md) — community bounty path alignment
