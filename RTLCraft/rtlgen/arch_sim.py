"""
rtlgen.arch_sim — Architecture-Level Cycle-Accurate Simulator

ArchSimulator: topological sort → per-cycle behavior execution →
signal propagation → metrics collection.

Works with ArchDefinition to run cycle-accurate simulation of any
processor or hardware architecture.

GPGPU-inspired enhancements:
  - Valid/ready handshake modeling (back-pressure propagation)
  - Queue/FIFO-based communication between pipeline stages
  - Instruction retirement tracking for precise IPC
  - Hierarchical PE execution (parent → children behaviors)
  - Scoreboard-based stall detection
"""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from rtlgen.arch_def import (
    ArchDefinition,
    CycleContext,
    InterconnectSpec,
    ProcessingElement,
)
from rtlgen.memory_model import MemoryModel
from rtlgen.regfile_model import RegisterFileModel
from rtlgen.cache_model import CacheModel


class _HandshakeState:
    """Per-connection valid/ready handshake state.

    Models the AXI/TileLink style valid-ready protocol:
    transfer occurs only when valid & ready are both asserted.
    """

    def __init__(self):
        self.valid: int = 0
        self.ready: int = 1  # default: receiver is ready
        self.payload: Dict[str, Any] = {}
        self.fire_last_cycle: bool = False  # was there a transfer last cycle?


class _FifoQueue:
    """Simple FIFO for queue-based inter-PE communication.

    Models the stream_fifo_pipe_true style queue used between
    LSU and D-Cache in the GPGPU SM wrapper.
    """

    def __init__(self, depth: int = 8):
        self.depth = depth
        self._data: deque = deque()

    @property
    def empty(self) -> bool:
        return len(self._data) == 0

    @property
    def full(self) -> bool:
        return len(self._data) >= self.depth

    @property
    def count(self) -> int:
        return len(self._data)

    def push(self, item: Dict[str, Any]) -> bool:
        if self.full:
            return False
        self._data.append(item)
        return True

    def pop(self) -> Optional[Dict[str, Any]]:
        if self.empty:
            return None
        return self._data.popleft()

    def peek(self) -> Optional[Dict[str, Any]]:
        if self.empty:
            return None
        return self._data[0]


