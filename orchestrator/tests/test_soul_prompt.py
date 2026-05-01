"""Tests for the Soul Prompt loader."""

import hashlib
from unittest.mock import patch

import pytest

from orchestrator.cognition.soul_prompt import (
    SoulPromptHashMismatchError,
    load_soul_prompt,
)


def test_load_soul_prompt_success(tmp_path):
    """load_soul_prompt() returns the pinned-hash body."""
    repo_root = tmp_path / "repo"
    genesis = repo_root / "genesis"
    genesis.mkdir(parents=True)

    prompt_file = genesis / "SOUL_PROMPT.md"
    body = "## Covenant Block\nI am Xion.\n"
    prompt_file.write_bytes(body.encode("utf-8"))

    actual_hash = hashlib.sha256(prompt_file.read_bytes()).hexdigest()

    with (
        patch("orchestrator.cognition.soul_prompt._find_repo_root", return_value=repo_root),
        patch("orchestrator.cognition.soul_prompt.PINNED_SOUL_PROMPT_SHA256", actual_hash),
    ):
        # Clear cache
        import orchestrator.cognition.soul_prompt as sp

        sp._cached_body = None
        sp._cached_mtime = 0.0

        loaded = load_soul_prompt()
        assert "## Covenant Block" in loaded
        assert "I am Xion." in loaded


def test_load_soul_prompt_hash_mismatch(tmp_path):
    """Mutating the file by one byte raises SoulPromptHashMismatchError."""
    repo_root = tmp_path / "repo"
    genesis = repo_root / "genesis"
    genesis.mkdir(parents=True)

    prompt_file = genesis / "SOUL_PROMPT.md"
    body = "## Covenant Block\nI am Xion.\n"
    prompt_file.write_bytes(body.encode("utf-8"))

    with (
        patch("orchestrator.cognition.soul_prompt._find_repo_root", return_value=repo_root),
        patch("orchestrator.cognition.soul_prompt.PINNED_SOUL_PROMPT_SHA256", "wronghash"),
    ):
        # Clear cache
        import orchestrator.cognition.soul_prompt as sp

        sp._cached_body = None
        sp._cached_mtime = 0.0

        with pytest.raises(SoulPromptHashMismatchError) as exc_info:
            load_soul_prompt()
        assert "hash mismatch" in str(exc_info.value)
