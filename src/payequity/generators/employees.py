"""Part 2 — Employee table: hire/termination dates, status, manager hierarchy, HR partners, system roles.

`system_role` is decided here and constrains Part 2 assignments: MANAGER → management-track level
(L6–L8), HR_PARTNER → role HRB. Managers, HR partners and the admin are drawn from employees hired
before the history window who never terminate, so every manager_id / hr_partner_id stays valid.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from payequity import ids
from payequity.config import Settings
from payequity.rng import RngFactory

PRE_WINDOW_HIRE_YEARS = 12     # pre-window hires spread over this many years before history_start
IN_WINDOW_HIRE_SHARE = 0.25    # share of employees hired inside the history window
MIN_SERVICE_DAYS = 30          # no hire within this many days of as_of; no termination this soon after hire
ON_LEAVE_SHARE = 0.03          # share of non-terminated employees currently ON_LEAVE
HR_PARTNERS_PER_EMPLOYEE = 0.01
MIN_HR_PARTNERS = 2


def _random_dates(rng: np.random.Generator, start: date, end: date, n: int) -> list[date]:
    """n dates drawn uniformly from [start, end] inclusive."""
    offsets = rng.integers(0, (end - start).days + 1, n)
    return [start + timedelta(days=int(d)) for d in offsets]


def _hire_and_termination(settings: Settings, rng: np.random.Generator) -> pd.DataFrame:
    n = settings.n_employees
    window_start = date.fromisoformat(f"{settings.history_start}-01")
    as_of = settings.as_of_date

    in_window = rng.random(n) < IN_WINDOW_HIRE_SHARE
    pre = _random_dates(rng, window_start.replace(year=window_start.year - PRE_WINDOW_HIRE_YEARS),
                        window_start - timedelta(days=1), n)
    inside = _random_dates(rng, window_start, as_of - timedelta(days=MIN_SERVICE_DAYS), n)
    hire = [i if w else p for w, p, i in zip(in_window, pre, inside)]

    # Termination: annual attrition applied over each employee's exposure inside the window.
    attrition = settings.workforce["annual_attrition"]
    exposure_from = [max(h, window_start) + timedelta(days=MIN_SERVICE_DAYS) for h in hire]
    exposure_years = np.array([max((as_of - s).days, 0) / 365.25 for s in exposure_from])
    terminates = rng.random(n) < 1 - (1 - attrition) ** exposure_years
    term_u = rng.random(n)
    termination = [
        s + timedelta(days=int(u * (as_of - s).days)) if t else None
        for t, s, u in zip(terminates, exposure_from, term_u)
    ]
    return pd.DataFrame({"hire_date": hire, "termination_date": termination, "pre_window": ~in_window})


def _capacities(rng: np.random.Generator, n_managers: int, n_reports: int, span: tuple[int, int]) -> np.ndarray:
    """Per-manager report counts within [lo, hi] that sum exactly to n_reports."""
    lo, hi = span
    if not n_managers * lo <= n_reports <= n_managers * hi:
        raise ValueError(f"{n_reports} reports cannot fit {n_managers} managers with span {span}")
    cap = rng.integers(lo, hi + 1, n_managers)
    while (diff := n_reports - int(cap.sum())) != 0:
        movable = np.flatnonzero(cap < hi) if diff > 0 else np.flatnonzero(cap > lo)
        cap[rng.choice(movable)] += 1 if diff > 0 else -1
    return cap


def _manager_tree(rng: np.random.Generator, n: int, managers: np.ndarray, span: tuple[int, int]) -> np.ndarray:
    """manager_id index per employee (-1 = top). managers[0] is the root.

    Reports are listed as managers[1:] (in order) followed by everyone else, and fill manager slots
    in managers order. Since each manager has ≥ span[0] ≥ 1 slots, manager k is always placed under
    a manager earlier in the list — so the hierarchy is a tree with no cycles.
    """
    others = np.setdiff1d(np.arange(n), managers)
    reports = np.concatenate([managers[1:], rng.permutation(others)])
    owners = np.repeat(managers, _capacities(rng, len(managers), len(reports), span))
    parent = np.full(n, -1)
    parent[reports] = owners
    return parent


def build_employees(settings: Settings, rngs: RngFactory) -> pd.DataFrame:
    rng = rngs("employees")
    n = settings.n_employees
    df = _hire_and_termination(settings, rng)

    # Leaders (managers, HR partners, admin) come from long-tenured employees who stay all window.
    stable = np.flatnonzero(df["pre_window"].to_numpy() & df["termination_date"].isna().to_numpy())
    span = tuple(settings.workforce["manager_span"])
    n_managers = round(n / ((span[0] + span[1]) / 2))
    n_hr = max(MIN_HR_PARTNERS, round(n * HR_PARTNERS_PER_EMPLOYEE))
    if len(stable) < n_managers + n_hr + 1:
        raise ValueError("not enough stable employees to staff managers, HR partners and admin")
    picked = rng.permutation(stable)[: n_managers + n_hr + 1]
    managers, hr_partners, admin = picked[:n_managers], picked[n_managers:-1], picked[-1]

    system_role = np.full(n, "EMPLOYEE", dtype=object)
    system_role[managers] = "MANAGER"
    system_role[hr_partners] = "HR_PARTNER"
    system_role[admin] = "SYS_ADMIN"

    emp_ids = np.array([ids.employee_id(i + 1) for i in range(n)], dtype=object)
    parent = _manager_tree(rng, n, managers, span)

    # Each employee gets an HR partner other than themselves.
    hr_pick = rng.integers(0, n_hr, n)
    hr_idx = hr_partners[hr_pick]
    clash = hr_idx == np.arange(n)
    hr_idx[clash] = hr_partners[(hr_pick[clash] + 1) % n_hr]

    terminated = df["termination_date"].notna().to_numpy()
    on_leave = ~terminated & (rng.random(n) < ON_LEAVE_SHARE) & (system_role == "EMPLOYEE")
    status = np.where(terminated, "TERMINATED", np.where(on_leave, "ON_LEAVE", "ACTIVE"))

    # Audit-only attribute: drawn independently of everything, never used to set pay.
    cohort = np.where(rng.random(n) < 0.5, "COHORT_A", "COHORT_B")

    return pd.DataFrame({
        "employee_id": emp_ids,
        "display_name": [f"Employee {i + 1:06d}" for i in range(n)],
        "hire_date": df["hire_date"],
        "termination_date": df["termination_date"],
        "employment_status": status,
        "manager_id": [emp_ids[p] if p >= 0 else None for p in parent],
        "hr_partner_id": emp_ids[hr_idx],
        "system_role": system_role,
        "analysis_cohort": cohort,
    })
