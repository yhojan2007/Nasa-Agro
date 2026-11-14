"""Puntaje de aptitud: trapecio de EcoCrop y media geométrica ponderada."""

import math
from dataclasses import dataclass

from app.constants import (
    ALERT_DROUGHT,
    ALERT_EXCESS,
    DROUGHT_BONUS,
    DROUGHT_PENALTY,
    EXCESS_PENALTY,
    FROST_FULL_MARGIN_C,
    LABEL_LOW,
    LABEL_VERY,
    LABEL_VIABLE,
    MISMATCH_FACTOR,
    WEIGHT_DRAINAGE,
    WEIGHT_FROST_SENSITIVE,
    WEIGHT_FROST_TOLERANT,
    WEIGHT_PH,
    WEIGHT_PRECIP,
    WEIGHT_TEMPERATURE,
    WEIGHT_TEXTURE,
)
from app.schemas import Alerta, Crop, MesClima, Recomendacion, SueloIn


@dataclass
class Factor:
    """Un factor ya evaluado entre 0 y 1."""

    nombre: str
    valor: float
    peso: float
    critico: bool


def trapezoid(
    value: float,
    abs_min: float,
    opt_min: float,
    opt_max: float,
    abs_max: float,
) -> float:
    """Aptitud trapezoidal. Vale 0 fuera de los absolutos y 1 en el óptimo.

    Si el tramo de subida o de bajada tiene longitud 0, devuelve 0 en ese
    tramo en lugar de dividir entre cero.

    Args:
        value: Valor observado.
        abs_min: Por debajo de aquí la aptitud es 0.
        opt_min: Inicio del óptimo.
        opt_max: Fin del óptimo.
        abs_max: Por encima de aquí la aptitud es 0.

    Returns:
        Aptitud entre 0 y 1.
    """
    if value <= abs_min or value >= abs_max:
        return 0.0
    if opt_min <= value <= opt_max:
        return 1.0
    if value < opt_min:
        span = opt_min - abs_min
        if span <= 0:
            return 0.0
        return (value - abs_min) / span
    span = abs_max - opt_max
    if span <= 0:
        return 0.0
    return (abs_max - value) / span


def cycle_length_days(ciclo_dias: list[int]) -> int:
    """Punto medio del rango de duración, redondeado al entero más cercano.

    Args:
        ciclo_dias: Mínimo y máximo de días (GMIN, GMAX).

    Returns:
        Días usados para contar los meses de la ventana.
    """
    return int((ciclo_dias[0] + ciclo_dias[1]) / 2 + 0.5)


def cycle_month_count(ciclo_dias: list[int]) -> int:
    """Cuántos meses cubre el ciclo. Siempre entre 1 y 12.

    Args:
        ciclo_dias: Rango de días del cultivo.

    Returns:
        Número de meses de la ventana, incluido el mes de siembra.
    """
    months = int(cycle_length_days(ciclo_dias) / 30 + 0.5)
    return min(12, max(1, months))


def months_in_window(start_month: int, count: int) -> list[int]:
    """Meses de la ventana, con vuelta de año.

    Args:
        start_month: Mes de siembra, 1 a 12.
        count: Largo de la ventana en meses.

    Returns:
        Meses en orden, por ejemplo octubre y cuatro meses: 10, 11, 12, 1.
    """
    return [((start_month - 1 + offset) % 12) + 1 for offset in range(count)]


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def window_climate(
    months: list[MesClima],
    window: list[int],
) -> tuple[float | None, float | None, float | None]:
    """Temperatura media, mínima más baja y lluvia acumulada de la ventana.

    Args:
        months: Doce meses de climatología.
        window: Meses incluidos, de 1 a 12.

    Returns:
        Temperatura media, mínima de la ventana y milímetros de lluvia.
    """
    by_month = {month.mes: month for month in months}
    temps = [by_month[mes].t2m for mes in window if by_month[mes].t2m is not None]
    mins = [by_month[mes].t2m_min for mes in window if by_month[mes].t2m_min is not None]
    rains = [by_month[mes].precip_mm for mes in window if by_month[mes].precip_mm is not None]
    return _mean(temps), (min(mins) if mins else None), (sum(rains) if rains else None)


def frost_factor(t_min: float, killing: float) -> float:
    """Penaliza la mínima de la ventana respecto de la temperatura letal.

    Args:
        t_min: Mínima climatológica más baja de la ventana, en °C.
        killing: KTMP de EcoCrop.

    Returns:
        0 si la mínima está en o bajo la temperatura letal, 1 si la supera
        por al menos 5 °C, y un valor lineal en medio.
    """
    if t_min <= killing:
        return 0.0
    if t_min >= killing + FROST_FULL_MARGIN_C:
        return 1.0
    return (t_min - killing) / FROST_FULL_MARGIN_C


