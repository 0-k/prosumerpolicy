import math
import numpy as np
from prosumerpolicy.paths import *


class Economics:
    def __init__(self, input, policy, optimization):
        self._input = input
        self._policy = policy
        self._optimization = optimization
        self.pv = self._input.pv
        self.battery = self._input.battery
        self._irr = None
        self._npv = None
        self._autarky = None
        self._self_consumption = None
        self._avoided_network_fees = None
        self._is_optimize_year = False
        self._set_economic_parameters_from_file()

    def _set_economic_parameters_from_file(self, path=None):
        """reads PV parameter from file in Path and updates attributes"""
        if path is None:
            path = gen_path(path_parameters)
        parameters = read_parameters(path)["economics"]
        self._discount = float(parameters["discount"])
        self._lifetime = int(parameters["lifetime"])
        self._invest_PV = float(parameters["invest_pv"])
        self._invest_Bat = float(parameters["invest_bat"])
        self._o_and_m_pv = float(parameters["o_and_m_pv"])
        self._o_and_m_bat = float(parameters["o_and_m_bat"])
        self._vat = float(parameters["vat"])
        self._scaling_factor_pv = float(parameters["scaling_factor_pv"])
        self._scaling_factor_battery = float(parameters["scaling_factor_battery"])
        self._optimization_foresight_hours = int(
            parameters["optimization_foresight_hours"]
        )

    def _pv_initial_cost(self):
        """Calculates initial cost of PV"""
        if self.pv.size == 0:
            initial_cost_per_kw = 0
        else:
            initial_cost_per_kw = (
                self._invest_PV * (self.pv.size / 10) ** self._scaling_factor_pv
            )
        initial_cost_pv = self.pv.size * initial_cost_per_kw
        return initial_cost_pv

    def _battery_initial_cost(self):
        """Calculates initial cost of Battery"""
        if self.battery.size == 0:
            initial_cost_per_kw = 0
        else:
            initial_cost_per_kw = (
                self._invest_Bat
                * (self.battery.size / 10) ** self._scaling_factor_battery
            )
        initial_cost_battery = self.battery.size * initial_cost_per_kw
        return initial_cost_battery

    def _calculate_avoided_network_fees(self):
        """calculates avoided network fees"""
        if (
            self._policy.is_fixed_network_charges
        ):  # all capacity-based network charges are conserved
            avoided_network_fees = 0
            return avoided_network_fees

        elif self._optimization._optimization_status == 1:  # BAU #TODO Enums
            self_produced = self._input.load_list - self._optimization.energy_from_grid_bau
            avoided_network_fees = sum(self_produced) * self._policy.network_charge
            return avoided_network_fees
        elif self._optimization._optimization_status == 2:  # Non-BAU
            self_produced = self._input.load_list - self._optimization.sum_energy_from_grid
            avoided_network_fees = sum(self_produced) * self._policy.network_charge
            return avoided_network_fees

    def _calculate_npv(self, discount=None):
        if discount is None:
            discount = self._discount
        PV = self._pv_initial_cost()
        Bat = self._battery_initial_cost()
        cost = (-PV - Bat) * self._vat  # initial investment in year 0
        logging.info("Net Present Value for {} years calculated".format(self._lifetime))
        if self.num_of_cycles == 0:
            battery_year = 100
        else:
            battery_year = (
                self.battery.total_battery_cycles / self.num_of_cycles
            )  # number of years to change battery.
            battery_year = int(battery_year)
        for year in range(1, int(self._lifetime + 1)):
            ref_year_cost = self.reference_total / math.pow(1.0 + discount, year)
            if year == battery_year:
                logging.warning("Battery is Changed")
                year_cost = (
                    self.revenue_total
                    - self._o_and_m_pv * PV
                    - Bat * self._vat * self.battery.replacement_cost_factor
                )
            else:
                year_cost = (
                    self.revenue_total - self._o_and_m_pv * PV - self._o_and_m_bat * Bat
                )
            year_cost = year_cost / math.pow(1.0 + discount, year)
            cost += year_cost - ref_year_cost
        return cost

    def _calculate_irr(self):
        x0 = -0.05
        x1 = -0.2
        x2 = -1
        threshold = 0.5
        sol_delta = 100 * threshold
        valid_run = False
        for _ in range(100):
            try:
                x2 = x1 - (x1 - x0) / (
                    self._calculate_npv(discount=x1) - self._calculate_npv(discount=x0)
                ) * self._calculate_npv(discount=x1)
                sol_delta = self._calculate_npv(discount=x2)
                x0 = x1
                x1 = x2
                if abs(sol_delta) < threshold:
                    valid_run = True
                    return x2
            except OverflowError:
                logging.warning("IRR Divergent")
                break
        if not valid_run:
            return -0.25

    def _calculate_battery_counts(self):
        """calculates battery counts"""
        tot = np.array(self.battery_total)
        tot1 = np.insert(tot, 0, self.battery.initial_battery_capacity)
        tot1 = np.delete(tot1, -1)
        diff = tot - tot1
        num_of_cycles = 0
        z = 0
        for i in diff:
            z += abs(i)
            if z >= 2 * self.battery.size:
                z = z - 2 * self.battery.size
                num_of_cycles += 1
        return num_of_cycles

    def _calculate_csc(self):  # charging State Correlator
        """calculates system friendliness indicator. After optimization of existing case the arbitrage case is optimized for entire year"""
        day = self._input.day
        self._input.day = 1
        time = self._input.time_duration
        self._input.time_duration = 8760
        self._optimization._optimize_arbitrage()
        if not self._is_optimize_year:
            self.optimize_year()
        arbitrage_charging = self._calculate_battery_state(
            self._optimization.energy_storage_arbitrage
        )
        optimize_charging = self._calculate_battery_state(self.energy_storage)
        logging.info(
            "System Friendliness Indicator for Arbitrage and {} calculated ".format(
                self._optimization.optimization_state
            )
        )
        assert len(arbitrage_charging) == len(optimize_charging)
        diff = 1 - sum(
            (arbitrage_charging[i] - optimize_charging[i]) ** 2
            for i in range(len(arbitrage_charging))
        ) / (2 * len(arbitrage_charging))
        self._input.time_duration = time
        self._input.day = day
        return diff

    def _calculate_mai(self):
        day = self._input.day
        self._input.day = 1
        time = self._input.time_duration
        self._input.time_duration = 8760
        self._optimization._optimize_arbitrage()
        if not self._is_optimize_year:
            self.optimize_year()
        self.welfare_battery = (
            self.welfare_battery_pv - self.welfare_pv - self.welfare_consumption
        )
        self.welfare_ref = np.dot(
            self._optimization.energy_to_grid_arbitrage
            - self._optimization.energy_from_grid_arbitrage,
            self._input.get_price_list(day=1, duration=8760),
        )
        self._input.time_duration = time
        self._input.day = day
        return self.welfare_battery / self.welfare_ref

    def optimize_year(self):
        self.revenue_total = 0
        self.reference_total = 0
        self.battery_total = []
        self.pv_total = 0
        self.fedin = 0
        self.from_grid = 0
        self.consumption_year = 0
        self.total_direct_use = 0
        self.total_avoided_network_fees = 0
        self.maximum_batt = 0
        self.delta_batt_grid = []
        self.welfare_pv = 0
        self.welfare_consumption = 0
        self.welfare_battery_pv = 0
        if not self._policy.is_rtp and not self._policy.is_vfit:  # BAU Case
            time = self._input.time_duration
            self._input.time_duration = 8760
            self._optimization.optimize()
            self.revenue_total = self._optimization.revenue
            self.reference_total = self._optimization.reference_revenue
            self.total_avoided_network_fees = self._calculate_avoided_network_fees()
            self.battery_total = self._optimization.energy_storage
            self.pv_total = sum(self._input.pv_gen_list)
            self.consumption_year = sum(self._input.load_list)
            self.welfare_pv += np.dot(
                self._input.pv_gen_list, self._input.get_price_list()
            )
            self.welfare_consumption -= np.dot(
                self._input.load_list, self._input.get_price_list()
            )
            self.welfare_battery_pv += -np.dot(
                self._optimization.energy_from_grid_bau, self._input.get_price_list()
            ) + np.dot(self._optimization.energy_to_grid_bau, self._input.get_price_list())
            self._input.time_duration = time
        else:
            for d in range(1, 366):
                self._input.time_duration = 24
                self._input.day = d
                self._optimization.optimize()
                self.delta_batt_grid.append(self._optimization.delta_batt)
                self.fedin += self._optimization.pv_to_grid
                self.from_grid += self._optimization.grid_to_load
                self.revenue_total += self._optimization.revenue
                self.reference_total += self._optimization.reference_revenue
                self.battery_total += self._optimization.energy_storage
                self.total_avoided_network_fees += (
                    self._calculate_avoided_network_fees()
                )
                self.pv_total += sum(self._input.pv_gen_list)
                self.consumption_year += sum(self._input.load_list)
                self.welfare_pv += np.dot(
                    self._input.pv_gen_list, self._input.get_price_list()
                )
                self.welfare_consumption -= np.dot(
                    self._input.load_list, self._input.get_price_list()
                )
                self.welfare_battery_pv += -np.dot(
                    self._optimization.sum_energy_from_grid,
                    self._input.get_price_list(),
                ) + np.dot(
                    self._optimization.sum_energy_to_grid, self._input.get_price_list()
                )
            self.energy_storage = self.battery_total
        self.num_of_cycles = self._calculate_battery_counts()
        self.revenue_total -= self._policy.fixed_capacity
        self.reference_total -= self._policy.fixed_capacity

    def _calculate_battery_state(self, energy_storage):
        energy_storage = np.array(energy_storage)
        energy_storage = np.insert(energy_storage, 0, self.battery.size)
        state_diff = np.diff(energy_storage)
        for i in range(len(state_diff)):
            state_diff[i] = round(state_diff[i], 3)
            if state_diff[i] > 0:
                state_diff[i] = 1
            elif (
                state_diff[i] < -self.battery.self_discharge * self.battery.size * 1.05
            ):
                state_diff[i] = -1
            else:
                state_diff[i] = 0
        return state_diff
