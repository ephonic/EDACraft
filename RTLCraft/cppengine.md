# rtlgen C++ 仿真引擎开发策略

> 本文档记录从 Python JIT 仿真器升级到 C++ 引擎的完整技术路线、架构设计和实施计划。

---

## 1. 背景与动机

### 1.1 当前瓶颈

Python JIT 编译器（`rtlgen/sim_jit.py`）已将 AST 解释开销消除，但受限于 Python 语言本身：

| 操作 | Python | C++ | 差距 |
|------|--------|-----|------|
| 整数加法 + mask | ~36 ns | ~2 ns | 18x |
| list 读+写 | ~43 ns | ~2 ns | 21x |
| 函数调用 | ~36 ns | ~3 ns | 12x |

**实测加速**：NPU 7.0x，BOOM 4.0x。每步仍需调用 ~1000 个 Python lambda。

### 1.2 目标场景

- **单元测试**：Python JIT 已足够（秒级）
- **完整推理**：10M-100M cycles，Python JIT 需 **1-15 小时**，不可接受
- **回归测试**：全量测试需分钟级完成

### 1.3 性能目标

| 指标 | Python JIT | C++ 引擎目标 | 提升 |
|------|-----------|-------------|------|
| NPU 速度 | ~1900 cps | ~50K-200K cps | **25-100x** |
| BOOM 速度 | ~600 cps | ~20K-80K cps | **30-130x** |
| 10M cycles 耗时 | ~1.5 小时 | **< 30 秒** | **> 180x** |

---

## 2. 架构设计

### 2.1 核心原则

> **C++ 只做高速 step()，Python 保留所有调试/观测功能。**

```
┌────────────────────────────────────────────┐
│  Python Layer: Simulator API               │
│  ├── Hierarchical peek/poke                │
│  │     (name → flat_idx → C++ get/set)     │
│  ├── Trace buffer (VCD / table)            │
│  │     (Python collects from C++ per-step   │
│  │      or bulk from C++ internal buffer)   │
│  ├── Breakpoints (Python lambdas)          │
│  ├── Memory dump                           │
│  ├── Reset / Batch run control             │
│  └── Verilog codegen (unchanged)           │
├────────────────────────────────────────────┤
│  pybind11 Bridge: _sim_cpp.so              │
│  ├── class CppSimulator                    │
│  │     step()                               │
│  │     step_batch(n)                        │
│  │     get_signal(idx) → uint64_t           │
│  │     set_signal(idx, val)                 │
│  │     get_memory(mem, addr)                │
│  │     set_memory(mem, addr, val)           │
│  │     get_trace_buffer() → np.ndarray      │
│  │     reset_all()                          │
│  └── Memory ownership: C++ owns, Python views│
├────────────────────────────────────────────┤
│  C++ Kernel                                │
│  ├── Flat state vector (uint64_t[])        │
│  ├── Pre-sorted comb execution array       │
│  │     (function pointers / inline ops)     │
│  ├── Seq commit logic                      │
│  ├── Internal trace ring buffer (optional) │
│  └── Multi-clock support (future)          │
└────────────────────────────────────────────┘
```

### 2.2 为什么保留 Python 上层？

| 功能 | 放 C++ 的问题 | 放 Python 的优势 |
|------|-------------|----------------|
| Hierarchical names | 需要字符串 map，C++ 不擅长 | Python dict 极快 |
| Trace formatting | VCD 字符串生成慢 | Python 字符串处理方便 |
| Breakpoints | Python lambda 无法传 C++ | 灵活，支持任意条件 |
| Memory dump hex | 格式化逻辑繁琐 | Python f-string 简洁 |
| Test assertions | 需重新编译 C++ | Python 动态断言 |

---

## 3. 技术方案

### 3.1 C++ 内核数据结构

```cpp
// sim_kernel.h
#include <cstdint>
#include <vector>
#include <functional>

namespace rtlgen {

using SignalValue = uint64_t;
using CombFn = std::function<void(const SignalValue*, SignalValue*)>;
using SeqFn = std::function<void(const SignalValue*, SignalValue*)>;

struct Memory {
    int width;
    int depth;
    std::vector<SignalValue> data;
};

struct CompiledModule {
    int num_signals;
    int num_seq_signals;  // subset that can be written by seq
    
    std::vector<CombFn> comb_fns;
    std::vector<SeqFn> seq_fns;
    std::vector<Memory> memories;
    
    // Pre-allocated buffers
    std::vector<SignalValue> state;
    std::vector<SignalValue> next_state;
    
    // Optional internal trace
    std::vector<int> trace_signal_indices;
    std::vector<SignalValue> trace_buffer;
    size_t trace_capacity;
    size_t trace_head;
    bool trace_ring;
};

class CppSimulator {
public:
    explicit CppSimulator(const CompiledModule& mod);
    
    void step();
    void step_batch(int n);
    
    SignalValue get_signal(int idx) const;
    void set_signal(int idx, SignalValue val);
    
    SignalValue get_memory(int mem_idx, int addr) const;
    void set_memory(int mem_idx, int addr, SignalValue val);
    
    void reset_all();
    
    // Trace
    void enable_trace(const std::vector<int>& signal_indices, 
                      int max_size, bool ring);
    pybind11::array_t<SignalValue> get_trace_buffer() const;
    void clear_trace();
    
private:
    CompiledModule mod_;
    void eval_comb();
    void eval_seq();
    void commit();
};

} // namespace rtlgen
```

