"""Part 9 — reproducibility checks for generated tables."""
from __future__ import annotations
import hashlib
import pandas as pd

def table_checksum(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def checksums(tables: dict[str, pd.DataFrame]) -> dict[str, str]:
    return {name: table_checksum(tables[name]) for name in sorted(tables)}

def verify_reproducible(factory, *args, **kwargs) -> bool:
    return checksums(factory(*args, **kwargs)) == checksums(factory(*args, **kwargs))
