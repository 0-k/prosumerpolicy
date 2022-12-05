import numpy as np
import pandas as pd

from prosumerpolicy.battery import Battery
from prosumerpolicy.paths import *
from prosumerpolicy.pv import PV


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

    def import_Load(self, path=path_load):
        try:
            absPath = gen_path(path)
            totalload = pd.read_csv(absPath, header=None, delimiter=";")
            logging.info("Load Successfully Imported from {}".format(path_load))
            return totalload
        except:
            logging.warning("Load Input from {} Error".format(path_load))

    def import_PV(self, path=path_pv_generation):
        try:
            absPath = gen_path(path)
            totalPvGen = pd.read_csv(absPath, header=None)
            print(totalPvGen)
            logging.info(
                "PV Gen Successfully Imported from {}".format(path_pv_generation)
            )
            self.pv.pv_profile = totalPvGen
            return totalPvGen
        except:
            logging.warning("Pv Gen Input from {} Error".format(path_pv_generation))

    def import_prices(self, path=path_prices):
        try:
            absPath = gen_path(path)
            totalPrices = pd.read_csv(absPath, sep=";")
            logging.info("Prices Successfully Imported from {}".format(path_prices))
            return totalPrices
        except:
            logging.warning("Price Input from {} Error ".format(path_prices))

    @property
    def pv_gen_list(self):
        return self.get_pv_gen_list()

    @property
    def price_list(self):
        return self.get_price_list()

    @property
    def load_list(self):
        return self.get_load_list()

    @property
    def time_duration(self):
        return self._time_duration

    @time_duration.setter
    def time_duration(self, value):
        self._time_duration = value

    @property
    def day(self):
        return self._day

    @day.setter
    def day(self, value):
        self._day = value

    @property
    def load_row(self):
        return self._load_row

    @load_row.setter
    def load_row(self, value):
        logging.info("Load Row Changed to {}".format(value))
        self._load_row = value

    def get_price_list(self, day=None, duration=None):
        """returns price list as np.array for specified day and duration"""
        if day is None:
            day = self.day
        """ returns price list as np.array for specified day and duration"""
        if duration is None:
            duration = self.time_duration
        if day is None or duration is None:
            raise ValueError("Please Specify a day and time series duration")
        try:
            hours = (day - 1) * 24
            price = np.array(self.total_prices["Price"][hours : hours + duration])
            if np.nan in price:
                raise IOError
            return price / 1000  # in kWh
        except IOError:
            logging.warning("Price list in day {} contains missing values ".format(day))

    def get_load_list(self, day=None, duration=None, load_row=None):
        if day is None:
            day = self.day
        if duration is None:
            duration = self.time_duration
        if load_row is None:
            load_row = self.load_row
        if day is None or duration is None or load_row is None:
            raise ValueError("Please set day, duration and load Row")

        try:
            if load_row == -1:  ## LOAD ROW -1 gives average load row
                hours = (day - 1) * 24
                load = np.array(self.total_average_load[:][hours : hours + duration])
                if np.nan in load:
                    raise IOError
                return load / 1000  # kWh
            else:
                hours = (day - 1) * 24
                load = np.array(self.total_load[load_row][hours : hours + duration])
                if np.nan in load:
                    raise IOError
                return load / 1000  # kWh
        except IOError:
            logging.warning("Load list in day {} contains missing values".format(day))

    def get_pv_gen_list(self, day=None, duration=None):
        if day is None:
            day = self.day
        if duration is None:
            duration = self.time_duration
        if day is None or duration is None:
            raise ValueError("Please Specify a day and time series duration")
        try:
            hours = (day - 1) * 24
            result = np.array(self.pv._calculatedPvGen[0][hours : hours + duration])
            if np.nan in result:
                raise IOError
            return result / 1000  # kW
        except IOError:
            logging.warning(
                "PV Generation list day {} contains missing values.".format(day)
            )
