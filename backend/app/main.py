"""Rutas de AgroNASA. El cálculo vive en los módulos de clima, puntaje y alertas."""

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from app.alerts import build_alerts
from app.catalog import load_crops
from app.climate import load_climate, parse_daily
from app.constants import AVISO, CATEGORIAS, FUENTE_CLIMA
from app.nasa_client import NasaError, get_daily
from app.rotation import RotationCandidate, aviso_rotacion, plan_rotation
from app.schemas import (
    AlertsResponse,
    ClimateResponse,
    CropPublic,
    ExploreRequest,
    Punto,
    RecommendRequest,
    RecommendResponse,
    RotationRequest,
    RotationResponse,
)
from app.scoring import cycle_month_count, rank_crops, score_month

app = FastAPI(title="AgroNASA", version="0.1.0")

_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: object, _exc: RequestValidationError) -> JSONResponse:
    """Traduce un body inválido a un mensaje corto en español."""
    return JSONResponse(
        status_code=422,
        content={
            "detalle": (
                "Revisa latitud (-90 a 90), longitud (-180 a 180), "
                "mes de siembra (1 a 12) y los datos de suelo."
            )
        },
    )


@app.exception_handler(NasaError)
async def nasa_handler(_request: object, exc: NasaError) -> JSONResponse:
    """POWER no está disponible y esta celda no tiene fixture de respaldo."""
    return JSONResponse(status_code=503, content={"detalle": exc.message})


def _check_category(name: str) -> None:
    if name not in CATEGORIAS:
        raise HTTPException(status_code=422, detail=f"Categoría no reconocida: {name}")


def _filter_crops(categorias: list[str] | None) -> list:
    if not categorias:
        return load_crops()
    for name in categorias:
        _check_category(name)
    allowed = set(categorias)
    return [crop for crop in load_crops() if crop.categoria in allowed]


def _alerts_for(lat: float, lon: float) -> tuple[list, str | None, str]:
    """Alertas del punto. Si POWER falla, el ranking sigue sin ajuste.

    Returns:
        Alertas, mensaje de error y origen de la serie.
    """
    try:
        payload, origen, _cell = get_daily(lat, lon)
    except NasaError as exc:
        return [], exc.message, "no_disponible"
    return build_alerts(parse_daily(payload)), None, origen


@app.get("/health")
def health() -> dict[str, str]:
    """Estado del proceso. No consulta a NASA.

    Returns:
        Un objeto con estado ok.
    """
    return {"estado": "ok"}


@app.get("/api/climate", response_model=ClimateResponse)
def climate(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
) -> ClimateResponse:
    """Climatología mensual del punto, con lluvia ya en milímetros."""
    return load_climate(lat, lon)


@app.get("/api/alerts", response_model=AlertsResponse)
def alerts(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
) -> AlertsResponse:
    """Anomalía del periodo reciente frente al histórico del mismo punto."""
    payload, origen, cell = get_daily(lat, lon)
    coordinates = payload.get("geometry", {}).get("coordinates", [])
    elevation = float(coordinates[2]) if len(coordinates) > 2 else None
    return AlertsResponse(
        punto=Punto(
            lat=lat,
            lon=lon,
            celda_nasa=[cell[0], cell[1]],
            elevacion_m=elevation,
        ),
        alertas=build_alerts(parse_daily(payload)),
        fuente=FUENTE_CLIMA,
        origen=origen,
    )


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(body: RecommendRequest) -> RecommendResponse:
    """Ranking de cultivos para el punto."""
    weather = load_climate(body.lat, body.lon)
    alertas, alertas_mensaje, _origen = _alerts_for(body.lat, body.lon)
    recomendaciones = rank_crops(
        _filter_crops(body.categorias),
        weather.meses,
        body.mes_siembra,
        body.suelo,
        alertas,
    )
    return RecommendResponse(
        punto=weather.punto,
        alertas=alertas,
        alertas_mensaje=alertas_mensaje,
        recomendaciones=recomendaciones,
        fuente=FUENTE_CLIMA,
        aviso=AVISO,
        origen_clima=weather.origen,
        periodo_climatologico=weather.periodo_climatologico,
    )


@app.get("/api/crops", response_model=list[CropPublic])
def crops(categoria: str | None = None) -> list[CropPublic]:
    """Catálogo. Si viene categoría, tiene que ser una de la lista cerrada."""
    selected = _filter_crops([categoria] if categoria else None)
    return [
        CropPublic(
            id=crop.id,
            nombre=crop.nombre,
            nombre_cientifico=crop.nombre_cientifico,
            categoria=crop.categoria,
            familia=crop.familia,
            validado=crop.validado,
            fuente=crop.fuente,
            notas=crop.notas,
        )
        for crop in selected
    ]


@app.post("/api/explore", response_model=RecommendResponse)
def explore(body: ExploreRequest) -> RecommendResponse:
    """El mismo motor de /api/recommend, limitado a una categoría."""
    weather = load_climate(body.lat, body.lon)
    alertas, alertas_mensaje, _origen = _alerts_for(body.lat, body.lon)
    recomendaciones = rank_crops(
        _filter_crops([body.categoria]),
        weather.meses,
        body.mes_siembra,
        body.suelo,
        alertas,
    )
    return RecommendResponse(
        punto=weather.punto,
        alertas=alertas,
        alertas_mensaje=alertas_mensaje,
        recomendaciones=recomendaciones,
        fuente=FUENTE_CLIMA,
        aviso=AVISO,
        origen_clima=weather.origen,
        periodo_climatologico=weather.periodo_climatologico,
    )


@app.post("/api/rotation", response_model=RotationResponse)
def rotation(body: RotationRequest) -> RotationResponse:
    """Hasta tres cultivos encadenados. Exige al menos un dato de suelo."""
    weather = load_climate(body.lat, body.lon)
    options: dict[int, list[RotationCandidate]] = {month: [] for month in range(1, 13)}
    for crop in load_crops():
        length = cycle_month_count(crop.ciclo_dias)
        for month in range(1, 13):
            scored = score_month(crop, weather.meses, month, body.suelo)
            options[month].append(
                RotationCandidate(
                    id=crop.id,
                    nombre=crop.nombre,
                    familia=crop.familia,
                    puntaje=scored["puntaje"],
                    mes=month,
                    ciclo_meses=length,
                    fertilidad=crop.fertilidad,
                    fija_nitrogeno=crop.fija_nitrogeno,
                    profundidad_raiz=crop.profundidad_raiz,
                )
            )
    steps, notes, message = plan_rotation(options, body.mes_siembra, body.suelo.materia_organica)
    return RotationResponse(
        punto=weather.punto,
        pasos=steps,
        observaciones=notes,
        mensaje=message,
        fuente=FUENTE_CLIMA,
        aviso=aviso_rotacion(),
    )


handler = Mangum(app)
