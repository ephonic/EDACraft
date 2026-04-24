#!/usr/bin/env python3
"""
UVM APB VIP 自动生成示例。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import UVMVIPEmitter


if __name__ == "__main__":
    vip = UVMVIPEmitter()
    files = vip.emit_apb_vip(addr_width=16, data_width=32, pkg_name="apb_vip_pkg")

    for fname, content in files.items():
        print(f"// {'='*60}")
        print(f"// File: {fname}")
        print(f"// {'='*60}")
        print(content)
        print()
