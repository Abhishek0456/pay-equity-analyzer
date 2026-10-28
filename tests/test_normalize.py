import pandas as pd

from payequity.analytics.normalize import normalize_salary


def test_normalize_fte_and_fx():
    salary = pd.DataFrame([{"base_salary_actual": 50000, "fte": .5,
                            "currency_code": "GBP", "period_month": "2026-01"}])
    fx = pd.DataFrame([{"currency_code": "GBP", "period_month": "2026-01",
                        "usd_per_unit": 1.25}])
    result = normalize_salary(salary, fx)
    assert result.loc[0, "base_salary_fte"] == 100000
    assert result.loc[0, "base_salary_usd_fte"] == 125000
    assert bool(result.loc[0, "is_comparable"])


def test_missing_fx_is_not_comparable():
    salary = pd.DataFrame([{"base_salary_actual": 50000, "fte": 1,
                            "currency_code": "EUR", "period_month": "2026-01"}])
    result = normalize_salary(salary, pd.DataFrame(columns=["currency_code", "period_month", "usd_per_unit"]))
    assert not bool(result.loc[0, "is_comparable"])
    assert pd.isna(result.loc[0, "base_salary_usd_fte"])
    assert result.loc[0, "normalization_flag"] == "MISSING_FX_RATE"
