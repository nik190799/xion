# 39 - Gateway Pattern

> *One stable interface, many replaceable implementations.*

This document codifies the provider pattern Xion already uses for inference,
billing, bridge attestation, embeddings, tools, broker coordination, and anchor
sinks. The rule is simple: every load-bearing external service Xion depends on
must sit behind a gateway before callers can use it.

This is doctrine for Phase 6.9.1. It does not refactor runtime code by itself.
It names the property, the conformance requirements, the exception for the
Arbiter, and the verifier that will eventually enforce the rule mechanically.

## Property Promised

Every load-bearing external dependency speaks to the rest of Xion through a
stable interface (`Protocol` or `ABC`), is selected through a registry or loader,
and can be replaced without changing its callers. A surface is acceptable only
when either:

1. at least one substitute provider is already wired, or
2. the missing substitute is named in `KNOWN_WEAKNESSES.md` with a pay-down
   commitment and a verifier path.

This is the operational form of the discipline in
`.cursor/rules/The-Xion-Builder.mdc`: no load-bearing single provider.

## Conformance Requirements

Every gateway must satisfy five requirements.

1. **Stable interface.** The gateway exposes a `Protocol` or `ABC` that names
   the minimum surface callers may rely on. For provider-like surfaces, the
   interface includes `provider_id`, a category or role when policy needs one,
   and `health()` when liveness affects selection.

2. **Concrete providers are isolated.** Implementations live in a sibling
   `providers/` package or a clearly named concrete module. Callers outside the
   gateway package import the interface or loader, never the concrete provider.

3. **Runtime selection is centralized.** Environment variables, manifests, or
   governance-published registries are read by one loader. Callers do not branch
   on provider names like `chutes`, `ollama`, `arweave`, `base`, or `ntfy`.

4. **Failure is typed and observable.** Runtime failures return a typed error,
   ledger row, metric, or verifier-readable result. A gateway that can fail
   during user-facing work must make the failure class stable enough for
   operators and Witnesses to compare across providers.

5. **Verifier coverage exists or is honestly unsealed.** Each gateway has a
   verifier that proves conformance, or a `NOT_YET_SEALED` verifier entry with a
   named `KW-` gap. The verifier checks the property; it does not merely assert
   that a provider module imports.

## Reference Shape

The reference implementation is the Inference Router:

- `orchestrator/inference_router/provider.py` defines `GenerativeProvider`.
- `orchestrator/inference_router/providers/chutes.py` implements the hosted
  Bittensor SN64 path.
- `orchestrator/inference_router/providers/ollama.py` implements the local
  open-weights floor.
- `orchestrator/inference_router/router.py` selects providers by policy, not by
  caller-side `if provider == "chutes"` branches.

New gateways should copy the shape, not the names. The durable property is:
callers depend on the interface; providers depend on the external service.

## Failure Vocabulary

The inference provider error taxonomy in
`orchestrator/inference_router/provider.py` is the reference vocabulary for
runtime provider failures:

- `insufficient_credits`
- `rate_limited_upstream`
- `provider_unreachable`
- `timeout`
- `moderation_refusal`
- `unknown_provider_error`

Other gateways do not have to subclass those exact Python classes if their
domain is not inference, but they must provide equivalently stable failure
classes. A repeated provider-specific error that can only be understood by
reading a vendor traceback is a missing gateway abstraction.

## Arbiter Exclusion

The Arbiter is deliberately not a provider in a general registry.

The Arbiter gates outbound speech and enforces the Covenant. It may call a
provider behind its own constrained interface, but the gate itself cannot share
the kernel it gates. `docs/04-ARCHITECTURE.md` states the boundary: the Arbiter
is outside the Casting Pipeline, has no Hermes tool loop, and cannot
self-improve through Hermes skills.

This exclusion strengthens Invariant 6. It is not a modularity gap.

## Registry Versioning

When a gateway's interface changes in a way that would break an existing
provider, the registry schema version changes. Old provider records remain
readable under their original version. New records use the new version.

This mirrors the append-only discipline used by `SAFETY_LEDGER`: historical
rows are never reinterpreted silently, and version dispatch is explicit.

## Current Audit

The live audit table is maintained in `docs/38-MODULAR-SUBSTRATE.md` because
that document tracks which implementation layers are replaceable today. This
document defines the rule; `docs/38-MODULAR-SUBSTRATE.md` names the surfaces.

`xion-verify gateway-conformance` is reserved as the cross-cutting verifier. It
returns `NOT_YET_SEALED` until the implementation slice can check every row in
the audit table and every `KW-` closure condition.

## Deprecation Path

A concrete provider can be retired by:

1. adding the replacement provider behind the same gateway,
2. running both in shadow or fallback posture where the surface permits it,
3. publishing the divergence or health evidence,
4. updating the policy loader to prefer the replacement, and
5. leaving the retired provider's historical ledger rows interpretable.

The interface is the promise. The provider is replaceable.
