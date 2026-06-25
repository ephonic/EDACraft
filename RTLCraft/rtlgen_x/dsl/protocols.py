"""
rtlgen_x.dsl.protocols — 接口与总线协议

提供 Bundle（信号组封装）以及常用标准总线协议的定义。
"""
from __future__ import annotations

from typing import Dict, Optional, TypeVar

from rtlgen_x.dsl.core import Input, Output, Signal

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
        for key, value in self.__dict__.items():
            if key not in {"_signals", "_directions"}:
                setattr(other, key, value)
        Bundle.__init__(other, name=self.name)
        for n, sig in self._signals.items():
            dir_ = "out" if self._directions[n] == "in" else "in"
            width = sig.width
            new_sig = Input(width, n) if dir_ == "in" else Output(width, n)
            other._add(n, new_sig, dir_)
        return other

    def prefixed(self: T, prefix: str) -> T:
        """Return a cloned bundle whose signal names are prefixed.

        The semantic field names stay unchanged, so protocol helpers such as
        ``payload_fields()`` / ``request_fields()`` still work the same way.
        """
        if not prefix:
            return self
        other: T = self.__class__.__new__(self.__class__)
        for key, value in self.__dict__.items():
            if key not in {"_signals", "_directions"}:
                setattr(other, key, value)
        Bundle.__init__(other, name=prefix)
        for field_name, sig in self._signals.items():
            direction = self._directions[field_name]
            width = sig.width
            signal_name = f"{prefix}_{field_name}"
            new_sig = Input(width, signal_name) if direction == "in" else Output(width, signal_name)
            other._add(field_name, new_sig, direction)
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

    def signal_map(self) -> Dict[str, Signal]:
        """Return the bundle's named signal dictionary."""
        return dict(self._signals)

    @property
    def signals(self) -> Dict[str, Signal]:
        """Compatibility surface shared with ``core.Interface`` helpers."""
        return dict(self._signals)

    def fields(self) -> tuple[str, ...]:
        return tuple(self._signals.keys())

    def input_fields(self) -> tuple[str, ...]:
        return tuple(name for name, direction in self._directions.items() if direction == "in")

    def output_fields(self) -> tuple[str, ...]:
        return tuple(name for name, direction in self._directions.items() if direction == "out")

    def direction_of(self, name: str) -> str:
        return self._directions[name]

    def port_map(
        self,
        *,
        include: Optional[tuple[str, ...]] = None,
        exclude: Optional[tuple[str, ...]] = None,
    ) -> Dict[str, Signal]:
        """Return a ``Module.instantiate(..., port_map=...)``-ready mapping."""
        include_set = set(include or self._signals.keys())
        exclude_set = set(exclude or ())
        return {
            name: sig
            for name, sig in self._signals.items()
            if name in include_set and name not in exclude_set
        }

    def instantiate_port_map(
        self,
        other: "Bundle",
        *,
        include: Optional[tuple[str, ...]] = None,
        exclude: Optional[tuple[str, ...]] = None,
    ) -> Dict[str, Signal]:
        """Return a ``Module.instantiate(..., port_map=...)``-ready mapping.

        Keys always use the *other* bundle's signal names, which makes the
        result suitable for connecting local signals to a submodule's bundle
        ports while keeping the local semantic field selection on ``self``.
        """
        if self.__class__ != other.__class__:
            raise TypeError("Can only instantiate Bundles of the same type")
        include_set = set(include or self._signals.keys())
        exclude_set = set(exclude or ())
        mapping: Dict[str, Signal] = {}
        for field_name, local_sig in self._signals.items():
            if field_name not in include_set or field_name in exclude_set:
                continue
            if field_name not in other._signals:
                raise KeyError(
                    f"bundle field '{field_name}' is missing on peer bundle "
                    f"{other.__class__.__name__}({other.name or 'anonymous'})"
                )
            mapping[other._signals[field_name].name] = local_sig
        return mapping


# ---------------------------------------------------------------------
# Standard Protocols
# ---------------------------------------------------------------------

