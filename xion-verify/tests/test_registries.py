import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.commands.registries import _check_module_conforms, _get_plugin_modules


def test_get_plugin_modules(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    
    (skills_dir / "skill_a.py").write_text("")
    
    skill_b_dir = skills_dir / "skill_b"
    skill_b_dir.mkdir()
    (skill_b_dir / "__init__.py").write_text("")
    
    # Should ignore this
    (skills_dir / "not_a_module").mkdir()
    (skills_dir / "not_a_module" / "foo.txt").write_text("")
    
    modules = _get_plugin_modules(tmp_path, "skills")
    assert "skills.skill_a" in modules
    assert "skills.skill_b" in modules
    assert "skills.not_a_module" not in modules


def test_check_module_conforms_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(tmp_path))
    
    (tmp_path / "my_plugin.py").write_text(
        "class MySense:\n"
        "    name = 'my_sense'\n"
        "    def perceive(self): pass\n"
    )
    
    from typing import Protocol

    class Sense(Protocol):
        name: str
        def perceive(self): ...

    errors = _check_module_conforms("my_plugin", Sense)
    assert not errors


def test_check_module_conforms_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(tmp_path))
    
    (tmp_path / "bad_plugin.py").write_text(
        "class BadSense:\n"
        "    pass\n"
    )
    
    from typing import Protocol

    class Sense(Protocol):
        name: str
        def perceive(self): ...

    errors = _check_module_conforms("bad_plugin", Sense)
    assert len(errors) == 1
    assert "does not export any class conforming to Sense" in errors[0]


def test_check_module_conforms_with_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(tmp_path))
    
    (tmp_path / "all_plugin.py").write_text(
        "__all__ = ['GoodSense']\n"
        "class BadSense:\n"
        "    pass\n"
        "class GoodSense:\n"
        "    name = 'good'\n"
        "    def perceive(self): pass\n"
    )
    
    from typing import Protocol

    class Sense(Protocol):
        name: str
        def perceive(self): ...

    errors = _check_module_conforms("all_plugin", Sense)
    assert not errors


def test_registries_cli_ok() -> None:
    runner = CliRunner()
    result = runner.invoke(root, ["registries"])
    assert result.exit_code == 0
    assert "registries: OK" in result.output
