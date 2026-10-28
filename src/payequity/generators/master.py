"""Part 1 — Role, Level, RoleLevel (200 combos), Location, FxRate, CompensationBand (per year, effective-dated)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from payequity import ids
from payequity.config import Settings
from payequity.rng import RngFactory

FX_MONTHLY_VOLATILITY = 0.01  # std-dev of monthly log change in usd_per_unit
BAND_ROUNDING = 100           # band amounts rounded to the nearest 100 local units


def build_roles(settings: Settings) -> pd.DataFrame:
    df = pd.DataFrame(settings.roles)
    df.insert(0, "role_id", df["role_code"].map(ids.role_id))
    df["market_base_usd"] = df["market_base_usd"].astype(float)
    df["is_active"] = True
    return df[["role_id", "role_code", "role_name", "job_family", "market_base_usd", "is_active"]]


def build_levels(settings: Settings) -> pd.DataFrame:
    df = pd.DataFrame(settings.levels).sort_values("rank", ignore_index=True)
    return df[["level_id", "level_name", "track", "rank", "level_multiplier"]]


def build_role_levels(roles: pd.DataFrame, levels: pd.DataFrame) -> pd.DataFrame:
    df = roles[["role_id", "role_code"]].merge(levels[["level_id", "rank"]], how="cross")
    df = df.sort_values(["role_code", "rank"], ignore_index=True)
    df.insert(0, "role_level_id", [ids.role_level_id(r, l) for r, l in zip(df["role_code"], df["level_id"])])
    return df[["role_level_id", "role_id", "level_id"]]


def build_locations(settings: Settings) -> pd.DataFrame:
    df = pd.DataFrame(settings.locations)
    df.insert(0, "location_id", df["location_code"].map(ids.location_id))
    return df[["location_id", "location_code", "city", "country_code", "currency_code",
               "geo_tier", "geo_differential"]]


def build_fx_rates(settings: Settings, rngs: RngFactory) -> pd.DataFrame:
    """Monthly USD-per-unit rates: a seeded log random walk from each currency's Jan anchor."""
    rng = rngs("fx_rates")
    months = settings.months
    rows = []
    for ccy in sorted(settings.fx_base):  # sorted => draw order independent of JSON key order
        if ccy == settings.base_currency:
            rates = np.ones(len(months))
        else:
            steps = np.concatenate([[0.0], rng.normal(0.0, FX_MONTHLY_VOLATILITY, len(months) - 1)])
            rates = settings.fx_base[ccy] * np.exp(np.cumsum(steps))
        rows += [
            {"fx_rate_id": ids.fx_rate_id(ccy, m), "currency_code": ccy, "period_month": m,
             "usd_per_unit": round(float(r), 6), "source": "SYNTHETIC"}
            for m, r in zip(months, rates)
        ]
    return pd.DataFrame(rows)


def _band_status(start: date, end: date, as_of: date) -> str:
    if end < as_of:
        return "EXPIRED"
    if start > as_of:
        return "FUTURE"
    return "ACTIVE"


def build_bands(
    settings: Settings,
    roles: pd.DataFrame,
    levels: pd.DataFrame,
    role_levels: pd.DataFrame,
    locations: pd.DataFrame,
    fx_rates: pd.DataFrame,
) -> pd.DataFrame:
    """One band per (role, level, location, year), priced by rule R-BAND-04 — no random noise."""
    years = settings.history_years
    spread = settings.comp["band_spread"]
    market_index = {int(y): v for y, v in settings.comp["yearly_market_index"].items()}

    df = (
        role_levels
        .merge(roles[["role_id", "role_code", "market_base_usd"]], on="role_id")
        .merge(levels[["level_id", "rank", "level_multiplier"]], on="level_id")
        .merge(locations[["location_id", "location_code", "currency_code", "geo_differential"]], how="cross")
        .merge(pd.DataFrame({"year": years}), how="cross")
    )

    jan_fx = fx_rates[fx_rates["period_month"].str.endswith("-01")].assign(
        year=lambda d: d["period_month"].str[:4].astype(int)
    )[["currency_code", "year", "usd_per_unit"]]
    df = df.merge(jan_fx, on=["currency_code", "year"], how="left", validate="many_to_one")
    if df["usd_per_unit"].isna().any():
        raise ValueError("missing January FX rate for a band currency/year")

    mid_usd = df["market_base_usd"] * df["level_multiplier"] * df["geo_differential"] * df["year"].map(market_index)
    mid_local = mid_usd / df["usd_per_unit"]

    def rnd(x: pd.Series) -> pd.Series:
        return (np.round(x / BAND_ROUNDING) * BAND_ROUNDING).astype(float)

    band_min = mid_local * 2 / (2 + spread)  # symmetric around mid: max/min = 1 + spread
    df["band_min"] = rnd(band_min)
    df["band_mid"] = rnd(mid_local)
    df["band_max"] = rnd(band_min * (1 + spread))

    df["band_id"] = [ids.band_id(r, l, c, y) for r, l, c, y in
                     zip(df["role_code"], df["level_id"], df["location_code"], df["year"])]
    df["effective_from"] = df["year"].map(lambda y: date(y, 1, 1))
    df["effective_to"] = df["year"].map(lambda y: date(y, 12, 31))
    df["band_status"] = [_band_status(s, e, settings.as_of_date)
                         for s, e in zip(df["effective_from"], df["effective_to"])]
    df["version"] = df["year"] - years[0] + 1

    df = df.sort_values(["role_code", "rank", "location_code", "year"], ignore_index=True)
    return df[["band_id", "role_id", "level_id", "location_id", "currency_code",
               "band_min", "band_mid", "band_max", "effective_from", "effective_to",
               "band_status", "version"]]


def build_master(settings: Settings, rngs: RngFactory) -> dict[str, pd.DataFrame]:
    """All master tables, keyed by table name (matches docs/data_dictionary.md)."""
    roles = build_roles(settings)
    levels = build_levels(settings)
    role_levels = build_role_levels(roles, levels)
    locations = build_locations(settings)
    fx_rates = build_fx_rates(settings, rngs)
    bands = build_bands(settings, roles, levels, role_levels, locations, fx_rates)
    return {
        "role": roles,
        "level": levels,
        "role_level": role_levels,
        "location": locations,
        "fx_rate": fx_rates,
        "compensation_band": bands,
    }
