"""
rtlgen.arch_def — Architecture Definition Framework

Universal building blocks for describing any processor or hardware architecture:
  - ProcessingElement: the atomic component (ports, state, behavior, timing)
  - CycleContext: per-cycle execution context for behavior functions
  - ArchDefinition: full architecture (PEs + interconnects + model)
  - AgentPackage: per-PE bundle for agent implementation
  - ModelProvider: domain-specific models (ISA, Protocol, Stream, Algorithm)
  - CoverageTracker: state/branch/input coverage tracking

Works for CPUs, GPGPUs, NPUs, protocol controllers (DDR/HDMI),
stream processors (video/image), and algorithm blocks (LDPC/FFT).
"""
from __future__ import annotations

import copy
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =====================================================================
# Port and State Descriptors
# =====================================================================

@dataclass
class PortDesc:
    """端口描述。"""
    name: str
    direction: str  # "input" | "output"
    width: int = 1
    description: str = ""


@dataclass
class StateDesc:
    """状态变量描述，带 RTL 结构提示。"""
    name: str
    type_hint: str = "int"       # "int" | "dict" | "list" | "bitmask"
    description: str = ""
    default: Any = None
    rtl_type: Optional[str] = None  # "reg" | "regfile" | "memory" | "queue" | "fifo"
    rtl_width: Optional[int] = None
    rtl_depth: Optional[int] = None


# =====================================================================
# ProcessingElement — Universal Architecture Building Block
# =====================================================================

@dataclass
class ProcessingElement:
    """处理器/架构的基本构建块。任何组件都可以用 PE 描述。

    适用于:
      - CPU 单元 (IFU, IDU, ALU, LSU, ROB, ...)
      - GPGPU 单元 (SM, WarpScheduler, SIMD pipe, ...)
      - NPU 单元 (MAC array, ConvEngine, LayerScheduler, ...)
      - 协议控制器 (AXI interface, Command Scheduler, PHY, ...)
      - 数据流处理器 (Scaler core, Filter, Codec, ...)
      - 数学编解码 (CheckNode, VariableNode, FFT butterfly, ...)
    """
    name: str
    pe_type: str = "generic"  # 类型标签，用于骨架模板选择
    description: str = ""     # 组件功能描述

    inputs: List[PortDesc] = field(default_factory=list)
    outputs: List[PortDesc] = field(default_factory=list)
    state: List[StateDesc] = field(default_factory=list)

    # 行为函数: fn(ctx: CycleContext) -> None
    behavior: Optional[Callable] = None

    # 时序
    latency: int = 0
    can_stall: bool = False
    is_pipeline_stage: bool = False

    # 处理器元数据（按需使用）
    pipeline_stage: Optional[str] = None  # "fetch" | "decode" | "execute" | "memory" | "writeback"
    issue_width: int = 1
    num_pipes: int = 1
    is_out_of_order: bool = False

    # 缓冲结构
    buffer_type: Optional[str] = None   # "rob" | "iq" | "lsq" | "regfile" | "sram"
    buffer_depth: int = 0

    # 层次化分解
    children: List["ProcessingElement"] = field(default_factory=list)

    # GPGPU/多线程扩展
    num_instances: int = 1  # 复制实例数 (e.g., NUM_WARP=8 → 8 个 warp scheduler 实例)
    instance_id_template: str = "i"  # generate 循环变量名

    # 策略（可选，用于 DSL 实现指导）
    strategy: Any = None  # StrategySpec (lazy import to avoid circular)
    timing: Any = None    # TimingSpec (lazy import)


# =====================================================================
# FuConfig / ExuConfig — Fine-grained Execution Unit Description
# =====================================================================

@dataclass
class FuConfig:
    """功能单元配置 — 描述单个执行单元的能力。

    用法:
        alu_cfg = FuConfig(
            name="alu", fu_type="alu",
            num_int_src=2, num_fp_src=0,
            write_int_rf=True, write_fp_rf=False,
            latency=1, has_redirect=True,
            op_types=["add", "sub", "slt", "and", "or", "xor", "sll", "srl", "sra"],
        )
    """
    name: str = "generic"
    fu_type: str = "generic"     # "alu" | "mul" | "div" | "jmp" | "csr" | "fence" | "fmac" | "ldu" | "stu" | "bku" | "f2i" | "f2f"
    num_int_src: int = 2
    num_fp_src: int = 0
    write_int_rf: bool = True
    write_fp_rf: bool = False
    latency: int = 1             # 延迟周期数（0=uncertain/多周期）
    has_redirect: bool = False   # 是否生成 redirect（分支/jump）
    flush_pipe: bool = False     # 是否需要冲刷流水线（CSR/fence）
    replay_inst: bool = False    # 是否需要重执行（load miss）
    has_input_buffer: bool = False
    input_buffer_depth: int = 0
    op_types: List[str] = field(default_factory=list)  # 支持的运算类型
    exception_out: List[int] = field(default_factory=list)  # 异常向量索引


@dataclass
class ExuConfig:
    """执行单元配置 — 组合多个 FuConfig，对应一个物理 ExuBlock。

    用法:
        alu_exu = ExuConfig(
            name="AluExeUnit",
            fu_configs=[alu_cfg],
            dispatch_ports=2,
        )
        mul_div_exu = ExuConfig(
            name="MulDivExeUnit",
            fu_configs=[mul_cfg, div_cfg, bku_cfg],
            dispatch_ports=1,
        )
    """
    name: str = "generic"
    fu_configs: List[FuConfig] = field(default_factory=list)
    dispatch_ports: int = 1
    write_int_rf: bool = True
    write_fp_rf: bool = False
    wb_int_priority: int = 0     # 写回仲裁优先级（int）
    wb_fp_priority: int = 0      # 写回仲裁优先级（fp）


