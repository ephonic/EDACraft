#!/usr/bin/env python3
"""总线协议示例：演示 Bundle / AXI4 / AXI4Stream / APB / AHBLite / Wishbone 的创建与 flip。"""

import sys
sys.path.insert(0, "..")

from rtlgen import (
    AXI4,
    AXI4Lite,
    AXI4Stream,
    AHBLite,
    APB,
    Bundle,
    Wishbone,
)


def dump_bundle(b):
    print(f"  {b}")


if __name__ == "__main__":
    print("=== AXI4Stream (with user) ===")
    axis = AXI4Stream(data_width=64, user_width=4, has_strb=True, name="s_axis")
    dump_bundle(axis)
    axis_m = axis.flip()
    dump_bundle(axis_m)

    print("\n=== AXI4Lite ===")
    axil = AXI4Lite(addr_width=16, data_width=32, name="s_axil")
    dump_bundle(axil)

    print("\n=== AXI4 (full) ===")
    axi = AXI4(id_width=4, addr_width=32, data_width=64, user_width=2, name="m_axi")
    dump_bundle(axi)

    print("\n=== APB ===")
    apb = APB(addr_width=16, data_width=32, name="s_apb")
    dump_bundle(apb)

    print("\n=== AHB-Lite ===")
    ahb = AHBLite(addr_width=32, data_width=64, name="m_ahb")
    dump_bundle(ahb)

    print("\n=== Wishbone ===")
    wb = Wishbone(addr_width=30, data_width=32, name="s_wb")
    dump_bundle(wb)

    print("\n=== connect demo ===")
    mapping = axi.connect(axi.flip())
    print(f"  mapped pairs: {len(mapping)}")
    for src, dst in list(mapping.items())[:5]:
        print(f"    {src.name} -> {dst.name}")
