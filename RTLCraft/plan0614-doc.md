# RTLCraft 文档驱动分层设计计划

**Project**: RTLCraft / Smart Earphone SoC  
**Date**: 2026-06-14  
**Version**: 0.1  
**Status**: Proposal / Ready for review  
**Relation**: 本计划是 `plan0614.md`（跨层约束与意图框架）在文档化、可交付物与工程组织方式上的延伸，目标是把 "单文件 Python Spec2RTL" 演进为 "文档驱动的分层 SoC 设计流程"。

---

## 1. 背景与问题

当前 `earphone/design_earphone.py` 是一个近 3200 行的单文件，囊括了：

- 顶层 SpecIR 需求与架构决策
- 各模块（RV32、SIMD、FFT、QSPI、I2C、SRAM、APB Bridge、Top）的行为模型、CycleIR、DSL、Verilog 生成
- 约束定义与跨层传播
- 测试与报告生成

虽然功能完整，但存在以下工业落地障碍：

1. **可维护性差**：单文件难以多人协作、版本控制和代码审查。
2. **设计输入不透明**：SpecIR/BehaviorIR/ArchitectureIR 等层级的决策混在代码里，无法作为下一级设计的清晰输入。
3. **文档缺失/滞后**：缺少与 IR 层级对应的系统设计文档、模块设计文档、测试计划与测试报告。
4. **用户参与困难**：顶层需求由用户给出，但当前流程没有显式地把“不完整输入 → Agent 默认补全 → 用户确认”闭环产品化。
5. **测试不可追溯**：L1/L3/跨层/约束测试分散，缺少逐级传递的测试计划和测试报告。

本计划提出：**以文档为枢纽，把 RTLCraft 从单文件脚本重构为分层、可追溯、可协作的 SoC 设计流程**。

---

## 2. 目标

1. **目录结构分层**：每个 IR 层或每个子系统拥有独立的目录与入口，避免单文件膨胀。
2. **文档与 IR 一一对应**：每一层生成对应的设计文档；上一层文档是下一层的设计输入。
3. **模板化文档**：复用 `doc_templates/` 中的工业界模板（Top-Level Spec、Module Spec、Test Plan、Test Report），必要时扩展寄存器规格、PPA 报告、设计变更单等模板。
4. **用户确认闭环**：用户给出的顶层文档不完整时，Agent 推断默认值，生成草案后由用户确认或修改。
5. **测试逐级传递**：每一层都有测试计划、测试执行、测试报告；顶层测试计划可由用户给出或由 Agent 从 Spec 自动生成。
6. **模块级与系统级测试完整**：单元（模块）测试、集成测试、系统测试、回归测试全覆盖。
7. **与现有约束框架集成**：文档中的需求、约束、决策直接映射到 `rtlgen/contracts.py` 的 `IRConstraint` / `DesignDecision`。

---

## 3. 设计原则

- **单一职责**：一个目录/文件只做一层 IR 或一个子系统的事。
- **输入输出清晰**：每个子目录有明确的 `input/`（来自上一层）和 `output/`（给下一层）。
- **文档即代码**：设计文档使用 Markdown + `{{ placeholder }}` 模板，Agent 可读写、可渲染、可版本控制。
- **最小必要模板**：设计流程中仅在必要时生成额外模板（如寄存器规格、设计变更单），不堆砌文档。
- **可回滚**：每一层的文档和产物都是可追踪的，支持从任意层回滚或重新生成。

---

## 4. 推荐目录结构

