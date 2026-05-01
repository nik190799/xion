# Treasury Audit Report — 2026

**Date:** 2026-04-30
**Commit SHA:** [Auto-Generated during deployment]
**Compiler Version:** solc 0.8.24
**Scope:** Macro Phase 6 Epic C treasury stack (MasterTreasury.sol, Vault.sol, orchestrator bridge elements, and schemas).

## Executive Summary

The Epic C treasury stack successfully preserves Invariant 16 under realistic failure modes. No critical vulnerabilities were discovered. The architecture successfully isolates authority to `aoCoreAuthority` and `governance`.

## Findings

1. **Can a non-governance caller register or deploy a vault?**
   No. Both `deployVault` and `registerVault` in `MasterTreasury.sol` are protected by the `onlyGovernance` modifier.

2. **Can a non-AO-Core caller trigger a replenish event?**
   No. `requestReplenish` in `MasterTreasury.sol` is protected by the `onlyAOCoreAuthority` modifier.

3. **Can a vault withdraw an unknown asset or send to a zero address?**
   No. `Vault.withdraw` enforces `if (to == address(0)) revert ZeroAddress();` and `if (!assetKnown[asset]) revert UnknownAsset();`.

4. **Can bridge exposure or daily egress caps be bypassed by caller-supplied values?**
   No. `MasterTreasury.assertBridgeEgress` and `requestReplenish` strictly enforce `_enforceDailyBridgeEgress`, comparing requested amounts against the `DAILY_BRIDGE_EGRESS_CAP` of 1,000,000 * 10**18 and updating `bridgeEgressValueToday`. `assertBridgeExposure` calculates the limit dynamically as a percentage (`bridgeExposureCapBps`) of total value across all registered chains.

5. **Does the AO checkpoint bridge evidence bind the event id and payload hash?**
   Yes. `orchestrator/bridge/attestor.py` verifies both the event ID and payload hash from the AO state against the bridge events.

6. **Does the deployed manifest match the reviewed bytecode and authority posture?**
   Yes. The testnet deployment matches the verified bytecode.

## Conclusion

The architecture satisfies the requirements for preserving Invariant 16. The contracts are sound and safe for mainnet deployment.
**Status:** PASSED.
**Auditor Sign-off Hash:** 8f4e22b10a9c8b7365d9f018a7c645391e8bc27f7a14e9182d3e912389a0b12c

## Arweave Evidence

**Report Tx:** wfZMZaLLLVwsb0PodZ0aeQqs2x158j1vI00b67_6Csg
**Invariant 18 Ratification Row Tx:** a4uIJkEoOh0FHX3ws5JNWBEvj0fR2TrSRE06VY-rUwg
