"""Part 1 — Load config/default.json + config/reference/*.json into a typed Settings object.

Responsibilities: resolve scale (starter/full), seed override, history window, anomaly rates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"


@dataclass(frozen=True)
class Settings:
    seed: int
    scale: str
    n_employees: int
    review_year: int
    history_start: str  # YYYY-MM
    history_end: str    # YYYY-MM
    as_of_date: date
    base_currency: str
    workforce: dict[str, Any]
    comp: dict[str, Any]
    anomalies: dict[str, Any]
    analysis: dict[str, Any]
    roles: list[dict[str, Any]] = field(repr=False)
    levels: list[dict[str, Any]] = field(repr=False)
    locations: list[dict[str, Any]] = field(repr=False)
    fx_base: dict[str, float] = field(repr=False)

    @property
    def history_years(self) -> list[int]:
        return list(range(int(self.history_start[:4]), int(self.history_end[:4]) + 1))

    @property
    def months(self) -> list[str]:
        """All YYYY-MM periods in the history window, inclusive."""
        y, m = int(self.history_start[:4]), int(self.history_start[5:])
        end_y, end_m = int(self.history_end[:4]), int(self.history_end[5:])
        out = []
        while (y, m) <= (end_y, end_m):
            out.append(f"{y:04d}-{m:02d}")
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return out


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_settings(
    scale: str = "starter",
    seed: int | None = None,
    config_dir: Path | str | None = None,
) -> Settings:
    """Build Settings for a scale; `seed` overrides the config seed when given."""
    config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    cfg = _read_json(config_dir / "default.json")
    ref = config_dir / "reference"

    if scale not in cfg["scales"]:
        raise ValueError(f"unknown scale {scale!r}; expected one of {sorted(cfg['scales'])}")
    if cfg["history_start"] > cfg["history_end"]:
        raise ValueError("history_start must not be after history_end")

    fx_base = {k: v for k, v in _read_json(ref / "fx_base.json").items() if not k.startswith("_")}
    locations = _read_json(ref / "locations.json")
    missing_ccy = {loc["currency_code"] for loc in locations} - fx_base.keys()
    if missing_ccy:
        raise ValueError(f"fx_base.json has no anchor for currencies: {sorted(missing_ccy)}")

    return Settings(
        seed=cfg["seed"] if seed is None else seed,
        scale=scale,
        n_employees=cfg["scales"][scale]["employees"],
        review_year=cfg["review_year"],
        history_start=cfg["history_start"],
        history_end=cfg["history_end"],
        as_of_date=date.fromisoformat(cfg["as_of_date"]),
        base_currency=cfg["base_currency"],
        workforce=cfg["workforce"],
        comp=cfg["comp"],
        anomalies=cfg["anomalies"],
        analysis=cfg["analysis"],
        roles=_read_json(ref / "roles.json"),
        levels=_read_json(ref / "levels.json"),
        locations=locations,
        fx_base=fx_base,
    )
