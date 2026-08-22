"""
Tests for the Web UI server implementation in HA Audio Events add-on.
Tests the camera discovery and source configuration endpoints.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock, patch

from aiohttp.test_utils import AioHTTPTestCase
from app.addon_mgr import AddonManager
from app.homeassistant.client import HomeAssistantClient
from app.webui.server import WebUI


class TestWebUI(AioHTTPTestCase):
    """Test suite for WebUI server endpoints."""

    async def get_application(self):
        """Create the aiohttp application for testing."""
        # Mock dependencies
        self.mock_hass_client = Mock(spec=HomeAssistantClient)
        self.mock_addon_manager = Mock(spec=AddonManager)

        # Create WebUI instance
        self.webui = WebUI(self.mock_hass_client, self.mock_addon_manager)
        return self.webui.app

    async def test_serve_index(self):
        """Test that the index page is served correctly."""
        resp = await self.client.request("GET", "/")
        assert resp.status == 200
        text = await resp.text()
        assert "<!DOCTYPE html>" in text
        assert "HA Audio Events" in text

    async def test_get_cameras_success(self):
        """Test successful camera discovery from Home Assistant."""
        # Mock HA client response
        mock_cameras = [
            {
                "entity_id": "camera.front_door",
                "state": "idle",
                "attributes": {"friendly_name": "Front Door Camera"},
            },
            {
                "entity_id": "camera.backyard",
                "state": "streaming",
                "attributes": {"friendly_name": "Backyard Camera"},
            },
        ]
        self.mock_hass_client.get_state = AsyncMock(return_value=mock_cameras)

        resp = await self.client.request("GET", "/api/cameras")
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 2
        assert data[0]["entity_id"] == "camera.front_door"
        assert data[0]["friendly_name"] == "Front Door Camera"
        assert data[1]["entity_id"] == "camera.backyard"
        assert data[1]["friendly_name"] == "Backyard Camera"

    async def test_get_cameras_no_cameras(self):
        """Test camera discovery when no cameras are available."""
        self.mock_hass_client.get_state = AsyncMock(return_value=[])

        resp = await self.client.request("GET", "/api/cameras")
        assert resp.status == 200
        data = await resp.json()
        assert data == []

    async def test_get_cameras_error(self):
        """Test camera discovery when HA API returns an error."""
        self.mock_hass_client.get_state = AsyncMock(return_value=None)

        resp = await self.client.request("GET", "/api/cameras")
        assert resp.status == 500
        data = await resp.json()
        assert "error" in data

    async def test_get_source_success(self):
        """Test successful retrieval of audio source."""
        self.mock_addon_manager.get_option = AsyncMock(return_value="camera.front_door")

        resp = await self.client.request("GET", "/api/source")
        assert resp.status == 200
        data = await resp.json()
        assert data == {"source": "camera.front_door"}

    async def test_get_source_not_set(self):
        """Test retrieval when audio source is not set."""
        self.mock_addon_manager.get_option = AsyncMock(return_value=None)

        resp = await self.client.request("GET", "/api/source")
        assert resp.status == 200
        data = await resp.json()
        assert data == {"source": ""}

    async def test_set_source_success(self):
        """Test successful setting of audio source."""
        self.mock_addon_manager.set_option = AsyncMock(return_value=True)
        self.mock_addon_manager.restart = AsyncMock(return_value=True)

        resp = await self.client.request(
            "POST", "/api/source", json={"source": "camera.front_door"}
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "success"
        assert "configured" in data["message"]

        # Verify the option was set; restart happens on a delay, not inline.
        self.mock_addon_manager.set_option.assert_called_once_with(
            "audio", "source_path", "camera.front_door"
        )

    async def test_set_source_restarts_only_after_response_is_delivered(self):
        """Regression: restarting the add-on used to run inline, killing the
        container before the HTTP response reached the browser -- the panel
        then showed cryptic JSON parse errors. The response must be fully
        delivered first, with the restart following on a short delay."""
        import asyncio

        self.mock_addon_manager.set_option = AsyncMock(return_value=True)
        self.mock_addon_manager.restart = AsyncMock(return_value=True)

        with patch.object(type(self.webui), "RESTART_DELAY", 0.05):
            resp = await self.client.request(
                "POST",
                "/api/source",
                json={"source": "camera.front_door"},
            )
            assert resp.status == 200
            _ = await resp.read()

            # Response is in the browser's hands: restart must not have run yet.
            self.mock_addon_manager.restart.assert_not_called()

            await asyncio.sleep(0.2)
            self.mock_addon_manager.restart.assert_awaited_once()

    async def test_set_source_failure_never_restarts(self):
        """A failed option write must not schedule a container restart."""
        import asyncio

        self.mock_addon_manager.set_option = AsyncMock(return_value=False)
        self.mock_addon_manager.restart = AsyncMock(return_value=True)

        resp = await self.client.request(
            "POST", "/api/source", json={"source": "camera.front_door"}
        )
        assert resp.status == 500

        await asyncio.sleep(0.05)
        self.mock_addon_manager.restart.assert_not_called()

    async def test_set_source_missing_parameter(self):
        """Test setting source with missing parameter."""
        resp = await self.client.request("POST", "/api/source", json={})
        assert resp.status == 400
        data = await resp.json()
        assert "Missing source parameter" in data["error"]

    async def test_set_source_failure(self):
        """Test setting source when addon manager fails."""
        self.mock_addon_manager.set_option = AsyncMock(return_value=False)

        resp = await self.client.request(
            "POST",
            "/api/source",
            json={"source": "camera.front_door"},
        )
        assert resp.status == 500
        data = await resp.json()
        assert "Failed to set source" in data["error"]

    async def test_set_source_restart_failure(self):
        """Restart failures happen after the response is delivered, so they
        surface as a logged error -- the browser still gets success (the
        source WAS configured)."""
        import asyncio

        self.mock_addon_manager.set_option = AsyncMock(return_value=True)
        self.mock_addon_manager.restart = AsyncMock(return_value=False)

        with patch.object(type(self.webui), "RESTART_DELAY", 0.01):
            resp = await self.client.request(
                "POST",
                "/api/source",
                json={"source": "camera.front_door"},
            )
            assert resp.status == 200
            await asyncio.sleep(0.05)

        self.mock_addon_manager.restart.assert_awaited_once()

    async def test_webui_availability(self):
        """Test that Web UI is accessible."""
        resp = await self.client.request("GET", "/")
        assert resp.status == 200

    async def test_cameras_endpoint(self):
        """Test cameras endpoint works correctly."""
        # Need to mock get_state for this test
        self.mock_hass_client.get_state = AsyncMock(return_value=[])
        resp = await self.client.request("GET", "/api/cameras")
        assert resp.status == 200
        data = await resp.json()
        assert isinstance(data, list)

    async def test_get_microphones_success(self):
        """Test successful assist_satellite (voice satellite) discovery."""
        mock_satellites = [
            {
                "entity_id": "assist_satellite.shed_sensor_assist_satellite",
                "state": "idle",
                "attributes": {"friendly_name": "Shed Sensor Assist satellite"},
            },
        ]
        self.mock_hass_client.get_state = AsyncMock(return_value=mock_satellites)

        resp = await self.client.request("GET", "/api/microphones")
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 1
        assert data[0]["entity_id"] == "assist_satellite.shed_sensor_assist_satellite"
        assert data[0]["friendly_name"] == "Shed Sensor Assist satellite"
        self.mock_hass_client.get_state.assert_called_once_with("assist_satellite")

    async def test_get_microphones_failure(self):
        """Test microphone discovery when HA client fails."""
        self.mock_hass_client.get_state = AsyncMock(return_value=None)

        resp = await self.client.request("GET", "/api/microphones")
        assert resp.status == 500
        data = await resp.json()
        assert "error" in data

    async def test_set_source_rejects_assist_satellite(self):
        """assist_satellite entities aren't a supported capture source yet --
        set_source should reject them with a clear explanation rather than
        silently accepting a source_path the pipeline can't read from."""
        resp = await self.client.request(
            "POST",
            "/api/source",
            json={"source": "assist_satellite.shed_sensor_assist_satellite"},
        )
        assert resp.status == 400
        data = await resp.json()
        assert (
            "assist_satellite" in data["error"] or "satellite" in data["error"].lower()
        )
        # Should never have tried to actually set the option
        self.mock_addon_manager.set_option.assert_not_called()

    async def test_get_detections_empty_without_history(self):
        """When no history was provided to WebUI, /api/detections returns []."""
        resp = await self.client.request("GET", "/api/detections")
        assert resp.status == 200
        data = await resp.json()
        assert data == []

    async def test_get_detections_with_history(self):
        """With a history buffer, /api/detections returns recorded events,
        most recent first."""
        from app.detection.history import EventHistory

        history = EventHistory()
        history.add("dog", 0.91, "started")
        history.add("dog", 0.93, "active")
        self.webui.history = history

        resp = await self.client.request("GET", "/api/detections")
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 2
        assert data[0]["label"] == "dog"
        assert data[0]["state"] == "active"
        assert data[1]["state"] == "started"


