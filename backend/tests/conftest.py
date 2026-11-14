"""Aísla la caché de POWER en un directorio temporal."""

import pytest


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Cada prueba escribe la caché en su propio directorio."""
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
