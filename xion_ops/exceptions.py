"""Exceptions for Xion operator automation.

These exceptions name the boundary that failed so callers can distinguish an
operator funding issue from a provider-ingress fault or a rollback event.
"""

from __future__ import annotations


class OpsError(RuntimeError):
    """Base class for xion-ops failures."""


class ConfigError(OpsError):
    """Configuration or funding-target registry is malformed."""


class FundingShortfall(OpsError):
    """A wallet is below its declared deployment target."""


class ProviderUnreachable(OpsError):
    """A provider reported readiness but its public endpoint was unreachable."""


class CommandFailed(OpsError):
    """An external command failed."""


class DeployRollbackTriggered(OpsError):
    """A deployment failed after allocation and rollback was attempted."""

