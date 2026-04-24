import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from examples.montgomery_mult_384 import MontgomeryMult384
from tests.test_montgomery_mult_384 import modinv, ref_montgomery
import random

def redunit128_signed(Z0, Z1, Z2, Z3, Z4, M0, M1, M2, Mp):
    def to_signed(val, bits):
        if val >= (1 << (bits - 1)):
            return val - (1 << bits)
        return val
    q = ((Z0 & ((1 << 128) - 1)) * Mp) & ((1 << 128) - 1)
    z0_full = Z0 + q * M0
    carry = z0_full >> 128
    Z1_s = to_signed(Z1, 263)
    Z2_s = to_signed(Z2, 260)
    Z3_s = to_signed(Z3, 260)
    Z4_s = to_signed(Z4, 257)
    z0_sum = carry + Z1_s + q * M1
    out_Z0 = z0_sum & ((1 << 265) - 1)
    z1_sum = Z2_s + q * M2
    out_Z1 = z1_sum & ((1 << 261) - 1)
    out_Z2 = Z3_s & ((1 << 260) - 1)
    out_Z3 = Z4_s & ((1 << 257) - 1)
    return out_Z0, out_Z1, out_Z2, out_Z3

def ref_hw(X, Y, M, Mp):
    x = [(X >> (i * 128)) & ((1 << 128) - 1) for i in range(3)]
    y = [(Y >> (i * 128)) & ((1 << 128) - 1) for i in range(3)]
    m = [(M >> (i * 128)) & ((1 << 128) - 1) for i in range(3)]
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
    z0, z1, z2, z3 = redunit128_signed(z0, z1, z2, z3, z4, m[0], m[1], m[2], Mp)
    z4 = 0
    z0, z1, z2, z3 = redunit128_signed(z0, z1, z2, z3, z4, m[0], m[1], m[2], Mp)
    z4 = 0
    z0, z1, z2, z3 = redunit128_signed(z0, z1, z2, z3, z4, m[0], m[1], m[2], Mp)
    result = (z1 << 128) + z0
    result = result & ((1 << 384) - 1)
    if result >= M:
        result -= M
    return result

random.seed(2024)
M = random.getrandbits(384) | 1
M |= (1 << 383)
X = random.randint(0, M - 1)
Y = random.randint(0, M - 1)
Mp = (-modinv(M, 1 << 128)) % (1 << 128)

dut = MontgomeryMult384()
sim = Simulator(dut)
sim.reset('rst_n')
sim.set("o_ready", 1)
sim.set("X", X)
sim.set("Y", Y)
sim.set("M", M)
sim.set("M_prime", Mp)
sim.set("i_valid", 1)
sim.step()
sim.set("i_valid", 0)

for cycle in range(1, 70):
    sim.step()
    s8v = sim.get("s8_valid")
    r0vr = sim.get("r0_valid_r")
    r1vr = sim.get("r1_valid_r")
    r2vr = sim.get("r2_valid_r")
    ov = sim.get("o_valid")
    if s8v or r0vr or r1vr or r2vr or ov:
        print(f"cycle {cycle:2d}: s8v={s8v} r0vr={r0vr} r1vr={r1vr} r2vr={r2vr} ov={ov}")
    if ov:
        print(f"  First o_valid at cycle {cycle}")
        break
