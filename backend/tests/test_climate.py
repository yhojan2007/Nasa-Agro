"""Unidades, huecos -999 y la climatología real de Cochabamba."""

import json

import pytest

from app.climate import monthly_precip_mm, parse_climatology, parse_daily
from app.nasa_client import NasaError, snap
from app.paths import DEMO_DIR


def _cochabamba() -> dict:
    return json.loads((DEMO_DIR / "power_climatology_cochabamba.json").read_text(encoding="utf-8"))


def test_january_rain_uses_millimetres_per_day() -> None:
    raw = _cochabamba()
    lon, lat, _elevation = raw["geometry"]["coordinates"]
    cell = snap(lat, lon)
    climate = parse_climatology(raw, "fixture_demo", cell, lat, lon)
    enero = climate.meses[0]
    assert enero.t2m == pytest.approx(14.16)
    assert enero.precip_mm == pytest.approx(3.36 * 31)
    assert climate.unidades["PRECTOTCORR"] == "mm/day"
    assert "ANN" not in {month.mes for month in climate.meses}


def test_missing_sentinel_becomes_none() -> None:
    raw = _cochabamba()
    raw["properties"]["parameter"]["T2M"]["JAN"] = -999
    lon, lat, _elevation = raw["geometry"]["coordinates"]
    climate = parse_climatology(raw, "fixture_demo", snap(lat, lon), lat, lon)
    assert climate.meses[0].t2m is None


def test_monthly_units_are_not_multiplied_by_days() -> None:
    assert monthly_precip_mm(120, 31, "mm/month") == 120
    assert monthly_precip_mm(2, 31, "mm/day") == 62


def test_unknown_precip_unit_is_rejected() -> None:
    with pytest.raises(NasaError, match="no se reconoce"):
        monthly_precip_mm(1, 30, "inches")


def test_missing_units_block_is_rejected() -> None:
    raw = _cochabamba()
    del raw["parameters"]
    lon, lat, _elevation = raw["geometry"]["coordinates"]
    with pytest.raises(NasaError, match="unidades"):
        parse_climatology(raw, "nasa_power", snap(lat, lon), lat, lon)


def test_daily_fixture_parses_leap_year() -> None:
    raw = json.loads((DEMO_DIR / "power_daily_cochabamba_2024.json").read_text(encoding="utf-8"))
    rows = parse_daily(raw)
    assert len(rows) == 366
    assert rows[0].day.isoformat() == "2024-01-01"
    assert rows[0].precip == pytest.approx(2.6)
    assert raw["parameters"]["PRECTOTCORR"]["units"] == "mm/day"


def test_daily_missing_value_is_skipped() -> None:
    raw = json.loads((DEMO_DIR / "power_daily_cochabamba_2024.json").read_text(encoding="utf-8"))
    raw["properties"]["parameter"]["PRECTOTCORR"]["20240101"] = -999
    rows = parse_daily(raw)
    assert rows[0].precip is None
