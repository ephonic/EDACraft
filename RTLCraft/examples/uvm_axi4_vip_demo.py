#!/usr/bin/env python3
"""
UVM AXI4 VIP 自动生成示例。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import UVMVIPEmitter


if __name__ == "__main__":
    vip = UVMVIPEmitter()
    files = vip.emit_axi4_vip(
        id_width=4,
        addr_width=32,
        data_width=64,
        user_width=8,
        pkg_name="axi4_vip_pkg",
    )

    for fname, content in files.items():
        print(f"// {'='*60}")
        print(f"// File: {fname}")
        print(f"// {'='*60}")
        print(content)
        print()
