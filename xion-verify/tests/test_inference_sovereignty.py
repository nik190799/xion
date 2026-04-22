"""`xion-verify inference-sovereignty` — structural manifest check."""

from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import root


def test_inference_sovereignty_ok_in_repo_checkout():
    here = Path(__file__).resolve().parents[2]
    if not (here / "orchestrator" / "inference_router" / "open_weights_manifest.json").is_file():
        return
    old = os.getcwd()
    try:
        os.chdir(here)
        runner = CliRunner()
        r = runner.invoke(
            root,
            ["inference-sovereignty"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old)
    assert r.exit_code == 0
    assert "OK" in r.output
