"""Traduce respuestas de POWER a clima mensual y serie diaria."""

from datetime import date, datetime

import httpx

from app.constants import DAYS_IN_MONTH, FUENTE_CLIMA, MISSING_THRESHOLD, MONTH_KEYS
from app.nasa_client import NasaError, get_climatology
from app.schemas import ClimateResponse, MesClima, Punto


def is_missing(value: object) -> bool:
    """POWER usa -999 como hueco. También se descarta un valor ilegible.

    Args:
        value: Número o texto de la respuesta.

    Returns:
        True si no debe entrar en un promedio ni en una suma.
    """
    if value is None:
        return True
    try:
        return float(value) <= MISSING_THRESHOLD
    except (TypeError, ValueError):
        return True


def clean_number(value: object) -> float | None:
    """Convierte un valor de POWER a float, o None si falta.

    Args:
        value: Campo numérico del JSON.

    Returns:
        El float, o None.
    """
    if is_missing(value):
        return None
    return float(value)


def monthly_precip_mm(value: float, days: int, units: str) -> float:
    """Pasa la precipitación de POWER a milímetros del mes.

    Args:
        value: Valor ya filtrado, sin -999.
        days: Días del mes climatológico.
        units: Unidad declarada en el encabezado de POWER.

    Returns:
        Milímetros acumulados del mes.

    Raises:
        NasaError: Si la unidad no es mm/día ni mm/mes.
    """
    normalized = units.lower().replace(" ", "")
    if normalized in {"mm/day", "mm/d", "mmday-1"}:
        return value * days
    if normalized in {"mm/month", "mm/mon", "mm"}:
        return value
    raise NasaError(
        f"La unidad de precipitación de POWER no se reconoce ({units}). "
        "No se convirtió el dato."
    )


def _units(payload: dict) -> dict[str, str]:
    parameters = payload.get("parameters")
    if not isinstance(parameters, dict):
        raise NasaError("La respuesta de NASA no trae el bloque de unidades.")
    found: dict[str, str] = {}
    for name, meta in parameters.items():
        if isinstance(meta, dict) and "units" in meta:
            found[str(name)] = str(meta["units"])
    return found


def _parameter_table(payload: dict, name: str) -> dict:
    table = payload.get("properties", {}).get("parameter", {}).get(name)
    if not isinstance(table, dict):
        raise NasaError(f"La respuesta de NASA no trae el parámetro {name}.")
    return table


def parse_climatology(
    payload: dict,
    origen: str,
    cell: tuple[float, float],
    requested_lat: float,
    requested_lon: float,
) -> ClimateResponse:
    """Arma la climatología mensual lista para el motor y el gráfico.

    El valor ANN de POWER no se usa: en mínima y máxima es un extremo de los
    meses, no el promedio del año.

    Args:
        payload: JSON crudo de POWER.
        origen: nasa_power o fixture_demo.
        cell: Celda de caché.
        requested_lat: Latitud que eligió el usuario.
        requested_lon: Longitud que eligió el usuario.

    Returns:
        Clima mensual con lluvia ya en mm.
    """
    units = _units(payload)
    precip_units = units.get("PRECTOTCORR")
    if not precip_units:
        raise NasaError("La respuesta de NASA no trae las unidades de la precipitación.")
    tables = {
        name: _parameter_table(payload, name)
        for name in ("T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "GWETROOT")
    }
    months: list[MesClima] = []
    for index, key in enumerate(MONTH_KEYS):
        daily = clean_number(tables["PRECTOTCORR"].get(key))
        precip = None
        if daily is not None:
            precip = monthly_precip_mm(daily, DAYS_IN_MONTH[index], precip_units)
        months.append(
            MesClima(
                mes=index + 1,
                t2m=clean_number(tables["T2M"].get(key)),
                t2m_max=clean_number(tables["T2M_MAX"].get(key)),
                t2m_min=clean_number(tables["T2M_MIN"].get(key)),
                precip_mm=precip,
                rh2m=clean_number(tables["RH2M"].get(key)),
                gwetroot=clean_number(tables["GWETROOT"].get(key)),
            )
        )
    coordinates = payload.get("geometry", {}).get("coordinates", [])
    elevation = float(coordinates[2]) if len(coordinates) > 2 else None
    header = payload.get("header", {})
    period = header.get("range") if isinstance(header, dict) else None
    return ClimateResponse(
        punto=Punto(
            lat=requested_lat,
            lon=requested_lon,
            celda_nasa=[cell[0], cell[1]],
            elevacion_m=elevation,
        ),
        meses=months,
        fuente=FUENTE_CLIMA,
        origen=origen,
        unidades=units,
        periodo_climatologico=str(period) if period else None,
    )


def load_climate(
    lat: float,
    lon: float,
    client: httpx.Client | None = None,
) -> ClimateResponse:
    """Consulta la climatología y la normaliza.

    Args:
        lat: Latitud.
        lon: Longitud.
        client: Cliente httpx opcional.

    Returns:
        Climatología lista para la API.
    """
    payload, origen, cell = get_climatology(lat, lon, client)
    return parse_climatology(payload, origen, cell, lat, lon)


class DailyObs:
    """Un día de la serie de alertas."""

    def __init__(
        self,
        day: date,
        precip: float | None,
        tmin: float | None,
        gwetroot: float | None,
    ) -> None:
        self.day = day
        self.precip = precip
        self.tmin = tmin
        self.gwetroot = gwetroot


def parse_daily(payload: dict) -> list[DailyObs]:
    """Lee la serie diaria. La lluvia tiene que venir en mm/día.

    Args:
        payload: JSON del endpoint daily/point.

    Returns:
        Observaciones ordenadas por fecha, con huecos en None.

    Raises:
        NasaError: Si falta la unidad o no es mm/día.
    """
    units = _units(payload)
    precip_units = units.get("PRECTOTCORR", "")
    normalized = precip_units.lower().replace(" ", "")
    if normalized not in {"mm/day", "mm/d", "mmday-1"}:
        raise NasaError(
            "La serie diaria de lluvia no está en mm/día "
            f"({precip_units or 'sin unidad'}). No se sumó."
        )
    precip = _parameter_table(payload, "PRECTOTCORR")
    tmin = _parameter_table(payload, "T2M_MIN")
    gwet = _parameter_table(payload, "GWETROOT")
    keys = sorted(set(precip) | set(tmin) | set(gwet))
    rows: list[DailyObs] = []
    for key in keys:
        if not (isinstance(key, str) and len(key) == 8 and key.isdigit()):
            continue
        rows.append(
            DailyObs(
                day=datetime.strptime(key, "%Y%m%d").date(),
                precip=clean_number(precip.get(key)),
                tmin=clean_number(tmin.get(key)),
                gwetroot=clean_number(gwet.get(key)),
            )
        )
    rows.sort(key=lambda row: row.day)
    return rows
