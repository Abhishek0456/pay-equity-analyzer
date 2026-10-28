"""Part 1 — Deterministic ID builders and regex validators.

EMP-000001, ROLE-SWE, RL-SWE-L3, LOC-NYC, BAND-SWE-L3-NYC-2026, ASG-EMP-000001-01,
SAL-EMP-000001-2026-01, PRM-000001, PERF-000001, TEN-EMP-000001-2026, FX-EUR-2026-01,
CG-2026-0001, ADJ-2026-000001, APR-2026-000001, GT-000001.

Builders take short codes (e.g. "SWE", "NYC"), not prefixed IDs; use `code_of` to convert.
"""

from __future__ import annotations

import re

_EMP = r"EMP-\d{6}"
_MONTH = r"\d{4}-(0[1-9]|1[0-2])"

PATTERNS: dict[str, re.Pattern[str]] = {
    kind: re.compile(f"^{rx}$")
    for kind, rx in {
        "employee": _EMP,
        "role": r"ROLE-[A-Z]{3}",
        "level": r"L[1-9]",
        "role_level": r"RL-[A-Z]{3}-L[1-9]",
        "location": r"LOC-[A-Z]{3}",
        "band": r"BAND-[A-Z]{3}-L[1-9]-[A-Z]{3}-\d{4}",
        "assignment": rf"ASG-{_EMP}-\d{{2}}",
        "salary_record": rf"SAL-{_EMP}-{_MONTH}",
        "promotion": r"PRM-\d{6}",
        "evidence": r"PERF-\d{6}",
        "tenure": rf"TEN-{_EMP}-\d{{4}}",
        "fx_rate": rf"FX-[A-Z]{{3}}-{_MONTH}",
        "group": r"CG-\d{4}-\d{4}",
        "adjustment": r"ADJ-\d{4}-\d{6}",
        "approval_event": r"APR-\d{4}-\d{6}",
        "ground_truth": r"GT-\d{6}",
    }.items()
}


def _counter(n: int, width: int) -> str:
    if not 1 <= n < 10**width:
        raise ValueError(f"counter {n} out of range for width {width}")
    return f"{n:0{width}d}"


def _check_month(month: str) -> str:
    if not re.fullmatch(_MONTH, month):
        raise ValueError(f"invalid month {month!r}; expected YYYY-MM")
    return month


def code_of(prefixed_id: str) -> str:
    """'ROLE-SWE' -> 'SWE', 'LOC-NYC' -> 'NYC'."""
    return prefixed_id.split("-", 1)[1]


def employee_id(n: int) -> str:
    return f"EMP-{_counter(n, 6)}"


def role_id(role_code: str) -> str:
    return f"ROLE-{role_code}"


def role_level_id(role_code: str, level_id: str) -> str:
    return f"RL-{role_code}-{level_id}"


def location_id(location_code: str) -> str:
    return f"LOC-{location_code}"


def band_id(role_code: str, level_id: str, location_code: str, year: int) -> str:
    return f"BAND-{role_code}-{level_id}-{location_code}-{year:04d}"


def assignment_id(emp_id: str, seq: int) -> str:
    return f"ASG-{emp_id}-{_counter(seq, 2)}"


def salary_record_id(emp_id: str, month: str) -> str:
    return f"SAL-{emp_id}-{_check_month(month)}"


def promotion_id(n: int) -> str:
    return f"PRM-{_counter(n, 6)}"


def evidence_id(n: int) -> str:
    return f"PERF-{_counter(n, 6)}"


def tenure_id(emp_id: str, year: int) -> str:
    return f"TEN-{emp_id}-{year:04d}"


def fx_rate_id(currency_code: str, month: str) -> str:
    return f"FX-{currency_code}-{_check_month(month)}"


def group_id(year: int, n: int) -> str:
    return f"CG-{year:04d}-{_counter(n, 4)}"


def adjustment_id(year: int, n: int) -> str:
    return f"ADJ-{year:04d}-{_counter(n, 6)}"


def approval_event_id(year: int, n: int) -> str:
    return f"APR-{year:04d}-{_counter(n, 6)}"


def ground_truth_id(n: int) -> str:
    return f"GT-{_counter(n, 6)}"


def is_valid(kind: str, value: str) -> bool:
    """True if `value` matches the documented format for ID `kind`."""
    return bool(PATTERNS[kind].match(value))
