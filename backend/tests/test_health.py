"""Salud del servicio y CORS del origen local."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"estado": "ok"}


def test_cors_allows_vite_dev_server() -> None:
    response = TestClient(app).get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
