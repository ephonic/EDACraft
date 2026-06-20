"""Generate and run an iverilog testbench for the Barrett multiplier.

The emitted RTL is checked directly against the golden Python reference model.
Test vectors (operand sets + the matching Barrett constant) are precomputed in
Python and embedded into the testbench.

The main ``run()`` path drives a back-to-back input stream (throughput 1) and
checks each output when ``out_valid`` asserts, so this covers the real
fully-pipelined contract rather than only a one-shot transaction.

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


def _artifact_stem(prefix: str, *parts: object) -> str:
    suffix = "_".join(str(part) for part in parts)
    return f"{prefix}_{suffix}" if suffix else prefix


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
    expects = [exp for _, _, exp in vecs]

    # Build the expected-value array initialization.
    exp_lines = "\n".join(f"    expected[{i}] = {_vhex(e,128)};" for i, e in enumerate(expects))

    submit_block = "\n".join(
        f"    submit_back_to_back({_vhex(a,128)}, {_vhex(b,128)});"
        for a, b, _ in vecs
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

  integer errors, checked, collected;
  reg [127:0] expected [0:{len(vecs) - 1}];

  wire [127:0] N = {_vhex(N_FULL,128)};
  wire [128:0] M = {_vhex(M_FULL,129)};

  // Canonical streaming pattern: drive operands/in_valid on a negedge so the
  // following posedge cleanly samples the transaction into S0.
  task submit_back_to_back;
    input [127:0] aa, bb;
    begin
      @(negedge clk);
      a = aa; b = bb; n = N; m = M; in_valid = 1;
    end
  endtask

  task finalize_stream;
    begin
      @(negedge clk);
      in_valid = 0; a = 0; b = 0; n = 0; m = 0;
    end
  endtask

  task drain_and_check_stream;
    integer max_cycles;
    begin
      // Guard the drain loop with a few extra cycles beyond the nominal
      // pipeline latency so the TB reports a clean VALID_MISS on regressions.
      max_cycles = {len(vecs)} + {latency} + 6;
      while (collected < {len(vecs)} && max_cycles > 0) begin
        @(negedge clk);
        if (out_valid) begin
          if (r !== expected[collected]) begin
            $display("MISMATCH idx=%0d got=0x%032x exp=0x%032x", collected, r, expected[collected]);
            errors = errors + 1;
          end else begin
            checked = checked + 1;
          end
          collected = collected + 1;
        end
        max_cycles = max_cycles - 1;
      end
      if (collected != {len(vecs)}) begin
        $display("VALID_MISS collected=%0d expected=%0d", collected, {len(vecs)});
        errors = errors + 1;
      end
    end
  endtask

  initial begin
    clk = 0; rst = 1; in_valid = 0; a = 0; b = 0; n = 0; m = 0;
    errors = 0; checked = 0; collected = 0;
    @(negedge clk); @(negedge clk);
    rst = 0;
    @(negedge clk);

{exp_lines}

    fork
      begin
{submit_block}
        finalize_stream();
      end
      begin
        drain_and_check_stream();
      end
    join

    $display("RESULT checked=%0d errors=%0d collected=%0d", checked, errors, collected);
    if (errors == 0 && checked == {len(vecs)}) $display("IVERILOG_PASS");
    else $display("IVERILOG_FAIL");
    $finish;
  end
endmodule
""")


def emit_rtl(tag: str = "barrett_mod_mul") -> Path:
    src = VerilogEmitter().emit(BarrettModMul())
    out = BUILD / f"{tag}.v"
    out.write_text(src, encoding="utf-8")
    return out


def run(vec_count: int = 64, seed: int = 20260620, latency: int | None = None) -> bool:
    vecs = build_vectors(vec_count, seed)
    eff_latency = BarrettModMul.LATENCY if latency is None else latency
    tag = _artifact_stem("barrett", vec_count, seed, eff_latency)
    rtl = emit_rtl(f"{tag}_rtl")
    tb_src = generate_tb(vecs, eff_latency)
    tb_path = BUILD / f"{tag}_tb.v"
    tb_path.write_text(tb_src, encoding="utf-8")

    vvp = BUILD / f"{tag}.vvp"
    compile_cmd = ["iverilog", "-g2012", "-o", str(vvp), str(rtl), str(tb_path)]
    cp = subprocess.run(compile_cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        print("iverilog compile FAILED:\n", cp.stderr)
        return False

    run_cmd = ["vvp", str(vvp)]
    rp = subprocess.run(run_cmd, capture_output=True, text=True)
    print(f"[latency={eff_latency}] " + rp.stdout.strip().replace("\n", " | "))
    return "IVERILOG_PASS" in rp.stdout


def measure_latency(seed: int = 1, max_cycles: int = 16) -> int | None:
    """Measure latency in the same convention as ``BarrettModMul.LATENCY``.

    The reported value is the number of post-submission drain cycles needed
    before ``out_valid`` becomes observable.
    """
    tag = _artifact_stem("barrett_latency", seed, max_cycles)
    rtl = emit_rtl(f"{tag}_rtl")
    a, b, exp = build_vectors(1, seed)[0]
    tb_src = textwrap.dedent(f"""\
`timescale 1ns/1ps
module tb_barrett_latency;
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

  wire [127:0] N = {_vhex(N_FULL,128)};
  wire [128:0] M = {_vhex(M_FULL,129)};

  always #5 clk = ~clk;

  integer cyc;
  initial begin
    clk = 0; rst = 1; in_valid = 0; a = 0; b = 0; n = 0; m = 0; cyc = 0;
    @(negedge clk); @(negedge clk);
    rst = 0;
    @(negedge clk);
    a = {_vhex(a,128)}; b = {_vhex(b,128)}; n = N; m = M; in_valid = 1;
    @(negedge clk);
    in_valid = 0; a = 0; b = 0; n = 0; m = 0;
    repeat ({max_cycles}) begin
      @(negedge clk);
      cyc = cyc + 1;
      if (out_valid) begin
        $display("LATENCY %0d GOT 0x%032x EXP 0x%032x", cyc, r, {_vhex(exp,128)});
        $finish;
      end
    end
    $display("LATENCY NONE");
    $finish;
  end
endmodule
""")
    tb_path = BUILD / f"{tag}_tb.v"
    tb_path.write_text(tb_src, encoding="utf-8")
    vvp = BUILD / f"{tag}.vvp"
    cp = subprocess.run(["iverilog", "-g2012", "-o", str(vvp), str(rtl), str(tb_path)], capture_output=True, text=True)
    if cp.returncode != 0:
        print("iverilog compile FAILED:\n", cp.stderr)
        return None
    rp = subprocess.run(["vvp", str(vvp)], capture_output=True, text=True)
    for line in rp.stdout.splitlines():
        if line.startswith("LATENCY "):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        found = measure_latency(seed=1, max_cycles=16)
        print(f"\nScan result: measured latency = {found}")
        sys.exit(0 if found is not None else 1)
    ok = run()
    sys.exit(0 if ok else 1)
