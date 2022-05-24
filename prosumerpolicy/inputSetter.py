import numpy as np
from paths import *
from input import *
from pv import PV
from battery import Battery
import logging

totalPrices = import_Prices(path_Prices)
totalPvGen = import_PV(path_PvGen)
totalLoad = import_Load(path_Load)


class _InputSetter:
    def __init__(self, duration=24, day=1, loadRow=0):
        self.PV = PV()
        self.Battery = Battery()
        self.totalPrices = totalPrices
        self.totalPvGen = totalPvGen
        self.totalLoad = totalLoad
        self.totalAverageLoad = totalLoad.mean(axis=1)
        self.__timeDuration = duration
        self.__day = day
        self.loadRow = loadRow

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
        return self.__timeDuration

    @timeDuration.setter
    def timeDuration(self, time):
        self.__timeDuration = time

    @property
    def day(self):
        return self.__day

    @day.setter
    def day(self, day):
        self.__day = day

    @property
    def loadRow(self):
        return self.__loadRow

    @loadRow.setter
    def loadRow(self, loadrow):
        logging.info("Load Row Changed to {}".format(loadrow))
        self.__loadRow = loadrow

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
            price = np.array(self.totalPrices["Price"][hours : hours + duration])
            if np.nan in price:
                raise IOError
            return price / 1000  # in kWh
        except IOError:
            logging.WARNING(
                "Price list in day {} contains missing values ".format(day)
            )  # FIXME Logger

    def get_load_list(self, day=None, duration=None, loadRow=None):
        if day is None:
            day = self.day
        if duration is None:
            duration = self.timeDuration
        if loadRow is None:
            loadRow = self.loadRow
        if day is None or duration is None or loadRow is None:
            raise ValueError("Please set day, duration and load Row")

        try:
            if loadRow == -1:  ## LOAD ROW -1 gives average load row
                hours = (day - 1) * 24
                load = np.array(self.totalAverageLoad[:][hours : hours + duration])
                if np.nan in load:
                    raise IOError
                return load / 1000  # kWh
            else:
                hours = (day - 1) * 24
                load = np.array(self.totalLoad[loadRow][hours : hours + duration])
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
            result = np.array(self.PV._calculatedPvGen[0][hours : hours + duration])
            if np.nan in result:
                raise IOError
            return result / 1000  # kW
        except IOError:
            logging.warning(
                "PV Generation list day {} contains missing values.".format(day)
            )
