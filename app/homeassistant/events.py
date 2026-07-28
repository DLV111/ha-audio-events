from __future__ import annotations

import logging
from typing import Any

from app.detection.models import EventMessage

_LOGGER = logging.getLogger(__name__)


def publish_event(event: EventMessage) -> None:
    _LOGGER.info("Publishing Home Assistant event %s: %s", event.event_type, event)
    # Placeholder: in actual add-on runtime, this could call the HA event bus API or websocket.
    # The current design keeps the logic isolated from HA internals.
    return
