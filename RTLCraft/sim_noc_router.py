"""NoC Router simulation test."""
import sys
sys.path.insert(0, "/Users/yangfan/release/EDACraft-main/RTLCraft")

from rtlgen.dsl_parser import parse_dsl_code
from rtlgen.sim import Simulator

from rtlgen.dsl_parser import load_dsl_module

result = load_dsl_module("generated_skill_ppa/riscv64_soc/code/NoCRouter_0.py")
assert result.success, f"Import failed: {result.errors}"
mod = result.module
sim = Simulator(mod)

def make_flit(dest_x, dest_y, payload):
    return (dest_x << 56) | (dest_y << 48) | (payload & 0xFF)

def drive_idle():
    for port in ["n", "s", "e", "w", "j"]:
        sim.poke(f"{port}_valid", 0)
        sim.poke(f"{port}_ready", 0)
        sim.poke(f"{port}_flit", 0)

passed = 0
failed = 0

def report(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name} {detail}")

# ── Test 1: Reset compliance ──
sim.reset(rst="rst_n", cycles=3)
drive_idle()
r = {sig: sim.peek(sig) for sig in
     ["n_valid_out", "s_valid_out", "e_valid_out", "w_valid_out", "j_valid_out",
      "n_ready_out", "s_ready_out", "e_ready_out", "w_ready_out", "j_ready_out"]}
report("Reset: all outputs zero", all(v == 0 for v in r.values()))

# ── Test 2: E→J (local, dest=(0,0)) ──
sim.reset(rst="rst_n", cycles=1)
drive_idle()
sim.poke("e_valid", 1)
sim.poke("e_flit", make_flit(0, 0, 0x77))
sim.poke("j_ready", 1)
sim.step()
report("E→J: valid=1", sim.peek("j_valid_out") == 1)
report("E→J: flit=0x77", sim.peek("j_flit_out") == 0x77,
       f"got 0x{sim.peek('j_flit_out'):x}")

# ── Test 3: N→E (dest_x > x_pos) ──
sim.reset(rst="rst_n", cycles=1)
drive_idle()
sim.poke("n_valid", 1)
sim.poke("n_flit", make_flit(1, 0, 0xAA))
sim.poke("e_ready", 1)
sim.step()
report("N→E: valid=1", sim.peek("e_valid_out") == 1)
report("N→E: flit=0xAA", sim.peek("e_flit_out") == 0xAA,
       f"got 0x{sim.peek('e_flit_out'):x}")

# ── Test 4: S→J (local) ──
sim.reset(rst="rst_n", cycles=1)
drive_idle()
sim.poke("s_valid", 1)
sim.poke("s_flit", make_flit(0, 0, 0xBB))
sim.poke("j_ready", 1)
sim.step()
report("S→J: valid=1", sim.peek("j_valid_out") == 1)
report("S→J: flit=0xBB", sim.peek("j_flit_out") == 0xBB,
       f"got 0x{sim.peek('j_flit_out'):x}")

# ── Test 5: W→E (dest_x > x_pos) ──
sim.reset(rst="rst_n", cycles=1)
drive_idle()
sim.poke("w_valid", 1)
sim.poke("w_flit", make_flit(2, 0, 0xCC))
sim.poke("e_ready", 1)
sim.step()
report("W→E: valid=1", sim.peek("e_valid_out") == 1)
report("W→E: flit=0xCC", sim.peek("e_flit_out") == 0xCC,
       f"got 0x{sim.peek('e_flit_out'):x}")

# ── Test 6: N→S (dest_y > y_pos) ──
sim.reset(rst="rst_n", cycles=1)
drive_idle()
sim.poke("n_valid", 1)
sim.poke("n_flit", make_flit(0, 3, 0xDD))
sim.poke("s_ready", 1)
sim.step()
report("N→S: valid=1", sim.peek("s_valid_out") == 1)
report("N→S: flit=0xDD", sim.peek("s_flit_out") == 0xDD,
       f"got 0x{sim.peek('s_flit_out'):x}")

# ── Test 7: Backpressure + release ──
sim.reset(rst="rst_n", cycles=1)
drive_idle()
sim.poke("e_valid", 1)
sim.poke("e_flit", make_flit(0, 0, 0xEE))
sim.poke("j_ready", 0)  # backpressure
sim.step()
report("Backpressure: buffer retains flit", sim.peek("e_buf_count") == 1,
       f"got {sim.peek('e_buf_count')}")

# Release: keep e_valid=0 (no new push), set j_ready=1
sim.poke("e_valid", 0)
sim.poke("j_ready", 1)
# Check BEFORE step: buffer should still have the flit
report("Before release step: buffer has flit", sim.peek("e_buf_count") == 1)
sim.step()
# After step: buffer drained (pop happened), flit was consumed
report("After release step: buffer drained", sim.peek("e_buf_count") == 0,
       f"got {sim.peek('e_buf_count')}")

# ── Test 8: Arbitration — two inputs, same output ──
sim.reset(rst="rst_n", cycles=1)
drive_idle()
sim.poke("n_valid", 1)
sim.poke("n_flit", make_flit(0, 0, 0x11))  # N→J
sim.poke("e_valid", 1)
sim.poke("e_flit", make_flit(0, 0, 0x22))  # E→J
sim.poke("j_ready", 1)
sim.step()
j_flit = sim.peek("j_flit_out")
report("Arbitration: N wins for J (priority)", j_flit == 0x11,
       f"got 0x{j_flit:x}")

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
