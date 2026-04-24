# NPU 分层验证架构方案

> **Status**: 实施中  
> **Created**: 2026-04-20  
> **Goal**: 建立系统化的 NPU 验证流程，终结"RTL 仿真中 printf 调试"的低效模式。

---

## 1. 问题诊断：为什么当前调试如此痛苦？

我们在修复 `test_e2e_linear_relu` 时陷入了典型的**无参考调试陷阱**：

| 症状 | 根本原因 |
|------|----------|
| 改一行代码 → 等 30~60s 仿真 → 发现还是错 | RTL 仿真粒度太粗，没有更快的 golden reference |
| 看到 SRAM 读出 65533，不知道是 RTL 算错还是测试读错 | 缺少独立的**语义参考模型**来回答"正确答案应该是什么" |
| SystolicAdapter 不启动，同时怀疑 Adapter/仲裁/编译器/连接 | 缺少**模块级隔离测试**，无法快速排除变量 |
| `sram_a_req_valid=1` 但 `SRAM_A_req_valid=0` | 信号传播链不透明，调试需要深入 rtlgen 框架内部 |
| 端到端测试失败后，无法判断是编译器、RTL 还是测试基础设施的锅 | 三层问题（软件/编译器/硬件）混在一起，没有分层隔离 |

**核心缺失**：我们没有一个比 RTL 快 1000 倍、且**语义等价**的参考模型。

---

## 2. 验证架构（四层模型）

```
┌─────────────────────────────────────────────────────────────────┐
│  Level 3: 端到端自动对比 (End-to-End Comparator)                  │
│  ─────────────────────────────────────────────                  │
│  输入: PyTorch 模型 + 随机/定向测试数据                            │
│  流程: PyTorch 参考 → 编译器 → [BehavioralModel ↔ RTL Simulator] │
│  输出: 自动报告差异 (buffer/addr/expected/actual)                 │
│  耗时: ~2s / test case                                          │
├─────────────────────────────────────────────────────────────────┤
│  Level 2: 子系统级 RTL 测试 (Subsystem Tests)                     │
│  ─────────────────────────────────────────────                  │
│  组合特定模块进行定向测试:                                         │
│  • SystolicAdapter + PingPongSRAM (GEMM 数据通路)                │
│  • VecALU + Crossbar (逐元素操作通路)                              │
│  • DMA + AXI + SRAM (LOAD/STORE 通路)                             │
│  目的: 定位 bug 在哪条数据通路，而非整个 SoC                      │
├─────────────────────────────────────────────────────────────────┤
│  Level 1: 模块级 RTL 测试 (Module Unit Tests)                     │
│  ─────────────────────────────────────────────                  │
│  每个模块独立仿真，与预期波形或参考输出对比:                         │
│  • SystolicArray: 给定 weight/act，验证 psum 输出                 │
│  • VectorALU: 给定 opcode + a/b，验证 result                      │
│  • PingPongSRAM: 读写、bank swap 验证                             │
│  • Crossbar: block/stride/broadcast/gather 模式验证               │
│  • InstructionDecode: 每条指令的字段解码验证                       │
│  目的: 确保单个模块在集成前就是正确的                              │
├─────────────────────────────────────────────────────────────────┤
│  Level 0: 行为级参考模型 (Behavioral Model)                       │
│  ─────────────────────────────────────────────                  │
│  纯 Python 实现，只关心 ISA 语义，不关心 cycle:                     │
│  • SRAM: 4 个 numpy buffer (A/B/C/Scratch)                        │
│  • GEMM: np.dot(weight, act)                                      │
│  • VEC_ALU: np element-wise ops (relu→np.maximum(0,x))            │
│  • CROSSBAR: memcpy with stride/broadcast                         │
│  • LOAD/STORE: DRAM ↔ SRAM 搬运                                   │
│  耗时: <10ms / program                                            │
│  关键属性: **它是 RTL 的语义等价物，不是性能模型**                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 各层职责与交互

| 层级 | 验证什么问题 | 不验证什么问题 | 输出 |
|------|-------------|---------------|------|
| **L0 Behavioral** | 编译器生成的指令序列是否语义正确？算法映射是否正确？ | 时序、流水线气泡、 arbitration 冲突 | "给定这些指令，SRAM 的最终状态应该是什么" |
| **L1 Module RTL** | 单个模块的 FSM、数据通路、接口协议是否正确？ | 模块间交互 | "SystolicAdapter 在给定输入下应在 N 周期后输出 X" |
| **L2 Subsystem RTL** | 模块组合后的数据通路是否正确？握手协议是否匹配？ | 完整 SoC 的所有 corner case | "Adapter→Systolic→Adapter 回写这条通路工作正常" |
| **L3 E2E Compare** | 整个系统（编译器+RTL）与 PyTorch 参考是否一致？ | 性能、功耗、面积 | "NPU 输出与 PyTorch 的 diff 为 0" |

**核心工作流**：
1. 新算子支持 → 先在 **L0** 验证指令语义
2. 新硬件模块 → 先在 **L1** 验证模块功能
3. 集成新模块 → 在 **L2** 验证数据通路
4. 完整模型 → 在 **L3** 对比 PyTorch reference

---

## 3. 当前 bug 的定位策略（以 `test_e2e_linear_relu` 为例）

### 旧模式（无参考模型）
```
PyTorch → 编译器 → RTL 仿真 → 读 SRAM → 65533 → ???
                                   ↑
                              同时怀疑编译器/RTL/测试读法
