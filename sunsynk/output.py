from sunsynk.resource import Resource
from sunsynk.vip import Vip


class Output(Resource):
    def __init__(self, data):
        self.vip = [Vip(vip_data) for vip_data in data.get('vip') or []]
        self.p_inv = data.get('pInv')
        self.pac = data.get('pac')
        self.fac = data.get('fac')
