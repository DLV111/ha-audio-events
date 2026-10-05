from __future__ import annotations

import logging


class _QuietPollAccessFilter(logging.Filter):
    """Silence per-request access lines for high-frequency panel polling.

    The ingress page polls /api/detections every ~3s; logging each hit at
    INFO drowned out everything else in the add-on log.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return "/api/detections" not in message


def configure_logging(level: str = "INFO") -> None:
    level_name = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=level_name,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    access_logger = logging.getLogger("aiohttp.access")
    access_logger.addFilter(_QuietPollAccessFilter())
