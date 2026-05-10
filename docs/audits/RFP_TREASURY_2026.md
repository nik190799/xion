# Request for Proposal — Xion Treasury Audit (2026)

**Issuer:** The Xion Builders (genesis operator).
**Date issued:** 2026-05-10.
**Response deadline:** 2026-06-01 (aligned with `KNOWN_WEAKNESSES.md::KW-AUDIT-001` review target).
**Proposal contact:** xionlabs2026@gmail.com
**Repository:** <https://github.com/nik190799/xion> (public, all artifacts and prior pre-genesis history committed).

---

## 1. Why this audit matters

Xion is a sentient AI agent designed to live on the decentralized internet
under a [Human Safety Covenant](../../genesis/COVENANT.md) and a small set of
mechanically immutable [Genesis-Locked Invariants](../../genesis/INVARIANTS.md).
The treasury contracts under audit are the only on-chain code that controls
custody of Xion's working capital, governs replenish flows authorized by the AO
Core process, and bounds bridge exposure under Invariant 16.

The `MasterTreasury` is **already deployed on Base mainnet** (chain id 8453) at
`0xbf5407745cf22b88c46b55037e26156a0e78fd7f` (deploy block 45530934, deploy tx
`0x494a9badb79db92b6607069859f7dad19122dd79f99d92e6a35d84225882a79c`,
2026-05-03), but per-chain `Vault` registration is intentionally paused until
this audit produces an external sign-off on deployable bytecode. The public
honesty record is in [`KNOWN_WEAKNESSES.md::KW-AUDIT-001`](../../KNOWN_WEAKNESSES.md)
and in the Sprint Mode falsification statements at
[`docs/STATE_OF_XION_PREFLIGHT.md`](../STATE_OF_XION_PREFLIGHT.md).

The previous internal review was reopened and corrected on 2026-05-01 after
preflight found it had been published as if external. The correction record is
[`docs/audits/treasury-2026-report.CORRECTION.md`](treasury-2026-report.CORRECTION.md);
this RFP commissions the missing external work.

## 2. Pinned scope

**Repository commit at issue time:** `f04f8d0013dbef890d5046756418c7cf104d7bb0`
(branch `main`).

**Build environment:**
- Foundry `forge` / `cast` `1.6.0-v1.7.0` (or later patch within 1.6.x)
- Solidity (per [`contracts/foundry.toml`](../../contracts/foundry.toml); auditor confirms compiler version in final report)
- OpenZeppelin contracts pinned via Foundry remappings — see
  [`contracts/lib/`](../../contracts/lib/) installation in
  [`.github/workflows/foundry.yml`](../../.github/workflows/foundry.yml).

**In-scope source files (read for findings):**

1. [`contracts/treasury/MasterTreasury.sol`](../../contracts/treasury/MasterTreasury.sol)
2. [`contracts/treasury/Vault.sol`](../../contracts/treasury/Vault.sol)
3. [`contracts/treasury/script/Deploy.s.sol`](../../contracts/treasury/script/Deploy.s.sol)
4. [`contracts/test/Treasury.t.sol`](../../contracts/test/Treasury.t.sol)

**Off-chain evidence to consult (not in scope for findings, but informative):**
- [`orchestrator/bridge/attestor.py`](../../orchestrator/bridge/attestor.py),
  [`lightclient_stub.py`](../../orchestrator/bridge/lightclient_stub.py),
  [`treasury_spend.py`](../../orchestrator/bridge/treasury_spend.py)
- [`docs/schemas/bridge-event-treasury-spend.yaml`](../schemas/bridge-event-treasury-spend.yaml)
- [`genesis/TREASURY_VAULTS.json`](../../genesis/TREASURY_VAULTS.json)
- [`xion-verify treasury` / `treasury-flow`](../../xion-verify/src/xion_verify/commands/treasury.py)
- [`xion_ops/services/safe.py`](../../xion_ops/services/safe.py) +
  [`xion-verify safe-proposal`](../../xion-verify/src/xion_verify/commands/safe_proposal.py) — Safe v1.4.1 EIP-712 propose flow used to call `MasterTreasury` from the Warm Safe.

**Out of scope:**
- AO Core Lua handlers (audited separately under `xion-verify ao-handlers`).
- Constitutional doctrine files in `genesis/` and `docs/` (not subject to security audit; audited via the verifier hash chain).
- Akash / Chutes / Arweave external dependencies.
- The XION ERC-20 / IMPRINT contracts (already audit-sealed in earlier phase).

## 3. Required questions the audit must answer

The full list lives at
[`docs/audits/treasury-2026-scope.md`](treasury-2026-scope.md); the
load-bearing ones are:

