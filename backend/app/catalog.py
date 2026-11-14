"""Carga el catálogo de cultivos versionado en el repositorio."""

import json

from app.paths import CROPS_PATH
from app.schemas import Crop

_CACHE: list[Crop] | None = None


def load_crops() -> list[Crop]:
    """Lee crops.json una vez por proceso.

    Returns:
        Catálogo validado con Pydantic.
    """
    global _CACHE
    if _CACHE is None:
        raw = json.loads(CROPS_PATH.read_text(encoding="utf-8"))
        _CACHE = [Crop.model_validate(item) for item in raw]
    return _CACHE


def clear_crop_cache() -> None:
    """Olvida el catálogo. Útil si una prueba reescribe el archivo."""
    global _CACHE
    _CACHE = None
