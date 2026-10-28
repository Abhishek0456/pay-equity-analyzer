"""Part 4 — FTE normalization and currency conversion (R-NORM-01/02)."""

from __future__ import annotations

import pandas as pd


def normalize_salary(
    salary_records: pd.DataFrame,
    fx_rates: pd.DataFrame,
    base_currency: str = "USD",
) -> pd.DataFrame:
    """Return salary records with derived FTE and base-currency pay columns.

    FX is joined by ``(currency_code, period_month)``.  Missing or invalid
    rates are deliberately retained as non-comparable rows rather than being
    treated as a 1.0 rate.
    """
    required = {
        "base_salary_actual", "fte", "currency_code", "period_month",
    }
    missing = required - set(salary_records.columns)
    if missing:
        raise ValueError(f"salary_records missing required columns: {sorted(missing)}")
    fx_required = {"currency_code", "period_month", "usd_per_unit"}
    fx_missing = fx_required - set(fx_rates.columns)
    if fx_missing:
        raise ValueError(f"fx_rates missing required columns: {sorted(fx_missing)}")

    result = salary_records.copy()
    result["base_salary_fte"] = (
        result["base_salary_actual"].astype(float) / result["fte"].astype(float)
    )

    rates = fx_rates[["currency_code", "period_month", "usd_per_unit"]].copy()
    if rates.duplicated(["currency_code", "period_month"]).any():
        raise ValueError("fx_rates contains duplicate currency/period rows")
    rates = rates.rename(columns={"usd_per_unit": "fx_usd_per_unit"})
    result = result.merge(rates, on=["currency_code", "period_month"], how="left", validate="many_to_one")

    # The generated master data stores USD as 1.0, but keeping this explicit
    # makes the function safe with minimal hand-built fixtures.
    result.loc[result["currency_code"].eq(base_currency) & result["fx_usd_per_unit"].isna(),
               "fx_usd_per_unit"] = 1.0
    result["base_salary_usd_fte"] = result["base_salary_fte"] * result["fx_usd_per_unit"]
    result["is_comparable"] = result["fx_usd_per_unit"].notna() & result["fx_usd_per_unit"].gt(0)
    result["normalization_flag"] = result["is_comparable"].map({True: None, False: "MISSING_FX_RATE"})
    return result


def normalize_compensation(*args, **kwargs) -> pd.DataFrame:
    """Compatibility alias for callers using the analytics-layer name."""
    return normalize_salary(*args, **kwargs)
