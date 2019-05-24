import logging

from pandas import DataFrame
from input import import_PV
from paths import *

class PV:
    def __init__(self, path=None):
        ''' Sets parameter from default values'''
        logging.info("PV Parameters are set")
        self.__size = None
        self.irradiation = None
        self.performanceRatio = None
        self.gamma = None
        self._set_pv_parameters_from_file(path)

    def _set_pv_parameters_from_file(self, path):
        ''' reads PV parameter from file in Path and updates attributes '''
        if path is None:
            path = gen_Path(path_parameters)
        parameters = read_parameters(path)['PV']
        self.size = parameters['size']
        self.irradiation = parameters['irradiation']
        self.performanceRatio = parameters['performanceRatio']
        self.gamma = parameters['gamma']
        logging.info("PV Parameters Set From {}".format(path))
        self._calculate_pv_generation()

    def update_parameters(self, path):
        if path is None:
            self._set_pv_parameters_from_file()
        else:
            self._set_pv_parameters_from_file(path)

    def _calculate_pv_generation(self, pvList=import_PV()):
        ''' calculates PvGen based on PV __parameters'''
        logging.info("PV Generation for PV Size {} kW is calculated".format(self.size))
        return pvList * self.size * self.irradiation * self.gamma * self.performanceRatio

    @property
    def _calculatedPvGen(self):
        return self._calculate_pv_generation()