def etiqueta(puntaje: int) -> str:
    """Nombre del puntaje para la interfaz.

    Args:
        puntaje: Entero de 0 a 100.

    Returns:
        Una de las cuatro etiquetas del proyecto.
    """
    if puntaje >= LABEL_VERY:
        return "Muy viable"
    if puntaje >= LABEL_VIABLE:
        return "Viable con cuidados"
    if puntaje >= LABEL_LOW:
        return "Poco viable"
    return "No recomendado"


def geometric_score(factors: list[Factor]) -> float:
    """Media geométrica ponderada, en escala 0 a 1.

    Un factor crítico en 0 anula el puntaje. Un factor no crítico en 0 no
    entra al producto: no esconde a los demás, y queda registrado como límite.

    Args:
        factors: Factores de un cultivo en un mes.

    Returns:
        Aptitud entre 0 y 1.
    """
    if not factors:
        return 0.0
    if any(factor.critico and factor.valor <= 0 for factor in factors):
        return 0.0
    used = [factor for factor in factors if factor.valor > 0]
    if not used:
        return 0.0
    weight = sum(factor.peso for factor in used)
    log_sum = sum(factor.peso * math.log(factor.valor) for factor in used)
    return math.exp(log_sum / weight)


def to_points(value: float) -> int:
    """Pasa la aptitud 0-1 a un entero 0-100.

    Args:
        value: Media geométrica.

    Returns:
        Puntaje entero.
    """
    return max(0, min(100, int(round(value * 100))))


def limiting_factor(factors: list[Factor]) -> str:
    """Nombre del factor más bajo.

    Args:
        factors: Factores evaluados.

    Returns:
        Clave del factor, o sin_datos si no hubo ninguno.
    """
    if not factors:
        return "sin_datos"
    worst = min(factors, key=lambda factor: (factor.valor, factor.nombre))
    return worst.nombre


def _soil_factors(crop: Crop, suelo: SueloIn | None) -> tuple[list[Factor], list[str]]:
    factors: list[Factor] = []
    notes: list[str] = []
    if suelo is None:
        return factors, notes
    if suelo.ph is not None:
        band = crop.suelo.ph
        factors.append(
            Factor(
                "ph",
                trapezoid(suelo.ph, band.abs_min, band.opt_min, band.opt_max, band.abs_max),
                WEIGHT_PH,
                True,
            )
        )
        if suelo.ph < band.abs_min:
            notes.append(
                f"pH {suelo.ph}: por debajo del mínimo de EcoCrop para {crop.nombre} "
                f"({band.abs_min})."
            )
            if suelo.ph < 5.5:
                notes.append(
                    f"pH {suelo.ph}: muy ácido para {crop.nombre}; "
                    "un técnico puede evaluar encalado."
                )
        elif suelo.ph > band.abs_max:
            notes.append(
                f"pH {suelo.ph}: por encima del máximo de EcoCrop para {crop.nombre} "
                f"({band.abs_max})."
            )
    if suelo.textura and crop.suelo.texturas:
        matched = 1.0 if suelo.textura in crop.suelo.texturas else MISMATCH_FACTOR
        factors.append(Factor("textura", matched, WEIGHT_TEXTURE, False))
    if suelo.drenaje and crop.suelo.drenaje:
        matched = 1.0 if suelo.drenaje in crop.suelo.drenaje else MISMATCH_FACTOR
        factors.append(Factor("drenaje", matched, WEIGHT_DRAINAGE, False))
    if suelo.n == "bajo" and crop.fertilidad == "alta":
        notes.append(
            f"{crop.nombre} figura en EcoCrop con fertilidad alta "
            "y marcaste el nitrógeno como bajo."
        )
    return factors, notes


def score_month(
    crop: Crop,
    months: list[MesClima],
    start_month: int,
    suelo: SueloIn | None,
) -> dict:
    """Puntúa un cultivo en un mes de siembra, todavía sin ajuste de alerta.

    Args:
        crop: Ficha del catálogo.
        months: Climatología del punto.
        start_month: Mes de siembra, 1 a 12.
        suelo: Datos opcionales del usuario.

    Returns:
        Diccionario con puntaje, factores y cifras de la ventana.
    """
    window = months_in_window(start_month, cycle_month_count(crop.ciclo_dias))
    temperature, t_min, rain = window_climate(months, window)
    factors: list[Factor] = []
    if temperature is not None:
        band = crop.temp
        factors.append(
            Factor(
                "temperatura",
                trapezoid(temperature, band.abs_min, band.opt_min, band.opt_max, band.abs_max),
                WEIGHT_TEMPERATURE,
                True,
            )
        )
    if rain is not None:
        band = crop.precip_ciclo_mm
        factors.append(
            Factor(
                "precipitacion",
                trapezoid(rain, band.abs_min, band.opt_min, band.opt_max, band.abs_max),
                WEIGHT_PRECIP,
                True,
            )
        )
    if t_min is not None and crop.temp_min_helada is not None:
        factors.append(
            Factor(
                "helada",
                frost_factor(t_min, crop.temp_min_helada),
                WEIGHT_FROST_SENSITIVE if crop.sensible_helada else WEIGHT_FROST_TOLERANT,
                crop.sensible_helada,
            )
        )
    soil_factors, notes = _soil_factors(crop, suelo)
    factors.extend(soil_factors)
    points = to_points(geometric_score(factors))
    return {
        "puntaje": points,
        "factores": {factor.nombre: round(factor.valor, 4) for factor in factors},
        "factor_limitante": limiting_factor(factors),
        "mes_siembra": start_month,
        "lluvia_ventana_mm": None if rain is None else round(rain, 1),
        "temperatura_ventana_c": None if temperature is None else round(temperature, 1),
        "t_min": None if t_min is None else round(t_min, 1),
        "observaciones": notes,
        "ventana": window,
    }


