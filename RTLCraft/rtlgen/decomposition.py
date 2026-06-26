"""
rtlgen.decomposition — 行为级拆分与 DSL 实现框架

框架仅提供标准接口和仿真能力，**所有实现由智能体完成**。

设计原则:
  1. 行为级端口直接使用 DSL 的 Input/Output
  2. Spec 仅保留结构化描述，禁止自然语言
  3. 处理器架构参考 gem5 组件层次 (Board → Processor / CacheHierarchy / Memory / Device)
  4. 子模块策略 (StrategySpec) 指导 DSL 实现的方向
  5. 智能体实现行为模型、定义拆分、编写 DSL；框架提供仿真与对应管理

接口一览:
  BehavioralSpec       — 结构化行为级描述（端口 + 行为函数）
  ConnectionSpec       — 子模块连线
  StrategySpec         — 子模块实现策略（性能/功耗/面积/平衡）
  DecompositionResult  — 设计拆分容器
  SystemSimulator      — 系统级行为仿真引擎

  处理器架构 (gem5 风格):
    SystemSpec         — 完整系统描述
    BoardSpec          — 主板（总线 + 外设容器）
    ProcessorSpec      — CPU/GPU 核心描述
    CacheHierarchySpec — 缓存层次描述
    MemorySpec         — 内存描述
    DeviceSpec         — 外设描述

  桥接:
    submodule_to_spec    — BehavioralSpec → SpecIR
    generate_dsl_skeleton — BehavioralSpec → DSL Module 骨架

  参考模板:
    SubModuleTemplates   — 可选使用的行为级参考实现
"""
from __future__ import annotations

import hashlib
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.core import (
    BehavioralModule,
    BehavioralRTLPair,
    ModelRegistry,
    ModelVersion,
    Input,
    Output,
)
from rtlgen.spec_ir import SpecIR, PortSpec, FunctionSpec, InterfaceSpec, PPASpec, TimingSpec


def _port_spec(p) -> PortSpec:
    """从 Input/Output 端口提取 PortSpec。"""
    return PortSpec(name=p.name, direction="input" if isinstance(p, Input) else "output", width=p.width)


# =====================================================================
# 1.5 通用分解元数据（避免 decomposition_rules 循环导入）
# =====================================================================

@dataclass
class Transform:
    """通用分解变换，框架核心理解其类型以计算 latency / delay。"""
    type: str  # "partition" | "pipeline" | "parallelize" | "serialize" | "substitute" | "retime"
    params: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_partition(self) -> bool:
        return self.type == "partition"

    @property
    def is_pipeline(self) -> bool:
        return self.type == "pipeline"

    @property
    def is_parallelize(self) -> bool:
        return self.type == "parallelize"


@dataclass
class PhysicalHint:
    """物理 / 结构属性，用于预 PPA 估算。"""
    width: int = 0
    depth: int = 0
    num_states: int = 0
    num_requests: int = 0
    memory_depth: int = 0
    memory_width: int = 0
    operation: str = ""  # e.g. "multiplication", "addition", "mux"
    comb_depth_estimate: int = 0

    def estimate_logic_depth(self) -> int:
        if self.operation == "multiplication":
            return self.width * 2
        if self.operation == "addition":
            return self.width
        if self.operation == "mux":
            return self.num_requests.bit_length()
        if self.operation == "fsm":
            return self.num_states.bit_length()
        return self.comb_depth_estimate


@dataclass
class PPAViolation:
    """预 PPA 阶段发现的违规项。"""
    node_name: str
    issue: str
    suggestion: str
    severity: str = "warning"
    auto_fixable: bool = False
    estimated_logic_depth: int = 0
    target_logic_depth: int = 0

    def to_markdown(self) -> str:
        emoji = "❌" if self.severity == "error" else "⚠️"
        return (
            f"{emoji} **{self.node_name}**: {self.issue}\n"
            f"   - Suggestion: {self.suggestion}\n"
            f"   - Est. depth: {self.estimated_logic_depth} (target: {self.target_logic_depth})\n"
        )


# =====================================================================
# 1.7 结构化数据打包/解包工具（用于 SystemSimulator 的 flat-int 接口）
# =====================================================================

class DataPacker:
    """Pack/unpack structured data (arrays, matrices) to/from flat integers.

    SystemSimulator passes all port values as flat integers.  For image/video
    and other array-based algorithms, use these helpers to convert between
    structured Python data and the flat representation.
    """

    @staticmethod
    def unpack_2d(val: int, rows: int, cols: int, bits: int = 8, signed: bool = False):
        """Unpack flat integer into rows x cols list-of-lists."""
        mask = (1 << bits) - 1
        sign_bit = 1 << (bits - 1) if signed else 0
        arr = []
        for i in range(rows):
            row = []
            for j in range(cols):
                shift = (i * cols + j) * bits
                v = (val >> shift) & mask
                if signed and (v & sign_bit):
                    v -= (1 << bits)
                row.append(v)
            arr.append(row)
        return arr

    @staticmethod
    def pack_2d(arr, bits: int = 8, signed: bool = False):
        """Pack rows x cols list-of-lists into flat integer."""
        mask = (1 << bits) - 1
        val = 0
        rows = len(arr)
        cols = len(arr[0]) if rows > 0 else 0
        for i in range(rows):
            for j in range(cols):
                shift = (i * cols + j) * bits
                v = arr[i][j] & mask
                val |= v << shift
        return val

    @staticmethod
    def unpack_1d(val: int, length: int, bits: int = 8, signed: bool = False):
        """Unpack flat integer into 1D list."""
        mask = (1 << bits) - 1
        sign_bit = 1 << (bits - 1) if signed else 0
        result = []
        for i in range(length):
            v = (val >> (i * bits)) & mask
            if signed and (v & sign_bit):
                v -= (1 << bits)
            result.append(v)
        return result

    @staticmethod
    def pack_1d(arr, bits: int = 8, signed: bool = False):
        """Pack 1D list into flat integer."""
        mask = (1 << bits) - 1
        val = 0
        for i, v in enumerate(arr):
            val |= (v & mask) << (i * bits)
        return val

    @staticmethod
    def split_2d_to_blocks(arr, block_rows: int, block_cols: int):
        """Split a 2D array into non-overlapping blocks."""
        rows = len(arr)
        cols = len(arr[0]) if rows > 0 else 0
        blocks = []
        for bi in range(0, rows, block_rows):
            for bj in range(0, cols, block_cols):
                block = [
                    [arr[bi + i][bj + j] for j in range(block_cols)]
                    for i in range(block_rows)
                ]
                blocks.append(block)
        return blocks

    @staticmethod
    def merge_blocks_to_2d(blocks, block_rows: int, block_cols: int, out_rows: int, out_cols: int):
        """Merge non-overlapping blocks into a 2D array."""
        arr = [[0] * out_cols for _ in range(out_rows)]
        idx = 0
        for bi in range(0, out_rows, block_rows):
            for bj in range(0, out_cols, block_cols):
                block = blocks[idx]
                for i in range(block_rows):
                    for j in range(block_cols):
                        arr[bi + i][bj + j] = block[i][j]
                idx += 1
        return arr


# =====================================================================
# 2. 结构化行为级描述
# =====================================================================