class ReadyValid(Bundle):
    """Canonical ready/valid channel bundle.

    Direction convention follows producer -> consumer:

    1. producer drives ``valid`` and payload
    2. consumer drives ``ready``

    The default bundle therefore models the producer-facing port shape:

    - ``valid`` / payload fields are ``in``
    - ``ready`` is ``out``

    Use ``flip()`` when the containing module is the producer side.
    """

    def __init__(
        self,
        data_width: int = 32,
        *,
        name: str = "",
        payload_name: str = "data",
        valid_name: str = "valid",
        ready_name: str = "ready",
        has_last: bool = False,
        last_name: str = "last",
        has_keep: bool = False,
        keep_name: str = "keep",
        keep_width: Optional[int] = None,
        user_width: int = 0,
        user_name: str = "user",
    ):
        super().__init__(name)
        self.data_width = int(data_width)
        self.payload_name = payload_name
        self.valid_name = valid_name
        self.ready_name = ready_name
        self.has_last = bool(has_last)
        self.last_name = last_name
        self.has_keep = bool(has_keep)
        self.keep_name = keep_name
        self.user_width = int(user_width)
        self.user_name = user_name
        resolved_keep_width = int(keep_width) if keep_width is not None else max((self.data_width + 7) // 8, 1)
        self.keep_width = resolved_keep_width

        self._add(payload_name, Input(self.data_width), "in")
        self._add(valid_name, Input(1), "in")
        self._add(ready_name, Output(1), "out")
        if self.has_last:
            self._add(last_name, Input(1), "in")
        if self.has_keep:
            self._add(keep_name, Input(self.keep_width), "in")
        if self.user_width > 0:
            self._add(user_name, Input(self.user_width), "in")

    def connect_port_map(
        self,
        other: "ReadyValid",
        *,
        include_ready: bool = True,
    ) -> Dict[str, Signal]:
        """Generate a protocol-aware port map between two ready/valid bundles."""
        if self.__class__ is not other.__class__:
            raise TypeError("Can only connect ReadyValid bundles of the same type")
        mapping = {self.payload_name: self._signals[self.payload_name], self.valid_name: self._signals[self.valid_name]}
        if self.has_last:
            mapping[self.last_name] = self._signals[self.last_name]
        if self.has_keep:
            mapping[self.keep_name] = self._signals[self.keep_name]
        if self.user_width > 0:
            mapping[self.user_name] = self._signals[self.user_name]
        if "tstrb" in self._signals:
            mapping["tstrb"] = self._signals["tstrb"]
        if include_ready:
            mapping[self.ready_name] = other._signals[other.ready_name]
        return mapping

    def payload_fields(self) -> tuple[str, ...]:
        fields = [self.payload_name]
        if self.has_last:
            fields.append(self.last_name)
        if self.has_keep:
            fields.append(self.keep_name)
        if self.user_width > 0:
            fields.append(self.user_name)
        if "tstrb" in self._signals:
            fields.append("tstrb")
        return tuple(fields)

    def forward_fields(self) -> tuple[str, ...]:
        return (*self.payload_fields(), self.valid_name)

    def backward_fields(self) -> tuple[str, ...]:
        return (self.ready_name,)

    def fire(self):
        return self._signals[self.valid_name] & self._signals[self.ready_name]


class ReqRsp(Bundle):
    """Canonical request/response channel bundle.

    Direction convention follows requester -> responder:

    1. requester drives request fields and ``req_valid``
    2. responder drives ``req_ready`` plus response fields and ``rsp_valid``
    3. requester drives ``rsp_ready``

    The default bundle models the responder-facing port shape:

    - request fields / ``req_valid`` / ``rsp_ready`` are ``in``
    - ``req_ready`` / response fields / ``rsp_valid`` are ``out``

    Use ``flip()`` when the containing module is the requester side.
    """

    def __init__(
        self,
        req_data_width: int = 32,
        rsp_data_width: int = 32,
        *,
        name: str = "",
        req_name: str = "req",
        rsp_name: str = "rsp",
        req_valid_name: str = "req_valid",
        req_ready_name: str = "req_ready",
        rsp_valid_name: str = "rsp_valid",
        rsp_ready_name: str = "rsp_ready",
        addr_width: int = 0,
        addr_name: str = "addr",
        write_enable: bool = False,
        write_name: str = "write",
        strobe_width: int = 0,
        strobe_name: str = "strb",
    ):
        super().__init__(name)
        self.req_data_width = int(req_data_width)
        self.rsp_data_width = int(rsp_data_width)
        self.req_name = req_name
        self.rsp_name = rsp_name
        self.req_valid_name = req_valid_name
        self.req_ready_name = req_ready_name
        self.rsp_valid_name = rsp_valid_name
        self.rsp_ready_name = rsp_ready_name
        self.addr_width = int(addr_width)
        self.addr_name = addr_name
        self.write_enable = bool(write_enable)
        self.write_name = write_name
        self.strobe_width = int(strobe_width)
        self.strobe_name = strobe_name

        if self.addr_width > 0:
            self._add(addr_name, Input(self.addr_width), "in")
        self._add(req_name, Input(self.req_data_width), "in")
        if self.write_enable:
            self._add(write_name, Input(1), "in")
        if self.strobe_width > 0:
            self._add(strobe_name, Input(self.strobe_width), "in")
        self._add(req_valid_name, Input(1), "in")
        self._add(req_ready_name, Output(1), "out")
        self._add(rsp_name, Output(self.rsp_data_width), "out")
        self._add(rsp_valid_name, Output(1), "out")
        self._add(rsp_ready_name, Input(1), "in")

    def request_fields(self) -> tuple[str, ...]:
        fields = []
        if self.addr_width > 0:
            fields.append(self.addr_name)
        fields.append(self.req_name)
        if self.write_enable:
            fields.append(self.write_name)
        if self.strobe_width > 0:
            fields.append(self.strobe_name)
        fields.extend((self.req_valid_name, self.req_ready_name))
        return tuple(fields)

    def response_fields(self) -> tuple[str, ...]:
        return (self.rsp_name, self.rsp_valid_name, self.rsp_ready_name)

    def connect_port_map(self, other: "ReqRsp") -> Dict[str, Signal]:
        """Generate a protocol-aware requester/responder port map."""
        if self.__class__ is not other.__class__:
            raise TypeError("Can only connect ReqRsp bundles of the same type")
        mapping: Dict[str, Signal] = {}
        if self.addr_width > 0:
            mapping[self.addr_name] = self._signals[self.addr_name]
        mapping[self.req_name] = self._signals[self.req_name]
        if self.write_enable:
            mapping[self.write_name] = self._signals[self.write_name]
        if self.strobe_width > 0:
            mapping[self.strobe_name] = self._signals[self.strobe_name]
        mapping[self.req_valid_name] = self._signals[self.req_valid_name]
        mapping[self.req_ready_name] = other._signals[other.req_ready_name]
        mapping[self.rsp_name] = other._signals[other.rsp_name]
        mapping[self.rsp_valid_name] = other._signals[other.rsp_valid_name]
        mapping[self.rsp_ready_name] = self._signals[self.rsp_ready_name]
        return mapping

    def request_payload_fields(self) -> tuple[str, ...]:
        fields = []
        if self.addr_width > 0:
            fields.append(self.addr_name)
        fields.append(self.req_name)
        if self.write_enable:
            fields.append(self.write_name)
        if self.strobe_width > 0:
            fields.append(self.strobe_name)
        return tuple(fields)

    def response_payload_fields(self) -> tuple[str, ...]:
        return (self.rsp_name,)

    def request_fire(self):
        return self._signals[self.req_valid_name] & self._signals[self.req_ready_name]

    def response_fire(self):
        return self._signals[self.rsp_valid_name] & self._signals[self.rsp_ready_name]

class AXI4Stream(ReadyValid):
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
        super().__init__(
            data_width,
            name=name,
            payload_name="tdata",
            valid_name="tvalid",
            ready_name="tready",
            has_last=True,
            last_name="tlast",
            has_keep=True,
            keep_name="tkeep",
            keep_width=max(data_width // 8, 1),
            user_width=user_width,
            user_name="tuser",
        )
        self._add("tid", Input(8), "in")
        self._add("tdest", Input(8), "in")
        if has_strb:
            self._add("tstrb", Input(data_width // 8), "in")


class APB(Bundle):
    """APB (AMBA Advanced Peripheral Bus) 接口。"""

    def __init__(self, addr_width: int = 32, data_width: int = 32, name: str = ""):
        super().__init__(name)
        self.addr_width = int(addr_width)
        self.data_width = int(data_width)
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

    def clock_reset_fields(self) -> tuple[str, ...]:
        return ("pclk", "presetn")

    def master_fields(self) -> tuple[str, ...]:
        return (
            "pclk",
            "presetn",
            "psel",
            "penable",
            "pwrite",
            "paddr",
            "pwdata",
            "pprot",
            "pstrb",
        )

    def slave_fields(self) -> tuple[str, ...]:
        return ("prdata", "pready", "pslverr")

    def connect_port_map(
        self,
        other: "APB",
        *,
        include_clock_reset: bool = True,
    ) -> Dict[str, Signal]:
        if self.__class__ is not other.__class__:
            raise TypeError("Can only connect APB bundles of the same type")
        fields = self.master_fields() if include_clock_reset else tuple(
            name for name in self.master_fields() if name not in self.clock_reset_fields()
        )
        mapping = {name: self._signals[name] for name in fields}
        mapping.update({name: other._signals[name] for name in self.slave_fields()})
        return mapping

    def transaction_port_map(
        self,
        other: "APB",
        *,
        include_clock_reset: bool = True,
    ) -> Dict[str, Signal]:
        return self.connect_port_map(other, include_clock_reset=include_clock_reset)


class AXI4Lite(Bundle):
    """AXI4-Lite 接口（简化版 AXI4）。"""

    def __init__(self, addr_width: int = 32, data_width: int = 32, name: str = ""):
        super().__init__(name)
        self.addr_width = int(addr_width)
        self.data_width = int(data_width)
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

    def write_address_fields(self) -> tuple[str, ...]:
        return ("awaddr", "awvalid", "awprot")

    def write_data_fields(self) -> tuple[str, ...]:
        return ("wdata", "wstrb", "wvalid")

    def write_response_fields(self) -> tuple[str, ...]:
        return ("awready", "wready", "bresp", "bvalid", "bready")

    def read_address_fields(self) -> tuple[str, ...]:
        return ("araddr", "arvalid", "arprot")

    def read_response_fields(self) -> tuple[str, ...]:
        return ("arready", "rdata", "rresp", "rvalid", "rready")

    def master_fields(self) -> tuple[str, ...]:
        return (
            *self.write_address_fields(),
            *self.write_data_fields(),
            "bready",
            *self.read_address_fields(),
            "rready",
        )

    def slave_fields(self) -> tuple[str, ...]:
        return ("awready", "wready", "bresp", "bvalid", "arready", "rdata", "rresp", "rvalid")

    def connect_port_map(self, other: "AXI4Lite") -> Dict[str, Signal]:
        if self.__class__ is not other.__class__:
            raise TypeError("Can only connect AXI4Lite bundles of the same type")
        mapping = {name: self._signals[name] for name in self.master_fields()}
        mapping.update({name: other._signals[name] for name in self.slave_fields()})
        return mapping

    def transaction_port_map(self, other: "AXI4Lite") -> Dict[str, Signal]:
        return self.connect_port_map(other)


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
        self.addr_width = int(addr_width)
        self.data_width = int(data_width)
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

    def clock_reset_fields(self) -> tuple[str, ...]:
        return ("hclk", "hresetn")

    def master_fields(self) -> tuple[str, ...]:
        return (
            "hclk",
            "hresetn",
            "haddr",
            "htrans",
            "hwrite",
            "hsize",
            "hburst",
            "hprot",
            "hwdata",
            "hsel",
        )

    def slave_fields(self) -> tuple[str, ...]:
        return ("hrdata", "hready", "hresp")

    def connect_port_map(
        self,
        other: "AHBLite",
        *,
        include_clock_reset: bool = True,
    ) -> Dict[str, Signal]:
        if self.__class__ is not other.__class__:
            raise TypeError("Can only connect AHBLite bundles of the same type")
        fields = self.master_fields() if include_clock_reset else tuple(
            name for name in self.master_fields() if name not in self.clock_reset_fields()
        )
        mapping = {name: self._signals[name] for name in fields}
        mapping.update({name: other._signals[name] for name in self.slave_fields()})
        return mapping

    def transaction_port_map(
        self,
        other: "AHBLite",
        *,
        include_clock_reset: bool = True,
    ) -> Dict[str, Signal]:
        return self.connect_port_map(other, include_clock_reset=include_clock_reset)


class Wishbone(Bundle):
    """Wishbone B4 接口（经典开源 SoC 总线）。"""

    def __init__(self, addr_width: int = 32, data_width: int = 32, name: str = ""):
        super().__init__(name)
        self.addr_width = int(addr_width)
        self.data_width = int(data_width)
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

    def clock_reset_fields(self) -> tuple[str, ...]:
        return ("clk_i", "rst_i")

    def master_fields(self) -> tuple[str, ...]:
        return (
            "clk_i",
            "rst_i",
            "adr_i",
            "dat_i",
            "we_i",
            "sel_i",
            "stb_i",
            "cyc_i",
            "cti_i",
            "bte_i",
        )

    def slave_fields(self) -> tuple[str, ...]:
        return ("dat_o", "ack_o", "err_o", "rty_o")

    def connect_port_map(
        self,
        other: "Wishbone",
        *,
        include_clock_reset: bool = True,
    ) -> Dict[str, Signal]:
        if self.__class__ is not other.__class__:
            raise TypeError("Can only connect Wishbone bundles of the same type")
        fields = self.master_fields() if include_clock_reset else tuple(
            name for name in self.master_fields() if name not in self.clock_reset_fields()
        )
        mapping = {name: self._signals[name] for name in fields}
        mapping.update({name: other._signals[name] for name in self.slave_fields()})
        return mapping

    def transaction_port_map(
        self,
        other: "Wishbone",
        *,
        include_clock_reset: bool = True,
    ) -> Dict[str, Signal]:
        return self.connect_port_map(other, include_clock_reset=include_clock_reset)
