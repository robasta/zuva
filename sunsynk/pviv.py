from sunsynk.resource import Resource, to_datetime


class PvIv(Resource):
    """PV input voltage/current data model."""

    def __init__(self, data):
        self.id = data.get('id')
        self.pv_no = data.get('pvNo')
        self.vpv = data.get('vpv')
        self.ipv = data.get('ipv')
        self.ppv = data.get('ppv')
        self.today_pv = data.get('todayPv')
        self.sn = data.get('sn')
        self.time = to_datetime(data.get('time'), "%Y-%m-%d %H:%M:%S")
