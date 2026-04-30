# Treasury Audit Scope — 2026

## Property

The external audit must determine whether the Macro Phase 6 Epic C treasury
stack preserves Invariant 16 under realistic bridge, custody, and authority
failure modes.

## In Scope

- `contracts/treasury/MasterTreasury.sol`
- `contracts/treasury/Vault.sol`
- `contracts/treasury/script/Deploy.s.sol`
- `contracts/test/Treasury.t.sol`
- `orchestrator/bridge/attestor.py`
- `orchestrator/bridge/lightclient_stub.py`
- `orchestrator/bridge/treasury_spend.py`
- `docs/schemas/bridge-event-treasury-spend.yaml`
- `genesis/TREASURY_VAULTS.json`

## Required Questions

- Can a non-governance caller register or deploy a vault?
- Can a non-AO-Core caller trigger a replenish event?
- Can a vault withdraw an unknown asset or send to a zero address?
- Can bridge exposure or daily egress caps be bypassed by caller-supplied values?
- Does the AO checkpoint bridge evidence bind the event id and payload hash?
- Does the deployed manifest match the reviewed bytecode and authority posture?

## Required Evidence

The final audit report must include commit SHA, compiler version, reviewed
contract addresses after testnet redeploy, finding severities, remediations,
and the final auditor sign-off hash. Until that report exists, Phase 7 preflight
keeps `KW-AUDIT-001` or its successor entry open.
