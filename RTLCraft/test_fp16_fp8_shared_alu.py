#!/usr/bin/env python3
"""
Simulation & Cosim test for FP16/FP8 shared pipelined ALU.
"""

import sys, math, struct
sys.path.insert(0, "/home/yangfan/EDAClaw/rtlgen")

from rtlgen import Simulator
from rtlgen.cosim import CosimRunner
from fp16_fp8_shared_alu import FP16FP8SharedALU, BIAS

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
    if math.isnan(f):
        return fp8_pack(0, 31, 1)
    if math.isinf(f):
        return fp8_pack(0 if f > 0 else 1, 31, 0)
    if f == 0.0:
        return fp8_pack(0 if math.copysign(1, f) > 0 else 1, 0, 0)
    sign = 0 if f > 0 else 1
    f = abs(f)
    u32 = struct.unpack('>I', struct.pack('>f', f))[0]
    f32_exp = ((u32 >> 23) & 0xFF) - 127
    f32_mant = u32 & 0x7FFFFF
    new_exp = f32_exp + BIAS
    if new_exp <= 0:
        return fp8_pack(sign, 0, 0)
    if new_exp >= 31:
        return fp8_pack(sign, 31, 0)
    mant_bits = (1 << 23) | f32_mant
    val = (mant_bits >> 21) & 0x3
    guard = (mant_bits >> 20) & 1
    if guard:
        val += 1
    if val >= 4:
        val = 0
        new_exp += 1
        if new_exp >= 31:
            return fp8_pack(sign, 31, 0)
    return fp8_pack(sign, new_exp, val)

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
# FP16 E5M10 helpers
# ---------------------------------------------------------------------------
def fp16_pack(sign, exp, mant):
    return (sign << 15) | (exp << 10) | (mant & 0x3FF)

def fp16_unpack(val):
    sign = (val >> 15) & 1
    exp = (val >> 10) & 0x1F
    mant = val & 0x3FF
    return sign, exp, mant

def fp16_from_float(f):
    if math.isnan(f):
        return fp16_pack(0, 31, 1)
    if math.isinf(f):
        return fp16_pack(0 if f > 0 else 1, 31, 0)
    if f == 0.0:
        return fp16_pack(0 if math.copysign(1, f) > 0 else 1, 0, 0)
    sign = 0 if f > 0 else 1
    f = abs(f)
    u32 = struct.unpack('>I', struct.pack('>f', f))[0]
    f32_exp = ((u32 >> 23) & 0xFF) - 127
    f32_mant = u32 & 0x7FFFFF
    new_exp = f32_exp + BIAS
    if new_exp <= 0:
        return fp16_pack(sign, 0, 0)
    if new_exp >= 31:
        return fp16_pack(sign, 31, 0)
    mant_bits = (1 << 23) | f32_mant
    val = (mant_bits >> 13) & 0x3FF
    guard = (mant_bits >> 12) & 1
    if guard:
        val += 1
    if val >= 1024:
        val = 0
        new_exp += 1
        if new_exp >= 31:
            return fp16_pack(sign, 31, 0)
    return fp16_pack(sign, new_exp, val)

def fp16_to_float(val):
    sign, exp, mant = fp16_unpack(val)
    if exp == 31 and mant != 0:
        return float('nan')
    if exp == 31 and mant == 0:
        return math.copysign(float('inf'), 1 - 2 * sign)
    if exp == 0 and mant == 0:
        return 0.0 * (1 - 2 * sign)
    hidden = 0 if exp == 0 else 1
    real_exp = 1 - BIAS if exp == 0 else exp - BIAS
    real_mant = (hidden << 10) | mant
    return math.copysign(real_mant / 1024.0 * (2.0 ** real_exp), 1 - 2 * sign)

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