@dataclass
class SchedulerConfig:
    """调度器/发射队列配置 — 描述 dispatch 和 issue 行为。

    用法:
        sched = SchedulerConfig(
            scheduler_type="int",
            dispatch_queues={"int_dq": {"size": 16, "deq_width": 4}},
            issue_queue={"size": 16, "num_entries": 16},
            wakeup_targets=["AluExeUnit", "LdExeUnit"],
        )
    """
    scheduler_type: str = "int"     # "int" | "fp" | "mem"
    dispatch_queues: Dict[str, Dict[str, int]] = field(default_factory=dict)
    issue_queue_size: int = 16
    num_rs_entries: int = 16
    wakeup_targets: List[str] = field(default_factory=list)
    select_targets: List[str] = field(default_factory=list)
    # 跨 scheduler 的快速 wakeup 端口
    inter_scheduler_wakeup: List[str] = field(default_factory=list)


# =====================================================================
# CycleContext — Per-Cycle Execution Context
# =====================================================================

@dataclass
class CycleContext:
    """Cycle-accurate behavioral simulation context.

    Behavior functions access inputs/outputs/state through this object.
    Extended with memory, register file, cache, and pipeline event support
    for true executable behavioral models.

    Usage:
        def my_behavior(ctx: CycleContext):
            if ctx.get_input("rst_n") == 0:
                ctx.set_state("pc", 0)
                return
            # Memory access
            inst = ctx.memory_read(ctx.get_state("pc", 0), size=4)
            # Register file access
            rs1 = ctx.register_read("int_rf", ctx.get_input("rs1", 0))
            # Cache access
            hit, way = ctx.cache_access("l1_icache", ctx.get_state("pc", 0))
            ctx.set_output("result", rs1 + ctx.get_input("imm", 0))
    """
    cycle: int = 0
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    next_state: Dict[str, Any] = field(default_factory=dict)

    # Domain-specific model (injected by ArchDefinition.model)
    model: Optional["ModelProvider"] = None

    # Extended behavioral models (injected by ArchSimulator)
    memory: Optional["MemoryModel"] = None
    register_files: Dict[str, "RegisterFileModel"] = field(default_factory=dict)
    caches: Dict[str, "CacheModel"] = field(default_factory=dict)
    fifos: Dict[str, deque] = field(default_factory=dict)

    metrics: Dict[str, Any] = field(default_factory=dict)

    # Instruction retirement count (for precise IPC)
    retired: int = 0

    # Pipeline control
    _stall: bool = False
    _flush: bool = False
    _flush_target: int = 0

    def get_input(self, name: str, default: Any = 0) -> Any:
        return self.inputs.get(name, default)

    def set_output(self, name: str, value: Any):
        self.outputs[name] = value

    def get_output(self, name: str, default: Any = 0) -> Any:
        return self.outputs.get(name, default)

    def get_state(self, name: str, default: Any = None) -> Any:
        return self.state.get(name, default)

    def set_state(self, name: str, value: Any):
        self.next_state[name] = value

    def get_model_service(self, name: str, **kwargs) -> Any:
        """Get domain model service (ISA fetch, protocol timing, golden ref, etc.)."""
        if self.model is None:
            return None
        try:
            return self.model.get_service(name, **kwargs)
        except NotImplementedError:
            return None

    def record_metric(self, key: str, value: Any):
        if key in self.metrics:
            if isinstance(self.metrics[key], (int, float)):
                self.metrics[key] += value
            elif isinstance(self.metrics[key], list):
                self.metrics[key].append(value)
        else:
            self.metrics[key] = value

    def retire(self, n: int = 1):
        """Mark instruction retirement. Used for precise IPC calculation."""
        self.retired += n

    # -----------------------------------------------------------------
    # Memory access
    # -----------------------------------------------------------------
    def memory_read(self, addr: int, size: int = 4) -> int:
        """Read `size` bytes from memory at `addr`."""
        if self.memory is None:
            raise RuntimeError("memory_read called but no MemoryModel attached")
        return self.memory.read(addr, size)

    def memory_write(self, addr: int, value: int, size: int = 4):
        """Write `size` bytes of `value` to memory at `addr`."""
        if self.memory is None:
            raise RuntimeError("memory_write called but no MemoryModel attached")
        self.memory.write(addr, value, size)

    def memory_read_signed(self, addr: int, size: int = 4) -> int:
        """Read `size` bytes and sign-extend."""
        if self.memory is None:
            raise RuntimeError("memory_read_signed called but no MemoryModel attached")
        return self.memory.read_signed(addr, size)

    # -----------------------------------------------------------------
    # Register file access
    # -----------------------------------------------------------------
    def register_read(self, rf_name: str, idx: int, bypass: bool = True) -> int:
        """Read register `idx` from register file `rf_name`."""
        rf = self.register_files.get(rf_name)
        if rf is None:
            raise RuntimeError(f"register_read called but no register file '{rf_name}' attached")
        return rf.read(idx, bypass)

    def register_write(self, rf_name: str, idx: int, value: int):
        """Write `value` to register `idx` in register file `rf_name`."""
        rf = self.register_files.get(rf_name)
        if rf is None:
            raise RuntimeError(f"register_write called but no register file '{rf_name}' attached")
        rf.write(idx, value)

    def register_write_pending(self, rf_name: str, idx: int, value: int):
        """Queue a register write to be committed on next cycle."""
        rf = self.register_files.get(rf_name)
        if rf is None:
            raise RuntimeError(f"register_write_pending called but no register file '{rf_name}' attached")
        rf.write_pending(idx, value)

    def register_set_forward(self, rf_name: str, idx: int, value: int):
        """Set bypass value for read-after-write forwarding."""
        rf = self.register_files.get(rf_name)
        if rf is None:
            raise RuntimeError(f"register_set_forward called but no register file '{rf_name}' attached")
        rf.set_forward(idx, value)

    def register_commit(self, rf_name: str):
        """Commit all pending writes to register file."""
        rf = self.register_files.get(rf_name)
        if rf is not None:
            rf.commit()

    # -----------------------------------------------------------------
    # Cache access
    # -----------------------------------------------------------------
    def cache_access(self, cache_name: str, addr: int, is_write: bool = False) -> Tuple[bool, int]:
        """Access cache `cache_name` at `addr`. Returns (hit, way)."""
        cache = self.caches.get(cache_name)
        if cache is None:
            raise RuntimeError(f"cache_access called but no cache '{cache_name}' attached")
        return cache.access(addr, is_write)

    def cache_hit(self, cache_name: str, addr: int) -> bool:
        """Check if cache `cache_name` has `addr` (read-only check)."""
        cache = self.caches.get(cache_name)
        if cache is None:
            return False
        hit, _ = cache.access(addr, is_write=False)
        return hit

    def cache_fill(self, cache_name: str, addr: int, way: int, data: bytes,
                   state: Optional[str] = None):
        """Fill cache line with data."""
        cache = self.caches.get(cache_name)
        if cache is None:
            raise RuntimeError(f"cache_fill called but no cache '{cache_name}' attached")
        cache.fill_line(addr, way, data, state)

    def cache_read(self, cache_name: str, addr: int, size: int = 8) -> int:
        """Read `size` bytes from cache `cache_name` at `addr`."""
        cache = self.caches.get(cache_name)
        if cache is None:
            raise RuntimeError(f"cache_read called but no cache '{cache_name}' attached")
        return cache.read(addr, size)

    def cache_write(self, cache_name: str, addr: int, value: int, size: int = 8):
        """Write `size` bytes to cache `cache_name` at `addr`."""
        cache = self.caches.get(cache_name)
        if cache is None:
            raise RuntimeError(f"cache_write called but no cache '{cache_name}' attached")
        cache.write(addr, value, size)

    def cache_invalidate(self, cache_name: str, addr: int) -> bool:
        """Invalidate line at `addr` in cache `cache_name`. Returns True if line was dirty."""
        cache = self.caches.get(cache_name)
        if cache is None:
            return False
        return cache.invalidate_line(addr)

    def cache_snoop(self, cache_name: str, addr: int, is_invalidate: bool = False) -> Tuple[bool, str, bool]:
        """Snoop cache for coherence. Returns (hit, state, was_dirty)."""
        cache = self.caches.get(cache_name)
        if cache is None:
            return False, "I", False
        return cache.snoop(addr, is_invalidate)

    # -----------------------------------------------------------------
    # Coherence
    # -----------------------------------------------------------------
    def coherence_request(self, req_type: str, addr: int) -> dict:
        """Issue a coherence request.

        req_type: "read_shared", "read_exclusive", "writeback", "invalidate"
        Returns: {"granted": bool, "data": bytes, "state": str}
        """
        self.record_metric("coherence_requests", 1)
        self.record_metric(f"coherence_{req_type}", 1)
        # Default: always grant, return empty data
        # Subclasses or model-specific behavior can override
        return {"granted": True, "data": b"", "state": "I"}

    # -----------------------------------------------------------------
    # FIFO / Queue
    # -----------------------------------------------------------------
    def fifo_push(self, fifo_name: str, data: Any) -> bool:
        """Push data to FIFO `fifo_name`. Returns True if successful."""
        q = self.fifos.get(fifo_name)
        if q is None:
            raise RuntimeError(f"fifo_push called but no FIFO '{fifo_name}' attached")
        if len(q) >= getattr(q, "maxlen", 16):
            return False
        q.append(data)
        return True

    def fifo_pop(self, fifo_name: str) -> Optional[Any]:
        """Pop data from FIFO `fifo_name`. Returns None if empty."""
        q = self.fifos.get(fifo_name)
        if q is None:
            raise RuntimeError(f"fifo_pop called but no FIFO '{fifo_name}' attached")
        if not q:
            return None
        return q.popleft()

    def fifo_peek(self, fifo_name: str) -> Optional[Any]:
        """Peek at head of FIFO `fifo_name`. Returns None if empty."""
        q = self.fifos.get(fifo_name)
        if q is None:
            return None
        return q[0] if q else None

    def fifo_count(self, fifo_name: str) -> int:
        """Return number of items in FIFO `fifo_name`."""
        q = self.fifos.get(fifo_name)
        return len(q) if q else 0

    def fifo_empty(self, fifo_name: str) -> bool:
        """Check if FIFO `fifo_name` is empty."""
        return self.fifo_count(fifo_name) == 0

    def fifo_full(self, fifo_name: str, depth: int = 16) -> bool:
        """Check if FIFO `fifo_name` is full."""
        return self.fifo_count(fifo_name) >= depth

    # -----------------------------------------------------------------
    # Pipeline control
    # -----------------------------------------------------------------
    def pipeline_stall(self, reason: str = ""):
        """Mark pipeline as stalled this cycle."""
        self._stall = True
        self.record_metric("stalls", 1)
        if reason:
            self.record_metric(f"stall_{reason}", 1)

    def pipeline_flush(self, target_pc: int = 0):
        """Mark pipeline as flushed this cycle."""
        self._flush = True
        self._flush_target = target_pc
        self.record_metric("flushes", 1)

    def is_stalled(self) -> bool:
        return self._stall

    def is_flushed(self) -> bool:
        return self._flush

    def flush_target(self) -> int:
        return self._flush_target

    def clear_control(self):
        """Clear stall/flush flags at cycle boundary."""
        self._stall = False
        self._flush = False
        self._flush_target = 0


