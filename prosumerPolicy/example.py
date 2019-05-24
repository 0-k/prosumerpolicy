from model import Model

m = Model()

# example case to evaluate market alignment indicator of PV-battery system of size 5 kW / 5 kWh

m.PV.size = 5
m.Battery.size = 5

m.Policy.isVFIT = False
m.Policy.isRTP = False
m.Policy.isFixedNetworkCharges = False

print(m.MAI)