class ArchSimulator:
    """周期精确架构仿真引擎。

    仿真流程:
    1. 拓扑排序确定 PE 执行顺序
    2. 每周期: 按序执行每个 PE 的 behavior(ctx)
    3. 通过 interconnect 传播信号 (支持 valid/ready 握手和 FIFO)
    4. 更新状态 (state ← next_state)
    5. 收集性能指标 (含指令退休计数)

    用法:
        sim = ArchSimulator(arch)
        report = sim.run_with_workload(workload=instructions, max_cycles=10000)
        print(f"IPC: {report['ipc']}, Retired: {report['retired']}")
    """

    def __init__(self, arch: ArchDefinition):
        self.arch = arch
        self._pe_map: Dict[str, ProcessingElement] = {
            pe.name: pe for pe in arch.processing_elements
        }
        self._exec_order: List[str] = self._topological_sort()
        self._signals: Dict[str, Any] = {}
        self._cycle = 0

        # 延迟队列: {conn_key: deque[(remaining, value)]}
        self._conn_queues: Dict[str, deque] = {}
        for conn in arch.interconnects:
            key = f"{conn.src_pe}.{conn.dst_pe}"
            self._conn_queues[key] = deque()

        # 每 PE 的输入延迟队列: {pe_name: deque[(remaining, outputs_dict)]}
        self._latency_queues: Dict[str, deque] = {}
        for pe in arch.processing_elements:
            self._latency_queues[pe.name] = deque()

        # 每 PE 指标
        self._pe_metrics: Dict[str, Dict[str, Any]] = {
            pe.name: {
                "cycles_active": 0,
                "cycles_stalled": 0,
                "events": [],
            }
            for pe in arch.processing_elements
        }

        # 全局指标 (新增: 指令退休计数)
        self._global_metrics: Dict[str, Any] = {
            "total_cycles": 0,
            "stall_cycles": 0,
            "total_retired": 0,
        }

        # --- GPGPU 扩展 ---

        # Valid/Ready 握手状态 (per handshake interconnect)
        self._handshake_states: Dict[str, _HandshakeState] = {}
        for conn in arch.interconnects:
            if conn.handshake is not None:
                key = f"{conn.src_pe}.{conn.dst_pe}"
                self._handshake_states[key] = _HandshakeState()

        # FIFO 队列 (per queue interconnect)
        self._fifo_queues: Dict[str, _FifoQueue] = {}
        for conn in arch.interconnects:
            if conn.queue is not None:
                key = f"{conn.src_pe}.{conn.dst_pe}"
                self._fifo_queues[key] = _FifoQueue(depth=conn.queue.depth)

        # Scoreboard: 跟踪哪些 PE 因下游依赖而停顿
        self._scoreboard: Dict[str, List[str]] = {}  # pe_name → [busy_resource_names]
        for pe in arch.processing_elements:
            self._scoreboard[pe.name] = []

        # 多实例 PE 展开 (e.g., NUM_WARP=8 → 8 个 warp scheduler)
        self._instance_map: Dict[str, List[str]] = {}  # base_name → [instance_names]
        self._expand_instances()

        # --- Behavioral model instances (memory, register files, caches) ---
        self._pe_memory: Dict[str, MemoryModel] = {}
        self._pe_register_files: Dict[str, Dict[str, RegisterFileModel]] = {}
        self._pe_caches: Dict[str, Dict[str, CacheModel]] = {}
        self._pe_fifos: Dict[str, Dict[str, deque]] = {}
        self._init_behavioral_models()

    def _init_behavioral_models(self):
        """Initialize per-PE behavioral models (memory, register files, caches, FIFOs).

        Infers model requirements from PE metadata:
        - buffer_type="regfile" → RegisterFileModel
        - buffer_type="memory" → MemoryModel
        - buffer_type="queue" / "fifo" → deque FIFO
        - pe_type contains "cache" → CacheModel
        """
        for pe in self.arch.processing_elements:
            pe_name = pe.name

            # Memory model (for CPU cores, DMA, etc.)
            if pe.buffer_type == "memory" or pe.pe_type in ("cpu", "rv64_core", "perf_core", "eff_core", "core"):
                self._pe_memory[pe_name] = MemoryModel(
                    size=2**32,
                    base_addr=0x8000_0000,
                    little_endian=True,
                )

            # Register file (for CPU cores)
            if pe.buffer_type == "regfile" or pe.pe_type in ("cpu", "rv64_core", "perf_core", "eff_core", "core"):
                rf_width = 64 if "64" in pe.pe_type else 32
                self._pe_register_files[pe_name] = {
                    "int_rf": RegisterFileModel(
                        num_regs=32,
                        width=rf_width,
                        x0_is_zero=True,
                        read_ports=2,
                        write_ports=1,
                    ),
                }

            # Cache models
            if "cache" in pe.pe_type:
                ways = 8 if "big" in pe.name.lower() or "l2" in pe.pe_type else 2
                sets = 128 if "l2" in pe.pe_type else 64
                protocol = "MESI" if "coh" in pe.pe_type or pe.pe_type in ("l1_cache", "l2_cache") else "none"
                self._pe_caches[pe_name] = {
                    pe.name: CacheModel(
                        sets=sets,
                        ways=ways,
                        line_size=64,
                        protocol=protocol,
                        replacement="LRU",
                        name=pe.name,
                    ),
                }

            # FIFOs for queue-based PEs
            if pe.buffer_type in ("queue", "fifo") or pe.pe_type in ("noc_router", "router", "arbiter"):
                depth = pe.buffer_depth if pe.buffer_depth > 0 else 8
                self._pe_fifos[pe_name] = {
                    "main_q": deque(maxlen=depth),
                }

    def _expand_instances(self):
        """展开多实例 PE。

        如果 PE.num_instances > 1，生成带实例名的子条目加入 _pe_map。
        例: warp_scheduler with num_instances=8 → warp_scheduler[0]..warp_scheduler[7]
        """
        for pe in self.arch.processing_elements:
            if pe.num_instances > 1:
                inst_names = []
                for i in range(pe.num_instances):
                    inst_name = f"{pe.name}[{i}]"
                    inst_names.append(inst_name)
                    # Create a copy with instance-specific name
                    inst_pe = ProcessingElement(
                        name=inst_name,
                        pe_type=pe.pe_type,
                        description=pe.description,
                        inputs=pe.inputs,
                        outputs=pe.outputs,
                        state=pe.state,
                        behavior=pe.behavior,
                        latency=pe.latency,
                        can_stall=pe.can_stall,
                        is_pipeline_stage=pe.is_pipeline_stage,
                        pipeline_stage=pe.pipeline_stage,
                        issue_width=pe.issue_width,
                        num_pipes=pe.num_pipes,
                        buffer_type=pe.buffer_type,
                        buffer_depth=pe.buffer_depth,
                    )
                    self._pe_map[inst_name] = inst_pe
                    self._pe_metrics[inst_name] = {
                        "cycles_active": 0,
                        "cycles_stalled": 0,
                        "events": [],
                    }
                self._instance_map[pe.name] = inst_names

    def _topological_sort(self) -> List[str]:
        """拓扑排序确定 PE 执行顺序。"""
        deps = self.arch.get_dependencies()
        visited = set()
        order = []

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            for dep in deps.get(name, []):
                visit(dep)
            order.append(name)

        for name in deps:
            visit(name)
        return order

    def _init_signals(self, init_inputs: Optional[Dict[str, Any]] = None):
        """初始化信号表。

        Supports both bare port names (applied to all PEs) and
        fully-qualified names like ``pe_name.port_name`` for per-PE
        control (e.g. ``sm_0.imem_wr_en``).

        Only resets input-port signals; preserves state and other
        signals so that multi-phase workloads (e.g. imem loading
        followed by kernel launch) do not lose state.
        """
        for pe in self.arch.processing_elements:
            for port in pe.inputs:
                key = f"{pe.name}.{port.name}"
                if init_inputs is None:
                    self._signals[key] = 0
                else:
                    # Prefer fully-qualified key, fallback to bare port name
                    self._signals[key] = init_inputs.get(
                        key, init_inputs.get(port.name, 0)
                    )

    def _evaluate_handshake(self, conn: InterconnectSpec, src_name: str,
                             dst_name: str) -> bool:
        """评估 valid/ready 握手是否 fire。

        返回 True 表示数据传输发生。
        """
        key = f"{src_name}.{dst_name}"
        hs = self._handshake_states.get(key)
        if hs is None:
            return False

        # 默认: 发送方有数据就置 valid，接收方始终 ready
        src_valid_key = f"{src_name}.{conn.handshake.valid_signal}"
        dst_ready_key = f"{dst_name}.{conn.handshake.ready_signal}"

        hs.valid = self._signals.get(src_valid_key, 0)
        hs.ready = self._signals.get(dst_ready_key, 1)
        hs.fire_last_cycle = (hs.valid & hs.ready) == 1
        return hs.fire_last_cycle

    def _step_fifo_queues(self):
        """推进 FIFO 队列：从队头弹出到目标 PE 信号。"""
        for conn in self.arch.interconnects:
            if conn.queue is None:
                continue
            key = f"{conn.src_pe}.{conn.dst_pe}"
            fifo = self._fifo_queues.get(key)
            if fifo is None:
                continue

            # Pop one item if destination is ready
            item = fifo.pop()
            if item is None:
                continue

            for sig in conn.signals:
                dst_key = f"{conn.dst_pe}.{sig.name}"
                self._signals[dst_key] = item.get(sig.name, 0)

    def _try_push_fifo(self, conn: InterconnectSpec, src_name: str,
                       outputs: Dict[str, Any]) -> bool:
        """尝试将 PE 输出推入 FIFO。返回是否成功。"""
        key = f"{src_name}.{conn.dst_pe}"
        fifo = self._fifo_queues.get(key)
        if fifo is None:
            return False
        val = {sig.name: outputs.get(sig.name, 0) for sig in conn.signals}
        return fifo.push(val)

    def step(self) -> Dict[str, Any]:
        """执行一个仿真周期。返回所有 PE 的输出。"""
        from collections import deque

        # 1. 处理模型周期回调
        if self.arch.model:
            self.arch.model.on_cycle(self._cycle)

        # 2. 处理连线延迟队列
        conn_arrivals: Dict[str, Any] = {}
        for conn in self.arch.interconnects:
            if conn.handshake is not None or conn.queue is not None:
                continue  # handled separately
            key = f"{conn.src_pe}.{conn.dst_pe}"
            q = self._conn_queues.get(key, deque())
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
                val_dict = arrived[-1]
                for sig in conn.signals:
                    dst_key = f"{conn.dst_pe}.{sig.name}"
                    scalar = val_dict.get(sig.name, 0) if isinstance(val_dict, dict) else val_dict
                    self._signals[dst_key] = scalar
                    conn_arrivals[key] = scalar

        # 3. 处理 FIFO 队列 (GPGPU 风格)
        self._step_fifo_queues()

        # 4. 处理 PE 延迟队列
        for pe in self.arch.processing_elements:
            q = self._latency_queues[pe.name]
            arrived_outputs = []
            remaining = deque()
            for item in q:
                rem, outputs = item
                rem -= 1
                if rem <= 0:
                    arrived_outputs.append(outputs)
                else:
                    remaining.append((rem, outputs))
            self._latency_queues[pe.name] = remaining
            if arrived_outputs:
                outputs = arrived_outputs[-1]
                for port in pe.outputs:
                    self._signals[f"{pe.name}.{port.name}"] = outputs.get(port.name, 0)

        # 5. 按拓扑序执行 PE 行为函数
        pe_outputs: Dict[str, Any] = {}
        for pe_name in self._exec_order:
            pe = self._pe_map.get(pe_name)
            if pe is None:
                continue

            # Execute with children (hierarchical PE)
            outputs = self._execute_pe(pe)
            if outputs is not None:
                pe_outputs[pe_name] = outputs

        # 6. 周期边界：提交寄存器文件 pending writes，clear pipeline control flags
        for pe_name, rfs in self._pe_register_files.items():
            for rf in rfs.values():
                rf.commit()

        self._cycle += 1
        self._global_metrics["total_cycles"] = self._cycle
        return pe_outputs

    def _execute_pe(self, pe: ProcessingElement) -> Optional[Dict[str, Any]]:
        """执行单个 PE（含子 PE 层次执行）。返回 PE 输出。"""
        if pe.behavior is None and not pe.children:
            return None

        # Build input dict
        inp = {}
        for port in pe.inputs:
            key = f"{pe.name}.{port.name}"
            inp[port.name] = self._signals.get(key, 0)

        # Check scoreboard-based stall
        is_stalled = False
        if pe.can_stall:
            stall_signal = f"stall_{pe.name}"
            is_stalled = self._signals.get(stall_signal, 0) == 1
            if is_stalled:
                self._pe_metrics[pe.name]["cycles_stalled"] += 1
                return None

        self._pe_metrics[pe.name]["cycles_active"] += 1

        # Attach behavioral models to CycleContext
        ctx = CycleContext(
            cycle=self._cycle,
            inputs=inp,
            state={s.name: self._signals.get(f"{pe.name}.{s.name}",
                      s.default if s.default is not None else 0)
                   for s in pe.state},
            model=self.arch.model,
            memory=self._pe_memory.get(pe.name),
            register_files=self._pe_register_files.get(pe.name, {}),
            caches=self._pe_caches.get(pe.name, {}),
            fifos=self._pe_fifos.get(pe.name, {}),
        )
        if pe.behavior is not None:
            pe.behavior(ctx)

        # Execute children (hierarchical PE)
        for child in pe.children:
            child_ctx = CycleContext(
                cycle=self._cycle,
                inputs=inp,
                state={s.name: self._signals.get(f"{child.name}.{s.name}",
                          s.default if s.default is not None else 0)
                       for s in child.state},
                model=self.arch.model,
                memory=self._pe_memory.get(child.name),
                register_files=self._pe_register_files.get(child.name, {}),
                caches=self._pe_caches.get(child.name, {}),
                fifos=self._pe_fifos.get(child.name, {}),
            )
            if child.behavior is not None:
                child.behavior(child_ctx)
            # Merge child outputs into parent outputs
            for k, v in child_ctx.outputs.items():
                ctx.outputs.setdefault(k, v)
            # Merge child metrics
            for k, v in child_ctx.metrics.items():
                ctx.metrics.setdefault(k, 0)
                if isinstance(v, (int, float)):
                    ctx.metrics[k] += v
            # Merge retirement count
            ctx.retired += child_ctx.retired

        # Collect outputs
        result = dict(ctx.outputs)
        for port in pe.outputs:
            self._signals[f"{pe.name}.{port.name}"] = ctx.outputs.get(port.name, 0)

        # Record metrics
        for k, v in ctx.metrics.items():
            self._pe_metrics[pe.name].setdefault(k, 0)
            if isinstance(v, (int, float)):
                self._pe_metrics[pe.name][k] += v

        # Track instruction retirement (GPGPU 精确 IPC)
        if ctx.retired > 0:
            self._global_metrics["total_retired"] += ctx.retired

        # Push outputs to interconnects
        self._push_outputs(pe, pe.name, result)

        # Update state
        for s in pe.state:
            key = f"{pe.name}.{s.name}"
            if s.name in ctx.next_state:
                self._signals[key] = ctx.next_state[s.name]
            elif key not in self._signals:
                self._signals[key] = s.default

        return result

    def _push_outputs(self, pe: ProcessingElement, pe_name: str, outputs: Dict[str, Any]):
        """将 PE 输出推到互连。支持延迟队列、握手、FIFO。"""
        for conn in self.arch.interconnects:
            if conn.src_pe != pe_name:
                continue
            key = f"{pe_name}.{conn.dst_pe}"

            # Handshake interconnect
            if conn.handshake is not None:
                # Valid is asserted, ready comes from destination
                dst_ready_key = f"{conn.dst_pe}.{conn.handshake.ready_signal}"
                is_ready = self._signals.get(dst_ready_key, 1)
                if is_ready:
                    val = {sig.name: outputs.get(sig.name, 0)
                           for sig in conn.signals}
                    if conn.delay_cycles > 0:
                        self._conn_queues[key].append((conn.delay_cycles, val))
                    else:
                        for sig in conn.signals:
                            dst_key = f"{conn.dst_pe}.{sig.name}"
                            self._signals[dst_key] = outputs.get(sig.name, 0)
                continue

            # FIFO interconnect
            if conn.queue is not None:
                self._try_push_fifo(conn, pe_name, outputs)
                continue

            # Standard delay queue
            val = {sig.name: outputs.get(sig.name, 0)
                   for sig in conn.signals}
            delay = max(conn.delay_cycles, pe.latency)
            if delay > 0:
                self._conn_queues[key].append((delay, val))
            else:
                for sig in conn.signals:
                    dst_key = f"{conn.dst_pe}.{sig.name}"
                    self._signals[dst_key] = outputs.get(sig.name, 0)

    def run(self, num_cycles: int,
            init_inputs: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """运行多个周期，返回每周期输出。"""
        self._init_signals(init_inputs)
        self._cycle = 0
        results = []
        for _ in range(num_cycles):
            outputs = self.step()
            results.append({
                "cycle": self._cycle - 1,
                "outputs": dict(outputs),
            })
        return results

    def run_with_workload(self, workload: Any = None,
                          max_cycles: int = 10000,
                          init_inputs: Optional[Dict[str, Any]] = None) -> dict:
        """加载工作负载运行，返回完整性能报告。

        Args:
            workload: 指令流/数据流/配置（根据架构类型解释）
            max_cycles: 最大仿真周期数
            init_inputs: 初始输入信号（如 {"rst_n": 1}），避免停留在复位状态

        Returns:
            {
                total_cycles, ipc, throughput, stalls,
                total_retired, per_pe_metrics, bottleneck_analysis
            }
        """
        self._init_signals(init_inputs)
        self._cycle = 0

        # If workload is a list of instructions (for ISA models)
        inst_list = workload if isinstance(workload, list) else []

        for cycle in range(max_cycles):
            outputs = self.step()
            # Check for completion: all PEs idle, no pending work
            if not outputs and cycle > 0:
                break

        return self._build_report(inst_list)

    def _build_report(self, inst_list: list = None) -> dict:
        """构建性能报告。"""
        total = self._global_metrics["total_cycles"]
        stalls = self._global_metrics["stall_cycles"]
        retired = self._global_metrics["total_retired"]

        # IPC: 从退休指令数精确计算 (GPGPU 风格)
        ipc = retired / max(total, 1) if retired > 0 else 0.0

        # 如果没有退休计数，回退到 ISA 模型
        if retired == 0 and self.arch.model and hasattr(self.arch.model, 'iss') and self.arch.model.iss:
            try:
                isa = self.arch.model.iss
                if hasattr(isa, 'state') and hasattr(isa.state, 'regs'):
                    ipc = 1.0  # default heuristic
            except Exception:
                pass

        # PE-level bottleneck analysis
        bottlenecks = []
        max_stall_pe = None
        max_stall = 0
        for pe_name, metrics in self._pe_metrics.items():
            if metrics["cycles_stalled"] > max_stall:
                max_stall = metrics["cycles_stalled"]
                max_stall_pe = pe_name

        if max_stall_pe and total > 0:
            bottleneck_pct = max_stall / total * 100
            if bottleneck_pct > 10:
                bottlenecks.append(
                    f"{max_stall_pe}: stalled {bottleneck_pct:.0f}% of cycles"
                )

        # Scoreboard analysis (GPGPU 风格)
        scoreboard_analysis = {}
        for pe_name, busy_resources in self._scoreboard.items():
            if busy_resources:
                scoreboard_analysis[pe_name] = busy_resources

        return {
            "total_cycles": total,
            "ipc": ipc,
            "throughput": len(inst_list) / max(total, 1) if inst_list else retired / max(total, 1),
            "stalls": stalls,
            "total_retired": retired,
            "per_pe_metrics": dict(self._pe_metrics),
            "bottleneck_analysis": bottlenecks,
            "scoreboard_analysis": scoreboard_analysis,
        }

    def set_scoreboard(self, pe_name: str, busy_resources: List[str]):
        """设置 PE 的 scoreboard 状态。

        用于 GPGPU 风格依赖跟踪：当某个 warp 的功能单元繁忙时，
        调度器会选择其他就绪的 warp 执行。
        """
        self._scoreboard[pe_name] = busy_resources

    def generate_test_vectors(self, num_vectors: int = 100) -> List[dict]:
        """自动生成测试向量，覆盖各种输入组合。"""
        import random
        tests = []
        for _ in range(num_vectors):
            inp = {}
            for pe in self.arch.processing_elements:
                for port in pe.inputs:
                    if port.width <= 1:
                        inp[f"{pe.name}.{port.name}"] = random.randint(0, 1)
                    elif port.width <= 8:
                        inp[f"{pe.name}.{port.name}"] = random.randint(0, 255)
                    else:
                        max_val = (1 << min(port.width, 16)) - 1
                        inp[f"{pe.name}.{port.name}"] = random.randint(0, max_val)
            tests.append({"inputs": inp})
        return tests

    def check_timing_constraints(self) -> List[str]:
        """检查协议时序约束是否满足（用于 Protocol_Model）。"""
        violations = []
        if self.arch.model is None:
            return violations
        if self.arch.model.model_type != "protocol":
            return violations

        model = self.arch.model
        for conn in self.arch.interconnects:
            for sig in conn.signals:
                constraint = model.get_service("timing_constraint",
                                               constraint=sig.name)
                if constraint and conn.delay_cycles > constraint:
                    violations.append(
                        f"Interconnect {conn.src_pe}->{conn.dst_pe}: "
                        f"delay {conn.delay_cycles} exceeds timing "
                        f"constraint {constraint} for {sig.name}"
                    )
        return violations
