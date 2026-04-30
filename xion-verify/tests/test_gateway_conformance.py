"""Tests for `xion-verify gateway-conformance`."""

from click.testing import CliRunner

from xion_verify.cli import _build_root
from xion_verify.exit_codes import OK

_CLI = _build_root()


def test_gateway_conformance_ao_core_presence_probe():
    result = CliRunner().invoke(
        _CLI,
        ["gateway-conformance", "--surface=ao-core-client"],
    )

    assert result.exit_code == OK
    assert "ao-core-client presence: OK" in result.output
    assert "AOCoreGateway Protocol" in result.output
    assert "legacynet placeholder" in result.output


def test_gateway_conformance_all_surfaces_live():
    result = CliRunner().invoke(_CLI, ["gateway-conformance"])

    assert result.exit_code == OK
    for surface in (
        "ao-core-client",
        "vault",
        "alerting",
        "observability",
        "relay-registry",
        "settlement-chain",
        "status",
        "gateway-conformance",
    ):
        assert f"{surface} presence: OK" in result.output
