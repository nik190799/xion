"""Phase 5g-iv: bearer-token authentication + per-principal sliding-window
rate-limit + the FastAPI dependency that wires both into the routes.

Doctrine anchors:
    docs/04-ARCHITECTURE.md § "The Admission-Control Surface (Phase 5g-iv)"
    docs/30-API-ADMISSION.md (operational doctrine)

This module owns three load-bearing things:

1. ``AdmissionConfig`` — an immutable, hash-friendly dataclass that captures
   the bearer-token registry, the per-principal rate-limit knobs, and the
   TLS / bind-host knobs the launcher reads. Loaded exactly once at lifespan
   startup and stashed on ``app.state.admission_config``.

2. ``SlidingWindow`` — the rate-limit primitive. ``collections.deque`` of
   monotonic-ns timestamps under a single ``threading.Lock``. ``check_and_record``
   evicts entries older than ``window_ns`` and either admits + records or rejects
   with the seconds-until-eviction needed for the ``Retry-After`` header.

3. ``admission_dependency`` — the FastAPI ``Depends()`` callable that runs in
   front of every authenticated route. Order is constitutionally pinned at
   ``401 → 429 → 402``: auth before rate-limit (so the bucket is per-principal,
   not per-IP); rate-limit before payment (so an unauthenticated scraper cannot
   probe pricing-validity by spamming 402-bait requests).

The token store is ``Mapping[str, bytes]`` mapping ``principal_id`` to a
shared secret of at least 16 bytes (≥128 bits, matching the B1 attestation
secret floor in ``BillingConfig``). Comparison is constant-time via
``hmac.compare_digest`` over every token (linear in token count, fine for D2
with O(10) integrators).

What this module deliberately does NOT do:

  - No federated identity. Bearer tokens are HMAC-shared-secret strings;
    Sign-In-With-Wallet / DID / on-chain pubkey lattice is Phase 6+
    (KW-AUTH-001).
  - No multi-worker rate-limit broker. The sliding window is in-process
    (KW-RATE-001).
  - No per-route auth scopes. Every authenticated principal can reach every
    authenticated route (lands when KW-AUTH-001 closes).
  - No principal_id promotion to PAYMENT_LEDGER. The matched principal_id
    is logged to operator-side stderr only at 5g-iv; PAYMENT_LEDGER schema
    stays at 1.0. principal_id reservation noted in
    docs/schemas/ledger-payment.yaml; closure reserved for Phase 6.
"""

from __future__ import annotations

import hmac
import os
import re
import threading
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import HTTPException, Request

from .models import AuthChallenge, RateLimitChallenge


# --- Errors --------------------------------------------------------------


class AdmissionConfigError(ValueError):
    """Raised when the admission config is internally inconsistent or refers
    to TLS material that cannot be loaded. The lifespan treats this as
    fail-closed: the app refuses to start. Mirrors ``BillingConfigError``."""


# --- Validation patterns -------------------------------------------------


# principal_id charset: lowercase alnum + underscore + hyphen, 1..64 chars.
# Keeps log-grep predictable and bucket-keys ASCII-clean. A future
# Phase-6+ Unicode-principal extension widens this but does not narrow it.
_PRINCIPAL_ID_RE = re.compile(r"^[a-z0-9_-]{1,64}\Z")

# Minimum secret entropy: 16 bytes = 128 bits. Matches the ``BillingConfig``
# B1 attestation floor so a single secret-strength rule applies across the
# orchestrator (operators only have to remember one number).
_MIN_SECRET_BYTES = 16


# --- AdmissionConfig -----------------------------------------------------


