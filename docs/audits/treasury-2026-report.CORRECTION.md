# Correction: Treasury Audit Report — 2026

**Date:** 2026-05-01  
**Corrects:** `docs/audits/treasury-2026-report.md`  
**Original Arweave tx:** `wfZMZaLLLVwsb0PodZ0aeQqs2x158j1vI00b67_6Csg`  
**Correction Arweave tx:** pending

## Summary

The document published as `Treasury Audit Report — 2026` overstated the evidence available for the Macro Phase 6 Epic C treasury stack.

It was written as an internal review / self-attestation, but it used language that implied an external audit had passed the exact deployable source and that the Base Sepolia deployment matched reviewed bytecode. During the 2026-05-01 Base mainnet deploy preflight, those claims were falsified.

This correction must be cited anywhere the original tx is cited.

## What Was Wrong

1. The report's `Commit SHA` field was a placeholder (`[Auto-Generated during deployment]`), so the report did not bind to immutable repository bytes.
2. The report named no external auditor, firm, contact, public key, or reproducible signature input.
3. The report's `PASSED` status and auditor sign-off hash were not independently verifiable.
4. `contracts/treasury/MasterTreasury.sol` did not compile under the declared `solc 0.8.24` compiler during mainnet deploy preflight.
5. The Base Sepolia `MasterTreasury` address pinned in `genesis/TREASURY_VAULTS.json` responds to older selectors (`governance`, `bridgeExposureCapBps`, `vaultForChain`) but not to later source selectors (`aoCoreAuthority`, `registeredChainCount`), proving a source/bytecode version mismatch.

## Evidence

The failed mainnet preflight produced:

```text
Error (2314): Expected identifier but got ';'
  --> treasury/MasterTreasury.sol:22:53:
   |
22 |     mapping(uint256 chainId => bool registeredChain);
   |                                                     ^
```

Base Sepolia probe against `0xFAAa1A20f07249316BdB33A9eA44522260Ed7E45` returned:

```text
governance=0xEBDDDf598b5b53C91ff185501d7b182ae5d6B88A
bridgeExposureCapBps=1000
DAILY_BRIDGE_EGRESS_CAP=1000000000000000000000000
vaultForChain_84532=0x474Df6994918B5c01Aab413Cf3718DFd1bb0F7Bc
aoCoreAuthority=execution reverted
registeredChainCount=execution reverted
```

## Corrective Action

- `KW-AUDIT-001` is reopened.
- `KW-AUDIT-002` tracks the audit-record and bytecode/source mismatch.
- `docs/audits/treasury-2026-report.md` is demoted to an internal review record.
- No Base mainnet treasury deployment may cite the original report as an external audit.
- A future mainnet deployment must either obtain a real external audit for exact deployable bytecode or proceed under explicit Sprint Mode unaudited acceptance with fresh Base Sepolia soak and Foundry test/coverage evidence.

## Current Status

Correction written locally. Arweave correction publish is still pending.
