import warnings
import numpy as np
from optimize import _Optimization
from inputSetter import _InputSetter
from economics import Economics
from policy import Policy


class Model:
    def __init__(self):
        self.__input_setter = _InputSetter()
        self.policy = Policy(self.__input_setter)
        self.__optimization = _Optimization(self.__input_setter, self.policy)
        self._economics = Economics(
            self.__input_setter, self.policy, self.__optimization
        )
        self.PV = self.__input_setter.PV
        self.Battery = self.__input_setter.Battery

    @property
    def day(self):
        return self.__input_setter.day

    @day.setter
    def day(self, d):
        self.__input_setter.day = d
        self._economics._isOptimizeYear = False

    @property
    def loadRow(self):
        return self.__input_setter.loadRow

    @loadRow.setter
    def loadRow(self, l):
        self.__input_setter.loadRow = l
        self._economics._isOptimizeYear = False

    @property
    def timeDuration(self):
        return self.__input_setter.timeDuration

    @timeDuration.setter
    def timeDuration(self, t):
        self.__input_setter.timeDuration = t
        self._economics._isOptimizeYear = False

    @property
    def avoidedNetworkFees(self):
        return self._economics._calculateAvoidedNetworkFees()

    @property
    def CSC(self):
        return self._economics._calculate_CSC()

    @property
    def NPV(self):
        if not self._economics._isOptimizeYear:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimizeYear()
        return self._economics._calculateNPV()

    @property
    def IRR(self):
        if not self._economics._isOptimizeYear:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimizeYear()
        return self._economics._calculateIRR()

    @property
    def pvGenList(self):
        return self.__input_setter.pvGenList

    @property
    def priceList(self):
        return self.__input_setter.priceList

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
        if not self._economics._isOptimizeYear:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimizeYear()
        if self.__optimization._optimizationStatus == 1:  # BAU
            return (
                1 - sum(self.__optimization.energyToGridBAU) / self._economics.pvTotal
            )
        else:
            return (
                1
                - (self._economics.fedin + max(sum(self._economics.deltaBattGrid), 0))
                / self._economics.pvTotal
            )

    @property
    def autarky(self):
        if not self._economics._isOptimizeYear:
            warnings.warn("Optimization for year automatically calculated")
            self._economics.optimizeYear()
        if self.__optimization._optimizationStatus == 1:  # BAU
            return (
                1
                - sum(self.__optimization.energyFromGridBAU)
                / self._economics.consumptionYear
            )
        else:
            return (
                1
                - (
                    self._economics.fromGrid
                    - min(sum(self._economics.deltaBattGrid), 0)
                )
                / self._economics.consumptionYear
            )

    @property
    def MAI(self):
        return self._economics._calculate_MAI()

    @property
    def optimizationState(self):
        return self.__optimization.optimizationState

    @property
    def storageDispatch(self):
        return np.array(self._economics.batteryTotal)

    @property
    def storageDispatchArbitrage(self):
        return self.__optimization.energyStorageArbitrage
