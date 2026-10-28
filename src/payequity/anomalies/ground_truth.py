"""Part 6 — Ground-truth label persistence, kept separate from analytics input."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = ["gt_id", "entity", "record_id", "issue_type", "rule_id", "expected_decision", "notes"]

def validate_ground_truth(labels: pd.DataFrame) -> pd.DataFrame:
    missing = set(REQUIRED_COLUMNS) - set(labels.columns)
    if missing:
        raise ValueError(f"ground truth missing columns: {sorted(missing)}")
    result = labels[REQUIRED_COLUMNS].copy()
    if result["gt_id"].duplicated().any():
        raise ValueError("duplicate ground-truth IDs")
    return result

def write_ground_truth(labels: pd.DataFrame, directory: str | Path) -> dict[str, Path]:
    result = validate_ground_truth(labels)
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    csv_path, json_path = target / "ground_truth.csv", target / "ground_truth.json"
    result.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(result.to_dict(orient="records"), indent=2), encoding="utf-8")
    return {"csv": csv_path, "json": json_path}

def save_ground_truth(*args, **kwargs):
    return write_ground_truth(*args, **kwargs)
