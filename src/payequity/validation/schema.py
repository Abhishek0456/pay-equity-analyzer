"""Part 7 — machine-readable required-column schema."""
SCHEMA = {
    "employee": {"employee_id", "hire_date", "employment_status"},
    "job_assignment": {"assignment_id", "employee_id", "fte", "effective_from"},
    "salary_record": {"salary_record_id", "employee_id", "period_month", "base_salary_actual", "fte"},
    "fx_rate": {"fx_rate_id", "currency_code", "period_month", "usd_per_unit"},
    "compensation_band": {"band_id", "band_min", "band_mid", "band_max"},
}

def missing_columns(table: str, columns) -> list[str]:
    return sorted(SCHEMA.get(table, set()) - set(columns))

def validate_schema(tables) -> dict[str, list[str]]:
    return {name: missing_columns(name, frame.columns) for name, frame in tables.items() if missing_columns(name, frame.columns)}
