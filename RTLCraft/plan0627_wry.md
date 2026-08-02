# plan0627_wry: rtlgen 基础收口专项计划

日期：2026-06-27

## 1. 背景与判断

这份计划承接三条已经形成共识的主线：

1. `plan0611-v2.md` 的方法论：把散落在代码里的事务、协议、检查规则收敛为 registry / schema / checker / report，而不是继续依赖零散 if 分支和经验写法。
2. `plan0626.md` 的当前状态判断：JPEG、backend policy、authoring intent、storage/diagnostics 等主 blocker 已经基本转入维护态，近期不应继续铺大功能面。
3. `plan_stdlib.md` 的下一阶段诉求：在进入更大的 stdlib / VIP / GPGPU 牵引之前，必须继续收口 readable RTL、diagnostics、storage/reset/CDC contract。

因此，本轮不做新的大协议、不做 DDR、不做 AXI4 full，也不做新的 orchestration framework。

本轮只做一件事：

**把 rtlgen 的基础可信度做成一个可执行 gate：readable RTL + unified diagnostics + storage/reset/CDC preflight。**

---

## 2. 一句话目标

建立 `rtlgen` 的 foundation contract gate，使任意 DSL module 在进入 stdlib、worked example、GPGPU seed 或 release 文档前，都可以跑：

```text
DSL Module
  -> readable RTL contract
  -> diagnostics schema normalization
  -> storage/reset/CDC contract preflight
  -> Markdown/JSON report
  -> regression lock
```

---

## 3. 本轮不做什么

本轮明确不做：

1. 不扩 AXI4 full。
2. 不做 DDR PHY / training / JEDEC 细节。
3. 不扩 emitted RTL 的任意 multi-port memory / macro mapping。
4. 不做自动 rewrite DSL。
5. 不引入新的重型 control plane。
6. 不把 `archsim` 变成 DSL 自动生成入口。
7. 不把所有已有 partial stdlib 一次性升级为 stable。

这些方向仍然有价值，但不属于 `plan0627_wry`。

---

## 4. 成功标准

本计划完成时，应满足下面条件：

1. `rtlgen` 有一份明确的 readable RTL contract 文档。
2. `EmitProfile.review()` 生成的代表性 RTL 可以被 readability gate 检查。
3. readability / CDC / storage / lowering / authoring intent finding 可以统一投影为同一类 diagnostic report。
4. `analyze_foundation_contract(...)` 或同等入口可以一次性给出模块基础体检结果。
5. 至少 5 个代表模块有 regression：
   - `SkidBuffer`
   - `ReadyValidFIFO`
   - `RegisterFile`
   - `APBRegisterBank`
   - `AXI4LiteRegisterBank` 或 `WishboneRegisterBank`
6. 文档和 support matrix 更新，明确哪些能力是 stable、partial、deliberate fail-fast。
7. 失败报告足够“带路”：能给 rule、source、object、suggested fix、evidence。

---

## 5. 建议代码触点

优先触碰这些文件：

1. `rtlgen/dsl/readability.py`
2. `rtlgen/dsl/codegen.py`
3. `rtlgen/dsl/core.py`
4. `rtlgen/dsl/adapter.py`
5. `rtlgen/verify/cdc.py`
6. `rtlgen/verify/__init__.py`
7. 新增 `rtlgen/diagnostics.py`
8. 新增 `rtlgen/verify/foundation.py`
9. 新增 `rtlgen/RTL_READABILITY_CONTRACT.md`
10. `rtlgen/DSL_SUPPORT_MATRIX.md`
11. `rtlgen/DSL_SEMANTICS.md`
12. `rtlgen/STDLIB_SUPPORT_MATRIX.md`
13. `rtlgen/tests/test_readability_contract.py`
14. `rtlgen/tests/test_foundation_contract.py`
15. `rtlgen/tests/test_dsl_docs.py`

注意：如果实现时发现 `rtlgen/diagnostics.py` 过于顶层，也可以放到 `rtlgen/verify/diagnostics.py`。但建议顶层放置，因为 readability、CDC、PPA、verify、DSL lowering 都会复用。

---

## 6. Workstream A: Readable RTL Contract

### A1. 写 contract 文档

新增：

```text
rtlgen/RTL_READABILITY_CONTRACT.md
```

文档至少包含：

