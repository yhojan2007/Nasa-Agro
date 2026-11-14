"""Alertas: el periodo reciente comparado con el mismo periodo de otros años."""

from datetime import date, timedelta

from app.climate import DailyObs
from app.constants import (
    FROST_ALERT_C,
    FROST_UNUSUAL_PERCENTILE,
    MIN_HISTORY_YEARS,
    MIN_WINDOW_COVERAGE,
    RAIN_DEFICIT_BELOW,
    RAIN_EXCESS_UNTIL,
    RAIN_NORMAL_UNTIL,
    RAIN_SEVERE_BELOW,
    SOIL_DRY_BELOW,
    SOIL_SATURATED_ABOVE,
)
from app.schemas import Alerta

FORBIDDEN = ("va a haber", "habrá", "va a llover", "pronóstico")


def percentile_of(value: float, sample: list[float]) -> float:
    """Dónde cae un valor dentro de una muestra histórica que no lo incluye.

    Args:
        value: Acumulado reciente.
        sample: Acumulados de los años anteriores.

    Returns:
        Percentil de 0 a 100. 0 es más seco que todo el histórico.
    """
    below = sum(1 for item in sample if item < value)
    ties = sum(1 for item in sample if item == value)
    return 100.0 * (below + 0.5 * ties) / len(sample)


def classify_rain(percentil: float) -> str:
    """Clase de lluvia según los cortes del proyecto.

    Args:
        percentil: 0 es el extremo seco y 100 el extremo húmedo.

    Returns:
        Clave de alerta. El 75 sigue siendo normal; por encima de 90 es extremo.
    """
    if percentil < RAIN_SEVERE_BELOW:
        return "sequia_severa"
    if percentil < RAIN_DEFICIT_BELOW:
        return "deficit_lluvia"
    if percentil <= RAIN_NORMAL_UNTIL:
        return "normal"
    if percentil <= RAIN_EXCESS_UNTIL:
        return "exceso_lluvia"
    return "exceso_extremo"


def _previous_end(end: date, years_back: int) -> date:
    try:
        return end.replace(year=end.year - years_back)
    except ValueError:
        return end.replace(year=end.year - years_back, day=28)


def _window_values(
    by_day: dict[date, DailyObs],
    end: date,
    days: int,
) -> tuple[float | None, int | None, float | None]:
    """Suma de lluvia, días bajo 2 °C y humedad media, si hay cobertura suficiente.

    Un hueco no se trata como cero: si falta más del 20 % de la ventana, el
    resultado es None. La suma se escala al largo completo de la ventana.
    """
    present_rain: list[float] = []
    present_tmin: list[float] = []
    present_soil: list[float] = []
    frost_days = 0
    for offset in range(days):
        observed = by_day.get(end - timedelta(days=offset))
        if observed is None:
            continue
        if observed.precip is not None:
            present_rain.append(observed.precip)
        if observed.tmin is not None:
            present_tmin.append(observed.tmin)
            if observed.tmin < FROST_ALERT_C:
                frost_days += 1
        if observed.gwetroot is not None:
            present_soil.append(observed.gwetroot)
    rain = None
    if len(present_rain) >= days * MIN_WINDOW_COVERAGE:
        rain = sum(present_rain) * days / len(present_rain)
    frost = frost_days if len(present_tmin) >= days * MIN_WINDOW_COVERAGE else None
    soil = None
    if len(present_soil) >= days * MIN_WINDOW_COVERAGE:
        soil = sum(present_soil) / len(present_soil)
    return rain, frost, soil


def rain_message(tipo: str, percentil: float, dias: int, anios: int) -> str:
    """Describe el pasado reciente. No pronostica.

    Args:
        tipo: Clase de lluvia.
        percentil: Percentil del acumulado.
        dias: 30 o 60.
        anios: Años históricos usados.

    Returns:
        Frase en español.
    """
    semanas = 4 if dias <= 30 else 8
    if tipo == "sequia_severa":
        phrase = f"están entre el 10 % más secas de los últimos {anios} años en tu zona"
    elif tipo == "deficit_lluvia":
        phrase = f"están entre el 25 % más secas de los últimos {anios} años en tu zona"
    elif tipo == "exceso_lluvia":
        phrase = f"están entre el 25 % más lluviosas de los últimos {anios} años en tu zona"
    elif tipo == "exceso_extremo":
        phrase = f"están entre el 10 % más lluviosas de los últimos {anios} años en tu zona"
    else:
        phrase = f"se parecen al histórico de los últimos {anios} años en tu zona"
    return (
        f"Las últimas {semanas} semanas {phrase} "
        f"(percentil {percentil:.0f}, ventana de {dias} días)."
    )


