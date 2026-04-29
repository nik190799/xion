"""Tests for `xion-verify gateway-conformance`."""

from click.testing import CliRunner

from xion_verify.cli import _build_root
from xion_verify.exit_codes import NOT_YET_SEALED

_CLI = _build_root()


def test_gateway_conformance_ao_core_presence_probe():
    result = CliRunner().invoke(
        _CLI,
        ["gateway-conformance", "--surface=ao-core-client"],
    )

    assert result.exit_code == NOT_YET_SEALED
    assert "ao-core-client presence: OK" in result.output
    assert "AOCoreGateway Protocol" in result.output
    assert "legacynet placeholder" in result.output