@dataclass
class BehavioralSpec:
    """结构化行为级子模块描述。

    端口直接使用 DSL 的 Input/Output，行为函数由智能体实现。

    新增（层次化分解支持）:
      - children: 子分解节点列表，构成分解树
      - transform: 通用分解变换描述（框架核心理解）
      - physical: 物理/结构属性，用于预 PPA 估算
      - delay_cycles: 与 sibling 对齐所需的延迟周期数

    示例:
        BehavioralSpec(
            name="mac",
            inputs=[
                Input(16, "a"),
                Input(16, "b"),
                Input(32, "c"),
            ],
            outputs=[
                Output(32, "y"),
                Output(1, "done"),
            ],
            func=lambda inp: {"y": inp["a"] * inp["b"] + inp["c"], "done": 1},
            mod_type="algorithm",
            strategy=StrategySpec.timing(),
        )
    """
    name: str
    inputs: List[Input]
    outputs: List[Output]
    func: Callable[[dict], dict]
    mod_type: str = "algorithm"  # "processor" | "algorithm" | "interconnect" | "memory" | "io"
    strategy: Optional[StrategySpec] = None  # 实现策略（可选）
    latency: int = 0  # 流水线延迟周期数（0表示组合逻辑）

    # ---- hierarchical decomposition fields (NEW) ----
    children: List["BehavioralSpec"] = field(default_factory=list)
    transform: Optional[Any] = None   # Transform object from decomposition_rules
    physical: Optional[Any] = None    # PhysicalHint object from decomposition_rules
    delay_cycles: int = 0             # delay cycles to align with siblings in partition transform

    def to_port_tuples(self) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
        """转为 (name, width) 元组列表，用于构建 BehavioralModule。"""
        ins = [(p.name, p.width) for p in self.inputs]
        outs = [(p.name, p.width) for p in self.outputs]
        return ins, outs

    def to_behavioral_module(self) -> BehavioralModule:
        """转为 BehavioralModule，参与仿真。"""
        ins, outs = self.to_port_tuples()
        return BehavioralModule(
            name=self.name,
            inputs=ins,
            outputs=outs,
            func=self.func,
        )

    def port_list(self) -> List[PortSpec]:
        """转为 PortSpec 列表。"""
        return [_port_spec(p) for p in self.inputs] + [_port_spec(p) for p in self.outputs]


# =====================================================================
# 2.5 强制性文档框架
# =====================================================================
# 设计各阶段智能体必须填充的文档接口。
# 每个文档提供 validate() 检查必填字段，to_markdown() 输出 markdown。

@dataclass
class ModuleDoc:
    """子模块文档 — 每个子模块必须有。

    必填字段:
      purpose: 模块功能描述（一句话）
      port_description: 每个端口的用途说明
      behavior_description: 行为函数算法/逻辑描述
    """
    module_name: str
    purpose: str = ""
    port_description: Dict[str, str] = field(default_factory=dict)
    behavior_description: str = ""
    strategy_justification: str = ""  # 为什么选择该策略

    def validate(self) -> List[str]:
        """检查必填字段，返回缺失项列表。"""
        missing = []
        if not self.purpose:
            missing.append("purpose")
        if not self.behavior_description:
            missing.append("behavior_description")
        return missing

    def to_markdown(self) -> str:
        lines = [
            f"## Module: `{self.module_name}`",
            "",
            f"**Purpose**: {self.purpose}",
            "",
        ]
        if self.port_description:
            lines.append("### Port Description")
            lines.append("")
            for name, desc in self.port_description.items():
                lines.append(f"- **{name}**: {desc}")
            lines.append("")
        if self.behavior_description:
            lines.append("### Behavior")
            lines.append("")
            lines.append(self.behavior_description)
            lines.append("")
        if self.strategy_justification:
            lines.append("### Strategy Justification")
            lines.append("")
            lines.append(self.strategy_justification)
            lines.append("")
        return "\n".join(lines)


@dataclass
class TopLevelDoc:
    """顶层文档 — 整个设计的系统级描述。

    必填字段:
      overview: 系统概述
      decomposition_rationale: 拆分依据
      interconnect_description: 模块互连描述
    """
    design_name: str
    overview: str = ""
    decomposition_rationale: str = ""
    interconnect_description: str = ""
    system_requirements: str = ""  # 系统级需求/约束

    def validate(self) -> List[str]:
        missing = []
        if not self.overview:
            missing.append("overview")
        if not self.decomposition_rationale:
            missing.append("decomposition_rationale")
        if not self.interconnect_description:
            missing.append("interconnect_description")
        return missing

    def to_markdown(self) -> str:
        lines = [
            f"# {self.design_name} — Top-Level Design Document",
            "",
            "## Overview",
            "",
            self.overview or "*(not provided)*",
            "",
            "## Decomposition Rationale",
            "",
            self.decomposition_rationale or "*(not provided)*",
            "",
        ]
        if self.system_requirements:
            lines.append("## System Requirements")
            lines.append("")
            lines.append(self.system_requirements)
            lines.append("")
        lines.append("## Interconnect Description")
        lines.append("")
        lines.append(self.interconnect_description or "*(not provided)*")
        lines.append("")
        return "\n".join(lines)


@dataclass
class StrategyDoc:
    """策略文档 — 各子模块的策略选择和依据。

    必填字段:
      chosen_strategy: 策略名称
      justification: 选择依据
    """
    module_name: str
    chosen_strategy: str = ""
    justification: str = ""
    constraints_summary: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        missing = []
        if not self.chosen_strategy:
            missing.append("chosen_strategy")
        if not self.justification:
            missing.append("justification")
        return missing

    def to_markdown(self) -> str:
        lines = [
            f"## Strategy: `{self.module_name}`",
            "",
            f"- **Chosen Strategy**: {self.chosen_strategy}",
            "",
            f"- **Justification**: {self.justification}",
            "",
        ]
        if self.constraints_summary:
            lines.append("### Constraints Summary")
            lines.append("")
            for k, v in self.constraints_summary.items():
                lines.append(f"- `{k}`: `{v}`")
            lines.append("")
        return "\n".join(lines)


@dataclass
class SimulationResult:
    """单次仿真运行结果。"""
    inputs: Dict[str, int]
    expected_outputs: Dict[str, int]
    actual_outputs: Dict[str, int]
    passed: bool
    error_message: str = ""

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def to_markdown(self) -> str:
        status = self.status
        emoji = "✅" if self.passed else "❌"
        lines = [
            f"#### Test: {emoji} {status}",
            "",
            f"- **Inputs**: `{self.inputs}`",
            f"- **Expected**: `{self.expected_outputs}`",
            f"- **Actual**: `{self.actual_outputs}`",
        ]
        if self.error_message:
            lines.append(f"- **Error**: {self.error_message}")
        lines.append("")
        return "\n".join(lines)


@dataclass
class SimulationDoc:
    """仿真验证文档 — 行为级仿真后必须填充。

    必填字段:
      test_plan: 测试计划描述
      results: 仿真结果列表（至少一个）
    """
    design_name: str
    test_plan: str = ""
    results: List[SimulationResult] = field(default_factory=list)
    coverage_summary: str = ""
    conclusion: str = ""

    def validate(self) -> List[str]:
        missing = []
        if not self.test_plan:
            missing.append("test_plan")
        if not self.results:
            missing.append("results")
        return missing

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.pass_count / len(self.results)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.design_name} — Behavioral Simulation Report",
            "",
            "## Test Plan",
            "",
            self.test_plan or "*(not provided)*",
            "",
            "## Results Summary",
            "",
            f"- **Total**: {len(self.results)}",
            f"- **Passed**: {self.pass_count}",
            f"- **Failed**: {self.fail_count}",
            f"- **Pass Rate**: {self.pass_rate:.1%}",
            "",
        ]
        if self.results:
            lines.append("## Detailed Results")
            lines.append("")
            for i, result in enumerate(self.results, 1):
                lines.append(f"### Test Case {i}")
                lines.append("")
                lines.append(result.to_markdown())
        if self.coverage_summary:
            lines.append("## Coverage Summary")
            lines.append("")
            lines.append(self.coverage_summary)
            lines.append("")
        if self.conclusion:
            lines.append("## Conclusion")
            lines.append("")
            lines.append(self.conclusion)
            lines.append("")
        return "\n".join(lines)