# =====================================================================
# Interconnect — PE-to-PE Connections
# =====================================================================

@dataclass
class HandshakeSpec:
    """Valid/Ready 握手协议描述。

    GPGPU/AXI/TileLink 等协议使用 valid/ready 双向流控:
    - src_valid: 发送方有数据
    - dst_ready: 接收方准备好
    - 传输仅在 valid & ready 同时为高时发生
    """
    valid_signal: str = "valid"
    ready_signal: str = "ready"
    # 可选: 额外控制信号 (e.g., last, opcode)
    control_signals: List[PortDesc] = field(default_factory=list)


@dataclass
class QueueSpec:
    """FIFO/Queue 缓冲区描述。

    GPGPU 流水线级间常用 FIFO 缓冲 (如 LSU → D-Cache 请求队列):
    - depth: FIFO 深度
    - almost_full/almost_empty: 可编程阈值
    """
    depth: int = 8
    almost_full_threshold: int = 0   # 0 = disabled
    almost_empty_threshold: int = 0  # 0 = disabled
    flow_control: str = "valid_ready"  # "valid_ready" | "credit" | "none"


@dataclass
class InterconnectSpec:
    """PE 之间的互连描述。"""
    src_pe: str
    dst_pe: str
    signals: List[PortDesc] = field(default_factory=list)
    flow_type: str = "stream"  # "stream" | "handshake" | "fifo"
    delay_cycles: int = 0

    # 扩展: 握手协议 (GPGPU/AXI/TileLink 风格)
    handshake: Optional[HandshakeSpec] = None

    # 扩展: 队列缓冲 (流水线级间 FIFO)
    queue: Optional[QueueSpec] = None


