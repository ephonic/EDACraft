import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from examples.montgomery_mult_384 import MontgomeryMult384
import random

random.seed(2024)
M = random.getrandbits(384) | 1
M |= (1 << 383)
X0 = random.randint(0, M - 1)
Y0 = random.randint(0, M - 1)
X1 = random.randint(0, M - 1)
Y1 = random.randint(0, M - 1)
Mp = (-pow(M, -1, 1 << 128)) % (1 << 128)

# Expected KO-3 products
def ko3_products(X, Y):
    x = [(X >> (i * 128)) & ((1 << 128) - 1) for i in range(3)]
    y = [(Y >> (i * 128)) & ((1 << 128) - 1) for i in range(3)]
    p0 = x[0] * y[0]
    p1 = x[1] * y[1]
    p2 = x[2] * y[2]
    p01 = (x[0] + x[1]) * (y[0] + y[1])
    p02 = (x[0] + x[2]) * (y[0] + y[2])
    p12 = (x[1] + x[2]) * (y[1] + y[2])
    z0 = p0
    z1 = p01 - p0 - p1
    z2 = p02 - p0 - p2 + p1
    z3 = p12 - p1 - p2
    z4 = p2
    return z0, z1, z2, z3, z4

exp_z0_0, exp_z1_0, exp_z2_0, exp_z3_0, exp_z4_0 = ko3_products(X0, Y0)
exp_z0_1, exp_z1_1, exp_z2_1, exp_z3_1, exp_z4_1 = ko3_products(X1, Y1)

dut = MontgomeryMult384()
sim = Simulator(dut)
sim.reset('rst_n')
sim.set("o_ready", 1)
sim.set("M", M)
sim.set("M_prime", Mp)

# Input 0
sim.set("X", X0)
sim.set("Y", Y0)
sim.set("i_valid", 1)
sim.step()

# Input 1
sim.set("X", X1)
sim.set("Y", Y1)
sim.step()

sim.set("i_valid", 0)

for cycle in range(3, 20):
    sim.step()
    s8v = sim.get("s8_valid")
    if s8v:
        z0 = sim.get_int("s8_Z0_r")
        z1 = sim.get_int("s8_Z1_r")
        z2 = sim.get_int("s8_Z2_r")
        z3 = sim.get_int("s8_Z3_r")
        z4 = sim.get_int("s8_Z4_r")
        print(f"cycle {cycle}: s8_valid=1")
        print(f"  Z0={hex(z0)} expected={hex(exp_z0_0) if cycle < 10 else hex(exp_z0_1)}")
        print(f"  Z1={hex(z1)} expected={hex(exp_z1_0) if cycle < 10 else hex(exp_z1_1)}")
        print(f"  Z2={hex(z2)} expected={hex(exp_z2_0) if cycle < 10 else hex(exp_z2_1)}")
        print(f"  Z3={hex(z3)} expected={hex(exp_z3_0) if cycle < 10 else hex(exp_z3_1)}")
        print(f"  Z4={hex(z4)} expected={hex(exp_z4_0) if cycle < 10 else hex(exp_z4_1)}")