1. review RTL 的定义。
2. review/default/compact 三类 profile 的区别。
3. 必须满足的结构要求：
   - module header 清晰
   - port table 可读
   - always block 有稳定分组
   - memory/init/clock/reset 语义不被隐藏
   - 关键注释不污染主阅读面
4. 反模式：
   - `_tmp17` / `_cse42` 泄漏到 review RTL
   - 超长单行表达式
   - 深层 ternary 链
   - duplicated marker
   - source-map 注释淹没 RTL 主体
5. gate 的边界：
   - readability gate 不证明功能正确
   - readability gate 不替代 Verilator/VCS
   - compact profile 可以放宽部分限制

### A2. 扩展 readability report

当前 `rtlgen/dsl/readability.py` 已有：

1. long line
2. anonymous helper
3. duplicated block prefix
4. deep mux assign
5. marker sequence

本轮补充：

1. `missing_module_header`
2. `missing_port_table`
3. `unlabeled_always_block`
4. `unstable_generated_name`
5. `source_map_noise`
6. `memory_block_not_grouped`
7. `clock_reset_not_visible`

建议数据结构扩展：

```python
@dataclass(frozen=True)
class ReadabilityReport:
    profile: str
    line_count: int
    max_line_length: int
    long_line_count: int
    anonymous_helper_count: int
    duplicated_block_prefix_count: int
    deep_mux_assign_count: int
    missing_header_count: int = 0
    missing_port_table_count: int = 0
    unlabeled_always_block_count: int = 0
    unstable_generated_name_count: int = 0
    source_map_noise_count: int = 0
    findings: tuple[ReadabilityFinding, ...] = ()
```

保持兼容：已有字段不要改名，新增字段给默认值。

### A3. 明确 review profile 的最小 emit contract

核对 `rtlgen/dsl/codegen.py` 中 `EmitProfile.review()`。

本轮只要求：

1. review profile 默认开启 readable markers。
2. review profile 默认避免匿名 helper 名称泄漏。
3. review profile 默认保留端口表/模块头信息。
4. compact profile 不强制端口表/长注释。

不要在本轮大改 emitter 架构。如果遇到某个模块难以满足 readability gate，优先先把 finding 写清楚，必要时将该规则标成 warning。

### A4. 新增 readable RTL regression

新增：

```text
rtlgen/tests/test_readability_contract.py
```

覆盖：

1. `SkidBuffer(width=8)`
2. `ReadyValidFIFO(width=8, depth=2)`
3. `RegisterFile(width=32, depth=8)`
4. 一个含 reset 的 accumulator 小模块
5. 一个含 memory init 的 LUT/RAM 小模块

测试内容：

1. `assert_emitted_rtl_contract(module)` 通过。
2. 人造坏 RTL 能报 `long_line`。
3. 人造坏 RTL 能报 `anonymous_helper`。
4. 人造坏 RTL 能报 `missing_module_header`。
5. marker 顺序错误时 report 能指出缺失或乱序。

### A5. A 阶段验收

运行：

```bash
python -m pytest -q rtlgen/tests/test_readability_contract.py
python -m pytest -q rtlgen/tests/test_stdlib_catalog.py
```

通过标准：

1. readable RTL gate 能独立跑。
2. 失败输出是 markdown report。
3. 代表模块不因格式漂移产生不稳定失败。

---

## 7. Workstream B: Unified Diagnostics Schema

### B1. 新增统一 finding 类型

新增：

```text
rtlgen/diagnostics.py
```

建议 dataclass：

```python
@dataclass(frozen=True)
class DiagnosticFinding:
    rule: str
    severity: str
    category: str
    message: str
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    obj: str = ""
    suggested_fix: str = ""
    evidence: Mapping[str, object] = field(default_factory=dict)
```

同时提供：

```python
@dataclass(frozen=True)
class DiagnosticReport:
    name: str
    passed: bool
    findings: tuple[DiagnosticFinding, ...]
```

辅助函数：

1. `emit_diagnostic_report_markdown(report)`
2. `diagnostic_report_to_json(report)`
3. `merge_diagnostic_reports(name, reports)`
4. `severity_rank(severity)`

severity 初期只支持：

1. `info`
2. `warning`
3. `error`

### B2. 适配已有 finding

新增 adapter，不强行重写旧模块：