```
project_root/
├── README.md                      # 项目入口，指向 Tutorial 和各子系统
├── Tutorial.md                    # 更新后的 Spec2RTL + 文档驱动流程指南
├── plan0614.md                    # 跨层约束框架计划
├── plan0614-doc.md                # 本文档
├── rtlgen/                        # 框架层（不变）
│   ├── contracts.py
│   ├── scaffold.py
│   └── ...
├── doc_templates/                 # 文档模板库（已存在）
│   ├── top_level_spec.md
│   ├── module_spec.md
│   ├── test_plan.md
│   ├── test_report.md
│   └── ...（仅在必要时扩展）
├── tests/                         # 框架级单元测试
│   ├── test_contract_framework.py
│   ├── test_doc_templates.py
│   └── ...
└── projects/                      # 具体 SoC 项目目录（示例：earphone）
    └── earphone/
        ├── README.md              # Earphone 项目入口
        ├── specs/                 # 顶层规格与跨层文档
        │   ├── 00_top_level_spec.md          # 顶层 SoC 规格（用户输入或 Agent 生成）
        │   ├── 01_architecture_spec.md       # ArchitectureIR 输入
        │   ├── 02_behavior_spec.md           # BehaviorIR 输入
        │   ├── 03_cycle_spec.md              # CycleIR 输入
        │   ├── 04_structural_spec.md         # StructuralIR 输入
        │   ├── 05_dsl_spec.md                # DSL 层输入
        │   ├── 06_verification_plan.md       # 顶层验证计划
        │   ├── 07_test_report.md             # 顶层测试报告
        │   ├── 08_constraint_traceability.md # 约束追溯（已存在）
        │   ├── 09_design_issues.md           # 设计问题（已存在）
        │   └── 10_decision_log.md            # 决策日志（已存在）
        ├── subsystem/             # 子系统级目录（可选，复杂 SoC 使用）
        │   └── cpu_subsystem/
        │       ├── specs/
        │       └── src/
        ├── modules/               # 模块级目录
        │   ├── rv32/
        │   │   ├── specs/
        │   │   │   ├── 00_module_spec.md       # Module Spec 模板渲染
        │   │   │   ├── 01_architecture_spec.md # ArchitectureIR 细化
        │   │   │   ├── 02_test_plan.md         # 模块级测试计划
        │   │   │   └── 03_test_report.md       # 模块级测试报告
        │   │   ├── src/
        │   │   │   ├── __init__.py
        │   │   │   ├── behavior.py             # L1 行为模型
        │   │   │   ├── cycle.py                # L2 CycleIR 模型
        │   │   │   ├── arch.py                 # L3 ArchitectureIR
        │   │   │   ├── structure.py            # L4 StructuralIR
        │   │   │   ├── dsl.py                  # L5 DSL 模块
        │   │   │   └── emitter.py              # Verilog 生成
        │   │   └── tests/
        │   │       ├── test_behavior.py
        │   │       ├── test_cycle.py
        │   │       ├── test_dsl.py
        │   │       └── test_verilog.py
        │   ├── simd16/
        │   │   └── ...
        │   ├── fft256/
        │   │   └── ...
        │   └── ...
        ├── integration/           # 集成测试与文档
        │   ├── specs/
        │   │   ├── integration_test_plan.md
        │   │   └── integration_test_report.md
        │   └── tests/
        │       └── test_integration.py
        ├── system/                # 系统级测试与文档
        │   ├── specs/
        │   │   ├── system_test_plan.md
        │   │   └── system_test_report.md
        │   └── tests/
        │       └── test_system.py
        ├── top/                   # SoC Top 级
        │   ├── specs/
        │   │   └── top_level_spec.md
        │   ├── src/
        │   │   └── earphone_top.py
        │   └── tests/
        │       └── test_top.py
        ├── tb/                    # 公共验证平台
        │   ├── cocotb/
        │   ├── uvm/
        │   └── constraints/
        ├── generated/             # 生成的 RTL、文档、报告
        │   ├── rtl/
        │   ├── docs/
        │   └── reports/
        └── flow.py                # Earphone 项目入口脚本（替代 design_earphone.py 单文件）
```

> **说明**：
> - 当前 `earphone/design_earphone.py` 中的模块实现将逐步迁移到 `earphone/modules/<module>/src/` 下。
> - `earphone/flow.py` 负责编排：读取 specs → 驱动各模块实现 → 运行测试 → 生成报告。
> - 每个模块目录下都有 `specs/` 和 `tests/`，确保模块级文档与测试自包含。

---

## 5. 文档层级与输入输出关系

| IR 层级 | 文档名称 | 输入 | 输出 | 负责人 |
|---------|----------|------|------|--------|
| **L0 用户意图** | `00_top_level_spec.md` | 用户提供（可部分） | Architecture/Behavior 高层约束 | 用户 / Agent 补全 |
| **L1 BehaviorIR** | `02_behavior_spec.md` | Top-Level Spec | 参考模型、L1 测试计划 | Agent |
| **L2 CycleIR** | `03_cycle_spec.md` | Behavior Spec | Cycle 模型、协议检查 | Agent |
| **L3 ArchitectureIR** | `01_architecture_spec.md` | Top-Level Spec + Cycle Spec | 微架构、决策记录 | Agent |
| **L4 StructuralIR** | `04_structural_spec.md` | Architecture Spec | 子模块划分、接口契约 | Agent |
| **L5 DSL** | `05_dsl_spec.md` | Structural Spec | DSL 实现说明 | Agent |
| **L6 Verilog** | 生成物 + lint/综合报告 | DSL Spec | RTL、SVA、UVM、cocotb | Agent |
| **测试** | `*_test_plan.md` / `*_test_report.md` | 同级 Spec | 测试结果、覆盖率、问题单 | Agent / 用户确认 |

**关键规则**：

- 上一级 Spec 中的每个需求、约束、决策必须能在下一级找到对应实现或细化。
- 如果下一级无法实现上一级约束，通过 `ConstraintFeedback` / `DesignGate` 向上反馈，更新上一级文档。
- 测试计划继承上一级测试目标，并补充本级特有的 corner cases。