```

### 新模式（有参考模型）
```
Step 1: PyTorch → 编译器 → BehavioralModel → 输出 = [5, 0, 2, 0]
        └──────────────────────────────────────┘
                    50ms, 确认编译器正确

Step 2: 编译器 → RTL 仿真 → 读 SRAM → 输出 = [5, 65533, 2, 65533]
        └──────────────────────────────────────┘
                    2s, 确认 RTL 在 ReLU 阶段出错

Step 3: 缩小范围
        • 只运行 GEMM 指令 → RTL 输出 [-3, -5, ...] 正确
        • 只运行 VEC_ALU(ReLU) 指令 → BehavioralModel 输出 [0,0,...]
                                              RTL 输出 [0, 65533, ...]
        → 锁定: VecALU 数据通路或结果写回有 signedness 问题
```

---

## 4. 实施计划

### Phase 1: Level 0 参考模型（今天完成）

**文件**: `skills/cpu/npu/sim/behavioral_model.py`

```python
class NPUBehavioralModel:
    """ISA-level semantic model of the NPU.
    
    Maintains 4 SRAM buffers and executes instructions sequentially.
    No cycle-accuracy: each instruction completes atomically.
    """
    
    def __init__(self, params: NeuralAccelParams):
        self.buffers = {
            0: np.zeros(params.SRAM_DEPTH, dtype=np.int16),  # SRAM_A
            1: np.zeros(params.SRAM_DEPTH, dtype=np.int16),  # SRAM_B
            2: np.zeros(params.SRAM_DEPTH, dtype=np.int16),  # SRAM_C
            3: np.zeros(params.SRAM_DEPTH, dtype=np.int16),  # Scratch
        }
        self.pc = 0
        self.program = []
        
    def load_program(self, instructions: List[int]):
        """Load binary instruction sequence."""
        
    def write_buffer(self, buf_id: int, addr: int, data: np.ndarray):
        """Write tensor data into buffer with array_size stride."""
        
    def read_buffer(self, buf_id: int, shape: Tuple, array_size: int) -> np.ndarray:
        """Read tensor data from buffer with array_size stride."""
        
    def step(self):
        """Execute one instruction."""
        
    def run(self) -> Dict[int, np.ndarray]:
        """Run to completion, return final buffer states."""
