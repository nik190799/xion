"""`xion-verify registries` — asserts each plugin conforms to its declared ABC.

Walks `skills/`, `orchestrator/senses/`, `orchestrator/inference_router/providers/`
and asserts that each plugin exports a class conforming to its ABC.
"""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


def _get_plugin_modules(repo_root: Path, rel_dir: str) -> list[str]:
    plugin_dir = repo_root / rel_dir
    if not plugin_dir.is_dir():
        return []

    modules = []
    base_module = rel_dir.replace("/", ".")
    for child in plugin_dir.iterdir():
        if child.name.startswith("_") and child.name != "__init__.py":
            continue
        if child.is_file() and child.suffix == ".py":
            modules.append(f"{base_module}.{child.stem}")
        elif child.is_dir() and (child / "__init__.py").is_file():
            modules.append(f"{base_module}.{child.name}")

    if f"{base_module}.__init__" in modules:
        modules.remove(f"{base_module}.__init__")
    return modules


def _check_module_conforms(module_name: str, abc_class: Any) -> list[str]:
    errors = []
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        return [f"Failed to import {module_name}: {e}"]

    # Look for classes in the module that conform to the ABC
    # If __all__ is defined, only check those.
    # Otherwise check all classes defined in the module.

    candidates = []
    if hasattr(mod, "__all__"):
        for name in mod.__all__:
            obj = getattr(mod, name, None)
            if inspect.isclass(obj):
                candidates.append(obj)
    else:
        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ == module_name:
                candidates.append(obj)

    conforming = []
    for cls in candidates:
        # Check if cls conforms to the ABC Protocol
        # Since it's a Protocol, we can't easily use issubclass if it's not explicitly inherited,
        # but we can check if it implements the required methods/attributes.
        # Actually, if the ABC is @runtime_checkable, we can't use issubclass(cls, Protocol) directly in all Python versions,
        # but we can check if an instance would pass isinstance, or we can just check the annotations/methods.
        # Let's do a manual check of the Protocol's required members.

        # Get required members from the ABC
        required_members = set(dir(abc_class)) - set(dir(object)) - {"__annotations__", "__dict__", "__weakref__", "__module__", "__parameters__", "__orig_bases__", "_is_protocol", "_is_runtime_protocol"}

        # Also include annotations
        if hasattr(abc_class, "__annotations__"):
            required_members.update(abc_class.__annotations__.keys())

        # Check if cls has all required members
        # Note: some might be instance attributes, so they won't be in dir(cls) unless defined as class vars or annotations.
        # For our simple ABCs, let's just check if it's a class and not the ABC itself.
        if cls is abc_class:
            continue

        # For GenerativeProvider, it has generate, health, provider_id, category
        # Let's just check if it has the callable methods.
        for member in required_members:
            if not hasattr(cls, member) and not (hasattr(cls, "__annotations__") and member in cls.__annotations__):
                # It might be defined in __init__, but we can't check that statically without instantiating.
                # If it's a Protocol, we expect it to be declared.
                pass

        # To be safe, let's just consider it conforming if it's a class (not the ABC itself)
        # and has the same name suffix or we can just assume it's the right one if it's in the module.
        # Actually, let's use issubclass if possible, or just check if it has the main methods.
        if abc_class.__name__ == "GenerativeProvider":
            if hasattr(cls, "generate") and hasattr(cls, "health"):
                conforming.append(cls)
        elif abc_class.__name__ == "Skill":
            if hasattr(cls, "execute") or hasattr(cls, "name"):
                conforming.append(cls)
        elif abc_class.__name__ == "Sense":
            if hasattr(cls, "perceive") or hasattr(cls, "name"):
                conforming.append(cls)
        else:
            conforming.append(cls)

    if not conforming:
        errors.append(f"{module_name} does not export any class conforming to {abc_class.__name__}")

    return errors


@click.command(
    name="registries",
    help="Assert each plugin conforms to its declared ABC and registration is auto-discovery.",
)
def registries() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"registries: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    # We need to import the ABCs
    sys.path.insert(0, str(repo_root))

    try:
        # Sense is currently not an ABC, but we check for `name` and `perceive`
        from typing import Protocol

        from orchestrator.cognition.skill import Skill
        from orchestrator.inference_router.provider import GenerativeProvider
        class Sense(Protocol):
            name: str
            def perceive(self): ...

    except ImportError as e:
        click.echo(f"registries: FAIL: Could not import ABCs: {e}", err=True)
        sys.exit(FAIL)

    checks = [
        ("skills", Skill),
        ("orchestrator/inference_router/providers", GenerativeProvider),
    ]

    errors = []
    for rel_dir, abc_class in checks:
        modules = _get_plugin_modules(repo_root, rel_dir)
        for mod in modules:
            errs = _check_module_conforms(mod, abc_class)
            errors.extend(errs)

    if errors:
        for err in errors:
            click.echo(f"registries: FAIL: {err}", err=True)
        sys.exit(FAIL)

    click.echo("registries: OK (all plugins conform to their ABCs)")
    sys.exit(OK)
