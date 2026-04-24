# rtlgen 仿真器优化路线图

## 一、现状诊断

### 性能基准

| 场景 | 信号数 | 子模块数 | 速度 | 1M cycles 耗时 |
|------|--------|---------|------|---------------|
| Flat Counter | 3 | 0 | 170,854 cps | ~6s |
| NeuralAccel NPU | ~912 | 9 | 170 cps | ~98 min |
| **差距** | — | — | **1006x** | — |

### 瓶颈分析（Profile 数据，100 cycles）

- `_eval_comb()` / `_exec_stmts()`:  dominate runtime — 递归遍历全部 AST
- `_eval_expr()`: ~460K calls, 大量 `isinstance()` 检查
- `_to_int()`: ~900K calls, Python int 转换
- `_exec_assign()`: ~160K calls
- **总函数调用**: ~585万次 / 50步 = **~11.7万次/步**

### 核心问题

1. **AST 递归解释开销**: 每个 cycle 都重新递归遍历 AST 树，没有缓存执行计划
2. **层级仿真开销**: 子模块独立运行，父-子间反复 sync state（`_sync_to_child` + `_sync_from_child`）
3. **状态字典查找**: `self.state[name]` 字符串 key 查找发生在每个表达式评估中
4. **收敛检测**: 每次 `_eval_comb` 都全量 snapshot 比较 state
5. **子模块信号不可见**: `sim.peek("decode.dec_valid")` 失败，必须用 Wire bridge  workaround

---

## 二、分阶段改进方案

### Phase 1: AST JIT 编译器（预期 50–500x 加速）

**目标**: 将 AST 编译为扁平化的 Python 执行序列，消除递归和字典查找。

**技术方案**:

1. **模块扁平化 (Elaboration)**
   - 递归展开所有子模块，将所有信号名前缀化：`systolic.state` → `systolic__state`
   - 消除子模块边界，生成一个“超级模块”
   - 端口连接变为直接的信号赋值

2. **执行计划生成 (Compilation)**
   - 遍历扁平化后的 AST，生成有序的 Assign/If/For 执行列表
   - 用拓扑排序确定组合逻辑依赖顺序，减少收敛迭代次数
   - 为每个表达式预生成执行闭包：
     ```python
     # 原: _eval_expr(BinOp("+", Ref(sig_a), Const(1, 8)))
     # 编译后: lambda state: (state[idx_a] + 1) & 0xFF
     ```
   - State 从 `dict[str, int]` 改为 `list[int]`，用整数索引访问

3. **优化后的 step() 流程**
   ```
   step():
     1. 执行预编译的组合逻辑列表 (一次遍历，无需收敛迭代)
     2. 执行预编译的时序逻辑列表 (生成 next_state)
     3. Commit: next_state → state (list 拷贝)
     4. 再次执行组合逻辑 (reg 输出可能驱动 comb)
   ```

**预期效果**:
- 函数调用从 ~11.7万次/步 → ~1000次/步（直接 Python 算术）
- 速度从 170 cps → 8,500–85,000 cps（50–500x）
- 1M cycles 从 98 min → 12 s–2 min

**工作量**: ~3–5 天

---

### Phase 2: 仿真器功能增强

在 Phase 1 编译后的扁平化 state 上，实现：

1. **层级 Peek/Poke**
   ```python
   sim.peek("systolic.pe_3_4.psum_out")  # 层级访问
   sim.poke("decode.dec_opcode", 3)
   sim.get_signal_path("systolic")  # 返回子树所有信号
   ```

2. **Trace Buffer 优化**
   - 当前：每步 snapshot 所有信号 → 内存爆炸
   - 改进：只 trace 指定信号；支持采样间隔；支持 ring buffer（循环覆盖）
   - VCD 导出保持兼容

3. **Memory Dumper**
   ```python
   sim.dump_memory("bank0", start=0, end=64, fmt="hex")
   sim.dump_memory_to_file("sram_dump.hex", "bank0")
   ```

4. **Breakpoints**
   ```python
   sim.add_breakpoint("state == DONE", lambda sim: print(f"Done at cycle {sim.cycle}"))
   sim.add_breakpoint("decode.dec_opcode == 3")  # 条件断点
   sim.run_until_break(max_cycles=10000)
   ```

5. **Fast Reset**
   - 当前：逐步执行 reset 序列
   - 改进：直接初始化 state 列表为 0，跳过 AST 执行

6. **Batch Step**
   ```python
   sim.run(10000)  # 内部用 C 风格循环，减少 Python 调用
   ```

**工作量**: ~2–3 天

---

### Phase 3: C++ 核心引擎（可选，中长期）

如果 Phase 1+2 后仍不足够（如需要 >100K cps 或 >10M cycles），再启动 C++ 引擎。

**架构**:
```
Python (rtlgen AST)
    ↓ 编译器 (Python)
C++ 仿真内核 (libsim.so)
    ├── Flattened module graph
    ├── Compiled update functions
    └── State vector (std::vector<uint64_t>)
    ↓ pybind11
Python API (Simulator 接口保持不变)
```

**C++ 内核职责**:
- 周期精确的 state update
- Memory / Array 管理
- Trace 采集（可选写入共享内存）

**预期额外加速**: 10–50x over Phase 1 JIT
- Phase 1 JIT 预估 8,500–85,000 cps
- C++ 引擎预估 100K–1M cps

**工作量**: ~2–3 周（需要 pybind11、CMake、跨平台构建）

---

## 三、实施建议

**推荐立即启动 Phase 1**，原因：
1. 投资回报率最高：3–5 天工作 → 50–500x 加速
2. 不改变现有 API，所有测试保持兼容
3. 不引入外部依赖（pybind11、CMake 等）
4. 为后续 C++ 引擎提供编译基础设施（AST → 扁平化的流程可复用）

**Phase 1 具体步骤**:
1. 实现 `ModuleElaborator`：递归 flatten 子模块，前缀化信号名
2. 实现 `JITCompiler`：AST → 有序执行列表 → Python lambda
3. 修改 `Simulator`：初始化时自动 compile，step() 走 JIT 路径
4. 保留 fallback：若 JIT 失败，自动回退到 AST 解释
5. 运行全部 104 个测试验证正确性

**风险**: AST 语义与 JIT 行为可能不一致（特别是 If/Switch/ForGen 的嵌套）。Mitigation：
- 保持原始 AST simulator 作为 fallback
- 渐进式启用：先对 BOOM/NPU 测试启用 JIT，通过后再全面推广

---

## 四、决策点

请确认：
1. **是否启动 Phase 1 (JIT Compiler)**？
2. **Phase 2 的功能优先级**？（层级peek/poke > trace优化 > breakpoints > memory dump > fast reset）
3. **是否现在规划 Phase 3 (C++)**，还是等 Phase 1/2 完成后再评估？
