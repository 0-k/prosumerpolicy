#rom prosumerpolicy.input2 import import_PV
from prosumerpolicy.paths import *


class PV:
    def __init__(self, path=None):
        """Sets parameter from default values"""
        logging.info("PV config are set")
        self.pv_profile = None
        self.__size = None
        self.irradiation = None
        self.performance_ratio = None
        self.gamma = None
        self._set_pv_parameters_from_file(path)

    def _set_pv_parameters_from_file(self, path):
        """reads PV parameter from file in Path and updates attributes"""
        if path is None:
            path = gen_path(path_parameters)
        parameters = read_parameters(path)["PV"]
        self.size = parameters["size"]
        self.irradiation = parameters["irradiation"]
        self.performance_ratio = parameters["performanceRatio"]
        self.gamma = parameters["gamma"]
        logging.info("PV config Set From {}".format(path))
        #self._calculate_pv_generation()

    def update_parameters(self, path):
        if path is None:
            self._set_pv_parameters_from_file()
        else:
            self._set_pv_parameters_from_file(path)

    def _calculate_pv_generation(self):
        """calculates PvGen based on PV __parameters"""
        logging.info("PV Generation for PV Size {} kW is calculated".format(self.size))
        return (
                self.pv_profile * self.size * self.irradiation * self.gamma * self.performance_ratio
        )

    @property
    def _calculatedPvGen(self):
        return self._calculate_pv_generation()
