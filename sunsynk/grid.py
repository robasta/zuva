from sunsynk.resource import Resource, to_float
from sunsynk.vip import Vip


class Grid(Resource):
    def __init__(self, data):
        self.vip = [Vip(vip_data) for vip_data in data.get('vip') or []]
        self.pac = data.get('pac')
        self.qac = data.get('qac')
        self.fac = data.get('fac')
        self.pf = data.get('pf')
        self.status = data.get('status')
        self.today_import = data.get('etodayFrom')
        self.today_export = data.get('etodayTo')
        self.total_import = data.get('etotalFrom')
        self.total_export = data.get('etotalTo')
        self.limiter_power_arr = data.get('limiterPowerArr')
        self.limiter_total_power = data.get('limiterTotalPower')

    def get_voltage(self) -> float | None:
        if len(self.vip) == 0:
            return None
        return to_float(self.vip[0].voltage)

    def get_current(self) -> float | None:
        if len(self.vip) == 0:
            return None
        return to_float(self.vip[0].current)

    def get_power(self) -> float | None:
        if len(self.vip) == 0:
            return None
        return to_float(self.vip[0].power)
