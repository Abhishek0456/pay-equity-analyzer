"""Part 4 — compa-ratio and band-position metrics (R-MET-01/02)."""

from __future__ import annotations

import pandas as pd


def calculate_metrics(
    salary_records: pd.DataFrame,
    bands: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Calculate derived compensation metrics without mutating the input.

    ``salary_records`` must contain ``base_salary_fte`` and either the three
    band values or ``band_id`` plus ``bands``.  Missing/invalid bands produce
    non-comparable rows with a traceable flag.
    """
    required = {"base_salary_fte"}
    missing = required - set(salary_records.columns)
    if missing:
        raise ValueError(f"salary_records missing required columns: {sorted(missing)}")
    result = salary_records.copy()
    band_cols = {"band_min", "band_mid", "band_max"}
    if not band_cols.issubset(result.columns):
        if bands is None or "band_id" not in result or "band_id" not in bands:
            raise ValueError("provide band_min/band_mid/band_max or bands keyed by band_id")
        lookup = bands[["band_id", *band_cols]].copy()
        if lookup.duplicated("band_id").any():
            raise ValueError("bands contains duplicate band_id rows")
        result = result.merge(lookup, on="band_id", how="left", validate="many_to_one")

    denominator = result["band_max"].astype(float) - result["band_min"].astype(float)
    valid_band = (
        result[["band_min", "band_mid", "band_max"]].notna().all(axis=1)
        & result["band_min"].astype(float).lt(result["band_mid"].astype(float))
        & result["band_mid"].astype(float).lt(result["band_max"].astype(float))
        & denominator.gt(0)
    )
    result["compa_ratio"] = result["base_salary_fte"].astype(float) / result["band_mid"]
    result["band_position"] = (result["base_salary_fte"].astype(float) - result["band_min"]) / denominator
    result.loc[~valid_band, ["compa_ratio", "band_position"]] = float("nan")
    result["metric_flag"] = result["compa_ratio"].where(valid_band).map(
        lambda value: "BELOW_BAND_MIN" if pd.notna(value) and value < 0.80 else None
    )
    result.loc[~valid_band, "metric_flag"] = "INVALID_OR_MISSING_BAND"
    return result


def build_metrics(*args, **kwargs) -> pd.DataFrame:
    """Compatibility alias used by pipeline callers."""
    return calculate_metrics(*args, **kwargs)
