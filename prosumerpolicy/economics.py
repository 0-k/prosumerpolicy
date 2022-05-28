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
        parameters = read_parameters(path)["Economics"]
        self._discount = float(parameters["discount"])
        self._lifetime = int(parameters["lifetime"])
        self._invest_PV = float(parameters["invest_PV"])
        self._invest_Bat = float(parameters["invest_Bat"])
        self._o_and_m_pv = float(parameters["oAndM_PV"])
        self._o_and_m_bat = float(parameters["oAndM_Bat"])
        self._vat = float(parameters["VAT"])
        self._scaling_factor_pv = float(parameters["scalingFactorPV"])
        self._scaling_factor_battery = float(parameters["scalingFactorBattery"])
        self._optimization_foresight_hours = int(
            parameters["optimizationForesightHours"]
        )

    def __pvInitialCost(self):
        """Calculates initial cost of PV"""
        if self.pv.size == 0:
            initial_cost_per_kw = 0
        else:
            initial_cost_per_kw = (
                    self._invest_PV * (self.pv.size / 10) ** self._scaling_factor_pv
            )
        initial_cost_pv = self.pv.size * initial_cost_per_kw
        return initial_cost_pv

    def __batteryInitialCost(self):
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

    def _calculateAvoidedNetworkFees(self):
        """calculates avoided network fees"""
        if (
            self._policy.is_fixed_network_charges
        ):  # all capacity-based network charges are conserved
            avoided_network_fees = 0
            return avoided_network_fees

        elif self._optimization._optimization_status == 1:  # BAU #TODO Enums
            self_produced = (
                    self._input.loadList - self._optimization.energyFromGridBAU
            )
            avoided_network_fees = sum(self_produced) * self._policy.networkCharge
            return avoided_network_fees
        elif self._optimization._optimization_status == 2:  # Non-BAU
            self_produced = (
                    self._input.loadList - self._optimization.sumEnergyFromGrid
            )
            avoided_network_fees = sum(self_produced) * self._policy.networkCharge
            return avoided_network_fees

    def _calculateNPV(self, discount=None):
        if discount is None:
            discount = self._discount
        PV = self.__pvInitialCost()
        Bat = self.__batteryInitialCost()
        cost = (-PV - Bat) * self._vat  # initial investment in year 0
        logging.info(
            "Net Present Value for {} years calculated".format(self._lifetime)
        )
        if self.numOfCycles == 0:
            batteryYear = 100
        else:
            batteryYear = (
                    self.battery.total_battery_cycles / self.numOfCycles
            )  # number of years to change battery.
            batteryYear = int(batteryYear)
        for year in range(1, int(self._lifetime + 1)):
            refYearCost = self.referenceTotal / math.pow(1.0 + discount, year)
            if year == batteryYear:
                logging.warning("Battery is Changed")
                yearCost = (
                        self.revenueTotal
                        - self._o_and_m_pv * PV
                        - Bat * self._vat * self.battery.replacement_cost_factor
                )
            else:
                yearCost = (
                        self.revenueTotal - self._o_and_m_pv * PV - self._o_and_m_bat * Bat
                )
            yearCost = yearCost / math.pow(1.0 + discount, year)
            cost += yearCost - refYearCost
        return cost

    def _calculateIRR(self):
        x0 = -0.05
        x1 = -0.2
        x2 = -1
        threshold = 0.5
        solDelta = 100 * threshold
        validRun = False
        for _ in range(100):
            try:
                x2 = x1 - (x1 - x0) / (
                    self._calculateNPV(discount=x1) - self._calculateNPV(discount=x0)
                ) * self._calculateNPV(discount=x1)
                solDelta = self._calculateNPV(discount=x2)
                x0 = x1
                x1 = x2
                if abs(solDelta) < threshold:
                    validRun = True
                    return x2
            except OverflowError:
                logging.warning("IRR Divergent")
                break
        if not validRun:
            return -0.25

    def _calculate_battery_counts(self):
        """calculates battery counts"""
        tot = np.array(self.batteryTotal)
        tot1 = np.insert(tot, 0, self.battery.initial_battery_capacity)
        tot1 = np.delete(tot1, -1)
        diff = tot - tot1
        numOfCycles = 0
        z = 0
        for i in diff:
            z += abs(i)
            if z >= 2 * self.battery.size:
                z = z - 2 * self.battery.size
                numOfCycles += 1
        return numOfCycles

    def _calculate_CSC(self):  # charging State Correlator
        """calculates system friendliness indicator. After optimization of existing case the arbitrage case is optimized for entire year"""
        day = self._input.day
        self._input.day = 1
        time = self._input.timeDuration
        self._input.timeDuration = 8760
        self._optimization._optimize_arbitrage()
        if not self._is_optimize_year:
            self.optimizeYear()
        arbitrageCharging = self._calculate_battery_state(
            self._optimization.energyStorageArbitrage
        )
        optimizeCharging = self._calculate_battery_state(self.energyStorage)
        logging.info(
            "System Friendliness Indicator for Arbitrage and {} calculated ".format(
                self._optimization.optimizationState
            )
        )
        assert len(arbitrageCharging) == len(optimizeCharging)
        diff = 1 - sum(
            (arbitrageCharging[i] - optimizeCharging[i]) ** 2
            for i in range(len(arbitrageCharging))
        ) / (2 * len(arbitrageCharging))
        self._input.timeDuration = time
        self._input.day = day
        return diff

    def _calculate_MAI(self):
        day = self._input.day
        self._input.day = 1
        time = self._input.timeDuration
        self._input.timeDuration = 8760
        self._optimization._optimize_arbitrage()
        if not self._is_optimize_year:
            self.optimizeYear()
        self.welfareBattery = (
            self.welfareBatteryPV - self.welfarePV - self.welfareConsumption
        )
        self.welfareRef = np.dot(
            self._optimization.energyToGridArbitrage
            - self._optimization.energyFromGridArbitrage,
            self._input.get_price_list(day=1, duration=8760),
        )
        self._input.timeDuration = time
        self._input.day = day
        return self.welfareBattery / self.welfareRef

    def optimizeYear(self):
        self.revenueTotal = 0
        self.referenceTotal = 0
        self.batteryTotal = []
        self.pvTotal = 0
        self.fedin = 0
        self.fromGrid = 0
        self.consumptionYear = 0
        self.totalDirectUse = 0
        self.totalAvoidedNetworkFees = 0
        self.maximumBATT = 0
        self.deltaBattGrid = []
        self.welfarePV = 0
        self.welfareConsumption = 0
        self.welfareBatteryPV = 0
        if not self._policy.is_rtp and not self._policy.isVFIT:  # BAU Case
            time = self._input.timeDuration
            self._input.timeDuration = 8760
            self._optimization.optimize()
            self.revenueTotal = self._optimization.revenue
            self.referenceTotal = self._optimization.referenceRevenue
            self.totalAvoidedNetworkFees = self._calculateAvoidedNetworkFees()
            self.batteryTotal = self._optimization.energyStorage
            self.pvTotal = sum(self._input.pvGenList)
            self.consumptionYear = sum(self._input.loadList)
            self.welfarePV += np.dot(
                self._input.pvGenList, self._input.get_price_list()
            )
            self.welfareConsumption -= np.dot(
                self._input.loadList, self._input.get_price_list()
            )
            self.welfareBatteryPV += -np.dot(
                self._optimization.energyFromGridBAU, self._input.get_price_list()
            ) + np.dot(
                self._optimization.energyToGridBAU, self._input.get_price_list()
            )
            self._input.timeDuration = time
        else:
            for d in range(1, 366):
                self._input.timeDuration = 24
                self._input.day = d
                self._optimization.optimize()
                self.deltaBattGrid.append(self._optimization.deltaBatt)
                self.fedin += self._optimization.PVtoGrid
                self.fromGrid += self._optimization.GridtoLoad
                self.revenueTotal += self._optimization.revenue
                self.referenceTotal += self._optimization.referenceRevenue
                self.batteryTotal += self._optimization.energyStorage
                self.totalAvoidedNetworkFees += self._calculateAvoidedNetworkFees()
                self.pvTotal += sum(self._input.pvGenList)
                self.consumptionYear += sum(self._input.loadList)
                self.welfarePV += np.dot(
                    self._input.pvGenList, self._input.get_price_list()
                )
                self.welfareConsumption -= np.dot(
                    self._input.loadList, self._input.get_price_list()
                )
                self.welfareBatteryPV += -np.dot(
                    self._optimization.sumEnergyFromGrid,
                    self._input.get_price_list(),
                ) + np.dot(
                    self._optimization.sumEnergyToGrid, self._input.get_price_list()
                )
            self.energyStorage = self.batteryTotal
        self.numOfCycles = self._calculate_battery_counts()
        self.revenueTotal -= self._policy.fixedCapacity
        self.referenceTotal -= self._policy.fixedCapacity

    def _calculate_battery_state(self, energyStorage):
        energyStorage = np.array(energyStorage)
        energyStorage = np.insert(energyStorage, 0, self.battery.size)
        stateDiff = np.diff(energyStorage)
        for i in range(len(stateDiff)):
            stateDiff[i] = round(stateDiff[i], 3)
            if stateDiff[i] > 0:
                stateDiff[i] = 1
            elif stateDiff[i] < -self.battery.self_discharge * self.battery.size * 1.05:
                stateDiff[i] = -1
            else:
                stateDiff[i] = 0
        return stateDiff
