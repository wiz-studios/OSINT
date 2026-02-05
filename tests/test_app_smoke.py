from __future__ import annotations

from wiretapper.app import create_app
from wiretapper.config import Settings


def test_app_starts_and_routes_respond() -> None:
    settings = Settings(
        wigle_api_name=None,
        wigle_api_token=None,
        opencellid_api_key=None,
        shodan_api_key=None,
        debug=False,
    )
    app = create_app(settings)
    client = app.test_client()

    assert client.get("/map-w").status_code == 200
    r = client.get("/nearby?lat=51.505&lon=-0.09")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")

    r = client.get("/searchzz?type=ssid&query=TestWiFi")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")

    r = client.get("/api/status")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")
