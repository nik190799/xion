"""Phase 6.4.b: ``topography`` and ``nervous-system`` verifiers exit OK."""

from __future__ import annotations

import pytest

from xion_verify.commands.nervous_system import verify_nervous_system
from xion_verify.commands.topography import verify_topography
from xion_verify.exit_codes import OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


def test_topography_and_nervous_system_ok() -> None:
    import io

    try:
        root = find_repo_root()
    except RepoRootNotFound:
        pytest.skip("not in a Xion checkout")
    out = io.StringIO()
    assert verify_topography(root, out) == OK
    assert "topography: OK" in out.getvalue()
    out2 = io.StringIO()
    assert verify_nervous_system(root, out2) == OK
    assert "nervous-system: OK" in out2.getvalue()
