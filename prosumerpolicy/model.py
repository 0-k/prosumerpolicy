import warnings

import numpy as np

from prosumerpolicy.economics import Economics
from prosumerpolicy.input import _Input
from prosumerpolicy.optimization import _Optimization
from prosumerpolicy.policy import Policy


class Model:
    def __init__(self):
        self._input_setter = _Input()
        self.policy = Policy(self._input_setter)
        self._optimization = _Optimization(self._input_setter, self.policy)
        self._economics = Economics(self._input_setter, self.policy, self._optimization)
        self.pv = self._input_setter.pv
        self.battery = self._input_setter.battery

    @property
    def day(self):
        return self._input_setter.day

    @day.setter
    def day(self, value):
        self._input_setter.day = value
        self._economics._is_optimize_year = False

    @property
    def load_row(self):
        return self._input_setter.load_row

    @load_row.setter
    def load_row(self, value):
        self._input_setter.load_row = value
        self._economics._is_optimize_year = False

    @property
    def time_duration(self):
        return self._input_setter.time_duration

    @time_duration.setter
    def time_duration(self, value):
        self._input_setter.time_duration = value
        self._economics._is_optimize_year = False

    @property
    def avoided_network_fees(self):
        return self._economics._calculate_avoided_network_fees()

    @property
    def csc(self):
        return self._economics._calculate_csc()

    @property
    def npv(self):
        if not self._economics._is_optimize_year:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimize_year()
        return self._economics._calculate_npv()

    @property
    def irr(self):
        if not self._economics._is_optimize_year:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimize_year()
        return self._economics._calculate_irr()

    @property
    def pv_gen_list(self):
        return self._input_setter.pv_gen_list

    @property
    def price_list(self):
        return self._input_setter.price_list

    @property
    def load_list(self):
        return self._input_setter.load_list

    @property
    def opt(self):
        if self.policy.is_rtp or self.policy.is_vfit:
            return self._optimization.optimize()[0]
        else:
            return self._optimization.optimize()

    @property
    def revenue(self):
        if self.policy.is_rtp or self.policy.is_vfit:
            return self._optimization.optimize()[1]
        else:
            self._optimization.optimize()
            return self._optimization.revenue

    @property
    def self_consumption(self):
        if not self._economics._is_optimize_year:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimize_year()
        if self._optimization._optimization_status == 1:  # BAU
            return (
                1
                - sum(self._optimization.energy_to_grid_bau) / self._economics.pv_total
            )
        else:
            return (
                1
                - (self._economics.fedin + max(sum(self._economics.delta_batt_grid), 0))
                / self._economics.pv_total
            )

    @property
    def autarky(self):
        if not self._economics._is_optimize_year:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimize_year()
        if self._optimization._optimization_status == 1:  # BAU
            return (
                1
                - sum(self._optimization.energy_from_grid_bau)
                / self._economics.consumption_year
            )
        else:
            return (
                1
                - (
                    self._economics.from_grid
                    - min(sum(self._economics.delta_batt_grid), 0)
                )
                / self._economics.consumption_year
            )

    @property
    def MAI(self):
        return self._economics._calculate_mai()

    @property
    def optimization_state(self):
        return self._optimization.optimization_state

    @property
    def storage_dispatch(self):
        return np.array(self._economics.battery_total)

    @property
    def storage_dispatch_arbitrage(self):
        return self._optimization.energyStorageArbitrage