class TestWebUIAuth(AioHTTPTestCase):
    """The optional shared token must lock every /api endpoint while keeping
    the index page reachable (so the browser can prompt for the token)."""

    TOKEN = "s3cret-token"

    async def get_application(self):
        self.mock_hass_client = Mock(spec=HomeAssistantClient)
        self.mock_addon_manager = Mock(spec=AddonManager)
        self.mock_hass_client.get_state = AsyncMock(return_value=[])
        self.webui = WebUI(
            self.mock_hass_client,
            self.mock_addon_manager,
            auth_token=self.TOKEN,
        )
        return self.webui.app

    async def test_api_rejected_without_token(self):
        resp = await self.client.request("GET", "/api/detections")
        assert resp.status == 401

    async def test_api_rejected_with_wrong_token(self):
        resp = await self.client.request(
            "GET", "/api/cameras", headers={"X-WebUI-Token": "wrong"}
        )
        assert resp.status == 401

    async def test_api_accepted_with_header_token(self):
        resp = await self.client.request(
            "GET", "/api/cameras", headers={"X-WebUI-Token": self.TOKEN}
        )
        assert resp.status == 200

    async def test_api_accepted_with_bearer_token(self):
        resp = await self.client.request(
            "GET",
            "/api/cameras",
            headers={"Authorization": f"Bearer {self.TOKEN}"},
        )
        assert resp.status == 200

    async def test_post_source_requires_token(self):
        import asyncio

        self.mock_addon_manager.set_option = AsyncMock(return_value=True)
        self.mock_addon_manager.restart = AsyncMock(return_value=True)

        resp = await self.client.request(
            "POST", "/api/source", json={"source": "camera.x"}
        )
        assert resp.status == 401
        self.mock_addon_manager.set_option.assert_not_called()

        with patch.object(type(self.webui), "RESTART_DELAY", 0.01):
            resp = await self.client.request(
                "POST",
                "/api/source",
                json={"source": "camera.x"},
                headers={"X-WebUI-Token": self.TOKEN},
            )
            assert resp.status == 200
            await asyncio.sleep(0.05)

    async def test_index_page_open_without_token(self):
        """The page itself must load so the user can be prompted for the
        token; only /api routes are gated."""
        resp = await self.client.request("GET", "/")
        assert resp.status == 200


