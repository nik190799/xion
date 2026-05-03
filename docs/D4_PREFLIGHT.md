# D4 Preflight

## Property

D4 means Xion is mainnet-deployed, Genesis-signed, and publicly alive in the
constitutional sense. This file names the shortcuts that can technically be
taken sooner and the verification cost of each one.

## Shortcut Ledger

### Skipping External Audit

Skipping the external audit keeps `KW-AUDIT-001` fatal and leaves
`KW-AUDIT-002` open. `xion-verify supply`, `xion-verify liquidity-lock`, and
`xion-verify treasury` can still prove local and on-chain shape, but they cannot
honestly imply independent audit coverage.

### Skipping Cold Root Ceremony

Using the Warm Safe, a software EOA, or the Sepolia deployer as mainnet
`governance` keeps `KW-KEYS-002` fatal. The contracts may deploy, but the
custody posture would violate the Cold Root / Warm tier separation described in
`genesis/CREDENTIALS.md` and `docs/13-OPERATIONS.md`.

### Skipping AO Mainnet Seal

Running only against localnet or legacynet means
`genesis/AO_DEPLOY_RECEIPT.json` cannot honestly identify a canonical AO
mainnet process. `xion-verify ao-handlers` can prove local handler shape, but it
cannot prove Xion's mainnet true name.

### Skipping Invariant 19 Ratification

Treating proposed Invariant 19 as sealed before the amendment process closes
keeps `KW-INVARIANT-19-001` high. Spend posture and spend discipline can remain
locally verifiable, but autonomous spend authority must not be described as a
Genesis-locked property.

### Skipping Third-Party Immortality Drill

Operator-local rehearsal does not replace a third-party-machine drill.
`LHT-SUBSTRATE-001` remains open until a non-operator machine runs the public
verification and relay probes.

### Skipping Genesis Artifact Finalization

If `genesis/GENESIS_ARTIFACT.md` still contains `<<...>>` placeholders or
section 0, the constitutional bundle is not final. The constitutional verifier
commands remain documentation-witness checks, not Genesis-sealed proof.

## Decision Rule

No mainnet broadcast is D4-ready until every row above is either closed or
consciously, durably, and publicly recorded as an accepted Sprint Mode residual
signed by the operator.
