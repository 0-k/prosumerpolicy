from prosumerpolicy.model import Model
import matplotlib.pyplot as plt

m = Model()

# example case to evaluate market alignment indicator of PV-battery system of size 5 kW / 5 kWh

m.pv.size = 5
m.battery.size = 0.2

m.policy.is_vfit = False
m.policy.is_rtp = False
m.policy.is_fixed_network_charges = False

m.time_duration = 8760

print(m.opt)