def apply_alert_adjustment(
    puntaje: int,
    crop: Crop,
    alertas: list[Alerta],
    lluvia_ventana_mm: float | None,
) -> tuple[int, bool]:
    """Empuja un poco el puntaje si la anomalía de 30 días ya está calculada.

    Un puntaje 0 por factor crítico no se modifica: la alerta no rescata un
    cultivo fuera de sus límites absolutos. Sin tolerancia_sequia en la ficha
    no hay bonus ni castigo de sequía, porque ese dato no está en EcoCrop.

    Args:
        puntaje: Puntaje climático de 0 a 100.
        crop: Ficha, por si trae tolerancia a sequía.
        alertas: Alertas del punto.
        lluvia_ventana_mm: Lluvia de la ventana, para el castigo por exceso.

    Returns:
        Puntaje ajustado y si el ajuste se aplicó.
    """
    if puntaje <= 0:
        return 0, False
    adjusted = float(puntaje)
    applied = False
    drought_done = False
    excess_done = False
    for alert in alertas:
        if alert.ventana_dias != 30:
            continue
        if alert.tipo in ALERT_DROUGHT and not drought_done:
            if crop.tolerancia_sequia == "alta":
                adjusted += DROUGHT_BONUS
                applied = True
            elif crop.tolerancia_sequia == "baja":
                adjusted -= DROUGHT_PENALTY
                applied = True
            drought_done = True
        elif (
            alert.tipo in ALERT_EXCESS
            and not excess_done
            and lluvia_ventana_mm is not None
            and lluvia_ventana_mm > crop.precip_ciclo_mm.abs_max
        ):
            adjusted -= EXCESS_PENALTY
            applied = True
            excess_done = True
    bounded = max(0, min(100, int(round(adjusted))))
    return bounded, applied


def rank_crops(
    crops: list[Crop],
    months: list[MesClima],
    mes_siembra: int | None,
    suelo: SueloIn | None,
    alertas: list[Alerta] | None = None,
) -> list[Recomendacion]:
    """Ordena cultivos de mayor a menor puntaje.

    Si no hay mes de siembra, cada cultivo usa el mes que más puntaje le da.

    Args:
        crops: Catálogo ya filtrado.
        months: Climatología.
        mes_siembra: Mes pedido, o None para buscar el mejor.
        suelo: Suelo opcional.
        alertas: Alertas para el ajuste. None equivale a lista vacía.

    Returns:
        Recomendaciones con explicación.
    """
    from app.explain import explain

    active = alertas or []
    ranked: list[Recomendacion] = []
    for crop in crops:
        months_to_try = [mes_siembra] if mes_siembra is not None else list(range(1, 13))
        best = max(
            (score_month(crop, months, month, suelo) for month in months_to_try),
            key=lambda item: (item["puntaje"], -item["mes_siembra"]),
        )
        puntaje, adjusted = apply_alert_adjustment(
            best["puntaje"],
            crop,
            active,
            best["lluvia_ventana_mm"],
        )
        best["puntaje"] = puntaje
        best["ajuste_alerta"] = adjusted
        ranked.append(
            Recomendacion(
                cultivo=crop.nombre,
                id=crop.id,
                categoria=crop.categoria,
                puntaje=puntaje,
                etiqueta=etiqueta(puntaje),
                factor_limitante=best["factor_limitante"],
                explicacion=explain(crop, best),
                mes_siembra=best["mes_siembra"],
                ajuste_alerta=adjusted,
                validado=crop.validado,
                lluvia_ventana_mm=best["lluvia_ventana_mm"],
                temperatura_ventana_c=best["temperatura_ventana_c"],
                factores=best["factores"],
                observaciones=best["observaciones"],
            )
        )
    ranked.sort(key=lambda item: (-item.puntaje, item.cultivo))
    return ranked
