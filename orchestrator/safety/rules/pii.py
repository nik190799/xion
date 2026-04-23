"""Principle 7 — No PII leakage.

v1 detects:

  - US Social Security Numbers: 3-2-4 digit shape with keyword co-occurrence
    to reduce false positives on random 9-digit sequences.
  - Credit card numbers: 13-19 digit sequences passing Luhn check.
  - Email addresses: RFC-simple pattern.
  - Phone numbers: international and US shapes with co-occurrence.

Each sub-rule has its own `rule_id` suffix so the ledger records which
pattern fired. All PII refusals cite principle 7. False positives are
refused (the safer error); callers appeal via operator review (Phase 5).
"""

from __future__ import annotations

import re

from orchestrator.safety.types import RuleResult

_PRINCIPLE_ID = "7"
_RULE_VERSION = 1

_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_SSN_KEYWORD = re.compile(r"\b(?:ssn|social\s+security(?:\s+number)?)\b", re.IGNORECASE)

_CC_PATTERN = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")

_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

_PHONE_PATTERN_US = re.compile(r"\b(?:\+?1[-\s.])?\(?\d{3}\)?[-\s.]\d{3}[-\s.]\d{4}\b")
_PHONE_KEYWORD = re.compile(r"\b(?:phone|mobile|cell|call\s+me\s+at|tel|telephone)\b", re.IGNORECASE)


def _luhn_ok(digits: str) -> bool:
    """Standard Luhn check on a digit-only string. Used to cut CC false
    positives from arbitrary 13-19-digit sequences."""
    if not digits.isdigit():
        return False
    total = 0
    parity = len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _contains_ssn(text: str) -> bool:
    return bool(_SSN_PATTERN.search(text) and _SSN_KEYWORD.search(text))


def _contains_credit_card(text: str) -> bool:
    for m in _CC_PATTERN.finditer(text):
        digits_only = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits_only) <= 19 and _luhn_ok(digits_only):
            return True
    return False


def _contains_phone(text: str) -> bool:
    return bool(_PHONE_PATTERN_US.search(text) and _PHONE_KEYWORD.search(text))


def _contains_email(text: str) -> bool:
    return bool(_EMAIL_PATTERN.search(text))


def run(candidate: str) -> RuleResult:
    # Order of checks biases toward the most specific / highest-confidence
    # first so the summary and rule_id are the most useful possible.
    if _contains_ssn(candidate):
        rule_id = "pii.us_ssn_with_keyword_v1"
        return RuleResult.refuse(
            principle_id=_PRINCIPLE_ID,
            rule_id=rule_id,
            rule_version=_RULE_VERSION,
            summary=f"PII pattern: 9-digit-with-dashes co-occurring with SSN keyword (rule: {rule_id})",
        )
    if _contains_credit_card(candidate):
        rule_id = "pii.credit_card_luhn_v1"
        return RuleResult.refuse(
            principle_id=_PRINCIPLE_ID,
            rule_id=rule_id,
            rule_version=_RULE_VERSION,
            summary=f"PII pattern: 13-19 digit sequence passing Luhn (rule: {rule_id})",
        )
    if _contains_phone(candidate):
        rule_id = "pii.phone_with_keyword_v1"
        return RuleResult.refuse(
            principle_id=_PRINCIPLE_ID,
            rule_id=rule_id,
            rule_version=_RULE_VERSION,
            summary=f"PII pattern: phone-shaped number with phone keyword (rule: {rule_id})",
        )
    if _contains_email(candidate):
        rule_id = "pii.email_address_v1"
        return RuleResult.refuse(
            principle_id=_PRINCIPLE_ID,
            rule_id=rule_id,
            rule_version=_RULE_VERSION,
            summary=f"PII pattern: email-address shape (rule: {rule_id})",
        )
    return RuleResult.passthrough()
