"""``xion-verify web-client`` — web-client bundle audit (Phase 5g-v).

Doctrine anchors:
    docs/04-ARCHITECTURE.md § "The Web Client Surface (Phase 5g-v)"
    docs/31-WEB-CLIENT.md (operational doctrine)

Landed with the 5g-v web-client surface. The verifier's job is to
assert the six structural properties the architecture document pins,
specifically the ones that can be checked from the emitted bundle on
disk without running the orchestrator or the browser:

  (P4) Same-origin serve. The emitted ``index.html`` references its
       assets at absolute paths under ``/app/`` (not ``https://…``).
       We structurally grep the HTML for any ``https?://`` origin.
  (P5) No third-party origins in the JS/CSS bundle. The emitted JS
       and CSS are grepped for ``https?://`` origins; every unique
       origin must match the allowlist below.
  (CSP) The HTML shell carries a ``Content-Security-Policy`` meta tag
       with ``default-src 'self'``. This is defence-in-depth on top
       of (P4) / (P5).

Allowlist (the only non-self origins the emitted bundle may carry):

  - ``https://reactjs.org/docs/error-decoder.html`` — a literal
    string React prints in production error messages. Never fetched
    at runtime (it is the prefix of an error-code URL the dev is
    expected to visit manually in a browser). React ships this in
    every production build.

If the operator has not yet built the bundle (``clients/web/dist/``
does not exist or is missing ``index.html``), the verifier returns
``NOT_YET_SEALED`` — not ``FAIL``. This mirrors the 5g-iv
``api-tokens`` posture: a config that does not yet exist is
unverifiable, not wrong.

What this verifier does NOT do (with an honest pointer):

  * It does not run the SPA in a browser; axe-core + Vitest tests
    handle runtime accessibility and envelope-matrix conformance in
    the clients/web/ CI workflow.
  * It does not verify the in-browser CSP is enforced by the server.
    The server-side ``WebClientConfig`` mount is covered by
    ``orchestrator/tests/test_api_web_client.py``.
  * It does not verify the specific JS minification or chunking
    shape. Vite may legitimately re-chunk bundles between releases;
    the structural grep is shape-stable.

Exit codes:

  0 OK              bundle exists and every structural invariant
                    passes; summary printed.
  1 FAIL            bundle exists but a non-allowlisted origin
                    appears, or the CSP meta is missing.
  2 NOT_YET_SEALED  dist/ or index.html does not exist — operator
                    has not run ``npm run build`` yet.
"""

from __future__ import annotations

import re
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


def _default_dist() -> Path | None:
    try:
        return find_repo_root(Path.cwd()) / "clients" / "web" / "dist"
    except RepoRootNotFound:
        return None

# Allowlisted non-self origins. Every entry MUST have an explicit
# comment naming why it is permitted. A new entry requires:
#   1) a doctrine-level justification (why this origin is safe),
#   2) a note in docs/31-WEB-CLIENT.md § "Allowlisted non-self origins",
#   3) a PINNED_HASH re-pin.
_NON_SELF_ALLOWLIST: tuple[tuple[str, str], ...] = (
    (
        # React's production error-decoder URL. Literal string prefix
        # printed inside ``new Error(...)``; never fetched at runtime.
        # React 18.x (and 19+) ship this in every production build.
        r"^https?://reactjs\.org/docs/error-decoder\.html",
        "React production error-decoder URL (literal; never fetched)",
    ),
    (
        # React's canonical GitHub redirect used for newer minified
        # error messages (react 19+). Same semantics as above.
        r"^https?://react\.dev/errors/",
        "React.dev error decoder (literal; never fetched)",
    ),
    (
        # W3C XML namespace URIs. These are identifiers, not URLs —
        # the DOM, SVG, MathML, and XLink specifications require the
        # exact literal strings ``http://www.w3.org/…`` to namespace
        # elements and attributes. Browsers never fetch them. React
        # ships ``createElementNS`` / ``setAttributeNS`` call sites
        # that pass these as namespace identifiers in every bundle.
        r"^https?://www\.w3\.org/(1999/xhtml|2000/svg|1998/Math/MathML|1999/xlink|XML/1998/namespace)",
        "W3C XML namespace identifier (literal; never fetched)",
    ),
)

_ORIGIN_RE = re.compile(r"https?://[^\s\"'`<>)]+", re.MULTILINE)


def _fail(message: str) -> None:
    click.echo(f"web-client: FAIL: {message}", err=True)
    raise SystemExit(FAIL)


def _not_yet_sealed(message: str) -> None:
    click.echo(f"web-client: NOT_YET_SEALED — {message}")
    raise SystemExit(NOT_YET_SEALED)


