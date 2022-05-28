import numpy as np
from prosumerpolicy.paths import *


class Policy:
    def __init__(self, Input, path=None):
        self._InputSetter = Input
        self._isRTP = False
        self._isVFIT = False
        self._isFixedNetworkCharges = False
        self.fixedFIT = None  # eur/kwh
        self.electricityTariff = None  # eur/kWh
        self.fixedElectricity = None  # eur/kWh
        self.taxes = None  # eur/KWh Konzessionsabgabe & Stromsteuer
        self._componentLevyFIT = None
        self.networkCharge = None
        self.fixedCapacity = None
        self.electricityBasePrice = None
        self.__parameters = None
        self._set_policy_parameters_from_file(path)
        self.__c = self._calculate_electricity_constant()
        self.__alpha = self._calculate_eeg_ratio()
        #self.__beta = self._calculate_feedIn_ratio()

    def _set_policy_parameters_from_file(self, path=None):
        """update attributes from file"""
        if path is None:
            path = gen_path(path_parameters)
        self.__parameters = read_parameters(path)
        logging.info("Loaded Policy config Set From {}".format(path))
        parameters_Policy = self.__parameters["Policy"]
        parameters_Economic = self.__parameters["Economics"]
        self.fixedFIT = float(parameters_Policy["fixedFIT"])  # eur/kwh
        self.__flatRateElectricityTariff = float(
            parameters_Policy["flatRateElectricityTariff"]
        )  # eur/kWh
        self.electricityWholesale = float(
            parameters_Policy["electricityWholesale"]
        )  # eur/kWh
        self.taxes = float(
            parameters_Policy["taxes"]
        )  # eur/KWh Konzessionsabgabe & Stromsteuer
        self._componentLevyFIT = float(parameters_Policy["componentLevyFIT"])
        if self._isFixedNetworkCharges:
            self.networkCharge = float(
                parameters_Policy["capacityCase"]["networkCharge"]
            )
            self.fixedCapacity = (
                float(parameters_Policy["capacityCase"]["fixedCapacity"])
                * parameters_Economic["VAT"]
            )
            logging.info("No Network Charges Imposed")
        else:
            self.networkCharge = float(
                parameters_Policy["volumetricCase"]["networkCharge"]
            )  # ct per kWh
            self.fixedCapacity = (
                float(parameters_Policy["volumetricCase"]["fixedCapacity"])
                * parameters_Economic["VAT"]
            )  # eur per KW per year
            logging.info("Volumetric Network Charges Imposed")
        self.VAT = parameters_Economic["VAT"]
        self.isRTP = bool(parameters_Policy["isRTP"])
        self.isFixedNetworkCharges = bool(parameters_Policy["isCapacity"])
        self.isVFIT = bool(parameters_Policy["isVFIT"])

    def update_parameters(self, path=None):
        if path is None:
            self._set_policy_parameters_from_file()
        else:
            self._set_policy_parameters_from_file(path)

    @property
    def isRTP(self):
        return self._isRTP

    @isRTP.setter
    def isRTP(self, rtp):
        rtp = bool(rtp)
        self._isRTP = rtp
        logging.info("RTP Status Changed to {}".format(str(rtp)))

    @property
    def isFixedNetworkCharges(self):
        return self._isFixedNetworkCharges

    @isFixedNetworkCharges.setter
    def isFixedNetworkCharges(self, cap):
        cap = bool(cap)
        self._isFixedNetworkCharges = cap
        logging.info("Capacity Status Changed to {}".format(str(cap)))

    @property
    def isVFIT(self):
        return self._isVFIT

    @isVFIT.setter
    def isVFIT(self, fit):
        fit = bool(fit)
        self._isVFIT = fit
        logging.info("Feed in Status Changed to {}".format(str(fit)))

    @property
    def FIT(self):
        return self._calculate_feed_in_tariff()

    @property
    def retailElectricity(self):
        return self._calculate_retail_electricity_prices()

    def _calculate_electricity_constant(self):
        totalAvgLoad = self._InputSetter.get_load_list(day=1, duration=8760, loadRow=-1)
        totalPrice = self._InputSetter.get_price_list(day=1, duration=8760)
        c = (
            self.electricityWholesale * sum(totalAvgLoad)
            - np.dot(totalAvgLoad, totalPrice)
        ) / sum(
            totalAvgLoad
        )  # constant added of price
        return c

    def _calculate_eeg_ratio(self):
        totalAvgLoad = self._InputSetter.get_load_list(day=1, duration=8760, loadRow=-1)
        totalPrice = self._InputSetter.get_price_list(day=1, duration=8760)
        c = self._calculate_electricity_constant()
        alpha = (
            self._componentLevyFIT
            * sum(totalAvgLoad)
            / np.dot((totalPrice + c), totalAvgLoad)
        )
        return alpha

    def _calculate_feedIn_ratio(self):
        totalPrice = self._InputSetter.get_price_list(day=1, duration=8760)
        totalPV = self._InputSetter.get_pvGen_list(day=1, duration=8760)
        c = self._calculate_electricity_constant()

        beta = self.fixedFIT * sum(totalPV) / (np.dot((totalPrice + c), totalPV))
        return beta

    def _calculate_feed_in_tariff(self):
        if self.isVFIT:
            logging.warning(" Variable FIT Set")
            self.__FIT = self.__beta * (
                self._InputSetter.get_price_list() + self.__c
            )  # coefficient obtained by dividing total feed in remuneration to realtime prices times production
            self.__FIT = np.array(self.__FIT)

        else:
            self.__FIT = [self.fixedFIT] * self._InputSetter.timeDuration

        return self.__FIT

    def _calculate_retail_electricity_prices(self):
        parameters = self.__parameters
        parameters_Policy = parameters["Policy"]

        if self.isVFIT and self.isRTP:
            self._componentLevyFIT = self.__alpha * (
                self._InputSetter.get_price_list() + self.__c
            )  # 2.3 calculated by dividing total eeg umlage by realtime prices and load

        if self.isFixedNetworkCharges:
            self.networkCharge = float(
                parameters_Policy["capacityCase"]["networkCharge"]
            )
            self.fixedCapacity = (
                float(parameters_Policy["capacityCase"]["fixedCapacity"])
                * parameters["Economics"]["VAT"]
            )
            logging.info("Capacity Network Charges Imposed")
        else:
            self.networkCharge = float(
                parameters_Policy["volumetricCase"]["networkCharge"]
            )  # ct per kWh
            self.fixedCapacity = (
                float(parameters_Policy["volumetricCase"]["fixedCapacity"])
                * parameters["Economics"]["VAT"]
            )  # eur per KW per year
            logging.info("Volumetric Network Charges Imposed")

        if self.isRTP:
            self.electricityBasePrice = self._InputSetter.get_price_list() + self.__c
            logging.info(
                "Real Time Pricing for Day {} and Time Duration {} Set ".format(
                    self._InputSetter.day, self._InputSetter.timeDuration
                )
            )

        else:
            fixedPrices = [self.electricityWholesale] * self._InputSetter.timeDuration
            fixedPrices = np.array(fixedPrices)
            self.electricityBasePrice = fixedPrices
            logging.info(
                "Constant Prices for day {} and Time Duration {}".format(
                    self._InputSetter.day, self._InputSetter.timeDuration
                )
            )

        total = (
            self._componentLevyFIT
            + self.taxes
            + self.electricityBasePrice
            + self.networkCharge
        )  # networkCharge is zero if case is capacity only

        total *= parameters["Economics"]["VAT"]

        return total
