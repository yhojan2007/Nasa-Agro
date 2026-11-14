"""Percentiles de lluvia y la serie real de un solo año."""

import json
from datetime import date, timedelta

from app.alerts import build_alerts, classify_rain, percentile_of
from app.climate import DailyObs, parse_daily
from app.paths import DEMO_DIR


def test_percentile_and_class_boundaries() -> None:
    assert percentile_of(0, [1, 2, 3]) == 0
    assert percentile_of(4, [1, 2, 3]) == 100
    assert classify_rain(9.9) == "sequia_severa"
    assert classify_rain(10) == "deficit_lluvia"
    assert classify_rain(24.9) == "deficit_lluvia"
    assert classify_rain(25) == "normal"
    assert classify_rain(75) == "normal"
    assert classify_rain(75.1) == "exceso_lluvia"
    assert classify_rain(90) == "exceso_lluvia"
    assert classify_rain(90.1) == "exceso_extremo"


def _series(
    amount_by_year: dict[int, float],
    tmin: float = 10,
    soil: float = 0.5,
) -> list[DailyObs]:
    rows: list[DailyObs] = []
    anchor = date(2025, 11, 1)
    for year, amount in amount_by_year.items():
        end = anchor.replace(year=year)
        for offset in range(60):
            rows.append(DailyObs(end - timedelta(days=offset), amount, tmin, soil))
    return rows


def test_current_year_drier_than_history_is_not_a_forecast() -> None:
    amounts = {year: 5.0 for year in range(2006, 2025)}
    amounts[2025] = 0.0
    alerts = build_alerts(_series(amounts), date(2025, 11, 1))
    rain = [item for item in alerts if item.ventana_dias == 30 and item.tipo != "helada"]
    assert rain[0].tipo == "sequia_severa"
    assert "va a haber" not in rain[0].mensaje
    assert "habrá" not in rain[0].mensaje
    assert "más secas" in rain[0].mensaje
    assert "pronóstico" not in rain[0].mensaje.lower()


def test_wet_year_is_excess_and_dry_soil_does_not_change_the_class() -> None:
    amounts = {year: 1.0 for year in range(2006, 2025)}
    amounts[2025] = 20.0
    alerts = build_alerts(_series(amounts, soil=0.1), date(2025, 11, 1))
    rain = next(item for item in alerts if item.ventana_dias == 30 and item.tipo != "helada")
    assert rain.tipo == "exceso_extremo"
    assert "zona de raíces" in rain.mensaje


def test_frost_alert_uses_place_threshold_not_a_crop() -> None:
    amounts = {year: 3.0 for year in range(2006, 2026)}
    rows = _series(amounts, tmin=10)
    current_end = date(2025, 11, 1)
    for offset in range(30):
        rows.append(DailyObs(current_end - timedelta(days=offset), 3.0, -1, 0.5))
    alerts = build_alerts(rows, current_end)
    frost = next(item for item in alerts if item.tipo == "helada")
    assert "2 °C" in frost.mensaje
    assert "va a haber" not in frost.mensaje


def test_one_real_year_is_not_enough_history() -> None:
    raw = json.loads((DEMO_DIR / "power_daily_cochabamba_2024.json").read_text(encoding="utf-8"))
    alerts = build_alerts(parse_daily(raw))
    assert alerts[0].tipo == "sin_historico"
    assert all("va a haber" not in item.mensaje for item in alerts)
