"""Tests for xion_ops.cli Chutes bearer file helper."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from xion_ops.cli import _read_chutes_bearer_file


def test_read_bearer_plain_first_line(tmp_path: Path) -> None:
    p = tmp_path / "t.txt"
    p.write_text("  sekrit-token  \n", encoding="utf-8")
    assert _read_chutes_bearer_file(p) == "sekrit-token"


def test_read_bearer_env_format(tmp_path: Path) -> None:
    p = tmp_path / "t.env"
    p.write_text("CHUTES_API_KEY=abc-def\n", encoding="utf-8")
    assert _read_chutes_bearer_file(p) == "abc-def"


def test_read_bearer_xion_prefix(tmp_path: Path) -> None:
    p = tmp_path / "t.env"
    p.write_text("XION_CHUTES_API_KEY=gateway\n", encoding="utf-8")
    assert _read_chutes_bearer_file(p) == "gateway"


def test_read_bearer_empty_raises(tmp_path: Path) -> None:
    p = tmp_path / "empty.txt"
    p.write_text("# only comment\n\n", encoding="utf-8")
    with pytest.raises(click.BadParameter, match="empty or missing"):
        _read_chutes_bearer_file(p)
