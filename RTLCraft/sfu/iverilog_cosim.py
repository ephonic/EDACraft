"""Iverilog cosim harness for the FP16 SFU emitted RTL."""

from __future__ import annotations

import random
import subprocess
import textwrap
from pathlib import Path

from rtlgen_x.dsl import VerilogEmitter

from sfu.driver import ALL_OPS
from sfu.dsl import Fp16Sfu
from sfu.reference import eval_fp16_sfu_scalar


REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "sfu" / "build" / "iverilog"
BUILD.mkdir(parents=True, exist_ok=True)


def _vhex(value: int, width: int) -> str:
    return f"{width}'h{value & ((1 << width) - 1):X}"


def _artifact_stem(prefix: str, *parts: object) -> str:
    suffix = "_".join(str(part) for part in parts)
    return f"{prefix}_{suffix}" if suffix else prefix


def build_vectors(count: int, seed: int) -> list[tuple[int, int, int]]:
    rng = random.Random(seed)
    vectors = []
    for _ in range(count):
        op = rng.choice(ALL_OPS)
        operand = rng.randrange(0, 1 << 16)
        vectors.append((op, operand, eval_fp16_sfu_scalar(op, operand)))
    return vectors


def directed_vectors() -> list[tuple[int, int, int]]:
    cases = [
        (0, 0xBC00),
        (0, 0x3C00),
        (1, 0x3C00),
        (2, 0xBC00),
        (3, 0x3C00),
        (4, 0x3C00),
        (3, 0x0000),
        (4, 0x0000),
        (1, 0x7C00),
        (2, 0xFC00),
    ]
    return [(op, operand, eval_fp16_sfu_scalar(op, operand)) for op, operand in cases]


def emit_rtl(tag: str = "fp16_sfu") -> Path:
    src = VerilogEmitter().emit(Fp16Sfu())
    out = BUILD / f"{tag}.v"
    out.write_text(src, encoding="utf-8")
    return out


def generate_tb(vecs: list[tuple[int, int, int]], latency: int) -> str:
    expect_lines = "\n".join(f"    expected[{i}] = {_vhex(exp, 16)};" for i, (_, _, exp) in enumerate(vecs))
    submit_lines = "\n".join(
        f"    submit_back_to_back({_vhex(op, 3)}, {_vhex(operand, 16)});" for op, operand, _ in vecs
    )
    return textwrap.dedent(
        f"""\
`timescale 1ns/1ps
module tb_fp16_sfu;
  reg clk, rst, in_valid;
  reg [2:0] op;
  reg [15:0] operand;
  wire in_accept, out_valid;
  wire [15:0] result;

  fp16_sfu dut(
    .clk(clk), .rst(rst), .in_valid(in_valid),
    .op(op), .operand(operand),
    .in_accept(in_accept), .out_valid(out_valid), .result(result)
  );

  always #5 clk = ~clk;

  integer errors, checked, collected;
  reg [15:0] expected [0:{len(vecs) - 1}];

  task submit_back_to_back;
    input [2:0] op_i;
    input [15:0] operand_i;
    begin
      @(negedge clk);
      op = op_i;
      operand = operand_i;
      in_valid = 1;
    end
  endtask

  task finalize_stream;
    begin
      @(negedge clk);
      op = 0;
      operand = 0;
      in_valid = 0;
    end
  endtask

  task drain_and_check_stream;
    integer max_cycles;
    begin
      max_cycles = {len(vecs)} + {latency} + 8;
      while (collected < {len(vecs)} && max_cycles > 0) begin
        @(negedge clk);
        if (out_valid) begin
          if (result !== expected[collected]) begin
            $display("MISMATCH idx=%0d got=0x%04x exp=0x%04x", collected, result, expected[collected]);
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
    clk = 0; rst = 1; in_valid = 0; op = 0; operand = 0;
    errors = 0; checked = 0; collected = 0;
    @(negedge clk); @(negedge clk);
    rst = 0;
    @(negedge clk);

{expect_lines}

    fork
      begin
{submit_lines}
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
"""
    )


def run(vecs: list[tuple[int, int, int]], *, latency: int | None = None, tag: str = "stream") -> bool:
    eff_latency = Fp16Sfu.LATENCY if latency is None else latency
    stem = _artifact_stem("fp16_sfu", tag, len(vecs), eff_latency)
    rtl = emit_rtl(f"{stem}_rtl")
    tb_path = BUILD / f"{stem}_tb.v"
    tb_path.write_text(generate_tb(vecs, eff_latency), encoding="utf-8")

    vvp = BUILD / f"{stem}.vvp"
    compile_cmd = ["iverilog", "-g2012", "-o", str(vvp), str(rtl), str(tb_path)]
    cp = subprocess.run(compile_cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        print("iverilog compile FAILED:\n", cp.stderr)
        return False

    rp = subprocess.run(["vvp", str(vvp)], capture_output=True, text=True)
    print(f"[{tag}] " + rp.stdout.strip().replace("\n", " | "))
    return "IVERILOG_PASS" in rp.stdout


if __name__ == "__main__":
    ok = run(directed_vectors(), tag="directed")
    ok = run(build_vectors(128, 20260621), tag="random128") and ok
    raise SystemExit(0 if ok else 1)
