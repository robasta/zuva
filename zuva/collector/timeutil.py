"""Local-time helpers.

Every time-of-day rule in this service (consumption windows, quiet hours) is a
business rule expressed in the site's local time, not in the container's clock.
Containers default to UTC, so local time must be explicit: set ``TIMEZONE`` to
an IANA zone name.

This module is intentionally duplicated in ``zuva_api`` because the collector
and the API ship as separate images with no shared package.
"""
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "Africa/Johannesburg"

_cache: dict[str, ZoneInfo] = {}


def get_timezone() -> ZoneInfo:
    name = os.getenv("TIMEZONE", DEFAULT_TIMEZONE)
    if name not in _cache:
        try:
            _cache[name] = ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            logger.error("Unknown TIMEZONE %r, falling back to UTC", name)
            _cache[name] = ZoneInfo("UTC")
    return _cache[name]


def local_now() -> datetime:
    """Current time as a timezone-aware datetime in the configured zone."""
    return datetime.now(get_timezone())
