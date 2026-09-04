from sunsynk.pviv import PvIv
from sunsynk.resource import Resource, to_float


class Input(Resource):
    def __init__(self, data):
        self.generated_today = data.get('etoday')
        self.generated_total = data.get('etotal')
        self.pac = data.get('pac')
        self.pv_iv = [PvIv(pviv_data) for pviv_data in data.get('pvIV') or []]

    def get_power(self) -> float:
        return sum(to_float(x.ppv, 0.0) for x in self.pv_iv)

    def get_voltage(self) -> float | None:
        if len(self.pv_iv) == 0:
            return None
        return sum(to_float(x.vpv, 0.0) for x in self.pv_iv) / len(self.pv_iv)