@dataclass
class MicroArchDoc:
    """微架构文档 — 从行为级到 DSL 实现时必须填充。

    必填字段:
      architecture_description: 微架构描述
      state_machine_description: 状态机描述（如有）
      timing_analysis: 时序分析
    """
    module_name: str
    architecture_description: str = ""
    state_machine_description: str = ""
    timing_analysis: str = ""
    datapath_description: str = ""
    control_logic_description: str = ""
    ppa_estimates: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        missing = []
        if not self.architecture_description:
            missing.append("architecture_description")
        return missing

    def to_markdown(self) -> str:
        lines = [
            f"## Module: `{self.module_name}` — Microarchitecture",
            "",
            "### Architecture Description",
            "",
            self.architecture_description or "*(not provided)*",
            "",
        ]
        if self.datapath_description:
            lines.append("### Datapath")
            lines.append("")
            lines.append(self.datapath_description)
            lines.append("")
        if self.control_logic_description:
            lines.append("### Control Logic")
            lines.append("")
            lines.append(self.control_logic_description)
            lines.append("")
        if self.state_machine_description:
            lines.append("### State Machine")
            lines.append("")
            lines.append(self.state_machine_description)
            lines.append("")
        if self.timing_analysis:
            lines.append("### Timing Analysis")
            lines.append("")
            lines.append(self.timing_analysis)
            lines.append("")
        if self.ppa_estimates:
            lines.append("### PPA Estimates")
            lines.append("")
            for k, v in self.ppa_estimates.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")
        return "\n".join(lines)


@dataclass
class DesignDocBundle:
    """设计文档包 — 某一阶段所有文档的集合。

    提供 validate_all() 和 to_markdown() 方法。
    """
    name: str
    phase: str  # "decomposition" | "simulation" | "microarch"
    module_docs: List[ModuleDoc] = field(default_factory=list)
    top_level_doc: Optional[TopLevelDoc] = None
    strategy_docs: List[StrategyDoc] = field(default_factory=list)
    simulation_doc: Optional[SimulationDoc] = None
    microarch_docs: List[MicroArchDoc] = field(default_factory=list)

    def validate_all(self) -> Dict[str, List[str]]:
        """验证所有文档，返回 {doc_name: [missing_fields]}。"""
        issues = {}
        if self.top_level_doc:
            m = self.top_level_doc.validate()
            if m:
                issues["top_level"] = m
        for md in self.module_docs:
            m = md.validate()
            if m:
                issues[f"module:{md.module_name}"] = m
        for sd in self.strategy_docs:
            m = sd.validate()
            if m:
                issues[f"strategy:{sd.module_name}"] = m
        if self.simulation_doc:
            m = self.simulation_doc.validate()
            if m:
                issues["simulation"] = m
        for mad in self.microarch_docs:
            m = mad.validate()
            if m:
                issues[f"microarch:{mad.module_name}"] = m
        return issues

    def is_valid(self) -> bool:
        return len(self.validate_all()) == 0

    def to_markdown(self) -> str:
        parts = [
            f"# {self.name} — Design Documentation",
            f"**Phase**: {self.phase}",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
        ]
        if self.top_level_doc:
            parts.append(self.top_level_doc.to_markdown())
            parts.append("---\n")
        if self.module_docs:
            parts.append("## Module Documentation\n")
            for md in self.module_docs:
                parts.append(md.to_markdown())
            parts.append("---\n")
        if self.strategy_docs:
            parts.append("## Strategy Documentation\n")
            for sd in self.strategy_docs:
                parts.append(sd.to_markdown())
            parts.append("---\n")
        if self.simulation_doc:
            parts.append(self.simulation_doc.to_markdown())
            parts.append("---\n")
        if self.microarch_docs:
            parts.append("## Microarchitecture Documentation\n")
            for mad in self.microarch_docs:
                parts.append(mad.to_markdown())
            parts.append("---\n")
        return "\n".join(parts)

@dataclass
class ConnectionSpec:
    """子模块之间的连线。

    (source_module, source_port) → (dest_module, dest_port)
    """
    src_module: str
    src_port: str
    dst_module: str
    dst_port: str
    delay_cycles: int = 0  # 连线延迟周期数（用于行为级仿真中对齐流水线）


# =====================================================================
# 3. 子模块实现策略
# =====================================================================

_STRATEGY_GUIDANCE = {
    "timing_first": (
        "性能优先：以最高时钟频率和最关键路径延迟为首要目标。\n"
        "DSL 实现指导：\n"
        "  - 允许插入流水线寄存器，即使增加面积\n"
        "  - 关键路径上的算子选用最快实现（如 Wallace 乘法器、进位选择加法器）\n"
        "  - 禁止资源共享（resource_sharing = False），避免多路复用器增加延迟\n"
        "  - 组合逻辑深度不超过 3 级，超过则必须流水线化\n"
        "  - FSM 使用 one-hot 编码以获得最快状态解码\n"
        "  - 允许时钟使能，不强制时钟门控\n"
        "  - 【强制】所有带时钟的流水线模块必须实现 valid_in / valid_out 流控接口；"
        "    寄存器仅在 valid_in=1 时更新数据，valid_out 反映数据有效延迟"
    ),
    "power_first": (
        "功耗优先：以降低动态功耗和静态功耗为首要目标。\n"
        "DSL 实现指导：\n"
        "  - 所有寄存器必须支持时钟门控（clock_gating = True），仅在数据变化时启用时钟\n"
        "  - 优先使用 Booth 乘法器（减少部分积数量，降低翻转率）\n"
        "  - FSM 使用 Gray 编码（单比特状态转换，降低总线翻转）\n"
        "  - 允许资源共享以减少活跃电路数量\n"
        "  - 输出寄存器在空闲时必须保持上一周期值（禁止无意义的 0 写入）\n"
        "  - 多路复用器使用平衡树结构减少扇出"
    ),
    "area_first": (
        "面积优先：以最小化门数和寄存器数量为首位目标。\n"
        "DSL 实现指导：\n"
        "  - 允许资源共享（resource_sharing = True），多个算子共用同一硬件\n"
        "  - 使用 Ripple Carry 加法器和 Array 乘法器（最小面积实现）\n"
        "  - FSM 使用 binary 编码（最少的寄存器数量）\n"
        "  - 尽可能减少流水线级数，接受较长的组合路径\n"
        "  - 位宽按实际需要的最小值分配，禁止过度宽的信号\n"
        "  - 使用多周期实现替代并行计算"
    ),
    "balanced": (
        "平衡：在性能、面积、功耗之间取得合理平衡。\n"
        "DSL 实现指导：\n"
        "  - 关键路径不超过 4 级组合逻辑\n"
        "  - 默认使用 Ripple Carry 加法器和 Array 乘法器\n"
        "  - 允许轻量级资源共享（2-3 个相似算子可共享）\n"
        "  - FSM 编码根据状态数自动选择（<=4 用 one-hot，>4 用 binary）\n"
        "  - 寄存器按需添加，不做激进的时钟门控\n"
        "  - 位宽按接口定义推导，内部信号可适度截断\n"
        "  - 【强制】所有带时钟的流水线模块必须实现 valid_in / valid_out 流控接口；"
        "    寄存器仅在 valid_in=1 时更新数据，valid_out 反映数据有效延迟"
    ),
}


