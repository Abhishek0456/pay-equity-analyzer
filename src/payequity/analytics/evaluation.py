"""Part 6/9 — evaluate detected issue labels against ground truth."""
from __future__ import annotations
import pandas as pd

def evaluate(detected: pd.DataFrame, ground_truth: pd.DataFrame, issue_column: str = "issue_type") -> pd.DataFrame:
    truth = set(zip(ground_truth["entity"], ground_truth["record_id"], ground_truth[issue_column]))
    found = set(zip(detected["entity"], detected["record_id"], detected[issue_column]))
    rows = []
    for issue in sorted(set(ground_truth[issue_column]) | set(detected[issue_column])):
        tp = len({x for x in truth & found if x[2] == issue})
        actual = sum(x[2] == issue for x in truth)
        predicted = sum(x[2] == issue for x in found)
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        rows.append({"issue_type": issue, "true_positive": tp, "precision": precision,
                     "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0})
    return pd.DataFrame(rows)

def evaluate_flags(*args, **kwargs):
    return evaluate(*args, **kwargs)