---

## 6. Agent 文档生成与确认流程

### 6.1 顶层 Spec 处理流程

```
用户输入（Top-Level Spec，可能不完整）
        ↓
Agent 解析关键字段：
  - 项目名、模块列表、接口、性能/功耗目标、时钟复位
        ↓
Agent 用 doc_templates/top_level_spec.md 渲染
        ↓
缺失字段由 Agent 推断默认值（基于项目类型/历史项目/通用假设）
        ↓
生成 00_top_level_spec.md（草案）
        ↓
用户审阅：确认 / 修改 / 补充
        ↓
定稿后的 Top-Level Spec 作为 L1/L3 的设计输入
```

**默认推断示例**：

| 缺失字段 | 推断策略 |
|----------|----------|
| 时钟频率 | Earphone 场景默认 160 MHz；可配置 |
| 复位方式 | 异步低电平复位，同步释放 |
| 总线宽度 | 32-bit AHB/APB |
| 功耗目标 | 根据工艺节点和目标应用推断，标记为 "待确认" |
| 模块列表 | 从 Top 模块实例化或用户描述中提取 |

**用户确认机制**：

- Agent 生成带 **TBD / 待确认** 标记的草案。
- 对于高影响字段（功耗预算、安全等级、关键接口协议），Agent 必须显式询问用户。
- 低影响字段可由 Agent 默认填充，用户可在审阅时一次性批准或修改。

### 6.2 模块 Spec 生成流程

```
Top-Level Spec 中关于模块 M 的段落
        ↓
Agent 提取模块级需求、接口、约束
        ↓
用 doc_templates/module_spec.md 渲染模块 Spec
        ↓
补充推断：端口位宽、时序、寄存器、复位值、默认参数
        ↓
生成 earphone/modules/<M>/specs/00_module_spec.md
        ↓
模块级设计输入确定后，进入 L1→L6 实现与验证
```

### 6.3 测试计划生成流程

**顶层测试计划**：

- 若用户提供了测试计划，Agent 解析并渲染到 `doc_templates/test_plan.md`。
- 若未提供，Agent 根据 Top-Level Spec 自动生成：
  - 功能测试目标
  - 性能测试目标
  - 功耗/PPA 测试目标
  - 接口协议测试目标
  - 安全/可靠性测试目标

**模块级测试计划**：

- 继承顶层测试计划中与本模块相关的条目。
- 补充模块特有的 directed tests、random tests、corner cases、assertion checks。

**测试报告**：

- 每级测试执行后，用 `doc_templates/test_report.md` 生成报告。
- 报告包含：通过/失败数、覆盖率、问题单、waivers、签核建议。

---

## 7. 测试策略

### 7.1 测试层级

| 层级 | 对象 | 方法 | 文档 |
|------|------|------|------|
| **L1 行为模型测试** | 各模块 `behavior.py` | Python 单元测试、ISS/功能模型 | `modules/<M>/tests/test_behavior.py` + `modules/<M>/specs/02_test_report.md` |
| **L2 CycleIR 测试** | 各模块 `cycle.py` | 周期精确比对 | `modules/<M>/tests/test_cycle.py` |
| **L3 DSL 测试** | 各模块 `dsl.py` | rtlgen Simulator、跨层等价性 | `modules/<M>/tests/test_dsl.py` |
| **L4 StructuralIR 测试** | 子模块连接、接口 | 静态检查、lint | `modules/<M>/tests/test_structure.py` |
| **L6 Verilog 测试** | 生成 RTL | cocotb、UVM、SVA、形式验证 | `tb/cocotb/`、`tb/uvm/`、`tb/constraints/` |
| **模块集成测试** | 模块间交互 | 集成 testbench | `integration/tests/` + `integration/specs/*_test_report.md` |
| **系统测试** | 完整 SoC | 系统级 scenario、性能/功耗回归 | `system/tests/` + `system/specs/*_test_report.md` |

### 7.2 测试传递规则

- **需求追溯**：每个测试用例必须追溯到上一级 Spec 或约束（通过 UID）。
- **失败处理**：任何层级失败都会生成 `ConstraintFeedback`，触发设计迭代或 Spec 更新。
- **覆盖率闭环**：模块级覆盖率汇总到集成级，再到系统级。

### 7.3 测试报告签核

每份 `*_test_report.md` 包含：

- 执行摘要
- 测试环境
- 结果汇总
- 覆盖率结果
- 问题单与 waivers
- 签核表（Verification Lead、Design Lead、System Architect、PM）

---

## 8. 与现有跨层约束框架的集成

文档驱动流程与 `plan0614.md` 的约束框架是互补的：

