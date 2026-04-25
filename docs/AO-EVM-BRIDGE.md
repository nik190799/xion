# AO ↔ EVM Bridge

Phase 6.9 treats AO-to-Base bridging as a modular substrate, not a single permanent trust assumption.

## Property

AO remains the identity and policy source. EVM contracts only accept bridge effects that are attested by a swappable `BridgeAttestor` and bounded by daily egress caps.

## Attestor Stack

- `MultisigBridgeAttestor` is the Genesis implementation: a threshold signer set attests AO events before they are submitted to EVM.
- `LightClientBridgeAttestor` is reserved as `NOT_YET_SEALED` for future trust-minimized AO proof verification.
- `xion-verify bridge-attest` checks that the multisig attestor satisfies the protocol and that the light-client path is honestly marked unsealed.

## Egress Caps

The bridge must fail closed before a compromised attestor can drain a day of value.

- `EmissionController.sol` enforces `DAILY_EGRESS_CAP` on scheduled mint egress.
- `MasterTreasury.sol` exposes `assertBridgeEgress()` and `DAILY_BRIDGE_EGRESS_CAP` for treasury bridge movements.
- `xion-verify bridge-egress-cap` checks both contract caps are present.

## Trust Boundary

The multisig attestor is a mitigation, not final decentralization. `KW-BRIDGE-001` stays open until a light-client or equivalent independently verifiable proof path replaces multisig trust.
