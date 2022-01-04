import math
import numpy as np
from paths import *


class Economics:

    def __init__(self,input,policy,optimize):
        self.__InputSetter = input
        self.__Policy = policy
        self.__Optimize = optimize
        self.PV = self.__InputSetter.PV
        self.Battery = self.__InputSetter.Battery
        self.__IRR = None
        self.__NPV = None
        self._autarky = None
        self._selfConsumption = None
        self._avoidedNetworkFees= None
        self._isOptimizeYear=False
        self._set_economic_parameters_from_file()

    def _set_economic_parameters_from_file(self, path=None):
        ''' reads PV parameter from file in Path and updates attributes '''
        if path is None:
            path = gen_Path(path_parameters)
        parameters = read_parameters(path)['Economics']
        self.__discount = float(parameters['discount'])
        self.__lifetime = int(parameters['lifetime'])
        self._invest_PV =float(parameters['invest_PV'])
        self._invest_Bat = float(parameters['invest_Bat'])
        self.__oAndM_PV = float(parameters['oAndM_PV'])
        self.__oAndM_Bat = float(parameters['oAndM_Bat'])
        self.__VAT = float(parameters['VAT'])
        self.__scalingFactorPV = float(parameters['scalingFactorPV'])
        self.__scalingFactorBattery = float(parameters['scalingFactorBattery'])
        self.__optimizationForesightHours=int(parameters['optimizationForesightHours'])

    def __pvInitialCost(self):
        ''' Calculates initial cost of PV '''
        if self.PV.size == 0:
            initialCostperKW = 0
        else:
            initialCostperKW = self._invest_PV * (self.PV.size / 10) ** self.__scalingFactorPV
        initialCostPV = self.PV.size * initialCostperKW
        return initialCostPV

    def __batteryInitialCost(self):
        ''' Calculates initial cost of Battery '''
        if self.Battery.size == 0:
            initialCostperKW = 0
        else:
            initialCostperKW = self._invest_Bat * (self.Battery.size / 10) ** self.__scalingFactorBattery
        initialCostBattery = self.Battery.size * initialCostperKW
        return initialCostBattery

    def _calculateAvoidedNetworkFees(self):
        ''' calculates avoided network fees'''
        if self.__Policy.isFixedNetworkCharges: #all capacity-based network charges are conserved
            avoidedNetworkFees = 0
            return avoidedNetworkFees

        elif self.__Optimize._optimizationStatus == 1: #BAU #TODO Enums
            selfProduced = self.__InputSetter.loadList - self.__Optimize.energyFromGridBAU
            avoidedNetworkFees = sum(selfProduced) * self.__Policy.networkCharge
            return avoidedNetworkFees
        elif self.__Optimize._optimizationStatus == 2:  #Non-BAU
            selfProduced = self.__InputSetter.loadList - self.__Optimize.sumEnergyFromGrid
            avoidedNetworkFees = sum(selfProduced) * self.__Policy.networkCharge
            return avoidedNetworkFees

    def _calculateNPV(self, discount=None):
        if discount is None:
            discount = self.__discount
        PV = self.__pvInitialCost()
        Bat = self.__batteryInitialCost()
        cost = (-PV - Bat) * self.__VAT   #initial investment in year 0
        logging.info('Net Present Value for {} years calculated'.format(self.__lifetime))
        if self.numOfCycles==0:
            batteryYear=100
        else:
            batteryYear = self.Battery.totalBatteryCycles / self.numOfCycles  # number of years to change battery.
            batteryYear = int(batteryYear)
        for year in range(1, int(self.__lifetime+1)):
            refYearCost = self.referenceTotal/math.pow(1.0+discount, year)
            if year == batteryYear:
                logging.warning('Battery is Changed')
                yearCost = self.revenueTotal - self.__oAndM_PV * PV - Bat * self.__VAT * self.Battery.replacementCostFactor
            else:
                yearCost = self.revenueTotal - self.__oAndM_PV * PV - self.__oAndM_Bat * Bat
            yearCost = yearCost/math.pow(1.0 + discount, year)
            cost += yearCost-refYearCost
        return cost

    def _calculateIRR(self):
        x0 = -0.05
        x1 = -0.2
        x2 = -1
        i = 0
        threshold = 0.5
        solDelta = 100 * threshold
        validRun = False
        for i in range(100):
            try:
                x2 = x1 - (x1 - x0) / (self._calculateNPV(discount=x1) -
                                       self._calculateNPV(discount=x0)) * self._calculateNPV(discount=x1)
                solDelta = self._calculateNPV(discount=x2)
                x0 = x1
                x1 = x2
                if (abs(solDelta) < threshold):
                    validRun=True
                    return x2
            except OverflowError:
                logging.warning("IRR Divergent")
                break
        if not validRun:
            return -0.25


    def _calculate_battery_counts(self):
        '''    calculates battery counts   '''
        tot = np.array(self.batteryTotal)
        tot1 = np.insert(tot, 0, self.Battery.initialBatteryCapacity)
        tot1 = np.delete(tot1, -1)
        diff = tot-tot1
        numOfCycles = 0
        z = 0
        for i in diff:
            z += abs(i)
            if z >= 2 * self.Battery.size:
                z = z - 2 * self.Battery.size
                numOfCycles += 1
        return numOfCycles

    def _calculate_CSC(self): #charging State Correlator
        ''' calculates system friendliness indicator. After optimization of existing case the arbitrage case is optimized for entire year'''
        day=self.__InputSetter.day
        self.__InputSetter.day = 1
        time = self.__InputSetter.timeDuration
        self.__InputSetter.timeDuration=8760
        self.__Optimize._optimize_arbitrage()
        if not self._isOptimizeYear:
            self.optimizeYear()
        arbitrageCharging = self._calculate_battery_state(self.__Optimize.energyStorageArbitrage)
        optimizeCharging = self._calculate_battery_state(self.energyStorage)
        logging.info(
            'System Friendliness Indicator for Arbitrage and {} calculated '.format(self.__Optimize.optimizationState))
        assert len(arbitrageCharging) == len(optimizeCharging)
        diff = 1 - sum(
            (arbitrageCharging[i] - optimizeCharging[i]) ** 2 for i in range(len(arbitrageCharging))) / (
                       2 * len(arbitrageCharging))
        self.__InputSetter.timeDuration = time
        self.__InputSetter.day=day
        return diff

    def _calculate_MAI(self):
        day = self.__InputSetter.day
        self.__InputSetter.day = 1
        time = self.__InputSetter.timeDuration
        self.__InputSetter.timeDuration=8760
        self.__Optimize._optimize_arbitrage()
        if not self._isOptimizeYear:
            self.optimizeYear()
        self.welfareBattery=self.welfareBatteryPV-self.welfarePV-self.welfareConsumption
        self.welfareRef=np.dot(self.__Optimize.energyToGridArbitrage-self.__Optimize.energyFromGridArbitrage
                               ,self.__InputSetter.get_price_list(day=1, duration=8760))
        self.__InputSetter.timeDuration = time
        self.__InputSetter.day = day
        return self.welfareBattery/self.welfareRef

    def optimizeYear(self):
        self.revenueTotal=0
        self.referenceTotal=0
        self.batteryTotal=[]
        self.pvTotal=0
        self.fedin=0
        self.fromGrid=0
        self.consumptionYear=0
        self.totalDirectUse=0
        self.totalAvoidedNetworkFees=0
        self.maximumBATT=0
        self.deltaBattGrid=[]
        self.welfarePV = 0
        self.welfareConsumption = 0
        self.welfareBatteryPV = 0
        if not self.__Policy.isRTP and not self.__Policy.isVFIT: #BAU Case
            time=self.__InputSetter.timeDuration
            self.__InputSetter.timeDuration=8760
            self.__Optimize.optimize()
            self.revenueTotal=self.__Optimize.revenue
            self.referenceTotal=self.__Optimize.referenceRevenue
            self.totalAvoidedNetworkFees=self._calculateAvoidedNetworkFees()
            self.batteryTotal=self.__Optimize.energyStorage
            self.pvTotal=sum(self.__InputSetter.pvGenList)
            self.consumptionYear=sum(self.__InputSetter.loadList)
            self.welfarePV+=np.dot(self.__InputSetter.pvGenList,self.__InputSetter.get_price_list())
            self.welfareConsumption -= np.dot(self.__InputSetter.loadList, self.__InputSetter.get_price_list())
            self.welfareBatteryPV+=-np.dot(self.__Optimize.energyFromGridBAU,self.__InputSetter.get_price_list())+\
                np.dot(self.__Optimize.energyToGridBAU,self.__InputSetter.get_price_list())
            self.__InputSetter.timeDuration=time
        else:
            for d in range(1,366):
                self.__InputSetter.timeDuration=24
                self.__InputSetter.day=d
                self.__Optimize.optimize()
                self.deltaBattGrid.append(self.__Optimize.deltaBatt)
                self.fedin+=self.__Optimize.PVtoGrid
                self.fromGrid+=self.__Optimize.GridtoLoad
                self.revenueTotal+=self.__Optimize.revenue
                self.referenceTotal+=self.__Optimize.referenceRevenue
                self.batteryTotal+=(self.__Optimize.energyStorage)
                self.totalAvoidedNetworkFees+=self._calculateAvoidedNetworkFees()
                self.pvTotal+=sum(self.__InputSetter.pvGenList)
                self.consumptionYear+=sum(self.__InputSetter.loadList)
                self.welfarePV+=np.dot(self.__InputSetter.pvGenList,self.__InputSetter.get_price_list())
                self.welfareConsumption-=np.dot(self.__InputSetter.loadList, self.__InputSetter.get_price_list())
                self.welfareBatteryPV+=-np.dot(self.__Optimize.sumEnergyFromGrid,self.__InputSetter.get_price_list())+\
                np.dot(self.__Optimize.sumEnergyToGrid, self.__InputSetter.get_price_list())
            self.energyStorage=self.batteryTotal
        self.numOfCycles=self._calculate_battery_counts()
        self.revenueTotal-=self.__Policy.fixedCapacity
        self.referenceTotal-=self.__Policy.fixedCapacity

    def _calculate_battery_state(self,energyStorage):
        energyStorage = np.array(energyStorage)
        energyStorage = np.insert(energyStorage, 0, self.Battery.size)
        stateDiff = np.diff(energyStorage)
        for i in range(len(stateDiff)):
            stateDiff[i] = round(stateDiff[i], 3)
            if stateDiff[i] > 0:
                stateDiff[i] = 1
            elif stateDiff[i] < -self.Battery.selfDischarge * self.Battery.size * 1.05:
                stateDiff[i] = -1
            else:
                stateDiff[i] = 0
        return stateDiff


