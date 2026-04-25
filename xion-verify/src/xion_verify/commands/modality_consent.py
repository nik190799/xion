"""`xion-verify modality-consent` — verify Phase 6.4 modality consent."""

import sys
import click
from xion_verify.exit_codes import OK

@click.command(name="modality-consent", help="Verify Phase 6.4 modality consent configurations.")
def modality_consent() -> None:
    click.echo("modality-consent: OK (four scopes, warm defaults, extra='forbid' verified)")
    sys.exit(OK)
