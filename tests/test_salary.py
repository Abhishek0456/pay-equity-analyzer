from payequity.pipeline import generate


def test_salary_records_are_positive_and_unique_per_employee_month():
    tables = generate("starter", 20261022)
    salary = tables["salary_record"]
    assert (salary["base_salary_actual"] > 0).all()
    assert salary[["employee_id", "period_month"]].duplicated().sum() == 0


def test_salary_fte_matches_documented_bounds():
    salary = generate("starter", 20261022)["salary_record"]
    assert salary["fte"].between(.2, 1.0).all()
