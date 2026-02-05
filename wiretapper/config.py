from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    wigle_api_name: str | None
    wigle_api_token: str | None
    opencellid_api_key: str | None
    shodan_api_key: str | None
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True
    strict_keys: bool = False
    rate_limit_rpm: int = 60
    cache_ttl_nearby_s: float = 45.0
    cache_ttl_search_s: float = 60.0
    cache_ttl_towers_s: float = 120.0

    def validate(self) -> None:
        if not self.strict_keys:
            return
        missing: list[str] = []
        if not self.wigle_api_name:
            missing.append("WIGLE_API_NAME")
        if not self.wigle_api_token:
            missing.append("WIGLE_API_TOKEN")
        if not self.opencellid_api_key:
            missing.append("OPENCELLID_API_KEY")
        if not self.shodan_api_key:
            missing.append("SHODAN_API_KEY")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


def load_dotenv_if_present(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    load_dotenv(dotenv_path=env_path, override=False)


def load_settings(*, project_root: Path | None = None) -> Settings:
    if project_root is None:
        project_root = Path(__file__).resolve().parents[1]

    if _truthy(os.getenv("WIRETAPPER_LOAD_DOTENV", "1")):
        load_dotenv_if_present(project_root)

    host = os.getenv("WIRETAPPER_HOST", "0.0.0.0")
    port_str = os.getenv("WIRETAPPER_PORT", "8080")
    try:
        port = int(port_str)
    except ValueError:
        port = 8080

    def _int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None or not raw.strip():
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def _float(name: str, default: float) -> float:
        raw = os.getenv(name)
        if raw is None or not raw.strip():
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    settings = Settings(
        wigle_api_name=os.getenv("WIGLE_API_NAME") or None,
        wigle_api_token=os.getenv("WIGLE_API_TOKEN") or None,
        opencellid_api_key=os.getenv("OPENCELLID_API_KEY") or None,
        shodan_api_key=os.getenv("SHODAN_API_KEY") or None,
        host=host,
        port=port,
        debug=_truthy(os.getenv("WIRETAPPER_DEBUG", "1")),
        strict_keys=_truthy(os.getenv("WIRETAPPER_STRICT_KEYS")),
        rate_limit_rpm=_int("WIRETAPPER_RATE_LIMIT_RPM", 60),
        cache_ttl_nearby_s=_float("WIRETAPPER_CACHE_NEARBY_S", 45.0),
        cache_ttl_search_s=_float("WIRETAPPER_CACHE_SEARCH_S", 60.0),
        cache_ttl_towers_s=_float("WIRETAPPER_CACHE_TOWERS_S", 120.0),
    )
    settings.validate()
    return settings
