import pandas as pd
import numpy as np
from gurobipy import *

pd.set_option("display.expand_frame_repr", False)


class _Optimization:
    def __init__(self, input, policy):
        self._input = input
        self._policy = policy
        self._optimization_status = None

    def optimize(self, rtp=None, vfit=None, capacity=None):
        if rtp is None:
            pass
        else:
            self._policy.is_rtp = rtp
        if vfit is None:
            pass
        else:
            self._policy.isVFIT = vfit
        if capacity is None:
            pass
        else:
            self._policy.is_fixed_network_charges = capacity
        if not self._policy.is_rtp and not self._policy.isVFIT:
            return self.__BAU()
        else:
            return self.__optimizerDispatch()

    def _optimize_arbitrage(self):
        """

        Function takes Maximum Charge Capacity, Max Discharge Capacity, BatterySize, number of hours and
        a random number generator  and price curve as input

        returns maximum revenue along with hourly Energy dispatch from grid,Energy dispatch to grid and battery state

        Complete foresight, linear optimization done with GUROBI SOLVER

        """
        self.arbitrageState = True
        model = Model("Arbitrage")  # Create Gurobi Model
        prices = self._input.price_list
        N = self._input.time_duration
        model.setParam("OutputFlag", 0)
        e_charge, e_discharge, e_storage = {}, {}, {}  # Intialize Constraint Dictionary
        # All Efficiencies are taken with reference to the battery. if battery discharges 1kwh, this means it actually gives
        # etaDischarge*1kwh to the grid...if battery charges by 1 kwh, this means it took 1/etacharge from the grid/pv
        for j in range(
            N
        ):  # fills constraint dictionary along with lower and upper bounds
            e_charge[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                / self._input.battery.charge_efficiency,
                name="ECharge[%s]" % j,
            )
            e_discharge[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                * self._input.battery.discharge_efficiency,
                name="EDischarge[%s]" % j,
            )
            e_storage[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.size,
                name="EStorage[%s]" % j,
            )
        model.update()
        # EDischarge and Echarge are directly to the grid
        # sets objective function
        model.setObjective(
            sum(
                e_discharge[j] * prices[j] - (e_charge[j]) * prices[j] for j in range(N)
            ),
            GRB.MAXIMIZE,
        )
        for i in range(N):  # Adding constraints for length of N
            if i == 0:
                model.addConstr(
                    e_storage[i]
                    - 0
                    * self._input.battery.size
                    * (1 - self._input.battery.self_discharge)
                    - e_charge[i] * self._input.battery.charge_efficiency
                    + e_discharge[i] / self._input.battery.discharge_efficiency
                    == 0
                )
            else:
                model.addConstr(
                    e_storage[i]
                    - e_storage[i - 1] * (1 - self._input.battery.self_discharge)
                    - e_charge[i] * self._input.battery.charge_efficiency
                    + e_discharge[i] / self._input.battery.discharge_efficiency
                    == 0
                )
        model.update()
        model.optimize()

        efrom_grid, eto_grid, battery_state = [], [], []

        # data wrangling to extract solution
        for i in range(N):
            variables = model.getVarByName("ECharge[%s]" % i)
            efrom_grid.append(variables.x)
            variables = model.getVarByName("EDischarge[%s]" % i)
            eto_grid.append(variables.x)
            variables = model.getVarByName("EStorage[%s]" % i)
            battery_state.append(variables.x)

        self.energyStorageArbitrage = np.array(battery_state)
        self.energyToGridArbitrage = np.array(eto_grid)
        self.energyFromGridArbitrage = np.array(efrom_grid)

        ans = pd.DataFrame(
            {
                "Prices": prices,
                "Battery State (kW)": battery_state,
                "Energy from the grid (kW)": efrom_grid,
                "Energy into the grid (kW)": eto_grid,
            },
        )
        # ans = ans.round(2)
        ans = ans[
            [
                "Prices",
                "Battery State (kW)",
                "Energy from the grid (kW)",
                "Energy into the grid (kW)",
            ]
        ]
        # self.numOfCyclesArb=self.batteryCountsArb()
        return ans
        # return ans, model.objVal  # function returns results as DataFrame and the value of objective function

    def __BAU(self):
        logging.info(
            "Business as Usual: Day {}, Time Duration {}, PV Size {} ".format(
                self._input.day,
                self._input.time_duration,
                self._input.pv.size,
            )
        )
        self._optimization_status = 1

        if self._policy.is_fixed_network_charges:
            self.optimizationState = "BAU Capacity"
        else:
            self.optimizationState = "BAU Volumetric"

        length = min(
            len(self._input.pv_gen_list), len(self._input.loadList)
        )  # in case the inputs  are not the same length, use the smaller.
        battState, energyFromGrid, energyToGrid, cases = (
            [],
            [],
            [],
            [],
        )  # Create Return Variables
        xi = self._input.pv_gen_list[:length] - self._input.loadList[:length]
        battStateATBeg = []
        # All Efficiencies are taken with reference to the battery. if battery discharges 1kwh, this means it actually gives
        # etaDischarge*1kwh to the grid...if battery charges by 1 kwh, this means it took 1kwh/etacharge from the grid/pv
        batteryState = self._input.battery.initial_battery_capacity
        for item in xi:
            battAtBeg = batteryState * (1 - self._input.battery.self_discharge)
            batteryState *= 1 - self._input.battery.self_discharge
            if item <= 0:
                EtoGrid = 0
                if (
                    abs(item)
                    <= min(
                        batteryState,
                        self._input.battery.maximum_charge_discharge_capacity,
                    )
                    * self._input.battery.discharge_efficiency
                ):
                    batteryState = batteryState - (
                        abs(item) / self._input.battery.discharge_efficiency
                    )
                    EfromGrid = 0
                elif (
                    abs(item)
                    > min(
                        batteryState,
                        self._input.battery.maximum_charge_discharge_capacity,
                    )
                    * self._input.battery.discharge_efficiency
                ):
                    EfromGrid = (
                        abs(item)
                        - min(
                            batteryState,
                            self._input.battery.maximum_charge_discharge_capacity,
                        )
                        * self._input.battery.discharge_efficiency
                    )
                    batteryState = batteryState - (
                        min(
                            batteryState,
                            self._input.battery.maximum_charge_discharge_capacity,
                        )
                    )
            else:
                EfromGrid = 0
                if (
                    item
                    >= min(
                        (self._input.battery.size - batteryState),
                        self._input.battery.maximum_charge_discharge_capacity,
                    )
                    / self._input.battery.charge_efficiency
                ):
                    EtoGrid = (
                        item
                        - min(
                            (self._input.battery.size - batteryState),
                            self._input.battery.maximum_charge_discharge_capacity,
                        )
                        / self._input.battery.charge_efficiency
                    )
                    batteryState = batteryState + min(
                        (self._input.battery.size - batteryState),
                        self._input.battery.maximum_charge_discharge_capacity,
                    )
                else:
                    batteryState = (
                        batteryState + item * self._input.battery.charge_efficiency
                    )
                    EtoGrid = 0

            battState.append(batteryState)
            energyFromGrid.append(EfromGrid)
            energyToGrid.append(EtoGrid)
            battStateATBeg.append(battAtBeg)

        ans = pd.DataFrame(
            {
                "Price": self._policy.retailElectricity,
                "load (kW)": self._input.loadList,
                "PV Generation": self._input.pv_gen_list,
                "Battery State (kW)": battState,
                "Energy from the grid (kW)": energyFromGrid,
                "Energy into the grid (kW)": energyToGrid,
                "Bat at beg": battStateATBeg,
            },
        )
        ans = ans[
            [
                "Price",
                "load (kW)",
                "PV Generation",
                "Battery State (kW)",
                "Energy from the grid (kW)",
                "Energy into the grid (kW)",
                "Bat at beg",
            ]
        ]
        energyToGrid = np.array(energyToGrid)
        energyFromGrid = np.array(energyFromGrid)

        revenue = (
            np.dot(self._policy.FIT, energyToGrid)
            - np.dot(self._policy.retailElectricity, energyFromGrid)
            + self._policy.FIT[0] * batteryState
        )

        self.energyToGridBAU = energyToGrid
        self.energyFromGridBAU = energyFromGrid
        self.energyStorage = battState
        self.revenue = revenue
        self.referenceRevenue = np.dot(
            -self._policy.retailElectricity, self._input.loadList
        )
        self.directUse = self._input.pv_gen_list - energyToGrid
        self.directUse = sum(self.directUse) - batteryState

        return ans

    def __optimizerDispatch(self):
        self._optimization_status = 2
        if self._policy.is_fixed_network_charges:
            capacity = " Capacity"
        else:
            capacity = " Volumetric"

        if self._policy.is_rtp and not self._policy.isVFIT:
            self.optimizationState = "RTP and Fixed FIT" + capacity
        elif self._policy.is_rtp and self._policy.isVFIT:
            self.optimizationState = "RTP and Variable FIT" + capacity
        elif not self._policy.is_rtp and self._policy.isVFIT:
            self.optimizationState = "Fixed Price and Variable FIT" + capacity
        logging.info(
            "Real Time Pricing Optimization: Day {}, Time Duration {}, PV Size {} ".format(
                self._input.day,
                self._input.time_duration,
                self._input.pv.size,
            )
        )  # Getting config
        wholesalepri = self._input.price_list
        pri = self._policy.retailElectricity
        load = self._input.loadList
        PV = self._input.pv_gen_list
        FeedIn = self._policy.FIT
        optimization_duration = self._input.time_duration
        model = Model("RTP_withForesight")  # Create Gurobi Model
        model.setParam("OutputFlag", 0)
        (
            eStorage,
            ePVtoBatt,
            ePVtoLoad,
            ePVtoGrid,
            eBatttoGrid,
            eBatttoLoad,
            eGridtoLoad,
            eGridtoBatt,
        ) = (
            {},
            {},
            {},
            {},
            {},
            {},
            {},
            {},
        )  # Initialize Constraint Dictionary
        y = {}
        """ All Efficiencies are taken with reference to the battery. if battery discharges 1kwh,
         this means it actually gives etaDischarge*1kwh to the grid...if battery charges by 1 kwh, this means it
          took 1/etacharge from the grid/pv
        """

        for j in range(
            optimization_duration
        ):  # creates variables along with lower and upper bounds
            y[j] = model.addVar(vtype="b")
            ePVtoBatt[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                / self._input.battery.charge_efficiency,
                name="ePVtoBatt[%s]" % j,
            )
            eBatttoLoad[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                * self._input.battery.discharge_efficiency,
                name="eBatttoLoad[%s]" % j,
            )
            ePVtoLoad[j] = model.addVar(vtype="C", lb=0, name="ePVtoLoad[%s]" % j)
            ePVtoGrid[j] = model.addVar(vtype="C", lb=0, name="ePVtoGrid[%s]" % j)
            eBatttoGrid[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                * self._input.battery.discharge_efficiency,
                name="eBatttoGrid[%s]" % j,
            )
            eGridtoBatt[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                / self._input.battery.charge_efficiency,
                name="eGridtoBatt[%s]" % j,
            )
            eStorage[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.size,
                name="eStorage[%s]" % j,
            )
            eGridtoLoad[j] = model.addVar(vtype="C", lb=0, name="eGridtoLoad[%s]" % j)

        model.update()

        model.setObjective(
            sum(
                eBatttoGrid[j] * wholesalepri[j]
                - eGridtoBatt[j] * pri[j]
                + FeedIn[j] * ePVtoGrid[j]
                - pri[j] * eGridtoLoad[j]
                for j in range(optimization_duration)
            ),
            GRB.MAXIMIZE,
        )  # set objective function maximizing revenue
        for i in range(
            optimization_duration
        ):  # Adding energy constraints for length of optimization_duration
            if i == 0:  # intial value
                model.addConstr(
                    eStorage[i]
                    - self._input.battery.initial_battery_capacity
                    * (1 - self._input.battery.self_discharge)
                    - ePVtoBatt[i] * self._input.battery.charge_efficiency
                    - eGridtoBatt[i] * self._input.battery.charge_efficiency
                    + eBatttoLoad[i] / self._input.battery.discharge_efficiency
                    + eBatttoGrid[i] / self._input.battery.discharge_efficiency
                    == 0
                )
            else:
                model.addConstr(
                    eStorage[i]
                    - eStorage[i - 1] * (1 - self._input.battery.self_discharge)
                    - ePVtoBatt[i] * self._input.battery.charge_efficiency
                    - eGridtoBatt[i] * self._input.battery.charge_efficiency
                    + eBatttoLoad[i] / self._input.battery.discharge_efficiency
                    + eBatttoGrid[i] / self._input.battery.discharge_efficiency
                    == 0
                )
            model.addConstr(ePVtoLoad[i] + ePVtoBatt[i] + ePVtoGrid[i] == PV[i])
            model.addConstr(eGridtoLoad[i] + eBatttoLoad[i] + ePVtoLoad[i] == load[i])
            model.addConstr(
                eBatttoGrid[i]
                <= self._input.battery.maximum_charge_discharge_capacity
                * y[i]
                * self._input.battery.discharge_efficiency
            )
            model.addConstr(
                eGridtoBatt[i]
                <= self._input.battery.maximum_charge_discharge_capacity
                * (1 - y[i])
                / self._input.battery.charge_efficiency
            )

        model.update()
        model.optimize()

        if model.status == GRB.Status.INF_OR_UNBD:
            # Turn presolve off to determine whether model is infeasible
            # or unbounded
            model.setParam(GRB.Param.Presolve, 0)
            model.optimize()
            print(model.status)
        # #extracting optimization results. Pretty ugly
        (
            PVtoGrid,
            PVtoLoad,
            PVtoBatt,
            BatttoLoad,
            BatttoGrid,
            BatteryState,
            GridtoLoad,
            GridtoBatt,
        ) = ([], [], [], [], [], [], [], [])
        for i in range(optimization_duration):
            vars = model.getVarByName("ePVtoBatt[%s]" % i)
            PVtoBatt.append(vars.x)
            vars = model.getVarByName("eBatttoLoad[%s]" % i)
            BatttoLoad.append(vars.x)
            vars = model.getVarByName("ePVtoLoad[%s]" % i)
            PVtoLoad.append(vars.x)
            vars = model.getVarByName("ePVtoGrid[%s]" % i)
            PVtoGrid.append(vars.x)
            vars = model.getVarByName("eBatttoGrid[%s]" % i)
            BatttoGrid.append(vars.x)
            vars = model.getVarByName("eGridtoBatt[%s]" % i)
            GridtoBatt.append(vars.x)
            vars = model.getVarByName("eStorage[%s]" % i)
            BatteryState.append(vars.x)
            vars = model.getVarByName("eGridtoLoad[%s]" % i)
            GridtoLoad.append(vars.x)

        ans = DataFrame(
            {
                "Prices": pri,
                "load": load,
                "PV": PV,
                "Feed in": FeedIn,
                "Battery State (kW)": BatteryState,
                "Energy PV to Batt (kW)": PVtoBatt,
                "Energy PV to Load (kW)": PVtoLoad,
                "Energy PV to Grid (kW)": PVtoGrid,
                "Energy Battery to Grid (kW)": BatttoGrid,
                "Energy Battery to Load (kW)": BatttoLoad,
                "Energy Grid to Load (kW)": GridtoLoad,
                "Energy Grid to Batt (kW)": GridtoBatt,
            },
        )

        ans = ans[
            [
                "Prices",
                "load",
                "PV",
                "Feed in",
                "Battery State (kW)",
                "Energy PV to Batt (kW)",
                "Energy PV to Load (kW)",
                "Energy PV to Grid (kW)",
                "Energy Battery to Grid (kW)",
                "Energy Battery to Load (kW)",
                "Energy Grid to Load (kW)",
                "Energy Grid to Batt (kW)",
            ]
        ]

        self.energyStorage = BatteryState  # used for SFI
        self.revenue = (
            np.dot(self._policy.FIT, PVtoGrid)
            + np.dot(self._input.price_list, BatttoGrid)
            - np.dot(self._policy.retailElectricity, GridtoLoad)
            - np.dot(self._policy.retailElectricity, GridtoBatt)
        )
        self.sumEnergyFromGrid = np.array(GridtoLoad) + np.array(
            GridtoBatt
        )  # used for avoided network costs
        self.sumEnergyToGrid = np.array(PVtoGrid) + np.array(BatttoGrid)
        self.deltaBatt = sum(np.array(BatttoGrid) - np.array(GridtoBatt))
        self.PVtoGrid = sum(PVtoGrid)
        self.GridtoLoad = sum(GridtoLoad)
        self.referenceRevenue = np.dot(
            -self._policy.retailElectricity, self._input.loadList
        )
        return (
            ans,
            model.objVal,
        )  # function returns results as DataFrame and the value of objective function
