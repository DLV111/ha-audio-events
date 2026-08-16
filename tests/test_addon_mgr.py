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
async def test_get_option_success(addon_manager, mock_session) -> None:
    """Test get_option retrieves option successfully."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content_length = 100
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "options": {
                    "audio": {"source_path": "rtsp://example.com/stream"},
                    "other": {"setting": "value"},
                }
            }
        }
    )

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value = mock_cm

    result = await addon_manager.get_option("audio", "source_path")

    assert result == "rtsp://example.com/stream"


@pytest.mark.asyncio
async def test_get_option_category_exists_key_missing(addon_manager, mock_session) -> None:
    """Test get_option returns None when key is missing."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content_length = 100
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "options": {
                    "audio": {"sample_rate": 16000},
                }
            }
        }
    )

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value = mock_cm

    result = await addon_manager.get_option("audio", "source_path")

    assert result is None


@pytest.mark.asyncio
async def test_get_option_missing_category(addon_manager, mock_session) -> None:
    """Test get_option returns None when category is missing."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content_length = 100
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "options": {
                    "other": {"setting": "value"},
                }
            }
        }
    )

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value = mock_cm

    result = await addon_manager.get_option("audio", "source_path")

    assert result is None


@pytest.mark.asyncio
async def test_get_option_none_result(addon_manager, mock_session) -> None:
    """Test get_option returns None when get_addon_info fails."""
    mock_session.request.return_value.__aenter__.return_value.status = 500

    result = await addon_manager.get_option("audio", "source_path")

    assert result is None


@pytest.mark.asyncio
async def test_set_option_uses_info_endpoint(addon_manager, mock_session) -> None:
    """Regression test: set_option should use /addons/self/info endpoint
    because GET /addons/self/options returns 405 from Supervisor API."""
    # This test verifies the fix for the 405 error

    # Mock for get_addon_info -> POST /addons/self/options
    info_response = AsyncMock()
    info_response.status = 200
    info_response.content_length = 100
    info_response.json = AsyncMock(
        return_value={
            "data": {
                "options": {
                    "audio": {"source_path": "old-path"},
                }
            }
        }
    )

    post_response = AsyncMock()
    post_response.status = 200
    post_response.content_length = 100
    post_response.json = AsyncMock(return_value={"data": {}, "result": "ok"})

    mock_get_cm = MagicMock()
    mock_get_cm.__aenter__ = AsyncMock(return_value=info_response)

    mock_post_cm = MagicMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=post_response)

    # First call is GET /addons/self/info, second is POST /addons/self/options
    mock_session.request.side_effect = [mock_get_cm, mock_post_cm]

    result = await addon_manager.set_option("audio", "source_path", "new-path")

    assert result is True
    # Verify it used /addons/self/info instead of /addons/self/options for GET
    calls = [str(call) for call in mock_session.request.call_args_list]
    assert any("/info" in str(call) for call in calls), "Should use /addons/self/info endpoint"


@pytest.mark.asyncio
async def test_set_option_success(addon_manager, mock_session) -> None:
    """Test successful option setting using info endpoint."""
    # First call - GET /addons/self/info
    info_response = AsyncMock()
    info_response.status = 200
    info_response.content_length = 100
    info_response.json = AsyncMock(
        return_value={
            "data": {
                "options": {
                    "audio": {"source_path": "old-path"},
                }
            }
        }
    )

    # Second call - POST /addons/self/options
    post_response = AsyncMock()
    post_response.status = 200
    post_response.content_length = 100
    post_response.json = AsyncMock(return_value={"data": {}, "result": "ok"})

    mock_get_cm = MagicMock()
    mock_get_cm.__aenter__ = AsyncMock(return_value=info_response)

    mock_post_cm = MagicMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=post_response)

    mock_session.request.side_effect = [mock_get_cm, mock_post_cm]

    result = await addon_manager.set_option("audio", "source_path", "new-path")

    assert result is True


@pytest.mark.asyncio
async def test_set_option_info_fails(addon_manager, mock_session) -> None:
    """Test set_option when get_addon_info fails."""
    mock_session.request.return_value.__aenter__.return_value.status = 500

    result = await addon_manager.set_option("test_category", "test_key", "test_value")

    assert result is False


@pytest.mark.asyncio
async def test_set_option_post_fails(addon_manager, mock_session) -> None:
    """Test set_option when POST fails."""
    # GET succeeds
    info_response = AsyncMock()
    info_response.status = 200
    info_response.content_length = 100
    info_response.json = AsyncMock(
        return_value={
            "data": {
                "options": {
                    "audio": {"source_path": "old-path"},
                }
            }
        }
    )

    # POST fails with error status
    post_response = AsyncMock()
    post_response.status = 500
    post_response.content_length = 0
    post_response.text = AsyncMock(return_value="Internal Server Error")

    mock_get_cm = MagicMock()
    mock_get_cm.__aenter__ = AsyncMock(return_value=info_response)

    mock_post_cm = MagicMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=post_response)

    mock_session.request.side_effect = [mock_get_cm, mock_post_cm]

    result = await addon_manager.set_option("audio", "source_path", "new-path")

    assert result is False


@pytest.mark.asyncio
async def test_set_option_creates_new_category(addon_manager, mock_session) -> None:
    """Test set_option creates a new category when it doesn't exist."""
    # GET returns existing options
    info_response = AsyncMock()
    info_response.status = 200
    info_response.content_length = 100
    info_response.json = AsyncMock(
        return_value={
            "data": {
                "options": {
                    "audio": {"source_path": "old-path"},
                }
            }
        }
    )

    # POST succeeds
    post_response = AsyncMock()
    post_response.status = 200
    post_response.content_length = 100
    post_response.json = AsyncMock(return_value={"data": {}, "result": "ok"})

    mock_get_cm = MagicMock()
    mock_get_cm.__aenter__ = AsyncMock(return_value=info_response)

    mock_post_cm = MagicMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=post_response)

    mock_session.request.side_effect = [mock_get_cm, mock_post_cm]

    result = await addon_manager.set_option("new_category", "new_key", "new_value")

    assert result is True


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


@pytest.mark.asyncio
async def test_get_addon_info_with_options(addon_manager, mock_session) -> None:
    """Test get_addon_info returns options field."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content_length = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "name": "HA Audio Events",
                "version": "1.0.0",
                "options": {
                    "audio": {"source_path": "rtsp://example.com/stream"},
                    "classifier": {"threshold": 0.8},
                },
            }
        }
    )

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.request.return_value = mock_cm

    result = await addon_manager.get_addon_info()

    assert result == {
        "name": "HA Audio Events",
        "version": "1.0.0",
        "options": {
            "audio": {"source_path": "rtsp://example.com/stream"},
            "classifier": {"threshold": 0.8},
        },
    }