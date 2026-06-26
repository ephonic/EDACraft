"""
rtlgen.protocols — 接口与总线协议

提供 Bundle（信号组封装）以及常用标准总线协议的定义。
"""
from __future__ import annotations

from typing import Dict, TypeVar

from rtlgen.core import Input, Output, Signal

T = TypeVar("T", bound="Bundle")


class Bundle:
    """信号束基类，用于封装一组相关信号（类似 SystemVerilog Interface）。

    子类在 __init__ 中通过 _add() 注册信号及其方向（"in" / "out"）。
    调用 flip() 可反转所有方向。
    """

    def __init__(self, name: str = ""):
        self.name = name
        self._signals: Dict[str, Signal] = {}
        self._directions: Dict[str, str] = {}  # "in" | "out"

    def _add(self, name: str, sig: Signal, direction: str):
        """注册一个信号到 Bundle。"""
        if not sig.name:
            sig.name = name
        setattr(self, name, sig)
        self._signals[name] = sig
        self._directions[name] = direction

    def flip(self: T) -> T:
        """返回方向反转后的新 Bundle 实例。"""
        other: T = self.__class__.__new__(self.__class__)
        Bundle.__init__(other, name=self.name)
        for n, sig in self._signals.items():
            dir_ = "out" if self._directions[n] == "in" else "in"
            width = sig.width
            new_sig = Input(width, n) if dir_ == "in" else Output(width, n)
            other._add(n, new_sig, dir_)
        return other

    def connect(self, other: "Bundle"):
        """将两个同类型 Bundle 的信号按名称配对，返回 {self_sig: other_sig} 映射。"""
        if self.__class__ != other.__class__:
            raise TypeError("Can only connect Bundles of the same type")
        mapping: Dict[Signal, Signal] = {}
        for name in self._signals:
            mapping[self._signals[name]] = other._signals[name]
        return mapping

    def __repr__(self):
        ports = ", ".join(f"{n}:{self._directions[n]}" for n in self._signals)
        return f"{self.__class__.__name__}({self.name or 'anonymous'})[{ports}]"


# ---------------------------------------------------------------------
# Standard Protocols
# ---------------------------------------------------------------------

