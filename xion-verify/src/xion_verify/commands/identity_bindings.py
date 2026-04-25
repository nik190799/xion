"""`xion-verify identity-bindings` — verify contributor identity binding rows."""

from __future__ import annotations

import base64
import json
import re
import sys
from typing import Any

import click
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_DEFAULT_BINDINGS_PATH = "ledgers/CONTRIBUTOR_IDENTITY_BINDINGS.jsonl"
_HANDLE_RE = re.compile(r"^@[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_PURPOSE = "xion-contributor-identity-binding-v1"


def _b64url_decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _expected_message(row: dict[str, Any]) -> str:
    return (
        f"{_PURPOSE}\n"
        f"github_handle={row['github_handle']}\n"
        f"wallet_pubkey_ed25519_base64url={row['wallet_pubkey_ed25519_base64url']}\n"
        f"signed_at_utc={row['signed_at_utc']}"
    )


def _validate_row(row: Any, line_no: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(row, dict):
        return [f"line {line_no}: row must be a JSON object"]

    required = {
        "schema_version",
        "purpose",
        "github_handle",
        "wallet_pubkey_ed25519_base64url",
        "signed_at_utc",
        "signed_message",
        "signature_ed25519_base64url",
    }
    missing = sorted(required - set(row))
    if missing:
        errors.append(f"line {line_no}: missing required field(s): {', '.join(missing)}")
        return errors

    if row["schema_version"] != 1:
        errors.append(f"line {line_no}: schema_version must be 1")
    if row["purpose"] != _PURPOSE:
        errors.append(f"line {line_no}: purpose must be {_PURPOSE!r}")
    handle = row["github_handle"]
    if not isinstance(handle, str) or not _HANDLE_RE.match(handle):
        errors.append(f"line {line_no}: github_handle must be a canonical @handle")

    expected_message = _expected_message(row)
    if row["signed_message"] != expected_message:
        errors.append(f"line {line_no}: signed_message does not match canonical binding message")

    try:
        pubkey = _b64url_decode(str(row["wallet_pubkey_ed25519_base64url"]))
        signature = _b64url_decode(str(row["signature_ed25519_base64url"]))
    except Exception as exc:
        errors.append(f"line {line_no}: base64url decode failed: {type(exc).__name__}")
        return errors

    if len(pubkey) != 32:
        errors.append(f"line {line_no}: Ed25519 public key must decode to 32 bytes")
    if len(signature) != 64:
        errors.append(f"line {line_no}: Ed25519 signature must decode to 64 bytes")
    if errors:
        return errors

    try:
        Ed25519PublicKey.from_public_bytes(pubkey).verify(signature, expected_message.encode("utf-8"))
    except InvalidSignature:
        errors.append(f"line {line_no}: signature does not verify")
    except ValueError as exc:
        errors.append(f"line {line_no}: invalid public key: {exc}")
    return errors


@click.command(name="identity-bindings", help="Verify contributor wallet-to-GitHub binding rows.")
@click.option(
    "--path",
    "bindings_path",
    default=_DEFAULT_BINDINGS_PATH,
    show_default=True,
    help="Repo-relative JSONL binding ledger to verify.",
)
def identity_bindings(bindings_path: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"identity-bindings: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    path = (repo_root / bindings_path).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError:
        click.echo(f"identity-bindings: FAIL: path escapes repo root: {bindings_path}", err=True)
        sys.exit(FAIL)

    if not path.exists():
        click.echo(
            f"identity-bindings: OK (no binding ledger at {bindings_path}; zero rows to verify)"
        )
        sys.exit(OK)

    errors: list[str] = []
    rows = 0
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        rows += 1
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON: {exc}")
            continue
        errors.extend(_validate_row(row, line_no))

    if errors:
        for err in errors:
            click.echo(f"identity-bindings: FAIL: {err}", err=True)
        sys.exit(FAIL)
    click.echo(f"identity-bindings: OK ({rows} binding row(s) verified)")
    sys.exit(OK)
