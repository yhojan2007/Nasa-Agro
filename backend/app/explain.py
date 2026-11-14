"""Frases en español a partir de números que el motor ya calculó."""

from app.constants import MONTH_NAMES
from app.schemas import Crop

FACTOR_NAMES = {
    "temperatura": "la temperatura",
    "precipitacion": "la lluvia",
    "helada": "el riesgo de helada",
    "ph": "el pH",
    "textura": "la textura del suelo",
    "drenaje": "el drenaje",
    "sin_datos": "la falta de datos",
}


def _temp_sentence(crop: Crop, temperature: float | None) -> str:
    if temperature is None:
        return "No hay temperatura utilizable en esta ventana."
    band = crop.temp
    if band.opt_min <= temperature <= band.opt_max:
        place = "está en el rango óptimo"
    elif temperature < band.opt_min:
        place = f"queda por debajo del óptimo (desde {band.opt_min:.0f} °C)"
    else:
        place = f"queda por encima del óptimo (hasta {band.opt_max:.0f} °C)"
    return (
        f"La temperatura de la ventana ({temperature:.1f} °C de promedio) {place} "
        f"para {crop.nombre}."
    )


def _rain_sentence(crop: Crop, rain: float | None) -> str:
    if rain is None:
        return "No hay lluvia utilizable en esta ventana."
    band = crop.precip_ciclo_mm
    if band.opt_min <= rain <= band.opt_max:
        place = "cae dentro de lo óptimo"
    elif rain < band.opt_min:
        place = f"está por debajo de los {band.opt_min:.0f} mm que EcoCrop marca como óptimo mínimo"
    else:
        place = f"supera los {band.opt_max:.0f} mm del óptimo máximo de EcoCrop"
    return f"En la ventana se acumulan unos {rain:.0f} mm y esa lluvia {place}."


def explain(crop: Crop, scored: dict) -> str:
    """Arma la explicación de una recomendación.

    Args:
        crop: Ficha de origen de los rangos citados.
        scored: Resultado de score_month más el ajuste de alerta.

    Returns:
        Texto corto. No anuncia el clima futuro.
    """
    month_name = MONTH_NAMES[scored["mes_siembra"]]
    parts = [
        f"Puntaje {scored['puntaje']}.",
        f"Mejor encaja sembrando en {month_name}.",
        _temp_sentence(crop, scored["temperatura_ventana_c"]),
        _rain_sentence(crop, scored["lluvia_ventana_mm"]),
    ]
    limit = scored["factor_limitante"]
    if limit in FACTOR_NAMES and scored["factores"].get(limit, 1) < 1:
        parts.append(f"Lo que más lo limita es {FACTOR_NAMES[limit]}.")
    if scored.get("ajuste_alerta"):
        parts.append(
            "Se aplicó un ajuste pequeño por la anomalía de lluvia de los últimos 30 días."
        )
    if not crop.validado:
        parts.append("Parte de los requisitos está marcada como ejemplo, no como ficha validada.")
    return " ".join(parts)
