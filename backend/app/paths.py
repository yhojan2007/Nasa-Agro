"""Rutas de datos del backend, relativas a este paquete."""

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
DEMO_DIR = DATA_DIR / "demo"
CROPS_PATH = DATA_DIR / "crops.json"