@dataclass
class StrategySpec:
    """子模块的实现策略。

    策略为智能体的 DSL 实现提供具体指导。
    预定义的四种策略（timing_first / power_first / area_first / balanced）
    包含具体的文本解释描述，智能体可以在此基础上自定义。

    示例:
        # 使用预定义策略
        strategy = StrategySpec.timing("timing_first")
        strategy = StrategySpec.area_first()
        strategy = StrategySpec.balanced()

        # 自定义策略
        strategy = StrategySpec(
            name="low_latency_mac",
            priority="timing_first",
            guidance="该 MAC 单元必须在 1 个时钟周期内完成。\\n"
                     "使用 Wallace 树乘法器，进位前瞻加法器。\\n"
                     "禁止流水线。",
            constraints={
                "max_logic_depth": 3,
                "pipeline_stages": 1,
                "resource_sharing": False,
            },
        )
    """
    name: str
    priority: str       # "timing_first" | "power_first" | "area_first" | "balanced" | custom
    guidance: str       # 具体文本解释，指导 DSL 实现
    constraints: Dict[str, Any] = field(default_factory=dict)  # 可选的数值约束

    @classmethod
    def timing(cls, custom_guidance: str = "") -> "StrategySpec":
        """性能优先策略。"""
        return cls(
            name="timing_first",
            priority="timing_first",
            guidance=custom_guidance or _STRATEGY_GUIDANCE["timing_first"],
            constraints={
                "max_logic_depth": 3,
                "max_comb_arithmetic_width": 32,
                "resource_sharing": False,
                "fsm_encoding": "one_hot",
            },
        )

    @classmethod
    def power(cls, custom_guidance: str = "") -> "StrategySpec":
        """功耗优先策略。"""
        return cls(
            name="power_first",
            priority="power_first",
            guidance=custom_guidance or _STRATEGY_GUIDANCE["power_first"],
            constraints={
                "clock_gating": True,
                "resource_sharing": True,
                "fsm_encoding": "gray",
            },
        )

    @classmethod
    def area(cls, custom_guidance: str = "") -> "StrategySpec":
        """面积优先策略。"""
        return cls(
            name="area_first",
            priority="area_first",
            guidance=custom_guidance or _STRATEGY_GUIDANCE["area_first"],
            constraints={
                "max_logic_depth": 8,
                "resource_sharing": True,
                "fsm_encoding": "binary",
            },
        )

    @classmethod
    def balanced(cls, custom_guidance: str = "") -> "StrategySpec":
        """平衡策略。"""
        return cls(
            name="balanced",
            priority="balanced",
            guidance=custom_guidance or _STRATEGY_GUIDANCE["balanced"],
            constraints={
                "max_logic_depth": 4,
                "max_comb_arithmetic_width": 32,
                "resource_sharing": True,
                "fsm_encoding": "auto",
            },
        )

    @property
    def guidance_text(self) -> str:
        """获取策略的文本解释（用于传递给智能体）。"""
        return self.guidance


