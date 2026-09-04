import datetime


class Resource:
    def __repr__(self):
        attrs = " ".join(f"{k}={v}" for k, v in self.__dict__.items())
        return f"<{self.__class__.__name__} @{id(self) & 0xFFFFFF} {attrs}>"


def to_float(value, default: float | None = None) -> float | None:
    """Coerce an API value to float, returning ``default`` when unusable.

    The Sunsynk API occasionally omits fields or returns them as strings; a
    missing reading must not raise mid-poll.
    """
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_datetime(value, fmt: str) -> datetime.datetime | None:
    """Parse an API timestamp, returning None when missing or malformed."""
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, fmt)
    except (TypeError, ValueError):
        return None


def to_isoformat(value) -> datetime.datetime | None:
    """Parse an ISO-8601 API timestamp, returning None when missing or malformed."""
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
