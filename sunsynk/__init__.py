"""Public names of the sunsynk client, resolved lazily.

``setup.py`` imports ``sunsynk.version_info`` - and therefore this module -
before the runtime dependencies in requirements.txt are installed. Importing
the client eagerly here would make a fresh ``pip install .`` fail on the
missing aiohttp/cryptography imports, so each name is loaded on first access.
"""
from importlib import import_module
from typing import TYPE_CHECKING

_EXPORTS = {
    'SunsynkClient': 'sunsynk.client',
    'SunsynkApiError': 'sunsynk.client',
    'SunsynkConnectionError': 'sunsynk.client',
    'SunsynkTimeoutError': 'sunsynk.client',
    'Battery': 'sunsynk.battery',
    'Grid': 'sunsynk.grid',
    'Input': 'sunsynk.input',
    'Output': 'sunsynk.output',
    'Inverter': 'sunsynk.inverter',
    'Plant': 'sunsynk.plant',
}

if TYPE_CHECKING:  # Gives type checkers and linters the real definitions.
    from sunsynk.battery import Battery
    from sunsynk.client import (
        SunsynkApiError,
        SunsynkClient,
        SunsynkConnectionError,
        SunsynkTimeoutError,
    )
    from sunsynk.grid import Grid
    from sunsynk.input import Input
    from sunsynk.inverter import Inverter
    from sunsynk.output import Output
    from sunsynk.plant import Plant

__all__ = list(_EXPORTS)


def __getattr__(name):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    return getattr(import_module(module_name), name)


def __dir__():
    return sorted(__all__)
