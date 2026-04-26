from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

import xion_verify.commands.image_digest as image_digest_module
from xion_verify.cli import root
from xion_verify.commands.image_digest import build_local_image_digest, read_relay_image_digest
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK

VALID_DIGEST = "sha256:" + ("a" * 64)
OTHER_DIGEST = "sha256:" + ("b" * 64)


def _write_repo_witnesses(repo: Path) -> None:
    (repo / "genesis").mkdir()
    (repo / "genesis" / "GENESIS_ARTIFACT.md").write_text("", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "00-INDEX.md").write_text("", encoding="utf-8")


def test_read_relay_image_digest_missing_digest(synthetic_repo: Path) -> None:
    code, message = read_relay_image_digest(synthetic_repo)

    assert code == NOT_YET_SEALED
    assert "not found" in message


def test_read_relay_image_digest_rejects_bad_shape(synthetic_repo: Path) -> None:
    (synthetic_repo / "genesis" / "RELAY_IMAGE_DIGEST.txt").write_text("not-a-digest\n", encoding="utf-8")

    code, message = read_relay_image_digest(synthetic_repo)

    assert code == FAIL
    assert "sha256" in message


def test_read_relay_image_digest_accepts_digest_with_dockerfile(synthetic_repo: Path) -> None:
    (synthetic_repo / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (synthetic_repo / "genesis" / "RELAY_IMAGE_DIGEST.txt").write_text(VALID_DIGEST + "\n", encoding="utf-8")

    code, message = read_relay_image_digest(synthetic_repo)

    assert code == OK
    assert message == VALID_DIGEST


def test_build_local_image_digest_reads_iidfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **_: object) -> SimpleNamespace:
        iidfile = Path(args[args.index("--iidfile") + 1])
        iidfile.write_text(VALID_DIGEST, encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(image_digest_module.subprocess, "run", fake_run)

    code, message = build_local_image_digest(tmp_path, tag="xion-relay:test")

    assert code == OK
    assert message == VALID_DIGEST


def test_build_local_image_digest_falls_back_to_wsl_on_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_: object) -> SimpleNamespace:
        calls.append(args)
        if args[0] == "docker":
            raise FileNotFoundError
        return SimpleNamespace(returncode=0, stdout=f"build output\n{VALID_DIGEST}\n", stderr="")

    monkeypatch.setattr(image_digest_module.sys, "platform", "win32")
    monkeypatch.setattr(image_digest_module.subprocess, "run", fake_run)
    monkeypatch.setattr(image_digest_module, "_windows_path_to_wsl", lambda path: "/mnt/c/repo")

    code, message = build_local_image_digest(tmp_path)

    assert code == OK
    assert message == VALID_DIGEST
    assert calls[1][:4] == ["wsl.exe", "--cd", "/mnt/c/repo", "--exec"]


def test_image_digest_check_local_detects_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_repo_witnesses(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path / "genesis" / "RELAY_IMAGE_DIGEST.txt").write_text(VALID_DIGEST + "\n", encoding="utf-8")

    def fake_build(repo_root: Path, tag: str | None = None) -> tuple[int, str]:
        assert repo_root == tmp_path
        assert tag is None
        return OK, OTHER_DIGEST

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(image_digest_module, "build_local_image_digest", fake_build)

    result = CliRunner().invoke(root, ["image-digest", "--check-local"])

    assert result.exit_code == FAIL
    assert "digest mismatch" in result.output
