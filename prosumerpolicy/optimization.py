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
            self._policy.is_vfit = vfit
        if capacity is None:
            pass
        else:
            self._policy.is_fixed_network_charges = capacity
        if not self._policy.is_rtp and not self._policy.is_vfit:
            return self._bau()
        else:
            return self._optimizer_dispatch()

    def _optimize_arbitrage(self):
        """

        Function takes Maximum Charge Capacity, Max Discharge Capacity, BatterySize, number of hours and
        a random number generator  and price curve as input

        returns maximum revenue along with hourly Energy dispatch from grid,Energy dispatch to grid and battery state

        Complete foresight, linear optimization done with GUROBI SOLVER

        """
        self.arbitrage_state = True
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

    def _bau(self):
        logging.info(
            "Business as Usual: Day {}, Time Duration {}, PV Size {} ".format(
                self._input.day,
                self._input.time_duration,
                self._input.pv.size,
            )
        )
        self._optimization_status = 1

        if self._policy.is_fixed_network_charges:
            self.optimization_state = "BAU Capacity"
        else:
            self.optimization_state = "BAU Volumetric"

        length = min(
            len(self._input.pv_gen_list), len(self._input.load_list)
        )  # in case the inputs  are not the same length, use the smaller.
        batt_state, energy_from_grid, energy_to_grid, cases = (
            [],
            [],
            [],
            [],
        )  # Create Return Variables
        xi = self._input.pv_gen_list[:length] - self._input.load_list[:length]
        battStateATBeg = []
        # All Efficiencies are taken with reference to the battery. if battery discharges 1kwh, this means it actually gives
        # etaDischarge*1kwh to the grid...if battery charges by 1 kwh, this means it took 1kwh/etacharge from the grid/pv
        battery_state = self._input.battery.initial_battery_capacity
        for item in xi:
            battAtBeg = battery_state * (1 - self._input.battery.self_discharge)
            battery_state *= 1 - self._input.battery.self_discharge
            if item <= 0:
                e_to_grid = 0
                if (
                    abs(item)
                    <= min(
                        battery_state,
                        self._input.battery.maximum_charge_discharge_capacity,
                    )
                    * self._input.battery.discharge_efficiency
                ):
                    battery_state = battery_state - (
                        abs(item) / self._input.battery.discharge_efficiency
                    )
                    e_from_grid = 0
                elif (
                    abs(item)
                    > min(
                        battery_state,
                        self._input.battery.maximum_charge_discharge_capacity,
                    )
                    * self._input.battery.discharge_efficiency
                ):
                    e_from_grid = (
                        abs(item)
                        - min(
                            battery_state,
                            self._input.battery.maximum_charge_discharge_capacity,
                        )
                        * self._input.battery.discharge_efficiency
                    )
                    battery_state = battery_state - (
                        min(
                            battery_state,
                            self._input.battery.maximum_charge_discharge_capacity,
                        )
                    )
            else:
                e_from_grid = 0
                if (
                    item
                    >= min(
                        (self._input.battery.size - battery_state),
                        self._input.battery.maximum_charge_discharge_capacity,
                    )
                    / self._input.battery.charge_efficiency
                ):
                    e_to_grid = (
                        item
                        - min(
                            (self._input.battery.size - battery_state),
                            self._input.battery.maximum_charge_discharge_capacity,
                        )
                        / self._input.battery.charge_efficiency
                    )
                    battery_state = battery_state + min(
                        (self._input.battery.size - battery_state),
                        self._input.battery.maximum_charge_discharge_capacity,
                    )
                else:
                    battery_state = (
                        battery_state + item * self._input.battery.charge_efficiency
                    )
                    e_to_grid = 0

            batt_state.append(battery_state)
            energy_from_grid.append(e_from_grid)
            energy_to_grid.append(e_to_grid)
            battStateATBeg.append(battAtBeg)

        ans = pd.DataFrame(
            {
                "Price": self._policy.retail_electricity,
                "load (kW)": self._input.load_list,
                "PV Generation": self._input.pv_gen_list,
                "Battery State (kW)": batt_state,
                "Energy from the grid (kW)": energy_from_grid,
                "Energy into the grid (kW)": energy_to_grid,
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
        energy_to_grid = np.array(energy_to_grid)
        energy_from_grid = np.array(energy_from_grid)

        revenue = (
            np.dot(self._policy.fit, energy_to_grid)
            - np.dot(self._policy.retail_electricity, energy_from_grid)
            + self._policy.fit[0] * battery_state
        )

        self.energy_to_grid_bau = energy_to_grid
        self.energy_from_grid_bau = energy_from_grid
        self.energy_storage = batt_state
        self.revenue = revenue
        self.reference_revenue = np.dot(
            -self._policy.retail_electricity, self._input.load_list
        )
        self.direct_use = self._input.pv_gen_list - energy_to_grid
        self.direct_use = sum(self.direct_use) - battery_state

        return ans

    def _optimizer_dispatch(self):
        self._optimization_status = 2
        if self._policy.is_fixed_network_charges:
            capacity = " Capacity"
        else:
            capacity = " Volumetric"

        if self._policy.is_rtp and not self._policy.is_vfit:
            self.optimization_state = "RTP and Fixed FIT" + capacity
        elif self._policy.is_rtp and self._policy.is_vfit:
            self.optimization_state = "RTP and Variable FIT" + capacity
        elif not self._policy.is_rtp and self._policy.is_vfit:
            self.optimization_state = "Fixed Price and Variable FIT" + capacity
        logging.info(
            "Real Time Pricing Optimization: Day {}, Time Duration {}, PV Size {} ".format(
                self._input.day,
                self._input.time_duration,
                self._input.pv.size,
            )
        )  # Getting config
        wholesale_price = self._input.price_list
        pri = self._policy.retail_electricity
        load = self._input.load_list
        PV = self._input.pv_gen_list
        feed_in = self._policy.fit
        optimization_duration = self._input.time_duration
        model = Model("RTP_withForesight")  # Create Gurobi Model
        model.setParam("OutputFlag", 0)
        (
            e_storage,
            e_pv_to_batt,
            e_pv_to_load,
            e_pv_to_grid,
            e_batt_to_grid,
            e_batt_to_load,
            e_grid_to_load,
            e_grid_to_batt,
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
            e_pv_to_batt[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                / self._input.battery.charge_efficiency,
                name="e_p_vto_batt[%s]" % j,
            )
            e_batt_to_load[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                * self._input.battery.discharge_efficiency,
                name="e_batt_to_load[%s]" % j,
            )
            e_pv_to_load[j] = model.addVar(vtype="C", lb=0, name="ePVtoLoad[%s]" % j)
            e_pv_to_grid[j] = model.addVar(vtype="C", lb=0, name="e_pv_to_grid[%s]" % j)
            e_batt_to_grid[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                * self._input.battery.discharge_efficiency,
                name="e_battto_grid[%s]" % j,
            )
            e_grid_to_batt[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.maximum_charge_discharge_capacity
                / self._input.battery.charge_efficiency,
                name="e_grid_to_batt[%s]" % j,
            )
            e_storage[j] = model.addVar(
                vtype="C",
                lb=0,
                ub=self._input.battery.size,
                name="e_storage[%s]" % j,
            )
            e_grid_to_load[j] = model.addVar(
                vtype="C", lb=0, name="e_grid_to_load[%s]" % j
            )

        model.update()

        model.setObjective(
            sum(
                e_batt_to_grid[j] * wholesale_price[j]
                - e_grid_to_batt[j] * pri[j]
                + feed_in[j] * e_pv_to_grid[j]
                - pri[j] * e_grid_to_load[j]
                for j in range(optimization_duration)
            ),
            GRB.MAXIMIZE,
        )  # set objective function maximizing revenue
        for i in range(
            optimization_duration
        ):  # Adding energy constraints for length of optimization_duration
            if i == 0:  # intial value
                model.addConstr(
                    e_storage[i]
                    - self._input.battery.initial_battery_capacity
                    * (1 - self._input.battery.self_discharge)
                    - e_pv_to_batt[i] * self._input.battery.charge_efficiency
                    - e_grid_to_batt[i] * self._input.battery.charge_efficiency
                    + e_batt_to_load[i] / self._input.battery.discharge_efficiency
                    + e_batt_to_grid[i] / self._input.battery.discharge_efficiency
                    == 0
                )
            else:
                model.addConstr(
                    e_storage[i]
                    - e_storage[i - 1] * (1 - self._input.battery.self_discharge)
                    - e_pv_to_batt[i] * self._input.battery.charge_efficiency
                    - e_grid_to_batt[i] * self._input.battery.charge_efficiency
                    + e_batt_to_load[i] / self._input.battery.discharge_efficiency
                    + e_batt_to_grid[i] / self._input.battery.discharge_efficiency
                    == 0
                )
            model.addConstr(
                e_pv_to_load[i] + e_pv_to_batt[i] + e_pv_to_grid[i] == PV[i]
            )
            model.addConstr(
                e_grid_to_load[i] + e_batt_to_load[i] + e_pv_to_load[i] == load[i]
            )
            model.addConstr(
                e_batt_to_grid[i]
                <= self._input.battery.maximum_charge_discharge_capacity
                * y[i]
                * self._input.battery.discharge_efficiency
            )
            model.addConstr(
                e_grid_to_batt[i]
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
            pv_to_grid,
            PVtoLoad,
            PVtoBatt,
            BatttoLoad,
            batt_to_grid,
            BatteryState,
            grid_to_load,
            grid_to_batt,
        ) = ([], [], [], [], [], [], [], [])
        for i in range(optimization_duration):
            vars = model.getVarByName("e_p_vto_batt[%s]" % i)
            PVtoBatt.append(vars.x)
            vars = model.getVarByName("e_batt_to_load[%s]" % i)
            BatttoLoad.append(vars.x)
            vars = model.getVarByName("ePVtoLoad[%s]" % i)
            PVtoLoad.append(vars.x)
            vars = model.getVarByName("e_pv_to_grid[%s]" % i)
            pv_to_grid.append(vars.x)
            vars = model.getVarByName("e_battto_grid[%s]" % i)
            batt_to_grid.append(vars.x)
            vars = model.getVarByName("e_grid_to_batt[%s]" % i)
            grid_to_batt.append(vars.x)
            vars = model.getVarByName("e_storage[%s]" % i)
            BatteryState.append(vars.x)
            vars = model.getVarByName("e_grid_to_load[%s]" % i)
            grid_to_load.append(vars.x)

        ans = pd.DataFrame(
            {
                "Prices": pri,
                "load": load,
                "PV": PV,
                "Feed in": feed_in,
                "Battery State (kW)": BatteryState,
                "Energy PV to Batt (kW)": PVtoBatt,
                "Energy PV to Load (kW)": PVtoLoad,
                "Energy PV to Grid (kW)": pv_to_grid,
                "Energy Battery to Grid (kW)": batt_to_grid,
                "Energy Battery to Load (kW)": BatttoLoad,
                "Energy Grid to Load (kW)": grid_to_load,
                "Energy Grid to Batt (kW)": grid_to_batt,
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

        self.energy_storage = BatteryState  # used for SFI
        self.revenue = (
            np.dot(self._policy.fit, pv_to_grid)
            + np.dot(self._input.price_list, batt_to_grid)
            - np.dot(self._policy.retail_electricity, grid_to_load)
            - np.dot(self._policy.retail_electricity, grid_to_batt)
        )
        self.sum_energy_from_grid = np.array(grid_to_load) + np.array(
            grid_to_batt
        )  # used for avoided network costs
        self.sum_energy_to_grid = np.array(pv_to_grid) + np.array(batt_to_grid)
        self.delta_batt = sum(np.array(batt_to_grid) - np.array(grid_to_batt))
        self.pv_to_grid = sum(pv_to_grid)
        self.grid_to_load = sum(grid_to_load)
        self.reference_revenue = np.dot(
            -self._policy.retail_electricity, self._input.load_list
        )
        return (
            ans,
            model.objVal,
        )  # function returns results as DataFrame and the value of objective function
