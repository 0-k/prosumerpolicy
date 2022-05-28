import numpy as np
from prosumerpolicy.paths import *


class Policy:
    def __init__(self, Input, path=None):
        self._input = Input
        self._is_rtp = False
        self._is_vfit = False
        self._is_fixed_network_charges = False
        self.fixed_fit = None  # eur/kwh
        self.electricity_tariff = None  # eur/kWh
        self.fixed_electricity = None  # eur/kWh
        self.taxes = None  # eur/KWh Konzessionsabgabe & Stromsteuer
        self._component_levy_fit = None
        self.network_charge = None
        self.fixed_capacity = None
        self.electricity_base_price = None
        self._parameters = None
        self._set_policy_parameters_from_file(path)
        self._c = self._calculate_electricity_constant()
        self._alpha = self._calculate_eeg_ratio()
        self._beta = self._calculate_feedIn_ratio()

    def _set_policy_parameters_from_file(self, path=None):
        """update attributes from file"""
        if path is None:
            path = gen_path(path_parameters)
        self._parameters = read_parameters(path)
        logging.info("Loaded Policy config Set From {}".format(path))
        parameters_policy = self._parameters["policy"]
        parameters_economic = self._parameters["economics"]
        self.fixed_fit = float(parameters_policy["fixed_fit"])  # eur/kwh
        self._flat_rate_electricity_tariff = float(
            parameters_policy["flat_rate_electricity_tariff"]
        )  # eur/kWh
        self.electricity_wholesale = float(
            parameters_policy["electricity_wholesale"]
        )  # eur/kWh
        self.taxes = float(
            parameters_policy["taxes"]
        )  # eur/KWh Konzessionsabgabe & Stromsteuer
        self._component_levy_fit = float(parameters_policy["component_levy_fit"])
        if self._is_fixed_network_charges:
            self.network_charge = float(
                parameters_policy["capacity_case"]["network_charge"]
            )
            self.fixed_capacity = (
                float(parameters_policy["capacity_case"]["fixed_capacity"])
                * parameters_economic["vat"]
            )
            logging.info("No Network Charges Imposed")
        else:
            self.network_charge = float(
                parameters_policy["volumetric_case"]["network_charge"]
            )  # ct per kWh
            self.fixed_capacity = (
                float(parameters_policy["volumetric_case"]["fixed_capacity"])
                * parameters_economic["vat"]
            )  # eur per KW per year
            logging.info("Volumetric Network Charges Imposed")
        self.vat = parameters_economic["vat"]
        self.is_rtp = bool(parameters_policy["is_rtp"])
        self.is_fixed_network_charges = bool(parameters_policy["is_capacity"])
        self.is_vfit = bool(parameters_policy["is_vfit"])

    def update_parameters(self, path=None):
        if path is None:
            self._set_policy_parameters_from_file()
        else:
            self._set_policy_parameters_from_file(path)

    @property
    def is_rtp(self):
        return self._is_rtp

    @is_rtp.setter
    def is_rtp(self, value):
        value = bool(value)
        self._is_rtp = value
        logging.info("RTP Status Changed to {}".format(str(value)))

    @property
    def is_fixed_network_charges(self):
        return self._is_fixed_network_charges

    @is_fixed_network_charges.setter
    def is_fixed_network_charges(self, value):
        value = bool(value)
        self._is_fixed_network_charges = value
        logging.info("Capacity Status Changed to {}".format(str(value)))

    @property
    def is_vfit(self):
        return self._is_vfit

    @is_vfit.setter
    def is_vfit(self, value):
        value = bool(value)
        self._is_vfit = value
        logging.info("Feed in Status Changed to {}".format(str(value)))

    @property
    def fit(self):
        return self._calculate_feed_in_tariff()

    @property
    def retail_electricity(self):
        return self._calculate_retail_electricity_prices()

    def _calculate_electricity_constant(self):
        total_avg_load = self._input.get_load_list(
            day=1, duration=8760, load_row=-1
        )
        total_price = self._input.get_price_list(day=1, duration=8760)
        c = (
                    self.electricity_wholesale * sum(total_avg_load)
                    - np.dot(total_avg_load, total_price)
        ) / sum(
            total_avg_load
        )  # constant added of price
        return c

    def _calculate_eeg_ratio(self):
        total_avg_load = self._input.get_load_list(
            day=1, duration=8760, load_row=-1
        )
        total_price = self._input.get_price_list(day=1, duration=8760)
        c = self._calculate_electricity_constant()
        alpha = (
            self._component_levy_fit
            * sum(total_avg_load)
            / np.dot((total_price + c), total_avg_load)
        )
        return alpha

    def _calculate_feedIn_ratio(self):
        total_price = self._input.get_price_list(day=1, duration=8760)
        total_pv = self._input.get_pv_gen_list(day=1, duration=8760)
        c = self._calculate_electricity_constant()
        beta = self.fixed_fit * sum(total_pv) / (np.dot((total_price + c), total_pv))
        return beta

    def _calculate_feed_in_tariff(self):
        if self.is_vfit:
            logging.warning(" Variable FIT Set")
            self.__FIT = self._beta * (
                    self._input.get_price_list() + self._c
            )  # coefficient obtained by dividing total feed in remuneration to realtime prices times production
            self.__FIT = np.array(self.__FIT)
        else:
            self.__FIT = [self.fixed_fit] * self._input.time_duration
        return self.__FIT

    def _calculate_retail_electricity_prices(self):
        parameters = self._parameters
        parameters_policy = parameters["policy"]
        if self.is_vfit and self.is_rtp:
            self._component_levy_fit = self._alpha * (
                    self._input.get_price_list() + self._c
            )  # 2.3 calculated by dividing total eeg umlage by realtime prices and load
        if self.is_fixed_network_charges:
            self.network_charge = float(
                parameters_policy["capacity_case"]["network_charge"]
            )
            self.fixed_capacity = (
                float(parameters_policy["capacity_case"]["fixed_capacity"])
                * parameters["economics"]["vat"]
            )
            logging.info("Capacity Network Charges Imposed")
        else:
            self.network_charge = float(
                parameters_policy["volumetric_case"]["network_charge"]
            )  # ct per kWh
            self.fixed_capacity = (
                float(parameters_policy["volumetric_case"]["fixed_capacity"])
                * parameters["economics"]["vat"]
            )  # eur per KW per year
            logging.info("Volumetric Network Charges Imposed")
        if self.is_rtp:
            self.electricity_base_price = self._input.get_price_list() + self._c
            logging.info(
                "Real Time Pricing for Day {} and Time Duration {} Set ".format(
                    self._input.day, self._input.time_duration
                )
            )
        else:
            fixed_prices = [self.electricity_wholesale] * self._input.time_duration
            fixed_prices = np.array(fixed_prices)
            self.electricity_base_price = fixed_prices
            logging.info(
                "Constant Prices for day {} and Time Duration {}".format(
                    self._input.day, self._input.time_duration
                )
            )
        total = (
            self._component_levy_fit
            + self.taxes
            + self.electricity_base_price
            + self.network_charge
        )  # networkCharge is zero if case is capacity only
        total *= parameters["economics"]["vat"]
        return total