class TestWebUINoAuthByDefault(AioHTTPTestCase):
    """Without an auth token configured (the HA-ingress default), API access
    stays open -- existing behaviour must not break."""

    async def get_application(self):
        self.mock_hass_client = Mock(spec=HomeAssistantClient)
        self.mock_hass_client.get_state = AsyncMock(return_value=[])
        self.webui = WebUI(self.mock_hass_client, Mock(spec=AddonManager), None)
        return self.webui.app

    async def test_api_open_without_token_configured(self):
        resp = await self.client.request("GET", "/api/detections")
        assert resp.status == 200


class TestWebUIHtmlSafety(AioHTTPTestCase):
    """Regression guards for the XSS fix in the detections panel."""

    async def get_application(self):
        self.webui = WebUI(Mock(spec=HomeAssistantClient), Mock(spec=AddonManager))
        return self.webui.app

    async def test_detections_rendering_does_not_interpolate_into_innerhtml(self):
        resp = await self.client.request("GET", "/")
        assert resp.status == 200
        html = await resp.text()
        # The vulnerable code built detection rows by interpolating label and
        # state straight into innerHTML. The fixed renderer must build DOM
        # nodes via textContent instead.
        assert "${d.label}" not in html
        assert "innerHTML = ``" not in html
        # No template-literal may be assigned to any innerHTML sink.
        assert ".innerHTML = `" not in html
        assert "textContent" in html

    async def test_responses_are_parsed_defensively(self):
        """Regression: the panel used to call .json() directly on every
        response; when the add-on was stopped, the ingress proxy answered
        with non-JSON error pages and users saw cryptic errors like
        'Unexpected non-whitespace character after JSON at position 3'."""
        resp = await self.client.request("GET", "/")
        html = await resp.text()
        assert "parseApiResponse" in html
        assert "application/json" in html
        # No bare .json() parsing of network responses may remain.
        assert "await response.json()" not in html
        assert "Response.json()" not in html


class TestWebUIBindNotices:
    """The open-bind warning must fire only for standalone deployments:
    behind Home Assistant ingress (SUPERVISOR_TOKEN present) it is noise."""

    def _notice(self, auth_token=None):
        from app.addon_mgr import AddonManager as _A  # noqa: F401
        from app.homeassistant.client import HomeAssistantClient as _H

        return WebUI(
            Mock(spec=_H), Mock(spec=AddonManager), auth_token=auth_token
        )._log_bind_notice

    def test_warning_when_standalone(self, caplog):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True), caplog.at_level(logging.WARNING):
            self._notice()("0.0.0.0", 8099)
        assert any("without an auth token" in r.message for r in caplog.records)

    def test_quiet_behind_ingress(self, caplog):
        import os
        from unittest.mock import patch

        with (
            patch.dict(os.environ, {"SUPERVISOR_TOKEN": "x"}, clear=True),
            caplog.at_level(logging.WARNING),
        ):
            self._notice()("0.0.0.0", 8099)
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]

    def test_quiet_with_auth_token_even_standalone(self, caplog):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True), caplog.at_level(logging.WARNING):
            self._notice(auth_token="secret")("0.0.0.0", 8099)
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]

    def test_quiet_on_loopback(self, caplog):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True), caplog.at_level(logging.WARNING):
            self._notice()("127.0.0.1", 8099)
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
