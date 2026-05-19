"""
rtlgen.registry — 组件元数据注册表

提供 ComponentMeta 和 ComponentRegistry，用于描述和检索 lib.py 中的
标准组件。支持按标签搜索、按面积过滤。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ComponentMeta:
    """组件元数据。"""
    tags: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    area: Dict[str, int] = field(default_factory=dict)   # {"gates": N, "regs": M}
    latency: int = 1                                    # 默认延迟（周期数）
    throughput: str = "1"                               # 默认每周期一个
    known_limits: List[str] = field(default_factory=list)


class ComponentRegistry:
    """全局组件注册表。"""

    _registry: Dict[str, tuple] = {}  # name -> (cls, meta)

    @classmethod
    def register(cls, name: str, component_cls: type, meta: ComponentMeta):
        """注册一个组件类及其元数据。"""
        cls._registry[name] = (component_cls, meta)

    @classmethod
    def get(cls, name: str) -> Optional[tuple]:
        """按名称获取组件。"""
        return cls._registry.get(name)

    @classmethod
    def search(cls, tags: Optional[List[str]] = None, max_area: Optional[int] = None) -> List[Dict[str, Any]]:
        """搜索组件。

        如果提供 tags，只返回包含所有指定标签的组件。
        如果提供 max_area，只返回面积不超过该值的组件。
        """
        results = []
        for name, (component_cls, meta) in cls._registry.items():
            if tags and not all(t in meta.tags for t in tags):
                continue
            if max_area is not None and meta.area.get("gates", 0) > max_area:
                continue
            results.append({
                "name": name,
                "cls": component_cls,
                "meta": meta,
            })
        return results

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """列出所有已注册的组件。"""
        return cls.search()


# ---------------------------------------------------------------------------
# Register all lib.py components
# ---------------------------------------------------------------------------

def _register_all():
    """延迟注册所有标准组件。"""
    from rtlgen.lib import (
        FSM, SyncFIFO, AsyncFIFO, Decoder, PriorityEncoder,
        BarrelShifter, LFSR, CRC, Divider, Counter, EdgeDetector,
        FixedPriorityArbiter, RoundRobinArbiter, StreamFIFO, FlatMemory,
        SpillRegister, RegSlice, CreditFlowControl, ClockGateCell, DataflowPipeline,
    )

    ComponentRegistry.register("FSM", FSM, ComponentMeta(
        tags=["control", "state-machine"],
        interfaces=["clk", "rst"],
        area={"gates": 50, "regs": 8},
        latency=1,
        known_limits=["Moore-style outputs only"],
    ))

    ComponentRegistry.register("SyncFIFO", SyncFIFO, ComponentMeta(
        tags=["fifo", "synchronous", "buffer"],
        interfaces=["clk", "rst", "in_data", "in_valid", "in_ready", "out_data", "out_valid", "out_ready"],
        area={"gates": 200, "regs": 64},
        latency=1,
        known_limits=["Single clock domain only"],
    ))

    ComponentRegistry.register("AsyncFIFO", AsyncFIFO, ComponentMeta(
        tags=["fifo", "asynchronous", "clock-crossing", "buffer"],
        interfaces=["wr_clk", "wr_rst", "wr_data", "wr_valid", "wr_ready", "rd_clk", "rd_rst", "rd_data", "rd_valid", "rd_ready"],
        area={"gates": 300, "regs": 128},
        latency=3,
        known_limits=["Requires depth >= 2, uses gray-code pointers"],
    ))

    ComponentRegistry.register("Decoder", Decoder, ComponentMeta(
        tags=["combinational", "decode"],
        interfaces=["in_data", "out"],
        area={"gates": 20, "regs": 0},
        latency=1,
        known_limits=["in_width <= 8 recommended"],
    ))

    ComponentRegistry.register("PriorityEncoder", PriorityEncoder, ComponentMeta(
        tags=["combinational", "encode", "priority"],
        interfaces=["in_data", "out", "valid"],
        area={"gates": 30, "regs": 0},
        latency=1,
        known_limits=["in_width <= 32 recommended"],
    ))

    ComponentRegistry.register("BarrelShifter", BarrelShifter, ComponentMeta(
        tags=["combinational", "arithmetic", "shift"],
        interfaces=["in_data", "shift_amount", "out"],
        area={"gates": 100, "regs": 0},
        latency=1,
        known_limits=["width <= 64 recommended"],
    ))

    ComponentRegistry.register("LFSR", LFSR, ComponentMeta(
        tags=["sequential", "pseudo-random", "counter"],
        interfaces=["clk", "rst", "out"],
        area={"gates": 40, "regs": 32},
        latency=1,
        known_limits=["Max 32 bits with built-in taps"],
    ))

    ComponentRegistry.register("CRC", CRC, ComponentMeta(
        tags=["sequential", "error-detection", "crc"],
        interfaces=["clk", "rst", "in_data", "in_valid", "out", "out_valid"],
        area={"gates": 150, "regs": 32},
        latency=1,
        known_limits=["Standard polynomials only"],
    ))

    ComponentRegistry.register("Divider", Divider, ComponentMeta(
        tags=["arithmetic", "division"],
        interfaces=["dividend", "divisor", "quotient", "remainder", "done"],
        area={"gates": 500, "regs": 64},
        latency=32,
        known_limits=["Iterative, one bit per cycle"],
    ))

    ComponentRegistry.register("Counter", Counter, ComponentMeta(
        tags=["sequential", "counter"],
        interfaces=["clk", "rst", "en", "out", "overflow"],
        area={"gates": 30, "regs": 32},
        latency=1,
    ))

    ComponentRegistry.register("EdgeDetector", EdgeDetector, ComponentMeta(
        tags=["sequential", "edge-detection"],
        interfaces=["clk", "rst", "in_signal", "rising_edge", "falling_edge", "any_edge"],
        area={"gates": 10, "regs": 2},
        latency=1,
    ))

    ComponentRegistry.register("FixedPriorityArbiter", FixedPriorityArbiter, ComponentMeta(
        tags=["arbitration", "priority", "combinational"],
        interfaces=["requests", "grant", "grant_valid"],
        area={"gates": 40, "regs": 0},
        latency=1,
        known_limits=["Starvation possible for low-priority requesters"],
    ))

    ComponentRegistry.register("RoundRobinArbiter", RoundRobinArbiter, ComponentMeta(
        tags=["arbitration", "round-robin", "fairness"],
        interfaces=["clk", "rst", "requests", "grant", "grant_valid"],
        area={"gates": 80, "regs": 16},
        latency=1,
    ))

    ComponentRegistry.register("StreamFIFO", StreamFIFO, ComponentMeta(
        tags=["fifo", "stream", "buffer", "handshake"],
        interfaces=["clk", "rst", "in_data", "in_valid", "in_ready", "out_data", "out_valid", "out_ready"],
        area={"gates": 250, "regs": 64},
        latency=1,
        known_limits=["Depth must be power of 2"],
    ))

    ComponentRegistry.register("FlatMemory", FlatMemory, ComponentMeta(
        tags=["memory", "storage"],
        interfaces=[],
        area={"gates": 100, "regs": 0},
        latency=1,
    ))

    ComponentRegistry.register("SpillRegister", SpillRegister, ComponentMeta(
        tags=["buffer", "handshake", "flow-control"],
        interfaces=["clk", "rst", "in_data", "in_valid", "in_ready", "out_data", "out_valid", "out_ready"],
        area={"gates": 60, "regs": 32},
        latency=1,
    ))

    ComponentRegistry.register("RegSlice", RegSlice, ComponentMeta(
        tags=["pipeline", "flow-control", "buffer"],
        interfaces=["clk", "rst", "in_data", "in_valid", "in_ready", "out_data", "out_valid", "out_ready"],
        area={"gates": 80, "regs": 32},
        latency=2,
    ))

    ComponentRegistry.register("CreditFlowControl", CreditFlowControl, ComponentMeta(
        tags=["flow-control", "credit"],
        interfaces=["clk", "rst", "in_data", "in_valid", "in_ready", "out_data", "out_valid", "out_ready"],
        area={"gates": 120, "regs": 32},
        latency=1,
    ))

    ComponentRegistry.register("ClockGateCell", ClockGateCell, ComponentMeta(
        tags=["power", "clock-gating"],
        interfaces=["clk", "en", "gated_clk"],
        area={"gates": 10, "regs": 1},
        latency=1,
        known_limits=["Requires latch-based implementation for glitch-free operation"],
    ))

    ComponentRegistry.register("DataflowPipeline", DataflowPipeline, ComponentMeta(
        tags=["pipeline", "dataflow", "flow-control"],
        interfaces=["clk", "rst", "in_data", "in_valid", "in_ready", "out_data", "out_valid", "out_ready"],
        area={"gates": 100, "regs": 64},
        latency=2,
    ))


_register_all()
