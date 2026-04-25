"""`xion-verify measurement-vocabulary` — Phase 6.8 static spend-unit audit."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import yaml

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_VOCAB_REL = "docs/MEASUREMENT-VOCABULARY.md"
_SPEND_DOCTRINE_RELS: tuple[str, ...] = (
    "docs/SPEND-AUTONOMY.md",
    "docs/19-TREASURY.md",
    "docs/21-SUSTAINABILITY.md",
    "docs/24-COGNITION.md",
    "docs/27-RESEARCH-SPEND.md",
)
_REQUIRED_VOCAB_REFS: tuple[str, ...] = (
    "docs/SPEND-AUTONOMY.md",
    "docs/19-TREASURY.md",
    "docs/21-SUSTAINABILITY.md",
    "docs/24-COGNITION.md",
)
_PERMITTED_UNITS: frozenset[str] = frozenset(
    {
        "runway_weeks",
        "fraction_of_operating_float",
        "fraction_of_improvement_fund",
        "distance_to_reserve_floor",
        "decision_count_under_posture",
        "self_audit_accuracy",
        "attestation_count",
        "audit_pass_count",
        "incident_count_window",
        "inflow_volatility_band",
        "recurring_burn_ratio",
        "reversibility_class",
    }
)

_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "elapsed-time authority gate",
        re.compile(
            r"\b(after|for|until|once|when)\s+\d+(?:[-–]\d+)?\s+"
            r"(seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "absolute-money spend cap",
        re.compile(
            r"(?:\$\s*\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s+"
            r"(?:USD|USDC|XION|ETH|AKT|AR)\s*/\s*"
            r"(?:day|week|month|year)\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "token-price authority gate",
        re.compile(r"\b(?:XION|token)\s+(?:trades?|price)\s+(?:above|below|over|under)\b", re.IGNORECASE),
    ),
    (
        "inflow-volume authority gate",
        re.compile(r"\b(?:donations?|inflows?|revenue|grants?)\s+(?:exceed|exceeds|above|over)\b", re.IGNORECASE),
    ),
    (
        "source-prestige authority gate",
        re.compile(r"\bgrant money unlocks\b", re.IGNORECASE),
    ),
)

_NAMED_EXCEPTION_HINTS: tuple[str, ...] = (
    "/forget",
    "crypto-migration",
    "cryptographic",
    "constitutional ratification",
    "public-comment",
    "constitutional floor",
)


@dataclass(frozen=True)
class VocabularyFinding:
    relpath: str
    line_number: int
    reason: str
    line: str

    def format(self) -> str:
        return f"{self.relpath}:{self.line_number}: {self.reason}: {self.line.strip()}"


def check_measurement_vocabulary(repo_root: Path) -> list[VocabularyFinding]:
    findings: list[VocabularyFinding] = []
    vocab_path = repo_root / _VOCAB_REL
    if not vocab_path.is_file():
        return [VocabularyFinding(_VOCAB_REL, 0, "missing measurement vocabulary", "")]

    for rel in _REQUIRED_VOCAB_REFS:
        path = repo_root / rel
        if not path.is_file():
            findings.append(VocabularyFinding(rel, 0, "missing required spend doctrine file", ""))
            continue
        text = path.read_text(encoding="utf-8")
        if "MEASUREMENT-VOCABULARY.md" not in text:
            findings.append(
                VocabularyFinding(rel, 0, "does not reference docs/MEASUREMENT-VOCABULARY.md", "")
            )

    for path in _scan_spend_doctrine(repo_root):
        findings.extend(_scan_forbidden_gates(repo_root, path))
    findings.extend(_check_agent_souls(repo_root))
    return findings


def _scan_spend_doctrine(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for rel in _SPEND_DOCTRINE_RELS:
        path = repo_root / rel
        if path.is_file():
            paths.append(path)
    return paths


def _scan_forbidden_gates(repo_root: Path, path: Path) -> list[VocabularyFinding]:
    rel = path.relative_to(repo_root).as_posix()
    findings: list[VocabularyFinding] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if _line_is_exception_context(line):
            continue
        for reason, pattern in _FORBIDDEN_PATTERNS:
            if pattern.search(line):
                findings.append(VocabularyFinding(rel, lineno, reason, line))
    return findings


def _line_is_exception_context(line: str) -> bool:
    lowered = line.lower()
    if "genesis default" in lowered and "authority" not in lowered and "posture" not in lowered:
        return True
    return any(hint in lowered for hint in _NAMED_EXCEPTION_HINTS)


def _check_agent_souls(repo_root: Path) -> list[VocabularyFinding]:
    souls_dir = repo_root / "genesis" / "AGENT_SOULS"
    if not souls_dir.is_dir():
        return []
    findings: list[VocabularyFinding] = []
    for path in sorted(souls_dir.glob("*.yaml")):
        rel = path.relative_to(repo_root).as_posix()
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            findings.append(VocabularyFinding(rel, 0, f"invalid Agent Soul YAML: {exc}", ""))
            continue
        if not isinstance(data, dict):
            findings.append(VocabularyFinding(rel, 0, "Agent Soul top-level value must be a mapping", ""))
            continue
        envelope = data.get("cost_envelope")
        if not isinstance(envelope, dict):
            findings.append(VocabularyFinding(rel, 0, "missing cost_envelope mapping", ""))
            continue
        if "monthly_usd" in envelope:
            findings.append(VocabularyFinding(rel, 0, "cost_envelope uses forbidden monthly_usd", ""))
        if "monthly_envelope_fraction" not in envelope:
            findings.append(
                VocabularyFinding(rel, 0, "cost_envelope missing monthly_envelope_fraction", "")
            )
        unit = envelope.get("unit")
        if unit not in _PERMITTED_UNITS:
            findings.append(
                VocabularyFinding(
                    rel,
                    0,
                    f"cost_envelope unit must be in docs/MEASUREMENT-VOCABULARY.md, got {unit!r}",
                    "",
                )
            )
    return findings


@click.command(
    name="measurement-vocabulary",
    help="Audit spend doctrine and Agent Souls for canonical measurement units.",
)
def measurement_vocabulary() -> None:
    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        click.echo(f"measurement-vocabulary: FAIL: {exc}", err=True)
        raise SystemExit(FAIL) from None

    findings = check_measurement_vocabulary(repo_root)
    if findings:
        for finding in findings:
            click.echo(f"measurement-vocabulary: FAIL: {finding.format()}", err=True)
        raise SystemExit(FAIL)
    click.echo("measurement-vocabulary: OK (spend doctrine and Agent Soul units verified)")
    raise SystemExit(OK)


__all__ = ["check_measurement_vocabulary", "measurement_vocabulary"]
