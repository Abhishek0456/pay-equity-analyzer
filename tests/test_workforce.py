from payequity.pipeline import generate


def test_starter_workforce_has_expected_size():
    tables = generate("starter", 20261022)
    assert len(tables["employee"]) == 500
    assert tables["employee"]["employee_id"].is_unique


def test_assignments_reference_existing_employees():
    tables = generate("starter", 20261022)
    employees = set(tables["employee"]["employee_id"])
    assignments = tables["job_assignment"]
    assert set(assignments["employee_id"]).issubset(employees)
    assert assignments["fte"].between(.2, 1.0).all()