# =====================================================================
# ArchDefinition — Full Architecture Definition
# =====================================================================

@dataclass
class ArchDefinition:
    """处理器/硬件架构定义。

    组合 ProcessingElement 和 InterconnectSpec，指定领域模型，
    构成完整的架构描述，可被仿真、分析和实现。
    """
    name: str
    description: str = ""
    isa: str = ""  # "riscv" | "arm" | "simt" | "tensor" | "protocol" | "stream" | "algorithm"

    processing_elements: List[ProcessingElement] = field(default_factory=list)
    interconnects: List[InterconnectSpec] = field(default_factory=list)

    # 领域特定模型
    model: Optional["ModelProvider"] = None

    # PPA 目标
    ppa_targets: Dict[str, Any] = field(default_factory=dict)  # {max_area, max_power, min_ipc, ...}

    def add_pe(self, pe: ProcessingElement) -> "ArchDefinition":
        self.processing_elements.append(pe)
        return self

    def add_interconnect(self, conn: InterconnectSpec) -> "ArchDefinition":
        self.interconnects.append(conn)
        return self

    def find_pe(self, name: str) -> Optional[ProcessingElement]:
        for pe in self.processing_elements:
            if pe.name == name:
                return pe
        return None

    def get_all_pes(self, include_children: bool = True) -> List[ProcessingElement]:
        """获取所有 PE（含嵌套 children）。"""
        result = []
        stack = list(self.processing_elements)
        while stack:
            pe = stack.pop()
            result.append(pe)
            if include_children:
                stack.extend(pe.children)
        return result

    def get_dependencies(self) -> Dict[str, List[str]]:
        """返回 PE 的依赖关系（用于拓扑排序）。"""
        deps: Dict[str, List[str]] = {pe.name: [] for pe in self.processing_elements}
        for conn in self.interconnects:
            if conn.dst_pe in deps and conn.src_pe in deps:
                if conn.src_pe not in deps[conn.dst_pe]:
                    deps[conn.dst_pe].append(conn.src_pe)
        return deps

    def to_behavioral_specs(self) -> List[Any]:
        """将 ArchDefinition 转为 BehavioralSpec 列表，桥接到现有流程。"""
        from rtlgen.decomposition import BehavioralSpec
        result = []
        for pe in self.processing_elements:
            inputs = [Input(p.width, p.name) for p in pe.inputs]
            outputs = [Output(p.width, p.name) for p in pe.outputs]
            result.append(BehavioralSpec(
                name=pe.name,
                inputs=inputs,
                outputs=outputs,
                func=self._pe_to_behavior(pe),
                mod_type=self._pe_to_mod_type(pe.pe_type),
                strategy=pe.strategy,
                latency=pe.latency,
            ))
        return result

    def _pe_to_behavior(self, pe: ProcessingElement) -> Callable:
        if pe.behavior is not None:
            return pe.behavior
        # Default: pass-through behavior
        def default_behavior(inp: dict) -> dict:
            return {p.name: inp.get(p.name, 0) for p in pe.outputs}
        return default_behavior

    def _pe_to_mod_type(self, pe_type: str) -> str:
        mapping = {
            "ifu": "processor", "idu": "processor", "alu": "processor",
            "lsu": "processor", "rtu": "processor", "regfile": "memory",
            "sm": "processor", "warp_scheduler": "processor",
            "mac_array": "algorithm", "conv": "algorithm",
            "axi_interface": "interconnect", "command_scheduler": "processor",
            "scaler": "algorithm", "filter": "algorithm",
        }
        return mapping.get(pe_type, "algorithm")


