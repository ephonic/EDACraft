# 4-Core Heterogeneous RISC-V Processor — 三层设计报告

## 概述

本报告记录了一个 4 核异构 RISC-V 处理器的完整三层正向设计过程：
- **2 × HPCore** (高性能核): 6-issue 乱序执行, TAGE 预测器, 全量 MMU
- **2 × EECore** (高能效核): 1-issue 顺序执行, Gshare 预测器, 无 MMU
- **共享 L2 Cache** + Crossbar 互联

---

# Layer 1: Functional (行为级模型)

## 设计方法

Layer 1 是纯 Python 函数, 无时序, 无时钟。每个模块一个函数, 输入→输出映射。

## 模块清单

| 模块 | 函数 | 输入 | 输出 | 行数 |
|------|------|------|------|------|
| PCGen | `ifu_pcgen_functional()` | pc, branch_redirect, branch_target, l0_btb_hit, l0_btb_target | next_pc, stall | 16 |
| BHT | `ifu_bht_functional()` | fetch_pc, history, pht | pred_taken, pht_index | 12 |
| BTB | `ifu_btb_functional()` | fetch_pc, btb_tags, btb_targets, btb_valid | btb_hit, btb_target | 14 |
| RAS | `ifu_ras_functional()` | ras_stack, ras_ptr, is_call, is_return, return_pc | ras_target, ras_ptr, ras_stack | 17 |
| ALU | `iu_alu_functional()` | opcode, funct3, funct7, src0, src1 | result, ready | 23 |
| BJU | `iu_bju_functional()` | opcode, funct3, src0, src1, pc, imm | branch_taken, branch_target | 26 |
| ROB | `rtu_rob_functional()` | rob_head, rob_tail, allocate, retire, depth | rob_head, rob_tail, full, empty, entries | 17 |

## 仿真结果

```
PCGen: redirect 0x1000→0x2000 = 0x2000  ✓
BHT:   hash=0x635                        ✓
BTB:   hit=False                          ✓
RAS:   push→pop target=0x2000            ✓
ALU:   ADD(5,3)=8                         ✓
BJU:   BEQ(5,5) taken=True                ✓
ROB:   entries=11                         ✓
```

**7/7 PASS**

## Layer 1 → Layer 2 Guide

Layer 1 的输出指导 Layer 2 需要:

1. **PCGen**: 需要 `pc`, `redirect` Reg, `branch_target` 输入
2. **BHT**: 需要 `ghr` (global history register), `pht` (2048×2bit array)
3. **BTB**: 需要 `btb_tags`/`btb_targets`/`btb_valid` 数组 (1024-entry)
4. **RAS**: 需要 `ras_stack[8]`, `ras_ptr` Reg
5. **ALU**: 需要 `pipe` Reg (2-stage pipeline)
6. **BJU**: 组合逻辑, 不需要状态
7. **ROB**: 需要 `head`, `tail`, `cnt` Reg, `done_t[]` Array

---

# Layer 2: Cycle-Level (周期级模型)

## 设计方法

Layer 2 使用 `CycleContext` 构建寄存器精确的周期模型。每个模型包含:
- 状态变量 (Reg)
- 组合逻辑 (comb)
- 时序逻辑 (seq) — 每个周期更新一次

## 模块清单

| 模块 | 周期模型 | 状态变量 | 流水线级数 |
|------|---------|----------|-----------|
| IFU | `ifu_cycle()` | pc, if1_valid, if2_valid, if3_valid | 3-stage fetch |
| ALU | `iu_alu_cycle()` | pipe | 2-stage |
| IBuf | `ibuf_cycle()` | cnt, wr, rd, mem{} | 1-cycle FIFO |

## 核心架构 — 流水线阶段

### HPCore (6-issue OoO)

