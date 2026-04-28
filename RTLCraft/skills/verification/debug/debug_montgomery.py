#!/usr/bin/env python3
"""
Debug example for MontgomeryMult384 using rtlgen.pipeline.DebugProbe.

This script demonstrates how to hierarchically trace signals across
submodules without manually writing nested get() calls.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from rtlgen.pipeline import DebugProbe
from examples.montgomery_mult_384 import MontgomeryMult384


def main():
    dut = MontgomeryMult384()
    sim = Simulator(dut)
    probe = DebugProbe(sim)

    sim.reset('rst_n')
    sim.set("o_ready", 1)

    # Two back-to-back transactions with different moduli
    M0 = (1 << 383) | 1
    Mp0 = 0x1
    X0 = 0x123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0
    Y0 = 0xfedcba09876543210fedcba09876543210fedcba09876543210fedcba098765

    M1 = 0xabcd1234f1a3fbd483b4eec8acf56789abcdef0123456789abcdef0123456789 | (1 << 383) | 1
    Mp1 = ((-pow(M1, -1, 1 << 384)) % (1 << 128)) & ((1 << 128) - 1)
    X1 = 0x1111111111111111111111111111111111111111111111111111111111111111
    Y1 = 0x2222222222222222222222222222222222222222222222222222222222222222

    sim.set("X", X0); sim.set("Y", Y0); sim.set("M", M0); sim.set("M_prime", Mp0)
    sim.set("i_valid", 1); sim.step()

    sim.set("X", X1); sim.set("Y", Y1); sim.set("M", M1); sim.set("M_prime", Mp1)
    sim.step()

    sim.set("i_valid", 0)

    # Trace key pipeline events
    print("Tracing MontgomeryMult384 pipeline events...\n")
    for c in range(2, 65):
        sim.step()

        ov = probe.get("o_valid")
        if ov:
            z = probe.get("Z")
            print(f"=== cycle {c}: OUTPUT Z={hex(z)} ===\n")

        # Print r0 stage events
        r0v = probe.get("r0_valid")
        if r0v and c < 30:
            print(f"cycle {c}: r0_valid=1")

        # Hierarchical peek into first RedUnit128
        if c == 23:
            r0_path, r0_sim = probe.find_subsim("u_r0")
            print(f"cycle {c}: [u_r0] qvd5={r0_sim.get('qv_d5')} qvd6={r0_sim.get('qv_d6')} "
                  f"outv={r0_sim.get('out_valid')} qm2={hex(r0_sim.get('qm2'))}")

        # Print top-level valid chain
        s8v = probe.get("s8_valid")
        r0vr = probe.get("r0_valid_r")
        r1v = probe.get("r1_valid")
        r1vr = probe.get("r1_valid_r")
        r2v = probe.get("r2_valid")
        r2vr = probe.get("r2_valid_r")
        if any([s8v, r0vr, r1v, r1vr, r2v, r2vr]) and not ov:
            print(f"cycle {c}: s8v={s8v} r0vr={r0vr} r1v={r1v} r1vr={r1vr} r2v={r2v} r2vr={r2vr}")


if __name__ == "__main__":
    main()
