"""Generate and run an iverilog testbench for the Barrett multiplier.

The emitted RTL is checked directly against the golden Python reference model.
Test vectors (operand sets + the matching Barrett constant) are precomputed in
Python and embedded into the testbench.

Usage:
    python crypto/barrett128/tests/iverilog_cosim.py
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO))

from rtlgen_x.dsl import VerilogEmitter  # noqa: E402
from crypto.barrett128 import BarrettModMul  # noqa: E402
from crypto.barrett128.reference import K, barrett_constant, modmul  # noqa: E402

BUILD = _REPO / "crypto" / "barrett128" / "build" / "iverilog"
BUILD.mkdir(parents=True, exist_ok=True)

N_FULL = (1 << 127) | 0x123456789ABCDEF0123456789ABCDEF
M_FULL = barrett_constant(N_FULL)


def _vhex(value: int, width: int) -> str:
    return f"{width}'h{value & ((1 << width) - 1):X}"


def build_vectors(count: int, seed: int) -> list:
    rng = random.Random(seed)
    vecs = []
    for _ in range(count):
        a = rng.getrandbits(K)
        b = rng.getrandbits(K)
        exp = modmul(a, b, N_FULL, M_FULL)
        vecs.append((a, b, exp))
    return vecs


def generate_tb(vecs, latency: int) -> str:
    submits = []
    for a, b, _ in vecs:
        submits.append(f"    submit({_vhex(a,128)}, {_vhex(b,128)}, N, M);")
    expects = [exp for _, _, exp in vecs]

    # Build the expected-value array initialization.
    exp_lines = "\n".join(f"    expected[{i}] = {_vhex(e,128)};" for i, e in enumerate(expects))

    submit_block = "\n".join(
        f"    submit_one({_vhex(a,128)}, {_vhex(b,128)});\n"
        f"    drain_and_check(expected[{i}]);"
        for i, (a, b, _) in enumerate(vecs)
    )

    return textwrap.dedent(f"""\
`timescale 1ns/1ps
module tb_barrett;
  reg clk, rst, in_valid;
  reg [127:0] a, b, n;
  reg [128:0] m;
  wire in_accept, out_valid;
  wire [127:0] r;

  barrett_mod_mul dut(
    .clk(clk), .rst(rst), .in_valid(in_valid),
    .a(a), .b(b), .n(n), .m(m),
    .in_accept(in_accept), .out_valid(out_valid), .r(r)
  );

  always #5 clk = ~clk;

  integer errors, checked, submitted, collect_idx;
  reg [127:0] expected [0:255];

  task submit;
    input [127:0] aa, bb, nn;
    input [128:0] mm;
    begin
      // hold inputs stable for the negedge before this posedge
      @(negedge clk);
      a = aa; b = bb; n = nn; m = mm; in_valid = 1;
      @(negedge clk);
      in_valid = 0; a = 0; b = 0;
      submitted = submitted + 1;
    end
  endtask

  wire [127:0] N = {_vhex(N_FULL,128)};
  wire [128:0] M = {_vhex(M_FULL,129)};

  // Drive one op: operands stable across one rising edge with in_valid=1.
  task submit_one;
    input [127:0] aa, bb;
    begin
      @(negedge clk);
      a = aa; b = bb; n = N; m = M; in_valid = 1;
      @(negedge clk);
      in_valid = 0; a = 0; b = 0;
    end
  endtask

  // After submitting, drain exactly LATENCY cycles then read the result.
  task drain_and_check;
    input [127:0] expval;
    begin
      repeat ({latency}) @(negedge clk);
      if (!out_valid) begin
        $display("VALID_MISS idx=%0d got_r=0x%032x exp=0x%032x", checked, r, expval);
        errors = errors + 1;
      end else if (r !== expval) begin
        $display("MISMATCH idx=%0d got=0x%032x exp=0x%032x", checked, r, expval);
        errors = errors + 1;
      end else begin
        checked = checked + 1;
      end
    end
  endtask

  initial begin
    clk = 0; rst = 1; in_valid = 0; a = 0; b = 0; n = 0; m = 0;
    errors = 0; checked = 0; submitted = 0;
    @(negedge clk); @(negedge clk);
    rst = 0;
    @(negedge clk);

{exp_lines}

{submit_block}

    $display("RESULT checked=%0d errors=%0d", checked, errors);
    if (errors == 0 && checked == {len(vecs)}) $display("IVERILOG_PASS");
    else $display("IVERILOG_FAIL");
    $finish;
  end
endmodule
""")


def emit_rtl() -> Path:
    src = VerilogEmitter().emit(BarrettModMul())
    out = BUILD / "barrett_mod_mul.v"
    out.write_text(src, encoding="utf-8")
    return out


def run(vec_count: int = 64, seed: int = 20260620, latency: int | None = None) -> bool:
    rtl = emit_rtl()
    vecs = build_vectors(vec_count, seed)
    eff_latency = BarrettModMul.LATENCY if latency is None else latency
    tb_src = generate_tb(vecs, eff_latency)
    tb_path = BUILD / "tb_barrett.v"
    tb_path.write_text(tb_src, encoding="utf-8")

    vvp = BUILD / "tb.vvp"
    compile_cmd = ["iverilog", "-g2012", "-o", str(vvp), str(rtl), str(tb_path)]
    cp = subprocess.run(compile_cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        print("iverilog compile FAILED:\n", cp.stderr)
        return False

    run_cmd = ["vvp", str(vvp)]
    rp = subprocess.run(run_cmd, capture_output=True, text=True)
    print(f"[latency={eff_latency}] " + rp.stdout.strip().replace("\n", " | "))
    return "IVERILOG_PASS" in rp.stdout


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        found = None
        for lat in range(0, 9):
            ok = run(vec_count=8, seed=1, latency=lat)
            if ok:
                found = lat
                break
        print(f"\nScan result: first matching latency = {found}")
        sys.exit(0 if found is not None else 1)
    ok = run()
    sys.exit(0 if ok else 1)
