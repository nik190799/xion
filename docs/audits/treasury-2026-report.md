# Treasury Internal Review Record — 2026

**Date:** 2026-04-30  
**Corrected:** 2026-05-01  
**Compiler Version:** solc 0.8.24  
**Scope:** Macro Phase 6 Epic C treasury stack (`MasterTreasury.sol`, `Vault.sol`, orchestrator bridge elements, and schemas).

## Status

This document is an **internal review record**, not an external audit report. It must not be cited as an auditor-signed `PASSED` report, and it must not close `KW-AUDIT-001`.

The prior version of this file was anchored to Arweave at tx `wfZMZaLLLVwsb0PodZ0aeQqs2x158j1vI00b67_6Csg` with language that overstated the evidence. The correction record is `docs/audits/treasury-2026-report.CORRECTION.md`.

## What The Review Checked

1. **Can a non-governance caller register or deploy a vault?**  
   The intended design protects `deployVault` and `registerVault` in `MasterTreasury.sol` with `onlyGovernance`.

2. **Can a non-AO-Core caller trigger a replenish event?**  
   The intended design protects `requestReplenish` in `MasterTreasury.sol` with `onlyAOCoreAuthority`.

3. **Can a vault withdraw an unknown asset or send to a zero address?**  
   `Vault.withdraw` enforces `if (to == address(0)) revert ZeroAddress();` and `if (!assetKnown[asset]) revert UnknownAsset();`.

4. **Can bridge exposure or daily egress caps be bypassed by caller-supplied values?**  
   The intended design routes both governance and AO replenish paths through `_enforceDailyBridgeEgress`, and `assertBridgeExposure` calculates the limit as a percentage (`bridgeExposureCapBps`) of total value across registered chains.

5. **Does the AO checkpoint bridge evidence bind the event id and payload hash?**  
   `orchestrator/bridge/attestor.py` verifies both the event ID and payload hash from the AO state against bridge events.

## Correction Notes

- The 2026-04-30 report used the title "Treasury Audit Report" and the status `PASSED`; those claims were too strong.
- The `Commit SHA` field was a placeholder and did not bind the review to immutable source bytes.
- The report did not identify an external auditor, auditor signing key, or reproducible sign-off input.
- On 2026-05-01, Base mainnet deploy preflight found that current `contracts/treasury/MasterTreasury.sol` did not compile under the declared compiler version.
- The Base Sepolia `MasterTreasury` address pinned in `genesis/TREASURY_VAULTS.json` responds to pre-change selectors but not to later selectors such as `aoCoreAuthority()` or `registeredChainCount()`, so the source and deployed bytecode are not the same version.

## Current Conclusion

The treasury design remains a useful internal review target, but this record is **not sufficient evidence for mainnet deployment under an externally audited claim**.

Mainnet deploy is blocked until one of the following is true:

1. An actual external audit signs a commit-specific report for the exact deployable bytecode; or
2. Sprint Mode proceeds explicitly as unaudited, with `KW-AUDIT-001` open, a fresh Base Sepolia soak, Foundry test/coverage output, and all residuals recorded in `docs/STATE_OF_XION_PREFLIGHT.md`.

## Arweave Evidence

**Original overstated report tx:** `wfZMZaLLLVwsb0PodZ0aeQqs2x158j1vI00b67_6Csg`  
**Correction tx:** pending  
**Invariant 18 ratification row tx:** `a4uIJkEoOh0FHX3ws5JNWBEvj0fR2TrSRE06VY-rUwg`
