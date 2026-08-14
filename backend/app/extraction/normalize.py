"""Mechanical unit/scale normalization of an extracted raw value. Anything
that can't be normalized with confidence (unparsable value, unrecognized
unit) is flagged rather than silently coerced -- it goes to the review
queue instead."""

from __future__ import annotations

import re
from dataclasses import dataclass

_UNIT_MULTIPLIERS: dict[str, float] = {
    "": 1.0,
    "$": 1.0,
    "unit": 1.0,
    "units": 1.0,
    "k": 1e3,
    "$k": 1e3,
    "thousand": 1e3,
    "thousands": 1e3,
    "m": 1e6,
    "$m": 1e6,
    "mm": 1e6,
    "million": 1e6,
    "millions": 1e6,
    "b": 1e9,
    "$b": 1e9,
    "billion": 1e9,
    "billions": 1e9,
    "%": 0.01,
    "percent": 0.01,
    "pct": 0.01,
}

_NUMBER_RE = re.compile(r"-?\d+\.?\d*")


@dataclass
class NormalizedResult:
    normalized_value: float | None
    needs_review: bool
    reason: str | None


def parse_numeric(raw_value: str) -> float | None:
    cleaned = raw_value.replace(",", "").replace("$", "").strip()
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]

    match = _NUMBER_RE.search(cleaned)
    if not match:
        return None

    value = float(match.group())
    return -value if negative else value


def normalize(raw_value: str, raw_unit: str | None) -> NormalizedResult:
    numeric = parse_numeric(raw_value)
    if numeric is None:
        return NormalizedResult(
            normalized_value=None, needs_review=True, reason=f"unparsable value: {raw_value!r}"
        )

    unit_key = (raw_unit or "").strip().lower()
    if unit_key not in _UNIT_MULTIPLIERS:
        return NormalizedResult(
            normalized_value=None, needs_review=True, reason=f"unrecognized unit: {raw_unit!r}"
        )

    return NormalizedResult(
        normalized_value=numeric * _UNIT_MULTIPLIERS[unit_key], needs_review=False, reason=None
    )
