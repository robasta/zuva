from sunsynk.resource import Resource, to_float


class Battery(Resource):
    def __init__(self, data):
        self.charge_today = data.get('etodayChg')
        self.discharge_today = data.get('etodayDischg')
        self.charge_month = data.get('emonthChg')
        self.discharge_month = data.get('emonthDischg')
        self.charge_year = data.get('eyearChg')
        self.discharge_year = data.get('eyearDischg')
        self.charge_total = data.get('etotalChg')
        self.discharge_total = data.get('etotalDischg')
        self.type = data.get('type')
        self.power = data.get('power')
        self.capacity = data.get('capacity')
        self.correct_cap = data.get('correctCap')
        self.current = data.get('current')
        self.voltage = data.get('voltage')
        self.temp = data.get('temp')
        self.soc = data.get('soc')
        self.charge_voltage = data.get('chargeVolt')
        self.discharge_voltage = data.get('dischargeVolt')
        self.charge_current_limit = data.get('chargeCurrentLimit')
        self.discharge_current_limit = data.get('dischargeCurrentLimit')
        self.max_charge_current_limit = data.get('maxChargeCurrentLimit')
        self.max_discharge_current_limit = data.get('maxDischargeCurrentLimit')
        self.status = data.get('status')
        self.battery_soc_1 = data.get('batterySoc1')
        self.battery_current_1 = data.get('batteryCurrent1')
        self.battery_volt_1 = data.get('batteryVolt1')
        self.battery_power_1 = data.get('batteryPower1')
        self.battery_temp_1 = data.get('batteryTemp1')
        self.battery_status_2 = data.get('batteryStatus2')
        self.battery_soc_2 = data.get('batterySoc2')
        self.battery_current_2 = data.get('batteryCurrent2')
        self.battery_volt_2 = data.get('batteryVolt2')
        self.battery_power_2 = data.get('batteryPower2')
        self.battery_temp_2 = data.get('batteryTemp2')
        self.number_of_batteries = data.get('numberOfBatteries')
        self.batt_1_factory = data.get('batt1Factory')
        self.batt_2_factory = data.get('batt2Factory')

    def get_voltage(self) -> float | None:
        return to_float(self.voltage)

    def get_current(self) -> float | None:
        return to_float(self.current)

    def get_power(self) -> float | None:
        return to_float(self.power)
