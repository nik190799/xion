from __future__ import annotations

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.exit_codes import OK


def test_embedder_health_runs_calibration_report() -> None:
    result = CliRunner().invoke(root, ["embedder-health"])

    assert result.exit_code == OK, result.output
    assert "calibration floors met" in result.output
