"""Tests for HomeAssistantClient."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from app.config import HomeAssistantConfig
from app.detection.models import EventMessage
from app.homeassistant.client import HomeAssistantClient


@pytest.fixture
def ha_config() -> HomeAssistantConfig:
    """Fixture for enabled HomeAssistantConfig."""
    return HomeAssistantConfig(
        enabled=True,
        url="http://localhost:8123",
        token="test_token",
        entity_prefix="audio",
    )


@pytest.fixture
def ha_config_disabled() -> HomeAssistantConfig:
    """Fixture for disabled HomeAssistantConfig."""
    return HomeAssistantConfig(
        enabled=False,
        url="http://localhost:8123",
        token="test_token",
        entity_prefix="audio",
    )


@pytest.fixture
def mock_event() -> EventMessage:
    """Fixture for EventMessage."""
    return EventMessage(
        event_type="audio.detected",
        label="train",
        confidence=0.95,
        duration=30.0,
        state="started",
        model="yamnet",
    )


@pytest.fixture
def mock_response_200() -> AsyncMock:
    """Fixture for a successful HTTP response mock."""
    mock = AsyncMock()
    mock.status = 200
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_response_400() -> AsyncMock:
    """Fixture for a 400 HTTP response mock."""
    mock = AsyncMock()
    mock.status = 400
    mock.text = AsyncMock(return_value="Bad Request")
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_response_500() -> AsyncMock:
    """Fixture for a 500 HTTP response mock."""
    mock = AsyncMock()
    mock.status = 500
    mock.text = AsyncMock(return_value="Internal Server Error")
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


def make_mock_session(response: AsyncMock | None = None) -> MagicMock:
    """Create a mock session whose .post() returns the given response."""
    mock_session = MagicMock()
    if response is not None:
        mock_session.post = MagicMock(return_value=response)
    mock_session.close = AsyncMock()
    return mock_session


class TestHomeAssistantClient:
    """Tests for HomeAssistantClient."""

    @pytest.mark.asyncio
    async def test_init_creates_session(self, ha_config: HomeAssistantConfig) -> None:
        """Test that __init__ creates an aiohttp session."""
        client = HomeAssistantClient(ha_config)
        assert client._session is not None
        assert isinstance(client._session, aiohttp.ClientSession)
        await client.close()

    @pytest.mark.asyncio
    async def test_close_closes_session(self, ha_config: HomeAssistantConfig) -> None:
        """Test that close closes the session."""
        client = HomeAssistantClient(ha_config)
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        client._session = mock_session

        await client.close()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_fire_event_disabled_returns_early(
        self,
        ha_config_disabled: HomeAssistantConfig,
        mock_event: EventMessage,
    ) -> None:
        """Test fire_event returns early if disabled."""
        client = HomeAssistantClient(ha_config_disabled)
        mock_session = make_mock_session()
        client._session = mock_session

        await client.fire_event(mock_event)
        mock_session.post.assert_not_called()
        await client.close()

    @pytest.mark.asyncio
    async def test_fire_event_success(
        self,
        ha_config: HomeAssistantConfig,
        mock_event: EventMessage,
        mock_response_200: AsyncMock,
    ) -> None:
        """Test fire_event sends correct request on success."""
        client = HomeAssistantClient(ha_config)
        mock_session = make_mock_session(mock_response_200)
        client._session = mock_session

        await client.fire_event(mock_event)

        mock_session.post.assert_called_once()
        call_args, kwargs = mock_session.post.call_args
        assert call_args[0] == "http://localhost:8123/api/events/audio.detected"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"
        assert kwargs["json"]["label"] == "train"
        assert kwargs["json"]["confidence"] == 0.95
        assert kwargs["json"]["duration"] == 30.0
        assert kwargs["json"]["state"] == "started"
        assert kwargs["json"]["model"] == "yamnet"
        await client.close()

    @pytest.mark.asyncio
    async def test_fire_event_http_error(
        self,
        ha_config: HomeAssistantConfig,
        mock_event: EventMessage,
        mock_response_400: AsyncMock,
    ) -> None:
        """Test fire_event logs warning on HTTP error."""
        client = HomeAssistantClient(ha_config)
        mock_session = make_mock_session(mock_response_400)
        client._session = mock_session

        with patch("app.homeassistant.client._LOGGER") as mock_logger:
            await client.fire_event(mock_event)
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "Failed to fire HA event" in call_args[0][0]
            assert "audio.detected" in call_args[0][1]
            assert "400" in str(call_args[0][2])
            assert "Bad Request" in call_args[0][3]
        await client.close()

    @pytest.mark.asyncio
    async def test_fire_event_exception(
        self,
        ha_config: HomeAssistantConfig,
        mock_event: EventMessage,
    ) -> None:
        """Test fire_event logs exception on error."""
        client = HomeAssistantClient(ha_config)
        mock_session = MagicMock()
        mock_session.post = AsyncMock(
            side_effect=aiohttp.ClientError("Connection failed")
        )
        mock_session.close = AsyncMock()
        client._session = mock_session

        with patch("app.homeassistant.client._LOGGER") as mock_logger:
            await client.fire_event(mock_event)
            mock_logger.exception.assert_called_once_with(
                "Error firing Home Assistant event"
            )
        await client.close()

    @pytest.mark.asyncio
    async def test_fire_event_cancelled_error_propagates(
        self,
        ha_config: HomeAssistantConfig,
        mock_event: EventMessage,
    ) -> None:
        """Test fire_event propagates CancelledError."""
        client = HomeAssistantClient(ha_config)

        async def _raise(*args, **kwargs):
            raise asyncio.CancelledError()

        response_mock = AsyncMock()
        response_mock.__aenter__ = AsyncMock(side_effect=_raise)
        response_mock.__aexit__ = AsyncMock(return_value=None)

        mock_session = make_mock_session(response_mock)
        client._session = mock_session

        with pytest.raises(asyncio.CancelledError):
            await client.fire_event(mock_event)
        await client.close()

    @pytest.mark.asyncio
    async def test_update_state_disabled_returns_early(
        self,
        ha_config_disabled: HomeAssistantConfig,
    ) -> None:
        """Test update_state returns early if disabled."""
        client = HomeAssistantClient(ha_config_disabled)
        mock_session = make_mock_session()
        client._session = mock_session

        await client.update_state("binary_sensor.test", "on", {"attr": "value"})
        mock_session.post.assert_not_called()
        await client.close()

    @pytest.mark.asyncio
    async def test_update_state_success(
        self,
        ha_config: HomeAssistantConfig,
        mock_response_200: AsyncMock,
    ) -> None:
        """Test update_state sends correct request on success."""
        client = HomeAssistantClient(ha_config)
        mock_session = make_mock_session(mock_response_200)
        client._session = mock_session

        await client.update_state(
            "binary_sensor.test",
            "on",
            {"attr": "value", "friendly_name": "Test"},
        )

        mock_session.post.assert_called_once()
        call_args, kwargs = mock_session.post.call_args
        assert call_args[0] == "http://localhost:8123/api/states/binary_sensor.test"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"
        assert kwargs["json"]["state"] == "on"
        assert kwargs["json"]["attributes"] == {
            "attr": "value",
            "friendly_name": "Test",
        }
        await client.close()

    @pytest.mark.asyncio
    async def test_update_state_with_none_attributes(
        self,
        ha_config: HomeAssistantConfig,
        mock_response_200: AsyncMock,
    ) -> None:
        """Test update_state handles None attributes."""
        client = HomeAssistantClient(ha_config)
        mock_session = make_mock_session(mock_response_200)
        client._session = mock_session

        await client.update_state("binary_sensor.test", "on", None)

        mock_session.post.assert_called_once()
        _args, kwargs = mock_session.post.call_args
        assert kwargs["json"]["attributes"] == {}
        await client.close()

    @pytest.mark.asyncio
    async def test_update_state_http_error(
        self,
        ha_config: HomeAssistantConfig,
        mock_response_500: AsyncMock,
    ) -> None:
        """Test update_state logs warning on HTTP error."""
        client = HomeAssistantClient(ha_config)
        mock_session = make_mock_session(mock_response_500)
        client._session = mock_session

        with patch("app.homeassistant.client._LOGGER") as mock_logger:
            await client.update_state("binary_sensor.test", "on", {})
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "Failed to update HA state" in call_args[0][0]
            assert "binary_sensor.test" in call_args[0][1]
            assert "500" in str(call_args[0][2])
            assert "Internal Server Error" in call_args[0][3]
        await client.close()

    @pytest.mark.asyncio
    async def test_update_state_exception(
        self,
        ha_config: HomeAssistantConfig,
    ) -> None:
        """Test update_state logs exception on error."""
        client = HomeAssistantClient(ha_config)
        mock_session = MagicMock()
        mock_session.post = AsyncMock(
            side_effect=aiohttp.ClientError("Connection failed")
        )
        mock_session.close = AsyncMock()
        client._session = mock_session

        with patch("app.homeassistant.client._LOGGER") as mock_logger:
            await client.update_state("binary_sensor.test", "on", {})
            mock_logger.exception.assert_called_once_with("Error updating HA state")
        await client.close()

    @pytest.mark.asyncio
    async def test_update_state_cancelled_error_propagates(
        self,
        ha_config: HomeAssistantConfig,
    ) -> None:
        """Test update_state propagates CancelledError."""
        client = HomeAssistantClient(ha_config)

        async def _raise(*args, **kwargs):
            raise asyncio.CancelledError()

        response_mock = AsyncMock()
        response_mock.__aenter__ = AsyncMock(side_effect=_raise)
        response_mock.__aexit__ = AsyncMock(return_value=None)

        mock_session = make_mock_session(response_mock)
        client._session = mock_session

        with pytest.raises(asyncio.CancelledError):
            await client.update_state("binary_sensor.test", "on", {})
        await client.close()

    @pytest.mark.asyncio
    async def test_fire_event_without_token(
        self,
        mock_event: EventMessage,
        mock_response_200: AsyncMock,
    ) -> None:
        """Test fire_event without token."""
        config = HomeAssistantConfig(
            enabled=True,
            url="http://localhost:8123",
            token="",
            entity_prefix="audio",
        )
        client = HomeAssistantClient(config)
        mock_session = make_mock_session(mock_response_200)
        client._session = mock_session

        await client.fire_event(mock_event)

        _args, kwargs = mock_session.post.call_args
        assert "Authorization" not in kwargs["headers"]
        await client.close()

    @pytest.mark.asyncio
    async def test_update_state_without_token(
        self,
        mock_response_200: AsyncMock,
    ) -> None:
        """Test update_state without token."""
        config = HomeAssistantConfig(
            enabled=True,
            url="http://localhost:8123",
            token="",
            entity_prefix="audio",
        )
        client = HomeAssistantClient(config)
        mock_session = make_mock_session(mock_response_200)
        client._session = mock_session

        await client.update_state("binary_sensor.test", "on", {})

        _args, kwargs = mock_session.post.call_args
        assert "Authorization" not in kwargs["headers"]
        await client.close()
