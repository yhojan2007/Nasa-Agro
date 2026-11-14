"""Trapecio, ventana, media geométrica y orden entre zonas de referencia."""

import json

from app.catalog import load_crops
from app.climate import parse_climatology
from app.constants import AVISO
from app.nasa_client import snap
from app.paths import DEMO_DIR
from app.schemas import Alerta, SueloIn
from app.scoring import (
    Factor,
    apply_alert_adjustment,
    etiqueta,
    geometric_score,
    months_in_window,
    rank_crops,
    score_month,
    trapezoid,
)


def test_trapezoid_edges_and_slope() -> None:
    assert trapezoid(10, 10, 20, 30, 40) == 0
    assert trapezoid(40, 10, 20, 30, 40) == 0
    assert trapezoid(25, 10, 20, 30, 40) == 1
    assert trapezoid(15, 10, 20, 30, 40) == 0.5
    assert trapezoid(35, 10, 20, 30, 40) == 0.5


def test_trapezoid_equal_bounds_do_not_raise() -> None:
    assert trapezoid(0, 5, 5, 10, 15) == 0
    assert trapezoid(20, 0, 10, 15, 15) == 0


def test_window_crosses_the_year() -> None:
    assert months_in_window(10, 4) == [10, 11, 12, 1]


def test_geometric_mean_and_critical_zero() -> None:
    even = geometric_score(
        [Factor("temperatura", 1, 1, True), Factor("precipitacion", 0.25, 1, True)]
    )
    assert round(even * 100) == 50
    assert geometric_score(
        [Factor("temperatura", 0, 1, True), Factor("precipitacion", 1, 1, True)]
    ) == 0
    kept = geometric_score(
        [Factor("temperatura", 1, 1, True), Factor("textura", 0, 0.4, False)]
    )
    assert kept == 1


def test_labels() -> None:
    assert etiqueta(75) == "Muy viable"
    assert etiqueta(50) == "Viable con cuidados"
    assert etiqueta(25) == "Poco viable"
    assert etiqueta(24) == "No recomendado"


def _zone(name: str):
    raw = json.loads((DEMO_DIR / f"power_climatology_{name}.json").read_text(encoding="utf-8"))
    lon, lat, _elevation = raw["geometry"]["coordinates"]
    return parse_climatology(raw, "fixture_demo", snap(lat, lon), lat, lon)


def _score(zone: str, crop_id: str) -> int:
    climate = _zone(zone)
    crop = next(item for item in load_crops() if item.id == crop_id)
    return rank_crops([crop], climate.meses, None, None, [])[0].puntaje


def test_reference_zones_do_not_reverse_local_expectation() -> None:
    assert _score("el_alto", "quinua") > _score("el_alto", "maiz")
    assert _score("el_alto", "quinua") > _score("el_alto", "soya")
    assert _score("santa_cruz", "maiz") > _score("santa_cruz", "quinua")
    assert _score("santa_cruz", "soya") > _score("santa_cruz", "quinua")


def test_explanation_quotes_the_numbers_and_the_aviso_is_stable() -> None:
    climate = _zone("santa_cruz")
    crop = next(item for item in load_crops() if item.id == "maiz")
    recommendation = rank_crops([crop], climate.meses, 10, None, [])[0]
    assert recommendation.mes_siembra == 10
    assert f"{recommendation.temperatura_ventana_c:.1f}" in recommendation.explicacion
    assert "Puntaje" in recommendation.explicacion
    assert "va a haber" not in recommendation.explicacion
    assert AVISO == "Recomendación orientativa; consulta a un técnico local."


def test_limiting_factor_is_the_lowest() -> None:
    climate = _zone("el_alto")
    crop = next(item for item in load_crops() if item.id == "maiz")
    scored = score_month(crop, climate.meses, 1, None)
    assert scored["factor_limitante"] == "temperatura"
    assert scored["puntaje"] == 0


def _drought(ventana: int = 30) -> Alerta:
    return Alerta(
        tipo="deficit_lluvia",
        percentil=18,
        ventana_dias=ventana,
        mensaje=(
            "Las últimas 4 semanas están entre el 25 % más secas "
            "de los últimos 20 años en tu zona."
        ),
    )


def test_alert_adjustment_is_small_and_skips_a_zero() -> None:
    base = next(item for item in load_crops() if item.id == "maiz")
    tolerant = base.model_copy(update={"tolerancia_sequia": "alta"})
    sensitive = base.model_copy(update={"tolerancia_sequia": "baja"})
    assert apply_alert_adjustment(70, tolerant, [_drought()], 100) == (78, True)
    assert apply_alert_adjustment(70, sensitive, [_drought()], 100) == (58, True)
    assert apply_alert_adjustment(70, base, [_drought()], 100) == (70, False)
    assert apply_alert_adjustment(0, tolerant, [_drought()], 100) == (0, False)
    assert apply_alert_adjustment(70, tolerant, [_drought(60)], 100) == (70, False)


def test_excess_penalty_only_above_the_crop_maximum() -> None:
    crop = next(item for item in load_crops() if item.id == "maiz")
    alert = Alerta(
        tipo="exceso_lluvia",
        percentil=80,
        ventana_dias=30,
        mensaje=(
            "Las últimas 4 semanas están entre el 25 % más lluviosas "
            "de los últimos 20 años en tu zona."
        ),
    )
    above = apply_alert_adjustment(70, crop, [alert], crop.precip_ciclo_mm.abs_max + 10)
    below = apply_alert_adjustment(70, crop, [alert], crop.precip_ciclo_mm.abs_max - 10)
    assert above == (62, True)
    assert below == (70, False)


def test_ph_outside_range_can_zero_the_score() -> None:
    climate = _zone("santa_cruz")
    crop = next(item for item in load_crops() if item.id == "maiz")
    scored = score_month(crop, climate.meses, 11, SueloIn(ph=3))
    assert scored["puntaje"] == 0
    assert scored["factor_limitante"] == "ph"
    assert any("encalado" in note for note in scored["observaciones"])
