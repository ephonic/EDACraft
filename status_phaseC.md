# Phase C 完成状态 — PDK 桥接 + 参数化增强（需求 2、5）

日期：2026-07-17。承接 Phase A+B（需求 6、7、1、3）。

## TL;DR

| 维度 | 状态 |
| --- | --- |
| 默认全量回归 | **164 tests, 139 PASSED / 0 FAILED / 51 SKIPPED**（C2 后 136 + C1 新增 3 个 Parser 测试） |
| C2 表达式增强 | 多参函数 + 三元 + 逻辑运算符 + 用户 `.func` + 多遍 `.param` 求值 |
| C1 `.lib`/`.endl` corner | 同文件块定义 + 跨文件 `.lib "path" CORNER` 选择性包含 |
| C1 `level=54` 映射 | **推迟**：需 PDK 端到端验证（数百参数映射 + 与 HSPICE 对比），见下方说明 |

## 落地清单

### 修改文件

| 文件 | 改动 |
| --- | --- |
| `src/parser/expression.{hpp,cpp}` | C2：`EvalContext.multiFuncs`（多参函数）；重写递归下降为 9 级优先级（ternary→\|\|→&&→==!=→<><=>=→+-→*/→unary→^→atom）；多参函数 `agauss/unif/gauss/pow/min/max/atan2/if`；条件 `?:` + 逻辑 `&&\|\|! ==!= <><=>=` |
| `src/model/device_factory.cpp` | C2：`buildResolvedEvalContext()` 多遍迭代求值 Expr 全局参数（修复原只加 Number 类型全局参数、Expr 参数无法被引用的 bug）；`resolveParamValue`/`lookupNumber`/`lookupFirstPositionalNumber` 共用之 |
| `src/parser/parser.cpp` | C1：`parseBodyInto` 与顶层 `parse()` 支持 `.lib NAME...endl NAME` 块记录 + `.lib "path" CORNER` 跨文件块选择；新增 `parseLibSelect`；`libBlocks_`/`libSelectSet_` 成员；块名小写归一 |
| `tests/test_expression.cpp` | C2：新增 5 测试（多参函数/三元/逻辑/PDK 风格/用户 .func） |
| `tests/test_parser.cpp` | C1：新增 3 测试（同文件块忽略/跨文件 TT corner/跨文件 SS corner） |

## 关键设计决策

### C2：表达式引擎全面增强（需求 5）

**原状**：`expression.cpp` 单参函数递归下降，无 `agauss`/`pow`(双参)/`min`/`max`/条件/`.func`；HSPICE PDK 的 `lmin='6.3e-7-dxln_hv18_ms'` 表达式参数无法正确求值（device_factory 只把 Number 类型全局参数加入 EvalContext）。

**增强**：
- **多参函数**：`EvalContext.multiFuncs`（`std::function<double(const std::vector<double>&)>`），优先于单参 `funcs`。预置 `agauss/unif/gauss`（确定性求值取名义值，MC 均值）、`pow(b,e)`、`min/max`（变参）、`atan2`、`if(cond,a,b)`。
- **条件 + 逻辑**：9 级优先级文法。`cond ? a : b`（右结合）、`&& || ! == != < > <= >=`（结果 1.0/0.0）。
- **用户 `.func`**：调用方可向 `EvalContext.multiFuncs` 注册自定义函数（`.func name(args) body` 解析后注入）。
- **多遍 `.param` 求值**：`buildResolvedEvalContext` 迭代求值 Expr 类型全局参数直到不动点（顺序无关的前向引用），修复 Expr 参数无法被引用的 bug。

### C1：`.lib`/`.endl` corner 块选择（需求 2 桥接基础）

**原状**：`parseInclude` 把 `.lib` 当 `.include` 用——丢弃 corner 名，包含整个文件。PDK 的 `.lib TOP_TT ... .endl TOP_TT` 块语义和 `.lib './path.l' TTMacro` 选择性包含无法工作。

**增强**：
- **同文件块定义**：`.lib NAME ... .endl NAME` 记录到 `libBlocks_[NAME]`（块名小写归一）。未选择的块内容不展开。
- **跨文件块选择**：`.lib "path" CORNER` → `parseLibSelect` 加载 path 文件，把 CORNER 注入子解析器 `libSelectSet_`，子解析器第三遍展开该块。PDK 嵌套 `.lib`（`TOP_TT → .lib './x.l' TTMacro`）自然递归。
- **顶层 + include 双路径**：`parse()` 与 `parseBodyInto` 都支持块记录（顶层网表和 include 文件均可定义/选择块）。

## C1 `level=54` BSIM4 → OSDI 映射（推迟说明）

PDK 的 `.model nch_hv nmos (level=54 vth0=... u0=... lmin='...' ...)` 使用 HSPICE 原生 BSIM4 level=54 格式，而仿真器只支持 OSDI（Verilog-A → `bsim4.dll`）。桥接需要：

1. **参数名映射表**：HSPICE BSIM4 参数（~300 个）与 Verilog-A bsim4.dll 参数多数同名（`vth0`/`u0`/`vsat`/`tox`...），但 `lmin`/`wmin`/`dxl`/`dxw` 等几何/收缩参数、`scale_mos` 等需特殊处理。
2. **level 识别**：`level=54/14` → 映射到现有 `bsim4.dll`（OSDI）。
3. **端到端验证**：用 `pdk/models/hspice/toplevel.l` + TT corner 跑 CS 放大器，与 HSPICE 结果对比。

**推迟原因**：这是深度集成工作（数百参数逐个核对 + 与 HSPICE 数值对比），需独立 sprint 与充分验证。本轮已完成**桥接的基础设施**（`.lib` corner 选择 + 表达式参数求值），`level=54` 映射表留后续。

## 交付标准核对

- [x] 默认 ctest **139/0/51** PASS（无退步）
- [x] C2 多参函数/三元/逻辑/用户 .func（5 测试）
- [x] C2 多遍 `.param` 求值（Expr 全局参数可被引用）
- [x] C1 `.lib`/`.endl` 同文件块定义 + 跨文件 corner 选择（3 测试）
- [~] C1 `level=54` → OSDI 映射（推迟，需 PDK 端到端验证）

## Phase A+B+C 总结

| Phase | 需求 | 状态 |
| --- | --- | --- |
| A1 求解器抽象+自动选择 | 6 | ✅ |
| A2 HB/Shooting 收敛加固 | 7 | ✅ |
| B1 器件 bypass 强化 | 1 | ✅ |
| B2 multi-rate 增强 | 3 | ✅ |
| C2 表达式/参数化增强 | 5 | ✅ |
| C1 `.lib` corner 选择 | 2 | ✅（基础）；`level=54` 映射推迟 |

回归 **139/0/51**，新增 28 个单元测试（LinearSolverSelect + NonlinearDamping + Expression C2 + Parser C1），无退步。

## 后续

- **Phase D**（需求 4）：波形输出多格式 + 增强 waveview
- **C1 `level=54` 映射表**：独立 sprint（参数映射 + PDK 端到端验证）
- **真正异步 multi-rate 时间网格**（B2 完全版）
