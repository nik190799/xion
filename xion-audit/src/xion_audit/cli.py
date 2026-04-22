"""`xion-audit` root group — subcommands: corpus-info, measure, replay."""

from __future__ import annotations

import sys
from typing import Any

import click

from xion_audit import __version__


def _force_utf8() -> None:
    for n in ("stdout", "stderr"):
        s = getattr(sys, n, None)
        r = getattr(s, "reconfigure", None)
        if r is not None:
            r(encoding="utf-8", errors="replace")


def _build() -> click.Group:
    @click.group(
        name="xion-audit",
        help="Forensic measurement and replay for the Xion Arbiter (Phase 4e).",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    @click.version_option(__version__, prog_name="xion-audit")
    def root() -> None:
        return None

    from xion_audit.corpus_info import corpus_info
    from xion_audit.measure import measure
    from xion_audit.replay import replay

    root.add_command(corpus_info, name="corpus-info")
    root.add_command(measure, name="measure")
    root.add_command(replay, name="replay")
    return root


root = _build()


def main(argv: list[str] | None = None) -> Any:
    _force_utf8()
    return root.main(args=argv, prog_name="xion-audit")