class AXI4Stream(Bundle):
    """AXI4-Stream 协议接口。

    参数:
        data_width: 数据位宽
        user_width: tuser 位宽（默认 0，即不生成 tuser）
        has_strb: 是否包含 tstrb（默认 False）
    """

    def __init__(
        self,
        data_width: int = 32,
        user_width: int = 0,
        has_strb: bool = False,
        name: str = "",
    ):
        super().__init__(name)
        self._add("tdata", Input(data_width), "in")
        self._add("tvalid", Input(1), "in")
        self._add("tready", Output(1), "out")
        self._add("tlast", Input(1), "in")
        self._add("tkeep", Input(data_width // 8), "in")
        self._add("tid", Input(8), "in")
        self._add("tdest", Input(8), "in")
        if has_strb:
            self._add("tstrb", Input(data_width // 8), "in")
        if user_width > 0:
            self._add("tuser", Input(user_width), "in")


class APB(Bundle):
    """APB (AMBA Advanced Peripheral Bus) 接口。"""

    def __init__(self, addr_width: int = 32, data_width: int = 32, name: str = ""):
        super().__init__(name)
        self._add("pclk", Input(1), "in")
        self._add("presetn", Input(1), "in")
        self._add("psel", Input(1), "in")
        self._add("penable", Input(1), "in")
        self._add("pwrite", Input(1), "in")
        self._add("paddr", Input(addr_width), "in")
        self._add("pwdata", Input(data_width), "in")
        self._add("prdata", Output(data_width), "out")
        self._add("pready", Output(1), "out")
        self._add("pslverr", Output(1), "out")
        self._add("pprot", Input(3), "in")
        self._add("pstrb", Input(data_width // 8), "in")


class AXI4Lite(Bundle):
    """AXI4-Lite 接口（简化版 AXI4）。"""

    def __init__(self, addr_width: int = 32, data_width: int = 32, name: str = ""):
        super().__init__(name)
        # Write address channel
        self._add("awaddr", Input(addr_width), "in")
        self._add("awvalid", Input(1), "in")
        self._add("awready", Output(1), "out")
        self._add("awprot", Input(3), "in")
        # Write data channel
        self._add("wdata", Input(data_width), "in")
        self._add("wstrb", Input(data_width // 8), "in")
        self._add("wvalid", Input(1), "in")
        self._add("wready", Output(1), "out")
        # Write response channel
        self._add("bresp", Output(2), "out")
        self._add("bvalid", Output(1), "out")
        self._add("bready", Input(1), "in")
        # Read address channel
        self._add("araddr", Input(addr_width), "in")
        self._add("arvalid", Input(1), "in")
        self._add("arready", Output(1), "out")
        self._add("arprot", Input(3), "in")
        # Read data channel
        self._add("rdata", Output(data_width), "out")
        self._add("rresp", Output(2), "out")
        self._add("rvalid", Output(1), "out")
        self._add("rready", Input(1), "in")


class AXI4(Bundle):
    """完整 AXI4 接口（支持 Burst、ID、Qos、Region、Lock、Cache、User 等）。

    参数:
        id_width:   ID 位宽（默认 4）
        addr_width: 地址位宽（默认 32）
        data_width: 数据位宽（默认 32）
        user_width: 各通道 User 位宽（默认 0，即不生成）
    """

    def __init__(
        self,
        id_width: int = 4,
        addr_width: int = 32,
        data_width: int = 32,
        user_width: int = 0,
        name: str = "",
    ):
        super().__init__(name)
        strb_width = data_width // 8

        # Write address channel
        self._add("awid", Input(id_width), "in")
        self._add("awaddr", Input(addr_width), "in")
        self._add("awlen", Input(8), "in")
        self._add("awsize", Input(3), "in")
        self._add("awburst", Input(2), "in")
        self._add("awlock", Input(1), "in")
        self._add("awcache", Input(4), "in")
        self._add("awprot", Input(3), "in")
        self._add("awqos", Input(4), "in")
        self._add("awregion", Input(4), "in")
        self._add("awvalid", Input(1), "in")
        self._add("awready", Output(1), "out")
        if user_width > 0:
            self._add("awuser", Input(user_width), "in")

        # Write data channel
        self._add("wdata", Input(data_width), "in")
        self._add("wstrb", Input(strb_width), "in")
        self._add("wlast", Input(1), "in")
        self._add("wvalid", Input(1), "in")
        self._add("wready", Output(1), "out")
        if user_width > 0:
            self._add("wuser", Input(user_width), "in")

        # Write response channel
        self._add("bid", Output(id_width), "out")
        self._add("bresp", Output(2), "out")
        self._add("bvalid", Output(1), "out")
        self._add("bready", Input(1), "in")
        if user_width > 0:
            self._add("buser", Output(user_width), "out")

        # Read address channel
        self._add("arid", Input(id_width), "in")
        self._add("araddr", Input(addr_width), "in")
        self._add("arlen", Input(8), "in")
        self._add("arsize", Input(3), "in")
        self._add("arburst", Input(2), "in")
        self._add("arlock", Input(1), "in")
        self._add("arcache", Input(4), "in")
        self._add("arprot", Input(3), "in")
        self._add("arqos", Input(4), "in")
        self._add("arregion", Input(4), "in")
        self._add("arvalid", Input(1), "in")
        self._add("arready", Output(1), "out")
        if user_width > 0:
            self._add("aruser", Input(user_width), "in")

        # Read data channel
        self._add("rid", Output(id_width), "out")
        self._add("rdata", Output(data_width), "out")
        self._add("rresp", Output(2), "out")
        self._add("rlast", Output(1), "out")
        self._add("rvalid", Output(1), "out")
        self._add("rready", Input(1), "in")
        if user_width > 0:
            self._add("ruser", Output(user_width), "out")


class AHBLite(Bundle):
    """AHB-Lite 接口（简化版 AHB，无 Split/Retry）。"""

    def __init__(self, addr_width: int = 32, data_width: int = 32, name: str = ""):
        super().__init__(name)
        # Global
        self._add("hclk", Input(1), "in")
        self._add("hresetn", Input(1), "in")
        # Master -> Slave
        self._add("haddr", Input(addr_width), "in")
        self._add("htrans", Input(2), "in")
        self._add("hwrite", Input(1), "in")
        self._add("hsize", Input(3), "in")
        self._add("hburst", Input(3), "in")
        self._add("hprot", Input(4), "in")
        self._add("hwdata", Input(data_width), "in")
        self._add("hsel", Input(1), "in")
        # Slave -> Master
        self._add("hrdata", Output(data_width), "out")
        self._add("hready", Output(1), "out")
        self._add("hresp", Output(1), "out")


class Wishbone(Bundle):
    """Wishbone B4 接口（经典开源 SoC 总线）。"""

    def __init__(self, addr_width: int = 32, data_width: int = 32, name: str = ""):
        super().__init__(name)
        self._add("clk_i", Input(1), "in")
        self._add("rst_i", Input(1), "in")
        self._add("adr_i", Input(addr_width), "in")
        self._add("dat_i", Input(data_width), "in")
        self._add("dat_o", Output(data_width), "out")
        self._add("we_i", Input(1), "in")
        self._add("sel_i", Input(data_width // 8), "in")
        self._add("stb_i", Input(1), "in")
        self._add("ack_o", Output(1), "out")
        self._add("cyc_i", Input(1), "in")
        self._add("err_o", Output(1), "out")
        self._add("rty_o", Output(1), "out")
        self._add("cti_i", Input(3), "in")
        self._add("bte_i", Input(2), "in")