1. `diagnostic_from_readability_finding(...)`
2. `diagnostic_from_cdc_finding(...)`
3. `diagnostic_from_exception(...)`
4. `diagnostics_from_readability_report(...)`
5. `diagnostics_from_cdc_report(...)`

映射规则：

| Source | rule | category |
| --- | --- | --- |
| readability long line | `ReadableRtlLongLine` | `readability` |
| readability anonymous helper | `ReadableRtlAnonymousHelper` | `readability` |
| CDC reset release | `CdcResetReleaseCrossing` | `cdc` |
| CDC data crossing | `CdcUnsafeCrossing` | `cdc` |
| storage fail-fast | `UnsupportedStorageContract` | `storage` |
| unknown submodule port | `UnknownSubmodulePort` | `authoring` |
| untracked signal/storage | `UntrackedDesignObject` | `authoring` |

### B3. 不破坏现有文本 schema

当前 `format_diagnostic(...)` 已经输出类似：

```text
[RuleName] severity=... source=... object=... suggested_fix=...
```

本轮不要删它。做法是：

1. 保留 `format_diagnostic(...)`。
2. 新 report 使用结构化 dataclass。
3. 需要文本时再 render 成与旧 schema 兼容的字符串。

### B4. 新增 diagnostics regression

新增或扩展：

```text
rtlgen/tests/test_foundation_contract.py
```

测试：

1. readability finding 能转成 `DiagnosticFinding`。
2. CDC finding 能转成 `DiagnosticFinding`，保留 src/dst source location。
3. storage exception 能转成 `DiagnosticFinding`。
4. markdown 包含 rule、source、object、suggested fix。
5. JSON 可以稳定 round-trip。

### B5. B 阶段验收

运行：

```bash
python -m pytest -q rtlgen/tests/test_foundation_contract.py -k diagnostics
python -m pytest -q rtlgen/tests/test_cdc.py
python -m pytest -q rtlgen/tests/test_dsl_import.py -k "Untracked or UnknownSubmodulePort or storage"
```

通过标准：

1. 旧测试不因 schema 新增而破坏。
2. 新 diagnostics report 可供后续 foundation gate 复用。

---

## 8. Workstream C: Storage / Reset / CDC Foundation Preflight

### C1. 新增 foundation analyzer

新增：

```text
rtlgen/verify/foundation.py
```

建议公开 API：

```python
def analyze_foundation_contract(
    module: Any,
    *,
    profile: EmitProfile | None = None,
    run_readability: bool = True,
    run_cdc: bool = True,
    run_storage: bool = True,
    strict: bool = False,
) -> FoundationContractReport:
    ...
```

数据结构：

```python
@dataclass(frozen=True)
class FoundationContractReport:
    module_name: str
    passed: bool
    readability: Optional[ReadabilityReport]
    cdc: Optional[CdcReport]
    diagnostics: DiagnosticReport
    summary: Mapping[str, object]
```

### C2. Foundation gate 的 v1 规则

v1 不做复杂证明，只做基础工程 gate。

#### Readability

调用：

```python
analyze_emitted_readability(module, profile=EmitProfile.review())
```

默认：

1. `long_line` 是 warning。
2. `anonymous_helper` 是 warning。
3. `missing_module_header` 是 warning。
4. marker 失败可配置为 error。

#### CDC / reset

调用：

```python
analyze_cdc(module)
```

规则：

1. `reset_release_crossing` 默认 warning。
2. raw async reset release 对 stdlib promotion 应视为 blocker。
3. cross-domain reuse of synchronized reset 默认 error。
4. unsafe data crossing 默认 error。
5. safe primitives 不报。

#### Storage

v1 不新增 storage backend 能力，只做 contract detection：

1. 先尝试 `lower_dsl_module_to_sim(module)`。
2. 再尝试 `VerilogEmitter(profile=EmitProfile.review()).emit(module)`。
3. 捕获 `DslLoweringError` / `ValueError` / storage contract 异常。
4. 转换成 `UnsupportedStorageContract` diagnostic。

分类：

| Case | v1 action |
| --- | --- |
| async 1R/1W read latency 0 | pass |
| byte-enable storage supported subset | pass |
| sync-read read_latency=1 executable | pass with emitted RTL warning if emit unsupported |
| multi-port memory | deliberate fail-fast |
| arbitrary latency | deliberate fail-fast |
| macro mapping | unsupported/future |

### C3. 代表模块 preflight

