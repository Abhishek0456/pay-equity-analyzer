"""Part 4 — Expected-pay model and robust residual outliers (R-DIS-01..03)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def robust_z(values: pd.Series) -> pd.Series:
    """Return MAD-based robust z scores (1.4826 scales MAD to sigma)."""
    median = values.median()
    mad = (values - median).abs().median()
    if pd.isna(mad) or mad == 0:
        return pd.Series(0.0, index=values.index)
    return (values - median) / (1.4826 * mad)


def detect_disparities(
    records: pd.DataFrame,
    group_col: str = "group_id",
    pay_col: str = "base_salary_usd_fte",
    min_group_size: int = 5,
    threshold: float = 2.0,
) -> pd.DataFrame:
    """Flag unexplained log-pay residuals within comparable groups.

    The expected pay baseline is each group's median after documented factors
    already represented by the grouping.  Small groups are reported as
    insufficient rather than statistically classified.
    """
    required = {group_col, pay_col}
    missing = required - set(records.columns)
    if missing:
        raise ValueError(f"records missing required columns: {sorted(missing)}")
    result = records.copy()
    pay = pd.to_numeric(result[pay_col], errors="coerce")
    result["expected_pay"] = np.nan
    result["log_residual"] = np.nan
    result["robust_z"] = np.nan
    result["disparity_flag"] = "NON_COMPARABLE"
    for _, idx in result.groupby(group_col, dropna=False, sort=False).groups.items():
        valid = idx[pay.loc[idx].gt(0).fillna(False)]
        if len(valid) == 0:
            continue
        expected = float(np.log(pay.loc[valid]).median())
        residual = np.log(pay.loc[valid]) - expected
        result.loc[valid, "expected_pay"] = np.exp(expected)
        result.loc[valid, "log_residual"] = residual
        if len(valid) < min_group_size:
            result.loc[valid, "disparity_flag"] = "INSUFFICIENT_N"
            continue
        scores = robust_z(residual)
        result.loc[valid, "robust_z"] = scores
        result.loc[valid, "disparity_flag"] = np.where(
            scores.abs().gt(threshold), "UNEXPLAINED_OUTLIER", "NONE"
        )
    return result


def find_outliers(*args, **kwargs) -> pd.DataFrame:
    return detect_disparities(*args, **kwargs)
