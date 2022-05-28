import warnings
import numpy as np
from prosumerpolicy.optimization import _Optimization
from prosumerpolicy.input import _Input
from prosumerpolicy.economics import Economics
from prosumerpolicy.policy import Policy


class Model:
    def __init__(self):
        self.__input_setter = _Input()
        self.policy = Policy(self.__input_setter)
        self.__optimization = _Optimization(self.__input_setter, self.policy)
        self._economics = Economics(
            self.__input_setter, self.policy, self.__optimization
        )
        self.PV = self.__input_setter.pv
        self.Battery = self.__input_setter.battery

    @property
    def day(self):
        return self.__input_setter.day

    @day.setter
    def day(self, d):
        self.__input_setter.day = d
        self._economics._is_optimize_year = False

    @property
    def loadRow(self):
        return self.__input_setter.load_row

    @loadRow.setter
    def loadRow(self, l):
        self.__input_setter.load_row = l
        self._economics._is_optimize_year = False

    @property
    def timeDuration(self):
        return self.__input_setter.time_duration

    @timeDuration.setter
    def timeDuration(self, t):
        self.__input_setter.time_duration = t
        self._economics._is_optimize_year = False

    @property
    def avoidedNetworkFees(self):
        return self._economics._calculate_avoided_network_fees()

    @property
    def CSC(self):
        return self._economics._calculate_csc()

    @property
    def NPV(self):
        if not self._economics._is_optimize_year:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimize_year()
        return self._economics._calculate_npv()

    @property
    def IRR(self):
        if not self._economics._is_optimize_year:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimize_year()
        return self._economics._calculate_irr()

    @property
    def pvGenList(self):
        return self.__input_setter.pv_gen_list

    @property
    def priceList(self):
        return self.__input_setter.price_list

    @property
    def loadList(self):
        return self.__input_setter.loadList

    @property
    def opt(self):
        if self.policy.isRTP or self.policy.isVFIT:
            return self.__optimization.optimize()[0]
        else:
            return self.__optimization.optimize()

    @property
    def revenue(self):
        if self.policy.isRTP or self.policy.isVFIT:
            return self.__optimization.optimize()[1]
        else:
            self.__optimization.optimize()
            return self.__optimization.revenue

    @property
    def selfConsumption(self):
        if not self._economics._is_optimize_year:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimize_year()
        if self.__optimization._optimization_status == 1:  # BAU
            return (
                1 - sum(self.__optimization.energyToGridBAU) / self._economics.pv_total
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
        if self.__optimization._optimization_status == 1:  # BAU
            return (
                1
                - sum(self.__optimization.energyFromGridBAU)
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
    def optimizationState(self):
        return self.__optimization.optimizationState

    @property
    def storageDispatch(self):
        return np.array(self._economics.battery_total)

    @property
    def storageDispatchArbitrage(self):
        return self.__optimization.energyStorageArbitrage
