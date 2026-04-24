"""`xion-verify new` — scaffold generators for Xion plugins.

Generates working skeletons with the eight-question template, local Arbiter
hook, and pytest scaffold.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_EIGHT_QUESTION_TEMPLATE = '''"""
1. What property does this promise?
   TODO: ...
2. What Invariants does it touch?
   TODO: ...
3. How is it verified?
   TODO: ...
4. How is it deprecated?
   TODO: ...
5. What is the blast radius?
   TODO: ...
6. What is the cost envelope?
   TODO: ...
7. What is the failure mode?
   TODO: ...
8. How does it fail safely?
   TODO: ...
"""
'''


def _write_file(path: Path, content: str) -> None:
    if path.exists():
        click.echo(f"new: FAIL: {path} already exists", err=True)
        sys.exit(FAIL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    click.echo(f"Created {path}")


@click.group(name="new", help="Scaffold generators for Xion plugins.", invoke_without_command=True)
@click.pass_context
def new_cmd(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(OK)


@new_cmd.command(name="skill", help="Generate a new skill skeleton.")
@click.argument("name")
def new_skill(name: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"new: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    plugin_dir = repo_root / "skills" / name
    _write_file(plugin_dir / "__init__.py", f"{_EIGHT_QUESTION_TEMPLATE}\nfrom .skill import {name.title()}Skill\n\n__all__ = ['{name.title()}Skill']\n")
    _write_file(plugin_dir / "skill.py", f'''from orchestrator.cognition.skill import Skill

class {name.title()}Skill:
    name = "{name}"
    
    def execute(self) -> str:
        # TODO: Implement local Arbiter hook
        return "success"
''')
    _write_file(repo_root / "tests" / "skills" / f"test_{name}.py", f'''from skills.{name}.skill import {name.title()}Skill

def test_{name}_execute() -> None:
    skill = {name.title()}Skill()
    assert skill.execute() == "success"
''')
    sys.exit(OK)


@new_cmd.command(name="sense", help="Generate a new sense skeleton.")
@click.argument("name")
def new_sense(name: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"new: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    plugin_dir = repo_root / "orchestrator" / "senses" / name
    _write_file(plugin_dir / "__init__.py", f"{_EIGHT_QUESTION_TEMPLATE}\nfrom .sense import {name.title()}Sense\n\n__all__ = ['{name.title()}Sense']\n")
    _write_file(plugin_dir / "sense.py", f'''from orchestrator.sensorium.senses import Sense

class {name.title()}Sense:
    name = "{name}"
    
    def perceive(self) -> str:
        # TODO: Implement local Arbiter hook
        return "perception"
''')
    _write_file(repo_root / "orchestrator" / "tests" / "senses" / f"test_{name}.py", f'''from orchestrator.senses.{name}.sense import {name.title()}Sense

def test_{name}_perceive() -> None:
    sense = {name.title()}Sense()
    assert sense.perceive() == "perception"
''')
    sys.exit(OK)


@new_cmd.command(name="provider", help="Generate a new provider skeleton.")
@click.argument("name")
def new_provider(name: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"new: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    plugin_file = repo_root / "orchestrator" / "inference_router" / "providers" / f"{name}.py"
    _write_file(plugin_file, f'''{_EIGHT_QUESTION_TEMPLATE}
from orchestrator.inference_router.provider import GenerationResult

class {name.title()}GenerativeProvider:
    provider_id = "{name}"
    category = "hosted_api"
    
    def health(self) -> bool:
        return True
        
    def generate(self, prompt: str, *, system: str | None, max_tokens: int, deadline_s: float) -> GenerationResult:
        # TODO: Implement local Arbiter hook
        return GenerationResult(
            text="response",
            model_id="{name}-model",
            usage_in=0,
            usage_out=0,
            finish_reason="stop",
            latency_ms=0,
        )
''')
    _write_file(repo_root / "orchestrator" / "tests" / "inference_router" / "providers" / f"test_{name}.py", f'''from orchestrator.inference_router.providers.{name} import {name.title()}GenerativeProvider

def test_{name}_health() -> None:
    provider = {name.title()}GenerativeProvider()
    assert provider.health()
''')
    sys.exit(OK)


@new_cmd.command(name="verifier", help="Generate a new verifier skeleton.")
@click.argument("name")
def new_verifier(name: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"new: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    plugin_file = repo_root / "xion-verify" / "src" / "xion_verify" / "commands" / f"{name.replace('-', '_')}.py"
    _write_file(plugin_file, f'''{_EIGHT_QUESTION_TEMPLATE}
import sys
import click
from xion_verify.exit_codes import OK, FAIL

@click.command(name="{name}", help="Verify {name} properties.")
def {name.replace('-', '_')}():
    # TODO: Implement verifier logic
    click.echo("{name}: OK")
    sys.exit(OK)
''')
    _write_file(repo_root / "xion-verify" / "tests" / f"test_{name.replace('-', '_')}.py", f'''from click.testing import CliRunner
from xion_verify.commands.{name.replace('-', '_')} import {name.replace('-', '_')}

def test_{name.replace('-', '_')}() -> None:
    runner = CliRunner()
    result = runner.invoke({name.replace('-', '_')})
    assert result.exit_code == 0
    assert "OK" in result.output
''')
    sys.exit(OK)


@new_cmd.command(name="proposal", help="Generate a new proposal skeleton.")
@click.argument("name")
def new_proposal(name: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"new: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    plugin_file = repo_root / "proposals" / f"{name}.md"
    _write_file(plugin_file, f'''# Proposal: {name}

{_EIGHT_QUESTION_TEMPLATE}

## Motivation
...

## Mechanism
...
''')
    sys.exit(OK)
