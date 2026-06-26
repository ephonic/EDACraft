"""
rtlgen.registry — 组件元数据注册表

提供 ComponentMeta 和 ComponentRegistry，用于描述和检索 lib.py 中的
标准组件。支持按标签搜索、按面积过滤。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


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
    """延迟注册所有标准组件。处理导入缺失的容错。"""
    try:
        from rtlgen.lib import (
            FSM, SyncFIFO, AsyncFIFO, Decoder, PriorityEncoder,
            BarrelShifter, LFSR, CRC, Divider,
            RoundRobinArbiter,
        )
    except ImportError:
        return

    # Register available components (with error tolerance for missing classes)
    _component_regs = [
        ("FSM", "FSM", {"tags": ["control", "state-machine"], "interfaces": ["clk", "rst"],
                        "area": {"gates": 50, "regs": 8}, "latency": 1}),
        ("SyncFIFO", "SyncFIFO", {"tags": ["fifo", "synchronous", "buffer"],
                                  "interfaces": ["clk", "rst"], "area": {"gates": 200, "regs": 64}, "latency": 1}),
        ("AsyncFIFO", "AsyncFIFO", {"tags": ["fifo", "asynchronous"], "interfaces": ["wr_clk", "rd_clk"],
                                    "area": {"gates": 300, "regs": 128}, "latency": 3}),
        ("Decoder", "Decoder", {"tags": ["decode"], "interfaces": ["in_data", "out"],
                                "area": {"gates": 20, "regs": 0}, "latency": 1}),
        ("PriorityEncoder", "PriorityEncoder", {"tags": ["encode", "priority"], "interfaces": ["in_data", "out"],
                                                 "area": {"gates": 30, "regs": 0}, "latency": 1}),
        ("BarrelShifter", "BarrelShifter", {"tags": ["shift"], "interfaces": ["in_data", "out"],
                                            "area": {"gates": 100, "regs": 0}, "latency": 1}),
        ("LFSR", "LFSR", {"tags": ["pseudo-random"], "interfaces": ["clk", "rst", "out"],
                          "area": {"gates": 40, "regs": 32}, "latency": 1}),
        ("CRC", "CRC", {"tags": ["error-detection"], "interfaces": ["clk", "rst"],
                        "area": {"gates": 150, "regs": 32}, "latency": 1}),
        ("Divider", "Divider", {"tags": ["division"], "interfaces": ["dividend", "divisor"],
                                "area": {"gates": 500, "regs": 64}, "latency": 32}),
        ("RoundRobinArbiter", "RoundRobinArbiter", {"tags": ["arbitration", "round-robin"],
                                                     "interfaces": ["clk", "rst"], "area": {"gates": 80, "regs": 16}, "latency": 1}),
    ]
    for reg_name, var_name, meta_kw in _component_regs:
        cls = locals().get(var_name)
        if cls is not None:
            try:
                ComponentRegistry.register(reg_name, cls, ComponentMeta(**meta_kw))
            except Exception:
                pass


_register_all()


# =====================================================================
# TemplateRegistry — Behavior template registration for skills
# =====================================================================
# Skills register templates at import time:
#   from rtlgen.registry import TemplateRegistry
#   TemplateRegistry.register("rv64_core", my_template)

class TemplateRegistry:
    _templates: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str, fn: Callable):
        cls._templates[name] = fn

    @classmethod
    def get(cls, name: str) -> Optional[Callable]:
        return cls._templates.get(name)

    @classmethod
    def list(cls) -> List[str]:
        return list(cls._templates.keys())
