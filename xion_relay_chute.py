"""Repo-root Chutes deployment module for the Xion Relay (D3 smoke build).

The Chutes CLI in this environment only accepts a top-level module reference
(``xion_relay_chute:chute``), so the deployable object stays self-contained
here.

What this module promises (Four Questions, per The-Xion-Builder):

- *Property*: a public Chutes deployment exists for chute id
  ``89866bfc-5ddd-5382-b887-116d8901808f`` whose three cords (``GET /health``,
  ``GET /xpricing``, ``GET /self``) return deterministic JSON without any
  external dependency.  This is the Relay registry's first honestly-served
  endpoint and the precondition for ``xion-verify discovery`` against
  Chutes.  The public cord is ``/xpricing`` (not ``/pricing``) because
  ``/pricing`` is intercepted by the Chutes platform proxy itself; see
  the routing-facts comment block below for the full empirical history.
- *Invariants touched*: none.  This is doctrine-bounded discovery surface
  (Phase B4 of the D2/D3 closure plan), not a constitutional artifact.  The
  full Relay (Arbiter + Hermes + ledgers) is provisioned in a follow-up
  commit; this build promises only that the cord pipeline is alive.
- *Verification*: ``scripts/debug-chute-d3.sh`` exercises the public
  endpoints; the response shape is asserted by ``xion-verify discovery``
  once we re-promote that verifier in a follow-up.
- *Deprecation*: replaced by the full Relay subprocess once
  ``orchestrator/api/launcher.py`` lands a sound ``AppDeps(relay=...)``
  construction.  Until then this module's smoke responses are tagged
  ``service="xion-relay-chutes-smoke"`` so a third party reading the cord
  output can see we are not yet serving the live Relay surface.

Why this shape *now*: an earlier build (``pre-genesis-d3-3``) tried to
``Popen`` ``uvicorn`` against ``orchestrator.api.app.create_app`` with a
hand-rolled ``AppDeps(cast_pool_on_boot=False)``.  That call raises
``TypeError: AppDeps.__init__() missing required positional argument:
'relay'`` immediately, the subprocess dies, ``_wait_for_relay()`` then
times out, and the Chutes platform deactivates the instance.  The next
proper fix is a small ``orchestrator/api/launcher.py`` that constructs a
real ``Relay`` and a real ``AppDeps``.  Until that lands we ship this
honest, named-as-smoke build so the Chutes cord pipeline itself is not
the unknown.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from chutes.chute import Chute, NodeSelector
from chutes.image import Image


SERVICE_NAME = "xion-relay-chutes-smoke"
IMAGE_TAG = "pre-genesis-d3-7"

# Three routing facts the D3-4 / D3-5 / D3-6 builds proved against the
# live Chutes platform, recorded so the next maintainer does not relearn
# them:
#
# 1. ``GET /pricing`` on ``*.chutes.ai`` is intercepted by the Chutes
#    platform proxy itself — it returns the platform's GPU pricing payload
#    ({"tao_usd":..., "gpu_price_estimates":{...}}) before the request
#    ever reaches a chute cord.  We saw this on a live ``pre-genesis-d3-5``
#    instance with ``/health`` and ``/self`` simultaneously returning the
#    chute's own envelope.
# 2. The two-segment public path ``/xion/pricing`` consistently returns a
#    fast (<200 ms) ``502 Bad Gateway`` from the platform's nginx ingress.
# 3. Even with the public path moved to single-segment ``/xpricing`` on
#    the d3-6 build, requests still 502'd in <200 ms.  The cause is that
#    the Chutes ``Cord`` defaults the *internal* upstream path to the
#    Python function name (``self.path = func.__name__``), so a function
#    named ``pricing`` exposes internal path ``/pricing`` even when the
#    public path is renamed.  The Chutes Aegis layer on the worker
#    rejects the upstream ``/pricing`` path the same way the public proxy
#    does, surfacing as a fast nginx 502.
#
# The fix that closes B4 is therefore to (a) rename the *Python function*
# off ``pricing`` to ``xpricing`` so the internal upstream cord path is
# also ``/xpricing``, and (b) keep the public path at ``/xpricing``.  The
# in-process FastAPI Relay (when the full surface lands) still serves
# ``/pricing`` locally — only the Chutes-deployed cord is renamed.
# ``/health`` and ``/self`` are not reserved and route straight through,
# so they keep their canonical Relay paths.


image = (
    Image(
        username="nikhilkadalge",
        name="xion-relay",
        tag=IMAGE_TAG,
        readme=(
            "Xion pre-genesis Relay runtime image — D3 cord smoke build. "
            "Static cord responses only; full Relay subprocess returns in a "
            "follow-up build."
        ),
    )
    .from_base("parachutes/python:3.12")
    .run_command("python -m pip install --user --no-cache-dir chutes")
    .with_env("XION_CHUTE_SERVICE", SERVICE_NAME)
    .with_env("XION_CHUTE_IMAGE_TAG", IMAGE_TAG)
)


chute = Chute(
    username="nikhilkadalge",
    name="xion-relay-pre-genesis-d3",
    tagline="Xion pre-genesis Relay on Chutes (smoke build)",
    readme=(
        "Xion Relay deployment adapter for D3 discovery verification. "
        "This build serves static cord responses while the full Relay "
        "subprocess (Arbiter + Hermes + ledgers) is rebuilt against a "
        "correctly-constructed AppDeps in a follow-up image."
    ),
    image=image,
    node_selector=NodeSelector(gpu_count=1, min_vram_gb_per_gpu=16),
    concurrency=4,
    max_instances=1,
    shutdown_after_seconds=300,
    allow_external_egress=False,
)


def _smoke_envelope(endpoint: str) -> dict[str, Any]:
    """Build the deterministic smoke-response envelope shared by all cords.

    The shape names what is and is not promised: ``status="ok"`` means the
    cord pipeline is alive; ``service`` discloses that we are running the
    smoke build, not the full Relay surface; ``image_tag`` lets a third
    party correlate a probe response to the exact Chutes image; ``endpoint``
    distinguishes the three cords; ``timestamp`` is a UTC isoformat string
    so the response is human-readable but never used for trust.
    """

    return {
        "status": "ok",
        "service": os.environ.get("XION_CHUTE_SERVICE", SERVICE_NAME),
        "image_tag": os.environ.get("XION_CHUTE_IMAGE_TAG", IMAGE_TAG),
        "endpoint": endpoint,
        "timestamp": datetime.now(UTC).isoformat(),
        "note": (
            "Smoke build — full Relay surface (Arbiter + Hermes + ledgers) "
            "lands in a follow-up image once AppDeps is constructed with a "
            "real Relay."
        ),
    }


@chute.cord(public_api_path="/health", public_api_method="GET")
async def health(self) -> dict[str, Any]:
    return _smoke_envelope("/health")


@chute.cord(public_api_path="/xpricing", public_api_method="GET")
async def xpricing(self) -> dict[str, Any]:
    return _smoke_envelope("/xpricing")


@chute.cord(public_api_path="/self", public_api_method="GET")
async def self_endpoint(self) -> dict[str, Any]:
    return _smoke_envelope("/self")


__all__ = ["chute"]
