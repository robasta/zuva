from sunsynk.resource import Resource


class Vip(Resource):
    """Voltage, Current, Power data model."""
    
    def __init__(self, data):
        self.voltage = float(data['volt'])
        self.current = float(data['current'])
        self.power = float(data['power'])