# =====================================================================
# AgentPackage — Agent Implementation Bundle
# =====================================================================

@dataclass
class AgentPackage:
    """每个 ProcessingElement 生成的智能体操作包。

    包含 agent 实现该模块所需的全部信息：
    - 可运行的行为参考模型
    - DSL Module 骨架（带 TODO 注释）
    - Golden 测试向量
    - PPA 性能目标
    - 互连接口定义（含 valid/ready 握手）
    - 增量实现步骤
    - Generate loop 模式（GPGPU per-warp/per-SM 复制）
    - 子模块分解（层次化 PE 的 sub-module 列表）
    """
    pe: ProcessingElement
    behavioral_reference: Callable
    dsl_skeleton: Any = None   # Module (lazy, set after generation)
    golden_tests: List[dict] = field(default_factory=list)
    performance_targets: Dict[str, Any] = field(default_factory=dict)
    interconnect_interface: Dict[str, Any] = field(default_factory=dict)
    implementation_steps: List[str] = field(default_factory=list)

    # GPGPU 扩展
    generate_loops: List[Any] = field(default_factory=list)        # GenerateLoopPattern list
    submodule_decomposition: Dict[str, Any] = field(default_factory=dict)  # submodules + internal conns

    def verify_rtl(self, rtl_module: Any, test_vectors: List[dict],
                   simulator_class: Any = None) -> Tuple[bool, List[str]]:
        """验证 RTL 实现与行为参考的一致性。

        Returns:
            (all_passed, list_of_failures)
        """
        from rtlgen.sim import Simulator

        failures = []
        sim_cls = simulator_class or Simulator

        for i, test in enumerate(test_vectors):
            # Run behavioral reference
            ctx = CycleContext(inputs=test.get("inputs", {}))
            self.behavioral_reference(ctx)
            expected = dict(ctx.outputs)

            # Run RTL simulation
            sim = sim_cls(rtl_module)
            for name, value in test.get("inputs", {}).items():
                sim.set(name, value)
            sim._eval_comb()
            actual = {name: sim.state.get(name, 0) for name in rtl_module._outputs}

            # Compare
            for port_name, exp_val in expected.items():
                act_val = actual.get(port_name, 0)
                if act_val != exp_val:
                    failures.append(
                        f"Test {i}: {port_name} expected={exp_val}, actual={act_val}"
                    )

        return (len(failures) == 0, failures)

    def generate_verify_script(self, output_path: str):
        """生成 Python 验证脚本。"""
        lines = [
            "#!/usr/bin/env python3",
            f"# Auto-generated verification script for {self.pe.name}",
            "",
            "from rtlgen.sim import Simulator",
            "from rtlgen.arch_def import CycleContext",
            "",
            f"# Behavioral reference",
            f"behavior = {self.behavioral_reference.__name__ if callable(self.behavioral_reference) else 'behavioral_reference'}",
            "",
            "# Golden test vectors",
            f"golden_tests = {self.golden_tests!r}",
            "",
            "def run_verification():",
            "    all_passed = True",
            "    for i, test in enumerate(golden_tests):",
            "        # Behavioral reference",
            "        ctx = CycleContext(inputs=test.get('inputs', {}))",
            "        behavior(ctx)",
            "        expected = dict(ctx.outputs)",
            "",
            "        # TODO: import and instantiate the RTL module",
            "        # from my_design import MyModule",
            "        # rtl = MyModule()",
            "        # sim = Simulator(rtl)",
            "        # for name, value in test.get('inputs', {}).items():",
            "        #     sim.set(name, value)",
            "        # sim._eval_comb()",
            "        # actual = {name: sim.state.get(name, 0) for name in rtl._outputs}",
            "        actual = expected  # placeholder",
            "",
            "        for port, exp in expected.items():",
            "            act = actual.get(port, 0)",
            "            if act != exp:",
            f'                print(f"FAIL test {{i}}: {{port}} expected={{exp}} actual={{act}}")',
            "                all_passed = False",
            "",
            "    if all_passed:",
            '        print("All tests passed!")',
            "",
            "if __name__ == '__main__':",
            "    run_verification()",
        ]
        with open(output_path, "w") as f:
            f.write("\n".join(lines) + "\n")


# =====================================================================
# CoverageTracker
# =====================================================================