@dataclass(frozen=True)
class AdmissionConfig:
    """Immutable admission config snapshot held on
    ``app.state.admission_config``.

    All fields are computed once at lifespan startup; rotation requires
    restarting the process (no soft rotation at 5g-iv; that lands when
    the principal lattice does — KW-AUTH-001).

    Fields:
      require_bearer:
        While True, ``/drive`` / ``/sensorium`` / ``/chat`` require a
        valid ``Authorization: Bearer <token>`` header. ``/health`` and
        ``/pricing`` remain unauth regardless.
      tokens:
        ``Mapping[principal_id -> secret_bytes]``. Every secret is at least
        ``_MIN_SECRET_BYTES`` long; every principal_id matches
        ``_PRINCIPAL_ID_RE``. Empty mapping is legal only when
        ``require_bearer=False`` (the 5g-i backward-compat mode).
      rate_budget:
        Per-principal request count admitted within ``rate_window_s``.
        Genesis Default 60. Must be ≥ 1.
      rate_window_s:
        Sliding-window length in seconds. Genesis Default 60. Must be ≥ 1.
      health_rate_budget:
        Per-IP ``/health`` budget in the same window. Genesis Default 600.
        Must be ≥ 1. Generous because liveness probes hit /health often
        and gating /health defeats the purpose of an external monitor.
      api_host, api_port:
        Bind host / port for the ``orchestrator/api/__main__.py`` launcher.
        Default 127.0.0.1 / 8000. A non-loopback ``api_host`` REQUIRES both
        ``tls_cert_path`` and ``tls_key_path``; the dataclass raises in
        ``__post_init__`` otherwise.
      tls_cert_path, tls_key_path:
        Paths to PEM-encoded cert + key. Required iff ``api_host`` is not
        ``127.0.0.1`` (loopback). Read once at process start by the
        launcher; not used by FastAPI request handling.
    """

    require_bearer: bool
    tokens: Mapping[str, bytes]
    rate_budget: int
    rate_window_s: int
    health_rate_budget: int
    api_host: str
    api_port: int
    tls_cert_path: Path | None
    tls_key_path: Path | None

    def __post_init__(self) -> None:
        # Token-store validation is symmetrical: every token must be
        # well-shaped, no exception. A malformed entry is a config
        # error; we refuse to start rather than silently drop it
        # (a silent drop would mean the operator's intended principal
        # is unreachable while the orchestrator quietly serves on a
        # smaller token set — exactly the kind of operational drift
        # the lifespan is supposed to prevent).
        for principal_id, secret in self.tokens.items():
            if not isinstance(principal_id, str) or not _PRINCIPAL_ID_RE.match(
                principal_id
            ):
                raise AdmissionConfigError(
                    f"principal_id {principal_id!r} does not match "
                    f"{_PRINCIPAL_ID_RE.pattern!r}; allowed charset is "
                    "lowercase alphanumeric, underscore, hyphen; 1..64 chars."
                )
            if not isinstance(secret, (bytes, bytearray)):
                raise AdmissionConfigError(
                    f"token secret for {principal_id!r} must be bytes; "
                    f"got {type(secret).__name__}."
                )
            if len(secret) < _MIN_SECRET_BYTES:
                raise AdmissionConfigError(
                    f"token secret for {principal_id!r} is "
                    f"{len(secret)} bytes; minimum is {_MIN_SECRET_BYTES} "
                    f"(>=128 bits, matching the B1 attestation floor)."
                )

        if self.require_bearer and not self.tokens:
            raise AdmissionConfigError(
                "require_bearer=true but XION_API_BEARER_TOKENS is empty: "
                "configure at least one principal_id:hex_secret pair, or "
                "set XION_API_REQUIRE_BEARER=false for 5g-i-compat mode."
            )

        for label, value in (
            ("rate_budget", self.rate_budget),
            ("rate_window_s", self.rate_window_s),
            ("health_rate_budget", self.health_rate_budget),
        ):
            if not isinstance(value, int) or value < 1:
                raise AdmissionConfigError(
                    f"{label} must be a positive int; got {value!r}."
                )

        if not isinstance(self.api_port, int) or not (1 <= self.api_port <= 65535):
            raise AdmissionConfigError(
                f"api_port must be in [1, 65535]; got {self.api_port!r}."
            )

        if not isinstance(self.api_host, str) or not self.api_host:
            raise AdmissionConfigError(
                f"api_host must be a non-empty string; got {self.api_host!r}."
            )

        # Fail-closed: a non-loopback bind without TLS is structurally a
        # Covenant Principle 2 violation (bearer secret crosses plaintext).
        # Mirrors BillingConfig's "billing_required + no posture" refusal.
        if not _is_loopback_host(self.api_host):
            if self.tls_cert_path is None or self.tls_key_path is None:
                raise AdmissionConfigError(
                    f"api_host={self.api_host!r} is non-loopback; both "
                    "XION_TLS_CERT_PATH and XION_TLS_KEY_PATH are required. "
                    "(For plaintext development, keep XION_API_HOST=127.0.0.1 "
                    "and front the orchestrator with a reverse proxy that "
                    "handles TLS.)"
                )
            if not self.tls_cert_path.is_file():
                raise AdmissionConfigError(
                    f"tls_cert_path does not exist or is not a file: "
                    f"{self.tls_cert_path}"
                )
            if not self.tls_key_path.is_file():
                raise AdmissionConfigError(
                    f"tls_key_path does not exist or is not a file: "
                    f"{self.tls_key_path}"
                )


