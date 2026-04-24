import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from examples.montgomery_mult_384 import MontgomeryMult384
from tests.test_montgomery_mult_384 import modinv, ref_montgomery
import random

random.seed(2024)
M = random.getrandbits(384) | 1
M |= (1 << 383)
X0 = random.randint(0, M - 1)
Y0 = random.randint(0, M - 1)
Mp = (-modinv(M, 1 << 128)) % (1 << 128)

# Second input
X1 = random.randint(0, M - 1)
Y1 = random.randint(0, M - 1)

exp0 = ref_montgomery(X0, Y0, M)
exp1 = ref_montgomery(X1, Y1, M)

dut = MontgomeryMult384()
sim = Simulator(dut)
sim.reset('rst_n')
sim.set("o_ready", 1)
sim.set("M", M)
sim.set("M_prime", Mp)

results = []

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

for cycle in range(3, 80):
    sim.step()
    if sim.get("o_valid"):
        results.append(sim.get("Z"))
        print(f"Result at cycle {cycle}: {hex(sim.get('Z'))}")
        if len(results) == 2:
            break

print(f"Expected: {hex(exp0)}, {hex(exp1)}")
print(f"Got:      {hex(results[0]) if len(results) > 0 else 'N/A'}, {hex(results[1]) if len(results) > 1 else 'N/A'}")
print(f"Match 0: {results[0] == exp0 if len(results) > 0 else False}")
print(f"Match 1: {results[1] == exp1 if len(results) > 1 else False}")