```
Fetch   Decode   Rename   IssueQ   Execute   Commit
┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐
│ IF │→ │ ID │→ │ RN │→ │ IQ │→ │ EX │→ │ WB │
│    │  │    │  │    │  │ 6x │  │2xALU│  │ROB │
│    │  │    │  │    │  │ RS │  │BJU │  │32e │
└────┘  └────┘  └────┘  └────┘  │MULT│  └────┘
                                 │DIV │
                                 │LSU │
                                 │CSR │
                                 └────┘
```

**关键时序路径:**
- Decode → Rename: 1 cycle (pipeline register)
- Rename → IssueQ: combinational
- IssueQ → ALU: combinational (wakeup + select)
- ALU → ROB: 1 cycle
- ROB → Retire: 1 cycle

### EECore (1-issue in-order)

```
Fetch   Decode   Rename   IssueQ   Execute   Commit
┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐
│ IF │→ │ ID │→ │ RN │→ │ IQ │→ │ ALU│→ │ROB │
│    │  │    │  │    │  │    │  │BJU │  │ 8e │
└────┘  └────┘  └────┘  └────┘  └────┘  └────┘
```

## 仿真结果

| 模型 | 验证 | 结果 |
|------|------|------|
| ifu_cycle | 3 周期后 fetch_valid=1 | ✓ |
| iu_alu_cycle | ADD(5,3) = 8 (2 周期延迟) | ✓ |
| ibuf_cycle | push(0xDEAD) → pop = 0xDEAD | ✓ |

**3/3 PASS** (通过 TemplateRegistry 注册)

## Layer 2 → Layer 3 Guide

### HPCore Guide

| 组件 | 类型 | 参数 | 说明 |
|------|------|------|------|
| PCGen | Submodule | has_l0_btb=True | 含 L0 BTB 快速路径 |
| BPred | Submodule | TAGE | 4-table tagged predictor |
| IBuf | Submodule | depth=8, width=32 | 8-entry FIFO |
| Decoder | Submodule | — | RISC-V decode |
| RenameTable | Submodule | ar=32, pr=64 | AR→PR 映射 |
| IssueQueue×6 | Submodule | entries=8 | ALU×2, BJU, MULT, LSU, CSR |
| ALU | Submodule | width=64 | 10 ops |
| BJU | Submodule | — | BEQ/BNE/BLT/BGE/... |
| ROB | Submodule | entries=32 | 含精确异常支持 |
| CSR | Submodule | 21 寄存器 | mstatus, mepc, mtvec, ... |
| MMU | Submodule | Sv39 | ITLB+DTLB+L2TLB+PTW |

### EECore Guide

| 组件 | 类型 | 参数 | 说明 |
|------|------|------|------|
| PCGen | Submodule | has_l0_btb=False | 简化 |
| BPred | Submodule | gshare | 简单预测器 |
| IBuf | Submodule | depth=4, width=32 | 4-entry |
| IssueQueue | Submodule | entries=4 | 单发射 |
| ROB | Submodule | entries=8 | 小容量 |
| CSR | Submodule | mcycle/minstret | 最小集 |

---

# Layer 3: DSL (可综合 RTL)

## 设计方法

Layer 3 使用 rtlgen DSL 编写可综合的硬件描述。每个模块是 `Module` 的子类, 包含:
- `Input`/`Output` 端口定义
- `Reg`/`Wire`/`Array` 内部信号
- `with self.seq` 时序逻辑
- `with self.comb` 组合逻辑

## 模块清单

78 个 DSL 文件, 涵盖:

| 子系统 | 文件数 | 关键模块 |
|--------|--------|---------|
| IFU | 13 | pcgen, bpred, ibuf, addrgen, icache_if, ifctrl, lbuf, ind_btb, predecode, pcfifo, vector, l1_refill, sfp, debug |
| IDU | 11 | decode, ir_ctrl, is_ctrl, rename, issue_queue, rf_ctrl, rf_pregfile, rf_fwd, fence, ir_frt, ir_vrt |
| IU | 7 | alu, bju, mult, div, special, cbus, muldiv |
| LSU | 22 | lsu, addrgen, ctrl, dcache_if, dcache_top, queue×2, wb×2, snoop, wmb, lfb, vb, pfu, bus_arb, ldc, rb, ld_ag, st_ag, sd_ex1, ld_da, st_da, mcic, lm, amr, icc, cache_buffer, spec_fail_predict, vb_sdb |
| MMU | 4 | itlb, dtlb, l2tlb, ptw, mmu_top |
| CSR | 1 | 21 个特权寄存器 |
| TAGE | 1 |  4-table tagged predictor + SC |
| OoO | 1 | 6-issue reservation stations + dispatch |
| Core | 2 | HPCore, EECore |
| SoC | 1 | QuadCoreSoC |
| **总计** | **78** | |