- **文档 → 约束**：Spec 中的需求被提取为 `IRConstraint`（owner="human"）。
- **约束 → 文档**：Agent 推导出的子层约束、决策、反馈被写回对应层级的 Spec 和测试计划。
- **反馈 → 文档更新**：`DesignGate` 检测到的 BLOCKER 会触发对应层级 Spec 的更新，并记录到 `design_issues.md`。
- **决策 → 文档**：`DesignDecision` 自动写入 `decision_log.md`，并引用到相关 Spec 的 "Design Decisions" 章节。

---

## 9. 模板扩展策略（仅在必要时）

当前 `doc_templates/` 已包含 4 个核心模板。设计流程中仅在需要时扩展：

| 场景 | 新增模板 |
|------|----------|
| 模块包含可编程寄存器 | `register_spec.md` |
| 需要跟踪设计变更 | `engineering_change_order.md` |
| 需要做 PPA 分析与优化 | `ppa_report.md` |
| 需要安全/功能安全分析 | `safety_analysis.md` |
| 需要软硬件接口约定 | `software_interface_spec.md` |

扩展原则：

- 新增模板必须先在一个真实模块中试用，确认有用后再通用化。
- 模板字段保持与 `IRConstraint` / `DesignDecision` 可映射。

---

## 10. 实施路线图

### Phase 1: 基础设施（1 周）

1. 创建 `projects/earphone/` 分层目录结构。
2. 将 `earphone/design_earphone.py` 按模块拆分到 `earphone/modules/<M>/src/`。
3. 创建 `earphone/flow.py` 作为新入口，调用各模块实现和测试。
4. 更新 `README.md` / `Tutorial.md`，说明新的分层目录和文档驱动流程。
5. 在 `doc_templates/` 中按需扩展 `register_spec.md`（若 Earphone 有需要）。

### Phase 2: 文档自动生成（1 周）

1. 实现 `DocRenderer`：读取模板 + 推断默认值 + 渲染 Markdown。
2. 实现顶层 Spec 解析与确认流程：用户输入 → Agent 补全 → 用户确认。
3. 为 Earphone 生成初始 `00_top_level_spec.md`、`06_verification_plan.md`。
4. 为每个模块生成 `00_module_spec.md` 和 `02_test_plan.md`。

### Phase 3: 测试完整化（1 周）

1. 为每个模块补充 L1/L2/L3/Verilog 测试。
2. 创建集成测试目录与 `integration_test_plan.md`。
3. 创建系统测试目录与 `system_test_plan.md`。
4. 实现测试报告自动生成（使用 `doc_templates/test_report.md`）。
5. 打通覆盖率汇总与签核表。

### Phase 4: 闭环与优化（1 周）

1. 将约束框架反馈自动更新到对应层级 Spec。
2. 实现 Spec 变更传播：修改顶层 Spec 后自动提示受影响模块。
3. 增加回归测试命令与 CI 脚本。
4. 用户验收：用不完整 Top-Level Spec 测试 Agent 的默认补全与确认流程。

---

## 11. 成功标准

1. **目录结构**：`earphone/design_earphone.py` 不再超过 500 行，核心逻辑分散到模块目录。
2. **文档覆盖**：每个模块目录下至少包含 Module Spec、Test Plan、Test Report。
3. **用户闭环**：Agent 能从不完整的 Top-Level Spec 生成可确认的完整草案。
4. **测试完整**：模块测试、集成测试、系统测试全部存在且能自动执行。
5. **可追溯性**：每个测试用例能追溯到 Spec/约束 UID；每个 Spec 变更能追溯到反馈或决策。
6. **无回归**：`tests/` 全部通过，`earphone/flow.py` 执行结果 PASS。

---

## 12. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 拆分单文件导致接口不兼容 | 高 | 保留 `design_earphone.py` 作为兼容入口，逐步迁移 |
| 文档过多增加维护负担 | 中 | 坚持“仅在必要时”扩展模板；使用 Agent 自动生成 |
| 用户确认流程阻塞迭代 | 中 | 高影响字段才强制确认；低影响字段默认填充 |
| 默认值推断不准确 | 中 | 默认值带 "推断" 标记，用户可一键审阅修改 |
| 测试报告与实际情况脱节 | 中 | 报告由测试执行结果自动生成，禁止手工编辑核心数据 |

---

## 13. 下一步行动

待本计划批准后：

1. 创建 `earphone/modules/` 目录结构。
2. 将 `EarphoneRV32` 作为第一个迁移示例，拆分到 `earphone/modules/rv32/`。
3. 为 `EarphoneRV32` 生成 Module Spec、Test Plan、Test Report 初稿。
4. 更新 `Tutorial.md` 中关于分层设计与文档驱动的章节。
5. 运行完整流程，验证无回归。

---

*End of plan.*
