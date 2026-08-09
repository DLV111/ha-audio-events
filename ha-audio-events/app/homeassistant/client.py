from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from app.config import HomeAssistantConfig
from app.detection.models import EventMessage

_LOGGER = logging.getLogger(__name__)


class HomeAssistantClient:
    def __init__(self, config: HomeAssistantConfig) -> None:
        self.config = config
        self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        await self._session.close()

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

    async def update_state(
        self, entity_id: str, state: str, attributes: dict[str, Any] | None = None
    ) -> None:
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