class CoverageTracker:
    """覆盖率追踪器 — 跟踪行为模型执行了多少状态路径。"""

    def __init__(self, pe: ProcessingElement):
        self.pe = pe
        self.state_coverage: Set[str] = set()
        self.input_coverage: Set[str] = set()
        self.branch_coverage: Set[str] = set()
        self.cycle_count = 0
        self._total_states = {s.name for s in pe.state}

    def record(self, ctx: CycleContext):
        """每个周期记录覆盖信息。"""
        self.cycle_count += 1
        # Record which state variables were read/written
        for name in ctx.state:
            self.state_coverage.add(name)
        for name in ctx.next_state:
            self.state_coverage.add(name)
        # Record which input patterns appeared
        for name, value in ctx.inputs.items():
            self.input_coverage.add(f"{name}={value}")

    def report(self) -> dict:
        total = max(len(self._total_states), 1)
        pct = len(self.state_coverage) / total * 100
        return {
            "state_coverage": f"{len(self.state_coverage)}/{total} ({pct:.0f}%)",
            "coverage_pct": pct,
            "input_coverage": f"{len(self.input_coverage)} patterns",
            "branch_coverage": f"{len(self.branch_coverage)} paths",
            "uncovered_states": list(self._total_states - self.state_coverage),
            "cycles": self.cycle_count,
        }

    def generate_missing_tests(self, n: int = 50) -> List[dict]:
        """生成缺失的测试用例，填补未覆盖的分支。"""
        tests = []
        uncovered = self._total_states - self.state_coverage
        for name in list(uncovered)[:n]:
            tests.append({
                "inputs": {"_target_state": name},
                "description": f"Cover state {name}",
            })
        # If still need more tests, generate random patterns
        import random
        for _ in range(n - len(tests)):
            inp = {}
            for port in self.pe.inputs:
                if port.width <= 1:
                    inp[port.name] = random.randint(0, 1)
                elif port.width <= 8:
                    inp[port.name] = random.randint(0, 255)
                else:
                    inp[port.name] = random.randint(0, (1 << min(port.width, 16)) - 1)
            tests.append({"inputs": inp, "description": "Random coverage test"})
        return tests


# =====================================================================
# ModelProvider — Domain-Specific Models
# =====================================================================

class ModelProvider:
    """领域特定模型的统一接口。

    子类实现 get_service() 提供领域服务：
    - ISA_Model: 指令取指/执行/内存访问
    - Protocol_Model: 协议时序/状态机/编码
    - Stream_Model: golden reference 算法/数据流迭代
    - Algorithm_Model: 算法参考实现/参数查询
    """
    model_type: str = "base"

    def on_cycle(self, cycle: int):
        """每周期回调，更新模型内部状态。"""
        pass

    def get_service(self, name: str, **kwargs) -> Any:
        """获取领域服务。子类实现。"""
        raise NotImplementedError


class ISA_Model(ModelProvider):
    """ISA 指令集模拟器模型。用于 CPU/GPGPU/NPU。

    通过 ISSBase 抽象接口支持任意 ISA：
    - RV32ISS (RISC-V RV32I)
    - ARM_ISS (ARMv7-M/ARMv8-A)
    - MIPS_ISS (MIPS32/64)
    - 自定义 DSP/NPU ISA

    用法:
        model = ISA_Model(iss=RV32ISS())
        inst = model.get_service('fetch_inst', pc=0x1000)
        model.get_service('step')  # 执行一条指令
        meta = model.get_service('isa_metadata')  # 寄存器名、特权级等
    """
    model_type = "isa"

    def __init__(self, iss: Any = None, memory: Any = None):
        self.iss = iss           # RV32ISS / ARM_ISS / 自定义 ISSBase 子类
        self.memory = memory      # 系统内存模型

    def get_service(self, name: str, **kwargs) -> Any:
        if self.iss is None:
            return self._fallback(name)

        # 优先使用 ISSBase 抽象接口
        if hasattr(self.iss, "isa_name"):
            return self._via_issbase(name, kwargs)

        # 回退：旧版 hasattr 兼容（非 ISSBase 子类的 ISS）
        return self._via_hasattr(name, kwargs)

    def _via_issbase(self, name: str, kwargs: dict) -> Any:
        """通过 ISSBase 抽象接口提供服务。"""
        iss = self.iss
        if name == "fetch_inst":
            return iss.fetch_instruction(kwargs.get("pc", 0))
        if name == "execute":
            iss.step()
            return {"done": True}
        if name == "step":
            iss.step()
            return {"done": True}
        if name == "isa_state":
            return iss
        if name == "get_pc":
            return iss.get_pc()
        if name == "get_register":
            return iss.get_register(kwargs.get("idx", 0))
        if name == "set_pc":
            iss.set_pc(kwargs.get("pc", 0))
            return {"done": True}
        if name == "set_register":
            iss.set_register(kwargs.get("idx", 0), kwargs.get("value", 0))
            return {"done": True}
        if name == "get_halted":
            return iss.get_halted()
        if name == "isa_metadata":
            return iss.get_isa_metadata()
        if name == "isa_name":
            return iss.isa_name
        if name == "reset":
            iss.reset()
            return {"done": True}
        if name == "memory_read":
            if self.memory is None:
                return 0
            return self.memory.read(kwargs.get("addr", 0), kwargs.get("size", 4))
        if name == "memory_write":
            if self.memory is None:
                return
            return self.memory.write(kwargs.get("addr", 0), kwargs.get("data", 0))
        return None

    def _via_hasattr(self, name: str, kwargs: dict) -> Any:
        """回退兼容：使用 hasattr 检查旧版 ISS 接口。"""
        iss = self.iss
        if name == "fetch_inst":
            if hasattr(iss, "fetch_instruction"):
                return iss.fetch_instruction(kwargs.get("pc", 0))
            if hasattr(getattr(iss, "state", None), "load_word"):
                return iss.state.load_word(kwargs.get("pc", 0))
            return 0x00000013
        if name in ("execute", "step"):
            if hasattr(iss, "step"):
                iss.step()
                return {"done": True}
            return {}
        if name == "isa_state":
            return iss
        if name == "isa_metadata":
            if hasattr(iss, "get_isa_metadata"):
                return iss.get_isa_metadata()
            return {"isa": getattr(iss, "isa_name", "unknown")}
        if name == "memory_read":
            if self.memory is None:
                return 0
            return self.memory.read(kwargs.get("addr", 0), kwargs.get("size", 4))
        if name == "memory_write":
            if self.memory is None:
                return
            return self.memory.write(kwargs.get("addr", 0), kwargs.get("data", 0))
        return None

    def _fallback(self, name: str) -> Any:
        """ISS 为 None 时的回退值。"""
        if name == "fetch_inst":
            return 0x00000013  # NOP
        if name in ("execute", "step"):
            return {}
        if name == "isa_state":
            return None
        if name == "isa_metadata":
            return {"isa": "none"}
        if name == "get_halted":
            return True
        if name == "isa_name":
            return "none"
        return None