新增测试覆盖这些模块：

1. `APBRegisterBank(depth=8)`
   - 预期：readability pass；CDC 有 reset-release warning。
2. `AXI4LiteRegisterBank(depth=8)`
   - 预期：foundation clean 或仅 info。
3. `WishboneRegisterBank(depth=8)`
   - 预期：foundation clean 或仅 info。
4. `ReadyValidFIFO(width=8, depth=2)`
   - 预期：readability pass；storage contract pass。
5. `AsyncFIFO(width=8, depth=4)`
   - 预期：CDC primitive clean。

### C4. 输出 Markdown / JSON

新增：

```python
emit_foundation_contract_markdown(report)
foundation_contract_report_to_json(report)
```

Markdown 结构：

```text
# Foundation Contract Report: <module>

- passed
- diagnostics: errors / warnings / info
- readability summary
- CDC summary
- storage summary

## Findings

- [rule] severity=... category=... source=... object=...
  message
  suggested_fix
  evidence
```

### C5. C 阶段验收

运行：

```bash
python -m pytest -q rtlgen/tests/test_foundation_contract.py
python -m pytest -q rtlgen/tests/test_cdc.py
python -m pytest -q rtlgen/tests/test_verify_uvm.py -k "RegisterBank or storage"
```

通过标准：

1. foundation report 可以覆盖 clean、warning、error 三种模块。
2. report 不吞掉 source mapping。
3. deliberate fail-fast 的 storage case 报告明确，不表现为未知 crash。

---

## 9. Workstream D: 文档与矩阵同步

### D1. 更新 DSL support matrix

更新：

```text
rtlgen/DSL_SUPPORT_MATRIX.md
```

新增或更新条目：

1. Readable RTL gate
2. Unified diagnostics report
3. Foundation contract preflight
4. Storage emitted RTL fail-fast boundary
5. Reset-release CDC preflight

状态建议：

| Capability | Status |
| --- | --- |
| Readable RTL analysis | `partial` |
| Review-profile readability gate | `partial` |
| Unified diagnostics schema | `partial` |
| Foundation contract preflight | `experimental` -> `partial` |
| CDC/reset-release preflight | `partial` |
| Storage emitted RTL expansion | `partial`, deliberate fail-fast |

### D2. 更新 DSL semantics

更新：

```text
rtlgen/DSL_SEMANTICS.md
```

加入章节：

1. Foundation contract gate
2. Diagnostic report contract
3. Readable RTL contract
4. Storage/reset/CDC preflight boundary

### D3. 更新 stdlib support matrix

更新：

```text
rtlgen/STDLIB_SUPPORT_MATRIX.md
```

为组件增加 note：

1. 是否通过 foundation preflight。
2. 是否仍有 reset-release warning。
3. 是否仍依赖 deliberate storage boundary。

不要假装全部 stable。能通过 preflight 但外部 UVM closure 仍 partial 的，仍标 partial。

### D4. 更新 README

更新：

```text
rtlgen/README.md
```

新增小节：

```text
Foundation Contract Gate
```

给出示例：

```python
from rtlgen.verify import analyze_foundation_contract, emit_foundation_contract_markdown

report = analyze_foundation_contract(module)
print(emit_foundation_contract_markdown(report))
```

### D5. D 阶段验收

运行：

```bash
python -m pytest -q rtlgen/tests/test_dsl_docs.py
python -m pytest -q rtlgen/tests/test_stdlib_catalog.py
```

通过标准：

1. README 链接新文档。
2. support matrix 与 catalog 不冲突。
3. 文档描述不宣称未完成能力已经 stable。

---

## 10. 执行排期

### Day 1: Readable RTL gate

1. 写 `RTL_READABILITY_CONTRACT.md`。
2. 扩展 `readability.py` report 字段和检查项。
3. 新增 `test_readability_contract.py`。
4. 代表模块跑通 review profile。

验收：

```bash
python -m pytest -q rtlgen/tests/test_readability_contract.py
```

### Day 2: Diagnostics schema

1. 新增 `rtlgen/diagnostics.py`。
2. 实现 markdown/json render。
3. 实现 readability / CDC adapter。
4. 新增 diagnostics tests。

验收：

```bash
python -m pytest -q rtlgen/tests/test_foundation_contract.py -k diagnostics
python -m pytest -q rtlgen/tests/test_cdc.py
```

