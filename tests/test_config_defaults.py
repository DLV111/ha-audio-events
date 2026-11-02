"""Regression tests for default config values that matter for correctness,
not just for exercising code paths."""

from __future__ import annotations

from app.config import HomeAssistantConfig, load_config


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


def test_load_config_clamps_negative_activity_timings(tmp_path) -> None:
    """Activity timing values should never accept invalid negatives: the
    silence timeout and hold time are user-facing timers and a negative value
    would invert the detector's quiet-state logic instead of producing a sane
    timeout.
    """
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
activity:
  rms_threshold: 0.04
  peak_threshold: 0.1
  hold_time: -5
  silence_timeout: -2
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.activity.hold_time == 0.0
    assert config.activity.silence_timeout == 0.0
