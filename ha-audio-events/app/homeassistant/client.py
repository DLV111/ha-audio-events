from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from app.config import HomeAssistantConfig
from app.detection.models import EventMessage
from app.homeassistant.entities import build_entity_ids, build_friendly_names

_LOGGER = logging.getLogger(__name__)

# Bound every HA request so an unresponsive Home Assistant can never stall
# the detection pipeline for aiohttp's 5-minute default timeout.
DEFAULT_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class HomeAssistantClient:
    def __init__(
        self,
        config: HomeAssistantConfig,
        request_timeout: aiohttp.ClientTimeout | None = None,
    ) -> None:
        self.config = config
        self._timeout = request_timeout or DEFAULT_REQUEST_TIMEOUT
        self._session = aiohttp.ClientSession(timeout=self._timeout)
        self._entity_ids: dict[str, str] | None = None
        self._friendly_names: dict[str, str] | None = None

    async def close(self) -> None:
        await self._session.close()

    async def init_entities(self) -> None:
        """Initialize required HA entities if they don't exist yet."""
        if self._entity_ids is not None and self._friendly_names is not None:
            return

        self._entity_ids = build_entity_ids(self.config)
        self._friendly_names = build_friendly_names(self.config)

        # Ensure each entity exists - create with default state if missing
        for entity_id in self._entity_ids.values():
            await self.update_state(entity_id, "off", {})

    async def fire_event(self, event: EventMessage) -> None:
        if not self.config.enabled:
            return

        url = f"{self.config.url}/api/events/{event.event_type}"
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"

        payload = {
            "label": event.label,
            "confidence": event.confidence,
            "duration": event.duration,
            "state": event.state,
            "model": event.model,
        }

        try:
            async with self._session.post(
                url, headers=headers, json=payload
            ) as response:
                if response.status >= 300:
                    text = await response.text()
                    _LOGGER.warning(
                        "Failed to fire HA event %s (%s): %s",
                        event.event_type,
                        response.status,
                        text,
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Error firing Home Assistant event")

    async def get_state(self, domain: str | None = None) -> list[dict[str, Any]] | None:
        """Fetch entity states from Home Assistant, optionally filtered to a domain.

        Returns a list of state dicts (matching HA's GET /api/states shape),
        or None on failure. If `domain` is given (e.g. "camera"), only
        entities whose entity_id starts with "{domain}." are returned.

        Unlike fire_event/update_state, this isn't gated on config.enabled:
        callers like the webui's camera picker need to query HA even when
        event/state publishing is turned off.
        """
        url = f"{self.config.url}/api/states"
        headers: dict[str, str] = {}
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"

        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status >= 300:
                    text = await response.text()
                    _LOGGER.warning(
                        "Failed to fetch HA states (%s): %s", response.status, text
                    )
                    return None
                states: list[dict[str, Any]] = await response.json()
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Error fetching Home Assistant states")
            return None

        if domain:
            prefix = f"{domain}."
            states = [
                s for s in states if str(s.get("entity_id", "")).startswith(prefix)
            ]
        return states

    async def update_state(
        self, entity_id: str, state: str, attributes: dict[str, Any] | None = None
    ) -> None:
        if not self.config.enabled:
            return

        url = f"{self.config.url}/api/states/{entity_id}"
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"

        payload = {"state": state, "attributes": attributes or {}}
        try:
            async with self._session.post(
                url, headers=headers, json=payload
            ) as response:
                if response.status >= 300:
                    text = await response.text()
                    _LOGGER.warning(
                        "Failed to update HA state %s (%s): %s",
                        entity_id,
                        response.status,
                        text,
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Error updating HA state")
