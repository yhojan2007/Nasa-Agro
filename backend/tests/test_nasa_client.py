"""Cliente POWER: malla, caché, reintento y respaldo de demostración."""

import json

import httpx
import pytest

from app.nasa_client import NasaError, fetch_power_json, get_climatology, snap
from app.paths import DEMO_DIR


def test_snap_matches_power_grid() -> None:
    assert snap(-17.39, -66.16) == (-17.5, -66.25)
    assert snap(-16.5, -68.15) == (-16.5, -68.125)
    assert snap(-17.8, -63.18) == (-18.0, -63.125)
    assert snap(-17.42, -66.2) == snap(-17.39, -66.16)


def test_fetch_retries_once_then_raises() -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(NasaError, match="no respondió"):
        fetch_power_json("https://power.example/test", {}, client)
    assert calls["n"] == 2


def test_nearby_points_share_one_request(monkeypatch) -> None:
    fixture = DEMO_DIR / "power_climatology_cochabamba.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    calls = {"n": 0}

    def fake(_url, _params, client=None):
        calls["n"] += 1
        return payload

    monkeypatch.setattr("app.nasa_client.fetch_power_json", fake)
    get_climatology(-17.39, -66.16)
    get_climatology(-17.42, -66.2)
    assert calls["n"] == 1


def test_demo_fixture_when_power_fails(monkeypatch) -> None:
    def boom(_url, _params, client=None):
        raise NasaError("NASA POWER no respondió. Intenta de nuevo en unos minutos.")

    monkeypatch.setattr("app.nasa_client.fetch_power_json", boom)
    payload, origen, cell = get_climatology(-17.39, -66.16)
    assert origen == "fixture_demo"
    assert cell == (-17.5, -66.25)
    assert "T2M" in payload["properties"]["parameter"]


def test_power_failure_without_fixture_raises(monkeypatch) -> None:
    def boom(_url, _params, client=None):
        raise NasaError("NASA POWER no respondió. Intenta de nuevo en unos minutos.")

    monkeypatch.setattr("app.nasa_client.fetch_power_json", boom)
    with pytest.raises(NasaError):
        get_climatology(0, 0)