### 3.2 AST → C++ 代码生成

不再生成 Python lambda，而是生成 C++ 源码，编译为 `.so`：

```cpp
// Generated: npu_jit.cpp
#include "sim_kernel.h"

extern "C" void npu_comb_0(const rtlgen::SignalValue* state, rtlgen::SignalValue* out) {
    // decode_dec_valid = instr_valid
    out[28] = state[2] & 0x1;
}

extern "C" void npu_comb_1(const rtlgen::SignalValue* state, rtlgen::SignalValue* out) {
    // busy = (state != 0)
    out[11] = (state[20] != 0) ? 1 : 0;
}

// ... 971 comb functions

extern "C" void npu_seq_0(const rtlgen::SignalValue* state, rtlgen::SignalValue* next) {
    // FSM: if (rst_n == 0) state = 0; else if (state == 0 && instr_valid & dec_valid) state = 1;
    if ((state[1] & 0x1) == 0) {
        next[20] = 0;
    } else if (state[20] == 0 && ((state[2] & state[14]) & 0x1)) {
        next[20] = 1;
    }
}
```

**编译流程**：
```
Python AST
    ↓ code generator (Python)
C++ source (npu_jit.cpp)
    ↓ setuptools / cmake
Compiled .so (npu_jit.so)
    ↓ pybind11 import
Python Simulator with C++ kernel
```

### 3.3 pybind11 绑定

```cpp
// sim_pybind.cpp
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include "sim_kernel.h"

namespace py = pybind11;

PYBIND11_MODULE(_sim_cpp, m) {
    m.doc() = "rtlgen C++ simulation kernel";
    
    py::class_<rtlgen::CppSimulator>(m, "CppSimulator")
        .def(py::init<const rtlgen::CompiledModule&>())
        .def("step", &rtlgen::CppSimulator::step)
        .def("step_batch", &rtlgen::CppSimulator::step_batch)
        .def("get_signal", &rtlgen::CppSimulator::get_signal)
        .def("set_signal", &rtlgen::CppSimulator::set_signal)
        .def("get_memory", &rtlgen::CppSimulator::get_memory)
        .def("set_memory", &rtlgen::CppSimulator::set_memory)
        .def("reset_all", &rtlgen::CppSimulator::reset_all)
        .def("enable_trace", &rtlgen::CppSimulator::enable_trace)
        .def("get_trace_buffer", &rtlgen::CppSimulator::get_trace_buffer)
        .def("clear_trace", &rtlgen::CppSimulator::clear_trace);
}
```

### 3.4 Python 层适配

`rtlgen/sim.py` 中 `Simulator` 类保持不变，内部根据条件选择：

```python
class Simulator:
    def __init__(self, module, ..., backend="auto"):
        # backend: "auto" | "jit" | "ast" | "cpp"
        if backend == "auto":
            if _can_use_cpp(module):
                self._backend = CppBackend(module)
            else:
                try:
                    self._backend = JITBackend(module)
                except:
                    self._backend = ASTBackend(module)
        ...
    
    def step(self):
        self._backend.step()
        self._post_step_sync()
    
    def get(self, name):
        return self._backend.get(name)
```

---

## 4. 三种运行模式

### 4.1 模式 A：单步返回（调试模式）

每步后返回 Python，支持完整调试功能。

```python
sim = Simulator(npu, backend="cpp")
for _ in range(1000):
    sim.step()
    if sim.peek("state") == 3:
        sim.dump_memory("bank0")
        break
```

**性能**：C++ step 快 25-60x，但 Python 层 overhead 仍在。

### 4.2 模式 B：Batch Step（回归测试）

C++ 内部循环 N 步，批量返回。

```python
sim = Simulator(npu, backend="cpp")
sim.step_batch(100000)  # C++ 内部循环，不返 Py

# 之后检查状态
assert sim.peek("done") == 1
```