def run_sim_tests():
    dut = FP16FP8SharedALU()
    sim = Simulator(dut)
    sim.reset('rst_n')
    sim.set("o_ready", 1)

    test_vectors = [
        # FP8 tests (fmt=0)
        (0, 1.0, 1.0, OP_ADD, 2.0, "fp8 1+1=2"),
        (0, 1.5, 2.0, OP_MUL, 3.0, "fp8 1.5*2=3"),
        (0, 1.0, 2.0, OP_CMP_LT, 1, "fp8 1<2"),
        (0, 2.0, 1.0, OP_CMP_LT, 0, "fp8 2<1 false"),
        (0, 1.0, 2.0, OP_MAX, 2.0, "fp8 max(1,2)=2"),
        (0, 1.0, 2.0, OP_MIN, 1.0, "fp8 min(1,2)=1"),
        (0, float('inf'), float('-inf'), OP_ADD, float('nan'), "fp8 inf-inf=nan"),
        (0, float('nan'), 1.0, OP_ADD, float('nan'), "fp8 nan+1=nan"),
        (0, 3.0, 1.0, OP_SUB, 2.0, "fp8 3-1=2"),
        # FP16 tests (fmt=1)
        (1, 1.0, 1.0, OP_ADD, 2.0, "fp16 1+1=2"),
        (1, 1.5, 2.0, OP_MUL, 3.0, "fp16 1.5*2=3"),
        (1, 1.0, 2.0, OP_CMP_LT, 1, "fp16 1<2"),
        (1, 2.0, 1.0, OP_CMP_LT, 0, "fp16 2<1 false"),
        (1, 1.0, 2.0, OP_MAX, 2.0, "fp16 max(1,2)=2"),
        (1, 1.0, 2.0, OP_MIN, 1.0, "fp16 min(1,2)=1"),
        (1, float('inf'), float('-inf'), OP_ADD, float('nan'), "fp16 inf-inf=nan"),
        (1, float('nan'), 1.0, OP_ADD, float('nan'), "fp16 nan+1=nan"),
        (1, 3.0, 1.0, OP_SUB, 2.0, "fp16 3-1=2"),
        # Mixed precision conceptual: FP8 inputs through FP16 path
        (0, 0.5, 0.5, OP_ADD, 1.0, "fp8 0.5+0.5=1"),
        (1, 0.5, 0.5, OP_ADD, 1.0, "fp16 0.5+0.5=1"),
    ]

    LATENCY = 3
    results = []

    for fmt, a_f, b_f, op, _, comment in test_vectors:
        if fmt == 0:
            a_val = fp8_from_float(a_f)
            b_val = fp8_from_float(b_f)
        else:
            a_val = fp16_from_float(a_f)
            b_val = fp16_from_float(b_f)
        sim.set("a", a_val)
        sim.set("b", b_val)
        sim.set("op", op)
        sim.set("fmt", fmt)
        sim.set("i_valid", 1)
        sim.step()
        if sim.get("o_valid"):
            results.append((sim.get("result"), sim.get("flags"), fmt))

    sim.set("i_valid", 0)
    for _ in range(LATENCY + len(test_vectors)):
        sim.step()
        if sim.get("o_valid"):
            results.append((sim.get("result"), sim.get("flags"), sim.get("result") >> 15))

    print(f"Captured {len(results)} result(s), expected {len(test_vectors)}")
    assert len(results) == len(test_vectors), f"Result count mismatch: {len(results)} vs {len(test_vectors)}"

    ok = True
    for i, ((r, flags, got_fmt), (fmt, a_f, b_f, op, expected, comment)) in enumerate(zip(results, test_vectors)):
        if op in (OP_CMP_LT, OP_CMP_EQ):
            actual = r & 1
            expected_int = expected
            match = (actual == expected_int)
            actual_str = f"{actual}"
            expected_str = f"{expected_int}"
        else:
            if fmt == 0:
                actual_f = fp8_to_float(r & 0xFF)
            else:
                actual_f = fp16_to_float(r & 0xFFFF)
            if isinstance(expected, float) and math.isnan(expected):
                match = math.isnan(actual_f)
            else:
                match = (actual_f == expected)
            actual_str = f"{actual_f}"
            expected_str = f"{expected}"

        status = "PASS" if match else "FAIL"
        if not match:
            ok = False
        print(f"[{status}] {comment:30s} -> result=0x{r:04x} ({actual_str:10s}) expected {expected_str:10s} flags=0x{flags:x}")

    if ok:
        print("\nAll simulation tests passed!")
    else:
        print("\nSome simulation tests FAILED!")
        sys.exit(1)


def run_cosim_tests():
    """Run iverilog cosim with a subset of vectors."""
    vectors = []
    # FP8 vectors
    for fmt in [0, 1]:
        for a_f, b_f, op in [
            (1.0, 1.0, OP_ADD),
            (1.5, 2.0, OP_MUL),
            (1.0, 2.0, OP_CMP_LT),
            (2.0, 1.0, OP_MAX),
            (3.0, 1.0, OP_SUB),
        ]:
            if fmt == 0:
                a_val = fp8_from_float(a_f)
                b_val = fp8_from_float(b_f)
            else:
                a_val = fp16_from_float(a_f)
                b_val = fp16_from_float(b_f)
            vectors.append({"a": a_val, "b": b_val, "op": op, "fmt": fmt, "o_ready": 1})

    CosimRunner(FP16FP8SharedALU(), vectors, mode="seq").run(verbose=True)
    print("Cosim tests passed!")


if __name__ == "__main__":
    run_sim_tests()
    run_cosim_tests()
