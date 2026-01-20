def __getattr__(name):
    """Lazy imports to avoid circular dependency during setup."""
    if name == 'SunsynkClient':
        from sunsynk.client import SunsynkClient
        return SunsynkClient
    elif name == 'Battery':
        from sunsynk.battery import Battery
        return Battery
    elif name == 'Grid':
        from sunsynk.grid import Grid
        return Grid
    elif name == 'Input':
        from sunsynk.input import Input
        return Input
    elif name == 'Output':
        from sunsynk.output import Output
        return Output
    elif name == 'Inverter':
        from sunsynk.inverter import Inverter
        return Inverter
    elif name == 'Plant':
        from sunsynk.plant import Plant
        return Plant
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'SunsynkClient',
    'Battery',
    'Grid',
    'Input',
    'Output',
    'Inverter',
    'Plant',
]

