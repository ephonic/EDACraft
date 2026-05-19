"""
rtlgen.arch_skel — Architecture Skeleton Generator

Generates AgentPackage bundles from ArchDefinition:
  - DSL Module skeleton with ports, state variables, and TODO comments
  - Golden test vectors from behavioral reference
  - Implementation steps based on PE type and metadata
  - Interconnect interface definition

Template categories (PE type → skeleton template):
  CPU:    ifu, idu, alu, lsu, rtu/rob, regfile, cache
  GPGPU:  cta_scheduler, warp_scheduler, sm_wrapper, pipe, pc_control,
          shared_mem, icache, dcache, arbiter, pop_cnt
  Memory: memory_controller, dfi_sequencer
  Generic: generic

GPGPU patterns from reference RTL:
  - Generate-loop patterns (per-warp pc_control, per-SM sm_wrapper)
  - Valid/ready handshake interface generation
  - Sub-module decomposition (cta_scheduler → 5 sub-modules)
  - Barrier synchronization state machines
  - Resource tracking (VGPR/SGPR/LDS allocation)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.arch_def import (
    AgentPackage,
    ArchDefinition,
    CycleContext,
    ProcessingElement,
    StateDesc,
)
from rtlgen.core import Module, Input, Output, Wire, Reg


# =====================================================================
# Skeleton Templates by PE Type
# =====================================================================

class _TemplateContext:
    """Template execution context for skeleton generation."""

    def __init__(self, pe: ProcessingElement, arch: ArchDefinition):
        self.pe = pe
        self.arch = arch
        self.module: Optional[Module] = None


def _create_base_module(pe: ProcessingElement) -> Module:
    """创建带端口声明的基础 DSL Module。"""
    module = Module(pe.name)
    module._type_name = pe.name  # Override class name with PE name
    # Clock and reset
    module.clk = Input(1, "clk")
    module.rst_n = Input(1, "rst_n")
    # Data ports
    for port in pe.inputs:
        setattr(module, port.name, Input(port.width, port.name))
    for port in pe.outputs:
        setattr(module, port.name, Output(port.width, port.name))
    return module


def _declare_state_vars(module: Module, state_list: List[StateDesc]):
    """根据 StateDesc 声明状态变量。

    For regfile/memory/queue/fifo types with large depth, declare as
    Array instead of unrolling individual Regs to avoid skeleton bloat.
    """
    for sd in state_list:
        if sd.rtl_type == "reg":
            width = sd.rtl_width or 32
            reg = Reg(width, sd.name)
            setattr(module, sd.name, reg)
        elif sd.rtl_type == "regfile":
            depth = sd.rtl_depth or 32
            width = sd.rtl_width or 32
            if depth <= 8:
                for i in range(depth):
                    reg = Reg(width, f"{sd.name}_{i}")
                    setattr(module, f"{sd.name}_{i}", reg)
            else:
                arr = Array(width, depth, sd.name)
                setattr(module, sd.name, arr)
        elif sd.rtl_type in ("memory", "queue", "fifo"):
            depth = sd.rtl_depth or 64
            width = sd.rtl_width or 32
            if depth <= 8:
                for i in range(depth):
                    reg = Reg(width, f"{sd.name}_{i}")
                    setattr(module, f"{sd.name}_{i}", reg)
            else:
                arr = Array(width, depth, sd.name)
                setattr(module, sd.name, arr)
        else:
            # Default: reg
            width = sd.rtl_width or 32
            reg = Reg(width, sd.name)
            setattr(module, sd.name, reg)


# =====================================================================
# PE Type → Template → Implementation Steps
# =====================================================================

_TEMPLATE_STEPS: Dict[str, List[str]] = {
    # ---- CPU Pipeline Stages ----
    "ifu": [
        "1. 实现 PC 寄存器（seq block with reset）",
        "2. 实现 PC 递增逻辑（pc_next = pc + 4 * issue_width）",
        "3. 实现分支预测结构（BTB/BHT/RAS 查找）",
        "4. 整合预测结果到 PC 选择器",
        "5. 实现取指数据打包（指令 bundle 输出）",
        "6. 实现停顿/冲刷处理",
        "7. 验证：对比 behavior model 的 PC 序列和指令流",
    ],
    "idu": [
        "1. 实现指令解码逻辑（opcode → func）",
        "2. 实现寄存器重命名表（arch → preg）",
        "3. 实现分发队列（dispatch queue）",
        "4. 实现到各 pipe 的信号分发",
        "5. 实现 stall 处理（ROB full → stall IFU）",
        "6. 验证：对比 behavior model 的分发序列",
    ],
    "alu": [
        "1. 实现多 pipe 分发逻辑（opcode → pipe）",
        "2. 实现各 pipe 的算子（ALU/Mult/BJU）",
        "3. 实现旁路网络（bypass/forwarding）",
        "4. 实现 completion 信号到 RTU",
        "5. 实现异常/中断处理",
        "6. 验证：对比 behavior model 的运算结果",
    ],
    "lsu": [
        "1. 实现地址计算（base + offset）",
        "2. 实现 Load Queue / Store Queue",
        "3. 实现 D-Cache 接口",
        "4. 实现数据前递（load → ALU bypass）",
        "5. 实现内存序约束（fence/acquire/release）",
        "6. 验证：对比 behavior model 的访存序列",
    ],
    "rtu": [
        "1. 实现 ROB 队列（create → complete → retire）",
        "2. 实现 commit/retire 逻辑",
        "3. 实现异常/flush 生成",
        "4. 实现物理寄存器状态管理",
        "5. 验证：对比 behavior model 的 retire 序列",
    ],
    "regfile": [
        "1. 实现多读多写寄存器文件",
        "2. 实现读写端口仲裁",
        "3. 实现 bypass 逻辑（同时读写同一寄存器）",
        "4. 验证：对比 behavior model 的寄存器状态",
    ],
    "cache": [
        "1. 实现 tag/data 阵列",
        "2. 实现 LRU 替换逻辑",
        "3. 实现 miss/refill 状态机",
        "4. 实现写策略（write-through/write-back）",
        "5. 验证：对比行为模型的 hit/miss 模式",
    ],

    # ---- GPGPU: CTA Scheduler (workgroup dispatch) ----
    # Reference: cta_scheduler → allocator_neo + top_resource_table +
    #            inflight_wg_buffer + gpu_interface + dis_controller
    "cta_scheduler": [
        "1. 实现 inflight_wg_buffer：host 请求接收 + 缓冲（valid/ready 握手）",
        "2. 实现 allocator_neo：VGPR/SGPR/LDS 资源分配（CAM 查找空闲块）",
        "3. 实现 top_resource_table：全局资源跟踪表（已分配 VGPR/SGPR/LDS 起始地址和大小）",
        "4. 实现 dis_controller：dispatch FSM（idle → alloc → dispatch → flush）",
        "5. 实现 gpu_interface：将 workgroup 分发到 CU（CU 就绪检查 + round-robin 选择）",
        "6. 实现 workgroup 完成处理（warp_done 计数 → 释放资源 → 通知 host）",
        "7. 验证：对比 behavior model 的资源分配和 dispatch 序列",
    ],

    # ---- GPGPU: Warp Scheduler (per-SM warp-level control) ----
    # Reference: warp_scheduler → pc_control × NUM_WARP (generate loop) +
    #            fixed_pri_arb + pop_cnt + barrier sync
    "warp_scheduler": [
        "1. 实现 warp_active 跟踪寄存器（warpReq 置位，warp_end 清零）",
        "2. 实现 pc_control 实例的 generate 循环（per-warp PC 管理：jump/stall/halt/normal）",
        "3. 实现 fixed priority arbiter：从就绪 warp 中选择下一个取指 warp",
        "4. 实现 barrier 同步状态机（warp_bar_belong + warp_bar_data）",
        "5. 实现 warpRsp 完成信号（warp_end → 通知 CTA scheduler）",
        "6. 实现 flush 生成（branch_jump 或 warp_end → 冲刷 I-buffer）",
        "7. 验证：对比 behavior model 的 warp 调度序列和 barrier 行为",
    ],

    # ---- GPGPU: PC Control (per-warp PC state machine) ----
    "pc_control": [
        "1. 实现 PC 选择器（pc_src: 1=新warp, 2=正常递增, 3=stall, 4=branch）",
        "2. 实现 PC 递增逻辑（pc_next = pc + NUM_FETCH * 4）",
        "3. 实现 fetch mask 生成（哪些 instruction lane 有效）",
        "4. 实现 stall/jump/halt 状态切换",
        "5. 验证：对比 behavior model 的 PC 序列",
    ],

    # ---- GPGPU: SM Wrapper ----
    # Reference: sm_wrapper → cta2warp + pipe + instruction_cache +
    #            shared_mem + l1_dcache + stream_fifo_pipe (LSU→D-cache)
    "sm_wrapper": [
        "1. 实现 cta2warp：接收 CTA dispatch → 生成 warp 请求（warpReq 握手）",
        "2. 实例化 pipe：SM 流水线（fetch/decode/IBuffer/Issue/OperandCollect/Execute/Writeback）",
        "3. 实现 instruction_cache：指令缓存 + 取指请求",
        "4. 实现 shared_mem：LDS 内存 + bank 冲突检测",
        "5. 实现 l1_dcache：数据缓存 + miss/refill 状态机",
        "6. 实现 LSU→D-cache FIFO 队列（stream_fifo_pipe_true：缓冲 LSU 内存请求）",
        "7. 实现 cache invalidation（workgroup 完成时冲刷 L1 I-cache）",
        "8. 验证：对比 behavior model 的 warp 执行和内存访问模式",
    ],

    # ---- GPGPU: SM Pipeline ----
    "pipe": [
        "1. 实现 Fetch 级：从 I-cache 取指 → 送入 Decode",
        "2. 实现 Decode 级：2-wide 解码 → 生成控制信号",
        "3. 实现 IBuffer 级：指令缓冲 + warp 选择",
        "4. 实现 Issue 级：发射到执行单元 + 依赖检查",
        "5. 实现 OperandCollect 级：收集操作数（寄存器读 + 前递）",
        "6. 实现 Execute 级：分发到 vALU/LSU/sALU/CSR/SIMT/SFU/MUL/TC/vFPU",
        "7. 实现 Writeback 级：写回结果 + 释放 scoreboard",
        "8. 验证：对比 behavior model 的流水线执行序列",
    ],

    # ---- GPGPU: Arbiters ----
    "arbiter": [
        "1. 实现请求输入（req_i × N）",
        "2. 实现仲裁算法（round-robin / fixed-priority / LRU）",
        "3. 实现 grant 输出一热编码（grant_o × N）",
        "4. 实现 ready 反馈（用于握手）",
        "5. 验证：对比 behavior model 的仲裁序列",
    ],

    # ---- GPGPU: Shared Memory ----
    "shared_mem": [
        "1. 实现多 bank SRAM 阵列（NUM_BANK × DEPTH × WIDTH）",
        "2. 实现 bank 冲突检测（同一 bank 多请求 → stall 或 serialize）",
        "3. 实现地址到 bank 的映射（地址低位 → bank 索引）",
        "4. 实现读写端口（每 bank 独立访问）",
        "5. 验证：对比 behavior model 的 bank 访问模式",
    ],

    # ---- GPGPU: Pop Count ----
    "pop_cnt": [
        "1. 实现位计数逻辑（count number of 1s in input vector）",
        "2. 实现组合逻辑或流水线版本（根据宽度选择）",
        "3. 验证：对所有输入模式计数正确",
    ],

    # ---- Memory Controller (DDR3/DDR4/LPDDR5) ----
    "memory_controller": [
        "1. 实现初始化 FSM（POWERUP → CKE low → LOAD_MODE → ZQCL → PRECHARGE_ALL）",
        "2. 实现 refresh 定时器（64ms/8192 行倒计时 + 自动刷新触发）",
        "3. 实现 row buffer 管理（per-bank open row 跟踪 + hit/miss 检测）",
        "4. 实现命令调度 FSM（IDLE → ACTIVATE → READ/WRITE → PRECHARGE）",
        "5. 实现地址解码（RBC/BRC 模式：addr → row/bank/col）",
        "6. 实现 write ack / read data 返回逻辑",
        "7. 验证：对比 behavioral model 的状态序列和行缓冲区行为",
    ],
    "dfi_sequencer": [
        "1. 实现命令时序延迟（tRCD, tRP, tRFC 等 JEDEC 时序）",
        "2. 实现写数据序列化（128-bit → 32-bit DFI burst）",
        "3. 实现读数据组装（32-bit → 128-bit 拼合）",
        "4. 实现 shift register 延迟跟踪（accept/early-accept）",
        "5. 实现 DFI 输出映射（command → cs_n/ras_n/cas_n/we_n）",
        "6. 验证：对比 behavioral model 的 DFI 信号序列",
    ],

    # ---- Generic ----
    "generic": [
        "1. 阅读 behavioral_reference，理解组件功能",
        "2. 实现状态寄存器初始化（seq block with reset）",
        "3. 实现组合逻辑（输入 → 处理 → 输出）",
        "4. 实现时序逻辑（状态更新）",
        "5. 实现停顿/冲刷/异常处理",
        "6. 验证：对比 behavior model 的输出",
    ],
}


# =====================================================================
# Generate-Loop Pattern Support
# =====================================================================

@dataclass
class GenerateLoopPattern:
    """Generate 循环模式描述。

    GPGPU 中常见的 parameterized 实例化模式:
      - pc_control × NUM_WARP（per-warp PC 管理）
      - sm_wrapper × NUM_SM（per-SM 封装）
      - L2 cache × NUM_L2CACHE（per-cache 实例）

    用法:
        pattern = GenerateLoopPattern(
            instance_name="pc_control",
            loop_var="i",
            loop_count=8,
            port_mapping={
                "clk": "clk",
                "new_pc_i": f"new_pc_i_tmp[i]",
                "pc_next_o": f"pc_next_o_tmp[i]",
            },
        )
    """
    instance_name: str
    loop_var: str = "i"
    loop_count: int = 1
    port_mapping: Dict[str, str] = field(default_factory=dict)
    description: str = ""


def _detect_generate_loops(pe: ProcessingElement,
                           arch: ArchDefinition) -> List[GenerateLoopPattern]:
    """从 PE 定义中检测 generate loop 模式。

    如果 PE 的 num_instances > 1，生成对应的 generate loop 模式。
    """
    patterns = []
    if pe.num_instances > 1:
        patterns.append(GenerateLoopPattern(
            instance_name=pe.name,
            loop_var=pe.instance_id_template,
            loop_count=pe.num_instances,
            description=f"{pe.name} × {pe.num_instances} instances",
        ))

    # Check for child PEs that should be generated in loops
    for child in pe.children:
        if child.num_instances > 1:
            patterns.append(GenerateLoopPattern(
                instance_name=child.name,
                loop_var=child.instance_id_template,
                loop_count=child.num_instances,
                description=f"{child.name} × {child.num_instances} instances",
            ))

    return patterns


# =====================================================================
# Handshake Interface Builder
# =====================================================================

def _build_handshake_interface(pe: ProcessingElement,
                               arch: ArchDefinition) -> Dict[str, Any]:
    """构建 PE 的 valid/ready 握手接口定义。

    从 interconnect 中检测 handshake 类型的连接，
    生成 valid/ready 信号对定义。
    """
    handshake_ports = []

    for conn in arch.interconnects:
        if conn.handshake is None:
            continue

        if conn.dst_pe == pe.name:
            # Input handshake
            handshake_ports.append({
                "direction": "input",
                "valid": f"{conn.src_pe}_{conn.handshake.valid_signal}",
                "ready": f"{pe.name}_{conn.handshake.ready_signal}",
                "from": conn.src_pe,
                "signals": [s.name for s in conn.signals],
            })
        if conn.src_pe == pe.name:
            # Output handshake
            handshake_ports.append({
                "direction": "output",
                "valid": f"{pe.name}_{conn.handshake.valid_signal}",
                "ready": f"{conn.dst_pe}_{conn.handshake.ready_signal}",
                "to": conn.dst_pe,
                "signals": [s.name for s in conn.signals],
            })

    return {"handshake_ports": handshake_ports}


# =====================================================================
# Queue/FIFO Interface Builder
# =====================================================================

def _build_queue_interface(pe: ProcessingElement,
                           arch: ArchDefinition) -> Dict[str, Any]:
    """构建 PE 的 FIFO 队列接口定义。"""
    queue_ports = []

    for conn in arch.interconnects:
        if conn.queue is None:
            continue

        if conn.dst_pe == pe.name:
            queue_ports.append({
                "direction": "input",
                "fifo_depth": conn.queue.depth,
                "from": conn.src_pe,
                "signals": [s.name for s in conn.signals],
            })
        if conn.src_pe == pe.name:
            queue_ports.append({
                "direction": "output",
                "fifo_depth": conn.queue.depth,
                "to": conn.dst_pe,
                "signals": [s.name for s in conn.signals],
            })

    return {"queue_ports": queue_ports}


# =====================================================================
# Golden Test Generator
# =====================================================================

def _gen_golden_tests(pe: ProcessingElement,
                      arch: ArchDefinition,
                      num_tests: int = 100) -> List[dict]:
    """从行为函数生成 golden 测试向量。"""
    import random
    tests = []

    for i in range(num_tests):
        inputs = {}
        for port in pe.inputs:
            if port.name in ("clk", "rst_n"):
                continue
            if port.width <= 1:
                inputs[port.name] = 1 if i == 0 else random.randint(0, 1)
            elif port.width <= 4:
                inputs[port.name] = random.randint(0, (1 << port.width) - 1)
            else:
                inputs[port.name] = random.randint(0, (1 << min(port.width, 16)) - 1)

        # Run behavioral reference
        if pe.behavior:
            ctx = CycleContext(inputs=inputs, model=arch.model)
            try:
                pe.behavior(ctx)
                tests.append({
                    "inputs": inputs,
                    "expected_outputs": dict(ctx.outputs),
                })
            except Exception:
                # If behavior fails, skip this test
                continue
        else:
            # No behavior function: use pass-through
            tests.append({
                "inputs": inputs,
                "expected_outputs": {p.name: inputs.get(p.name, 0)
                                     for p in pe.outputs},
            })

    # Ensure at least one reset test
    if pe.behavior:
        reset_inputs = {p.name: 0 for p in pe.inputs}
        reset_inputs["rst_n"] = 0
        ctx = CycleContext(inputs=reset_inputs, model=arch.model)
        try:
            pe.behavior(ctx)
            tests.insert(0, {
                "inputs": reset_inputs,
                "expected_outputs": dict(ctx.outputs),
            })
        except Exception:
            pass

    return tests


# =====================================================================
# Interconnect Interface Builder
# =====================================================================

def _build_interface(pe: ProcessingElement,
                     arch: ArchDefinition) -> Dict[str, Any]:
    """构建 PE 的互连接口定义。"""
    upstream = []
    downstream = []

    for conn in arch.interconnects:
        if conn.dst_pe == pe.name:
            entry = {
                "from": conn.src_pe,
                "signals": [s.name for s in conn.signals],
                "flow_type": conn.flow_type,
            }
            upstream.append(entry)
        if conn.src_pe == pe.name:
            entry = {
                "to": conn.dst_pe,
                "signals": [s.name for s in conn.signals],
                "flow_type": conn.flow_type,
            }
            downstream.append(entry)

    result = {"upstream": upstream, "downstream": downstream}

    # Add handshake interface details
    result.update(_build_handshake_interface(pe, arch))

    # Add queue interface details
    result.update(_build_queue_interface(pe, arch))

    return result


# =====================================================================
# Performance Target Extractor
# =====================================================================

def _extract_targets(pe: ProcessingElement,
                     arch: ArchDefinition) -> Dict[str, Any]:
    """从 PE 和架构提取性能目标。"""
    targets = {}

    if pe.latency > 0:
        targets["max_latency"] = pe.latency
    if pe.issue_width > 1:
        targets["min_throughput"] = pe.issue_width
    if pe.pe_type in ("alu", "mac_array"):
        targets["target_freq"] = 500e6
    if pe.pe_type in ("warp_scheduler", "cta_scheduler"):
        targets["min_ipc"] = pe.num_instances  # GPGPU: IPC scales with warp count
    if arch.ppa_targets:
        targets.update(arch.ppa_targets)

    return targets


# =====================================================================
# Sub-module Decomposition for Hierarchical PEs
# =====================================================================

def _build_submodule_decomposition(pe: ProcessingElement,
                                   arch: ArchDefinition) -> Dict[str, Any]:
    """构建子模块分解描述。

    对于有 children 的 PE，生成子模块实例化和互连描述。
    例如 cta_scheduler 分解为 5 个子模块。
    """
    if not pe.children:
        return {}

    submodules = []
    for child in pe.children:
        submodules.append({
            "name": child.name,
            "type": child.pe_type,
            "description": child.description,
            "instances": child.num_instances,
        })

    # Internal connections between children
    internal_conns = []
    for conn in arch.interconnects:
        src_is_child = any(c.name == conn.src_pe for c in pe.children)
        dst_is_child = any(c.name == conn.dst_pe for c in pe.children)
        if src_is_child and dst_is_child:
            internal_conns.append({
                "from": conn.src_pe,
                "to": conn.dst_pe,
                "signals": [s.name for s in conn.signals],
            })

    return {
        "submodules": submodules,
        "internal_connections": internal_conns,
    }


# =====================================================================
# ArchSkeletonGenerator — Main Entry Point
# =====================================================================

class ArchSkeletonGenerator:
    """为 ArchDefinition 中的每个 PE 生成 AgentPackage。

    用法:
        gen = ArchSkeletonGenerator()
        packages = gen.generate_all(arch)
        ifu_pkg = packages["IFU"]
        # ifu_pkg.behavioral_reference
        # ifu_pkg.dsl_skeleton
        # ifu_pkg.golden_tests
        # ifu_pkg.implementation_steps
    """

    def generate_all(self, arch: ArchDefinition) -> Dict[str, AgentPackage]:
        """为架构中每个 PE 生成 AgentPackage。"""
        packages = {}
        for pe in arch.processing_elements:
            packages[pe.name] = self._generate_package(pe, arch)
        return packages

    def _generate_package(self, pe: ProcessingElement,
                          arch: ArchDefinition) -> AgentPackage:
        # 1. Create DSL Module with ports
        module = _create_base_module(pe)

        # 2. Generate state variables
        _declare_state_vars(module, pe.state)

        # 3. Generate golden tests
        golden_tests = _gen_golden_tests(pe, arch)

        # 4. Build interconnect interface (incl. handshake + queue)
        interface = _build_interface(pe, arch)

        # 5. Extract performance targets
        targets = _extract_targets(pe, arch)

        # 6. Generate implementation steps (GPGPU-aware)
        steps = _TEMPLATE_STEPS.get(pe.pe_type, _TEMPLATE_STEPS["generic"])

        # 7. Use behavioral reference (or default pass-through)
        behavior = pe.behavior or self._default_behavior(pe)

        # 8. Detect generate-loop patterns
        gen_loops = _detect_generate_loops(pe, arch)

        # 9. Sub-module decomposition
        submod_info = _build_submodule_decomposition(pe, arch)

        return AgentPackage(
            pe=pe,
            behavioral_reference=behavior,
            dsl_skeleton=module,
            golden_tests=golden_tests,
            performance_targets=targets,
            interconnect_interface=interface,
            implementation_steps=steps,
            generate_loops=gen_loops,
            submodule_decomposition=submod_info,
        )

    def _default_behavior(self, pe: ProcessingElement) -> Callable:
        """为没有行为函数的 PE 生成默认 pass-through 行为。

        先按名称匹配输入输出；名称不匹配时按位置一一映射。
        """
        input_names = [p.name for p in pe.inputs]

        def default_behavior(ctx: CycleContext):
            for port in pe.outputs:
                if port.name in ctx.inputs:
                    val = ctx.inputs[port.name]
                else:
                    # 按位置映射：第一个输入 -> 第一个输出
                    idx = pe.outputs.index(port)
                    if idx < len(input_names):
                        val = ctx.inputs.get(input_names[idx], 0)
                    else:
                        val = 0
                ctx.set_output(port.name, val)
        return default_behavior