class Protocol_Model(ModelProvider):
    """协议时序模型。用于 DDR/HDMI/PCIe/USB 等协议控制器。"""
    model_type = "protocol"

    def __init__(self, protocol: str = "generic",
                 timing: Optional[Dict[str, int]] = None,
                 scheduler: Any = None):
        self.protocol = protocol
        self.timing = timing or {}
        self.scheduler = scheduler
        self._state: Dict[str, Any] = {"link_up": False, "cycle": 0}

    def on_cycle(self, cycle: int):
        self._state["cycle"] = cycle

    def get_service(self, name: str, **kwargs) -> Any:
        if name == "timing_constraint":
            return self.timing.get(kwargs.get("constraint", ""), 0)
        if name == "phy_ready":
            return self._state.get("link_up", False)
        if name == "link_state":
            return self._state
        if name == "encode":
            return kwargs.get("data", 0)
        if name == "decode":
            return kwargs.get("data", 0)
        if name == "schedule_cmd":
            if self.scheduler:
                return self.scheduler.schedule(**kwargs)
            return None
        return None


class Stream_Model(ModelProvider):
    """数据流模型。用于视频/图像/音频处理。"""
    model_type = "stream"

    def __init__(self, golden_ref: Optional[Callable] = None,
                 frame_size: Optional[Tuple[int, int]] = None,
                 pixel_format: str = "rgb888"):
        self.golden_ref = golden_ref
        self.frame_size = frame_size
        self.pixel_format = pixel_format
        self._stream_iter: Any = None

    def get_service(self, name: str, **kwargs) -> Any:
        if name == "golden_ref":
            if self.golden_ref is None:
                return kwargs.get("input", 0)
            return self.golden_ref(kwargs.get("input"))
        if name == "next_block":
            if self._stream_iter:
                return next(self._stream_iter, None)
            return None
        if name == "frame_size":
            return self.frame_size
        return None


class Algorithm_Model(ModelProvider):
    """算法模型。用于 LDPC/FFT/Crypto 等数学编解码。"""
    model_type = "algorithm"

    def __init__(self, golden_ref: Optional[Callable] = None,
                 parameters: Optional[Dict[str, Any]] = None):
        self.golden_ref = golden_ref
        self.parameters = parameters or {}

    def get_service(self, name: str, **kwargs) -> Any:
        if name == "golden_ref":
            if self.golden_ref is None:
                return kwargs.get("input", 0)
            return self.golden_ref(kwargs.get("input"), **self.parameters)
        if name == "parameter":
            return self.parameters.get(kwargs.get("key", ""))
        return None