**性能**：最大化 C++ 速度，适合**长时间推理**。

### 4.3 模式 C：内部 Trace + Batch（观测模式）

C++ 内部收集 trace，批量返回。

```python
sim = Simulator(npu, backend="cpp")
sim.enable_trace(["state", "busy", "done"], max_size=10000)
sim.step_batch(100000)
trace = sim.get_trace_buffer()  # np.ndarray shape=(10000, 3)
```

**性能**：接近纯 C++ 速度，同时保留关键信号观测。

---

## 5. 实施计划

### Phase 1: C++ 内核基础（1 周）

- [ ] 创建 `rtlgen/cpp/` 目录结构
- [ ] 实现 `sim_kernel.h`：State vector, Memory, CompiledModule
- [ ] 实现 `CppSimulator::step()`：comb → seq → commit → comb
- [ ] 实现 `CppSimulator::step_batch()`
- [ ] 实现 `reset_all()`
- [ ] 单元测试：C++ 内核独立测试

### Phase 2: pybind11 桥接（3-4 天）

- [ ] `sim_pybind.cpp`：绑定 `CppSimulator`
- [ ] `CMakeLists.txt` 或 `setuptools` 构建配置
- [ ] 跨平台构建（macOS / Linux）
- [ ] Python 端 `CppBackend` 适配类
- [ ] 测试：Python → C++ → Python round-trip

### Phase 3: AST → C++ 代码生成（3-4 天）

- [ ] 复用现有 `JITModule` 的扁平化逻辑
- [ ] 新增 `CppCodeGen`：AST → C++ 源码
- [ ] 生成 comb/seq 函数数组
- [ ] 编译链集成：生成 `.cpp` → 编译 `.so` → 动态加载
- [ ] 测试：NPU / BOOM 模块编译通过

### Phase 4: Trace / Debug 适配（2-3 天）

- [ ] C++ 内部 trace buffer（ring / linear）
- [ ] `get_trace_buffer()` → `np.ndarray`
- [ ] Python 层 `trace` / `dump_trace()` / `to_vcd()` 兼容
- [ ] Breakpoint checkpoint 机制（batch 中定期返回）

### Phase 5: 集成验证（2-3 天）

- [ ] 全部 146 个测试通过
- [ ] 性能基准：NPU / BOOM / FSMM
- [ ] 与 Python JIT 结果逐周期对比验证
- [ ] 文档更新

**总计：2-2.5 周**

---

## 6. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| pybind11 构建复杂 | 中 | 延迟 | 先用 setuptools + cpp_extension，后期迁移 CMake |
| 跨平台兼容（macOS ARM / Linux x86） | 中 | 构建失败 | CI 矩阵测试；提供 wheel |
| AST → C++ 代码生成 bug | 中 | 仿真错误 | 与 Python JIT 逐周期 diff 验证 |
| X/Z 四态逻辑未实现 | 低 | 部分测试无法迁移 | Phase 1 只支持二态；X/Z 后续添加 |
| 动态编译开销（大模块） | 中 | 首次运行慢 | 缓存 `.so`；复用编译产物 |
| NumPy 依赖 | 低 | 安装复杂 | 仅用于 trace buffer 返回；可选项 |

---

## 7. 替代方案对比

| 方案 | 工作量 | 额外加速 | 维护成本 | 推荐度 |
|------|--------|---------|---------|--------|
| **C++ 引擎**（本方案） | 2-2.5 周 | 25-100x | 中 | ⭐⭐⭐⭐⭐ |
| Numba JIT | 3-5 天 | 5-15x | 低 | ⭐⭐⭐ |
| Cython | 1-2 周 | 10-30x | 中 | ⭐⭐⭐⭐ |
| 保持 Python JIT | 0 | 0 | 低 | ⭐⭐（已达天花板） |

**结论**：C++ 引擎是唯一能将 10M cycles 从小时级降到秒级的方案，且架构清晰（C++ 内核 + Python 外壳），长期收益最大。

---

## 8. 关键决策点

1. **是否现在启动？**
   - 若 NPU 目标包含**完整推理**（>1M cycles）：建议立即启动
   - 若当前只需求**单元测试级仿真**：Python JIT 已够用，可延后

2. **构建系统选择？**
   - 快速原型：`setuptools.Extension` + `pybind11`
   - 长期维护：`CMake` + `scikit-build-core`

3. **X/Z 四态支持？**
   - Phase 1 先实现二态（覆盖 95% 场景）
   - Phase 2 添加 `SimValue {uint64_t v, x, z}`

---

*文档版本: v1.0*
*创建日期: 2026-04-17*
*状态: 待启动*
