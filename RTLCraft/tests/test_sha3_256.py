#!/usr/bin/env python3
"""Basic directed sanity test for SHA3_256 pipe (no UVM)."""

import hashlib
import sys

sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from examples.sha3_256_pipe import SHA3_256


def run_sha3_test(dut, msg_bytes):
    sim = Simulator(dut)

    # Reset
    sim.set("rst_n", 0)
    sim.set("i_valid", 0)
    sim.set("o_ready", 1)
    sim.set("block", 0)
    sim.set("block_len", 0)
    sim.set("last_block", 0)
    for _ in range(3):
        sim.step()
    sim.set("rst_n", 1)
    sim.step()

    block_val = int.from_bytes(msg_bytes, "little")
    sim.set("block", block_val)
    sim.set("block_len", len(msg_bytes))
    sim.set("last_block", 1)
    sim.set("i_valid", 1)
    sim.step()
    sim.set("i_valid", 0)

    # Wait up to 30 cycles for output
    for _ in range(30):
        sim.step()
        if int(sim.get("o_valid")):
            break
    else:
        raise RuntimeError("Timeout waiting for o_valid")

    hash_val = int(sim.get("hash"))
    expected = int.from_bytes(hashlib.sha3_256(msg_bytes).digest(), "little")
    return hash_val, expected


def test_sha3_256():
    dut = SHA3_256()
    vectors = [
        b"",
        b"abc",
        b"hello world",
        bytes(range(135)),
    ]
    for msg in vectors:
        actual, expected = run_sha3_test(dut, msg)
        assert actual == expected, f"Mismatch for msg={msg!r}: actual={actual:064x}, expected={expected:064x}"
        print(f"[PASS] msg_len={len(msg):3d} -> hash={actual:064x}")
    print("\nAll SHA3-256 tests passed!")


if __name__ == "__main__":
    test_sha3_256()
