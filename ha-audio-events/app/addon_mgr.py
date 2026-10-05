"""
Addon Manager for HA Audio Events add-on.
Handles communication with Supervisor API for options and restart.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class AddonManager:
    def __init__(self, supervisor_token: str) -> None:
        self.supervisor_token = supervisor_token
        self._session: aiohttp.ClientSession | None = None

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
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
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

                # Read the body first and only parse when non-empty: with
                # chunked responses content_length is None even though a JSON
                # body follows, so keying off content_length loses data.
                text = await response.text()
                if not text.strip():
                    return {}

                try:
                    return json.loads(text)
                except ValueError:
                    _LOGGER.warning(
                        "Supervisor API returned non-JSON body (%s...)", text[:120]
                    )
                    return None

        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Error making Supervisor API request")
            return None

    async def set_option(self, category: str, key: str, value: Any) -> bool:
        """Set an option in add-on configuration."""
        try:
            # Get current options via the info endpoint (GET /options returns 405)
            info = await self.get_addon_info()
            if info is None:
                _LOGGER.warning("Failed to retrieve add-on info")
                return False
            current_options = info.get("options", {})
            if not current_options:
                _LOGGER.warning("No current options found in add-on response: %s", info)
                return False

            # Update the specific option
            if category not in current_options:
                current_options[category] = {}
            current_options[category][key] = value

            # Prepare the update payload
            update_data = {"options": current_options}

            result = await self._make_request(
                "POST", "/addons/self/options", update_data
            )
            if result is None:
                _LOGGER.warning("Failed to update add-on options via POST request")
                return False

            # Supervisor returns {"result": "ok"} on success
            if result.get("result") != "ok":
                _LOGGER.warning(
                    "Supervisor returned non-ok result: %s", result.get("result")
                )
                return False

            return True

        except Exception:
            _LOGGER.exception("Error setting add-on option")
            return False

    async def get_option(self, category: str, key: str) -> Any | None:
        """Get an option value from add-on configuration.

        Uses the /addons/self/info endpoint because GET
        /addons/self/options returns 405 from the Supervisor API.
        """
        info = await self.get_addon_info()
        if info is None:
            return None
        options = info.get("options", {})
        category_options = options.get(category, {})
        if isinstance(category_options, dict):
            return category_options.get(key)
        return None

    async def restart(self) -> bool:
        """Restart the add-on."""
        try:
            result = await self._make_request("POST", "/addons/self/restart")
            return result is not None
        except Exception:
            _LOGGER.exception("Error restarting add-on")
            return False

    async def get_addon_info(self) -> dict[str, Any] | None:
        """Get information about the current add-on."""
        try:
            result = await self._make_request("GET", "/addons/self/info")
            if result is None:
                _LOGGER.warning("Failed to get add-on info: no result")
                return None
            # Extract the data field from the response
            return result.get("data")
        except Exception:
            _LOGGER.exception("Error getting add-on info")
            return None
