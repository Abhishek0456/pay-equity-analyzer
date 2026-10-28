"""Part 7 — reusable data-integrity checks."""
from __future__ import annotations
import pandas as pd

def check_primary_key(frame: pd.DataFrame, column: str) -> list[str]:
    if column not in frame: return [f"missing column: {column}"]
    return [f"duplicate {column}: {value}" for value in frame.loc[frame[column].duplicated(keep=False), column].dropna().unique()]

def check_foreign_key(frame: pd.DataFrame, column: str, parent: pd.DataFrame, parent_column: str | None = None) -> list[str]:
    parent_column = parent_column or column
    if column not in frame or parent_column not in parent: return [f"missing FK column: {column}"]
    valid = set(parent[parent_column].dropna())
    return [f"orphan {column}: {value}" for value in frame.loc[~frame[column].isin(valid), column].dropna().unique()]

def check_salary_reconciliation(salary: pd.DataFrame, tolerance: float = 0.011) -> list[str]:
    required = {"base_salary_actual", "fte"}
    if not required.issubset(salary): return ["salary reconciliation columns missing"]
    if (salary["fte"] <= 0).any(): return ["non-positive FTE"]
    return []

def validate_tables(tables: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    errors = {}
    for name, frame in tables.items():
        if not isinstance(frame, pd.DataFrame): errors[name] = ["not a DataFrame"]; continue
        if "_id" in "".join(frame.columns):
            for col in frame.columns:
                if col.endswith("_id") and col == name + "_id":
                    errors[name] = check_primary_key(frame, col)
    if "salary_record" in tables:
        errors["salary_record"] = errors.get("salary_record", []) + check_salary_reconciliation(tables["salary_record"])
    return {k: v for k, v in errors.items() if v}

def run_checks(*args, **kwargs):
    return validate_tables(*args, **kwargs)
