import pandas as pd

from payequity.analytics.disparity import detect_disparities, robust_z


def test_robust_z_centers_at_zero():
    scores = robust_z(pd.Series([10.0, 10.0, 10.0]))
    assert (scores == 0).all()


def test_small_group_is_not_classified_as_outlier():
    records = pd.DataFrame({"group_id": ["G1"] * 4,
                            "base_salary_usd_fte": [80000, 82000, 83000, 200000]})
    result = detect_disparities(records)
    assert set(result["disparity_flag"]) == {"INSUFFICIENT_N"}


def test_large_group_flags_extreme_residual():
    records = pd.DataFrame({"group_id": ["G1"] * 6,
                            "base_salary_usd_fte": [80000, 81000, 82000, 83000, 84000, 300000]})
    result = detect_disparities(records)
    assert "UNEXPLAINED_OUTLIER" in set(result["disparity_flag"])
