import warnings
import numpy as np
from paths import *
from optimize import _Optimize
from inputSetter import _InputSetter
from economic import Economic
from policy import Policy

class Model:

    def __init__(self, path=None):
        self.__InputSetter = _InputSetter()
        self.Policy = Policy(self.__InputSetter)
        self.__Optimize = _Optimize(self.__InputSetter, self.Policy)
        self._Economic=Economic(self.__InputSetter, self.Policy, self.__Optimize)
        self.PV = self.__InputSetter.PV
        self.Battery = self.__InputSetter.Battery

    @property
    def day(self):
        return self.__InputSetter.day

    @day.setter
    def day(self,d):
        self.__InputSetter.day=d
        self._Economic._isOptimizeYear=False

    @property
    def loadRow(self):
        return self.__InputSetter.loadRow

    @loadRow.setter
    def loadRow(self,l):
        self.__InputSetter.loadRow=l
        self._Economic._isOptimizeYear = False

    @property
    def timeDuration(self):
        return self.__InputSetter.timeDuration

    @timeDuration.setter
    def timeDuration(self,t):
        self.__InputSetter.timeDuration=t
        self._Economic._isOptimizeYear = False

    @property
    def avoidedNetworkFees(self):
        return self._Economic._calculateAvoidedNetworkFees()

    @property
    def CSC(self):
        return self._Economic._calculate_CSC()

    @property
    def NPV(self):
        if not self._Economic._isOptimizeYear:
            warnings.warn("Optimization for year automatically calculated")
            self._Economic.optimizeYear()
        return self._Economic._calculateNPV()

    @property
    def IRR(self):
        if not self._Economic._isOptimizeYear:
            warnings.warn("Optimization for year automatically calculated")
            self._Economic.optimizeYear()
        return self._Economic._calculateIRR()

    @property
    def pvGenList(self):
        return self.__InputSetter.pvGenList

    @property
    def priceList(self):
        return self.__InputSetter.priceList

    @property
    def loadList(self):
        return self.__InputSetter.loadList

    @property
    def opt(self):
        if self.Policy.isRTP or self.Policy.isVFIT:
            return self.__Optimize.optimize()[0]
        else:
            return self.__Optimize.optimize()

    @property
    def revenue(self):
        if self.Policy.isRTP or self.Policy.isVFIT:
            return self.__Optimize.optimize()[1]
        else:
            self.__Optimize.optimize()
            return self.__Optimize.revenue

    @property
    def selfConsumption(self):
        if not self._Economic._isOptimizeYear:
            warnings.warn("Optimization for year automatically calculated")
            self._Economic.optimizeYear()
        if self.__Optimize._optimizationStatus == 1:  # BAU
            return 1 - sum(self.__Optimize.energyToGridBAU) / self._Economic.pvTotal
        else:
            return 1 - (self._Economic.fedin + max(sum(self._Economic.deltaBattGrid), 0)) / self._Economic.pvTotal

    @property
    def autarky(self):
        if not self._Economic._isOptimizeYear:
            warnings.warn("Optimization for year automatically calculated")
            self._Economic.optimizeYear()
        if self.__Optimize._optimizationStatus == 1:  # BAU
            return 1 - sum(self.__Optimize.energyFromGridBAU) / self._Economic.consumptionYear
        else:
            return 1 - (self._Economic.fromGrid - min(sum(self._Economic.deltaBattGrid), 0)) / self._Economic.consumptionYear

    @property
    def MAI(self):
        return self._Economic._calculate_MAI()

    @property
    def optimizationState(self):
        return self.__Optimize.optimizationState

    @property
    def storageDispatch(self):
        return np.array(self._Economic.batteryTotal)
    @property
    def storageDispatchArbitrage(self):
        return self.__Optimize.energyStorageArbitrage