@dataclass
class DecompositionResult:
    """设计拆分结果容器。

    智能体通过 add_submodule() / add_connection() 填充，
    调用 simulate() 验证。

    示例:
        result = DecompositionResult(design_name="MAC16", design_type="algorithm")
        result.add_submodule(mac_spec)
        result.add_connection(ConnectionSpec(...))
        sim = result.simulate([{"a": 3, "b": 4, "c": 10}])
        result.register_pairs()
    """
    design_name: str
    design_type: str  # "processor" | "algorithm"
    submodules: List[BehavioralSpec] = field(default_factory=list)
    connections: List[ConnectionSpec] = field(default_factory=list)
    top_inputs: List[Input] = field(default_factory=list)
    top_outputs: List[Output] = field(default_factory=list)
    spec_hash: str = ""

    # 文档接口（智能体必须填充）
    top_level_doc: Optional[TopLevelDoc] = None
    module_docs: List[ModuleDoc] = field(default_factory=list)
    strategy_docs: List[StrategyDoc] = field(default_factory=list)
    simulation_doc: Optional[SimulationDoc] = None
    microarch_docs: List[MicroArchDoc] = field(default_factory=list)

    def add_submodule(self, spec: BehavioralSpec) -> "DecompositionResult":
        """添加子模块。"""
        self.submodules.append(spec)
        return self

    def add_connection(self, conn: ConnectionSpec) -> "DecompositionResult":
        """添加连线。"""
        self.connections.append(conn)
        return self

    def set_top_ports(
        self,
        inputs: List[Input],
        outputs: List[Output],
    ) -> "DecompositionResult":
        """设置顶层端口。"""
        self.top_inputs = inputs
        self.top_outputs = outputs
        return self

    def compute_hash(self) -> str:
        """计算拆分哈希。"""
        data = {
            "name": self.design_name,
            "type": self.design_type,
            "submodules": [(s.name, s.mod_type) for s in self.submodules],
            "connections": [(c.src_module, c.dst_module) for c in self.connections],
        }
        self.spec_hash = hashlib.md5(repr(data).encode()).hexdigest()[:8]
        return self.spec_hash

    def register_pairs(self) -> List[BehavioralRTLPair]:
        """注册行为级-RTL 对应。"""
        pairs = []
        for sm in self.submodules:
            beh = sm.to_behavioral_module()
            pair = BehavioralRTLPair(
                name=sm.name,
                behavioral=beh,
                rtl=beh,
                beh_version=ModelVersion(0, 1, 0),
                rtl_version=ModelVersion(0, 0, 0),
                spec_hash=self.spec_hash,
                notes=f"Submodule of {self.design_name} ({self.design_type})",
            )
            ModelRegistry.register_pair(pair)
            pairs.append(pair)
        return pairs

    # ------------------------------------------------------------------
    # 文档生成接口
    # ------------------------------------------------------------------

    def generate_decomposition_doc(self) -> DesignDocBundle:
        """Phase 1 文档包：顶层文档 + 各模块文档 + 策略文档。

        返回 DesignDocBundle，调用 to_markdown() 输出，
        调用 is_valid() 检查强制性字段。
        """
        return DesignDocBundle(
            name=self.design_name,
            phase="decomposition",
            module_docs=list(self.module_docs),
            top_level_doc=self.top_level_doc,
            strategy_docs=list(self.strategy_docs),
        )

    def generate_simulation_doc(self) -> DesignDocBundle:
        """Phase 1b 仿真文档包。

        返回包含仿真报告的设计文档包。
        """
        return DesignDocBundle(
            name=self.design_name,
            phase="simulation",
            simulation_doc=self.simulation_doc,
        )

    def generate_microarch_doc(self) -> DesignDocBundle:
        """Phase 2 微架构文档包。

        返回从行为级到 DSL 实现的微架构文档。
        """
        return DesignDocBundle(
            name=self.design_name,
            phase="microarch",
            microarch_docs=list(self.microarch_docs),
        )

    def generate_full_doc(self) -> DesignDocBundle:
        """所有阶段完整文档包。"""
        return DesignDocBundle(
            name=self.design_name,
            phase="full",
            module_docs=list(self.module_docs),
            top_level_doc=self.top_level_doc,
            strategy_docs=list(self.strategy_docs),
            simulation_doc=self.simulation_doc,
            microarch_docs=list(self.microarch_docs),
        )

    def validate_decomposition_docs(self) -> Dict[str, List[str]]:
        """验证 Phase 1 强制性文档字段。

        返回 {doc_name: [missing_fields]}，空字典表示全部通过。
        """
        issues = {}
        if self.top_level_doc:
            m = self.top_level_doc.validate()
            if m:
                issues["top_level"] = m
        else:
            issues["top_level"] = ["TopLevelDoc not provided"]
        for md in self.module_docs:
            m = md.validate()
            if m:
                issues[f"module:{md.module_name}"] = m
        for sd in self.strategy_docs:
            m = sd.validate()
            if m:
                issues[f"strategy:{sd.module_name}"] = m
        return issues

    def simulate(self, test_inputs: List[dict], cycles: int = 1) -> List[dict]:
        """系统级行为仿真（通过 SystemSimulator）。

        参数:
            test_inputs: 测试输入列表
            cycles: 仿真周期数（默认 1，流水线设计需要更多周期）
        """
        sim = SystemSimulator(self)
        return sim.run(test_inputs, cycles=cycles)

    def simulate_with_report(self, test_inputs: List[dict],
                             test_plan: str = "",
                             expected_outputs: Optional[List[Dict[str, int]]] = None,
                             cycles: int = 1) -> SimulationDoc:
        """系统级行为仿真并生成仿真文档。

        仿真结果自动存入 self.simulation_doc，调用 to_markdown() 输出。

        参数:
            test_inputs: 测试输入列表
            test_plan: 测试计划描述
            expected_outputs: 期望输出（可选）
            cycles: 仿真周期数（默认 1，流水线设计需要更多周期）

        示例:
            sim_doc = result.simulate_with_report(
                test_inputs=[{"a": 3, "b": 4, "c": 10}],
                test_plan="Basic MAC functional test",
                expected_outputs=[{"y": 22, "done": 1}],
            )
            print(sim_doc.to_markdown())
        """
        sim = SystemSimulator(self)
        safe_expected = expected_outputs if expected_outputs is not None else [{} for _ in range(len(test_inputs))]
        results = sim.run_with_expected(test_inputs, safe_expected, cycles=cycles)

        sim_results = []
        for i, r in enumerate(results):
            expected = safe_expected[i]
            passed = True
            error_msg = ""
            if expected:
                for key, exp_val in expected.items():
                    actual_val = r["outputs"].get(key, 0)
                    if actual_val != exp_val:
                        passed = False
                        error_msg = f"{key}: expected {exp_val}, got {actual_val}"
                        break
            sim_results.append(SimulationResult(
                inputs=r["inputs"],
                expected_outputs=expected,
                actual_outputs=r["outputs"],
                passed=passed,
                error_message=error_msg,
            ))

        self.simulation_doc = SimulationDoc(
            design_name=self.design_name,
            test_plan=test_plan or f"Behavioral simulation of {self.design_name}",
            results=sim_results,
        )
        return self.simulation_doc

    # ------------------------------------------------------------------
    # 结构化文档生成
    # ------------------------------------------------------------------

    def write_design_doc(self, output_dir: str = ".") -> Dict[str, str]:
        """生成结构化全局设计和详细设计文档，输出到文件。

        返回 {filename: content} 字典。

        输出文件:
          - {name}_design.md       — 全局设计文档（顶层 + 模块 + 策略）
          - {name}_detailed.md     — 详细设计文档（微架构）
          - {name}_test_report.md  — 测试报告（仿真结果）
          - {name}_full.md         — 完整文档（全部合并）
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        files = {}

        # 全局设计文档
        design_bundle = self.generate_decomposition_doc()
        if design_bundle.is_valid():
            md = design_bundle.to_markdown()
            fname = os.path.join(output_dir, f"{self.design_name}_design.md")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(md)
            files[fname] = md

        # 详细设计文档
        detailed_bundle = self.generate_microarch_doc()
        if detailed_bundle.is_valid():
            md = detailed_bundle.to_markdown()
            fname = os.path.join(output_dir, f"{self.design_name}_detailed.md")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(md)
            files[fname] = md

        # 测试报告
        if self.simulation_doc:
            test_bundle = self.generate_simulation_doc()
            md = test_bundle.to_markdown()
            fname = os.path.join(output_dir, f"{self.design_name}_test_report.md")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(md)
            files[fname] = md

        # 完整文档
        full_bundle = self.generate_full_doc()
        if full_bundle.is_valid():
            md = full_bundle.to_markdown()
            fname = os.path.join(output_dir, f"{self.design_name}_full.md")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(md)
            files[fname] = md

        return files

    def summary(self) -> Dict[str, Any]:
        """拆分摘要。"""
        return {
            "design": f"{self.design_name} ({self.design_type})",
            "submodules": [
                {
                    "name": s.name,
                    "type": s.mod_type,
                    "inputs": [(p.name, p.width) for p in s.inputs],
                    "outputs": [(p.name, p.width) for p in s.outputs],
                }
                for s in self.submodules
            ],
            "connections": [
                {"from": f"{c.src_module}.{c.src_port}", "to": f"{c.dst_module}.{c.dst_port}"}
                for c in self.connections
            ],
            "top_inputs": [(p.name, p.width) for p in self.top_inputs],
            "top_outputs": [(p.name, p.width) for p in self.top_outputs],
        }


# =====================================================================
# 3. 系统级仿真器
# =====================================================================

class SystemSimulator:
    """系统级行为仿真引擎（支持流水线延迟建模）。

    智能体用法:
        sim = SystemSimulator(result)
        sim.set_inputs({"a": 3, "b": 4, "c": 10})
        for _ in range(latency):
            outputs = sim.step()
    """

    def __init__(self, result: DecompositionResult):
        self.result = result
        self._signals: Dict[str, int] = {}
        self._cycle = 0
        from collections import deque
        # 每个子模块的输出延迟队列: {module_name: deque[(remaining_cycles, outputs_dict)]}
        self._latency_queues: Dict[str, Any] = {}
        # 连线延迟队列: {conn_key: deque[(remaining_cycles, value)]}
        self._conn_queues: Dict[str, Any] = {}
        self._init_queues()

    def _init_queues(self):
        from collections import deque
        for sm in self.result.submodules:
            self._latency_queues[sm.name] = deque()
        for conn in self.result.connections:
            key = f"{conn.src_module}.{conn.src_port}->{conn.dst_module}.{conn.dst_port}"
            self._conn_queues[key] = deque()

    def set_inputs(self, inputs: dict):
        """设置顶层输入。"""
        self._signals.update(inputs)

    def step(self) -> Dict[str, int]:
        """执行一个仿真周期（考虑子模块latency和连线delay）。"""
        from collections import deque

        # --- 1. 处理连线延迟队列（到期的值写入信号表临时区）---
        conn_arrivals: Dict[str, int] = {}
        for conn in self.result.connections:
            key = f"{conn.src_module}.{conn.src_port}->{conn.dst_module}.{conn.dst_port}"
            q = self._conn_queues[key]
            arrived = []
            remaining = deque()
            for item in q:
                rem, val = item
                rem -= 1
                if rem <= 0:
                    arrived.append(val)
                else:
                    remaining.append((rem, val))
            self._conn_queues[key] = remaining
            if arrived:
                conn_arrivals[key] = arrived[-1]

        # --- 2. 处理子模块延迟队列（到期的输出写入信号表）---
        for sm in self.result.submodules:
            q = self._latency_queues[sm.name]
            arrived_outputs = []
            remaining = deque()
            for item in q:
                rem, outputs = item
                rem -= 1
                if rem <= 0:
                    arrived_outputs.append(outputs)
                else:
                    remaining.append((rem, outputs))
            self._latency_queues[sm.name] = remaining
            if arrived_outputs:
                for port in sm.outputs:
                    self._signals[f"{sm.name}.{port.name}"] = arrived_outputs[-1].get(port.name, 0)

        # --- 3. 计算各子模块输入（优先使用连线延迟值，其次直接信号）---
        module_input_dicts: Dict[str, Dict[str, int]] = {}
        for sm in self.result.submodules:
            module_inputs = {}
            for port in sm.inputs:
                value = self._signals.get(port.name, 0)
                for conn in self.result.connections:
                    if conn.dst_module == sm.name and conn.dst_port == port.name:
                        key = f"{conn.src_module}.{conn.src_port}->{conn.dst_module}.{conn.dst_port}"
                        src_key = f"{conn.src_module}.{conn.src_port}"
                        if key in conn_arrivals:
                            value = conn_arrivals[key]
                        elif src_key in self._signals:
                            value = self._signals[src_key]
                module_inputs[port.name] = value
            module_input_dicts[sm.name] = module_inputs

        # --- 4. 执行子模块行为函数 ---
        for sm in self.result.submodules:
            outputs = sm.func(module_input_dicts[sm.name])
            latency = sm.latency
            if latency > 0:
                self._latency_queues[sm.name].append((latency, outputs))
            else:
                for port in sm.outputs:
                    self._signals[f"{sm.name}.{port.name}"] = outputs.get(port.name, 0)

        # --- 5. 将子模块输出推入连线延迟队列 ---
        for conn in self.result.connections:
            key = f"{conn.src_module}.{conn.src_port}->{conn.dst_module}.{conn.dst_port}"
            src_key = f"{conn.src_module}.{conn.src_port}"
            if src_key in self._signals:
                val = self._signals[src_key]
                delay = conn.delay_cycles
                if delay > 0:
                    self._conn_queues[key].append((delay, val))

        self._cycle += 1
        return {k: v for k, v in self._signals.items() if "." in k}

    def get_outputs(self) -> Dict[str, int]:
        """获取输出。"""
        return {k: v for k, v in self._signals.items() if "." in k}

    def run(self, test_inputs: List[dict], cycles: int = 1) -> List[dict]:
        """运行多组测试（每组连续运行cycles个周期）。"""
        results = []
        for inputs in test_inputs:
            self._signals.clear()
            self._init_queues()
            self._cycle = 0
            self._signals.update(inputs)
            for _ in range(cycles):
                outputs = self.step()
            results.append({"inputs": inputs, "outputs": dict(outputs), "cycles": cycles})
        return results

    def run_pipeline(self, test_inputs: List[dict], warmup_cycles: int = 0) -> List[dict]:
        """流水线模式：每个周期注入一个输入，收集所有周期输出。

        适用于验证吞吐量和latency。
        """
        self._signals.clear()
        self._init_queues()
        self._cycle = 0
        results = []
        for _ in range(warmup_cycles):
            self.step()
        for inputs in test_inputs:
            self._signals.update(inputs)
            self.step()
            results.append({
                "cycle": self._cycle - 1,
                "inputs": dict(inputs),
                "outputs": dict(self.get_outputs()),
            })
        return results

    def run_with_expected(self, test_inputs: List[dict],
                          expected_outputs: List[dict],
                          cycles: int = 1) -> List[dict]:
        """运行多组测试，保留原始输出用于文档生成。

        返回与 run() 相同格式的结果，但包含完整信号状态。
        """
        results = []
        for inputs in test_inputs:
            self._signals.clear()
            self._init_queues()
            self._cycle = 0
            self._signals.update(inputs)
            for _ in range(cycles):
                self.step()
            outputs = {k: v for k, v in self._signals.items() if "." in k}
            results.append({"inputs": inputs, "outputs": outputs, "cycles": cycles})
        return results


# =====================================================================
# 4. gem5 风格处理器架构描述
# =====================================================================
# 参考 gem5 组件层次:
#   System
#     → Board
#       → Processor (CPU core(s), ISA, pipeline config)
#       → CacheHierarchy (L1I, L1D, L2, bus topology)
#       → Memory (DRAM, address range)
#       → Device (UART, GPIO, Disk, Ethernet)

@dataclass
class CoreSpec:
    """处理器核心描述（参考 gem5 BaseCPU / BaseMinorCPU）。"""
    name: str
    isa: str = "riscv"               # "riscv" | "arm" | "x86" | "mips"
    core_model: str = "simple"       # "simple" | "inorder" | "o3" | "minor"
    num_threads: int = 1
    clock: str = "1GHz"

    # 流水线参数（参考 gem5 MinorCPU params）
    fetch_width: int = 64            # 取指宽度 (bits)
    decode_width: int = 4            # 译码宽度
    execute_width: int = 4           # 执行宽度
    commit_width: int = 4            # 提交宽度
    num_pipeline_stages: int = 4     # 流水线级数

    # 功能单元（参考 gem5 FUPool）
    num_int_alus: int = 2
    num_fp_alus: int = 0
    num_mem_ports: int = 2
    has_branch_pred: bool = True
    branch_pred_type: str = "tournament"  # "tournament" | "gshare" | "bimodal"

    # 寄存器文件
    int_regs: int = 32               # 整数寄存器数量
    fp_regs: int = 32                # 浮点寄存器数量

    # 行为函数 (inputs_dict → outputs_dict)
    func: Optional[Callable[[dict], dict]] = None

    def to_behavioral_spec(self, extra_inputs: Optional[List[Input]] = None,
                           extra_outputs: Optional[List[Output]] = None) -> BehavioralSpec:
        """将核心描述转为 BehavioralSpec。"""
        inputs = [
            Input(32, "instruction"),
            Input(32, "pc_in"),
            Input(1, "reset"),
            Input(1, "interrupt"),
        ]
        outputs = [
            Output(32, "addr"),
            Output(32, "reg_out"),
            Output(1, "write_en"),
            Output(32, "write_data"),
        ]
        if extra_inputs:
            inputs.extend(extra_inputs)
        if extra_outputs:
            outputs.extend(extra_outputs)

        func = self.func or (lambda inp: {
            "addr": inp.get("pc_in", 0) & 0xFFFFFFFF,
            "reg_out": 0,
            "write_en": 0,
            "write_data": 0,
        })

        return BehavioralSpec(
            name=self.name,
            inputs=inputs,
            outputs=outputs,
            func=func,
            mod_type="processor",
        )


@dataclass
class CacheHierarchySpec:
    """缓存层次描述（参考 gem5 CacheHierarchy / BaseCache）。"""
    name: str = "cache_hierarchy"

    # L1 指令缓存
    l1i_size: int = 32768            # bytes
    l1i_assoc: int = 8
    l1i_linesize: int = 64           # bytes
    l1i_latency: int = 1             # cycles

    # L1 数据缓存
    l1d_size: int = 32768
    l1d_assoc: int = 8
    l1d_linesize: int = 64
    l1d_latency: int = 1

    # L2 缓存
    l2_present: bool = False
    l2_size: int = 262144
    l2_assoc: int = 8
    l2_linesize: int = 64
    l2_latency: int = 10

    # 替换策略
    replacement_policy: str = "lru"  # "lru" | "fifo" | "random"

    # 总线拓扑
    bus_type: str = "crossbar"       # "crossbar" | "point_to_point" | "mesh"

    def to_behavioral_spec(self) -> BehavioralSpec:
        """缓存层次的行为级模型（理想缓存）。"""
        def cache_func(inputs: dict) -> dict:
            # 理想行为：直接透传
            return {
                "hit": 1,
                "data_out": inputs.get("data_in", 0),
                "ready": 1,
            }

        return BehavioralSpec(
            name=self.name,
            inputs=[
                Input(32, "addr"),
                Input(32, "data_in"),
                Input(1, "read_req"),
                Input(1, "write_req"),
            ],
            outputs=[
                Output(1, "hit"),
                Output(32, "data_out"),
                Output(1, "ready"),
            ],
            func=cache_func,
            mod_type="memory",
        )


@dataclass
class MemorySpec:
    """内存描述（参考 gem5 DRAM / SimpleMemory）。"""
    name: str = "main_memory"
    size_mb: int = 256               # MB
    bandwidth: int = 16              # bytes/cycle
    latency: int = 50                # cycles (row hit)
    memory_type: str = "ddr3"        # "ddr3" | "ddr4" | "lpddr5" | "sram"

    def to_behavioral_spec(self, init_data: Optional[Dict[int, int]] = None) -> BehavioralSpec:
        """内存的行为级模型。"""
        mem = dict(init_data) if init_data else {}

        def mem_func(inputs: dict) -> dict:
            addr = inputs.get("addr", 0)
            read = inputs.get("read_req", 0)
            write = inputs.get("write_req", 0)
            data_in = inputs.get("data_in", 0)

            if write:
                mem[addr] = data_in
                return {"data_out": 0, "ready": 1, "error": 0}
            elif read:
                return {"data_out": mem.get(addr, 0), "ready": 1, "error": 0}
            return {"data_out": 0, "ready": 1, "error": 0}

        return BehavioralSpec(
            name=self.name,
            inputs=[
                Input(32, "addr"),
                Input(32, "data_in"),
                Input(1, "read_req"),
                Input(1, "write_req"),
            ],
            outputs=[
                Output(32, "data_out"),
                Output(1, "ready"),
                Output(1, "error"),
            ],
            func=mem_func,
            mod_type="memory",
        )


@dataclass
class DeviceSpec:
    """外设描述（参考 gem5 的 UART / RealView / PL011 等）。"""
    name: str
    device_type: str                 # "uart" | "gpio" | "disk" | "ethernet" | "interrupt_ctrl" | "timer"
    interrupt_id: int = 0
    mmio_addr: int = 0               # memory-mapped I/O base address

    # 行为函数
    func: Optional[Callable[[dict], dict]] = None

    def to_behavioral_spec(self) -> BehavioralSpec:
        """转为 BehavioralSpec。"""
        defaults = self._default_ports()
        func = self.func or defaults["func"]
        return BehavioralSpec(
            name=self.name,
            inputs=defaults["inputs"],
            outputs=defaults["outputs"],
            func=func,
            mod_type="io",
        )

    def _default_ports(self) -> Dict[str, Any]:
        if self.device_type == "uart":
            return {
                "inputs": [Input(8, "tx_data"), Input(1, "tx_start")],
                "outputs": [Output(1, "tx_line"), Output(1, "tx_busy"), Output(1, "tx_done")],
                "func": lambda inp: {"tx_line": 0, "tx_busy": 1, "tx_done": 0} if inp.get("tx_start") else {"tx_line": 1, "tx_busy": 0, "tx_done": 1},
            }
        elif self.device_type == "gpio":
            return {
                "inputs": [Input(8, "data_out"), Input(8, "dir")],
                "outputs": [Output(8, "pin_state")],
                "func": lambda inp: {"pin_state": inp.get("data_out", 0) & inp.get("dir", 0)},
            }
        elif self.device_type == "interrupt_ctrl":
            return {
                "inputs": [Input(1, "irq"), Input(1, "fiq"), Input(16, "source_id")],
                "outputs": [Output(1, "cpu_irq"), Output(1, "cpu_fiq"), Output(16, "ack_id")],
                "func": lambda inp: {"cpu_irq": inp.get("irq", 0), "cpu_fiq": inp.get("fiq", 0), "ack_id": inp.get("source_id", 0)},
            }
        else:
            return {
                "inputs": [Input(32, "data_in")],
                "outputs": [Output(32, "data_out")],
                "func": lambda inp: {"data_out": inp.get("data_in", 0)},
            }


@dataclass
class BoardSpec:
    """主板描述（参考 gem5 BaseBoard）。

    容器：总线互连 + 外设集合
    """
    name: str = "board"
    bus_type: str = "axi"            # "axi" | "apb" | "ahb" | "simple"
    num_masters: int = 1
    num_slaves: int = 2
    devices: List[DeviceSpec] = field(default_factory=list)

    def add_device(self, dev: DeviceSpec) -> "BoardSpec":
        self.devices.append(dev)
        return self


@dataclass
class ProcessorSpec:
    """处理器系统描述（参考 gem5 的 System 中处理器部分）。

    包含一个或多个 CPU 核心 + 缓存层次。

    示例:
        proc = ProcessorSpec(
            name="riscv_soc",
            cores=[CoreSpec("core0", isa="riscv", core_model="simple")],
            cache=CacheHierarchySpec(l1i_size=32768, l1d_size=32768, l2_present=True),
            board=BoardSpec(devices=[
                DeviceSpec("uart0", "uart", mmio_addr=0x10000000),
                DeviceSpec("gpio0", "gpio", mmio_addr=0x20000000),
            ]),
            memory=MemorySpec(size_mb=256),
        )
    """
    name: str
    cores: List[CoreSpec]
    cache: Optional[CacheHierarchySpec] = None
    board: Optional[BoardSpec] = None
    memory: Optional[MemorySpec] = None

    def to_submodules(self) -> List[BehavioralSpec]:
        """将处理器系统拆分为子模块 BehavioralSpec 列表。

        智能体可调用此方法获取建议的子模块列表，
        然后在此基础上修改、添加自定义模块。
        """
        modules = []

        # Core(s)
        for core in self.cores:
            modules.append(core.to_behavioral_spec())

        # Cache hierarchy
        if self.cache:
            modules.append(self.cache.to_behavioral_spec())

        # Memory
        if self.memory:
            modules.append(self.memory.to_behavioral_spec())

        # Devices
        if self.board:
            for dev in self.board.devices:
                modules.append(dev.to_behavioral_spec())

        return modules


@dataclass
class SystemSpec:
    """完整系统描述（参考 gem5 的 System 层次）。

    这是处理器/SoC 设计的顶层结构化描述。

    示例:
        system = SystemSpec(
            name="RISCV_SoC",
            processor=ProcessorSpec(
                name="cpu_complex",
                cores=[CoreSpec("core0", isa="riscv")],
                cache=CacheHierarchySpec(l2_present=True),
                memory=MemorySpec(size_mb=256),
                board=BoardSpec(devices=[
                    DeviceSpec("uart0", "uart"),
                    DeviceSpec("gpio0", "gpio"),
                ]),
            ),
        )

        # 获取建议的子模块列表
        submodules = system.to_submodules()

        # 或手动构建 DecompositionResult
        result = DecompositionResult(...)
        for sm in submodules:
            result.add_submodule(sm)
    """
    name: str
    processor: ProcessorSpec

    def to_submodules(self) -> List[BehavioralSpec]:
        """获取建议的子模块列表。"""
        return self.processor.to_submodules()


# =====================================================================
# 5. 参考模板库（智能体可选使用）
# =====================================================================

class SubModuleTemplates:
    """预定义行为级参考模板。

    智能体可以：
    1. 直接使用模板
    2. 基于模板修改
    3. 完全自己编写

    所有模板使用 Input/Output 声明端口，与 DSL 完全一致。
    """

    @staticmethod
    def riscv_cpu(name: str = "cpu") -> BehavioralSpec:
        """RISC-V CPU 参考行为模型。"""
        return BehavioralSpec(
            name=name,
            inputs=[
                Input(32, "instruction"),
                Input(32, "pc_in"),
                Input(1, "reset"),
                Input(1, "interrupt"),
            ],
            outputs=[
                Output(32, "addr"),
                Output(32, "reg_out"),
                Output(1, "write_en"),
                Output(32, "write_data"),
            ],
            func=lambda inp: {
                "addr": inp.get("pc_in", 0) & 0xFFFFFFFF,
                "reg_out": 0,
                "write_en": 0,
                "write_data": 0,
            },
            mod_type="processor",
        )

    @staticmethod
    def mac_unit(name: str = "mac", width: int = 16) -> BehavioralSpec:
        """MAC 单元参考行为模型。"""
        return BehavioralSpec(
            name=name,
            inputs=[
                Input(width, "a"),
                Input(width, "b"),
                Input(width * 2, "c"),
            ],
            outputs=[
                Output(width * 2, "y"),
                Output(1, "done"),
            ],
            func=lambda inp: {
                "y": (inp["a"] * inp["b"] + inp["c"]) & ((1 << (width * 2)) - 1),
                "done": 1,
            },
            mod_type="algorithm",
        )

    @staticmethod
    def filter_2d(name: str = "fir", width: int = 16,
                  taps: int = 5, coeffs: Optional[List[int]] = None) -> BehavioralSpec:
        """FIR 滤波器参考行为模型。"""
        c = coeffs or [1] * taps
        return BehavioralSpec(
            name=name,
            inputs=[Input(width, f"pixel_{i}") for i in range(taps)],
            outputs=[Output(width, "filtered"), Output(1, "valid")],
            func=lambda inp: {
                "filtered": sum(inp.get(f"pixel_{i}", 0) * c[i] for i in range(taps)) & ((1 << width) - 1),
                "valid": 1,
            },
            mod_type="algorithm",
        )

    @staticmethod
    def fft_butterfly(name: str = "fft_bf", width: int = 16) -> BehavioralSpec:
        """FFT 蝶形运算参考行为模型。"""
        return BehavioralSpec(
            name=name,
            inputs=[
                Input(width, "a_real"), Input(width, "b_real"),
                Input(width, "a_imag"), Input(width, "b_imag"),
            ],
            outputs=[
                Output(width, "out_real"), Output(width, "out_imag"),
                Output(1, "valid"),
            ],
            func=lambda inp: {
                "out_real": (inp["a_real"] + inp["b_real"]) & ((1 << width) - 1),
                "out_imag": (inp["a_imag"] + inp["b_imag"]) & ((1 << width) - 1),
                "valid": 1,
            },
            mod_type="algorithm",
        )

    @staticmethod
    def montgomery_mult(
        name: str = "montgomery_mult",
        width: int = 384,
        word_width: int = 128,
    ) -> BehavioralSpec:
        """蒙哥马利模乘参考行为模型。

        返回的根节点带有 physical.operation="multiplication"，
        使得 DecompositionEngine 可以自动应用 KO-2/KO-3 分解规则。

        参数:
            width: 模数位宽（默认384）
            word_width: 字长（默认128，用于SOS约减）
        """
        n_words = width // word_width
        m_prime_width = word_width

        def _montgomery_func(inputs: dict) -> dict:
            X = inputs.get("X", 0) & ((1 << width) - 1)
            Y = inputs.get("Y", 0) & ((1 << width) - 1)
            M = inputs.get("M", 0) & ((1 << width) - 1)
            M_prime = inputs.get("M_prime", 0) & ((1 << m_prime_width) - 1)

            # 1. Full multiplication
            T = X * Y

            # 2. SOS reduction: n_words iterations
            mask_w = (1 << word_width) - 1
            for _ in range(n_words):
                T_i = T & mask_w
                q = (T_i * M_prime) & mask_w
                T = T + q * M
                T = T >> word_width

            # 3. Final conditional subtraction (up to 2 times for safety)
            for _ in range(2):
                if T >= M:
                    T = T - M

            return {
                "Z": T & ((1 << width) - 1),
                "valid_out": 1,
            }

        return BehavioralSpec(
            name=name,
            inputs=[
                Input(width, "X"),
                Input(width, "Y"),
                Input(width, "M"),
                Input(m_prime_width, "M_prime"),
                Input(1, "valid_in"),
            ],
            outputs=[
                Output(width, "Z"),
                Output(1, "valid_out"),
            ],
            func=_montgomery_func,
            mod_type="algorithm",
            strategy=StrategySpec.timing(),
            latency=60,  # 典型KO-3 + SOS流水线延迟
            physical=PhysicalHint(width=width, operation="multiplication"),
        )


# =====================================================================
# 6. SpecIR ↔ DSL 桥接
# =====================================================================

def submodule_to_spec(sm: BehavioralSpec, parent_name: str = "Module") -> SpecIR:
    """将 BehavioralSpec 转为 SpecIR。

    智能体拿到 SpecIR 后可以：
    1. 用 ArchitecturePlanner + DSLGenerator 生成骨架
    2. 手动修改、增强逻辑
    3. 完全自己写 Module 类（只需端口匹配）
    """
    # 有 latency 的模块（流水线）必须生成 stream_pipeline 骨架，
    # 并自动添加 valid_in / valid_out 流控端口
    if sm.latency is not None and sm.latency > 0:
        category = "stream_pipeline"
    elif sm.mod_type == "processor":
        category = "fsm_controller"
    else:
        category = "comb_alu"

    ports = list(sm.port_list())
    interfaces = None

    # 为流水线模块自动补全 valid/ready 流控端口
    if category == "stream_pipeline":
        interfaces = InterfaceSpec(input_protocol="ready_valid", output_protocol="ready_valid")
        port_names = {p.name for p in ports}
        handshake_ports = [
            PortSpec(name="in_valid", direction="input", width=1),
            PortSpec(name="in_ready", direction="output", width=1),
            PortSpec(name="out_valid", direction="output", width=1),
            PortSpec(name="out_ready", direction="input", width=1),
        ]
        for port in handshake_ports:
            if port.name not in port_names:
                ports.append(port)

    return SpecIR(
        name=f"{parent_name}_{sm.name}",
        category=category,
        function=FunctionSpec(expr=""),
        ports=ports,
        interfaces=interfaces,
        timing=TimingSpec(latency_max=max(sm.latency, 1) if category == "stream_pipeline" else None),
        ppa=PPASpec(),
    )


def generate_dsl_skeleton(sm: BehavioralSpec, parent_name: str = "Module"):
    """为 BehavioralSpec 生成 DSL 骨架。

    这是**起点**，智能体应在此基础上添加实际逻辑。
    """
    from rtlgen import ArchitecturePlanner, DSLGenerator, SpecCompleter

    spec = submodule_to_spec(sm, parent_name)
    completed = SpecCompleter.complete(spec)
    planner = ArchitecturePlanner(completed)
    arch = planner.plan()
    return DSLGenerator(completed, arch).generate()
