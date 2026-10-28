import pandas as pd

from payequity.pipeline import generate, validate
from payequity.validation.checks import check_primary_key
from payequity.validation.schema import missing_columns


def test_duplicate_primary_key_is_reported():
    frame = pd.DataFrame({"employee_id": ["E1", "E1"]})
    assert check_primary_key(frame, "employee_id") == ["duplicate employee_id: E1"]


def test_missing_schema_columns_are_reported():
    assert "fte" in missing_columns("salary_record", ["salary_record_id"])


def test_generated_baseline_passes_validation():
    assert validate(generate("starter", 20261022)) == {}
