import pandas as pd

from payequity.analytics.metrics import calculate_metrics


def test_metrics_calculate_compa_and_position():
    salary = pd.DataFrame([{"salary_record_id": "SAL-1", "base_salary_fte": 90000,
                            "band_id": "B1"}])
    bands = pd.DataFrame([{"band_id": "B1", "band_min": 80000,
                           "band_mid": 100000, "band_max": 120000}])
    result = calculate_metrics(salary, bands)
    assert result.loc[0, "compa_ratio"] == .9
    assert result.loc[0, "band_position"] == .25
    assert pd.isna(result.loc[0, "metric_flag"])


def test_invalid_band_is_flagged():
    salary = pd.DataFrame([{"base_salary_fte": 90000, "band_id": "B1"}])
    bands = pd.DataFrame([{"band_id": "B1", "band_min": 100000,
                           "band_mid": 90000, "band_max": 120000}])
    result = calculate_metrics(salary, bands)
    assert result.loc[0, "metric_flag"] == "INVALID_OR_MISSING_BAND"
    assert pd.isna(result.loc[0, "compa_ratio"])
