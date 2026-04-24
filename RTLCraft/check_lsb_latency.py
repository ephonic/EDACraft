import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from examples.montgomery_mult_384 import LSBMult128Pipe

dut = LSBMult128Pipe()
sim = Simulator(dut)
sim.reset('rst_n')
sim.set("a", 1)
sim.set("b", 1)
sim.set("ready_in", 1)
sim.set("valid_in", 1)
sim.step()
sim.set("valid_in", 0)

for cycle in range(1, 15):
    sim.step()
    if sim.get("valid_out"):
        print(f"LSBMult128Pipe latency = {cycle} cycles, prod_lo = {hex(sim.get('prod_lo'))}")
        break
