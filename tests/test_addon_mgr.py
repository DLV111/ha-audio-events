"""Tests for addon manager."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.addon_mgr import AddonManager


@pytest.fixture
def mock_response():
    """Create a mock aiohttp response."""
    response = AsyncMock()
    response.status = 200
    response.content_length = 100
    response.json = AsyncMock(return_value={"data": {}})
    response.text = AsyncMock(return_value="")
    return response


@pytest.fixture
def mock_session(mock_response):
    """Create a mock aiohttp session."""
    session = MagicMock()
    session.closed = False
    # request returns an async context manager
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    session.request.return_value = mock_cm
    return session


@pytest.fixture
def addon_manager(mock_session):
    """Create an AddonManager with mocked session."""
    manager = AddonManager(supervisor_token="test-token")
    manager._session = mock_session
    return manager


@pytest.mark.asyncio
async def test_addon_manager_init() -> None:
    """Test AddonManager initialization."""
    manager = AddonManager(supervisor_token="test-token")
    assert manager.supervisor_token == "test-token"
    assert manager._session is None


@pytest.mark.asyncio
async def test_get_session_creates_new() -> None:
    """Test _get_session creates a new session."""
    manager = AddonManager(supervisor_token="test-token")

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session

        session = await manager._get_session()

        assert session == mock_session
        mock_session_class.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_reuses_existing() -> None:
    """Test _get_session reuses existing session."""
    manager = AddonManager(supervisor_token="test-token")
    mock_session = AsyncMock()
    mock_session.closed = False
    manager._session = mock_session

    session = await manager._get_session()

    assert session == mock_session


@pytest.mark.asyncio
async def test_get_session_recreates_closed() -> None:
    """Test _get_session recreates closed session."""
    manager = AddonManager(supervisor_token="test-token")
    mock_session = AsyncMock()
    mock_session.closed = True
    manager._session = mock_session

    with patch("aiohttp.ClientSession") as mock_session_class:
        new_session = AsyncMock()
        mock_session_class.return_value = new_session

        session = await manager._get_session()

        assert session == new_session
        mock_session_class.assert_called_once()


@pytest.mark.asyncio
async def test_close_session() -> None:
    """Test close method closes session."""
    manager = AddonManager(supervisor_token="test-token")
    mock_session = AsyncMock()
    mock_session.closed = False
    manager._session = mock_session

    await manager.close()

    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_no_session() -> None:
    """Test close when no session exists."""
    manager = AddonManager(supervisor_token="test-token")
    manager._session = None

    # Should not raise
    await manager.close()


@pytest.mark.asyncio
async def test_make_request_success(addon_manager, mock_session) -> None:
    """Test successful API request."""
    mock_session.request.return_value.__aenter__.return_value.json = AsyncMock(
        return_value={"data": {"test": "value"}}
    )

    result = await addon_manager._make_request("GET", "/test")

    assert result == {"data": {"test": "value"}}
    mock_session.request.assert_called_once()


@pytest.mark.asyncio
async def test_make_request_error_status(addon_manager, mock_session) -> None:
    """Test API request with error status."""
    mock_session.request.return_value.__aenter__.return_value.status = 500
    mock_session.request.return_value.__aenter__.return_value.text.return_value = (
        "Internal Server Error"
    )

    result = await addon_manager._make_request("GET", "/test")

    assert result is None


@pytest.mark.asyncio
async def test_make_request_empty_response(addon_manager, mock_session) -> None:
    """Test API request with empty response."""
    mock_session.request.return_value.__aenter__.return_value.content_length = 0

    result = await addon_manager._make_request("GET", "/test")

    assert result == {}


@pytest.mark.asyncio
async def test_make_request_cancelled(addon_manager, mock_session) -> None:
    """Test API request cancellation."""
    mock_session.request.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await addon_manager._make_request("GET", "/test")


@pytest.mark.asyncio
async def test_make_request_exception(addon_manager, mock_session) -> None:
    """Test API request with exception."""
    mock_session.request.side_effect = Exception("Network error")

    result = await addon_manager._make_request("GET", "/test")

    assert result is None


@pytest.mark.asyncio
async def test_set_option_success(addon_manager, mock_session) -> None:
    """Test successful option setting."""
    # First call - GET current options
    mock_get_response = AsyncMock()
    mock_get_response.status = 200
    mock_get_response.content_length = 100
    mock_get_response.json = AsyncMock(
        return_value={"data": {"options": {"existing": {}}}}
    )

    # Second call - POST update
    mock_post_response = AsyncMock()
    mock_post_response.status = 200
    mock_post_response.content_length = 100
    mock_post_response.json = AsyncMock(return_value={"data": {}, "result": "ok"})

    mock_get_cm = MagicMock()
    mock_get_cm.__aenter__ = AsyncMock(return_value=mock_get_response)
    mock_post_cm = MagicMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=mock_post_response)

    mock_session.request.side_effect = [mock_get_cm, mock_post_cm]

    result = await addon_manager.set_option("test_category", "test_key", "test_value")

    assert result is True


@pytest.mark.asyncio
async def test_set_option_get_fails(addon_manager, mock_session) -> None:
    """Test set_option when GET fails."""
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Error")

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value = mock_cm

    result = await addon_manager.set_option("test_category", "test_key", "test_value")

    assert result is False


@pytest.mark.asyncio
async def test_restart_success(addon_manager, mock_session) -> None:
    """Test successful restart."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content_length = 100
    mock_response.json = AsyncMock(return_value={"data": {}})

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value = mock_cm

    result = await addon_manager.restart()

    assert result is True


@pytest.mark.asyncio
async def test_restart_failure(addon_manager, mock_session) -> None:
    """Test restart failure."""
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Error")

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value = mock_cm

    result = await addon_manager.restart()

    assert result is False


@pytest.mark.asyncio
async def test_get_addon_info_success(addon_manager, mock_session) -> None:
    """Test successful add-on info retrieval."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content_length = 100
    mock_response.json = AsyncMock(return_value={"data": {"version": "1.0.0"}})

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value = mock_cm

    result = await addon_manager.get_addon_info()

    assert result == {"version": "1.0.0"}


@pytest.mark.asyncio
async def test_get_addon_info_failure(addon_manager, mock_session) -> None:
    """Test add-on info retrieval failure."""
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Error")

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value = mock_cm

    result = await addon_manager.get_addon_info()

    assert result is None
