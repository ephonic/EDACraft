#!/usr/bin/env python3
"""
Simulation test for FP8 (E5M2) pipelined ALU.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from examples.fp8e5m2_alu_pipe import FP8ALU, BIAS

# ---------------------------------------------------------------------------
# FP8 E5M2 helpers
# ---------------------------------------------------------------------------
def fp8_pack(sign, exp, mant):
    return (sign << 7) | (exp << 2) | (mant & 0x3)

def fp8_unpack(val):
    sign = (val >> 7) & 1
    exp = (val >> 2) & 0x1F
    mant = val & 0x3
    return sign, exp, mant

def fp8_from_float(f):
    """Crude float -> FP8 E5M2 conversion for test vectors."""
    import math
    if math.isnan(f):
        return fp8_pack(0, 31, 1)
    if math.isinf(f):
        return fp8_pack(0 if f > 0 else 1, 31, 0)
    if f == 0.0:
        return fp8_pack(0 if math.copysign(1, f) > 0 else 1, 0, 0)
    sign = 0 if f > 0 else 1
    f = abs(f)
    import struct
    # Use float32 as intermediate
    f32 = struct.unpack('>I', struct.pack('>f', f))[0]
    f32_sign = (f32 >> 31) & 1
    f32_exp = ((f32 >> 23) & 0xFF) - 127
    f32_mant = f32 & 0x7FFFFF
    # Convert to FP8 E5M2
    new_exp = f32_exp + BIAS
    if new_exp <= 0:
        return fp8_pack(sign, 0, 0)  # underflow to zero for simplicity
    if new_exp >= 31:
        return fp8_pack(sign, 31, 0)  # overflow to inf
    # Mantissa: top 2 bits of float32 mantissa + hidden 1
    hidden = 1
    mant_bits = (hidden << 23) | f32_mant
    # Position relative to FP8: we want 1.xx, so shift mant_bits right by 21
    fp8_mant = (mant_bits >> 21) & 0x3
    # Round half up using next bit
    guard = (mant_bits >> 20) & 1
    if guard:
        fp8_mant += 1
        if fp8_mant >= 4:
            fp8_mant = 0
            new_exp += 1
            if new_exp >= 31:
                return fp8_pack(sign, 31, 0)
    return fp8_pack(sign, new_exp, fp8_mant)

def fp8_to_float(val):
    sign, exp, mant = fp8_unpack(val)
    if exp == 31 and mant != 0:
        return float('nan')
    if exp == 31 and mant == 0:
        return math.copysign(float('inf'), 1 - 2 * sign)
    if exp == 0 and mant == 0:
        return 0.0 * (1 - 2 * sign)
    hidden = 0 if exp == 0 else 1
    real_exp = 1 - BIAS if exp == 0 else exp - BIAS
    real_mant = (hidden << 2) | mant
    return math.copysign(real_mant / 4.0 * (2.0 ** real_exp), 1 - 2 * sign)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
OP_ADD = 0
OP_SUB = 1
OP_MUL = 2
OP_MIN = 3
OP_MAX = 4
OP_CMP_LT = 5
OP_CMP_EQ = 6

def run_tests():
    dut = FP8ALU()
    sim = Simulator(dut)
    sim.reset('rst_n')

    # Drive constant controls
    sim.set("o_ready", 1)

    test_vectors = [
        # (a_f, b_f, op, expected_result_f_or_int, comment)
        (1.0, 1.0, OP_ADD, 2.0, "1+1=2"),
        (1.5, 2.0, OP_MUL, 3.0, "1.5*2=3"),
        (1.0, 2.0, OP_CMP_LT, 1, "1<2"),
        (2.0, 1.0, OP_CMP_LT, 0, "2<1 false"),
        (1.0, 2.0, OP_MAX, 2.0, "max(1,2)=2"),
        (1.0, 2.0, OP_MIN, 1.0, "min(1,2)=1"),
        (float('inf'), float('-inf'), OP_ADD, float('nan'), "inf-inf=nan"),
        (float('nan'), 1.0, OP_ADD, float('nan'), "nan+1=nan"),
        (3.0, 1.0, OP_SUB, 2.0, "3-1=2"),
    ]

    # Latency = 3 cycles
    LATENCY = 3
    results = []

    # Send all inputs and collect outputs on the fly
    for a_f, b_f, op, _, comment in test_vectors:
        a_val = fp8_from_float(a_f)
        b_val = fp8_from_float(b_f)
        sim.set("a", a_val)
        sim.set("b", b_val)
        sim.set("op", op)
        sim.set("i_valid", 1)
        sim.step()
        if sim.get("o_valid"):
            results.append((sim.get("result"), sim.get("flags")))

    # Flush pipeline
    sim.set("i_valid", 0)
    for _ in range(LATENCY + len(test_vectors)):
        sim.step()
        if sim.get("o_valid"):
            results.append((sim.get("result"), sim.get("flags")))

    print(f"Captured {len(results)} result(s), expected {len(test_vectors)}")
    assert len(results) == len(test_vectors), f"Result count mismatch: {len(results)} vs {len(test_vectors)}"

    ok = True
    for i, ((r, flags), (a_f, b_f, op, expected, comment)) in enumerate(zip(results, test_vectors)):
        if op in (OP_CMP_LT, OP_CMP_EQ):
            actual = r & 1
            expected_int = expected
            match = (actual == expected_int)
            actual_str = f"{actual}"
            expected_str = f"{expected_int}"
        else:
            actual_f = fp8_to_float(r)
            if isinstance(expected, float) and math.isnan(expected):
                match = math.isnan(actual_f)
            else:
                match = (actual_f == expected)
            actual_str = f"{actual_f}"
            expected_str = f"{expected}"

        status = "PASS" if match else "FAIL"
        if not match:
            ok = False
        print(f"[{status}] {comment:20s} -> result=0x{r:02x} ({actual_str:10s}) expected {expected_str:10s} flags=0x{flags:x}")

    if ok:
        print("\nAll tests passed!")
    else:
        print("\nSome tests FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    import math
    run_tests()
