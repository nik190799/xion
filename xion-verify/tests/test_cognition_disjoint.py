from pathlib import Path

from xion_verify.commands.cognition_disjoint import check_disjoint


def test_check_disjoint_ok(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    (skills_dir / "skill_a.py").write_text("import os\n")

    skill_b_dir = skills_dir / "skill_b"
    skill_b_dir.mkdir()
    (skill_b_dir / "__init__.py").write_text("from . import helper\n")
    (skill_b_dir / "helper.py").write_text("import sys\n")

    errors = check_disjoint(tmp_path)
    assert not errors


def test_check_disjoint_fail_absolute_import(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    (skills_dir / "skill_a.py").write_text("import skills.skill_b\n")
    (skills_dir / "skill_b.py").write_text("pass\n")

    errors = check_disjoint(tmp_path)
    assert len(errors) == 1
    assert "cross-import of sibling plugin 'skill_b'" in errors[0]


def test_check_disjoint_fail_from_import(tmp_path: Path) -> None:
    senses_dir = tmp_path / "orchestrator" / "senses"
    senses_dir.mkdir(parents=True)

    (senses_dir / "sense_a.py").write_text("from orchestrator.senses.sense_b import foo\n")
    (senses_dir / "sense_b.py").write_text("foo = 1\n")

    errors = check_disjoint(tmp_path)
    assert len(errors) == 1
    assert "cross-import of sibling plugin 'sense_b'" in errors[0]


def test_check_disjoint_fail_relative_import_file(tmp_path: Path) -> None:
    providers_dir = tmp_path / "orchestrator" / "inference_router" / "providers"
    providers_dir.mkdir(parents=True)

    (providers_dir / "prov_a.py").write_text("from . import prov_b\n")
    (providers_dir / "prov_b.py").write_text("pass\n")

    errors = check_disjoint(tmp_path)
    assert len(errors) == 1
    assert "cross-import of sibling plugin 'prov_b'" in errors[0]


def test_check_disjoint_fail_relative_import_package(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    skill_a_dir = skills_dir / "skill_a"
    skill_a_dir.mkdir()
    (skill_a_dir / "__init__.py").write_text("from ..skill_b import foo\n")

    (skills_dir / "skill_b.py").write_text("foo = 1\n")

    errors = check_disjoint(tmp_path)
    assert len(errors) == 1
    assert "cross-import of sibling plugin 'skill_b'" in errors[0]