### Day 3: Foundation preflight

1. 新增 `rtlgen/verify/foundation.py`。
2. 整合 readability + CDC + storage/lowering/emit preflight。
3. 输出 markdown/json。
4. 跑代表模块。

验收：

```bash
python -m pytest -q rtlgen/tests/test_foundation_contract.py
```

### Day 4: Docs/matrix

1. 更新 README。
2. 更新 DSL support matrix。
3. 更新 DSL semantics。
4. 更新 stdlib support matrix。
5. 补 docs tests。

验收：

```bash
python -m pytest -q rtlgen/tests/test_dsl_docs.py
python -m pytest -q rtlgen/tests/test_stdlib_catalog.py
```

### Day 5: Stabilization

1. 跑相关回归集合。
2. 修 report 文案。
3. 确认 warning/error 分级。
4. 确认不会把 deliberate fail-fast 误写成 bug。

建议回归：

```bash
python -m pytest -q rtlgen/tests/test_readability_contract.py
python -m pytest -q rtlgen/tests/test_foundation_contract.py
python -m pytest -q rtlgen/tests/test_cdc.py
python -m pytest -q rtlgen/tests/test_verify_uvm.py
python -m pytest -q rtlgen/tests/test_dsl_import.py
python -m pytest -q rtlgen/tests/test_stdlib_catalog.py
```

---

## 11. 风险与处理

### 风险 1: readability gate 太严格导致大量现有模块失败

处理：

1. v1 默认 warning，不默认 error。
2. 只对代表模块建立 hard gate。
3. 规则分为 `required` 和 `advisory`。

### 风险 2: diagnostics schema 诱发大规模重构

处理：

1. 不重写已有 finding。
2. 先做 adapter。
3. 旧文本 schema 保留。

### 风险 3: storage contract 被误解为要扩 backend

处理：

1. v1 只做 preflight 和报告。
2. 不实现 multi-port/macro mapping。
3. support matrix 明确 deliberate fail-fast。

### 风险 4: CDC checker 被期待为 formal proof

处理：

1. 文档明确 CDC 是 report-oriented。
2. 只识别常见 unsafe/safe pattern。
3. 对复杂协议 crossing 给 warning 和 recommended primitive。

### 风险 5: foundation gate 和 stdlib catalog 口径冲突

处理：

1. catalog status 不自动升级。
2. foundation clean 只表示基础 gate 通过。
3. stable 仍要求 lowering/sim/emit/verify/docs/regression 全闭环。

---

## 12. 最小可交付版本

如果时间只够 2 天，最小交付为：

1. `RTL_READABILITY_CONTRACT.md`
2. `test_readability_contract.py`
3. `rtlgen/diagnostics.py`
4. readability + CDC diagnostic adapter
5. `analyze_foundation_contract(...)` 的最小版本：
   - readability
   - CDC
   - markdown report

storage 可以先只在 report 中列为 planned，但不要写成完成。

---

## 13. 完整交付版本

完整交付为：

1. readable RTL gate 完整可跑。
2. diagnostics schema 支持 markdown/json。
3. foundation preflight 覆盖 readability/CDC/storage。
4. 5 个代表模块 regression。
5. README / DSL support matrix / DSL semantics / stdlib matrix 同步。
6. 相关 tests 全绿。

---

## 14. 本计划完成后的下一步

完成 `plan0627_wry` 后，下一步才适合进入：

1. 从 GPGPU seed 中选择一个真实组件，跑 foundation gate。
2. 将通过 gate 的组件推进 stdlib support matrix。
3. 针对真实 failure 扩展 diagnostics rule。
4. 再考虑 protocol/channel/VIP 的闭环升级。

推荐下一个专项名称：

```text
plan0628_seed_gate
```

目标可以是：

```text
把 gpu_sm / gpgpu_stack 的一个真实 seed flow 接入 foundation gate，并产出 architecture/PPA/RTL/readability/CDC 一体报告。
```

---

## 15. 一句话总结

`plan0627_wry` 的核心不是“再加一个功能”，而是：

**把 rtlgen 已经具备的 readable RTL、diagnostics、storage/reset/CDC 能力收成一个统一、可执行、可报告、可回归的基础 contract gate。**

最后, 将本轮做的贡献写到C:\Users\F先生\fudan-work\contribution里面, 写成md文件。