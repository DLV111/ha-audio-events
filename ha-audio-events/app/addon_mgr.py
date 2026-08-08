"""
Addon Manager for HA Audio Events add-on.
Handles communication with Supervisor API for options and restart.
"""

from __future__ import annotations

import aiohttp
import asyncio
import logging
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


class AddonManager:
    def __init__(self, supervisor_token: str) -> None:
        self.supervisor_token = supervisor_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any] | None:
        """Make a request to Supervisor API."""
        try:
            session = await self._get_session()
            url = f"http://supervisor{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.supervisor_token}",
                "Content-Type": "application/json",
            }

            async with session.request(
                method, url, headers=headers, json=data
            ) as response:
                if response.status >= 300:
                    text = await response.text()
                    _LOGGER.warning(
                        "Supervisor API error %s: %s", response.status, text
                    )
                    return None

                if response.content_length == 0 or response.content_length is None:
                    return {}

                return await response.json()

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _LOGGER.exception("Error making Supervisor API request: %s", exc)
            return None

    async def get_option(self, category: str, key: str) -> Any:
        """Get an option from add-on configuration."""
        try:
            result = await self._make_request("GET", "/addons/self/options")
            if result is None:
                return None

            options = result.get("data", {}).get("options", {})
            category_options = options.get(category, {})
            return category_options.get(key)

        except Exception as exc:
            _LOGGER.exception("Error getting add-on option: %s", exc)
            return None

    async def set_option(self, category: str, key: str, value: Any) -> bool:
        """Set an option in add-on configuration."""
        try:
            # Get current options first
            current_result = await self._make_request("GET", "/addons/self/options")
            if current_result is None:
                return False

            current_options = current_result.get("data", {}).get("options", {})
            
            # Update the specific option
            if category not in current_options:
                current_options[category] = {}
            current_options[category][key] = value

            # Prepare the update payload
            update_data = {"options": current_options}
            
            result = await self._make_request(
                "POST", "/addons/self/options", update_data
            )
            return result is not None

        except Exception as exc:
            _LOGGER.exception("Error setting add-on option: %s", exc)
            return False

    async def restart(self) -> bool:
        """Restart the add-on."""
        try:
            result = await self._make_request("POST", "/addons/self/restart")
            return result is not None
        except Exception as exc:
            _LOGGER.exception("Error restarting add-on: %s", exc)
            return False

    async def get_addon_info(self) -> Dict[str, Any] | None:
        """Get information about the current add-on."""
        try:
            result = await self._make_request("GET", "/addons/self/info")
            if result is None:
                return None
            return result.get("data")
        except Exception as exc:
            _LOGGER.exception("Error getting add-on info: %s", exc)
            return None
