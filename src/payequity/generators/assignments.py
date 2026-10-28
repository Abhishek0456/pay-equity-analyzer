"""Part 2 — JobAssignment: effective-dated, append-only history per employee.

Each employee starts with a HIRE assignment on hire_date; within the history window, monthly draws
add PROMOTION (rank +1, ≥ 12 months at level — R-GEN-02), RELOCATION (new location, usually new
currency — R-GEN-03), TRANSFER (same job family and level) and FTE_CHANGE rows. Events take effect
on the 1st of a month. Rows are contiguous: effective_to = next effective_from − 1 day, and the last
row ends on termination_date (or is open, null, for current staff).

Constraints from employees.py: MANAGER → management track (root manager at the top level),
HR_PARTNER → role HRB (and only HR partners hold HRB). Promotions are decided here; Part 3
performance must give promoted employees a rating ≥ 4 in the preceding cycle.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from payequity import ids
from payequity.config import Settings
from payequity.rng import RngFactory

HR_PARTNER_ROLE = "HRB"
IC_LEVEL_WEIGHTS = [0.25, 0.30, 0.25, 0.13, 0.07]  # L1..L5 at hire
MANAGER_LEVEL_WEIGHTS = [0.60, 0.30, 0.10]          # L6..L8 at hire (root manager: top level)
PART_TIME_FTES = [0.20, 0.50, 0.60, 0.80]           # includes the 0.20 boundary
PROMOTION_ANNUAL_RATE = 0.12                        # among eligible employees
TRANSFER_ANNUAL_RATE = 0.03
FTE_CHANGE_ANNUAL_RATE = 0.03
MIN_DAYS_AT_LEVEL = 365


def _track_ranks(levels: pd.DataFrame) -> dict[str, list[int]]:
    return {t: sorted(g["rank"]) for t, g in levels.groupby("track")}


def _initial_state(rng, emp, settings, roles, track_ranks, location_codes) -> dict:
    if emp.system_role == "HR_PARTNER":
        role = HR_PARTNER_ROLE
    else:
        role = str(rng.choice(roles.loc[roles["role_code"] != HR_PARTNER_ROLE, "role_code"]))

    if emp.system_role == "MANAGER":
        ranks = track_ranks["MANAGEMENT"]
        rank = ranks[-1] if pd.isna(emp.manager_id) else int(rng.choice(ranks, p=MANAGER_LEVEL_WEIGHTS))
    else:
        rank = int(rng.choice(track_ranks["IC"], p=IC_LEVEL_WEIGHTS))

    part_time = rng.random() < settings.workforce["part_time_share"]
    fte = float(rng.choice(PART_TIME_FTES)) if part_time else 1.0
    return {"role": role, "rank": rank, "location": str(rng.choice(location_codes)), "fte": fte}


def _employee_history(rng, emp, settings, roles, track_ranks, location_codes) -> list[tuple]:
    """[(effective_from, state, change_reason), ...] for one employee, in date order."""
    state = _initial_state(rng, emp, settings, roles, track_ranks, location_codes)
    track = "MANAGEMENT" if emp.system_role == "MANAGER" else "IC"
    family_of = dict(zip(roles["role_code"], roles["job_family"]))
    end = emp.termination_date if pd.notna(emp.termination_date) else None
    level_since = emp.hire_date
    history = [(emp.hire_date, dict(state), "HIRE")]

    for month in settings.months:
        d = date(int(month[:4]), int(month[5:]), 1)
        if d <= emp.hire_date:
            continue
        if end is not None and d > end:
            break
        u = rng.random(4)  # fixed draw count per month keeps the stream aligned across branches
        can_promote = ((d - level_since).days >= MIN_DAYS_AT_LEVEL
                       and state["rank"] < track_ranks[track][-1])
        transfer_to = [] if state["role"] == HR_PARTNER_ROLE else [
            r for r, f in family_of.items()
            if f == family_of[state["role"]] and r not in (state["role"], HR_PARTNER_ROLE)
        ]

        if can_promote and u[0] < PROMOTION_ANNUAL_RATE / 12:
            state["rank"] += 1
            level_since = d
            reason = "PROMOTION"
        elif u[1] < settings.workforce["annual_relocation_rate"] / 12:
            state["location"] = str(rng.choice([c for c in location_codes if c != state["location"]]))
            reason = "RELOCATION"
        elif transfer_to and u[2] < TRANSFER_ANNUAL_RATE / 12:
            state["role"] = str(rng.choice(transfer_to))
            reason = "TRANSFER"
        elif u[3] < FTE_CHANGE_ANNUAL_RATE / 12:
            state["fte"] = float(rng.choice(PART_TIME_FTES)) if state["fte"] == 1.0 else 1.0
            reason = "FTE_CHANGE"
        else:
            continue
        history.append((d, dict(state), reason))
    return history


def build_assignments(
    settings: Settings,
    rngs: RngFactory,
    employees: pd.DataFrame,
    master: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rng = rngs("assignments")
    roles, levels = master["role"], master["level"]
    track_ranks = _track_ranks(levels)
    level_of_rank = dict(zip(levels["rank"], levels["level_id"]))
    location_codes = list(master["location"]["location_code"])

    rows = []
    for emp in employees.itertuples(index=False):
        history = _employee_history(rng, emp, settings, roles, track_ranks, location_codes)
        end = emp.termination_date if pd.notna(emp.termination_date) else None
        for seq, (start, state, reason) in enumerate(history, start=1):
            nxt = history[seq][0] - timedelta(days=1) if seq < len(history) else end
            rows.append({
                "assignment_id": ids.assignment_id(emp.employee_id, seq),
                "employee_id": emp.employee_id,
                "role_id": ids.role_id(state["role"]),
                "level_id": level_of_rank[state["rank"]],
                "location_id": ids.location_id(state["location"]),
                "fte": state["fte"],
                "effective_from": start,
                "effective_to": nxt,
                "change_reason": reason,
            })
    return pd.DataFrame(rows)