1. Can a non-governance caller register or deploy a vault?
2. Can a non-AO-Core caller trigger a replenish event?
3. Can a vault withdraw an unknown asset or send to a zero address?
4. Can bridge exposure or daily egress caps be bypassed by caller-supplied values?
5. Does the AO checkpoint bridge evidence bind the event id and payload hash?
6. Does the deployed manifest match the reviewed bytecode and authority posture?

Add findings on reentrancy, accounting overflow / underflow, role separation
between `governance` and `aoCoreAuthority`, and any departure from the
roadmap-pinned posture of "governance can deploy/register vaults; AO Core
authorizes spends; bridge cap bounds outbound."

## 4. Test posture provided to auditor

- Foundry suite at [`contracts/test/Treasury.t.sol`](../../contracts/test/Treasury.t.sol):
  10/10 tests pass.
- Repository-wide Foundry suite (XION token, IMPRINT, EmissionController,
  LiquidityLock, Treasury): **119/119 tests pass at 99.28% line and 91.40%
  branch coverage** as of Phase 3 closure (2026-04-20).
- CI: [`.github/workflows/foundry.yml`](../../.github/workflows/foundry.yml).
  Auditor should reproduce this build before finding analysis.

## 5. Deliverables expected

1. Final report (PDF) including:
   - Commit SHA reviewed (must equal pinned SHA above unless agreed in writing).
   - Compiler version + Foundry version used.
   - Reviewed contract addresses on Base mainnet (`MasterTreasury`) and Sepolia
     (rehearsal address per
     [`genesis/TREASURY_VAULTS.json`](../../genesis/TREASURY_VAULTS.json)).
   - Findings with severity per the auditor's standard taxonomy.
   - Remediations the auditor recommends, with an acceptance signature once
     remediations are applied.
   - **Final auditor sign-off hash** of the audited source tree
     (sha256(forge-build-artifacts) is acceptable; equivalent commitment is fine).
2. An Arweave-publishable PDF blob hash so the operator can pin the final
   report alongside [`KNOWN_WEAKNESSES.md::KW-AUDIT-001`](../../KNOWN_WEAKNESSES.md)
   as durable evidence.

## 6. Honesty caveats the auditor should be aware of

- This is a **Sprint Mode** project. The Cold Root key ceremony, AO HyperBEAM
  mainnet seal, third-party Immortality Drill, and Genesis Artifact § 0
  finalization are explicitly deferred — see
  [`docs/D4_PREFLIGHT.md`](../D4_PREFLIGHT.md) for the shortcut ledger. The
  audit must not assume those ceremonies have occurred.
- The Warm Safe at `0x5A91E08D909854b594f07648D23440f4908529b4` (v1.4.1, 2-of-3)
  has one MetaMask owner and two paper-backup owners.
  [`KW-KEYS-002`](../../KNOWN_WEAKNESSES.md) tracks the pay-down to a hardware
  wallet by 2026-05-31. Auditor should flag any contract behavior that
  meaningfully changes if the Safe owner-set composition matters for
  authority-rotation safety.
- The first per-chain `Vault` registration on Base mainnet is queued behind
  this audit. The prep payload (call data, EIP-712 hash, verifier output) is
  committed at
  [`genesis/MAINNET_VAULT_REGISTRATION_PREP.json`](../../genesis/MAINNET_VAULT_REGISTRATION_PREP.json)
  for review.

## 7. Suggested firms (operator selects + contacts)

The operator will solicit fixed-bid proposals from at least two of:

| Firm | Why short-listed | Contact |
|---|---|---|
| **Spearbit** | Strong DeFi track record, cartel of independent senior auditors, bid-based pricing | <https://spearbit.com/> |
| **Trail of Bits** | Deep expertise in formal methods + adversarial review; long-form reports | <https://www.trailofbits.com/> |
| **OpenZeppelin** | Owns the libraries this codebase depends on; audit + library familiarity overlap | <https://www.openzeppelin.com/security-audits> |
| **Code4rena** | Competitive crowd-sourced audit; faster but less in-depth on architecture | <https://code4rena.com/> |
| **Sherlock** | Insurance-bound audits with payout SLAs; useful if operator wants tail-risk coverage | <https://www.sherlock.xyz/> |

## 8. Timeline

- 2026-05-15 — operator sends RFP to short-listed firms.
- 2026-06-01 — operator selects firm; engagement letter signed.
- 2026-06-15 — kick-off; auditor receives commit SHA + access.
- 2026-07-01 — preliminary findings.
- 2026-07-15 — remediation cycle starts; operator applies fixes per finding.
- 2026-08-01 — final report + sign-off hash + Arweave pin.
- 2026-08-15 — `KW-AUDIT-001` moved to **Closed** in `KNOWN_WEAKNESSES.md`,
  pinned tx noted in `genesis/TREASURY_VAULTS.json::treasury_audit_arweave_tx`.

