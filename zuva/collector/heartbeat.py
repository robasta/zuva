"""Liveness heartbeat for the collector.

The monitor loop can wedge (hung socket, stuck await) while the process stays
alive, which silently stops all alerting. The loop touches a heartbeat file
after every completed poll; ``python -m collector.heartbeat`` exits non-zero
when that file is missing or stale, which is what the container healthcheck
runs.
"""
import logging
import os
import sys
import time

logger = logging.getLogger(__name__)

DEFAULT_HEARTBEAT_PATH = "/tmp/zuva-heartbeat"  # nosec B108 - container-local liveness marker


def heartbeat_path() -> str:
    return os.getenv("HEARTBEAT_PATH", DEFAULT_HEARTBEAT_PATH)


def touch() -> None:
    try:
        with open(heartbeat_path(), "w", encoding="utf-8") as handle:
            handle.write(str(time.time()))
    except OSError as error:
        logger.debug("Could not write heartbeat: %s", error)


def age_seconds() -> float | None:
    """Seconds since the last completed poll, or None if never recorded."""
    try:
        return time.time() - os.path.getmtime(heartbeat_path())
    except OSError:
        return None


def max_age_seconds() -> float:
    """Staleness budget: a few poll intervals, with a floor for fast polling."""
    poll_interval = float(os.getenv("POLL_INTERVAL", "60"))
    return max(poll_interval * 3 + 60, 180)


def main() -> int:
    age = age_seconds()
    budget = max_age_seconds()
    if age is None:
        print("no heartbeat recorded yet")
        return 1
    if age > budget:
        print(f"heartbeat is stale: {age:.0f}s old (budget {budget:.0f}s)")
        return 1
    print(f"heartbeat ok: {age:.0f}s old")
    return 0


if __name__ == "__main__":
    sys.exit(main())
