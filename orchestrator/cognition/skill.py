"""Skill Protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Skill(Protocol):
    """A registered skill."""
    name: str
