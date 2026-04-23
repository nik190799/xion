"""Tests for `xion_verify.repo.find_repo_root`.

Property under test: the repo-root locator finds the root from any subdirectory
and raises cleanly when none of the witnesses exist.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xion_verify.repo import RepoRootNotFound, find_repo_root


def test_finds_root_from_root(synthetic_repo: Path) -> None:
    assert find_repo_root(start=synthetic_repo) == synthetic_repo.resolve()


def test_finds_root_from_subdirectory(synthetic_repo: Path) -> None:
    nested = synthetic_repo / "deep" / "nest" / "ed"
    nested.mkdir(parents=True)
    assert find_repo_root(start=nested) == synthetic_repo.resolve()


def test_raises_when_witnesses_absent(tmp_path: Path) -> None:
    with pytest.raises(RepoRootNotFound):
        find_repo_root(start=tmp_path)


def test_real_repo_discoverable(real_repo_root: Path) -> None:
    found = find_repo_root(start=real_repo_root)
    assert found == real_repo_root.resolve()