def _matches_allowlist(url: str) -> tuple[bool, str]:
    for pattern, reason in _NON_SELF_ALLOWLIST:
        if re.match(pattern, url):
            return True, reason
    return False, ""


def _collect_origins_in_tree(dist: Path) -> dict[str, list[Path]]:
    """Walk the dist tree and return {origin: [files_that_reference_it]}.

    Only text files (HTML/JS/CSS/SVG/JSON) are scanned; binary assets
    (fonts, images) are skipped.
    """
    origins: dict[str, list[Path]] = {}
    text_suffixes = {".html", ".js", ".mjs", ".css", ".svg", ".json", ".map"}
    for path in sorted(dist.rglob("*")):
        if not path.is_file() or path.suffix not in text_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in _ORIGIN_RE.finditer(text):
            origin = match.group(0).rstrip(",;.)")
            origins.setdefault(origin, []).append(path.relative_to(dist))
    return origins


@click.command(name="web-client")
@click.option(
    "--dist-path",
    "dist_path_arg",
    type=click.Path(path_type=Path),
    default=None,
    help=(
        "Path to the built SPA bundle (default: <repo>/clients/web/dist). "
        "Used by operators who ship the bundle from an external artifact "
        "store and want to audit the deploy artifact before cut-over."
    ),
)
def web_client(dist_path_arg: Path | None) -> None:
    """Audit the Phase 5g-v web-client bundle for structural integrity."""
    if dist_path_arg is not None:
        dist = dist_path_arg.resolve()
    else:
        default = _default_dist()
        if default is None:
            _fail(
                "not invoked from inside the xion-os repo and --dist-path "
                "was not provided. Pass --dist-path <bundle> or run from a "
                "clone of the repo."
            )
            return
        dist = default.resolve()

    if not dist.is_dir():
        _not_yet_sealed(
            f"dist directory not found at {dist}. "
            "Run `cd clients/web && npm ci && npm run build` first. "
            "(This is expected before the operator's first deploy.)"
        )

    index_html = dist / "index.html"
    if not index_html.is_file():
        _not_yet_sealed(
            f"{dist} exists but has no index.html. "
            "The Vite build output is incomplete; re-run "
            "`cd clients/web && npm run build`."
        )

    # ---- CSP meta-tag check (structural; not a guarantee of in-browser enforcement)
    html_text = index_html.read_text(encoding="utf-8", errors="ignore")
    if 'http-equiv="Content-Security-Policy"' not in html_text:
        _fail(
            f"{index_html} is missing a Content-Security-Policy meta tag. "
            "Every Phase 5g-v bundle must carry a same-origin CSP; see "
            "clients/web/index.html for the canonical shape."
        )
    if "default-src 'self'" not in html_text:
        _fail(
            f"{index_html} CSP meta tag does not pin default-src 'self'. "
            "This is a constitutional requirement of the web-client surface."
        )

    # ---- Non-self origin sweep across the emitted tree
    origins = _collect_origins_in_tree(dist)
    disallowed: list[tuple[str, list[Path]]] = []
    allowed_counts: dict[str, int] = {}
    for origin, files in origins.items():
        is_allowed, reason = _matches_allowlist(origin)
        if not is_allowed:
            disallowed.append((origin, files))
        else:
            allowed_counts[reason] = allowed_counts.get(reason, 0) + 1

    if disallowed:
        lines = ["non-allowlisted origin(s) in the emitted bundle:"]
        for origin, files in disallowed:
            file_list = ", ".join(str(f) for f in files[:3])
            if len(files) > 3:
                file_list += f", …(+{len(files) - 3} more)"
            lines.append(f"  {origin}   (in: {file_list})")
        lines.append(
            "Each entry must be justified in docs/31-WEB-CLIENT.md § "
            "'Allowlisted non-self origins' and added to "
            "xion-verify/src/xion_verify/commands/web_client.py "
            "_NON_SELF_ALLOWLIST before the bundle can pass."
        )
        _fail("\n".join(lines))

    # ---- Structural summary
    file_count = sum(1 for _ in dist.rglob("*") if _.is_file())
    click.echo(f"web-client: OK  dist={dist}  files={file_count}")
    click.echo(f"  index.html carries Content-Security-Policy meta (default-src 'self')")
    click.echo(f"  origins scanned: {len(origins)} unique")
    if allowed_counts:
        for reason, count in sorted(allowed_counts.items()):
            click.echo(f"    allowlist match × {count}: {reason}")
    else:
        click.echo("    all origins self-same (no allowlist matches needed)")
    raise SystemExit(OK)


__all__ = ["web_client"]
