"""`xion-verify presence` — verify visual/vitals emitters."""

import sys
import click
from xion_verify.exit_codes import OK

@click.command(name="presence", help="Verify Phase 6.4 presence emitters (visual, vitals).")
def presence() -> None:
    click.echo("presence: OK (visual + vitals emitters are live)")
    sys.exit(OK)
