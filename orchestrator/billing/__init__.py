"""Phase 5g-iii billing surface — package exports.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface
(Phase 5g-iii)" and ``docs/29-BILLING-X402.md``.

Three responsibilities live in this package, mirroring the structure of
``orchestrator/safety/``:

  - ``ledger``      — the PAYMENT_LEDGER writer + hash-chain verifier,
                      byte-exact canonicalization with SAFETY_LEDGER.
  - ``commitment``  — the ``X-Payment-Commitment`` header parser and
                      the per-posture verifiers (B1 operator-attest,
                      B2 x402-shape-only; B3 reserved for Phase 6+).
  - ``config``      — the ``BillingConfig`` dataclass loaded once at
                      lifespan startup from env vars.

The core orchestrator deps remain zero. HMAC-SHA256 (stdlib) provides
the B1 cryptographic integrity guarantee at Phase 5g-iii; a Phase-6+
migration to Ed25519 is in-scope for the Invariant-14 Crypto-Agility
Mandate and ships under unchanged PAYMENT_LEDGER schema (only the
commitment-parser and the env-var name rotate).
"""

from __future__ import annotations

from .commitment import (
    Commitment,
    CommitmentRejectReason,
    parse_commitment_header,
    verify_b1_attestation,
    verify_b2_x402_shape,
)
from .config import BillingConfig, BillingConfigError, load_billing_config_from_env
from .credit_ledger import (
    ChainBroken as BillingCreditChainBroken,
)
from .credit_ledger import (
    append_billing_row,
)
from .credit_ledger import (
    iter_rows as iter_billing_rows,
)
from .credit_ledger import (
    verify_chain as verify_billing_credit_chain,
)
from .ledger import (
    SCHEMA_VERSION,
    ZERO_HASH,
    ChainBroken,
    append_payment_row,
    build_payment_row,
    chain_tip,
    iter_rows,
    verify_chain,
)

__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "BillingConfig",
    "BillingConfigError",
    "BillingCreditChainBroken",
    "ChainBroken",
    "Commitment",
    "CommitmentRejectReason",
    "append_billing_row",
    "append_payment_row",
    "build_payment_row",
    "chain_tip",
    "iter_billing_rows",
    "iter_rows",
    "load_billing_config_from_env",
    "parse_commitment_header",
    "verify_b1_attestation",
    "verify_b2_x402_shape",
    "verify_billing_credit_chain",
    "verify_chain",
]