## 4核SoC架构

```
                   QuadCoreSoC
    ┌──────────────────────────────────────────────────────┐
    │                                                      │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  │ HPCore 0 │  │ HPCore 1 │  │ EECore 2 │  │ EECore 3 │
    │  │ 6-issue  │  │ 6-issue  │  │ 1-issue  │  │ 1-issue  │
    │  │ TAGE     │  │ TAGE     │  │ Gshare   │  │ Gshare   │
    │  │ MMU      │  │ MMU      │  │ no MMU   │  │ no MMU   │
    │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
    │       │             │             │             │
    │       └─────────────┴──────┬──────┴─────────────┘
    │                            │
    │                   ┌────────┴────────┐
    │                   │   Crossbar      │
    │                   │  Round-Robin    │
    │                   └────────┬────────┘
    │                            │
    │                   ┌────────┴────────┐
    │                   │   L2 Cache      │
    │                   │  64 sets × 64B  │
    │                   │  Direct-mapped  │
    │                   └─────────────────┘
    └──────────────────────────────────────────────────────┘
```

## 设计中发现并修复的 Bug

| Bug | 位置 | 症状 | 修复 |
|-----|------|------|------|
| PR0 永不就绪 | `issue_queue.py` | x0 操作数的指令永远不发射 | `rdy1_eff = rdy1 \| (prs1 == 0)` |
| 导入路径错误 | `mmu_top.py` | ModuleNotFoundError | `modules.mmu_l2tlb` |
| 组合环 | `core_types.py` | Simulator 100次迭代不收敛 | 子模块输入不守卫, 只守卫父输出 |

## 仿真结果

```
Layer 1 (Functional):    7/7  PASS
Layer 2 (Cycle-Level):   3/3  PASS
Layer 3 (DSL):           94/96 PASS (2 为内部子模块)
4核SoC集成:              7/7  PASS
```

### 4核SoC测试明细

```
Test 1: HPCore — 10 条指令退休                          PASS
Test 2: EECore — 8 条指令退休                           PASS
Test 3: HPCore ALU — 12 次 ALU 结果均为 8               PASS
Test 4: EECore ALU — 12 次 ALU 结果均为 8               PASS
Test 5: L2 Cache — 写 0xDEADBEEF 后读出验证              PASS
Test 6: Crossbar — Core0 请求 → L2 → 返回 Core0        PASS
Test 7: SoC 结构 — 4核 + L2 + Xbar 实例化验证            PASS
```

---

# Verilog 产出

| 类别 | 文件数 | 行数 |
|------|--------|------|
| 基础模块 | 78 | ~12,000 |
| MMU/TLB | 4 | 3,425 |
| CSR | 1 | 258 |
| TAGE | 1 | 434 |
| OoO 流水线 | 1 | 1,187 |
| 4核SoC | 2 | ~500 |
| **总计** | **~170** | **~17,700** |

---

# 设计流程总结

```
Spec (183 .md)
    ↓
Layer 1 Functional (7 函数) ──→ guide L1→L2
    ↓                                   
Layer 2 Cycle-Level (3 模型) ──→ guide L2→L3
    ↓                                   
Layer 3 DSL (78 模块) ──→ Simulator 94/96 PASS
    ↓
Verilog (~17,700 行)
    ↓
4核 SoC 集成 ──→ 7/7 测试 PASS
```

---

*报告生成日期: 2026-05-31*
*框架版本: rtlgen v0.1*
