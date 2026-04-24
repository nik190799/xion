"""Sense Protocol."""

from typing import Protocol, runtime_checkable

@runtime_checkable
class Sense(Protocol):
    """A registered sense."""
    name: str