# --- Loopback detection --------------------------------------------------


def _is_loopback_host(host: str) -> bool:
    """Return True iff ``host`` is the IPv4 / IPv6 loopback or ``localhost``.

    The launcher's fail-closed TLS check uses this to decide whether cert+key
    are mandatory. Anything other than the three forms below is treated as
    externally reachable and requires TLS.
    """
    return host in ("127.0.0.1", "::1", "localhost")


# --- SlidingWindow -------------------------------------------------------


@dataclass
class SlidingWindow:
    """Per-key sliding-window rate-limit primitive.

    Holds a deque of monotonic-ns timestamps under a single
    ``threading.Lock``. ``check_and_record`` evicts entries older than
    ``window_ns`` (O(1) amortized — the deque is FIFO so eviction is
    leftpop-while-stale), then either admits + records (returns
    ``(True, 0)``) or rejects without recording (returns
    ``(False, retry_after_s)``).

    The window is true-sliding (deque, not fixed-bucket) so a principal
    cannot game the boundary by issuing ``budget`` requests at the very
    end of one window and ``budget`` more at the very start of the next.

    Thread-safety: every public method acquires the lock. Contention is
    bounded — the critical section is O(1) amortized — so a single
    process can sustain thousands of admissions per second without lock
    starvation.

    Multi-process: this class is single-process by construction. A
    ``uvicorn --workers N`` deployment has N independent
    ``SlidingWindow`` instances per principal, each with ``budget``
    capacity. KW-RATE-001 tracks; the 5g-iv operator runbook pins
    single-worker as the supported configuration.
    """

    budget: int
    window_ns: int
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _timestamps: deque[int] = field(default_factory=deque, repr=False)

    def __post_init__(self) -> None:
        if self.budget < 1:
            raise ValueError(f"budget must be ≥ 1; got {self.budget}")
        if self.window_ns < 1:
            raise ValueError(f"window_ns must be ≥ 1; got {self.window_ns}")

    def check_and_record(self, now_ns: int | None = None) -> tuple[bool, int]:
        """Admit (True, 0) or reject (False, retry_after_s).

        ``now_ns`` is a test seam — production callers leave it None and
        get ``time.monotonic_ns()``. Tests pass an explicit value to make
        eviction-boundary assertions deterministic.

        ``retry_after_s`` is the integer-rounded-up seconds until the
        oldest in-window timestamp evicts (i.e., a budget slot frees).
        Always ≥ 1 on rejection so the client does not spin.
        """
        if now_ns is None:
            now_ns = time.monotonic_ns()
        cutoff_ns = now_ns - self.window_ns
        with self._lock:
            # Evict stale entries (FIFO leftpop-while-stale; O(1)
            # amortized over the lifetime of the deque).
            while self._timestamps and self._timestamps[0] <= cutoff_ns:
                self._timestamps.popleft()
            if len(self._timestamps) < self.budget:
                self._timestamps.append(now_ns)
                return True, 0
            # Full bucket. retry_after = (oldest + window) - now,
            # rounded up to the next integer second; clamped to ≥ 1.
            oldest_ns = self._timestamps[0]
            retry_after_ns = (oldest_ns + self.window_ns) - now_ns
            retry_after_s = max(1, _ns_to_ceil_seconds(retry_after_ns))
            return False, retry_after_s

    def current_size(self) -> int:
        """For test introspection only. Production code does not call this."""
        with self._lock:
            return len(self._timestamps)


