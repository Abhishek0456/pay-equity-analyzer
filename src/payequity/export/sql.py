"""Part 8 — SQLite-compatible SQL seed export."""
from __future__ import annotations
from pathlib import Path
import sqlite3
import pandas as pd

def write_sql(tables: dict[str, pd.DataFrame], path: str | Path) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(":memory:")
    try:
        for name, frame in tables.items():
            frame.to_sql(name, connection, index=False, if_exists="replace")
        with target.open("w", encoding="utf-8") as stream:
            for line in connection.iterdump():
                stream.write(line + "\n")
    finally:
        connection.close()
    return target

def export_sql(*args, **kwargs):
    return write_sql(*args, **kwargs)
