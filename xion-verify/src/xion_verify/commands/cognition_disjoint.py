"""`xion-verify cognition-disjoint` — asserts no cross-imports between sibling plugins.

Walks `skills/`, `orchestrator/senses/`, `orchestrator/inference_router/providers/`
and asserts that no plugin imports another plugin from the same directory.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_PLUGIN_DIRS = (
    "skills",
    "orchestrator/senses",
    "orchestrator/inference_router/providers",
)


def _get_plugin_names(plugin_dir: Path) -> set[str]:
    """Return the names of all plugins in a directory."""
    if not plugin_dir.is_dir():
        return set()
    
    plugins = set()
    for child in plugin_dir.iterdir():
        if child.name.startswith("_") and child.name != "__init__.py":
            continue
        if child.is_file() and child.suffix == ".py":
            plugins.add(child.stem)
        elif child.is_dir() and (child / "__init__.py").is_file():
            plugins.add(child.name)
    
    plugins.discard("__init__")
    return plugins


def check_disjoint(repo_root: Path) -> list[str]:
    """Walk plugin directories and assert no cross-imports between siblings."""
    errors = []
    
    for rel_dir in _PLUGIN_DIRS:
        plugin_dir = repo_root / rel_dir
        if not plugin_dir.is_dir():
            continue
            
        base_module = rel_dir.replace("/", ".")
        plugins = _get_plugin_names(plugin_dir)
        
        for plugin in plugins:
            plugin_path_py = plugin_dir / f"{plugin}.py"
            plugin_path_dir = plugin_dir / plugin
            
            files_to_check = []
            if plugin_path_py.is_file():
                files_to_check.append((plugin_path_py, plugin))
            if plugin_path_dir.is_dir():
                for py_file in plugin_path_dir.rglob("*.py"):
                    files_to_check.append((py_file, plugin))
                    
            for file_path, p_name in files_to_check:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    tree = ast.parse(content, filename=str(file_path))
                except Exception as e:
                    errors.append(f"Failed to parse {file_path.relative_to(repo_root)}: {e}")
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            parts = alias.name.split(".")
                            if alias.name.startswith(f"{base_module}."):
                                imported_plugin = parts[len(base_module.split("."))]
                                if imported_plugin in plugins and imported_plugin != p_name:
                                    errors.append(f"{file_path.relative_to(repo_root)}: cross-import of sibling plugin '{imported_plugin}' via 'import {alias.name}'")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.level == 0:
                            parts = node.module.split(".")
                            if node.module.startswith(f"{base_module}."):
                                imported_plugin = parts[len(base_module.split("."))]
                                if imported_plugin in plugins and imported_plugin != p_name:
                                    errors.append(f"{file_path.relative_to(repo_root)}: cross-import of sibling plugin '{imported_plugin}' via 'from {node.module} import ...'")
                            elif node.module == base_module:
                                for alias in node.names:
                                    if alias.name in plugins and alias.name != p_name:
                                        errors.append(f"{file_path.relative_to(repo_root)}: cross-import of sibling plugin '{alias.name}' via 'from {node.module} import {alias.name}'")
                        elif node.level > 0:
                            # Relative import
                            if plugin_path_py.is_file():
                                # Single file plugin
                                if node.module and node.module in plugins and node.module != p_name:
                                    errors.append(f"{file_path.relative_to(repo_root)}: cross-import of sibling plugin '{node.module}' via relative import")
                                elif not node.module:
                                    for alias in node.names:
                                        if alias.name in plugins and alias.name != p_name:
                                            errors.append(f"{file_path.relative_to(repo_root)}: cross-import of sibling plugin '{alias.name}' via relative import")
                            else:
                                # Package plugin
                                rel_to_plugin = file_path.relative_to(plugin_path_dir)
                                # rel_to_plugin has len(rel_to_plugin.parts) parts.
                                # e.g. skills/my_skill/foo.py -> rel_to_plugin = foo.py (len 1)
                                # level 1 = my_skill, level 2 = skills
                                if node.level > len(rel_to_plugin.parts):
                                    # Escapes the package
                                    if node.level == len(rel_to_plugin.parts) + 1:
                                        # It reached the parent directory (e.g. skills/)
                                        if node.module and node.module in plugins and node.module != p_name:
                                            errors.append(f"{file_path.relative_to(repo_root)}: cross-import of sibling plugin '{node.module}' via relative import")
                                        elif not node.module:
                                            for alias in node.names:
                                                if alias.name in plugins and alias.name != p_name:
                                                    errors.append(f"{file_path.relative_to(repo_root)}: cross-import of sibling plugin '{alias.name}' via relative import")
                                    else:
                                        # Escapes even further, not necessarily a sibling plugin but bad practice for disjoint plugins
                                        pass

    return errors


@click.command(
    name="cognition-disjoint",
    help="Assert no cross-imports between sibling skills/senses/providers.",
)
def cognition_disjoint() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"cognition-disjoint: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    errors = check_disjoint(repo_root)
    if errors:
        for err in errors:
            click.echo(f"cognition-disjoint: FAIL: {err}", err=True)
        sys.exit(FAIL)

    click.echo("cognition-disjoint: OK (no cross-imports detected)")
    sys.exit(OK)