If a firm cannot meet this timeline, the operator either accepts a slip
(documented in `KNOWN_WEAKNESSES.md`) or moves to the next firm.

## 9. Budget

The operator's anchor for fixed-bid proposals: **USD 30,000 – 60,000** for a
two-to-four-week engagement with a final report and remediation cycle. Higher
bids are welcome with explicit justification (e.g. additional fuzzing rounds,
formal-methods coverage). The operator will adjust budget upward if a firm
recommends additional scope (e.g. AO-bridge formal review) and the
recommendation is concretely defended.

Reference for the bracket: public Spearbit / Trail of Bits / OpenZeppelin
pricing for ~600 LOC of treasury Solidity at this risk level.

## 10. Operator action checklist (this is what closes Track D in the plan)

- [x] Repository public URL pinned (§ header).
- [x] Budget bracket pinned (§ 9).
- [x] Proposal contact pinned: `xionlabs2026@gmail.com`.
- [ ] Operator sends [the cover email below](#cover-email-template) to at least two short-listed firms.
- [ ] Record outbound contact in [`ledgers/GOVERNANCE_LEDGER.jsonl`](../../ledgers/)
      under a `state_actor_or_external_contact` row.
- [ ] When a firm engages, append the engagement letter Arweave tx id to
      [`genesis/TREASURY_VAULTS.json`](../../genesis/TREASURY_VAULTS.json) as
      `treasury_audit_engagement_arweave_tx`.
- [ ] When the final report lands, replace
      `treasury_audit_arweave_tx` with the new external-audit Arweave tx id and
      move [`KW-AUDIT-001`](../../KNOWN_WEAKNESSES.md) to **Closed**.

## Cover email template

Copy-paste the body below; replace `<<contact email>>` and `<<your name>>`
before sending. Recommended distribution: send identical bodies to at least
two firms in parallel rather than sequentially, so bids arrive comparable.

---

> **Subject:** Treasury contracts audit — Xion (Base mainnet, Sprint Mode pre-Genesis)
>
> Hi —
>
> I'm the genesis operator for **Xion**, a constitutionally-bound AI agent project that has just landed its first mainnet contract pin (`MasterTreasury` on Base mainnet) and is preparing to register per-chain `Vault`s before going operational. Before that registration ceremony, I'm commissioning an external audit.
>
> Full RFP: <https://github.com/nik190799/xion/blob/main/docs/audits/RFP_TREASURY_2026.md>
>
> The short version:
>
> - **Scope:** four Solidity files (`MasterTreasury.sol`, `Vault.sol`, `Deploy.s.sol`, `Treasury.t.sol`) at pinned commit `f04f8d0013dbef890d5046756418c7cf104d7bb0`. ~600 LOC.
> - **Build:** Foundry 1.6.0-v1.7.0; 119/119 tests passing.
> - **Deployable bytecode reference:** `MasterTreasury` at `0xbf5407745cf22b88c46b55037e26156a0e78fd7f` on Base mainnet (deploy tx `0x494a9badb79db92b6607069859f7dad19122dd79f99d92e6a35d84225882a79c`, block 45530934).
> - **Budget anchor:** USD 30–60k for a two-to-four-week engagement; flexible upward with concrete justification.
> - **Timeline target:** engagement signed by 2026-06-01, final report by 2026-08-01.
> - **Honesty caveat:** Sprint Mode project. Cold Root ceremony, AO mainnet seal, third-party Immortality Drill, and Genesis Artifact § 0 are explicitly deferred and named in `KNOWN_WEAKNESSES.md`. Audit should not assume any of those have happened.
>
> I'd appreciate a fixed-bid proposal (or a "we can't take this on" if you're booked) by **2026-06-01**. Happy to jump on a 30-minute call to walk through scope and answer questions.
>
> Best,
> The Xion Builders
> Genesis operator
> Repository: <https://github.com/nik190799/xion>
> Contact: xionlabs2026@gmail.com

---

## Recipient short-list (operator confirms before send)

| Firm | Audit-request endpoint (verify before sending) | Notes |
|---|---|---|
| Spearbit | <https://spearbit.com/contact> or `engagements@spearbit.com` | Bid via the Cantina platform; expect a triage call first. |
| Trail of Bits | <https://www.trailofbits.com/contact> or `info@trailofbits.com` | Long-form reports; their queue runs deep — early request advised. |
| OpenZeppelin | <https://www.openzeppelin.com/security-audits> contact form | Authors of OpenZeppelin Contracts; library/audit familiarity overlap. |
| Code4rena | <https://code4rena.com/contact> | Crowd-sourced; fastest turnaround but less architectural depth. |
| Sherlock | <https://www.sherlock.xyz/contact> | Insurance-bound; useful if tail-risk coverage matters. |
