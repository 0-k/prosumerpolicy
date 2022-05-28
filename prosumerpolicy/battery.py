from prosumerpolicy.paths import *


class Battery(object):
    def __init__(self, path=None):
        """Sets parameter from default values"""
        logging.info("battery config is set")
        self._size = None
        self.charge_efficiency = None
        self.discharge_efficiency = None
        self.self_discharge = None
        self.initial_battery_capacity = None
        self._ratio_e2p = None
        self.maximum_charge_discharge_capacity = None
        self.total_battery_cycles = None
        self._set_battery_parameters_from_file(path)

    def _set_battery_parameters_from_file(self, path=None):
        """reads battery parameter from file in Path and updates attributes"""
        if path is None:
            path = gen_path(path_parameters)
        parameters = read_parameters(path)["battery"]
        self.size = int(parameters["size"])
        self.charge_efficiency = float(parameters["charge_efficiency"])
        self.discharge_efficiency = float(parameters["discharge_efficiency"])
        self.self_discharge = float(parameters["self_discharge"])
        self.initial_battery_capacity = float(parameters["initial_battery_capacity"])
        self.ratio_e2p = float(parameters["ratio_e2p"])
        self.total_battery_cycles = int(parameters["battery_cycles"])
        self.replacement_cost_factor = float(parameters["replacement_cost_factor"])
        self.maximum_charge_discharge_capacity = (
            self.__calculate_maximum_charge_discharge_capacity()
        )

    def update_parameters(self, path=None):
        if path is None:
            self._set_battery_parameters_from_file()
        else:
            self._set_battery_parameters_from_file(path)

    @property
    def ratio_e2p(self):
        """battery E2P ratio"""
        return self._ratio_e2p

    @ratio_e2p.setter
    def ratio_e2p(self, value):
        assert value >= 0
        self._ratio_e2p = value
        self.maximum_charge_discharge_capacity = (
            self.__calculate_maximum_charge_discharge_capacity()
        )

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = value
        self.maximum_charge_discharge_capacity = (
            self.__calculate_maximum_charge_discharge_capacity()
        )  # recalculates discharge and charge capacity

    def __calculate_maximum_charge_discharge_capacity(self):
        if self._ratio_e2p is None:
            self._ratio_e2p = 1
        return self._size / self._ratio_e2p
