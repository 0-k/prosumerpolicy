from model import Model

m = Model()

# example case to evaluate market alignment indicator of PV-battery system of size 5 kW / 5 kWh

m.PV.size = 5
m.Battery.size = 0.2

m.policy.isVFIT = True
m.policy.isRTP = True
m.policy.isFixedNetworkCharges = True

print(m.MAI)