class MemoryModel(ModelProvider):
    """内存控制器模型。用于 DDR3/DDR4/LPDDR5/HBM 等内存控制器。"""
    model_type = "memory"

    def __init__(self, mem_type: str = "DDR3",
                 speed_bin: str = "DDR3-800",
                 bus_width: int = 32,
                 burst_len: int = 8,
                 bank_count: int = 8,
                 row_count: int = 32768,
                 col_count: int = 1024,
                 addr_mapping: str = "rbc",
                 mhz: int = 25,
                 timing: Optional[Dict[str, int]] = None):
        self.mem_type = mem_type
        self.speed_bin = speed_bin
        self.bus_width = bus_width
        self.burst_len = burst_len
        self.bank_count = bank_count
        self.row_count = row_count
        self.col_count = col_count
        self.addr_mapping = addr_mapping
        self.mhz = mhz
        self.timing = timing or {}
        # Per-bank row state: {bank_idx: open_row_addr or None}
        self._bank_rows: Dict[int, Optional[int]] = {i: None for i in range(bank_count)}
        self._refresh_counter = 0
        self._state: Dict[str, Any] = {"initialized": False, "cycle": 0}

    def timing_cycles(self, name: str) -> int:
        """获取时序约束的周期数 (e.g., 'tRCD', 'tRP', 'tRFC')。"""
        return self.timing.get(name, 0)

    def refresh_due(self, cycle: int) -> bool:
        """检查是否需要自动刷新。"""
        if "tREFI" in self.timing:
            return (cycle % self.timing["tREFI"]) == 0
        # Default: 64ms / 8192 rows
        ref_cycles = int((64000 * self.mhz) // 8192)
        return (cycle % ref_cycles) == 0

    def row_open(self, bank: int) -> bool:
        return self._bank_rows.get(bank) is not None

    def row_hit(self, bank: int, row: int) -> bool:
        return self._bank_rows.get(bank) == row

    def row_miss(self, bank: int, row: int) -> bool:
        br = self._bank_rows.get(bank)
        return br is not None and br != row

    def activate_row(self, bank: int, row: int):
        self._bank_rows[bank] = row

    def precharge_bank(self, bank: int):
        self._bank_rows[bank] = None

    def precharge_all(self):
        for b in self._bank_rows:
            self._bank_rows[b] = None

    def decode_address(self, addr: int) -> Dict[str, int]:
        """将物理地址解码为 (bank, row, col)。"""
        import math
        col_bits = int(math.log2(self.col_count))
        bank_bits = int(math.log2(self.bank_count))
        if self.addr_mapping == "rbc":
            col = addr & ((1 << col_bits) - 1)
            bank = (addr >> col_bits) & ((1 << bank_bits) - 1)
            row = addr >> (col_bits + bank_bits)
        else:  # brc
            bank = addr & ((1 << bank_bits) - 1)
            col = (addr >> bank_bits) & ((1 << col_bits) - 1)
            row = addr >> (col_bits + bank_bits)
        return {"bank": bank, "row": row, "col": col}

    def on_cycle(self, cycle: int):
        self._state["cycle"] = cycle

    def get_service(self, name: str, **kwargs) -> Any:
        if name == "timing_cycles":
            return self.timing_cycles(kwargs.get("timing_name", ""))
        if name == "refresh_due":
            return self.refresh_due(kwargs.get("cycle", 0))
        if name == "row_open":
            return self.row_open(kwargs.get("bank", 0))
        if name == "row_hit":
            return self.row_hit(kwargs.get("bank", 0), kwargs.get("row", 0))
        if name == "row_miss":
            return self.row_miss(kwargs.get("bank", 0), kwargs.get("row", 0))
        if name == "decode_address":
            return self.decode_address(kwargs.get("addr", 0))
        if name == "activate_row":
            self.activate_row(kwargs.get("bank", 0), kwargs.get("row", 0))
            return True
        if name == "precharge_bank":
            self.precharge_bank(kwargs.get("bank", 0))
            return True
        if name == "mem_type":
            return self.mem_type
        if name == "bus_width":
            return self.bus_width
        if name == "burst_len":
            return self.burst_len
        return None


@dataclass
class MemoryControllerSpec:
    """内存控制器规范 — 架构级内存 PE 定义。

    用于在 ArchDefinition 中定义内存控制器 ProcessingElement。

    Usage:
        mem_spec = MemoryControllerSpec(
            mem_type="DDR3", speed_bin="DDR3-800",
            bus_width=32, burst_len=8, bank_count=8,
            row_w=15, col_w=10, addr_mapping="rbc", mhz=25,
        )
        pe = ProcessingElement(
            name="DDR3Controller", pe_type="memory_controller",
            behavior=memory_controller_template(
                mem_type=mem_spec.mem_type,
                bank_count=mem_spec.bank_count,
            ),
            ...
        )
    """
    mem_type: str = "DDR3"          # "DDR3" | "DDR4" | "LPDDR5" | "HBM2"
    speed_bin: str = "DDR3-800"     # JEDEC speed bin
    bus_width: int = 32             # 数据总线宽度 (bits)
    burst_len: int = 8              # 突发长度 (BL8 for DDR3)
    bank_count: int = 8             # Bank 数量
    row_w: int = 15                 # 行地址位宽
    col_w: int = 10                 # 列地址位宽
    addr_mapping: str = "rbc"       # "rbc" (row-bank-col) | "brc" (bank-row-col)
    mhz: int = 25                   # 控制器时钟频率
    dll_off: bool = True            # DLL-off 模式 (低速运行)

    @property
    def total_capacity_mbits(self) -> int:
        """总内存容量 (Mbits)。"""
        import math
        bits_per_bank = 1 << (self.row_w + self.col_w)
        total_bits = bits_per_bank * self.bank_count * self.bus_width
        return total_bits // (1024 * 1024)

    def to_timing_dict(self, mhz: Optional[int] = None) -> Dict[str, int]:
        """将时序规范转换为周期数。"""
        from rtlgen.mem_timing import DDR3Timing, ns_to_cycles
        mhz = mhz or self.mhz
        if self.mem_type == "DDR3":
            timing = DDR3Timing(self.speed_bin)
            return timing.to_cycles(mhz)
        # Fallback for unsupported types
        return {}


# =====================================================================
# Imports (local, for bridge methods)
# =====================================================================

# Lazy import Input/Output for to_behavioral_specs
def Input(width: int, name: str):
    from rtlgen.core import Input as _Input
    return _Input(width, name)

def Output(width: int, name: str):
    from rtlgen.core import Output as _Output
    return _Output(width, name)
