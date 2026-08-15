"""
Tests for the Web UI server implementation in HA Audio Events add-on.
Tests the camera discovery and source configuration endpoints.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

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

        # Verify the calls were made
        self.mock_addon_manager.set_option.assert_called_once_with(
            "audio", "source_path", "camera.front_door"
        )
        self.mock_addon_manager.restart.assert_called_once()

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
        """Test setting source succeeds but restart fails."""
        self.mock_addon_manager.set_option = AsyncMock(return_value=True)
        self.mock_addon_manager.restart = AsyncMock(return_value=False)

        resp = await self.client.request(
            "POST",
            "/api/source",
            json={"source": "camera.front_door"},
        )
        assert resp.status == 500
        data = await resp.json()
        assert "failed to restart" in data["error"]

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
        assert "assist_satellite" in data["error"] or "satellite" in data["error"].lower()
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
