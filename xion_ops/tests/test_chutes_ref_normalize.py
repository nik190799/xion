"""Unit tests for Chutes ref normalization and deploy output parsing."""

from __future__ import annotations

from xion_ops.services.chutes import (
    _chutes_cli_transient_failure,
    normalize_chute_ref,
    parse_chutes_deploy_output,
    verify_module_relative_path,
)
from xion_ops.types import CommandResult


def test_normalize_chute_ref_default_empty() -> None:
    from xion_ops.services.chutes import DEFAULT_CHUTE_REF

    assert normalize_chute_ref("") == DEFAULT_CHUTE_REF


def test_normalize_py_stem_to_ref() -> None:
    assert normalize_chute_ref("xion_relay_chute.py") == "xion_relay_chute:chute"
    assert normalize_chute_ref("./xion_relay_chute.py") == "xion_relay_chute:chute"


def test_normalize_preserves_explicit_ref() -> None:
    assert normalize_chute_ref("foo_pkg:custom_chute") == "foo_pkg:custom_chute"


def test_verify_module_relative_path_from_ref() -> None:
    assert verify_module_relative_path("xion_relay_chute:chute") == "xion_relay_chute.py"


def test_parse_chutes_deploy_success_line_quoted_chute_id() -> None:
    cid = "89866bfc-5ddd-5382-b887-116d8901808f"
    ver = "5b8129a3-6253-58ec-9e2e-6de71e178625"
    blob = (
        f"Successfully deployed chute xion-relay-pre-genesis-d3 chute_id='{cid}' "
        f"version={ver} invocations will be available soon!"
    )
    got = parse_chutes_deploy_output(blob)
    assert got["chute_id"] == cid
    assert got["version"] == ver


def test_parse_chutes_deploy_loguru_success_line() -> None:
    cid = "89866bfc-5ddd-5382-b887-116d8901808f"
    blob = (
        f"stuff Successfully deployed chute xion-relay-pre-genesis-d3 chute_id={cid} "
        f"version=afaf8384 invocations!\nalso https://user-xion-relay.chutes.ai/end"
    )
    got = parse_chutes_deploy_output(blob)
    assert got["chute_id"] == cid
    assert got["version"] == "afaf8384"
    assert got["url"] == "https://user-xion-relay.chutes.ai/end"


def test_chutes_cli_transient_failure_502() -> None:
    r = CommandResult(
        command=("chutes", "build", "x:chute"),
        returncode=1,
        stdout="",
        stderr="Exception: <html>502 Bad Gateway</html>",
    )
    assert _chutes_cli_transient_failure(r) is True


def test_chutes_cli_transient_failure_content_type_500() -> None:
    r = CommandResult(
        command=("chutes", "deploy", "x:chute"),
        returncode=1,
        stdout="",
        stderr="ContentTypeError: 500, message='bad mimetype'",
    )
    assert _chutes_cli_transient_failure(r) is True


def test_chutes_cli_transient_failure_image_not_ready_yet() -> None:
    r = CommandResult(
        command=("chutes", "deploy", "x:chute"),
        returncode=1,
        stdout="Image '956d86bb-4dab-54c4-97e7-20924534914d' is not available to be used (yet)!",
        stderr="",
    )
    assert _chutes_cli_transient_failure(r) is True


def test_chutes_cli_transient_failure_image_exists_not_retried() -> None:
    r = CommandResult(
        command=("chutes", "build", "x:chute"),
        returncode=1,
        stdout="Image with name=xion-relay and tag=t already exists!",
        stderr="",
    )
    assert _chutes_cli_transient_failure(r) is False


def test_parse_chutes_deploy_json_fallback() -> None:
    import json

    cid = "89866bfc-5ddd-5382-b887-116d8901808f"
    blob = json.dumps({"chute_id": cid, "version": "v2"})
    got = parse_chutes_deploy_output(blob)
    assert got["chute_id"] == cid
    assert got["version"] == "v2"
