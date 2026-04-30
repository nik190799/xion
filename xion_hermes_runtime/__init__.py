"""Vendored Hermes runtime pin adapter for Xion Genesis.

This package is intentionally small: it records the exact upstream Hermes Agent
identity Xion casts against while the integration remains mediated by Xion's
own cognition wrappers.
"""

HERMES_AGENT_REPO = "https://github.com/nousresearch/hermes-agent"
HERMES_AGENT_TAG = "v2026.4.16"
HERMES_AGENT_COMMIT = "4a0358d2e741eb049a6ffb9b8e610db946a4fec5"
__version__ = "0.1.0"


def describe_runtime() -> dict[str, str]:
    return {
        "package": "xion-hermes-runtime",
        "version": __version__,
        "repo": HERMES_AGENT_REPO,
        "tag": HERMES_AGENT_TAG,
        "commit": HERMES_AGENT_COMMIT,
    }
