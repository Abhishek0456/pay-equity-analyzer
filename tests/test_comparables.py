import pandas as pd
import pytest

from payequity.analytics.comparables import build_comparable_groups


def test_default_groups_same_role_level_location():
    records = pd.DataFrame([
        {"employee_id": f"E{i}", "salary_record_id": f"S{i}",
         "role_id": "R1" if i < 2 else "R2", "level_id": "L1", "location_id": "N"}
        for i in range(3)
    ])
    result = build_comparable_groups(records, "2026-01")
    assert len(result["comparable_group"]) == 2
    assert len(result["comparable_group_member"]) == 3


def test_broader_group_requires_rationale():
    records = pd.DataFrame([{"employee_id": "E1", "salary_record_id": "S1",
                             "role_id": "R1", "level_id": "L1", "location_id": "N",
                             "job_family": "ENG"}])
    with pytest.raises(ValueError, match="rationale"):
        build_comparable_groups(records, "2026-01", "SAME_FAMILY")
