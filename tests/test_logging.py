"""Tests for logging behaviour: quiet panel-polling access logs and the
conditional open-bind warning."""

from __future__ import annotations

import logging

from app.utils.logging import _QuietPollAccessFilter, configure_logging


def test_detections_polling_access_lines_are_filtered() -> None:
    filt = _QuietPollAccessFilter()

    assert (
        filt.filter(
            logging.LogRecord(
                "aiohttp.access",
                logging.INFO,
                "p",
                1,
                '172.30.32.2 "GET /api/detections HTTP/1.1" 200 179',
                None,
                None,
            )
        )
        is False
    )
    # Everything else still passes.
    assert (
        filt.filter(
            logging.LogRecord(
                "aiohttp.access",
                logging.INFO,
                "p",
                1,
                '172.30.32.2 "GET /api/source HTTP/1.1" 200 212',
                None,
                None,
            )
        )
        is True
    )


def test_configure_logging_installs_poll_filter(caplog) -> None:
    caplog.set_level(logging.INFO, logger="aiohttp.access")
    configure_logging("INFO")

    logger = logging.getLogger("aiohttp.access")
    assert any(isinstance(f, _QuietPollAccessFilter) for f in logger.filters)

    # The polling line must not surface through the configured chain...
    with caplog.at_level(logging.INFO, logger="aiohttp.access"):
        logger.info('"GET /api/detections HTTP/1.1" 200 179')
    assert all("/api/detections" not in r.message for r in caplog.records)

    # ...while other endpoints still do.
    with caplog.at_level(logging.INFO, logger="aiohttp.access"):
        logger.info('"GET /api/cameras HTTP/1.1" 200 321')
    assert any("/api/cameras" in r.message for r in caplog.records)
