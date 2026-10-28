"""Part 6 — deterministic, labelled anomaly injection."""
from __future__ import annotations
import numpy as np
import pandas as pd

def inject_anomalies(tables: dict[str, pd.DataFrame], seed: int = 0, rates: dict | None = None):
    """Return (copied tables, ground-truth labels); labels never feed analytics."""
    out = {k: v.copy() for k, v in tables.items()}
    labels = []
    rng = np.random.default_rng(seed)
    rates = rates or {}
    salary = out.get("salary_record")
    if salary is None or salary.empty:
        return out, pd.DataFrame(columns=["gt_id", "entity", "record_id", "issue_type", "rule_id", "expected_decision", "notes"])
    def label(entity, record_id, issue, rule, decision, notes=""):
        labels.append({"gt_id": f"GT-{len(labels)+1:06d}", "entity": entity, "record_id": record_id, "issue_type": issue, "rule_id": rule, "expected_decision": decision, "notes": notes})
    def choose(rate, minimum=False):
        count = int(len(salary) * float(rates.get(rate, 0)))
        if minimum and float(rates.get(rate, 0)) > 0: count = max(1, count)
        return rng.choice(salary.index.to_numpy(), size=min(count, len(salary)), replace=False) if count else []

    # FTE_IGNORED: actual pay is overwritten with the normalized amount.
    for idx in choose("FTE_IGNORED"):
        if float(salary.loc[idx, "fte"]) < 1:
            salary.loc[idx, "base_salary_actual"] = round(float(salary.loc[idx, "base_salary_actual"]) / float(salary.loc[idx, "fte"]), 2)
            label("salary_record", salary.loc[idx, "salary_record_id"], "FTE_IGNORED", "R-NORM-01", "FLAG")

    # UNAPPROVED_ADJUSTMENT: mark an adjustment without a proposal link.
    for idx in choose("UNAPPROVED_ADJUSTMENT"):
        salary.loc[idx, "change_reason"] = "ADJUSTMENT"
        salary.loc[idx, "adjustment_id"] = None
        label("salary_record", salary.loc[idx, "salary_record_id"], "UNAPPROVED_ADJUSTMENT", "R-ADJ-04", "FLAG")

    # EXPIRED_BAND: use a prior-year band when one exists for the record.
    bands = out.get("compensation_band")
    for idx in choose("EXPIRED_BAND"):
        if bands is not None and "band_id" in salary and not bands.empty:
            current = str(salary.loc[idx, "band_id"])
            prior = bands[bands["band_id"].astype(str).str.rsplit("-", n=1).str[-1].astype(int).lt(int(str(salary.loc[idx, "period_month"])[:4]))]
            if not prior.empty:
                salary.loc[idx, "band_id"] = prior.iloc[-1]["band_id"]
                label("salary_record", salary.loc[idx, "salary_record_id"], "EXPIRED_BAND", "R-BAND-01", "FLAG")

    # UNEXPLAINED_OUTLIER: lower pay without a documented factor change.
    n = max(1, int(len(salary) * float(rates.get("UNEXPLAINED_OUTLIER", 0))))
    for idx in rng.choice(salary.index.to_numpy(), size=min(n, len(salary)), replace=False):
        salary.loc[idx, "base_salary_actual"] = round(float(salary.loc[idx, "base_salary_actual"]) * 0.75, 2)
        label("salary_record", salary.loc[idx, "salary_record_id"], "UNEXPLAINED_OUTLIER", "R-DIS-02", "REVIEW")
    # FX_MISSING: remove selected currency/month rates from the analytical input.
    fx = out.get("fx_rate")
    if fx is not None and not fx.empty:
        for idx in choose("FX_MISSING_SLICES")[:int(rates.get("FX_MISSING_SLICES", 0))]:
            key = (salary.loc[idx, "currency_code"], salary.loc[idx, "period_month"])
            hit = fx.index[fx["currency_code"].eq(key[0]) & fx["period_month"].eq(key[1])]
            if len(hit):
                out["fx_rate"] = fx.drop(hit)
                label("fx_rate", f"{key[0]}-{key[1]}", "FX_MISSING", "R-NORM-02", "EXCLUDE")
    out["salary_record"] = salary
    return out, pd.DataFrame(labels)

def inject(*args, **kwargs):
    return inject_anomalies(*args, **kwargs)
