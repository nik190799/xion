"""``xion-verify api-tokens`` — admission-control config audit (Phase 5g-iv).

Doctrine anchors:
    docs/04-ARCHITECTURE.md § "The Admission-Control Surface (Phase 5g-iv)"
    docs/30-API-ADMISSION.md (operational doctrine)

Lands with the 5g-iv admission surface. The verifier loads the same
``AdmissionConfig`` the orchestrator's lifespan loads (via
``orchestrator.api.admission.load_admission_config_from_env``), runs the
same ``__post_init__`` validation, and reports the result with a stable
human-readable summary plus the structural counts an integrator needs
to confirm what they configured.

Properties verified (sourced from ``AdmissionConfig.__post_init__``):

  - Every bearer secret is ≥ 16 bytes (128 bits), matching the B1
    attestation secret floor in ``BillingConfig``.
  - Every principal_id matches ``[a-z0-9_-]{1,64}``.
  - ``require_bearer=true`` requires at least one configured token.
  - A non-loopback ``XION_API_HOST`` requires both ``XION_TLS_CERT_PATH``
    and ``XION_TLS_KEY_PATH``, and both files must exist as regular files.
  - ``rate_budget``, ``rate_window_s``, ``health_rate_budget`` are
    positive ints; ``api_port`` is in ``[1, 65535]``.

Optional flag:

  ``--env-file PATH``
    Read the env-file at ``PATH`` and use its values instead of (or in
    addition to) the process environment. Useful for CI gates that
    audit a deployment ``.env`` without invoking the operator's shell.
    Lines beginning with ``#`` and blank lines are ignored. Non-quoted
    values are taken literally up to the line end (no shell expansion).

Exit codes:

  0 OK              admission config loads and passes every structural
                    invariant; summary printed.
  1 FAIL            loader raises ``AdmissionConfigError`` or any other
                    exception; message names the specific reason.
  2 NOT_YET_SEALED  never returned (the loader has Genesis Defaults for
                    every knob; ``require_bearer=true`` with no tokens
                    is the only required-input path, and it fails to
                    OK rather than to NOT_YET_SEALED).

What this verifier does NOT do (with an honest pointer):

  * It does not verify the running orchestrator's loaded config matches
    this audit. Endpoint-vs-config drift is a deployment concern; this
    verifier audits the env shape itself.
  * It does not verify TLS chain validity, expiry, or revocation status.
    KW-TLS-001 names this as residual; the long-term path is reverse-
    proxy delegation with the proxy owning chain validation.
  * It does not validate that token entropy is *cryptographically*
    random (i.e., it cannot detect ``"a" * 32`` vs. a real 256-bit
    secret of identical length). The 128-bit floor is a lower bound,
    not a guarantee; operators are responsible for sourcing tokens
    from ``secrets.token_bytes`` or equivalent.
  * It does not enumerate the principal_id list to stdout. A future
    deploy automation that wants to assert "principal X is in the
    registry" can extend the JSON output (``--format json``) under a
    later commit; the 5g-iv minimum prints counts only.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import click

from xion_verify.exit_codes import FAIL, OK

if TYPE_CHECKING:
    from collections.abc import Iterator


def _fail(message: str) -> None:
    click.echo(f"api-tokens: FAIL: {message}", err=True)
    raise SystemExit(FAIL)


def _iter_env_file_lines(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (key, value) pairs from a simple ``.env`` file.

    Format (intentionally narrow — this is not a full dotenv parser):
      - Blank lines and lines beginning with ``#`` are skipped.
      - Each non-skipped line must contain ``=``; the key is everything
        before the first ``=``, the value is everything after.
      - Surrounding whitespace on the key is stripped; the value is
        taken verbatim except for one optional leading + trailing
        matched pair of double-quotes (so an operator may quote a
        value that contains spaces).
      - No shell expansion. ``XION_API_BEARER_TOKENS=alice:$ENVVAR``
        passes ``$ENVVAR`` to the loader as a literal four-character
        string.

    A line that begins with ``=`` (empty key) raises ``ValueError``;
    a key that contains characters other than ``[A-Za-z0-9_]`` raises
    ``ValueError``. These constraints catch the most common operator
    typos (forgotten newline, accidental shell metacharacter) without
    pretending to be a full dotenv parser.
    """
    text = path.read_text(encoding="utf-8")
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(
                f"{path}:{line_no}: line is not a key=value pair: {raw_line!r}"
            )
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            raise ValueError(f"{path}:{line_no}: empty key in {raw_line!r}")
        for ch in key:
            if not (ch.isalnum() or ch == "_"):
                raise ValueError(
                    f"{path}:{line_no}: key {key!r} contains illegal "
                    f"character {ch!r} (must be alnum or underscore)."
                )
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]
        yield key, value


