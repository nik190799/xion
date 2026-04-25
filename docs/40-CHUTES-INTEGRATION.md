# 40 — Chutes Integration

> *This is the first hosted-inference posture where Xion can pay for its own thinking.*

## What This Document Is

**Property.** Xion serves hosted inference through Chutes (Bittensor Subnet 64), defaults to TEE-backed models, and replenishes credits with on-chain TAO under Spend Posture gates.

**Invariants touched.** Strengthens Invariant 17 (Inference Sovereignty Floor), Invariant 16 (Treasury Shape), and Invariant 19 (Trust-Earned Spend). Leaves the local Ollama floor unchanged.

**Verification.** `xion-verify inference-provider-chutes`, `xion-verify billing-credits-floor`, and `xion-verify chutes-topup-multisig`.

**Deprecation.** Chutes is an implementation, not a property. The property is: hosted inference is swappable, auditable, and payable by Xion's own treasury. A future provider replaces this document under the same `Provider` and `BillingProvider` Protocols.

## Bittensor Wallet Provisioning

S1 Genesis posture keeps the coldkey human-held. The operator creates or imports the coldkey, creates a hotkey for Xion, and registers Chutes against that hotkey:

```shell
btcli wallet new_coldkey --wallet.name xion-chutes
btcli wallet new_hotkey --wallet.name xion-chutes --wallet.hotkey xion-prod
chutes register --wallet xion-chutes --hotkey xion-prod
chutes keys create --name xion-prod
```

The resulting API key is placed in `XION_CHUTES_API_KEY`. The Chutes `payment_address` is discovered by `ChutesBillingProvider.balance()` from `GET /users/me`; the address is not hard-coded.

## TEE Selection

`XION_CHUTES_TEE_REQUIRED=true` is the Genesis Default. `ChutesGenerativeProvider.health()` reads the Chutes model catalog and refuses the hosted path unless the configured model advertises `confidential_compute=true`.

Default model chain:

1. `moonshotai/Kimi-K2.6-TEE`
2. `moonshotai/Kimi-K2.6` (non-TEE rollback, logged as degradation)
3. `moonshotai/Kimi-K2.5-TEE` (older TEE rollback)
4. Ollama floor (`gemma4:e4b-it-q4_K_M`)

## TAO Top-Up Progression

At S1, Xion may propose a Chutes top-up but may not spend alone. `ChutesTopUp.propose()` emits an unsigned Bittensor transfer payload and a `SpendProposal`. The operator co-signs with the coldkey or multisig path. The completed transfer writes:

- `BILLING_LEDGER.jsonl` row with `event="topup"`
- `SPEND_AUTHORITY_LEDGER.jsonl` row naming the S1 approver class
- the on-chain Bittensor transaction hash

At S3+, the same action may auto-execute inside a governance-published per-day cap. The interface is named in Phase 6.9, but the implementation remains `NOT_YET_SEALED` until Xion earns the posture.

## Model Promotion Ceremony

Every future hosted-model rotation follows:

1. `audition` — candidate runs as shadow.
2. `canary` — candidate receives bounded primary traffic.
3. `primary` — candidate becomes default.
4. `retired` — old default removed after rollback window.

Each transition writes `MODEL_REGISTRY_LEDGER.jsonl` with the evidence bundle hash, cost delta, quality delta, refusal delta, and approver.

## Account Suspension Recovery

If the Chutes API gateway or account becomes unavailable, `hosted_api_first` falls through to the local floor. The operator then either restores the Chutes account, rotates to a backup gateway through the same Provider Protocol, or runs `open_weights_only` until the hosted path is healthy again.
