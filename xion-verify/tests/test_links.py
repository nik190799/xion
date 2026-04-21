"""Tests for `xion-verify links`.

Property under test: the link scanner catches broken cross-references in
doctrine, respects the ALLOWED_FORWARD_REFS.txt allowlist, and passes against
the current repo state.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import root as cli_root
from xion_verify.commands.links import (
    check_link,
    find_broken_links,
    load_allowed_forward_refs,
)
from xion_verify.exit_codes import FAIL, OK


@contextmanager
def _chdir(target: Path) -> Iterator[None]:
    prior = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(prior)


def test_scheme_allowlist_permits_external(synthetic_repo: Path) -> None:
    source = synthetic_repo / "docs" / "00-INDEX.md"
    assert check_link(source, "https://example.com", synthetic_repo, frozenset()) is None
    assert check_link(source, "mailto:alice@example.org", synthetic_repo, frozenset()) is None
    assert check_link(source, "ar://tx_id", synthetic_repo, frozenset()) is None


def test_anchor_only_link_is_ok(synthetic_repo: Path) -> None:
    source = synthetic_repo / "docs" / "00-INDEX.md"
    assert check_link(source, "#section-heading", synthetic_repo, frozenset()) is None


def test_ceremony_placeholder_is_ok(synthetic_repo: Path) -> None:
    source = synthetic_repo / "docs" / "00-INDEX.md"
    assert check_link(source, "<<AO_PROCESS_ID>>", synthetic_repo, frozenset()) is None


def test_broken_relative_link_is_reported(synthetic_repo: Path) -> None:
    source = synthetic_repo / "docs" / "00-INDEX.md"
    reason = check_link(source, "./not-here.md", synthetic_repo, frozenset())
    assert reason is not None
    assert "does not exist" in reason


def test_allowed_forward_ref_is_tolerated(synthetic_repo: Path) -> None:
    source = synthetic_repo / "docs" / "00-INDEX.md"
    allow = frozenset({"docs/future.md"})
    reason = check_link(source, "./future.md", synthetic_repo, allow)
    assert reason is None


def test_find_broken_links_catches_typos(synthetic_repo: Path) -> None:
    broken_doc = synthetic_repo / "docs" / "drift.md"
    broken_doc.write_text(
        "See [missing](./does-not-exist.md) for details.\n",
        encoding="utf-8",
    )
    broken = find_broken_links(synthetic_repo)
    assert any(b.target.endswith("does-not-exist.md") for b in broken)


def test_real_repo_links_clean(real_repo_root: Path) -> None:
    runner = CliRunner()
    with _chdir(real_repo_root):
        result = runner.invoke(cli_root, ["links"])
    assert result.exit_code == OK, result.output


def test_malformed_allowlist_raises(tmp_path: Path) -> None:
    allowlist_dir = tmp_path / "xion-verify"
    allowlist_dir.mkdir()
    (allowlist_dir / "ALLOWED_FORWARD_REFS.txt").write_text(
        "this-line-has-no-commas\n", encoding="utf-8"
    )
    try:
        load_allowed_forward_refs(tmp_path)
    except ValueError as exc:
        assert "malformed" in str(exc)
    else:
        raise AssertionError("expected ValueError on malformed allowlist")


def test_synthetic_links_scanner_runs(synthetic_repo: Path) -> None:
    runner = CliRunner()
    with _chdir(synthetic_repo):
        result = runner.invoke(cli_root, ["links"])
    assert result.exit_code in (OK, FAIL)