def _ns_to_ceil_seconds(ns: int) -> int:
    """Round nanoseconds up to the next whole second. Always ≥ 0."""
    if ns <= 0:
        return 0
    return (ns + 999_999_999) // 1_000_000_000


# --- Bearer verification -------------------------------------------------


_BEARER_PREFIX = "Bearer "


def verify_bearer(
    header: str | None,
    tokens: Mapping[str, bytes],
) -> str | None:
    """Return the matched ``principal_id``, or ``None`` if the header is
    missing, malformed, or matches no token.

    Comparison is constant-time over every token via
    ``hmac.compare_digest`` (linear in token count). Total comparison
    time is independent of which token matches — a side-channel
    cannot leak which principal_id is present in the registry.

    Token format on the wire: ``Authorization: Bearer <hex>`` where
    ``<hex>`` is the lowercase hex encoding of the principal's
    shared secret (matches the ``XION_API_BEARER_TOKENS`` env-var
    encoding, so an integrator copy-pastes the same string).

    Honest scope: this function does NOT take a ``request`` object,
    does NOT touch any rate-limiter, does NOT raise. It is a pure
    string-to-id mapping under constant-time comparison. The
    ``admission_dependency`` orchestrates 401 / 429 / 402 ordering;
    this function is its underlying primitive.
    """
    if not header:
        return None
    if not header.startswith(_BEARER_PREFIX):
        return None
    raw = header[len(_BEARER_PREFIX):].strip()
    if not raw:
        return None
    try:
        offered = bytes.fromhex(raw)
    except ValueError:
        return None
    if len(offered) < _MIN_SECRET_BYTES:
        # Short input cannot be a valid secret. Still constant-time
        # over the token table for shape-uniformity (do not early-return
        # before scanning, because the timing of "no scan" leaks "input
        # was malformed"); but compare against the expected length to
        # short-circuit obviously-wrong inputs without touching the
        # table. The trade-off is a tiny side channel on input length
        # vs. spending O(n_tokens) on every malformed probe, which a
        # scraper would exploit. Length-check wins.
        return None
    matched: str | None = None
    # Constant-time scan: compare against every entry, do not break.
    for principal_id, secret in tokens.items():
        # ``hmac.compare_digest`` is constant-time only when both inputs
        # are the same length; if not, it falls back to a length
        # comparison and returns False. That is the desired behaviour —
        # secrets of different lengths cannot match anyway.
        if hmac.compare_digest(offered, secret):
            matched = principal_id
            # Do NOT break: keep scanning to keep the timing uniform.
    return matched


# --- Env loading ---------------------------------------------------------


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
    raise AdmissionConfigError(
        f"{name} must be a boolean (true/false); got {raw!r}."
    )


def _read_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise AdmissionConfigError(
            f"{name} must be an integer; got {raw!r}."
        ) from e


