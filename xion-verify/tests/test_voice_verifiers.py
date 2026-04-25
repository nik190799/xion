"""voice-sovereignty and voice-form verifiers."""

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_voice_sovereignty_ok() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "xion_verify", "voice-sovereignty"],
        cwd=_repo_root(),
        check=False,
        text=True,
        capture_output=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, out
    assert "OK" in out


def test_voice_form_ok() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "xion_verify", "voice-form"],
        cwd=_repo_root(),
        check=False,
        text=True,
        capture_output=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, out
    assert "OK" in out
