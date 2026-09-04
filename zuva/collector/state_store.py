"""Durable alert-suppression state for the collector.

Dedupe state (which alerts have already fired, grid up/down, cooldown clocks)
must survive a restart: an in-memory-only evaluator re-alerts on every restart,
so a crash loop becomes a notification flood.

Storage is a single small JSON file written atomically. Failures degrade to
in-memory operation rather than taking the monitor loop down.
"""
import json
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

DEFAULT_STATE_PATH = "/data/collector-state.json"


class StateStore:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("COLLECTOR_STATE_PATH", DEFAULT_STATE_PATH)
        self.enabled = True

    def load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                logger.warning("Ignoring malformed state file %s", self.path)
                return {}
            logger.info("Loaded alert state from %s", self.path)
            return data
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Could not read state file %s: %s", self.path, error)
            return {}

    def save(self, state: dict) -> None:
        if not self.enabled:
            return
        directory = os.path.dirname(self.path) or "."
        try:
            os.makedirs(directory, exist_ok=True)
            # Atomic replace so a crash mid-write cannot leave a truncated file.
            with tempfile.NamedTemporaryFile(
                mode="w", dir=directory, delete=False, encoding="utf-8"
            ) as handle:
                json.dump(state, handle)
                temp_path = handle.name
            os.replace(temp_path, self.path)
        except OSError as error:
            # Log once, then stop trying: an unwritable path will not fix itself
            # and must not spam the log on every poll.
            logger.warning(
                "Could not persist alert state to %s (%s). "
                "Continuing in memory; alerts may repeat after a restart.",
                self.path,
                error,
            )
            self.enabled = False
