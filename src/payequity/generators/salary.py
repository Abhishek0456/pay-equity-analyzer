"""Part 3 — Monthly SalaryRecord history (36 months): starting pay, merit, promotion raises, relocation resets.

One record per (employee, month) in settings.months in which the employee is employed on any day.
The record's assignment is the one active on min(month-end, termination_date); band_id is the band
for that assignment's (role, level, location) in the month's calendar year (R-BAND-01).

Pay state is tracked on an FTE basis (`fte_pay`, local currency, annual, whole units after every
change); base_salary_actual = round(fte_pay × fte, 2) (R-GEN-04, R-NORM-01).

Rules, applied in this order each month after the employee's first record:
- Starting pay: band position = clip(0.30 + 0.05 × min(years since hire, 6) + N(0, 0.12), 0, 1).
  Clipping deliberately yields some records exactly at band_min / band_max (boundary edge case).
- MERIT (March): MERIT_BY_RATING[prior-year ANNUAL_RATING, default 3] ± 0.005 jitter, clipped to
  [0, 6%] (R-GEN-01). One-off premiums for prior-year CERTIFICATION / CRITICAL_SKILL /
  MARKET_PREMIUM evidence (documented in Q1) are added ON TOP of the 0–6% merit, so total March
  uplift can exceed 6%; this ties pay to documented factors (R-DIS-01). Result is floored at
  band_min and capped at band_max. Skipped for employees hired < 3 months before March 1.
- Assignment change (applied after merit in the same month): PROMOTION raises 8–15%, lifted to the
  new band_min and capped at the new band_max (R-GEN-02); RELOCATION keeps the previous band
  position ±0.1, re-priced in the new band/currency (R-GEN-03); TRANSFER does the same (bands differ
  by role, so carrying pay over unchanged would fall far outside the new band); FTE_CHANGE keeps
  fte_pay (R-GEN-04).
- change_reason: on the first record, the assignment's reason if a non-HIRE change takes effect in
  that month (no raise: there is no prior pay), else HIRE if hired that month, else NONE; later
  records use the assignment change (PROMOTION beats MERIT in the same month), else MERIT if merit
  applied, else NONE. ADJUSTMENT rows and
  adjustment_id are produced later (Part 5/6), never here.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date

import pandas as pd

from payequity import ids
from payequity.config import Settings
from payequity.rng import RngFactory

START_POS_BASE = 0.30
START_POS_PER_YEAR = 0.05
START_POS_SD = 0.12
START_POS_MAX_YEARS = 6
DEFAULT_RATING = 3
MERIT_BY_RATING = {1: 0.0, 2: 0.015, 3: 0.03, 4: 0.045, 5: 0.06}
MERIT_JITTER = 0.005
MERIT_MAX = 0.06
POSITION_JITTER = 0.1
PREMIUMS = {"CERTIFICATION": 0.02, "CRITICAL_SKILL": 0.03, "MARKET_PREMIUM": 0.05}
RECORD_REASON = {"PROMOTION": "PROMOTION", "TRANSFER": "TRANSFER", "RELOCATION": "RELOCATION",
                 "FTE_CHANGE": "FTE_CHANGE"}
COLUMNS = ["salary_record_id", "employee_id", "assignment_id", "band_id", "period_month",
           "currency_code", "base_salary_actual", "fte", "change_reason", "adjustment_id"]


def _band_index(master: dict[str, pd.DataFrame]) -> dict[tuple, tuple]:
    """(role, level, location, year) → (band_id, currency, band_min, band_max)."""
    b = master["compensation_band"]
    years = pd.to_datetime(b["effective_from"]).dt.year
    return {
        (r, l, loc, int(y)): (bid, cur, float(mn), float(mx))
        for bid, r, l, loc, cur, mn, mx, y in zip(
            b["band_id"], b["role_id"], b["level_id"], b["location_id"], b["currency_code"],
            b["band_min"], b["band_max"], years)
    }


def _evidence_index(performance: pd.DataFrame) -> tuple[dict, dict]:
    """(employee, review_year) → rating, and → summed one-off premium."""
    ratings: dict[tuple, int] = {}
    premiums: dict[tuple, float] = {}
    for emp, typ, year, rating in zip(performance["employee_id"], performance["evidence_type"],
                                      performance["review_year"], performance["rating"]):
        key = (emp, int(year))
        if typ == "ANNUAL_RATING":
            ratings[key] = int(rating)
        else:
            premiums[key] = premiums.get(key, 0.0) + PREMIUMS[typ]
    return ratings, premiums


def _assignment_index(assignments: pd.DataFrame) -> dict[str, list[tuple]]:
    """employee → [(assignment_id, role, level, location, fte, from, to, change_reason), ...] by date."""
    out: dict[str, list[tuple]] = {}
    a = assignments.sort_values(["employee_id", "effective_from"])
    for row in zip(a["employee_id"], a["assignment_id"], a["role_id"], a["level_id"], a["location_id"],
                   a["fte"], a["effective_from"], a["effective_to"], a["change_reason"]):
        out.setdefault(row[0], []).append(row[1:])
    return out


def _round_pay(x: float) -> float:
    return float(round(x))


def build_salary(
    settings: Settings,
    rngs: RngFactory,
    employees: pd.DataFrame,
    assignments: pd.DataFrame,
    performance: pd.DataFrame,
    master: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rng = rngs("salary")
    bands = _band_index(master)
    ratings, premiums = _evidence_index(performance)
    by_emp = _assignment_index(assignments)
    merit_month = int(settings.comp["merit_month"])
    promo_lo, promo_hi = settings.comp["promotion_raise"]

    month_info = []
    for ym in settings.months:
        y, m = int(ym[:4]), int(ym[5:])
        month_info.append((ym, y, m, date(y, m, 1), date(y, m, monthrange(y, m)[1])))

    def band_for(a: tuple, year: int) -> tuple:
        key = (a[1], a[2], a[3], year)
        try:
            return bands[key]
        except KeyError:
            raise ValueError(f"missing compensation band for {key}") from None

    rows: list[tuple] = []
    for emp_id, hire, term in zip(employees["employee_id"], employees["hire_date"],
                                  employees["termination_date"]):
        term = None if pd.isna(term) else term
        alist = by_emp[emp_id]
        ptr = 0
        prev = None          # previous month's assignment tuple
        fte_pay = 0.0
        for ym, year, month, mstart, mend in month_info:
            if hire > mend or (term is not None and term < mstart):
                continue
            ref = mend if term is None or term > mend else term
            while ptr + 1 < len(alist) and alist[ptr + 1][5] <= ref:
                ptr += 1
            cur = alist[ptr]
            if not (cur[5] <= ref and (pd.isna(cur[6]) or cur[6] >= ref)):
                raise ValueError(f"no active assignment for {emp_id} in {ym}")
            b_id, currency, b_min, b_max = band_for(cur, year)

            if prev is None:
                years_since = max((mstart - hire).days / 365.25, 0.0)
                pos = (START_POS_BASE + START_POS_PER_YEAR * min(years_since, START_POS_MAX_YEARS)
                       + rng.normal(0.0, START_POS_SD))
                pos = min(max(pos, 0.0), 1.0)
                fte_pay = _round_pay(b_min + pos * (b_max - b_min))
                if cur[7] in RECORD_REASON and mstart <= cur[5] <= mend:
                    reason = RECORD_REASON[cur[7]]
                else:
                    reason = "HIRE" if (hire.year, hire.month) == (year, month) else "NONE"
            else:
                changed = cur[0] != prev[0]
                # Merit is priced against the band held before any assignment change this month.
                old_band = band_for(prev, year) if changed else (b_id, currency, b_min, b_max)
                merit_applied = False
                if month == merit_month and hire <= date(year - 1, 12, 1):
                    r = ratings.get((emp_id, year - 1), DEFAULT_RATING)
                    merit = MERIT_BY_RATING[r] + rng.uniform(-MERIT_JITTER, MERIT_JITTER)
                    merit = min(max(merit, 0.0), MERIT_MAX) + premiums.get((emp_id, year - 1), 0.0)
                    # The band_max cap never cuts pay: pay already above the band (e.g. after an FX move) just gets 0%.
                    capped = min(max(fte_pay * (1.0 + merit), old_band[2]), old_band[3])
                    fte_pay = _round_pay(max(fte_pay, capped))
                    merit_applied = True
                reason = "MERIT" if merit_applied else "NONE"
                if changed:
                    chg = cur[7]
                    if chg == "PROMOTION":
                        raised = fte_pay * (1.0 + rng.uniform(promo_lo, promo_hi))
                        fte_pay = _round_pay(min(max(raised, b_min), b_max))
                    elif chg in ("RELOCATION", "TRANSFER"):
                        o_min, o_max = old_band[2], old_band[3]
                        pos = (fte_pay - o_min) / (o_max - o_min) + rng.uniform(-POSITION_JITTER, POSITION_JITTER)
                        pos = min(max(pos, 0.0), 1.0)
                        fte_pay = _round_pay(b_min + pos * (b_max - b_min))
                    if chg in RECORD_REASON:
                        reason = RECORD_REASON[chg]
            fte = float(cur[4])
            rows.append((ids.salary_record_id(emp_id, ym), emp_id, cur[0], b_id, ym, currency,
                         round(fte_pay * fte, 2), fte, reason, None))
            prev = cur

    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.sort_values(["employee_id", "period_month"], ignore_index=True)
