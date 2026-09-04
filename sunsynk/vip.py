from sunsynk.resource import Resource, to_float


class Vip(Resource):
    """Voltage, Current, Power data model."""

    def __init__(self, data):
        self.voltage = to_float(data.get('volt'), 0.0)
        self.current = to_float(data.get('current'), 0.0)
        self.power = to_float(data.get('power'), 0.0)
