from prosumerpolicy.model import Model
import matplotlib.pyplot as plt

m = Model()

# example case to evaluate market alignment indicator of PV-battery system of size 5 kW / 5 kWh

m.PV.size = 5
m.Battery.size = 0.2

m.policy.isVFIT = False
m.policy.is_rtp = False
m.policy.is_fixed_network_charges = False

m.timeDuration = 8760

print(m.opt)


