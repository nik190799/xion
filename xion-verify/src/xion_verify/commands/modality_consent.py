"""`xion-verify modality-consent` — verify Phase 6.4 modality consent."""

import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="modality-consent", help="Verify Phase 6.4 modality consent configurations.")
def modality_consent() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"modality-consent: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    sys.path.insert(0, str(repo_root))
    try:
        from orchestrator.api.memory import ModalityConsent
        from pydantic import ValidationError
    except ImportError as e:
        click.echo(f"modality-consent: FAIL: Could not import orchestrator modules: {e}", err=True)
        sys.exit(FAIL)

    # 1. Assert fields
    fields = set(ModalityConsent.model_fields.keys())
    expected = {"stream_visual", "stream_vitals", "stream_voice", "stream_memory"}
    if fields != expected:
        click.echo(f"modality-consent: FAIL: Expected fields {expected}, got {fields}", err=True)
        sys.exit(FAIL)

    # 2. Assert extra=forbid
    try:
        ModalityConsent(extra_field=True)
        click.echo("modality-consent: FAIL: ModalityConsent accepted extra fields", err=True)
        sys.exit(FAIL)
    except ValidationError:
        pass

    # 3. Assert defaults
    default_consent = ModalityConsent()
    if default_consent.stream_visual is not False:
        click.echo("modality-consent: FAIL: stream_visual default must be False", err=True)
        sys.exit(FAIL)
    if default_consent.stream_vitals is not False:
        click.echo("modality-consent: FAIL: stream_vitals default must be False", err=True)
        sys.exit(FAIL)
    if default_consent.stream_voice is not False:
        click.echo("modality-consent: FAIL: stream_voice default must be False", err=True)
        sys.exit(FAIL)
    if default_consent.stream_memory is not True:
        click.echo("modality-consent: FAIL: stream_memory default must be True", err=True)
        sys.exit(FAIL)

    # 4. Store API round-trip
    import tempfile
    from pathlib import Path

    from orchestrator.consent.store import read_consent, write_consent
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "CONSENT_LEDGER.jsonl"
        write_consent(store_path, "test-principal", default_consent.model_dump())
        read_back = read_consent(store_path, "test-principal")
        if read_back != default_consent.model_dump():
            click.echo("modality-consent: FAIL: ConsentStore round-trip failed", err=True)
            sys.exit(FAIL)

    click.echo("modality-consent: OK (four scopes, warm defaults, extra='forbid' verified)")
    sys.exit(OK)
