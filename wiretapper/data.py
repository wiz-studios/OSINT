from __future__ import annotations

from typing import Any

DUMMY_DATA: list[dict[str, Any]] = [
    {
        "lat": 51.505,
        "lon": -0.09,
        "ssid": "TestWiFi",
        "bssid": "00:14:22:01:23:45",
        "vendor": "Generic",
        "signal": -65,
        "accuracy": 50,
        "timestamp": "2025-04-11T10:00:00Z",
        "type": "router",
    },
    {
        "lat": 51.506,
        "lon": -0.088,
        "cell_id": "123456789",
        "vendor": "N/A",
        "signal": -70,
        "accuracy": 100,
        "timestamp": "2025-04-11T10:01:00Z",
        "type": "cell_tower",
    },
    {
        "lat": 51.504,
        "lon": -0.091,
        "ip": "192.168.1.100",
        "vendor": "CameraCorp",
        "type": "camera",
    },
]
