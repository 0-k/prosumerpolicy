from paths import *


class Battery(object):
    def __init__(self, path=None):
        ''' Sets parameter from default values'''
        logging.info("PV Parameters are set")
        self._size = None
        self.chargeEfficiency = None
        self.dischargeEfficiency = None
        self.selfDischarge = None
        self.initialBatteryCapacity = None
        self._ratioE2P = None
        self.maximumChargeDischargeCapacity = None
        self.totalBatteryCycles = None
        self._set_battery_parameters_from_file(path)

    def _set_battery_parameters_from_file(self, path=None):
        ''' reads battery parameter from file in Path and updates attributes '''
        if path is None:
            path = gen_Path(path_parameters)
        parameters = read_parameters(path)['Battery']
        self.size = int(parameters['size'])
        self.chargeEfficiency = float(parameters['chargeEfficiency'])
        self.dischargeEfficiency = float(parameters['dischargeEfficiency'])
        self.selfDischarge =float(parameters['selfDischarge'])
        self.initialBatteryCapacity =float(parameters['initialBatteryCapacity'])
        self.ratioE2P = float(parameters['ratioE2P'])
        self.totalBatteryCycles = int(parameters['totalbatteryCycles'])
        self.replacementCostFactor =float(parameters['replacementCostFactor'])
        self.maximumChargeDischargeCapacity=self.__calculate_maximum_charge_discharge_capacity()

    def update_parameters(self, path=None):
        if path is None:
            self._set_battery_parameters_from_file()
        else:
            self._set_battery_parameters_from_file(path)

    @property
    def ratioE2P(self):
        ''' battery E2P ratio '''
        return self._ratioE2P

    @ratioE2P.setter
    def ratioE2P(self, r):
        assert r>=0
        self._ratioE2P = r
        self.maximumChargeDischargeCapacity=self.__calculate_maximum_charge_discharge_capacity()

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, m):
        self._size = m
        self.maximumChargeDischargeCapacity =self.__calculate_maximum_charge_discharge_capacity() #recalculates discharge and charge capacity


    def __calculate_maximum_charge_discharge_capacity(self):
        if self._ratioE2P is None:
            self._ratioE2P = 1
        return self._size / self._ratioE2P