```

**支持的指令**（按优先级）：
1. `GEMM` —— matmul with array_size stride
2. `VEC_ALU` —— element-wise ops (ReLU, ADD, etc.)
3. `CROSSBAR` —— data movement
4. `LOAD/STORE` —— DRAM transfer (mocked)
5. `CONFIG` —— ignored at semantic level

### Phase 2: 对比框架（今天完成）

**文件**: `tests/test_npu_behavioral_vs_rtl.py`

```python
def compare_program(instructions, init_buffers, params):
    """Run same program on both BehavioralModel and RTL, compare results."""
    # L0 reference
    bm = NPUBehavioralModel(params)
    for buf_id, data in init_buffers.items():
        bm.write_buffer(buf_id, 0, data)
    bm.load_program(instructions)
    bm.run()
    
    # RTL
    npu = NeuralAccel(params)
    sim = Simulator(npu)
    sim.reset("rst_n")
    # ... load buffers, program, run ...
    
    # Compare
    for buf_id in [0, 1, 2, 3]:
        np.testing.assert_array_equal(
            bm.buffers[buf_id], 
            rtl_buffers[buf_id],
            err_msg=f"Buffer {buf_id} mismatch"
        )
```

### Phase 3: 用参考模型定位当前 bug（立即执行）

目标问题列表：
1. `test_e2e_linear_relu` 失败
2. `test_e2e_linear_identity` 也卡死（意外发现）
3. `_read_tensor_from_sram` signedness overflow

使用参考模型后，预期可以在 **5 分钟内**确定：
- 编译器输出是否正确
- 具体是哪条指令在 RTL 上行为异常

### Phase 4: 模块级测试补全（本周内）

为以下模块编写独立的 L1 测试：
- `test_systolic_array_standalone.py` —— 直接驱动 PE grid，验证 weight loading + compute
- `test_systolic_adapter_standalone.py` —— 用 mock SRAM 验证 FSM 时序
- `test_vector_alu_standalone.py` —— 验证所有 opcode
- `test_crossbar_standalone.py` —— 验证 4 种 transfer mode

### Phase 5: CI 集成（后续）

- `pytest tests/test_npu_behavioral_vs_rtl.py --count=100` —— 随机指令序列对比
- 每个 PR 必须通过 L0 + L3 测试

---

## 5. 文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `skills/cpu/npu/sim/behavioral_model.py` | 🚧 新建 | 行为级参考模型 |
| `tests/test_npu_behavioral_vs_rtl.py` | 🚧 新建 | RTL vs 参考模型对比框架 |
| `tests/test_npu_e2e_numerical.py` | 🔄 修改 | 使用参考模型断言，修复 signedness |
| `PLAN_behavioral_model_verification.md` | ✅ 本文档 | 架构设计与实施计划 |

---

## 6. 决策记录

| 决策 | 理由 |
|------|------|
| BehavioralModel 不做 cycle-accuracy | 我们的首要问题是**语义正确性**而非时序。cycle-accurate 模型和 RTL 一样难 debug，失去意义。 |
| BehavioralModel 放在 `skills/cpu/npu/sim/` | 让参考模型成为 NPU 包的一部分，编译器测试也可以直接 import 使用。 |
| 先建 L0 再修当前 bug | 没有参考模型的修复是盲目的。参考模型本身只需 ~150 行，ROI 极高。 |
| 对比测试从 buffer 级别而非 cycle 级别 | cycle-level 对比会导致大量无意义的 diff（RTL 可能有合法的气泡/延迟）。buffer-level 对比只关心"指令完成后内存是否正确"。 |

---

## 7. 附录：当前已知问题清单

1. **VecALU 未连接数据通路** —— `core.py` 中 `v_alu.a/b/result` 完全悬空
2. **SRAM_A req_valid 信号传播异常** —— `sram_a_req_valid=1` 但 `SRAM_A_req_valid=0`
3. **`_read_tensor_from_sram` signedness** —— 65533 未转 -3
4. **`test_e2e_linear_identity` 卡死** —— 可能是 SystolicAdapter 在 RD_ACT 阶段无进展

> 以上问题将在参考模型建立后，通过对比测试逐一收敛。
