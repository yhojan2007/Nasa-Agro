"""Endpoints con la climatología de demostración, sin salir a la red."""

from fastapi.testclient import TestClient

from app.main import app
from app.nasa_client import NasaError

client = TestClient(app)
COCHABAMBA = {"lat": -17.39, "lon": -66.16}


def _offline(monkeypatch) -> None:
    def boom(_url, _params, client=None):
        raise NasaError("NASA POWER no respondió. Intenta de nuevo en unos minutos.")

    monkeypatch.setattr("app.nasa_client.fetch_power_json", boom)


def test_climate_uses_demo_cell_when_power_is_down(monkeypatch) -> None:
    _offline(monkeypatch)
    response = client.get("/api/climate", params=COCHABAMBA)
    assert response.status_code == 200
    body = response.json()
    assert body["origen"] == "fixture_demo"
    assert body["punto"]["celda_nasa"] == [-17.5, -66.25]
    assert body["meses"][0]["precip_mm"] > 0
    assert body["fuente"] == "NASA POWER (comunidad AG)"


def test_unknown_point_returns_503(monkeypatch) -> None:
    _offline(monkeypatch)
    response = client.get("/api/climate", params={"lat": 0, "lon": 0})
    assert response.status_code == 503
    assert "NASA POWER" in response.json()["detalle"]


def test_invalid_latitude_is_422() -> None:
    response = client.get("/api/climate", params={"lat": 95, "lon": 0})
    assert response.status_code == 422
    assert "latitud" in response.json()["detalle"]


def test_recommend_ranks_and_includes_the_warning(monkeypatch) -> None:
    _offline(monkeypatch)
    response = client.post("/api/recommend", json=COCHABAMBA)
    assert response.status_code == 200
    body = response.json()
    assert body["aviso"] == "Recomendación orientativa; consulta a un técnico local."
    assert body["recomendaciones"]
    assert body["recomendaciones"][0]["explicacion"]
    assert "va a haber" not in body["recomendaciones"][0]["explicacion"]
    assert body["alertas"][0]["tipo"] == "sin_historico"


def test_unknown_category_is_422(monkeypatch) -> None:
    _offline(monkeypatch)
    response = client.post("/api/recommend", json={**COCHABAMBA, "categorias": ["banana"]})
    assert response.status_code == 422


def test_explore_matches_recommend_for_the_same_category(monkeypatch) -> None:
    _offline(monkeypatch)
    explored = client.post("/api/explore", json={**COCHABAMBA, "categoria": "cereales"})
    recommended = client.post(
        "/api/recommend",
        json={**COCHABAMBA, "categorias": ["cereales"]},
    )
    assert explored.status_code == 200
    left = {item["id"]: item["puntaje"] for item in explored.json()["recomendaciones"]}
    right = {item["id"]: item["puntaje"] for item in recommended.json()["recomendaciones"]}
    assert left == right
    assert "maiz" in left
    assert "papa" not in left


def test_crops_filter() -> None:
    response = client.get("/api/crops", params={"categoria": "cereales"})
    ids = {item["id"] for item in response.json()}
    assert ids == {"maiz", "quinua", "arroz"}
    assert response.json()[0]["fuente"]


def test_rotation_requires_some_soil_data(monkeypatch) -> None:
    _offline(monkeypatch)
    empty = client.post("/api/rotation", json={**COCHABAMBA, "suelo": {}})
    assert empty.status_code == 422
    filled = client.post(
        "/api/rotation",
        json={**COCHABAMBA, "suelo": {"ph": 6.2, "textura": "franco", "drenaje": "bueno"}},
    )
    assert filled.status_code == 200
    body = filled.json()
    assert body["aviso"].startswith("Es una guía general")
    families = [step["familia"] for step in body["pasos"]]
    assert all(left != right for left, right in zip(families, families[1:]))
