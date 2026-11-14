"""Modelos de entrada y salida de la API."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RangeBand(BaseModel):
    """Límites absoluto y óptimo de una variable, al estilo EcoCrop."""

    model_config = ConfigDict(extra="forbid")

    abs_min: float
    opt_min: float
    opt_max: float
    abs_max: float


class SoilProfile(BaseModel):
    """Requisitos de suelo copiados o traducidos desde EcoCrop."""

    model_config = ConfigDict(extra="forbid")

    ph: RangeBand
    texturas: list[str]
    drenaje: list[str]


class Crop(BaseModel):
    """Un cultivo del catálogo local."""

    model_config = ConfigDict(extra="forbid")

    id: str
    nombre: str
    nombre_cientifico: str
    ecoport: str
    categoria: str
    familia: str
    ciclo_dias: list[int]
    temp: RangeBand
    temp_min_helada: float | None
    sensible_helada: bool
    precip_ciclo_mm: RangeBand
    suelo: SoilProfile
    fertilidad: str | None
    fija_nitrogeno: bool
    profundidad_raiz: str | None
    tolerancia_sequia: str | None = None
    fuente: str
    validado: bool
    notas: str


class SueloIn(BaseModel):
    """Datos de suelo que el usuario puede estimar. Todos son opcionales."""

    model_config = ConfigDict(extra="forbid")

    ph: float | None = Field(default=None, ge=0, le=14)
    textura: str | None = None
    drenaje: str | None = None
    materia_organica: float | None = Field(default=None, ge=0, le=100)
    n: str | None = None
    p: str | None = None
    k: str | None = None

    @model_validator(mode="after")
    def at_least_one_value(self) -> "SueloIn":
        """Rechaza un objeto de suelo vacío.

        Returns:
            La misma instancia si hay al menos un campo informado.
        """
        filled = (
            self.ph,
            self.textura,
            self.drenaje,
            self.materia_organica,
            self.n,
            self.p,
            self.k,
        )
        if all(value is None or value == "" for value in filled):
            raise ValueError("Indica al menos un dato de suelo.")
        return self


class RecommendRequest(BaseModel):
    """Cuerpo de POST /api/recommend."""

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    mes_siembra: int | None = Field(default=None, ge=1, le=12)
    categorias: list[str] | None = None
    suelo: SueloIn | None = None


class ExploreRequest(BaseModel):
    """Cuerpo de POST /api/explore."""

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    mes_siembra: int | None = Field(default=None, ge=1, le=12)
    categoria: str
    suelo: SueloIn | None = None


class RotationRequest(BaseModel):
    """Cuerpo de POST /api/rotation. El suelo es obligatorio."""

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    mes_siembra: int | None = Field(default=None, ge=1, le=12)
    suelo: SueloIn


class Punto(BaseModel):
    """Coordenada pedida y celda de la malla con la que se consulta POWER."""

    lat: float
    lon: float
    celda_nasa: list[float]
    elevacion_m: float | None = None


class MesClima(BaseModel):
    """Climatología de un mes, ya en unidades de trabajo."""

    mes: int
    t2m: float | None
    t2m_max: float | None
    t2m_min: float | None
    precip_mm: float | None
    rh2m: float | None
    gwetroot: float | None


class ClimateResponse(BaseModel):
    """Respuesta de GET /api/climate."""

    punto: Punto
    meses: list[MesClima]
    fuente: str
    origen: str
    unidades: dict[str, str]
    periodo_climatologico: str | None = None


class Alerta(BaseModel):
    """Anomalía del periodo reciente frente a su histórico. No es un pronóstico."""

    tipo: str
    percentil: float | None
    ventana_dias: int | None
    mensaje: str


class AlertsResponse(BaseModel):
    """Respuesta de GET /api/alerts."""

    punto: Punto
    alertas: list[Alerta]
    fuente: str
    origen: str


class Recomendacion(BaseModel):
    """Un cultivo ya puntuado."""

    cultivo: str
    id: str
    categoria: str
    puntaje: int
    etiqueta: str
    factor_limitante: str
    explicacion: str
    mes_siembra: int
    ajuste_alerta: bool
    validado: bool
    lluvia_ventana_mm: float | None
    temperatura_ventana_c: float | None
    factores: dict[str, float]
    observaciones: list[str]


class RecommendResponse(BaseModel):
    """Ranking para un punto."""

    punto: Punto
    alertas: list[Alerta]
    alertas_mensaje: str | None = None
    recomendaciones: list[Recomendacion]
    fuente: str
    aviso: str
    origen_clima: str
    periodo_climatologico: str | None = None


class CropPublic(BaseModel):
    """Ficha breve para el catálogo."""

    id: str
    nombre: str
    nombre_cientifico: str
    categoria: str
    familia: str
    validado: bool
    fuente: str
    notas: str


class PasoRotacion(BaseModel):
    """Un eslabón del ciclo sugerido."""

    orden: int
    cultivo: str
    id: str
    mes_siembra: int
    puntaje: int
    familia: str
    descanso_meses: int
    motivo: str


class RotationResponse(BaseModel):
    """Ciclo sugerido y el aviso de que no reemplaza un plan de manejo."""

    punto: Punto
    pasos: list[PasoRotacion]
    observaciones: list[str]
    mensaje: str
    fuente: str
    aviso: str
