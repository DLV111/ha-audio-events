"""Regression tests for default config values that matter for correctness,
not just for exercising code paths."""

from __future__ import annotations

from app.config import HomeAssistantConfig


def test_homeassistant_default_url_uses_correct_supervisor_proxy_path() -> None:
    """The Supervisor's internal proxy to Home Assistant Core's REST API is
    reachable at http://supervisor/core/api/... (see the official Home
    Assistant developer docs: https://developers.home-assistant.io/docs/add-ons/communication/).

    An earlier version of this default used http://supervisor/homeassistant,
    which is not a valid Supervisor proxy path -- every call built on top of
    it (fire_event, update_state, and the webui's get_state) would silently
    fail. HomeAssistantClient builds URLs as f"{config.url}/api/...", so the
    base here must NOT include a trailing /api itself.
    """
    config = HomeAssistantConfig()
    assert config.url == "http://supervisor/core"
    assert not config.url.endswith("/api")
    assert "homeassistant" not in config.url.split("/")[-1]
