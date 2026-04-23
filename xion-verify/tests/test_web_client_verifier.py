"""Tests for ``xion-verify web-client`` (Phase 5g-v).

The verifier audits a Vite-emitted ``clients/web/dist/`` tree for
structural integrity without running the browser or the orchestrator.
These tests build synthetic ``dist/`` trees to cover every branch
(OK, NOT_YET_SEALED, FAIL-no-CSP, FAIL-non-allowlisted-origin,
FAIL-no-default-src-self) deterministically and hermetically.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.commands.web_client import web_client
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


_GOOD_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:" />
<title>Xion</title>
<script type="module" src="/app/assets/index.js"></script>
<link rel="stylesheet" href="/app/assets/index.css" />
</head>
<body><div id="root"></div></body>
</html>
"""


def _build_dist(root: Path, *, index_html: str, js_body: str = "", css_body: str = "") -> Path:
    dist = root / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text(index_html, encoding="utf-8")
    (assets / "index.js").write_text(js_body, encoding="utf-8")
    (assets / "index.css").write_text(css_body, encoding="utf-8")
    return dist


def _invoke(dist: Path) -> tuple[int, str]:
    runner = CliRunner()
    result = runner.invoke(web_client, ["--dist-path", str(dist)])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    output = result.output
    if result.exception and not isinstance(result.exception, SystemExit):
        output += f"\n[exception] {result.exception!r}"
    return code, output


def test_missing_dist_is_not_yet_sealed(tmp_path: Path) -> None:
    code, out = _invoke(tmp_path / "does-not-exist")
    assert code == NOT_YET_SEALED
    assert "NOT_YET_SEALED" in out
    assert "npm run build" in out


def test_missing_index_is_not_yet_sealed(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    code, out = _invoke(dist)
    assert code == NOT_YET_SEALED
    assert "no index.html" in out


def test_bundle_without_csp_fails(tmp_path: Path) -> None:
    html = _GOOD_INDEX_HTML.replace(
        '<meta http-equiv="Content-Security-Policy" '
        "content=\"default-src 'self'; img-src 'self' data:\" />",
        "",
    )
    dist = _build_dist(tmp_path, index_html=html)
    code, out = _invoke(dist)
    assert code == FAIL
    assert "Content-Security-Policy" in out


def test_bundle_without_default_src_self_fails(tmp_path: Path) -> None:
    html = _GOOD_INDEX_HTML.replace("default-src 'self'", "default-src https://example.org")
    dist = _build_dist(tmp_path, index_html=html)
    code, out = _invoke(dist)
    assert code == FAIL
    assert "default-src 'self'" in out


def test_bundle_with_non_allowlisted_origin_fails(tmp_path: Path) -> None:
    # A stray CDN URL baked into the JS — exactly what the verifier exists to catch.
    js = "fetch('https://evil.example.org/tracker.js');\n"
    dist = _build_dist(tmp_path, index_html=_GOOD_INDEX_HTML, js_body=js)
    code, out = _invoke(dist)
    assert code == FAIL
    assert "non-allowlisted origin" in out
    assert "evil.example.org" in out


def test_react_error_decoder_is_allowlisted(tmp_path: Path) -> None:
    js = (
        "throw new Error('Minified React error; visit "
        "https://reactjs.org/docs/error-decoder.html?invariant=42');\n"
    )
    dist = _build_dist(tmp_path, index_html=_GOOD_INDEX_HTML, js_body=js)
    code, out = _invoke(dist)
    assert code == OK, out
    assert "React production error-decoder URL" in out


def test_w3c_namespace_ids_are_allowlisted(tmp_path: Path) -> None:
    js = (
        "createElementNS('http://www.w3.org/2000/svg','svg');\n"
        "createElementNS('http://www.w3.org/1999/xhtml','div');\n"
        "setAttributeNS('http://www.w3.org/1999/xlink','href','#x');\n"
    )
    dist = _build_dist(tmp_path, index_html=_GOOD_INDEX_HTML, js_body=js)
    code, out = _invoke(dist)
    assert code == OK, out
    assert "W3C XML namespace identifier" in out


def test_clean_bundle_passes(tmp_path: Path) -> None:
    dist = _build_dist(tmp_path, index_html=_GOOD_INDEX_HTML, js_body="const x=1;\n")
    code, out = _invoke(dist)
    assert code == OK, out
    assert "web-client: OK" in out
    assert "default-src 'self'" in out


def test_svg_file_is_scanned(tmp_path: Path) -> None:
    """SVG files are text and must also be swept for non-self origins."""
    dist = _build_dist(tmp_path, index_html=_GOOD_INDEX_HTML)
    (dist / "assets" / "logo.svg").write_text(
        "<svg xmlns='http://www.w3.org/2000/svg'>"
        "<image href='https://cdn.leak.example/logo.png'/>"
        "</svg>",
        encoding="utf-8",
    )
    code, out = _invoke(dist)
    assert code == FAIL
    assert "cdn.leak.example" in out
