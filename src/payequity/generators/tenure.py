"""Part 3 — Yearly tenure snapshots derived from employees and assignments.

Fully derived (no randomness): one row per employee and history year for every employee who is
employed on Dec 31 of that year (hire_date <= Dec 31 and not terminated on or before it). Snapshot
date (as_of_date) = Dec 31 of the year.

  * company_tenure_years = (as_of_date - hire_date) / 365.25
  * role_tenure_years    = time in the current role_id: from the effective_from of the earliest
                           assignment in the latest unbroken run of assignments sharing the active
                           assignment's role_id (PROMOTION / RELOCATION / FTE_CHANGE do not reset it,
                           TRANSFER does)
  * level_tenure_years   = time in the current (role_id, level_id) combination, computed the same way
                           (resets on PROMOTION or TRANSFER)

Defining level tenure on the (role, level) combination, rather than on level_id alone, guarantees
level_tenure <= role_tenure <= company_tenure, as required by the data dictionary. Values are
rounded to 2 decimals.
"""

from __future__ import annotations

import pandas as pd

from payequity import ids
from payequity.config import Settings

_DAYS_PER_YEAR = 365.25


def _run_start(a: pd.DataFrame, keys: list[str]) -> pd.Series:
    """effective_from of the first assignment of the unbroken run of equal `keys` (per employee)."""
    g = a.groupby("employee_id", sort=False)
    new_run = g["employee_id"].cumcount().eq(0)
    for k in keys:
        new_run |= a[k].ne(g[k].shift())
    return a["effective_from"].where(new_run).groupby(a["employee_id"], sort=False).ffill()


def build_tenure(settings: Settings, employees: pd.DataFrame, assignments: pd.DataFrame) -> pd.DataFrame:
    a = assignments[["employee_id", "role_id", "level_id", "effective_from", "effective_to"]].copy()
    a["effective_from"] = pd.to_datetime(a["effective_from"])
    a["effective_to"] = pd.to_datetime(a["effective_to"])
    a = a.sort_values(["employee_id", "effective_from"], ignore_index=True)
    a["role_start"] = _run_start(a, ["role_id"])
    a["level_start"] = _run_start(a, ["role_id", "level_id"])

    emp = employees[["employee_id", "hire_date", "termination_date"]].copy()
    emp["hire_date"] = pd.to_datetime(emp["hire_date"])
    emp["termination_date"] = pd.to_datetime(emp["termination_date"])

    frames = []
    for year in settings.history_years:
        as_of = pd.Timestamp(year=year, month=12, day=31)
        employed = emp[(emp["hire_date"] <= as_of)
                       & (emp["termination_date"].isna() | (emp["termination_date"] > as_of))]
        frames.append(employed.assign(as_of_date=as_of))
    snap = pd.concat(frames, ignore_index=True)

    active = snap.merge(a, on="employee_id", how="left")
    active = active[(active["effective_from"] <= active["as_of_date"])
                    & (active["effective_to"].isna() | (active["effective_to"] >= active["as_of_date"]))]
    if active.duplicated(["employee_id", "as_of_date"]).any():
        raise ValueError("employee has overlapping assignments on a snapshot date")
    t = snap.merge(active[["employee_id", "as_of_date", "role_start", "level_start"]],
                   on=["employee_id", "as_of_date"], how="left", validate="one_to_one")
    if t["role_start"].isna().any():
        raise ValueError("employed employee-year has no assignment active on Dec 31")

    def years(start: pd.Series) -> pd.Series:
        return ((t["as_of_date"] - start).dt.days / _DAYS_PER_YEAR).round(2)

    t = t.sort_values(["employee_id", "as_of_date"], ignore_index=True)
    return pd.DataFrame({
        "tenure_id": [ids.tenure_id(e, d.year) for e, d in zip(t["employee_id"], t["as_of_date"])],
        "employee_id": t["employee_id"],
        "as_of_date": t["as_of_date"].dt.date,
        "company_tenure_years": years(t["hire_date"]),
        "role_tenure_years": years(t["role_start"]),
        "level_tenure_years": years(t["level_start"]),
    })
