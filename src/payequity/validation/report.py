"""Part 7 — validation report persistence."""
from __future__ import annotations
import json
from pathlib import Path

def make_report(errors: dict[str, list[str]]) -> dict:
    total = sum(len(items) for items in errors.values())
    return {"valid": total == 0, "error_count": total, "errors": errors}

def write_report(errors: dict[str, list[str]], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(make_report(errors), indent=2), encoding="utf-8")
    return target

def validation_summary(errors):
    return make_report(errors)