def _read_path_env(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    return Path(raw)


def _parse_token_table(raw: str) -> dict[str, bytes]:
    """Parse ``XION_API_BEARER_TOKENS`` content into ``{principal_id: bytes}``.

    Wire format (matches ``.env.example``):

        principal_id_a:hex_secret_a,principal_id_b:hex_secret_b,...

    Whitespace around commas / colons is permitted (operator convenience).
    Duplicate principal_ids are an error (silently overwriting would
    confuse the operator's mental model of which secret is live).
    Empty entries (e.g., a trailing comma) are tolerated.
    """
    out: dict[str, bytes] = {}
    if not raw.strip():
        return out
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            raise AdmissionConfigError(
                f"XION_API_BEARER_TOKENS entry {entry!r} is missing ':' "
                "separator (expected principal_id:hex_secret)."
            )
        principal_id, _, hex_secret = entry.partition(":")
        principal_id = principal_id.strip()
        hex_secret = hex_secret.strip()
        if not principal_id:
            raise AdmissionConfigError(
                f"XION_API_BEARER_TOKENS entry {entry!r} has empty principal_id."
            )
        if not hex_secret:
            raise AdmissionConfigError(
                f"XION_API_BEARER_TOKENS entry for principal {principal_id!r} "
                "has empty hex secret."
            )
        try:
            secret = bytes.fromhex(hex_secret)
        except ValueError as e:
            raise AdmissionConfigError(
                f"XION_API_BEARER_TOKENS entry for principal {principal_id!r} "
                f"has non-hex secret: {e}"
            ) from e
        if principal_id in out:
            raise AdmissionConfigError(
                f"XION_API_BEARER_TOKENS has duplicate principal_id "
                f"{principal_id!r}; remove the duplicate."
            )
        out[principal_id] = secret
    return out


def load_admission_config_from_env() -> AdmissionConfig:
    """Construct an ``AdmissionConfig`` from process environment variables.

    Reads ten env vars (all optional with Genesis Defaults except
    ``XION_API_BEARER_TOKENS``, which is required when
    ``XION_API_REQUIRE_BEARER=true``). Validation lives in
    ``AdmissionConfig.__post_init__``; this loader's only job is the
    string-to-typed-value conversion.

    Returns a fully-validated config; raises ``AdmissionConfigError`` on
    any malformed value. The lifespan treats any error as fail-closed
    (the FastAPI app refuses to start), mirroring the
    ``BillingConfig`` / ``PricingConfig`` posture.
    """
    require_bearer = _read_bool_env("XION_API_REQUIRE_BEARER", True)
    raw_tokens = os.environ.get("XION_API_BEARER_TOKENS", "")
    tokens = _parse_token_table(raw_tokens)

    rate_budget = _read_int_env("XION_API_RATE_BUDGET", 60)
    rate_window_s = _read_int_env("XION_API_RATE_WINDOW_S", 60)
    health_rate_budget = _read_int_env("XION_API_HEALTH_RATE_BUDGET", 600)

    api_host = os.environ.get("XION_API_HOST", "").strip() or "127.0.0.1"
    api_port = _read_int_env("XION_API_PORT", 8000)

    tls_cert_path = _read_path_env("XION_TLS_CERT_PATH")
    tls_key_path = _read_path_env("XION_TLS_KEY_PATH")

    return AdmissionConfig(
        require_bearer=require_bearer,
        tokens=tokens,
        rate_budget=rate_budget,
        rate_window_s=rate_window_s,
        health_rate_budget=health_rate_budget,
        api_host=api_host,
        api_port=api_port,
        tls_cert_path=tls_cert_path,
        tls_key_path=tls_key_path,
    )


# --- Rate-limiter map construction ---------------------------------------


def build_rate_limiters(
    config: AdmissionConfig,
) -> dict[str, SlidingWindow]:
    """Construct one ``SlidingWindow`` per known principal_id.

    Lifespan stashes the result on ``app.state.rate_limiters``. The map
    is closed at lifespan time — a token added to the env after process
    start is not picked up until restart (mirrors the no-soft-rotation
    posture pinned in docs/30-API-ADMISSION.md).

    The IP-keyed ``/health`` bucket is constructed separately on demand
    by ``admission_dependency`` (see ``_health_limiter_for``); building
    one per IP at startup would let an attacker pre-allocate memory
    by spraying the surface, which is exactly the kind of degenerate
    case the per-IP cap is supposed to bound.
    """
    window_ns = config.rate_window_s * 1_000_000_000
    return {
        principal_id: SlidingWindow(budget=config.rate_budget, window_ns=window_ns)
        for principal_id in config.tokens
    }


# --- Routes that bypass admission ---------------------------------------


# Routes that are constitutionally public (per existing 5g-iii pricing
# doctrine) or unauthenticated by industry convention (/health). Listed
# explicitly so a future route addition that is meant to be public has
# to opt in here AND by not adding ``Depends(admission_dependency)`` —
# defense in depth against accidentally exposing a new endpoint.
_PUBLIC_ROUTES: frozenset[str] = frozenset({"/pricing"})

# /health gets per-IP rate limiting but no auth (liveness probes work
# without a token; the bucket bounds hostile scraping cadence).
_IP_RATE_LIMITED_PUBLIC_ROUTES: frozenset[str] = frozenset({"/health"})


# --- The admission FastAPI dependency ------------------------------------


# A sentinel principal_id used in operator-side logs for routes that
# reach the dependency without bearer auth (the public routes above).
# Pattern: ``unauth-public:<route>``. Never appears in any ledger row.
_UNAUTH_PUBLIC = "unauth-public"


def admission_dependency(request: Request) -> str:
    """FastAPI ``Depends()`` callable: enforces 401 → 429 → 402 ordering.

    Returns the matched ``principal_id`` (or ``"unauth-public"`` for
    /health and /pricing) to the route handler. The handler is free to
    log it; at 5g-iv it does NOT promote into PAYMENT_LEDGER (KW-AUTH-001).

    Order of checks (constitutionally pinned):

      1. If the route is in ``_PUBLIC_ROUTES`` (e.g., /pricing): pass
         through without any check. /pricing is constitutionally public
         per existing 5g-iii doctrine and cannot be narrowed by 5g-iv.
      2. If the route is in ``_IP_RATE_LIMITED_PUBLIC_ROUTES`` (e.g.,
         /health): per-IP rate-limit only; no auth. ``RateLimitChallenge``
         on overflow with ``bucket="ip"``.
      3. Otherwise: bearer auth (401 if missing/invalid), then per-principal
         rate-limit (429 if budget exceeded).

    Honest scope: this dependency does NOT enforce payment. The 5g-iii
    ``_gate_commitment`` in ``orchestrator/api/chat.py`` is the next
    layer down and runs after this returns. The constitutional ordering
    is documented in docs/04-ARCHITECTURE.md § "The Admission-Control
    Surface".
    """
    app = request.app
    config: AdmissionConfig | None = getattr(app.state, "admission_config", None)
    if config is None:
        # Defensive: a missing admission config is a lifespan-construction
        # bug, not a request-time failure mode. Refuse closed.
        raise HTTPException(
            status_code=500,
            detail="admission_config not loaded (lifespan did not run?)",
        )

    route_path = _route_path(request)

    # 1. Constitutionally public — no admission check at all.
    if route_path in _PUBLIC_ROUTES:
        return _UNAUTH_PUBLIC

    # 2. Public-but-IP-rate-limited (e.g., /health).
    if route_path in _IP_RATE_LIMITED_PUBLIC_ROUTES:
        client_ip = _client_ip(request)
        limiter = _health_limiter_for(app, config, client_ip)
        admitted, retry_after_s = limiter.check_and_record()
        if not admitted:
            challenge = RateLimitChallenge(
                error="rate_limited",
                retry_after_s=retry_after_s,
                bucket="ip",
            )
            raise HTTPException(
                status_code=429,
                detail=challenge.model_dump(),
                headers={"Retry-After": str(retry_after_s)},
            )
        return _UNAUTH_PUBLIC

    # 3. Authenticated routes — bearer required (modulo backward-compat).
    if not config.require_bearer:
        # 5g-i compat mode: no bearer required, no rate-limit. The
        # operator-side runbook in docs/30-API-ADMISSION.md pins this
        # as local-development only and forbids it on non-loopback
        # binds (the AdmissionConfig __post_init__ enforces TLS for
        # non-loopback regardless, so this is not a security regression).
        return _UNAUTH_PUBLIC

    auth_header = request.headers.get("Authorization")
    principal_id = verify_bearer(auth_header, config.tokens)
    if principal_id is None:
        challenge = AuthChallenge(
            error="unauthorized",
            accepted_schemes=["Bearer"],
        )
        raise HTTPException(
            status_code=401,
            detail=challenge.model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    rate_limiters: Mapping[str, SlidingWindow] = getattr(
        app.state, "rate_limiters", {}
    )
    limiter = rate_limiters.get(principal_id)
    if limiter is None:
        # Defensive: a verified principal_id without a bucket means
        # the lifespan and the admission dependency disagree on the
        # token table. That is a lifespan-construction bug, not a
        # request-time failure mode. Refuse closed.
        raise HTTPException(
            status_code=500,
            detail=(
                f"rate-limiter not built for principal {principal_id!r} "
                "(lifespan / admission_dependency disagreement?)"
            ),
        )
    admitted, retry_after_s = limiter.check_and_record()
    if not admitted:
        challenge = RateLimitChallenge(
            error="rate_limited",
            retry_after_s=retry_after_s,
            bucket="principal",
        )
        raise HTTPException(
            status_code=429,
            detail=challenge.model_dump(),
            headers={"Retry-After": str(retry_after_s)},
        )

    return principal_id


# --- Helpers used by the dependency --------------------------------------


def _route_path(request: Request) -> str:
    """Return the FastAPI-route path for ``request``.

    Prefers ``request.scope["route"].path`` (the registered template
    like ``/users/{id}``) over ``request.url.path`` (the concrete
    request URL like ``/users/42``). At 5g-iv every route is static
    so the two coincide; the template-aware lookup is forward-proof
    for 5g-v+ routes that take path parameters.
    """
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path


def _client_ip(request: Request) -> str:
    """Best-effort client IP. Used only as the /health bucket key.

    Honest scope: this is NOT a security primitive. ``X-Forwarded-For``
    is trivially spoofable by a direct client; we only honor it when
    ``XION_API_TRUST_FORWARDED_FOR=true`` (operator opt-in for deployments
    behind a trusted reverse proxy). Default is the direct socket peer.

    A fall-back of ``"unknown"`` keeps the bucket map keyed even when
    ``request.client`` is None (rare; happens in some ASGI test harnesses).
    """
    if _read_bool_env("XION_API_TRUST_FORWARDED_FOR", False):
        forwarded = request.headers.get("X-Forwarded-For", "").strip()
        if forwarded:
            # Take the leftmost (originating) entry; further entries are
            # the proxy chain. Strip whitespace; collapse to "unknown" if
            # the header is malformed.
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    if request.client is None:
        return "unknown"
    return request.client.host or "unknown"


def _health_limiter_for(
    app, config: AdmissionConfig, client_ip: str
) -> SlidingWindow:
    """Lazy per-IP /health bucket. Allocated on first sight of an IP.

    The map lives on ``app.state.health_rate_limiters`` (created lazily
    on first request so the lifespan does not need to know about
    /health-specific state). Lock around the dict mutation; the
    ``SlidingWindow`` itself has its own internal lock for
    ``check_and_record``.

    Memory-cap caveat: the map grows unboundedly with distinct source
    IPs. A long-running deployment under heavy hostile probing could
    accumulate millions of empty buckets. This is acceptable at 5g-iv
    because (a) the budget is generous so legitimate IPs do not
    accumulate empty windows often, (b) operators behind a reverse
    proxy will see only the proxy IP, and (c) the broker pay-down
    in ``KW-RATE-001`` includes per-IP eviction policy for /health.
    """
    state_map_lock: threading.Lock = getattr(
        app.state, "_health_rate_limiters_lock", None
    )
    if state_map_lock is None:
        state_map_lock = threading.Lock()
        app.state._health_rate_limiters_lock = state_map_lock
    state_map: dict[str, SlidingWindow] = getattr(
        app.state, "health_rate_limiters", None
    )
    if state_map is None:
        state_map = {}
        app.state.health_rate_limiters = state_map
    with state_map_lock:
        limiter = state_map.get(client_ip)
        if limiter is None:
            window_ns = config.rate_window_s * 1_000_000_000
            limiter = SlidingWindow(
                budget=config.health_rate_budget, window_ns=window_ns
            )
            state_map[client_ip] = limiter
        return limiter


__all__ = [
    "AdmissionConfig",
    "AdmissionConfigError",
    "SlidingWindow",
    "admission_dependency",
    "build_rate_limiters",
    "load_admission_config_from_env",
    "verify_bearer",
]
