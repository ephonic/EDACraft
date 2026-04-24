#!/usr/bin/env python3
"""
UVM RAL 自动生成示例：定义 GPIO 寄存器块并生成 UVM RAL 模型。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import UVMEmitter, RegField, Register, RegBlock


if __name__ == "__main__":
    # 定义 GPIO 控制寄存器块
    ctrl_reg = Register("ctrl", width=32, fields=[
        RegField("enable", width=1, access="RW", reset=0),
        RegField("mode",   width=3, access="RW", reset=0),
        RegField("irq_en", width=1, access="RW", reset=0),
        RegField("rsvd",   width=27, access="RO", reset=0),
    ])

    data_reg = Register("data", width=32)

    status_reg = Register("status", width=32, fields=[
        RegField("busy",  width=1, access="RO", reset=0),
        RegField("error", width=1, access="RO", reset=0),
        RegField("rsvd",  width=30, access="RO", reset=0),
    ])

    gpio_block = RegBlock("gpio", base_addr=0x4000_0000)
    gpio_block.add_reg(ctrl_reg,   0x00)
    gpio_block.add_reg(data_reg,   0x04)
    gpio_block.add_reg(status_reg, 0x08)

    uvm = UVMEmitter()
    files = uvm.emit_ral(gpio_block, pkg_name="gpio_test_pkg")

    for fname, content in files.items():
        print(f"// {'='*60}")
        print(f"// File: {fname}")
        print(f"// {'='*60}")
        print(content)
        print()
