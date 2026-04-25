"""Tests for `xion-verify provisioning`."""

from click.testing import CliRunner

from xion_verify.cli import _build_root
from xion_verify.exit_codes import OK


def test_provisioning_ok_against_repo() -> None:
    result = CliRunner().invoke(_build_root(), ["provisioning"])
    assert result.exit_code == OK, result.output
    assert "provisioning: OK" in result.output
    assert "5 provision-* handlers canonical" in result.output
