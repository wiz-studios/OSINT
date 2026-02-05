from __future__ import annotations

import pytest

from wiretapper.config import load_settings


def test_strict_keys_requires_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIRETAPPER_LOAD_DOTENV", "0")
    monkeypatch.delenv("WIGLE_API_NAME", raising=False)
    monkeypatch.delenv("WIGLE_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENCELLID_API_KEY", raising=False)
    monkeypatch.delenv("SHODAN_API_KEY", raising=False)
    monkeypatch.setenv("WIRETAPPER_STRICT_KEYS", "1")

    with pytest.raises(ValueError, match="Missing required environment variables"):
        load_settings()


def test_non_strict_allows_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIRETAPPER_LOAD_DOTENV", "0")
    monkeypatch.delenv("WIGLE_API_NAME", raising=False)
    monkeypatch.delenv("WIGLE_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENCELLID_API_KEY", raising=False)
    monkeypatch.delenv("SHODAN_API_KEY", raising=False)
    monkeypatch.setenv("WIRETAPPER_STRICT_KEYS", "0")

    settings = load_settings()
    assert settings.wigle_api_name is None
    assert settings.wigle_api_token is None
    assert settings.opencellid_api_key is None
    assert settings.shodan_api_key is None