@click.command(name="api-tokens")
@click.option(
    "--env-file",
    "env_file",
    type=click.Path(
        exists=True,
        dir_okay=False,
        readable=True,
        path_type=Path,
    ),
    default=None,
    help=(
        "Read this env-file instead of (or in addition to) the process "
        "environment. Keys defined in the file shadow keys in the "
        "process env for the duration of this invocation only."
    ),
)
def api_tokens(env_file: Path | None) -> None:
    """Audit the Phase 5g-iv admission-control env shape.

    Loads ``AdmissionConfig`` via the orchestrator's own loader; reports
    OK with a structural summary, or FAIL with the specific
    ``AdmissionConfigError`` message on any violation.
    """
    try:
        from orchestrator.api.admission import (
            AdmissionConfigError,
            load_admission_config_from_env,
        )
    except Exception as exc:
        _fail(
            f"cannot import orchestrator.api.admission: "
            f"{type(exc).__name__}: {exc}"
        )

    saved_env: dict[str, str | None] = {}
    overlaid_keys: list[str] = []
    if env_file is not None:
        try:
            pairs = list(_iter_env_file_lines(env_file))
        except ValueError as exc:
            _fail(str(exc))
        # Restrict the overlay to the nine env vars the loader reads.
        # An unrelated key (e.g., XION_PAYMENT_LEDGER) in the env-file
        # is silently ignored — the verifier's scope is admission only,
        # and a typo in an unrelated key should not silently affect
        # this run. A future commit can promote unrelated-key reporting
        # to a soft warning.
        relevant = {
            "XION_API_REQUIRE_BEARER",
            "XION_API_BEARER_TOKENS",
            "XION_API_RATE_BUDGET",
            "XION_API_RATE_WINDOW_S",
            "XION_API_HEALTH_RATE_BUDGET",
            "XION_API_HOST",
            "XION_API_PORT",
            "XION_TLS_CERT_PATH",
            "XION_TLS_KEY_PATH",
        }
        for key, value in pairs:
            if key not in relevant:
                continue
            saved_env[key] = os.environ.get(key)
            os.environ[key] = value
            overlaid_keys.append(key)

    try:
        try:
            config = load_admission_config_from_env()
        except AdmissionConfigError as exc:
            _fail(
                f"AdmissionConfig rejected: {exc} "
                f"See docs/30-API-ADMISSION.md § "
                f"'Operator workflow — token issuance' / "
                f"'Operator workflow — TLS termination'."
            )
        except Exception as exc:
            _fail(
                f"unexpected error loading admission config: "
                f"{type(exc).__name__}: {exc}"
            )
    finally:
        for key in overlaid_keys:
            prior = saved_env.get(key)
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior

    host = config.api_host
    is_loopback = host in ("127.0.0.1", "::1", "localhost")
    posture = "loopback (plaintext)" if is_loopback else "non-loopback (TLS)"

    click.echo(
        f"api-tokens: OK  bind={host}:{config.api_port} ({posture})"
    )
    click.echo(
        f"  require_bearer={config.require_bearer}  "
        f"tokens_loaded={len(config.tokens)}"
    )
    click.echo(
        f"  rate_budget={config.rate_budget} req / "
        f"rate_window_s={config.rate_window_s}s  "
        f"health_rate_budget={config.health_rate_budget} req / window"
    )
    if not is_loopback:
        click.echo(
            f"  tls_cert={config.tls_cert_path}  "
            f"tls_key={config.tls_key_path}"
        )
    if config.tokens:
        secret_lengths = sorted({len(s) for s in config.tokens.values()})
        click.echo(
            f"  secret-byte lengths observed: {secret_lengths}  "
            f"(floor: 16 = 128 bits)"
        )
    if env_file is not None:
        click.echo(
            f"  env-file overlay: {env_file}  "
            f"({len(overlaid_keys)} relevant key(s) applied)"
        )
    raise SystemExit(OK)


__all__ = ["api_tokens"]
