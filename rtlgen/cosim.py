"""
rtlgen.cosim — Python & iverilog 协同仿真框架

对同一个 pyRTL Module，同时在 Python Simulator 和 iverilog 中执行相同的
测试向量，并自动对比输出 trace，确保语义一致性。
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union

from rtlgen import Simulator, VerilogEmitter
from rtlgen.core import Module


class CosimError(Exception):
    pass


def _to_sv_literal(val: Any) -> str:
    """将 Python int 或布尔值转为 Verilog 字面量。"""
    if isinstance(val, bool):
        return "1'b1" if val else "1'b0"
    if isinstance(val, int):
        return str(val)
    raise CosimError(f"Unsupported SV literal type: {type(val)} for value {val}")


def _generate_sv_tb(
    module: Module,
    vectors: List[Dict[str, Any]],
    mode: str,
    clk_period_ns: int = 10,
    extra_decls: Optional[str] = None,
) -> str:
    """为 iverilog 生成一个简易 testbench。"""
    inputs = list(module._inputs.values())
    outputs = list(module._outputs.values())
    has_clk = any(sig.name == "clk" for sig in inputs)
    is_seq = mode == "seq"

    lines: List[str] = []
    lines.append(f"`timescale 1ns/1ps")
    lines.append(f"module tb_top;")

    # 声明
    if is_seq and has_clk:
        lines.append(f"    reg clk = 0;")
    for sig in inputs:
        if sig.name == "clk" and is_seq:
            continue
        wdecl = f"[{sig.width-1}:0] " if sig.width > 1 else ""
        lines.append(f"    reg {wdecl}{sig.name};")
    for sig in outputs:
        wdecl = f"[{sig.width-1}:0] " if sig.width > 1 else ""
        lines.append(f"    wire {wdecl}{sig.name};")

    # 内部辅助 wire：把 output reg 也暴露为 wire 以便采样
    # （iverilog 中 output reg 不能直接作为 wire 用在 $display 中？实际上可以）

    if extra_decls:
        lines.append(extra_decls)

    lines.append("")
    mod_name = getattr(module, "_type_name", module.name)
    lines.append(f"    {mod_name} u_dut (")
    port_items = []
    for sig in inputs:
        port_items.append(f"        .{sig.name}({sig.name})")
    for sig in outputs:
        port_items.append(f"        .{sig.name}({sig.name})")
    for i, p in enumerate(port_items):
        comma = "," if i < len(port_items) - 1 else ""
        lines.append(f"{p}{comma}")
    lines.append(f"    );")
    lines.append("")

    if is_seq and has_clk:
        lines.append(f"    always #{clk_period_ns//2} clk = ~clk;")
        lines.append("")

    # initial 块
    lines.append(f"    initial begin")

    # 显式初始化所有输入（避免 iverilog 中 always @(*) time-0 不触发问题）
    for sig in inputs:
        if sig.name == "clk" and is_seq:
            continue
        lines.append(f"        {sig.name} = 0;")
    lines.append(f"        #0;")

    # 自动复位序列（与 Python Simulator 对齐）
    if is_seq and has_clk:
        has_rst = any(sig.name == "rst" for sig in inputs)
        has_rst_n = any(sig.name == "rst_n" for sig in inputs)
        if has_rst:
            lines.append(f"        rst = 1;")
            lines.append(f"        @(posedge clk);")
            lines.append(f"        @(posedge clk);")
            lines.append(f"        rst = 0;")
            lines.append(f"        @(posedge clk);")
        elif has_rst_n:
            lines.append(f"        rst_n = 0;")
            lines.append(f"        @(posedge clk);")
            lines.append(f"        @(posedge clk);")
            lines.append(f"        rst_n = 1;")
            lines.append(f"        @(posedge clk);")
        else:
            lines.append(f"        @(posedge clk); // 等待第一个上升沿对齐")
    elif is_seq:
        pass

    last_vals: Dict[str, Any] = {}
    for cycle, vec in enumerate(vectors):
        # 设置输入
        for sig in inputs:
            if sig.name == "clk" and is_seq:
                continue
            val = vec.get(sig.name, last_vals.get(sig.name, 0))
            if last_vals.get(sig.name) != val:
                lines.append(f"        {sig.name} = {_to_sv_literal(val)};")
            last_vals[sig.name] = val

        if is_seq and has_clk:
            lines.append(f"        @(posedge clk);")
            lines.append(f"        #1;")
        else:
            lines.append(f"        #{clk_period_ns};")

        # 采样输出
        out_parts = [f"{sig.name}=%0d" for sig in outputs]
        out_vars = [sig.name for sig in outputs]
        lines.append(f"        $display(\"CYCLE %0d {' '.join(out_parts)}\", {cycle}, {', '.join(out_vars)});")

    lines.append(f"        $display(\"COSIM_DONE\");")
    lines.append(f"        $finish;")
    lines.append(f"    end")
    lines.append(f"endmodule")
    return "\n".join(lines)


def _parse_sv_output(stdout: str) -> List[Dict[str, int]]:
    """解析 iverilog $display 输出，提取每个 cycle 的信号值。"""
    trace: List[Dict[str, int]] = []
    cycle_pat = re.compile(r"^\s*CYCLE\s+(\d+)\s+(.*)$")
    for line in stdout.splitlines():
        m = cycle_pat.match(line)
        if not m:
            continue
        cycle = int(m.group(1))
        rest = m.group(2)
        snap: Dict[str, int] = {"_cycle": cycle}
        # 解析 key=value 对，支持 10 进制整数
        for kv in re.finditer(r"(\w+)=(\d+)", rest):
            snap[kv.group(1)] = int(kv.group(2))
        trace.append(snap)
    return trace


def _compile_and_run(sv_src: str, src_files: Optional[List[str]] = None) -> str:
    """用 iverilog 编译并运行 SV 代码，返回 stdout。"""
    with tempfile.TemporaryDirectory(prefix="rtlgen_cosim_") as tmpdir:
        tb_path = os.path.join(tmpdir, "tb_top.sv")
        with open(tb_path, "w") as f:
            f.write(sv_src)

        vvp_path = os.path.join(tmpdir, "tb_top.vvp")
        cmd_compile = ["iverilog", "-g2012", "-o", vvp_path, tb_path]
        if src_files:
            cmd_compile.extend(src_files)
        result = subprocess.run(cmd_compile, capture_output=True, text=True)
        if result.returncode != 0:
            raise CosimError(
                f"iverilog compilation failed:\nstdout={result.stdout}\nstderr={result.stderr}"
            )

        cmd_run = ["vvp", vvp_path]
        result = subprocess.run(cmd_run, capture_output=True, text=True)
        if result.returncode != 0:
            raise CosimError(
                f"vvp execution failed:\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result.stdout


class CosimRunner:
    """
    协同仿真 runner：在 Python Simulator 和 iverilog 中执行同一组测试向量，
    自动对比输出 trace。
    """

    def __init__(
        self,
        module: Module,
        vectors: List[Dict[str, Any]],
        mode: str = "auto",
        clock_period_ns: int = 10,
    ):
        self.module = module
        self.vectors = vectors
        self.clock_period_ns = clock_period_ns
        inputs = {sig.name for sig in module._inputs.values()}
        has_clk = "clk" in inputs
        if mode == "auto":
            self.mode = "seq" if has_clk else "comb"
        else:
            self.mode = mode

    def run_python(self) -> List[Dict[str, int]]:
        """在 Python Simulator 中运行测试向量，返回 trace。"""
        sim = Simulator(self.module, clock_period_ns=self.clock_period_ns)
        trace: List[Dict[str, int]] = []
        outputs = [sig.name for sig in self.module._outputs.values()]
        input_names = {sig.name for sig in self.module._inputs.values()}

        # 自动复位（与 iverilog TB 对齐）
        if self.mode == "seq":
            if "rst" in input_names:
                sim.reset("rst", cycles=2)
            elif "rst_n" in input_names:
                sim.reset("rst_n", cycles=2)

        for cycle, vec in enumerate(self.vectors):
            for sig in self.module._inputs.values():
                if sig.name in vec:
                    sim.set(sig.name, vec[sig.name])

            if self.mode == "seq":
                sim.step(do_trace=False)
            else:
                sim._eval_comb()
                sim.time_ns += self.clock_period_ns

            snap: Dict[str, int] = {"_cycle": cycle}
            for name in outputs:
                snap[name] = sim.get_int(name)
            trace.append(snap)
        return trace

    def run_iverilog(self) -> List[Dict[str, int]]:
        """生成 SV 代码和 testbench，用 iverilog 运行，返回 trace。"""
        emitter = VerilogEmitter()
        dut_src = emitter.emit_design(self.module)

        with tempfile.TemporaryDirectory(prefix="rtlgen_cosim_dut_") as tmpdir:
            dut_path = os.path.join(tmpdir, f"{self.module.name}.sv")
            with open(dut_path, "w") as f:
                f.write(dut_src)

            tb_sv = _generate_sv_tb(
                self.module,
                self.vectors,
                self.mode,
                self.clock_period_ns,
            )
            stdout = _compile_and_run(tb_sv, [dut_path])
            if "COSIM_DONE" not in stdout:
                raise CosimError(f"iverilog simulation did not reach COSIM_DONE. stdout:\n{stdout}")
            return _parse_sv_output(stdout)

    def run(self, verbose: bool = False) -> Tuple[List[Dict[str, int]], List[Dict[str, int]]]:
        """同时运行两边并对比。返回 (py_trace, sv_trace)。"""
        py_trace = self.run_python()
        sv_trace = self.run_iverilog()

        if len(py_trace) != len(sv_trace):
            raise CosimError(
                f"Trace length mismatch: Python={len(py_trace)}, iverilog={len(sv_trace)}"
            )

        outputs = [sig.name for sig in self.module._outputs.values()]
        for i, (py, sv) in enumerate(zip(py_trace, sv_trace)):
            for name in outputs:
                py_val = py.get(name)
                sv_val = sv.get(name)
                if py_val != sv_val:
                    raise CosimError(
                        f"Mismatch at cycle {i}, signal '{name}': "
                        f"Python={py_val}, iverilog={sv_val}"
                    )

        if verbose:
            print(f"[Cosim] {len(py_trace)} cycles matched OK.")
        return py_trace, sv_trace


def assert_cosim(
    module: Module,
    vectors: List[Dict[str, Any]],
    mode: str = "auto",
    clock_period_ns: int = 10,
    verbose: bool = False,
):
    """便捷函数：对给定模块和测试向量执行协同仿真并断言结果一致。"""
    runner = CosimRunner(module, vectors, mode=mode, clock_period_ns=clock_period_ns)
    runner.run(verbose=verbose)
