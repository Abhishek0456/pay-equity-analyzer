"""Part 8 — tabular export helpers."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

def write_table(frame: pd.DataFrame, name: str, directory: str | Path) -> Path:
    target = Path(directory); target.mkdir(parents=True, exist_ok=True)
    path = target / f"{name}.csv"
    frame.to_csv(path, index=False)
    return path

def write_tables(tables: dict[str, pd.DataFrame], directory: str | Path) -> dict[str, Path]:
    return {name: write_table(frame, name, directory) for name, frame in tables.items()}
