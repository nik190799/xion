"""Billing-surface configuration loaded once at lifespan startup.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface
(Phase 5g-iii)" → "Lifespan contract (extended from 5g-i)".

Four env-var dials, all with honest defaults:

  ``XION_BILLING_REQUIRED``       (bool, default True at 5g-iii)
      If True, /chat returns 402 on missing / malformed / invalid
      commitments. If False, /chat still accepts commitments but
      ALSO accepts no-header requests, writing a PAYMENT row with
      ``posture="disabled"`` and zero money fields. The disabled
      posture preserves the ledger continuity (every turn has a
      terminal row) so ``xion-verify refusal-is-free`` continues to
      structurally enforce the SAFETY ↔ PAYMENT join even in the
      backward-compat mode.

  ``XION_BILLING_ALLOW_X402``     (bool, default True at 5g-iii)
      If False, B2 (x402) commitments are rejected with 402
      ``posture_not_accepted``. Intended for D1-only deployments that
      never intend to accept external integrators.

  ``XION_OPERATOR_ATTESTATION_SECRET``  (hex string, required iff
                                         billing required and B1 may
                                         be used)
      HMAC-SHA256 shared secret for B1 operator-attestation at
      5g-iii. Phase-6+ migration to Ed25519 rotates this to a pubkey
      under the Crypto-Agility Mandate; the PAYMENT_LEDGER row shape
      does not change across that migration.

  ``XION_PAYMENT_LEDGER``         (path, default <repo>/PAYMENT_LEDGER.jsonl)
      Where the PAYMENT_LEDGER JSONL lives. Autouse conftest fixture
      redirects this to a per-test tmp_path so tests cannot contaminate
      the repo-root ledger.

The loader computes one derived value, ``architecture_sha256``, the
sha256 of ``docs/04-ARCHITECTURE.md`` at lifespan-startup time. This
hash lands in every PAYMENT_LEDGER row's ``source_sha256`` field so
future doctrine-drift detection is trivial (a row whose
``source_sha256`` does not match any known historical architecture
sha is a drift signal).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


class BillingConfigError(ValueError):
    """Raised when the billing config is internally inconsistent or
    refers to a secret / ledger path that cannot be loaded. The
    lifespan treats this as fail-closed: the app refuses to start."""


@dataclass(frozen=True)
class BillingConfig:
    """Immutable billing config snapshot held on ``app.state.billing_config``.

    All fields are computed once at lifespan startup. A governance or
    operator rotation (new secret, new ledger path) requires restarting
    the process.
    """

    billing_required: bool
    allow_x402: bool
    operator_attestation_secret: bytes | None
    payment_ledger_path: Path
    architecture_sha256: str
    b1_freshness_window_ns: int = 300_000_000_000  # 5 minutes default

    def __post_init__(self) -> None:
        if self.billing_required and self.operator_attestation_secret is None:
            # With billing required AND no B1 secret, the Relay has
            # no way to attest anything locally. If the operator ALSO
            # disables x402, no commitment posture can succeed — 402
            # all the way down. This is a misconfiguration: refuse to
            # start. (The operator who wants pure B2 keeps billing on
            # + sets XION_BILLING_ALLOW_X402=true + leaves the secret
            # unset, in which case billing_required-with-no-secret is
            # legal only if allow_x402 is True.)
            if not self.allow_x402:
                raise BillingConfigError(
                    "billing_required=true but neither B1 nor B2 posture "
                    "is available: set XION_OPERATOR_ATTESTATION_SECRET "
                    "and/or XION_BILLING_ALLOW_X402=true, or set "
                    "XION_BILLING_REQUIRED=false for 5g-i-compat mode."
                )
        if len(self.architecture_sha256) != 64:
            raise BillingConfigError(
                "architecture_sha256 must be 64 hex chars"
            )


_TRUE_STRINGS = frozenset({"1", "true", "t", "yes", "y", "on"})
_FALSE_STRINGS = frozenset({"0", "false", "f", "no", "n", "off"})


def _read_bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE_STRINGS:
        return True
    if raw in _FALSE_STRINGS:
        return False
    raise BillingConfigError(
        f"{name} must be a boolean (true/false); got {raw!r}."
    )


def _read_secret_env(name: str) -> bytes | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    # Accept hex encoding (canonical) or raw UTF-8 (operator
    # convenience for development). We prefer hex to make the secret
    # copy-paste-safe; a UTF-8 fallback is honest about a D1 operator
    # who types a plain secret into .env.
    try:
        decoded = bytes.fromhex(raw)
        if len(decoded) >= 16:
            return decoded
    except ValueError:
        pass
    # Minimum secret length: 16 UTF-8 bytes. Anything shorter is
    # dangerously close to brute-forceable on HMAC-SHA256 (128 bits
    # is the accepted floor; 16 bytes = 128 bits). An operator who
    # types a 4-char secret into .env gets fail-closed, not a silent
    # serve-with-broken-crypto.
    encoded = raw.encode("utf-8")
    if len(encoded) < 16:
        raise BillingConfigError(
            f"{name} must be at least 16 bytes (got {len(encoded)}). "
            "Use a 32-byte hex string for best compatibility."
        )
    return encoded


def _default_payment_ledger_path() -> Path:
    """Locate ``<repo>/PAYMENT_LEDGER.jsonl`` by walking up from cwd to
    the nearest directory containing a ``genesis/`` sibling. Mirrors
    the behaviour of the SAFETY_LEDGER default resolver.
    """
    for base in [Path.cwd(), *Path.cwd().parents]:
        if (base / "genesis").is_dir():
            return base / "PAYMENT_LEDGER.jsonl"
    return Path.cwd() / "PAYMENT_LEDGER.jsonl"


def _architecture_sha256() -> str:
    """Compute sha256 of ``docs/04-ARCHITECTURE.md`` as it exists at
    lifespan-startup time.

    If the file cannot be located (operator running from a non-repo
    cwd), we fall back to a known sentinel hash ``"unavailable" + "0"*55``
    rather than crashing — the lifespan still starts, and the absent
    architecture anchor shows up in every PAYMENT_LEDGER row as a
    doctrine-drift signal that can be reconciled out-of-band.
    """
    target: Path | None = None
    for base in [Path.cwd(), *Path.cwd().parents]:
        candidate = base / "docs" / "04-ARCHITECTURE.md"
        if candidate.is_file():
            target = candidate
            break
    if target is None:
        # A 64-char hex string starting with 'u' marks "unavailable";
        # real sha256 outputs do not start with 'u'. Operators and
        # verifiers can pattern-match on it.
        return "u" + "0" * 63
    try:
        data = target.read_bytes()
    except OSError:
        return "u" + "0" * 63
    return hashlib.sha256(data).hexdigest()


def load_billing_config_from_env(
    *,
    architecture_sha256: str | None = None,
) -> BillingConfig:
    """Load the billing config from environment variables.

    ``architecture_sha256`` is a test seam: tests pin a known hash so
    PAYMENT row assertions are deterministic. Production callers leave
    it ``None`` and get the lifespan-startup sha256 of
    ``docs/04-ARCHITECTURE.md``.
    """
    billing_required = _read_bool_env("XION_BILLING_REQUIRED", True)
    allow_x402 = _read_bool_env("XION_BILLING_ALLOW_X402", True)
    secret = _read_secret_env("XION_OPERATOR_ATTESTATION_SECRET")

    raw_path = os.environ.get("XION_PAYMENT_LEDGER", "").strip()
    if raw_path:
        ledger_path = Path(raw_path)
    else:
        ledger_path = _default_payment_ledger_path()

    if architecture_sha256 is None:
        architecture_sha256 = _architecture_sha256()

    return BillingConfig(
        billing_required=billing_required,
        allow_x402=allow_x402,
        operator_attestation_secret=secret,
        payment_ledger_path=ledger_path,
        architecture_sha256=architecture_sha256,
    )


__all__ = [
    "BillingConfig",
    "BillingConfigError",
    "load_billing_config_from_env",
]
