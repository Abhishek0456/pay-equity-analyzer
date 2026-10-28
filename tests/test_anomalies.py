import pandas as pd

from payequity.anomalies.ground_truth import write_ground_truth
from payequity.anomalies.inject import inject_anomalies


def test_outlier_injection_is_deterministic():
    tables = {"salary_record": pd.DataFrame([
        {"salary_record_id": "S1", "base_salary_actual": 100000, "fte": 1,
         "currency_code": "USD", "period_month": "2026-01"},
        {"salary_record_id": "S2", "base_salary_actual": 100000, "fte": 1,
         "currency_code": "USD", "period_month": "2026-01"},
    ])}
    _, first = inject_anomalies(tables, 7, {"UNEXPLAINED_OUTLIER": 0.5})
    _, second = inject_anomalies(tables, 7, {"UNEXPLAINED_OUTLIER": 0.5})
    assert first["record_id"].tolist() == second["record_id"].tolist()


def test_ground_truth_writes_csv_and_json(tmp_path):
    labels = pd.DataFrame([{"gt_id": "GT-000001", "entity": "salary_record",
                            "record_id": "S1", "issue_type": "FX_MISSING",
                            "rule_id": "R-NORM-02", "expected_decision": "EXCLUDE", "notes": ""}])
    paths = write_ground_truth(labels, tmp_path)
    assert paths["csv"].exists() and paths["json"].exists()
