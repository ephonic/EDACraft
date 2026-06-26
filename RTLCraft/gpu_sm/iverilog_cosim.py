"""Iverilog cosim harness for the GPU SM emitted RTL.

The harness builds a vector program, computes expected writeback transactions
with the golden reference model, and drives the emitted RTL through iverilog to
verify cycle-by-cycle output matches.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import textwrap

from rtlgen_x.dsl import VerilogEmitter

from gpu_sm.driver import collect_writebacks, directed_program, run_program
from gpu_sm.reference import GpuSmRef


REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "gpu_sm" / "build" / "iverilog"
BUILD.mkdir(parents=True, exist_ok=True)


def _vhex(value: int, width: int) -> str:
    return f"{width}'h{value & ((1 << width) - 1):X}"


def emit_rtl(tag: str = "gpu_sm") -> Path:
    """Emit the GpuSm RTL to the build directory."""
    from gpu_sm.dsl import GpuSm

    src = VerilogEmitter().emit(GpuSm())
    out = BUILD / f"{tag}.v"
    out.write_text(src, encoding="utf-8")
    return out


def _build_vectors(program: list[tuple[int, int]]) -> list[tuple[int, int, int, int]]:
    """Run the program on the reference model and return expected writebacks.

    Each tuple is (warp, reg, data, cycle_offset).  cycle_offset is not used by
    the iverilog harness directly; the harness drains until all expected beats
    are collected.
    """
    ref = GpuSmRef()
    ref.reset()
    outputs = run_program(ref, program, drain_cycles=len(program) + GpuSmRef.SFU_LATENCY + 8)
    return [(w, r, d, 0) for w, r, d in collect_writebacks(outputs)]


def generate_tb(program: list[tuple[int, int]], vectors: list[tuple[int, int, int, int]]) -> str:
    """Generate a self-checking iverilog testbench."""
    expect_lines = "\n".join(
        f"    expected[{i}] = 64'h{data:016X}; expected_reg[{i}] = 4'd{reg}; expected_warp[{i}] = 1'd{warp};"
        for i, (warp, reg, data, _) in enumerate(vectors)
    )
    instr_lines = "\n".join(
        f"      instrs[{i}] = {_vhex(instr, 32)}; instr_valids[{i}] = 1'b{valid};"
        for i, (valid, instr) in enumerate(program)
    )
    return textwrap.dedent(
        f"""\
`timescale 1ns/1ps
module tb_gpu_sm;
  reg clk, rst, instr_valid;
  reg [31:0] instr;
  wire out_valid;
  wire [0:0] out_warp;
  wire [3:0] out_reg;
  wire [63:0] out_data;
  wire busy;

  gpu_sm dut(
    .clk(clk), .rst(rst), .instr_valid(instr_valid), .instr(instr),
    .out_valid(out_valid), .out_warp(out_warp), .out_reg(out_reg),
    .out_data(out_data), .busy(busy)
  );

  always #5 clk = ~clk;

  integer errors, checked, collected;
  reg [63:0] expected [0:{len(vectors) - 1}];
  reg [3:0]  expected_reg [0:{len(vectors) - 1}];
  reg [0:0]  expected_warp [0:{len(vectors) - 1}];
  reg [31:0] instrs [0:{len(program) - 1}];
  reg        instr_valids [0:{len(program) - 1}];
  integer    prog_idx;

  task drive_program;
    begin
      for (prog_idx = 0; prog_idx < {len(program)}; prog_idx = prog_idx + 1) begin
        @(negedge clk);
        instr_valid = instr_valids[prog_idx];
        instr = instrs[prog_idx];
      end
      @(negedge clk);
      instr_valid = 0;
      instr = 0;
    end
  endtask

  task drain_and_check;
    integer max_cycles;
    begin
      max_cycles = {len(program)} + 16;
      while (collected < {len(vectors)} && max_cycles > 0) begin
        @(negedge clk);
        if (out_valid) begin
          if (out_data !== expected[collected] || out_reg !== expected_reg[collected] || out_warp !== expected_warp[collected]) begin
            $display("MISMATCH idx=%0d got(w=%0d r=%0d d=0x%016x) exp(w=%0d r=%0d d=0x%016x)",
                     collected, out_warp, out_reg, out_data,
                     expected_warp[collected], expected_reg[collected], expected[collected]);
            errors = errors + 1;
          end else begin
            checked = checked + 1;
          end
          collected = collected + 1;
        end
        max_cycles = max_cycles - 1;
      end
      if (collected != {len(vectors)}) begin
        $display("VALID_MISS collected=%0d expected=%0d", collected, {len(vectors)});
        errors = errors + 1;
      end
    end
  endtask

  initial begin
    clk = 0; rst = 1; instr_valid = 0; instr = 0;
    errors = 0; checked = 0; collected = 0;
    @(negedge clk); @(negedge clk);
    rst = 0;
    @(negedge clk);

{expect_lines}

{instr_lines}

    fork
      drive_program();
      drain_and_check();
    join

    $display("RESULT checked=%0d errors=%0d collected=%0d", checked, errors, collected);
    if (errors == 0 && checked == {len(vectors)}) $display("IVERILOG_PASS");
    else $display("IVERILOG_FAIL");
    $finish;
  end
endmodule
"""
    )


def run(program: list[tuple[int, int]] | None = None, *, tag: str = "directed") -> bool:
    """Run iverilog cosim for the given program."""
    from gpu_sm.dsl import GpuSm

    eff_program = program if program is not None else directed_program()
    vectors = _build_vectors(eff_program)
    rtl = emit_rtl(f"gpu_sm_{tag}")
    tb_path = BUILD / f"gpu_sm_{tag}_tb.v"
    tb_path.write_text(generate_tb(eff_program, vectors), encoding="utf-8")

    vvp = BUILD / f"gpu_sm_{tag}.vvp"
    compile_cmd = ["iverilog", "-g2012", "-o", str(vvp), str(rtl), str(tb_path)]
    cp = subprocess.run(compile_cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        print("iverilog compile FAILED:\n", cp.stderr)
        return False

    rp = subprocess.run(["vvp", str(vvp)], capture_output=True, text=True)
    print(f"[{tag}] " + rp.stdout.strip().replace("\n", " | "))
    return "IVERILOG_PASS" in rp.stdout


if __name__ == "__main__":
    ok = run(directed_program(), tag="directed")
    raise SystemExit(0 if ok else 1)
