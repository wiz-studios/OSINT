# WireTapper Notes (Refactor)

## Entrypoints

- `app.py`: legacy launcher (recommended for local dev).
- `python -m wiretapper`: module launcher.

## Routes (Flask)

- `GET /map-w`: renders the Wi-Fi map UI (`templates/wifi-search.html`)
- `GET /nearby?lat=<float>&lon=<float>&mode=wifi|bluetooth`: returns `{"devices":[...]}` with correlated nearby devices
- `GET /api/geo/towers?lat=<float>&lon=<float>`: returns a JSON array of towers from OpenCellID `getInArea`
- `GET /api/geo/celltower?lat=<float>&lon=<float>`: returns a JSON array of towers from OpenCellID public GeoJSON endpoint
- `GET /searchzz?type=location|ssid|bssid|network&query=<...>`: returns `{"devices":[...]}`

## Env vars

- `WIGLE_API_NAME`, `WIGLE_API_TOKEN`: Wigle auth for Wi-Fi/Bluetooth searches
- `OPENCELLID_API_KEY`: used for UnwiredLabs (`/nearby`) and OpenCellID `getInArea` (`/api/geo/towers`)
- `SHODAN_API_KEY`: used for Shodan searches
- `WIRETAPPER_HOST` (default `0.0.0.0`), `WIRETAPPER_PORT` (default `8080`), `WIRETAPPER_DEBUG` (default `1`)
- `WIRETAPPER_STRICT_KEYS`: when `1`, missing API keys fail startup

## External calls (mock in tests)

- Wigle:
  - `https://api.wigle.net/api/v2/network/search`
  - `https://api.wigle.net/api/v2/bluetooth/search`
- OpenCellID / UnwiredLabs:
  - `https://us1.unwiredlabs.com/v2/process.php`
  - `http://opencellid.org/cell/getInArea`
  - `https://www.opencellid.org/ajax/getCells.php`
- Shodan:
  - `https://api.shodan.io/shodan/host/search`

