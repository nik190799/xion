"""Tests for `xion_verify.hashing`.

Property under test: `sha256_file` and `sha256_bytes` are byte-for-byte
deterministic; `tree_hash` is deterministic, path-sorted, and respects the
exclude set.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from xion_verify.hashing import sha256_bytes, sha256_file, tree_hash


def test_sha256_file_matches_stdlib(tmp_path: Path) -> None:
    target = tmp_path / "probe.bin"
    data = b"xion\x00\xff\x01payload\n"
    target.write_bytes(data)
    assert sha256_file(target) == hashlib.sha256(data).hexdigest()


def test_sha256_bytes_empty_string() -> None:
    assert sha256_bytes(b"") == hashlib.sha256(b"").hexdigest()


def test_tree_hash_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("print('b')\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("print('c')\n", encoding="utf-8")

    first = tree_hash(tmp_path, ("**/*.py",))
    second = tree_hash(tmp_path, ("**/*.py",))
    assert first == second


def test_tree_hash_changes_with_content(tmp_path: Path) -> None:
    target = tmp_path / "a.py"
    target.write_text("print('a')\n", encoding="utf-8")
    before = tree_hash(tmp_path, ("**/*.py",))
    target.write_text("print('b')\n", encoding="utf-8")
    after = tree_hash(tmp_path, ("**/*.py",))
    assert before != after


def test_tree_hash_respects_exclude(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("print('a')\n", encoding="utf-8")
    b.write_text("print('b')\n", encoding="utf-8")
    full = tree_hash(tmp_path, ("**/*.py",))
    excluded = tree_hash(tmp_path, ("**/*.py",), exclude=frozenset({b.resolve()}))
    assert full != excluded


def test_tree_hash_ignores_directories(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    result = tree_hash(tmp_path, ("**/*",))
    assert result == sha256_bytes(b"")


@pytest.mark.parametrize("pattern", ["**/*.py", "*.py"])
def test_tree_hash_accepts_glob_patterns(tmp_path: Path, pattern: str) -> None:
    (tmp_path / "x.py").write_text("pass\n", encoding="utf-8")
    assert len(tree_hash(tmp_path, (pattern,))) == 64
