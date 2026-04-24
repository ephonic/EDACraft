import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import random
from rtlgen import Simulator
from examples.montgomery_mult_384 import MontgomeryMult384
from tests.test_montgomery_mult_384 import modinv, ref_montgomery

LATENCY = 53

random.seed(2024)
dut = MontgomeryMult384()
sim = Simulator(dut)
sim.reset('rst_n')
sim.set("o_ready", 1)

inputs = []
expected = []
for _ in range(50):
    M = random.getrandbits(384) | 1
    M |= (1 << 383)
    X = random.randint(0, M - 1)
    Y = random.randint(0, M - 1)
    Mp = (-modinv(M, 1 << 128)) % (1 << 128)
    inputs.append((X, Y, M, Mp))
    expected.append(ref_montgomery(X, Y, M))

results = []
cycle = 0
for X, Y, M, Mp in inputs:
    sim.set("X", X)
    sim.set("Y", Y)
    sim.set("M", M)
    sim.set("M_prime", Mp)
    sim.set("i_valid", 1)
    sim.step()
    cycle += 1
    if sim.get("o_valid"):
        results.append(sim.get("Z"))

sim.set("i_valid", 0)
for _ in range(LATENCY + 10):
    sim.step()
    cycle += 1
    if sim.get("o_valid"):
        results.append(sim.get("Z"))

print(f"Total results: {len(results)}, expected: {len(expected)}")

mismatches = 0
for i, (exp, act) in enumerate(zip(expected, results)):
    if exp != act:
        mismatches += 1

print(f"Total mismatches: {mismatches}")
for i in [0, 25, 49]:
    exp = expected[i]
    act = results[i]
    match = "MATCH" if exp == act else "MISMATCH"
    print(f"Vector {i}: {match}")
    if exp != act:
        print(f"  expected: {hex(exp)}")
        print(f"  actual:   {hex(act)}")
