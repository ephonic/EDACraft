#!/usr/bin/env python3
"""
UVM Testbench 自动生成示例：为 Counter 模块生成完整 UVM 验证平台。

运行后会打印所有生成的 SystemVerilog/UVM 文件内容。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import UVMEmitter
from counter import Counter


if __name__ == "__main__":
    dut = Counter(width=8)
    uvm = UVMEmitter()
    files = uvm.emit_full_testbench(dut)

    for fname, content in files.items():
        print(f"// {'='*60}")
        print(f"// File: {fname}")
        print(f"// {'='*60}")
        print(content)
        print()
