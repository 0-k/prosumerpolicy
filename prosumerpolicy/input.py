import numpy as np
from prosumerpolicy.pv import PV
from prosumerpolicy.battery import Battery
from prosumerpolicy.paths import *
import pandas as pd
import logging


class _Input:
    def __init__(self, duration=24, day=1, loadRow=0):
        self.pv = PV()
        self.battery = Battery()
        self.total_prices = self.import_prices()
        self.total_pv_gen = self.import_PV()
        self.total_load = self.import_Load()
        self.total_average_load = self.total_load.mean(axis=1)
        self._time_duration = duration
        self._day = day
        self.load_row = loadRow

    def import_Load(self, path=path_Load):
        try:
            absPath = gen_path(path)
            totalload = pd.read_csv(absPath, header=None, delimiter=";")
            logging.info("Load Successfully Imported from {}".format(path_Load))
            return totalload
        except:
            logging.warning("Load Input from {} Error".format(path_Load))

    def import_PV(self, path=path_PvGen):
        try:
            absPath = gen_path(path)
            totalPvGen = pd.read_csv(absPath, header=None)
            print(totalPvGen)
            logging.info("PV Gen Successfully Imported from {}".format(path_PvGen))
            self.pv.pv_profile = totalPvGen
            return totalPvGen
        except:
            logging.warning("Pv Gen Input from {} Error".format(path_PvGen))

    def import_prices(self, path=path_Prices):
        try:
            absPath = gen_path(path)
            totalPrices = pd.read_csv(absPath, sep=";")
            logging.info("Prices Successfully Imported from {}".format(path_Prices))
            return totalPrices
        except:
            logging.warning("Price Input from {} Error ".format(path_Prices))

    @property
    def pvGenList(self):
        return self.get_pvGen_list()

    @property
    def priceList(self):
        return self.get_price_list()

    @property
    def loadList(self):
        return self.get_load_list()

    @property
    def timeDuration(self):
        return self._time_duration

    @timeDuration.setter
    def timeDuration(self, value):
        self._time_duration = value

    @property
    def day(self):
        return self._day

    @day.setter
    def day(self, value):
        self._day = value

    @property
    def load_row(self):
        return self.__loadRow

    @load_row.setter
    def load_row(self, value):
        logging.info("Load Row Changed to {}".format(value))
        self.__loadRow = value

    def get_price_list(self, day=None, duration=None):
        """returns price list as np.array for specified day and duration"""
        if day is None:
            day = self.day
        """ returns price list as np.array for specified day and duration"""
        if duration is None:
            duration = self.timeDuration
        if day is None or duration is None:
            raise ValueError("Please Specify a day and time series duration")
        try:
            hours = (day - 1) * 24
            price = np.array(self.total_prices["Price"][hours: hours + duration])
            if np.nan in price:
                raise IOError
            return price / 1000  # in kWh
        except IOError:
            logging.warning(
                "Price list in day {} contains missing values ".format(day)
            )

    def get_load_list(self, day=None, duration=None, loadRow=None):
        if day is None:
            day = self.day
        if duration is None:
            duration = self.timeDuration
        if loadRow is None:
            loadRow = self.load_row
        if day is None or duration is None or loadRow is None:
            raise ValueError("Please set day, duration and load Row")

        try:
            if loadRow == -1:  ## LOAD ROW -1 gives average load row
                hours = (day - 1) * 24
                load = np.array(self.total_average_load[:][hours: hours + duration])
                if np.nan in load:
                    raise IOError
                return load / 1000  # kWh
            else:
                hours = (day - 1) * 24
                load = np.array(self.total_load[loadRow][hours: hours + duration])
                if np.nan in load:
                    raise IOError
                return load / 1000  # kWh
        except IOError:
            logging.warning("Load list in day {} contains missing values".format(day))

    def get_pvGen_list(self, day=None, duration=None):
        if day is None:
            day = self.day
        if duration is None:
            duration = self.timeDuration
        if day is None or duration is None:
            raise ValueError("Please Specify a day and time series duration")
        try:
            hours = (day - 1) * 24
            result = np.array(self.pv._calculatedPvGen[0][hours: hours + duration])
            if np.nan in result:
                raise IOError
            return result / 1000  # kW
        except IOError:
            logging.warning(
                "PV Generation list day {} contains missing values.".format(day)
            )
