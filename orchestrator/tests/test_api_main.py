"""Tests for the orchestrator/api/__main__.py launcher.

Finding #3: XION_DOTENV_PATH opt-in loader.
"""

import os
import sys
from unittest.mock import patch

import pytest

from orchestrator.api.__main__ import _maybe_load_dotenv


def test_maybe_load_dotenv_unset(capsys):
    """Unset XION_DOTENV_PATH -> no load, no stderr line."""
    with patch.dict(os.environ, clear=True):
        _maybe_load_dotenv()
        captured = capsys.readouterr()
        assert captured.err == ""


def test_maybe_load_dotenv_missing_path(capsys):
    """Set to a missing path -> SystemExit(2) + State-of-Xion line."""
    with patch.dict(os.environ, {"XION_DOTENV_PATH": "/does/not/exist/12345"}):
        with pytest.raises(SystemExit) as exc_info:
            _maybe_load_dotenv()
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "State-of-Xion:" in captured.err
        assert "does not exist or is not a file" in captured.err


def test_maybe_load_dotenv_success(tmp_path, capsys):
    """Set to a real tmp_path/.env -> values land in os.environ, existing keys are preserved."""
    env_file = tmp_path / ".env"
    env_file.write_text("XION_TEST_KEY=from_file\nXION_TEST_OVERRIDE=from_file\n")

    # Set up environ where XION_TEST_OVERRIDE is already set
    with patch.dict(
        os.environ,
        {
            "XION_DOTENV_PATH": str(env_file),
            "XION_TEST_OVERRIDE": "from_env",
        },
        clear=True,
    ):
        _maybe_load_dotenv()
        
        # New key should be added
        assert os.environ.get("XION_TEST_KEY") == "from_file"
        # Existing key should be preserved (override=False)
        assert os.environ.get("XION_TEST_OVERRIDE") == "from_env"

        captured = capsys.readouterr()
        assert "State-of-Xion: dotenv loaded from" in captured.err
        assert "2 keys, 1 applied" in captured.err
