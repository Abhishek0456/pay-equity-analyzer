"""Part 3 — Promotion table derived from PROMOTION assignment changes.

Fully derived (no randomness): each PROMOTION assignment row is paired with the employee's previous
assignment. approved_by = the employee's manager (always a MANAGER; the root manager is already at
the top level and cannot be promoted).
"""

from __future__ import annotations

import pandas as pd

from payequity import ids


def build_promotions(employees: pd.DataFrame, assignments: pd.DataFrame) -> pd.DataFrame:
    a = assignments.sort_values(["employee_id", "effective_from"], ignore_index=True)
    a["from_assignment_id"] = a.groupby("employee_id")["assignment_id"].shift()
    a["from_level_id"] = a.groupby("employee_id")["level_id"].shift()
    p = a[a["change_reason"] == "PROMOTION"].merge(
        employees[["employee_id", "manager_id"]], on="employee_id", how="left", validate="many_to_one")

    if p["from_assignment_id"].isna().any():
        raise ValueError("PROMOTION assignment without a preceding assignment")
    if p["manager_id"].isna().any():
        raise ValueError("promoted employee has no manager to approve the promotion")

    p = p.reset_index(drop=True)
    return pd.DataFrame({
        "promotion_id": [ids.promotion_id(i + 1) for i in range(len(p))],
        "employee_id": p["employee_id"],
        "from_assignment_id": p["from_assignment_id"],
        "to_assignment_id": p["assignment_id"],
        "from_level_id": p["from_level_id"],
        "to_level_id": p["level_id"],
        "effective_date": p["effective_from"],
        "approved_by": p["manager_id"],
    })
