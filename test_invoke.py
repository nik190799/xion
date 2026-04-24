import sys

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


@click.command()
def cmd_ok():
    click.echo("OK")
    sys.exit(OK)


@click.command()
def cmd_nys():
    click.echo("NOT YET SEALED")
    sys.exit(NOT_YET_SEALED)


@click.command()
@click.pass_context
def pre_genesis(ctx):
    try:
        ctx.invoke(cmd_ok)
    except SystemExit as exc:
        if exc.code != OK:
            sys.exit(FAIL)
    
    try:
        ctx.invoke(cmd_nys)
    except SystemExit as exc:
        if exc.code != NOT_YET_SEALED:
            sys.exit(FAIL)

    click.echo("pre-genesis: OK")
    sys.exit(OK)

if __name__ == "__main__":
    pre_genesis()