def soil_note(mean_gwet: float | None) -> str:
    """Refuerzo con humedad de suelo. No cambia la clase de lluvia.

    Args:
        mean_gwet: Promedio reciente de GWETROOT, de 0 a 1.

    Returns:
        Frase vacía, de suelo seco o de suelo saturado.
    """
    if mean_gwet is None:
        return ""
    if mean_gwet < SOIL_DRY_BELOW:
        return (
            f" La humedad de la zona de raíces está baja ({mean_gwet:.2f} en una escala de 0 a 1)."
        )
    if mean_gwet > SOIL_SATURATED_ABOVE:
        return (
            " La humedad de la zona de raíces está saturada "
            f"({mean_gwet:.2f} en una escala de 0 a 1)."
        )
    return ""


def frost_message(days_count: int, percentil: float | None, anios: int) -> str:
    """Describe cuántos días recientes bajaron de 2 °C.

    Args:
        days_count: Días bajo el umbral del lugar.
        percentil: Percentil de esa cuenta frente a otros años.
        anios: Años comparados.

    Returns:
        Frase sobre el periodo ya ocurrido.
    """
    base = (
        f"En los últimos 30 días la mínima bajó de {FROST_ALERT_C:.0f} °C "
        f"en {days_count} días."
    )
    if percentil is None:
        return base
    if percentil > FROST_UNUSUAL_PERCENTILE:
        return (
            f"{base} Esa cantidad está entre las más altas del mismo periodo "
            f"en los últimos {anios} años (percentil {percentil:.0f})."
        )
    return (
        f"{base} En el mismo periodo de los últimos {anios} años eso queda "
        f"en el percentil {percentil:.0f}."
    )


def build_alerts(rows: list[DailyObs], end: date | None = None) -> list[Alerta]:
    """Compara 30 y 60 días con el mismo calendario de años anteriores.

    Args:
        rows: Serie diaria ya parseada.
        end: Último día a evaluar. Por defecto, el último día con datos.

    Returns:
        Alertas de lluvia y, si corresponde, de helada del lugar.
    """
    if not rows:
        return [
            Alerta(
                tipo="sin_historico",
                percentil=None,
                ventana_dias=None,
                mensaje="No hay serie diaria para comparar este periodo con su histórico.",
            )
        ]
    by_day = {row.day: row for row in rows}
    last = end or max(by_day)
    sample_count = 0
    for years_back in range(1, 40):
        rain, _, _ = _window_values(by_day, _previous_end(last, years_back), 30)
        if rain is not None:
            sample_count += 1
    if sample_count < MIN_HISTORY_YEARS:
        return [
            Alerta(
                tipo="sin_historico",
                percentil=None,
                ventana_dias=30,
                mensaje=(
                    "No hay suficientes años en la serie para comparar este periodo "
                    f"con su histórico. Hacen falta al menos {MIN_HISTORY_YEARS} años "
                    f"y la serie permite comparar {sample_count}."
                ),
            )
        ]
    alerts: list[Alerta] = []
    for days in (30, 60):
        current_rain, _, current_soil = _window_values(by_day, last, days)
        history: list[float] = []
        for years_back in range(1, 40):
            past_rain, _, _ = _window_values(by_day, _previous_end(last, years_back), days)
            if past_rain is not None:
                history.append(past_rain)
        if current_rain is None or len(history) < MIN_HISTORY_YEARS:
            alerts.append(
                Alerta(
                    tipo="sin_historico",
                    percentil=None,
                    ventana_dias=days,
                    mensaje=(
                        f"No hay suficientes datos para la ventana de {days} días "
                        "en este punto."
                    ),
                )
            )
            continue
        percentil = percentile_of(current_rain, history)
        tipo = classify_rain(percentil)
        message = rain_message(tipo, percentil, days, len(history)) + soil_note(current_soil)
        alerts.append(
            Alerta(
                tipo=tipo,
                percentil=round(percentil, 1),
                ventana_dias=days,
                mensaje=message,
            )
        )
    _, frost_days, _ = _window_values(by_day, last, 30)
    if frost_days is not None and frost_days > 0:
        history_frost: list[float] = []
        for years_back in range(1, 40):
            _, past_frost, _ = _window_values(by_day, _previous_end(last, years_back), 30)
            if past_frost is not None:
                history_frost.append(float(past_frost))
        percentil_frost = (
            percentile_of(float(frost_days), history_frost) if history_frost else None
        )
        alerts.append(
            Alerta(
                tipo="helada",
                percentil=None if percentil_frost is None else round(percentil_frost, 1),
                ventana_dias=30,
                mensaje=frost_message(
                    frost_days,
                    percentil_frost,
                    len(history_frost),
                ),
            )
        )
    for alert in alerts:
        lowered = alert.mensaje.lower()
        for phrase in FORBIDDEN:
            if phrase in lowered:
                raise ValueError(f"La alerta no puede decir '{phrase}'.")
    return alerts
