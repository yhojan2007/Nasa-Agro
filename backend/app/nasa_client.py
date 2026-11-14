"""Cliente de NASA POWER con caché por celda de la malla."""

import json
import os
from datetime import date, timedelta
from pathlib import Path

import httpx

from app.constants import (
    GRID_LAT_DEG,
    GRID_LON_DEG,
    HISTORY_YEARS,
    POWER_LAG_DAYS,
)
from app.paths import DEMO_DIR

CLIMATOLOGY_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_COMMUNITY = "AG"


class NasaError(Exception):
    """POWER no respondió o la respuesta no trae las unidades esperadas."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def snap(lat: float, lon: float) -> tuple[float, float]:
    """Redondea a la malla meteorológica de POWER (0.5° × 0.625°).

    Args:
        lat: Latitud en grados.
        lon: Longitud en grados.

    Returns:
        Latitud y longitud del centro de celda usado como clave de caché.
    """
    snapped_lat = round(round(lat / GRID_LAT_DEG) * GRID_LAT_DEG, 4)
    snapped_lon = round(round(lon / GRID_LON_DEG) * GRID_LON_DEG, 4)
    return snapped_lat, snapped_lon


def nasa_timeout() -> float:
    """Lee el timeout de POWER desde el entorno.

    Returns:
        Segundos de espera. 60 si la variable no es un número.
    """
    raw = os.environ.get("NASA_TIMEOUT_SECONDS", "60")
    try:
        return float(raw)
    except ValueError:
        return 60.0


def cache_directory() -> Path:
    """Carpeta de caché. CACHE_DIR vacío usa backend/data/cache.

    Returns:
        Directorio, sin crearlo todavía.
    """
    raw = os.environ.get("CACHE_DIR", "").strip()
    if raw:
        return Path(raw)
    return DEMO_DIR.parent / "cache"


def cache_path(kind: str, cell: tuple[float, float], suffix: str = "") -> Path:
    """Ruta del archivo de caché de una celda.

    Args:
        kind: climatology o daily.
        cell: Latitud y longitud ya redondeadas.
        suffix: Fechas, solo para la serie diaria.

    Returns:
        Ruta del JSON de caché.
    """
    lat, lon = cell
    return cache_directory() / f"{kind}_{lat}_{lon}{suffix}.json"


def fetch_power_json(
    url: str,
    params: dict[str, str | float],
    client: httpx.Client | None = None,
) -> dict:
    """Pide un JSON a POWER. Reintenta una vez si la red o el servidor fallan.

    Args:
        url: Endpoint temporal de POWER.
        params: Parámetros de la consulta.
        client: Cliente httpx inyectable en las pruebas.

    Returns:
        Cuerpo JSON ya decodificado.

    Raises:
        NasaError: Si los dos intentos fallan.
    """
    owns_client = client is None
    http = client or httpx.Client(timeout=nasa_timeout())
    last_error: Exception | None = None
    try:
        for _ in range(2):
            try:
                response = http.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise NasaError("NASA POWER devolvió una respuesta que no es un objeto JSON.")
                return payload
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
    finally:
        if owns_client:
            http.close()
    raise NasaError(
        "NASA POWER no respondió. Intenta de nuevo en unos minutos."
    ) from last_error


def _geometry_cell(payload: dict) -> tuple[float, float] | None:
    coordinates = payload.get("geometry", {}).get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    lon, lat = coordinates[0], coordinates[1]
    return snap(float(lat), float(lon))


def load_demo(kind: str, cell: tuple[float, float]) -> dict | None:
    """Busca una respuesta guardada cuya coordenada cae en la misma celda.

    Args:
        kind: climatology o daily.
        cell: Celda pedida.

    Returns:
        El JSON de demostración, o None si esta celda no tiene respaldo.
    """
    pattern = "power_climatology_*.json" if kind == "climatology" else "power_daily_*.json"
    for path in sorted(DEMO_DIR.glob(pattern)):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if _geometry_cell(payload) == cell:
            return payload
    return None


def _store(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def get_climatology(
    lat: float,
    lon: float,
    client: httpx.Client | None = None,
) -> tuple[dict, str, tuple[float, float]]:
    """Climatología mensual de la celda, con caché y respaldo de demostración.

    Args:
        lat: Latitud pedida por el usuario.
        lon: Longitud pedida por el usuario.
        client: Cliente httpx opcional.

    Returns:
        Payload crudo, origen (nasa_power o fixture_demo) y celda.

    Raises:
        NasaError: Si POWER falla y no hay un fixture de esa celda.
    """
    cell = snap(lat, lon)
    path = cache_path("climatology", cell)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")), "nasa_power", cell
    params: dict[str, str | float] = {
        "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,GWETROOT",
        "community": POWER_COMMUNITY,
        "longitude": cell[1],
        "latitude": cell[0],
        "format": "JSON",
    }
    try:
        payload = fetch_power_json(CLIMATOLOGY_URL, params, client)
    except NasaError:
        demo = load_demo("climatology", cell)
        if demo is None:
            raise
        return demo, "fixture_demo", cell
    _store(path, payload)
    return payload, "nasa_power", cell


def daily_window(today: date | None = None) -> tuple[date, date]:
    """Ventana de unos 20 años que termina una semana antes de hoy.

    POWER publica con retraso. Pedir "hoy" suele devolver días vacíos.

    Args:
        today: Fecha de referencia, inyectable en pruebas.

    Returns:
        Fecha inicial y fecha final inclusive.
    """
    current = today or date.today()
    end = current - timedelta(days=POWER_LAG_DAYS)
    try:
        start = end.replace(year=end.year - HISTORY_YEARS)
    except ValueError:
        start = end.replace(year=end.year - HISTORY_YEARS, day=28)
    return start, end


def get_daily(
    lat: float,
    lon: float,
    client: httpx.Client | None = None,
    today: date | None = None,
) -> tuple[dict, str, tuple[float, float]]:
    """Serie diaria de lluvia, mínima y humedad de suelo para las alertas.

    Args:
        lat: Latitud pedida.
        lon: Longitud pedida.
        client: Cliente httpx opcional.
        today: Fecha de referencia para cerrar la ventana.

    Returns:
        Payload crudo, origen y celda.

    Raises:
        NasaError: Si POWER falla y no hay fixture diario de esa celda.
    """
    cell = snap(lat, lon)
    start, end = daily_window(today)
    suffix = f"_{start:%Y%m%d}_{end:%Y%m%d}"
    path = cache_path("daily", cell, suffix)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")), "nasa_power", cell
    params: dict[str, str | float] = {
        "parameters": "PRECTOTCORR,T2M_MIN,GWETROOT",
        "community": POWER_COMMUNITY,
        "longitude": cell[1],
        "latitude": cell[0],
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    try:
        payload = fetch_power_json(DAILY_URL, params, client)
    except NasaError:
        demo = load_demo("daily", cell)
        if demo is None:
            raise
        return demo, "fixture_demo", cell
    _store(path, payload)
    return payload, "nasa_power", cell
