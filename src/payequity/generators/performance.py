"""Part 3 — PerformanceEvidence: annual ratings, certifications, critical skills, market premiums.

Evidence for review_year Y is documented in Q1 of Y+1 (before the March merit cycle), so only review
years documented by as_of_date are generated. Merit in March of Y uses the Y−1 rating (salary.py
falls back to a neutral rating when none exists).

Ratings come from a persistent per-employee latent score plus yearly noise. R-GEN-02: an employee
promoted in year P gets a review_year P−1 rating ≥ 4 (when that year is generated).
Rated population for year Y: hired by Oct 1 of Y and still employed on Dec 31 of Y.
documented_by = the employee's manager, or their HR partner for the root manager.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from payequity import ids
from payequity.config import Settings
from payequity.rng import RngFactory

RATING_CENTER = 3.1
LATENT_WEIGHT = 0.7        # persistent component of the rating
NOISE_WEIGHT = 0.5         # year-to-year component
MIN_PROMOTION_RATING = 4
RATING_CUTOFF_MONTH_DAY = (10, 1)  # hired after this date in Y → not rated for Y
DOCUMENTED_WINDOW = ((1, 5), (2, 28))  # (month, day) range in Y+1, ahead of March merit

CERTIFICATION_RATE = 0.06      # per rated employee-year
CRITICAL_SKILL_RATE = 0.03
MARKET_PREMIUM_RATE = 0.02     # only for MARKET_PREMIUM_FAMILIES
MARKET_PREMIUM_FAMILIES = {"ENGINEERING", "DATA", "LEGAL"}

CERTIFICATIONS = {
    "ENGINEERING": ["AWS Solutions Architect", "CKA Kubernetes Administrator", "CISSP"],
    "DATA": ["Google Professional Data Engineer", "Databricks ML Associate"],
    "PRODUCT": ["Certified Scrum Product Owner", "PMP"],
    "SALES": ["MEDDICC Practitioner", "Salesforce Administrator"],
    "MARKETING": ["Google Ads Certification", "HubSpot Inbound"],
    "FINANCE": ["CPA", "CFA Level II"],
    "HR": ["SHRM-CP", "CIPD Level 5"],
    "OPERATIONS": ["Lean Six Sigma Green Belt", "CIPS Level 4"],
    "SUPPORT": ["ITIL 4 Foundation", "HDI Support Center Analyst"],
    "LEGAL": ["CIPP/E", "CCEP Compliance"],
}
CRITICAL_SKILLS = ["Niche domain expertise", "Key client relationship", "Platform ownership",
                   "Regulatory sign-off authority"]
MARKET_PREMIUM_TEXT = "Hot-skill market premium"
EVIDENCE_TYPE_ORDER = ["ANNUAL_RATING", "CERTIFICATION", "CRITICAL_SKILL", "MARKET_PREMIUM"]


def evidence_years(settings: Settings) -> list[int]:
    """Review years whose Q1 documentation falls on or before as_of_date."""
    m, d = DOCUMENTED_WINDOW[1]
    return [y for y in settings.history_years if date(y + 1, m, d) <= settings.as_of_date]


def _rated_employee_years(employees: pd.DataFrame, assignments: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """One row per (employee, review_year) in the rated population, with year-end job family role."""
    ey = employees[["employee_id", "hire_date", "termination_date", "manager_id", "hr_partner_id"]].merge(
        pd.DataFrame({"review_year": years}), how="cross")
    year_end = ey["review_year"].map(lambda y: date(y, 12, 31))
    cutoff = ey["review_year"].map(lambda y: date(y, *RATING_CUTOFF_MONTH_DAY))
    employed = ey["termination_date"].isna() | (ey["termination_date"].map(lambda t: t if pd.notna(t) else date.max) > year_end)
    ey = ey[(ey["hire_date"] <= cutoff) & employed].assign(year_end=year_end)

    # Assignment active on Dec 31 of the review year.
    a = assignments[["employee_id", "role_id", "effective_from", "effective_to"]].merge(
        ey[["employee_id", "review_year", "year_end"]], on="employee_id")
    active = (a["effective_from"] <= a["year_end"]) & (
        a["effective_to"].isna() | (a["effective_to"].map(lambda t: t if pd.notna(t) else date.max) >= a["year_end"]))
    a = a[active][["employee_id", "review_year", "role_id"]]
    out = ey.merge(a, on=["employee_id", "review_year"], how="left", validate="one_to_one")
    if out["role_id"].isna().any():
        raise ValueError("rated employee-year without an active assignment on Dec 31")
    return out.sort_values(["employee_id", "review_year"], ignore_index=True)


def _documented_dates(rng: np.random.Generator, years: pd.Series) -> list[date]:
    (m0, d0), (m1, d1) = DOCUMENTED_WINDOW
    starts = [date(y + 1, m0, d0) for y in years]
    spans = np.array([(date(y + 1, m1, d1) - s).days + 1 for y, s in zip(years, starts)])
    offsets = (rng.random(len(starts)) * spans).astype(int)
    return [s + timedelta(days=int(o)) for s, o in zip(starts, offsets)]


def build_performance(
    settings: Settings,
    rngs: RngFactory,
    employees: pd.DataFrame,
    assignments: pd.DataFrame,
    master: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rng = rngs("performance")
    years = evidence_years(settings)
    ey = _rated_employee_years(employees, assignments, years)
    n = len(ey)

    # Ratings: persistent latent score + yearly noise, then the R-GEN-02 floor for promotions.
    latent = dict(zip(employees["employee_id"], rng.normal(0.0, 1.0, len(employees))))
    raw = RATING_CENTER + LATENT_WEIGHT * ey["employee_id"].map(latent).to_numpy() + NOISE_WEIGHT * rng.normal(0.0, 1.0, n)
    rating = np.clip(np.round(raw), 1, 5).astype(int)
    promo = assignments[assignments["change_reason"] == "PROMOTION"]
    promo_keys = set(zip(promo["employee_id"], promo["effective_from"].map(lambda d: d.year - 1)))
    needs_floor = np.array([k in promo_keys for k in zip(ey["employee_id"], ey["review_year"])], dtype=bool)
    rating[needs_floor] = np.maximum(rating[needs_floor], MIN_PROMOTION_RATING)

    family = ey["role_id"].map(dict(zip(master["role"]["role_id"], master["role"]["job_family"])))
    documented_by = ey["manager_id"].where(ey["manager_id"].notna(), ey["hr_partner_id"])
    base = pd.DataFrame({"employee_id": ey["employee_id"], "review_year": ey["review_year"],
                         "documented_by": documented_by})

    u = rng.random((n, 3))
    cert = u[:, 0] < CERTIFICATION_RATE
    crit = u[:, 1] < CRITICAL_SKILL_RATE
    prem = (u[:, 2] < MARKET_PREMIUM_RATE) & family.isin(MARKET_PREMIUM_FAMILIES).to_numpy()
    frames = [
        base.assign(evidence_type="ANNUAL_RATING", rating=rating, value_text=None),
        base[cert].assign(evidence_type="CERTIFICATION", rating=None,
                          value_text=[str(rng.choice(CERTIFICATIONS[f])) for f in family[cert]]),
        base[crit].assign(evidence_type="CRITICAL_SKILL", rating=None,
                          value_text=[str(rng.choice(CRITICAL_SKILLS)) for _ in range(int(crit.sum()))]),
        base[prem].assign(evidence_type="MARKET_PREMIUM", rating=None, value_text=MARKET_PREMIUM_TEXT),
    ]
    df = pd.concat(frames, ignore_index=True)
    df["_type_order"] = df["evidence_type"].map(EVIDENCE_TYPE_ORDER.index)
    df = df.sort_values(["employee_id", "review_year", "_type_order"], ignore_index=True)
    df["rating"] = df["rating"].astype("Int64")
    df["documented_date"] = _documented_dates(rng, df["review_year"])
    df.insert(0, "evidence_id", [ids.evidence_id(i + 1) for i in range(len(df))])
    return df[["evidence_id", "employee_id", "evidence_type", "review_year", "rating",
               "value_text", "documented_by", "documented_date"]]
