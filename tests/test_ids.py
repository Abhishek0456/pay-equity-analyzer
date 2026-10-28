import pytest

from payequity.ids import employee_id, fx_rate_id, group_id, is_valid, salary_record_id


def test_ids_follow_documented_formats():
    assert employee_id(1) == "EMP-000001"
    assert salary_record_id("EMP-000001", "2026-01") == "SAL-EMP-000001-2026-01"
    assert fx_rate_id("USD", "2026-01") == "FX-USD-2026-01"
    assert group_id(2026, 1) == "CG-2026-0001"


def test_invalid_month_is_rejected():
    with pytest.raises(ValueError):
        salary_record_id("EMP-000001", "2026-13")


def test_is_valid_checks_kind_pattern():
    assert is_valid("employee", "EMP-000001")
    assert not is_valid("employee", "employee-1")
