"""
rtlgen.cocotbgen — cocotb 测试代码生成器

为 pyRTL Module 生成基于 cocotb 的 Python 测试平台。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from rtlgen.core import Module


class CocotbEmitter:
    """cocotb 代码发射器。"""

    def __init__(self, indent: str = "    "):
        self.indent = indent

    @staticmethod
    def _find_clock(module: Module) -> Optional[str]:
        for n in ["clk", "clock", "aclk", "pclk"]:
            if n in module._inputs:
                return n
        return None

    def _data_ports(self, module: Module) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
        clk = self._find_clock(module)
        ignore = {clk, "rst", "reset", "rst_n", "reset_n", "aresetn", "presetn"}
        inputs = [(n, s.width) for n, s in module._inputs.items() if n not in ignore]
        outputs = [(n, s.width) for n, s in module._outputs.items()]
        return inputs, outputs

    def emit_test(self, module: Module) -> str:
        base = module.name.lower()
        clk = self._find_clock(module) or "clk"
        rst = ""
        for r in ["rst", "reset", "rst_n", "reset_n", "aresetn"]:
            if r in module._inputs:
                rst = r
                break
        inputs, outputs = self._data_ports(module)

        drive_lines = "\n".join(
            [f"        dut.{n}.value = random.randint(0, (1 << {w}) - 1)" for n, w in inputs]
        ) or "        # no data inputs"

        check_lines = "\n".join(
            [f"        # dut.{n}.value  # read output" for n, w in outputs]
        ) or "        # no data outputs"

        rst_logic = "active_high"
        rst_val_init = "1"
        rst_val_rel = "0"
        if rst.endswith("_n") or rst.endswith("n"):
            rst_logic = "active_low"
            rst_val_init = "0"
            rst_val_rel = "1"

        rst_block = ""
        if rst:
            rst_block = f"""
    # Reset sequence ({rst_logic})
    dut.{rst}.value = {rst_val_init}
    await ClockCycles(dut.{clk}, 5)
    dut.{rst}.value = {rst_val_rel}
    await ClockCycles(dut.{clk}, 2)
"""

        return f"""import cocotb
from cocotb.triggers import ClockCycles, Timer
from cocotb.clock import Clock
import random


@cocotb.test()
async def test_{base}_random(dut):
    \"\"\"Random stimulus test for {module.name}.\"\"\"
    # Start clock (10 ns period -> 100 MHz)
    cocotb.start_soon(Clock(dut.{clk}, 10, units="ns").start())
{rst_block}
    # Main stimulus loop
    for _ in range(20):
        await ClockCycles(dut.{clk}, 1)
{drive_lines}
{check_lines}

    await ClockCycles(dut.{clk}, 5)
"""

    def emit_makefile(
        self,
        top_module_name: str,
        verilog_sources: Optional[List[str]] = None,
    ) -> str:
        srcs = verilog_sources or [f"{top_module_name}.sv"]
        src_str = " \\\n    ".join(srcs)
        base = top_module_name.lower()
        return f"""# Makefile for cocotb simulation

VERILOG_SOURCES = {src_str}
TOPLEVEL = {top_module_name}
MODULE = test_{base}

SIM = icarus

include $(shell cocotb-config --makefiles)/Makefile.sim
"""

    def emit_full_cocotb(
        self,
        module: Module,
        verilog_sources: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        base = module.name.lower()
        files: Dict[str, str] = {}
        files[f"test_{base}.py"] = self.emit_test(module)
        files["Makefile"] = self.emit_makefile(module.name, verilog_sources)
        return files
