#!/usr/bin/env python3
"""
cocotb 测试代码自动生成示例：为 Counter 模块生成 Python 测试平台。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import CocotbEmitter
from counter import Counter


if __name__ == "__main__":
    dut = Counter(width=8)
    cocotb = CocotbEmitter()
    files = cocotb.emit_full_cocotb(dut, verilog_sources=["Counter.v", "tb_top.sv"])

    for fname, content in files.items():
        print(f"# {'='*60}")
        print(f"# File: {fname}")
        print(f"# {'='*60}")
        print(content)
        print()
