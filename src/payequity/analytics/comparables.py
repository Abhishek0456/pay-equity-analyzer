"""Part 4 — Comparable groups and bridge tables (R-GRP-01/02)."""

from __future__ import annotations

import pandas as pd

from payequity.ids import group_id


def build_comparable_groups(
    records: pd.DataFrame,
    as_of_month: str | None = None,
    grouping_basis: str = "SAME_ROLE",
    grouping_rationale: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Build group, role-bridge, and member-bridge tables.

    The default is the documented same-role + level + location grouping.  A
    caller may request a broader grouping only with a non-empty rationale.
    """
    required = {"employee_id", "salary_record_id", "role_id", "level_id", "location_id"}
    missing = required - set(records.columns)
    if missing:
        raise ValueError(f"records missing required columns: {sorted(missing)}")
    if grouping_basis not in {"SAME_ROLE", "SAME_FAMILY", "CROSS_FAMILY"}:
        raise ValueError("invalid grouping_basis")
    if grouping_basis != "SAME_ROLE" and not grouping_rationale:
        raise ValueError("a rationale is required for non-SAME_ROLE groups")
    if as_of_month is None:
        if "period_month" not in records:
            raise ValueError("as_of_month is required when period_month is absent")
        as_of_month = str(records["period_month"].max())

    key = ["level_id", "location_id"]
    if grouping_basis == "SAME_ROLE":
        key.insert(0, "role_id")
    elif "job_family" in records:
        key.insert(0, "job_family")
    else:
        raise ValueError("broader grouping requires a job_family column")

    groups = []
    role_rows = []
    member_rows = []
    for n, (_, frame) in enumerate(records.groupby(key, dropna=False, sort=True), 1):
        gid = group_id(int(str(as_of_month)[:4]), n)
        first = frame.iloc[0]
        groups.append({"group_id": gid, "level_id": first["level_id"],
                       "location_id": first["location_id"],
                       "geo_tier": first.get("geo_tier"),
                       "grouping_basis": grouping_basis,
                       "grouping_rationale": grouping_rationale,
                       "as_of_month": as_of_month,
                       "member_count": len(frame),
                       "outlier_eligible": len(frame) >= 5})
        for role in frame["role_id"].drop_duplicates():
            role_rows.append({"group_id": gid, "role_id": role})
        for _, row in frame.iterrows():
            member_rows.append({"group_id": gid, "employee_id": row["employee_id"],
                                "salary_record_id": row["salary_record_id"]})
    return {"comparable_group": pd.DataFrame(groups),
            "comparable_group_role": pd.DataFrame(role_rows),
            "comparable_group_member": pd.DataFrame(member_rows)}


def build_groups(*args, **kwargs) -> dict[str, pd.DataFrame]:
    return build_comparable_groups(*args, **kwargs)
