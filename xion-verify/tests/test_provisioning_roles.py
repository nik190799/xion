"""Tests for `xion-verify provisioning-roles`.

Builds tmp-path git repos with synthetic merge commits, asserting OK / FAIL /
NOT_YET_SEALED across the algorithm's branches. Mirrors the conftest pattern
in test_new.py.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


def _run_git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> None:
    base_env = os.environ.copy()
    base_env.update({
        "GIT_AUTHOR_NAME": "test-bot",
        "GIT_AUTHOR_EMAIL": "test-bot@example.com",
        "GIT_COMMITTER_NAME": "test-bot",
        "GIT_COMMITTER_EMAIL": "test-bot@example.com",
    })
    if env:
        base_env.update(env)
    subprocess.run(["git", *args], cwd=cwd, check=True, env=base_env, capture_output=True)


def _seed_witnesses(tmp_path: Path) -> None:
    (tmp_path / "genesis").mkdir(exist_ok=True)
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("# stub", encoding="utf-8")
    (tmp_path / "docs" / "00-INDEX.md").write_text("# stub", encoding="utf-8")


def _seed_schemas(tmp_path: Path, operator_handle: str = "test-bot") -> None:
    schemas_dir = tmp_path / "docs" / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    (schemas_dir / "levels.yaml").write_text(
        "schema_version: 1\n"
        "source_doctrine: docs/14-UPGRADE-PATHS.md\n"
        "source_sha256:   " + ("0" * 64) + "\n"
        "status: canonical\n"
        "levels:\n"
        "  - id: 1\n"
        "    name: Core\n"
        "    proposer: operators_or_community\n"
        "    artifacts:\n"
        "      - core/**\n"
        "      - core/*\n"
        "  - id: 11\n"
        "    name: Operators\n"
        "    proposer: operator_only\n"
        "    artifacts:\n"
        "      - operator/**\n"
        "      - operator/*\n"
        "  - id: 12\n"
        "    name: Meta\n"
        "    proposer: anyone\n"
        "    artifacts:\n"
        "      - docs/14-UPGRADE-PATHS.md\n"
        "      - DEVELOPMENT_ROADMAP.md\n",
        encoding="utf-8",
    )
    (schemas_dir / "roles.yaml").write_text(
        "schema_version: 1\n"
        "source_doctrine: docs/09-GOVERNANCE.md\n"
        "source_sha256:   " + ("0" * 64) + "\n"
        "status: canonical\n"
        "actors:\n"
        "  - id: operator\n"
        "    name: Operator\n"
        "    key_class: safe\n"
        "    scope_summary: ops\n"
        "    authorized_levels: [1, 11]\n"
        "  - id: community\n"
        "    name: Community\n"
        "    key_class: wallet\n"
        "    scope_summary: comm\n"
        "    authorized_levels: [1, 12]\n"
        "level_proposer_resolution:\n"
        "  operators_or_community:\n"
        "    actors: [operator, community]\n"
        "  operator_only:\n"
        "    actors: [operator]\n"
        "  anyone:\n"
        "    actors: [operator, community]\n"
        "github_identity_map:\n"
        f"  operator:\n    handles: ['{operator_handle}']\n"
        "  community:\n    handles: []\n",
        encoding="utf-8",
    )


def _commit_file(tmp_path: Path, rel: str, body: str, message: str) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    _run_git(tmp_path, "add", rel)
    _run_git(tmp_path, "commit", "-m", message)


def _branch_merge(
    tmp_path: Path,
    branch: str,
    rel: str,
    body: str,
    branch_msg: str,
    pr_subject: str,
    operator_handle: str = "test-bot",
) -> None:
    _run_git(tmp_path, "checkout", "-b", branch)
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    _run_git(tmp_path, "add", rel)
    _run_git(tmp_path, "commit", "-m", branch_msg)
    _run_git(tmp_path, "checkout", "main")
    env = {"GIT_AUTHOR_NAME": operator_handle, "GIT_COMMITTER_NAME": operator_handle}
    _run_git(
        tmp_path,
        "merge",
        "--no-ff",
        branch,
        "-m",
        f"Merge pull request #1 from {operator_handle}/{branch}\n\n{pr_subject}",
        env=env,
    )


@pytest.fixture
def synthetic_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _seed_witnesses(tmp_path)
    _run_git(tmp_path, "init", "-b", "main")
    _commit_file(tmp_path, "genesis/GENESIS_ARTIFACT.md", "# stub\n", "init")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_not_yet_sealed_when_schemas_missing(synthetic_repo: Path) -> None:
    """Missing roles.yaml or levels.yaml → NOT_YET_SEALED."""
    result = CliRunner().invoke(root, ["provisioning-roles"])
    assert result.exit_code == NOT_YET_SEALED
    assert "NOT_YET_SEALED" in result.output


def test_ok_when_no_merges_in_window(synthetic_repo: Path) -> None:
    """Repo with schemas but zero merges → OK (vacuously true)."""
    _seed_schemas(synthetic_repo)
    _run_git(synthetic_repo, "add", "docs/schemas/")
    _run_git(synthetic_repo, "commit", "-m", "land schemas")
    result = CliRunner().invoke(root, ["provisioning-roles"])
    assert result.exit_code == OK
    assert "OK" in result.output


def test_ok_single_level_authorized_initiator(synthetic_repo: Path) -> None:
    """Post-gate merge touching one level by authorized initiator → OK."""
    _seed_schemas(synthetic_repo, operator_handle="alice")
    _run_git(synthetic_repo, "add", "docs/schemas/")
    _run_git(synthetic_repo, "commit", "-m", "land schemas")
    _branch_merge(
        synthetic_repo,
        "core-bump",
        "core/policy.md",
        "policy",
        "core: bump policy",
        "core: bump policy",
        operator_handle="alice",
    )
    result = CliRunner().invoke(root, ["provisioning-roles", "--strict"])
    assert result.exit_code == OK, result.output
    assert "OK" in result.output


def test_fail_cross_level_strict(synthetic_repo: Path) -> None:
    """Post-gate merge spanning two levels under --strict → FAIL."""
    _seed_schemas(synthetic_repo, operator_handle="alice")
    _run_git(synthetic_repo, "add", "docs/schemas/")
    _run_git(synthetic_repo, "commit", "-m", "land schemas")
    _run_git(synthetic_repo, "checkout", "-b", "cross")
    (synthetic_repo / "core").mkdir(exist_ok=True)
    (synthetic_repo / "core" / "x.md").write_text("x", encoding="utf-8")
    (synthetic_repo / "DEVELOPMENT_ROADMAP.md").write_text("y", encoding="utf-8")
    _run_git(synthetic_repo, "add", "core/x.md", "DEVELOPMENT_ROADMAP.md")
    _run_git(synthetic_repo, "commit", "-m", "cross-level")
    _run_git(synthetic_repo, "checkout", "main")
    env = {"GIT_AUTHOR_NAME": "alice", "GIT_COMMITTER_NAME": "alice"}
    _run_git(
        synthetic_repo,
        "merge",
        "--no-ff",
        "cross",
        "-m",
        "Merge pull request #2 from alice/cross\n\ncross-level merge",
        env=env,
    )
    result = CliRunner().invoke(root, ["provisioning-roles", "--strict"])
    assert result.exit_code == FAIL, result.output
    assert "spans levels" in (result.output + result.stderr_bytes.decode() if result.stderr_bytes else result.output)


def test_pre_gate_violation_is_warn_not_fail(synthetic_repo: Path) -> None:
    """A cross-level merge BEFORE roles.yaml lands → WARN, exit OK."""
    _branch_merge(
        synthetic_repo,
        "premerge",
        "core/old.md",
        "old",
        "old work",
        "old work",
        operator_handle="alice",
    )
    (synthetic_repo / "DEVELOPMENT_ROADMAP.md").write_text("rdm", encoding="utf-8")
    _run_git(synthetic_repo, "add", "DEVELOPMENT_ROADMAP.md")
    _run_git(synthetic_repo, "commit", "-m", "amend roadmap")
    _seed_schemas(synthetic_repo, operator_handle="alice")
    _run_git(synthetic_repo, "add", "docs/schemas/")
    _run_git(synthetic_repo, "commit", "-m", "land gate")

    result = CliRunner().invoke(root, ["provisioning-roles"])
    assert result.exit_code == OK, result.output
    assert "pre-gate" in result.output or "historical" in result.output


def test_fail_unauthorized_initiator_post_gate(synthetic_repo: Path) -> None:
    """Operator-only level + non-operator merger → FAIL under --strict.

    Targets Level 11 (`operator_only` → actors: [operator] with no community
    fallback). Authorized handle is 'alice'; merger is 'mallory' → FAIL.
    """
    _seed_schemas(synthetic_repo, operator_handle="alice")
    _run_git(synthetic_repo, "add", "docs/schemas/")
    _run_git(synthetic_repo, "commit", "-m", "land schemas")
    _branch_merge(
        synthetic_repo,
        "evil",
        "operator/runbook.md",
        "evil",
        "evil",
        "evil operator change",
        operator_handle="mallory",
    )
    result = CliRunner().invoke(root, ["provisioning-roles", "--strict"])
    assert result.exit_code == FAIL, result.output
    combined = result.output + (result.stderr_bytes.decode() if result.stderr_bytes else "")
    assert "not authorized" in combined
