# IC Backend Design Agent Support System — 综合计划

> **定位**：面向集成电路后端设计的**多层次设计知识数据库与 Agent 闭环优化平台**。
> 核心价值不在脚本生成，而在：**数据抽取 → QoR 诊断 → 设计意图建模 → 跨阶段因果分析 → 自动化闭环修复 → 可解释决策**。

---

## 1. 项目概述

### 1.1 目标

构建一个支持数字后端全流程的 Agent 系统，覆盖：

1. 逻辑综合：Design Compiler / Genus / Fusion Compiler
2. 物理实现：ICC2 / Innovus
3. STA sign-off：PrimeTime / Tempus
4. 功耗分析：PrimePower / Joules / Voltus
5. EMIR sign-off：RedHawk / Voltus / PrimeRail
6. 物理验证：Calibre / Pegasus / ICV（DRC / LVS / ERC fixing）
7. 自动化流程封装：Python API 封装不同 EDA 工具体系
8. 设计知识沉淀：RTL、综合、布局、时序、功耗、EMIR、DRC-LVS 统一建模

它应该是 **后端设计 Copilot + 自动诊断专家系统 + 流程优化引擎**，而非命令生成器。

### 1.2 核心设计哲学

| 原则 | 说明 |
|------|------|
| **"硬核"优先** | 每个模块提供真实的分析/求解能力，而非生成Tcl脚本让工具跑 |
| **工具无关抽象** | Agent调用`timing.optimize()`而不需关心底层是DC还是Genus |
| **数据库驱动** | 所有决策基于可查询的设计知识图谱，不依赖零散report |
| **决策可解释** | 所有建议附带量化依据、证据链、spec关联、trade-off数据 |
| **闭环可验证** | 每个action有before/after QoR对比，可回滚 |
| **安全边界** | LLM不直接修改设计，通过受控Python API + regression checker执行 |
| **增量式分析** | 支持在设计流程早期快速估算，后期精确分析 |

### 1.3 关键原则：LLM 的角色边界

**不要让 LLM 直接修改后端设计。**

LLM/Agent 应负责：
1. 读报告
2. 调用分析器
3. 形成假设
4. 生成可验证 action
5. 调用工具执行
6. 比较前后 QoR
7. 给出解释

真正执行的动作必须通过 **受控 Python API + EDA tool adapter + regression checker** 完成。

---

## 2. 系统架构（六层）

```text
┌──────────────────────────────────────────────────────────────────┐
│ L6: Agent Reasoning / Planning / Decision Layer                  │
│ 任务分解、诊断推理、方案比较、闭环优化、多Agent协作             │
└──────────────────────────────────────────────────────────────────┘
                        │
┌──────────────────────────────────────────────────────────────────┐
│ L5: Domain Analysis Engines                                      │
│ 约束分析、综合QoR、时序根因、floorplan、macro、EMIR、DRC         │
└──────────────────────────────────────────────────────────────────┘
                        │
┌──────────────────────────────────────────────────────────────────┐
│ L4: Multi-level Design Representation Database                   │
│ Spec / Design / Artifact / Metric / Report / KG / Decision       │
└──────────────────────────────────────────────────────────────────┘
                        │
┌──────────────────────────────────────────────────────────────────┐
│ L3: Parsers & Extractors                                         │
│ RTL/SDC/UPF/DEF/SPEF/STA/Power/EMIR/DRC/LVS                      │
└──────────────────────────────────────────────────────────────────┘
                        │
┌──────────────────────────────────────────────────────────────────┐
│ L2: Tool Adapter Layer                                           │
│ DC/Genus/FC/ICC2/Innovus/PT/Tempus/Voltus/Calibre                │
└──────────────────────────────────────────────────────────────────┘
                        │
┌──────────────────────────────────────────────────────────────────┐
│ L1: Flow Execution & Infrastructure Layer                        │
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                 │
│  │ Task Scheduling    │  │ Version Control    │                 │
│  │ - Task Decomposer  │  │ - Design VCS       │                 │
│  │ - DAG Scheduler    │  │ - Flow Script Mgr  │                 │
│  │ - Runtime Estimator│  │ - DB Ref Manager   │                 │
│  │ - Progress Tracker │  │ - Lineage Tracker  │                 │
│  │ - Log Analyzer     │  │ - Git Integration  │                 │
│  │ - Notification     │  │ - Config Manager   │                 │
│  └────────────────────┘  └────────────────────┘                 │
│  Python Flow API / Resource Manager / Checkpoint / Resume        │
└──────────────────────────────────────────────────────────────────┘
```

**数据库是整个系统的核心中枢**（L4），不只是存储层。它让Agent能够回答：
- 为什么这么做？依据是什么？
- 违反了哪个 spec？影响了哪个指标？
- 和上一版相比是否真的更好？
- 这个 ECO 是否安全？
- 这个 floorplan 决策是否可复用？

---

## 3. 核心设计对象模型

### 3.1 Design Object Hierarchy

```python
Design
 ├── Modules
 ├── Instances
 │    ├── StandardCells
 │    ├── Macros
 │    └── Memories
 ├── Nets
 ├── Clocks
 ├── Constraints
 ├── TimingPaths
 ├── PhysicalRegions
 ├── PowerDomains
 ├── VoltageAreas
 ├── IRDropHotspots
 ├── EMViolations
 ├── DRCViolations
 └── LVSReports
```

### 3.2 跨阶段关联（系统的灵魂）

```text
RTL signal
  → synthesized net/cell
  → placed instance
  → routed net
  → SPEF RC
  → STA path
  → power activity
  → EMIR region
  → DRC/LVS violation
```

**关键示例**：一个 setup violation 不应只看到 `U1/Q → U2/D, slack = -120ps`，而要能追溯到：

```text
RTL module: dma_scheduler
逻辑功能: arbitration critical path
综合策略: high-effort area recovery 后产生大 fanout mux
物理位置: source 和 sink 跨越 macro channel
RC 特征: 70% delay 来自 net delay
拥塞: M3/M4 utilization > 85%
修复建议: floorplan partition / pipeline / register duplication / macro move / useful skew
```

---

## 4. 多层次设计表征数据库（核心基础设施）

### 4.1 数据库目标

支持四类核心问题：

**A. 设计意图追踪**
```text
这个模块为什么需要 1GHz？
这个 latency 约束来自哪个 spec？
这个 SRAM banking 方案是哪个架构决策导致的？
这个 pipeline 是为了修哪个 timing path？
```

**B. 多层次对象映射**
```text
Spec requirement
  → architecture block
  → RTL module
  → synthesized hierarchy
  → physical region
  → timing path
  → power hotspot
  → EMIR hotspot
  → ECO action
```

**C. 设计版本比较**
```text
run_023 相比 run_018：
- WNS 改善 120ps
- area 增加 3.5%
- dynamic power 增加 1.8%
- IR drop 变差 12mV
- DRC violation 减少 43 个
- 主要变化来自 macro placement v4 和 SDC update v7
```

**D. Agent 可查询证据**
```text
根据 spec.section.3.2
根据 synthesis_run_041 的 report_timing
根据 floorplan_v5 的 macro placement
根据 PT signoff report
根据 EMIR report cluster #12
```

### 4.2 数据库总体结构

```text
┌──────────────────────────────────────────────────────────┐
│ Design Knowledge Layer                                    │
│ Spec / Intent / Decision / ECO / Human Notes             │
└──────────────────────────────────────────────────────────┘
                        │
┌──────────────────────────────────────────────────────────┐
│ Design Object Graph                                      │
│ Module / Net / Cell / Macro / Path / Region              │
└──────────────────────────────────────────────────────────┘
                        │
┌──────────────────────────────────────────────────────────┐
│ Run & Metric Database                                    │
│ QoR / STA / Power / EMIR / DRC / LVS / Runtime          │
└──────────────────────────────────────────────────────────┘
                        │
┌──────────────────────────────────────────────────────────┐
│ Artifact Store                                           │
│ RTL / Netlist / DEF / SPEF / GDS / Reports               │
└──────────────────────────────────────────────────────────┘
```

**技术组合**：

| 存储 | 用途 |
|------|------|
| **PostgreSQL** | 结构化指标、run metadata、版本、配置、QoR |
| **Graph Database** (Neo4j/Neptune) | 设计对象关系、跨层次映射、路径关系 |
| **Object Storage** (S3/MinIO) | RTL、SDC、UPF、DEF、SPEF、GDS、report、log |
| **Vector Database** | spec、设计文档、历史分析报告、专家经验、工具warning解释 |
| **Parquet / DuckDB** | 大规模 timing path、cell、net、power、DRC violation 表 |

### 4.3 核心数据实体

#### Spec 表征

```python
class SpecItem:
    spec_id: str
    title: str
    description: str
    category: str          # functional_spec, performance_spec, latency_spec, etc.
    priority: str
    source_file: str
    source_section: str
    owner: str
    status: str
    linked_design_objects: list[str]
    linked_metrics: list[str]
```

#### Design Artifact

```python
class DesignArtifact:
    artifact_id: str
    design_id: str
    artifact_type: str     # rtl, sdc, upf, lib, lef, def, netlist, spef, gds, ...
    file_path: str
    git_repo: str
    git_commit: str
    checksum: str
    version_tag: str
    created_by: str
    created_at: str
    tool_stage: str
    parent_artifacts: list[str]
```

#### Design Object

```python
class DesignObject:
    object_id: str
    object_type: str       # architecture_block, rtl_module, synth_module, standard_cell, macro, ...
    name: str
    hierarchy_path: str
    design_stage: str
    source_artifact: str
    parent_object: str
    attributes: dict
```

#### Metric

```python
class Metric:
    metric_id: str
    design_id: str
    run_id: str
    object_id: str
    metric_type: str
    value: float | str
    unit: str
    corner: str
    mode: str
    stage: str
    source_report: str
```

#### Report

```python
class Report:
    report_id: str
    run_id: str
    report_type: str       # report_qor, report_timing, report_power, report_emir, ...
    tool: str
    stage: str
    file_path: str
    parser_version: str
    summary: dict
    extracted_tables: list[str]
    linked_objects: list[str]
```

#### Design Run

```python
class DesignRun:
    run_id: str
    design_id: str
    parent_run_id: str
    stage: str
    tool_chain: str
    tool_versions: dict
    input_artifacts: list[str]
    output_artifacts: list[str]
    config: dict
    status: str
    start_time: str
    end_time: str
    owner: str
    agent_version: str
    decision_context: str
```

#### Design Decision

```python
class DesignDecision:
    decision_id: str
    design_id: str
    title: str
    decision_type: str     # constraint_decision, synthesis_strategy_decision, floorplan_partition_decision, ...
    alternatives: list[dict]
    selected_option: dict
    rationale: str
    evidence: list[str]
    expected_impact: dict
    actual_impact: dict
    owner: str
    status: str
```

### 4.4 多层次关联关系（核心"边"）

```text
SpecItem ─requires→ Metric
SpecItem ─implemented_by→ RTLModule
RTLModule ─synthesized_to→ SynthModule
SynthModule ─placed_in→ PhysicalRegion
TimingPath ─passes_through→ Instance
TimingPath ─related_to→ SpecItem
Macro ─connected_to→ Macro
Macro ─belongs_to→ FloorplanGroup
IRHotspot ─overlaps→ PhysicalRegion
DRCViolation ─overlaps→ Net / Shape / Macro
ECOAction ─fixes→ TimingPath / DRCViolation / IRHotspot
Run ─uses→ Artifact
Run ─generates→ Report
Run ─produces→ Metric
```

**典型链路示例**：
```text
SPEC_LAT_001: dma latency <= 16 cycles
  → RTL module: dma_pipeline
  → synthesized cells: U_dma_pipeline/*
  → timing path cluster: TP_CLUSTER_017
  → floorplan region: REGION_LEFT_MID
  → post-place violation: WNS -0.18ns
  → ECO action: insert pipeline stage
  → updated spec impact: latency +1 cycle, still <=16
```

### 4.5 最小可用 Schema（MVP 优先实现）

```sql
CREATE TABLE design (
    design_id TEXT PRIMARY KEY,
    name TEXT,
    project TEXT,
    process_node TEXT,
    top_module TEXT,
    description TEXT
);

CREATE TABLE spec_item (
    spec_id TEXT PRIMARY KEY,
    design_id TEXT,
    title TEXT,
    category TEXT,
    description TEXT,
    target_value TEXT,
    unit TEXT,
    priority TEXT,
    source_artifact_id TEXT,
    status TEXT
);

CREATE TABLE design_artifact (
    artifact_id TEXT PRIMARY KEY,
    design_id TEXT,
    artifact_type TEXT,
    file_path TEXT,
    git_repo TEXT,
    git_commit TEXT,
    checksum TEXT,
    version_tag TEXT,
    tool_stage TEXT,
    created_at TIMESTAMP
);

CREATE TABLE design_run (
    run_id TEXT PRIMARY KEY,
    design_id TEXT,
    parent_run_id TEXT,
    stage TEXT,
    tool_chain TEXT,
    tool_versions JSONB,
    config JSONB,
    status TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP
);

CREATE TABLE metric (
    metric_id TEXT PRIMARY KEY,
    design_id TEXT,
    run_id TEXT,
    object_id TEXT,
    metric_type TEXT,
    value TEXT,
    numeric_value DOUBLE PRECISION,
    unit TEXT,
    mode TEXT,
    corner TEXT,
    stage TEXT,
    source_report_id TEXT
);

CREATE TABLE report (
    report_id TEXT PRIMARY KEY,
    design_id TEXT,
    run_id TEXT,
    report_type TEXT,
    tool TEXT,
    stage TEXT,
    file_path TEXT,
    parser_version TEXT,
    summary JSONB
);

CREATE TABLE design_object (
    object_id TEXT PRIMARY KEY,
    design_id TEXT,
    object_type TEXT,
    name TEXT,
    hierarchy_path TEXT,
    stage TEXT,
    source_artifact_id TEXT,
    attributes JSONB
);

CREATE TABLE object_relation (
    relation_id TEXT PRIMARY KEY,
    design_id TEXT,
    src_object_id TEXT,
    relation_type TEXT,
    dst_object_id TEXT,
    confidence DOUBLE PRECISION,
    evidence JSONB
);

CREATE TABLE timing_path_cluster (
    cluster_id TEXT PRIMARY KEY,
    design_id TEXT,
    run_id TEXT,
    module TEXT,
    path_type TEXT,
    wns DOUBLE PRECISION,
    tns DOUBLE PRECISION,
    path_count INTEGER,
    cell_delay_ratio DOUBLE PRECISION,
    net_delay_ratio DOUBLE PRECISION,
    root_cause TEXT,
    recommendation TEXT
);

CREATE TABLE design_decision (
    decision_id TEXT PRIMARY KEY,
    design_id TEXT,
    run_id TEXT,
    decision_type TEXT,
    title TEXT,
    alternatives JSONB,
    selected_option JSONB,
    rationale TEXT,
    evidence JSONB,
    expected_impact JSONB,
    actual_impact JSONB,
    status TEXT
);
```

### 4.6 Database Python API

```python
class DesignDB:
    def register_spec(self, spec_file: str) -> list[SpecItem]:
        pass

    def register_artifact(self, artifact: DesignArtifact) -> str:
        pass

    def create_run(self, run: DesignRun) -> str:
        pass

    def add_metric(self, metric: Metric):
        pass

    def add_report(self, report: Report):
        pass

    def link_objects(self, src_id: str, relation: str, dst_id: str):
        pass

    def query_design_context(self, object_id: str) -> DesignContext:
        pass

    def compare_runs(self, run_a: str, run_b: str) -> RunDiff:
        pass

    def trace_requirement(self, spec_id: str) -> RequirementTrace:
        pass

    def trace_violation(self, violation_id: str) -> ViolationTrace:
        pass

    def record_decision(self, decision: DesignDecision):
        pass

    # Semantic query
    def query(self, natural_language_query: str) -> QueryResult:
        pass

    def get_timing_clusters(
        self, run_id: str, module: str = None, min_tns_ratio: float = 0.0
    ) -> list[TimingPathCluster]:
        pass

    def get_spec_margin(self, metric: str, object: str) -> SpecMargin:
        pass

    def get_physical_context(self, timing_path_id: str) -> PhysicalContext:
        pass
```

---

## 5. 工具适配与流程编排

### 5.1 Tool-independent Python Flow API

```python
class BackendFlow:
    def synthesize(self, config: SynthesisConfig) -> SynthesisResult:
        pass

    def analyze_synthesis_qor(self, result: SynthesisResult) -> SynthesisDiagnosis:
        pass

    def generate_floorplan(self, config: FloorplanConfig) -> FloorplanResult:
        pass

    def place_macros(self, config: MacroPlacementConfig) -> MacroPlacementResult:
        pass

    def run_place_opt(self, config: PlaceOptConfig) -> PlaceOptResult:
        pass

    def run_cts(self, config: CTSConfig) -> CTSResult:
        pass

    def run_route(self, config: RouteConfig) -> RouteResult:
        pass

    def run_sta(self, config: STAConfig) -> STAResult:
        pass

    def run_power(self, config: PowerConfig) -> PowerResult:
        pass

    def run_emir(self, config: EMIRConfig) -> EMIRResult:
        pass

    def run_drc_lvs(self, config: PVConfig) -> PVResult:
        pass

    def propose_eco(self, diagnosis: Diagnosis) -> ECOPlan:
        pass

    def apply_eco(self, eco: ECOPlan) -> ECOResult:
        pass
```

### 5.2 Tool Adapter

**工具覆盖矩阵**

| 阶段 | Synopsys | Cadence | Siemens/Mentor | 其他 |
|------|----------|---------|----------------|------|
| **综合** | DC, Fusion Compiler | Genus | - | - |
| **PnR** | ICC2 | Innovus | - | - |
| **STA** | PrimeTime | Tempus | - | - |
| **Power** | PrimePower | Joules, Voltus | - | - |
| **Extraction** | StarRC | Quantus | - | - |
| **Formal** | Formality | JasperGold | Questa Formal | - |
| **DFT** | DFT Compiler, TetraMAX | Modus | Tessent | - |
| **EM/IR** | PrimeRail, RedHawk | Voltus | - | Ansys |
| **DRC/LVS** | ICV | Pegasus | Calibre | - |
| **PAD/Bump** | ICC2 pad planning | Innovus pad, SSO | - | - |
| **SI** | StarXtract | SSO Analyzer | - | - |
| **Reliability** | - | - | - | Ansys RedHawk-Rel |
| **Package** | - | - | - | CST, Ansys |

```python
class SynopsysBackendFlow(BackendFlow):
    # DC / Fusion Compiler / ICC2 / PrimeTime / PrimePower / ICV
    # Formality / TetraMAX / StarRC / PrimeRail / RedHawk

class CadenceBackendFlow(BackendFlow):
    # Genus / Innovus / Tempus / Voltus / Pegasus / Quantus
    # JasperGold / Modus / SSO Analyzer

class SiemensBackendFlow(BackendFlow):
    # Calibre (DRC/LVS/ERC) / Tessent (DFT) / Questa Formal

class AnsysAdapter:
    # RedHawk / RedHawk-Reliability / Celsius / HFSS (package)
```

### 5.3 命令执行模型

每条命令必须带：
1. 输入文件
2. 输出报告
3. 期望 QoR
4. 失败检测
5. 回滚策略
6. 前后对比指标

```python
class ToolCommand:
    tool: str
    stage: str
    tcl: str
    expected_outputs: list[str]
    sanity_checks: list[Check]
    rollback_strategy: str
    qor_gates: dict[str, Gate]
```

### 5.4 工具集成模式

```python
# 模式1：命令行调用（最常见）
result = subprocess.run(
    ["dc_shell", "-f", script_file, "-output_log_file", log_file],
    env=tool_env,
)
parsed = DCResultParser(log_file, ddc_file)

# 模式2：Tcl API（需要精细控制时）
tcl_cmd = generate_tcl_command(operation, params)
result = send_to_tcl_server(tcl_cmd)

# 模式3：数据库直接读取（高效，无需工具运行）
ddc = read_ddc_file(path)
```

---

## 6. 模块详细设计

### 6.1 Module 1: 逻辑综合约束/优化策略Trade-off分析

#### 功能描述
分析约束合理性、频率目标可行性、PPA取舍，而非简单生成 `compile_ultra`。

#### 分析器

**A. Constraint Consistency Analyzer**

检查：
1. clock 是否完整
2. generated clock 是否定义
3. clock group 是否合理
4. false path 是否过宽
5. multicycle 是否有 paired setup/hold
6. IO delay 是否与顶层 budget 对齐
7. max_transition / max_cap / max_fanout 是否过松或过紧
8. uncertainty 是否符合阶段：synthesis / placement / CTS / signoff

输出：
```text
constraint_risk_score
missing_clock_list
suspicious_false_path
over_constrained_path
under_constrained_interface
```

**B. Synthesis Strategy Explorer**

对同一 RTL 运行多组综合策略：
```text
baseline / timing_high_effort / area_recovery / power_high_effort
congestion_aware / physical_aware / retiming_enabled
ungroup_aggressive / dont_touch_conservative
```

输出 Pareto 曲线：
```text
WNS / TNS / area / leakage / dynamic / cell count / buffer count
mux depth / fanout / estimated congestion
```

**C. Trade-off Engine**

| 现象 | 可能原因 | 建议 |
|------|----------|------|
| timing好但area暴涨 | over-constraint / excessive buffering | 放松uncertainty / 限制max area / 局部重综合 |
| area好但WNS差 | critical path结构性过长 | RTL改写 / pipeline / datapath restructuring |
| hold buffer激增 | clock uncertainty / skew model不合理 | 区分preCTS/postCTS策略 |
| mux path很深 | arbitration / bus select结构问题 | RTL层重构、one-hot、pipeline |
| fanout大 | control/reset/enable网络 | register duplication / logic replication |
| net delay估计异常 | 物理信息不足 | physical-aware synthesis / early floorplan |

#### Python API

```python
class SynthesisExplorer:
    def __init__(self, design: RTLDesign, lib: LibrarySet, db: DesignDB):
        ...

    def check_constraints(self, sdc: SDCModel) -> ConstraintDiagnosis:
        """约束一致性检查"""
        ...

    def explore_design_space(
        self,
        objectives: list[str],          # ["timing", "area", "power", "congestion"]
        constraints: dict,
        n_samples: int = 100,
    ) -> ParetoFront:
        """返回Pareto最优的约束配置集合"""
        ...

    def sensitivity_analysis(
        self,
        baseline_config: SynthesisConfig,
        parameter: str,
        sweep_range: tuple[float, float],
    ) -> SensitivityCurve:
        ...

    def recommend_constraints(
        self,
        target: dict,
        tool: str = "DC",
    ) -> list[SynthesisConfig]:
        ...

    def tradeoff_report(
        self,
        results: list[SynthesisResult],
    ) -> TradeoffReport:
        """生成结构化trade-off分析报告"""
        ...
```

---

### 6.2 Module 2: 逻辑综合时序修复分析

#### 功能描述
从综合结果判断violation是约束问题、RTL结构问题、工具策略问题、物理不可实现问题，还是需要floorplan/micro-architecture修改。

#### Timing Path Classifier

```python
class TimingPathFeature:
    startpoint_type: str
    endpoint_type: str
    logic_depth: int
    cell_delay_ratio: float
    net_delay_ratio: float
    fanout_max: int
    mux_count: int
    adder_count: int
    multiplier_count: int
    comparator_count: int
    crossing_modules: list[str]
    clock_domain_relation: str
    slack: float
```

#### Path 类型分类

**A. Datapath dominated** (adder tree, multiplier, comparator, barrel shifter, priority encoder)
- 修复：pipeline, datapath restructuring, carry-save, compressor tree, parallel prefix, retiming

**B. Control dominated** (deep if-else, FSM next-state, priority mux, decode network)
- 修复：one-hot, predecode, split FSM, register duplication, reduce priority chain, pipeline control

**C. Physical dominated** (net delay ratio > 50%, cross-module path, macro-to-macro long path)
- 修复：floorplan adjustment, placement constraint, buffer insertion, hierarchy preservation, region constraint

**D. Constraint dominated** (unrealistic IO delay, missing generated clock, wrong clock group, unpaired multicycle hold)
- 修复：修SDC, 重新budget, 重新定义clock relation, CDC路径隔离

#### 输出格式示例

```text
Path cluster #1:
- 数量：384 条
- TNS 占比：47%
- 主要模块：dma_scheduler
- 主要结构：priority mux + grant select
- 平均 logic depth：18
- mux count：9
- net delay ratio：22%
- 判断：RTL control path dominated
- 推荐动作：
  1. RTL one-hot grant
  2. 插入一级 grant pipeline
  3. 对 grant bus 做 register duplication
- 预计收益：WNS +80~150ps，面积 +1~3%，延迟 +1 cycle
```

#### Python API

```python
class TimingFixAdvisor:
    def __init__(self, timing_db: TimingDatabase, netlist: Netlist, db: DesignDB):
        ...

    def analyze_violations(
        self,
        scenario: TimingScenario,
        top_n: int = 20,
    ) -> list[ViolationReport]:
        """返回结构化违例报告，含根因分析"""
        ...

    def classify_path(self, path: TimingPath) -> PathClassification:
        """分类path为datapath/control/physical/constraint dominated"""
        ...

    def decompose_slack(self, path: TimingPath) -> SlackBreakdown:
        ...

    def cluster_paths(
        self,
        violations: list[ViolationReport],
    ) -> list[PathCluster]:
        """路径聚类，识别系统性问题"""
        ...

    def suggest_fixes(
        self,
        violation: ViolationReport,
        allow: list[str] = ["retiming", "buffering", "sizing", "pipelining"],
    ) -> list[FixProposal]:
        ...

    def simulate_fix_sequence(
        self, fixes: list[FixProposal],
    ) -> TimingProjection:
        ...

    def auto_fix(
        self,
        scenario: TimingScenario,
        max_iterations: int = 5,
        target_slack: float = 0.0,
    ) -> FixReport:
        ...
```

---

### 6.3 Module 3: RTL & 综合结果 → 设计划分与Floorplan规划

#### 功能描述
从RTL和综合网表提取**结构性insight**，驱动block partitioning和floorplan规划。连接逻辑域和物理域的关键桥梁。

#### Module Connectivity Graph

节点：`module / submodule / macro / IO group / clock domain / power domain`

边权重：
```python
edge_weight = (
    alpha * net_count
  + beta  * bus_width
  + gamma * timing_criticality
  + delta * toggle_rate
  + eta   * pipeline_sensitivity
)
```

#### Floorplan 规则

| 分析结果 | floorplan 建议 |
|----------|----------------|
| 两模块连接强且timing critical | 放近，避免跨芯片长路径 |
| 模块间连接宽但不critical | 可放近但优先级低于timing path |
| 模块与多个macro交互 | 模块围绕macro分布 |
| macro-to-macro数据流强 | macro对齐或相邻 |
| control fanout到多个区域 | control logic中心化或复制 |
| 高toggle模块集中 | 注意IR drop和热 |
| 多clock domain | CDC边界清晰化 |
| scan/test逻辑复杂 | 预留scan chain routing channel |

#### Python API

```python
class DesignPartitioner:
    def __init__(self, netlist: Netlist, sdc: SDCParser, db: DesignDB):
        ...

    def analyze_rtl_structure(self, rtl_files: list[str]) -> RTLInsight:
        """返回层次树、重复模式、关键路径、时钟域等结构化信息"""
        ...

    def build_communication_matrix(self) -> CommunicationMatrix:
        """模块间通信强度矩阵"""
        ...

    def identify_critical_pairs(self) -> list[ModulePair]:
        """需要物理邻近的模块对"""
        ...

    def partition(
        self,
        n_partitions: int,
        constraints: dict = None,
        objective: str = "min_cut",
    ) -> PartitionResult:
        ...

    def generate_floorplan(
        self,
        partition: PartitionResult,
        chip_outline: tuple[float, float],
        aspect_ratio_range: tuple[float, float] = (0.5, 2.0),
    ) -> FloorplanProposal:
        ...

    def evaluate_floorplan(
        self, floorplan: FloorplanProposal
    ) -> FloorplanScore:
        ...

    def estimate_congestion_risk(
        self, floorplan: FloorplanProposal
    ) -> CongestionMap:
        ...

    def estimate_timing_risk(
        self, floorplan: FloorplanProposal
    ) -> TimingRiskMap:
        ...
```

---

### 6.4 Module 4: Macro布局规划

#### 功能描述
对SRAM、PLL、IO pad、analog IP等macro进行精确布局规划，考虑routing、power、timing、DRC多维度约束。

#### Macro 分类
1. SRAM / Register file
2. ROM
3. PLL
4. Analog macro
5. IO macro
6. PHY
7. Hard IP
8. Large generated macro

#### 规划规则

**A. Dataflow-aware**
- 强数据流macro同向排列
- pin对pin
- 减少交叉
- 缩短高位宽bus

**B. Timing-aware**
- critical macro path减少距离
- 保证channel足够
- 避免跨越blockage
- 必要时插pipeline register island

**C. Routing-aware**
- 预留channel width、pin access space、power strap space、clock trunk space、ECO cell space

**D. Power-aware**
- 大SRAM或高toggle macro附近加强power strap
- 避免IR hotspot
- 预留decap
- 避免多个高功耗macro聚集

**E. DRC-aware**
- macro edge/corner/notch/channel需考虑min spacing、implant/well spacing、density、pin access、via enclosure、metal fill

#### Python API

```python
class MacroPlanner:
    def __init__(self, floorplan: Floorplan, macros: list[MacroDef], db: DesignDB):
        ...

    def place_macros(
        self,
        objective: str = "wl",
        constraints: MacroConstraints = None,
    ) -> MacroPlacement:
        ...

    def check_pin_access(
        self, placement: MacroPlacement
    ) -> list[PinAccessIssue]:
        ...

    def route_channel_analysis(
        self, placement: MacroPlacement
    ) -> ChannelReport:
        ...

    def what_if_move(
        self,
        macro_id: str,
        new_location: tuple[float, float],
        new_orientation: str,
    ) -> MoveImpact:
        ...

    def generate_placement_script(
        self,
        placement: MacroPlacement,
        tool: str = "ICC2",
    ) -> ToolCommand:
        ...

    def score_placement(
        self, placement: MacroPlacement
    ) -> MacroPlacementScore:
        """综合评分：timing + routing + power + DRC risk"""
        ...
```

---

### 6.5 Module 5: 顶层EM/IR考虑

#### 功能描述
EMIR不应等到sign-off才看。分三阶段：
1. **floorplan阶段预估**
2. **post-place/post-route快速分析**
3. **sign-off精细分析**

#### 分析器

**A. Power Grid Planning Advisor**
- 输入：power domain, voltage domain, macro current, switching activity, cell density, clock tree estimate, package bump location, pad/ring location, power strap resource
- 输出：strap pitch, strap width, mesh layer assignment, macro ring requirement, bump assignment risk, decap insertion region

**B. IR Hotspot Predictor**

早期预测模型：
```python
IR_risk = f(
    local_power_density,
    distance_to_bump,
    strap_density,
    macro_current,
    simultaneous_switching,
    clock_density,
    routing_blockage
)
```

**C. EM Risk Analyzer**
- high-current net
- clock trunk
- power switch
- macro power pin
- narrow metal
- via array
- long route with high toggle
- redundant via缺失

**D. EMIR-aware Floorplan Feedback**
```text
发现：
- top-left区域power density高
- 最近bump距离820um
- SRAM macro power pin朝内，导致局部电流集中
- clock spine穿过高功耗区域

建议：
1. 将SRAM bank旋转，使power pin靠近power strap
2. 在M8/M9增加vertical strap
3. 在dma datapath周围加入decap
4. 将high-toggle block分散
5. 调整bump assignment
```

#### Python API

```python
class PowerGridPlanner:
    def __init__(self, placement: Placement, tech: TechInfo, db: DesignDB):
        ...

    def plan_power_grid(
        self,
        voltage_domains: list[VoltageDomain],
        current_budget: dict[str, float],
    ) -> PowerGridPlan:
        ...

    def estimate_ir_drop(
        self, grid_plan: PowerGridPlan
    ) -> IRDropMap:
        ...

    def predict_ir_hotspots(
        self, placement: Placement
    ) -> list[IRHotspot]:
        ...

    def check_em_risk(
        self, grid_plan: PowerGridPlan
    ) -> list[EMRisk]:
        ...

    def plan_decaps(
        self,
        ir_map: IRDropMap,
        available_decap_cells: list[CellDef],
    ) -> DecapPlan:
        ...

    def plan_power_domains(
        self,
        sdc: SDCParser,
        voltage_map: dict[str, float],
    ) -> PowerDomainPlan:
        ...

    def emir_aware_floorplan_feedback(
        self, floorplan: FloorplanProposal
    ) -> EMIRFeedback:
        """EMIR驱动的floorplan调整建议"""
        ...
```

---

### 6.6 Module 6: 布局后时序修复反馈与打拍建议

#### 功能描述
place & route完成后，基于real parasitics提供精准时序修复和寄存器重拍方案。

#### Timing Evolution Tracker

对每个path cluster跟踪：
```text
WNS change / TNS change / cell delay change / net delay change
transition change / capacitance change / fanout change
physical distance / detour ratio / congestion overlap
```

#### 修复动作分类

**A. 物理ECO**
- cell sizing / buffer insertion / Vt swap / placement spreading
- critical cell clustering / route layer promotion / shielding / useful skew

**B. 逻辑ECO**
- logic restructuring / register duplication / retiming
- boundary optimization / datapath rewrite

**C. RTL feedback**（当物理ECO无法收敛时）

打拍/pipeline的判断条件：
- violation cluster跨越距离 > 1mm
- net delay ratio > 60%
- 多轮ECO后WNS改善 < 20ps
- path为宽bus或arbitration mux
- 修复导致hold/area/congestion明显恶化

#### Pipeline Feedback 示例

```text
建议在 dma_rd_data_valid 与 axi_wdata_pack 之间插入一级 pipeline：

原因：
- 当前路径 slack = -180ps
- net delay 占比 67%
- 起点与终点物理距离 1.4mm
- 路径经过 SRAM macro channel，拥塞高
- cell sizing 已尝试 3 轮，WNS 仅改善 22ps
- 插入 pipeline 后预计 WNS 改善 120~220ps

代价：
- 增加 1 cycle latency
- 增加约 512 个 flop
- dynamic power 增加约 X
- 需要检查 valid/ready 协议

Spec check:
- dma latency budget = 16 cycles
- 当前 latency = 14 cycles
- 插入后 latency = 15 cycles
- 不违反 spec ✓
```

#### Python API

```python
class PostRouteTimingFixer:
    def __init__(self, timing_db: TimingDatabase, spef: SPEFParser, db: DesignDB):
        ...

    def analyze_post_route_timing(
        self,
        corners: list[str] = ["ss_0p8v_125c", "tt_1p0v_25c", "ff_1p1v_m40c"],
    ) -> PostRouteTimingReport:
        ...

    def track_timing_evolution(
        self,
        run_id: str,
        baseline_run_id: str,
    ) -> TimingEvolution:
        """跟踪时序从synthesis到post-route的演变"""
        ...

    def suggest_incremental_fixes(
        self,
        violation: TimingViolation,
    ) -> list[IncrementalFix]:
        ...

    def retiming_optimization(
        self,
        target_period: float,
        preserve_io: bool = True,
        max_displacement: int = 20,
    ) -> RetimingResult:
        ...

    def suggest_pipeline_insertion(
        self,
        max_stages: int = 3,
    ) -> list[PipelineProposal]:
        ...

    def co_fix_setup_hold(
        self,
        scenario: TimingScenario,
    ) -> CoFixReport:
        ...

    def evaluate_mc_robustness(
        self,
        fixes: list[FixProposal],
    ) -> MCRobustnessScore:
        ...

    def should_feedback_rtl(
        self,
        violations: list[TimingViolation],
    ) -> RTLFeedbackRecommendation:
        """判断是否需要反馈RTL修改"""
        ...
```

---

### 6.7 Module 7: PrimeTime / Tempus & 功耗分析 Sign-off

#### 功能描述
时序和功耗的sign-off阶段深度分析。不仅运行PT，更提供sign-off readiness评估。

#### STA Sign-off 检查项

1. SDC consistency
2. MMMC scenario coverage
3. setup / hold
4. recovery / removal
5. min pulse width
6. max transition / capacitance
7. clock gating check
8. generated clock
9. CDC boundary
10. SI / crosstalk
11. OCV/AOCV/POCV
12. PBA vs GBA
13. ECO side effect
14. ECO后formal equivalence

#### Power 分析

输入：SAIF/VCD/FSDB activity, UPF, Liberty power model, SPEF, clock tree report

分析维度：
1. module-level power breakdown
2. clock power ratio
3. high-toggle hotspot
4. glitch power
5. unnecessary switching
6. clock gating opportunity
7. multi-bit flop opportunity
8. Vt mix
9. power domain shutdown correctness
10. DVFS mode power

#### Python API

```python
class SignoffAnalyzer:
    def __init__(self, pt_db: PrimeTimeDatabase, spef: SPEFParser, db: DesignDB):
        ...

    def run_mcmm_analysis(
        self, scenarios: list[TimingScenario],
    ) -> MCMMReport:
        ...

    def check_signoff_readiness(self) -> SignoffChecklist:
        """Sign-off就绪检查"""
        ...

    def margin_analysis(
        self, scenario: TimingScenario,
    ) -> MarginDistribution:
        ...

    def si_impact_analysis(self) -> SIReport:
        ...

    def compare_derating_schemes(
        self, schemes: list[str] = ["SOCV", "AOCV", "POCV"],
    ) -> DeratingComparison:
        ...

    def power_breakdown(
        self,
        hierarchy: bool = True,
        granularity: str = "module",
    ) -> PowerBreakdown:
        ...

    def power_optimization_suggestions(self) -> list[PowerSuggestion]:
        ...

    def clock_power_analysis(self) -> ClockPowerReport:
        ...

    def waiver_risk_analysis(self) -> list[WaiverRisk]:
        ...

    def signoff_power_diagnosis(self) -> PowerDiagnosis:
        ...
```

---

### 6.8 Module 8: EM/IR Sign-off

#### 功能描述
完整EM/IR sign-off分析，对接RedHawk/Voltus/PrimeRail，提供结果解读和修复方案。

#### IR Drop Diagnosis 分类

1. static IR
2. dynamic IR
3. macro pin IR
4. power switch IR
5. bump-limited IR
6. strap-limited IR
7. localized cell density IR

#### Root Cause Mapping

```text
IR hotspot
  → physical region
  → instances/macros
  → power domain
  → activity source
  → clock/data burst
  → possible floorplan/power grid fixes
```

#### 修复策略

| 问题 | 修复 |
|------|------|
| strap稀疏 | 增加strap / 加宽metal |
| bump距离远 | 调整bump / pad / power grid topology |
| macro current集中 | 加macro ring / 改macro orientation |
| local dynamic IR | 加decap / 分散high-toggle cells |
| via EM | 加redundant via |
| clock EM | widen / route promotion / split trunk |
| power switch IR | 增加switch / 改switch分布 |

#### Python API

```python
class EMIRSignoffAnalyzer:
    def __init__(self, emir_db: EMIRDatabase, tech: TechInfo, db: DesignDB):
        ...

    def static_ir_analysis(self) -> StaticIRReport:
        ...

    def dynamic_ir_analysis(
        self,
        window: float = 1e-9,
        resolution: float = 1e-12,
    ) -> DynamicIRReport:
        ...

    def classify_ir_violations(self) -> list[IRViolationCluster]:
        """将IR violation分类为static/dynamic/macro pin/switch/bump/strap/density"""
        ...

    def em_check(self) -> EMCheckReport:
        ...

    def hotspot_detection(self) -> list[Hotspot]:
        ...

    def root_cause_mapping(
        self, hotspot: Hotspot
    ) -> HotspotRootCause:
        """将hotspot映射到物理区域、实例、power domain、activity source"""
        ...

    def generate_fix(
        self,
        violation: EMIRViolation,
        strategy: str = "minimal",
    ) -> EMIRFixProposal:
        ...

    def signoff_report(self) -> EMIRSignoffReport:
        ...

    def compare_with_spec(
        self, spec: EMIRSpec,
    ) -> ComplianceReport:
        ...
```

---

### 6.9 Module 9: DRC/LVS Fixing

#### 功能描述
物理验证阶段的**自动修复**。结构化理解violation，而非简单文本转发。

#### DRC Violation 模型

```python
class DRCViolation:
    rule_id: str
    rule_type: str          # spacing, width, enclosure, via, notch, density, antenna, ...
    layer: str
    bbox: BBox
    objects: list[LayoutObject]
    severity: str
    repeated_pattern: bool
    near_macro: bool
    near_pin: bool
    near_power_grid: bool
    fix_candidates: list[FixAction]
```

#### DRC 分类

1. spacing
2. width
3. enclosure
4. via
5. notch
6. density
7. antenna
8. pin access
9. min area
10. end-of-line
11. double patterning / coloring
12. macro boundary
13. power grid DRC
14. fill DRC

#### DRC Fix 策略

| 类型 | 修复 |
|------|------|
| metal spacing | rip-up reroute / NDR / layer promotion |
| via enclosure | via replacement / widen metal |
| antenna | diode insertion / metal jumper |
| density | fill insertion / fill blockage adjustment |
| macro boundary spacing | move macro / add keepout / route blockage |
| pin access | cell padding / swap cell / route guide |
| min area | patch metal |
| EOL | route cleanup / jog adjustment |

#### LVS 问题分类

1. net mismatch
2. device mismatch
3. missing connection
4. short
5. open
6. power/ground mismatch
7. blackbox mismatch
8. pin name mismatch
9. hierarchy mismatch
10. extracted parasitic issue
11. fill/dummy device issue

#### Python API

```python
class PhysicalVerificationFixer:
    def __init__(self, layout_db: LayoutDatabase, tech_rules: TechRules, db: DesignDB):
        ...

    def parse_drc_results(self, results_file: str) -> DRCReport:
        ...

    def parse_lvs_results(self, results_file: str) -> LVSReport:
        ...

    def classify_violations(
        self, report: Union[DRCReport, LVSReport]
    ) -> ViolationClassification:
        ...

    def cluster_violations(
        self, violations: list[Violation]
    ) -> list[ViolationCluster]:
        """violation聚类，识别系统性问题"""
        ...

    def root_cause_analysis(
        self, violation: Violation
    ) -> RootCause:
        ...

    def generate_fix(
        self,
        violation: Violation,
        strategy: str = "conservative",
    ) -> FixProposal:
        ...

    def auto_fix_flow(
        self,
        max_iterations: int = 10,
        target_clean: bool = True,
    ) -> AutoFixReport:
        ...

    def fix_priority_queue(self) -> list[FixTask]:
        ...

    def verify_fix(
        self, fix: FixProposal,
    ) -> FixVerification:
        ...

    def mine_repeated_patterns(self) -> list[RepeatedPattern]:
        """挖掘重复出现的violation模式"""
        ...
```

---

### 6.10 Module 10: 自动化流程生成与工具适配

#### 功能描述
统一Python函数接口编排整个后端流程，自动处理工具调用、数据转换、中间结果管理。

#### 硬核能力

| 能力 | 实现方式 |
|------|----------|
| **工具抽象层** | 统一Tool接口，屏蔽DC/Genus/FC、ICC2/Innovus、PT/Tempus差异 |
| **Flow模板引擎** | 预定义flow模板（综合flow、PnR flow、signoff flow），支持参数化定制 |
| **数据管道** | 工具间数据自动转换 |
| **Checkpoint管理** | 每个flow step结果持久化，支持断点续跑 |
| **并行执行** | 多scenario/多corner并行执行管理 |
| **增量流程** | 支持从任意中间step重启flow |
| **结果追踪** | 完整flow执行日志和结果血缘追踪 |
| **环境管理** | 工具版本、license、环境变量统一管理 |

#### Python API

```python
class BackendFlowOrchestrator:
    def __init__(self, adapter: ToolAdapter, db: DesignDB):
        ...

    def run_full_flow(
        self, design: str, constraints: dict, tech_node: str,
    ) -> FlowReport:
        ...

    def run_synthesis_flow(
        self, rtl: list[str], libs: list[str], sdc: str,
        config: SynthesisConfig = None,
    ) -> SynthesisFlowResult:
        ...

    def run_pnr_flow(
        self, netlist: str, floorplan: Floorplan = None,
        sdc: str = None, config: PnRConfig = None,
    ) -> PnRFlowResult:
        ...

    def run_signoff_flow(
        self, design: str,
        include: list[str] = ["sta", "power", "emir", "drc", "lvs"],
    ) -> SignoffFlowResult:
        ...

    def checkpoint_save(self, step: str, data: Any):
        ...

    def checkpoint_load(self, step: str) -> Any:
        ...

    def get_flow_status(self) -> FlowStatus:
        ...
```

---

### 6.11 Module 11: 脚本级任务调度与日志分析

#### 功能描述
在脚本执行层面提供**任务拆分、调度、日志分析、进度可视化、时间预估**等能力，让Agent和用户能够实时掌握flow执行状态，并对异常进行快速诊断。

#### 核心能力

**A. 任务拆分引擎（Task Decomposition）**

将高层flow目标自动拆分为可执行的原子任务：
```text
"Run full signoff for dma_core at 800MHz"
  → [Task 1] Generate signoff SDC
  → [Task 2] Run PrimeTime STA (3 corners)
  → [Task 3] Run PrimePower
  → [Task 4] Run PrimeRail EMIR
  → [Task 5] Run Calibre DRC
  → [Task 6] Run Calibre LVS
  → [Task 7] Aggregate reports
  → [Task 8] Generate signoff summary
```

任务模型：
```python
class Task:
    task_id: str
    name: str
    type: str                  # "synthesis", "pnr", "sta", "power", "emir", "drc", "lvs", "custom"
    tool: str                  # "dc_shell", "icc2_shell", "pt_shell", "calibre", ...
    depends_on: list[str]      # 依赖的前置task
    inputs: list[Artifact]
    outputs: list[Artifact]
    config: dict
    estimated_runtime: float   # 预估运行时间（秒）
    estimated_memory: float    # 预估内存（GB）
    priority: int
    retry_policy: RetryPolicy
    timeout: float
    tags: list[str]
```

**B. 任务调度器（Task Scheduler）**

```python
class TaskScheduler:
    def decompose(self, goal: FlowGoal) -> list[Task]:
        """将目标拆分为任务DAG"""
        ...

    def schedule(
        self,
        tasks: list[Task],
        resources: ResourcePool,      # CPU cores, memory, license count
        strategy: str = "earliest_deadline_first",
    ) -> SchedulePlan:
        """生成调度方案，考虑依赖、资源、license、优先级"""
        ...

    def execute(self, plan: SchedulePlan) -> TaskStream:
        """流式执行，实时返回状态"""
        ...

    def parallel_corners(
        self,
        base_task: Task,
        corners: list[str],
    ) -> list[Task]:
        """自动展开多corner并行任务"""
        ...

    def pause_and_resume(
        self,
        schedule_id: str,
        action: str = "pause",        # "pause", "resume", "cancel"
    ) -> ScheduleStatus:
        """暂停/恢复/取消调度"""
        ...
```

**C. 日志分析引擎（Log Analyzer）**

```python
class LogAnalyzer:
    def parse_log(
        self,
        log_file: str,
        tool: str,                    # "dc", "icc2", "pt", "calibre", ...
    ) -> StructuredLog:
        """将原始log解析为结构化对象"""
        ...

    def detect_errors(
        self, log: StructuredLog
    ) -> list[LogError]:
        """检测error/warning/critical，分类严重程度"""
        ...

    def extract_metrics(
        self, log: StructuredLog
    ) -> LogMetrics:
        """从log提取运行时指标：runtime, memory, license usage, ..."""
        ...

    def detect_anomalies(
        self, log: StructuredLog, baseline: LogMetrics = None
    ) -> list[Anomaly]:
        """与历史baseline对比，检测异常（runtime异常长、memory暴涨、warning激增）"""
        ...

    def explain_error(
        self, error: LogError
    ) -> ErrorExplanation:
        """解释error原因并给出修复建议"""
        ...

    def search_similar_issues(
        self, error: LogError
    ) -> list[KnownIssue]:
        """在知识库中搜索类似问题"""
        ...
```

**D. 进度可视化（Progress Visualization）**

```python
class ProgressTracker:
    def get_flow_progress(
        self, schedule_id: str
    ) -> FlowProgress:
        """返回flow整体进度：完成百分比、当前阶段、剩余任务"""
        ...

    def get_task_progress(
        self, task_id: str
    ) -> TaskProgress:
        """返回单任务进度：running time, estimated remaining, current step"""
        ...

    def render_gantt_chart(
        self, schedule_id: str
    ) -> GanttChart:
        """生成甘特图，展示任务时序和依赖"""
        ...

    def render_dependency_graph(
        self, schedule_id: str
    ) -> DependencyGraph:
        """生成任务依赖图"""
        ...

    def generate_dashboard(
        self, schedule_id: str
    ) -> DashboardData:
        """生成实时dashboard数据：任务状态、QoR、log摘要、资源使用"""
        ...

    def send_notification(
        self,
        event: str,                   # "task_completed", "error_detected", "flow_done"
        message: str,
        channels: list[str] = ["console", "email", "slack"],
    ):
        """发送进度/异常通知"""
        ...
```

**E. 时间预估（Runtime Estimation）**

```python
class RuntimeEstimator:
    def estimate_task_runtime(
        self,
        task: Task,
        design_size: DesignSize,
        historical_data: list[HistoricalRun] = None,
    ) -> RuntimeEstimate:
        """基于设计规模和历史数据预估任务运行时间"""
        ...

    def estimate_flow_completion(
        self, schedule_id: str
    ) -> CompletionEstimate:
        """预估整个flow的完成时间（含置信区间）"""
        ...

    def update_estimate(
        self,
        task_id: str,
        current_progress: float,
        elapsed_time: float,
    ) -> UpdatedEstimate:
        """基于实际进度更新剩余时间预估"""
        ...

    def learn_from_run(
        self,
        completed_run: CompletedRun,
    ):
        """从已完成的run中学习，更新预估模型"""
        ...
```

#### Python API 整合示例

```python
class TaskExecutionEngine:
    def __init__(self, scheduler: TaskScheduler, db: DesignDB):
        ...

    def run_with_monitoring(
        self,
        goal: FlowGoal,
        resources: ResourcePool = None,
    ) -> MonitoredFlowResult:
        """执行flow并实时监控"""
        tasks = self.scheduler.decompose(goal)
        plan = self.scheduler.schedule(tasks, resources)

        for task_result in self.scheduler.execute(plan):
            # 实时更新进度
            self.progress_tracker.update(task_result)

            # 日志分析
            log = self.log_analyzer.parse_log(task_result.log_file, task_result.tool)
            errors = self.log_analyzer.detect_errors(log)

            if errors:
                self.progress_tracker.send_notification("error_detected", str(errors))

            # 写回数据库
            self.db.add_metric(task_result.metrics)
            self.db.add_report(task_result.report)

        return MonitoredFlowResult(
            tasks=tasks,
            progress=self.progress_tracker.get_flow_progress(plan.id),
            dashboard=self.progress_tracker.generate_dashboard(plan.id),
        )
```

---

### 6.12 Module 12: 版本管理与设计配置管理

#### 功能描述
提供完整的**版本管理**功能，通过版本管理系统对**脚本、代码、设计**进行管理。对于大型设计数据库，在版本管理系统中记录**数据库名/cell名称**的引用。

#### 核心能力

**A. 设计版本管理（Design Version Control）**

```python
class DesignVersionManager:
    def commit(
        self,
        design_id: str,
        changes: list[DesignChange],
        message: str,
        author: str,
        tag: str = None,              # 可选tag：v1.0, release_2024Q3, ...
    ) -> DesignCommit:
        """提交设计变更"""
        ...

    def checkout(
        self,
        design_id: str,
        version: str,                 # commit hash, tag, or branch
    ) -> DesignSnapshot:
        """检出特定版本的设计"""
        ...

    def diff(
        self,
        design_id: str,
        version_a: str,
        version_b: str,
    ) -> DesignDiff:
        """比较两个版本的设计差异"""
        ...

    def log(
        self,
        design_id: str,
        n: int = 20,
    ) -> list[DesignCommit]:
        """查看设计提交历史"""
        ...

    def tag(
        self,
        design_id: str,
        version: str,
        tag_name: str,
        message: str = None,
    ):
        """打tag（如 tapeout_v1, signoff_approved, ...）"""
        ...

    def branch(
        self,
        design_id: str,
        branch_name: str,
        from_version: str = "HEAD",
    ) -> DesignBranch:
        """创建分支（如eco_branch, timing_fix_branch）"""
        ...
```

**B. 多层级版本对象**

版本管理覆盖三个层面：

```text
1. 代码/脚本层
   - RTL代码（Verilog/SystemVerilog）
   - Tcl脚本（DC/ICC2/PT/Calibre）
   - Python flow脚本
   - SDC/UPF约束文件
   - 配置文件

2. 设计数据层
   - 综合结果（DDC/设计数据库）
   - 物理设计（DEF/GDS/OAS）
   - Timing报告
   - Power报告
   - EMIR报告
   - DRC/LVS报告

3. 大型数据库引用层
   - 数据库名称（DB name）
   - Cell名称（Cell name / library name）
   - Macro名称（Macro name）
   - 通过引用而非复制管理大型数据
```

```python
class DesignObject:
    """设计对象版本"""
    object_id: str
    object_type: str          # "rtl_module", "synth_db", "def", "gds", "timing_report", ...
    name: str                 # 对象名（模块名、cell名、数据库名）
    version: str              # 版本号
    git_ref: str              # Git commit/ref
    db_name: str = None       # 设计数据库名称（如DC的design name）
    cell_name: str = None     # Cell/library名称
    checksum: str
    size_bytes: int
    created_at: str
    author: str
    parent_versions: list[str]
```

**C. 大型设计数据库的版本引用**

对于大型设计（数十GB），不存储完整数据，而是记录引用：

```python
class DesignDatabaseRef:
    """大型设计数据库的版本引用"""
    ref_id: str
    db_name: str              # 数据库名称（如 "dma_core_synthesized_v3"）
    db_type: str              # "ddc", "innovus_db", "pt_db", ...
    tool: str                 # 生成工具
    location: str             # 物理路径（NFS/存储路径）
    version: str              # 版本标签
    git_commit: str           # 关联的Git commit（记录配置/脚本版本）
    design_id: str
    cell_names: list[str]     # 包含的cell名称列表
    snapshot_time: str
    checksum: str
    metadata: dict            # 额外元数据（corner, mode, etc.）
```

**D. Flow脚本版本管理**

```python
class FlowScriptManager:
    def register_script(
        self,
        script_path: str,
        tool: str,
        stage: str,
        design_id: str,
        parameters: dict,
    ) -> ScriptVersion:
        """注册flow脚本版本"""
        ...

    def get_script(
        self,
        tool: str,
        stage: str,
        version: str = "latest",
    ) -> FlowScript:
        """获取特定版本的脚本"""
        ...

    def diff_scripts(
        self,
        script_id: str,
        version_a: str,
        version_b: str,
    ) -> ScriptDiff:
        """比较脚本版本差异"""
        ...

    def replay_script(
        self,
        script_version: str,
        design_version: str,
    ) -> ReplayResult:
        """使用特定版本的脚本跑特定版本的设计（复现性）"""
        ...
```

**E. 版本关联与血缘追踪**

```python
class VersionLineage:
    def trace_artifact(
        self, artifact_id: str
    ) -> ArtifactLineage:
        """追踪一个artifact的完整血缘：
        RTL_v12 → SDC_v5 → synth_run_021 → DDC_v18 → floorplan_run_008 → DEF_v22 ..."""
        ...

    def compare_lineage(
        self,
        lineage_a: str,
        lineage_b: str,
    ) -> LineageDiff:
        """比较两条血缘的差异点"""
        ...

    def find_divergence_point(
        self,
        run_a: str,
        run_b: str,
    ) -> DivergencePoint:
        """找到两个run从哪个点开始分叉"""
        ...
```

**F. 与Git的集成**

```python
class GitIntegration:
    def __init__(self, repo_path: str):
        ...

    def init_design_repo(self, design_id: str):
        """初始化设计仓库的Git结构"""
        ...

    def commit_design_snapshot(
        self,
        snapshot: DesignSnapshot,
        message: str,
        tag: str = None,
    ) -> GitCommit:
        """提交设计快照到Git"""
        ...

    def get_git_state(self) -> GitState:
        """获取当前Git状态：branch, commit, dirty files, ..."""
        ...

    def create_release(
        self,
        tag: str,
        design_id: str,
        artifacts: list[str],
    ) -> Release:
        """创建设计release（含所有相关artifacts）"""
        ...
```

#### Python API 整合示例

```python
class DesignConfigurationManager:
    """设计配置管理总入口"""
    def __init__(
        self,
        vcs: DesignVersionManager,
        script_mgr: FlowScriptManager,
        db_refs: DesignDatabaseRefManager,
        git: GitIntegration,
        design_db: DesignDB,
    ):
        ...

    def snapshot_current_state(
        self, design_id: str
    ) -> DesignStateSnapshot:
        """对当前设计状态做完整快照：代码+脚本+数据+配置"""
        ...

    def create_run_from_versions(
        self,
        design_version: str,
        sdc_version: str,
        script_versions: dict,
        config: dict,
    ) -> DesignRun:
        """从特定版本组合创建run（完全可复现）"""
        ...

    def tag_milestone(
        self,
        design_id: str,
        milestone: str,             # "synthesis_done", "floorplan_approved", "tapeout"
        artifacts: list[str],
        approvers: list[str],
    ) -> MilestoneTag:
        """打里程碑tag，记录审批人"""
        ...

    def audit_trail(
        self,
        design_id: str,
    ) -> AuditTrail:
        """完整审计轨迹：谁在什么时候做了什么变更，为什么"""
        ...
```

#### 版本管理目录结构示例

```text
design_repo/
 ├── .git/
 ├── design.yaml                  # 设计元数据
 ├── rtl/
 │    ├── dma_core.v
 │    ├── axi_if.v
 │    └── ...
 ├── constraints/
 │    ├── sdc/
 │    │    ├── v1/
 │    │    ├── v2/
 │    │    └── current -> v2/
 │    └── upf/
 ├── scripts/
 │    ├── synthesis/
 │    │    ├── dc_run.tcl
 │    │    └── fc_run.tcl
 │    ├── pnr/
 │    │    ├── icc2_run.tcl
 │    │    └── innovus_run.tcl
 │    └── signoff/
 │        ├── pt_run.tcl
 │        └── calibre_run.tcl
 ├── refs/                         # 大型数据库引用
 │    ├── synth_db.yaml             # 综合数据库引用（DB name, cell names, path）
 │    ├── pnr_db.yaml
 │    └── signoff_db.yaml
 ├── runs/
 │    ├── run_001/
 │    │    ├── config.yaml
 │    │    ├── log/
 │    │    └── reports/
 │    └── run_002/
 └── releases/
      ├── v1.0/
      └── tapeout_2024Q4/
```

---

### 6.13 Module 13: 形式化验证（Formal Verification）

#### 功能描述
提供完整的形式化验证能力，确保设计在各阶段的功能正确性。形式化验证是后端ECO安全的**基石**——没有LEC验证，agent不能自动接受任何逻辑修改。

#### 核心验证类型

**A. 逻辑等价性检查（Logic Equivalence Checking, LEC）**

| 验证场景 | 说明 |
|----------|------|
| **RTL vs Netlist** | 综合后功能等价验证 |
| **Netlist vs Netlist** | ECO前后等价验证 |
| **Pre-scan vs Post-scan** | Scan插入前后等价验证 |
| **Pre-low-power vs Post-low-power** | Power intent插入后等价验证 |
| **Metal ECO** | Metal-only ECO的功能等价验证 |
| **Multi-corner** | 不同corner下netlist的功能等价 |

**B. 属性检查（Property Checking / Model Checking）**

```text
验证类型：
- 断言验证（SVA assertions）
- 安全属性（safety properties）
- 活性属性（liveness properties）
- 协议一致性（protocol compliance）
- 死锁检测（deadlock freedom）
```

**C. CDC/RDC 验证**

```text
验证内容：
- 时钟域交叉（CDC）结构正确性
- 复位域交叉（RDC）结构正确性
- 同步器正确性
- 格雷码/异步FIFO验证
- 隔离单元（isolation cell）正确性
- Level shifter正确性
- Retention register正确性
```

**D. Low-Power Intent 验证**

```text
验证内容：
- UPF/CPF一致性
- Power domain隔离正确性
- Supply net连接正确性
- Power switch控制逻辑
- Always-on区域完整性
- Retention策略验证
- State retention / restore正确性
```

**E. 约束验证**

```text
验证内容：
- SDC与UPF一致性
- Clock definition完整性
- False path / multicycle path合理性
- IO constraint自洽性
- Generated clock定义正确性
```

#### 硬核分析能力

| 能力 | 实现方式 |
|------|----------|
| **Non-equivalence分析** | 非等价点的根因分析，定位到具体instance/net |
| **Divergence point定位** | 找到两个设计开始分叉的最小cut point |
| **Equivalent point识别** | 自动识别可安全用作比较点的equivalent points |
| **Abstraction建议** | 对复杂模块自动建议abstraction策略 |
| **Debug辅助** | 生成counter-example trace辅助debug |
| **ECO安全评估** | 在ECO执行前预估LEC风险 |
| **Incremental LEC** | 支持增量LEC，避免全芯片重新验证 |

#### Python API

```python
class FormalVerificationEngine:
    def __init__(self, db: DesignDB):
        ...

    # LEC相关
    def run_lec(
        self,
        golden: DesignArtifact,       # golden design (RTL / pre-ECO netlist)
        revised: DesignArtifact,      # revised design (netlist / post-ECO netlist)
        config: LECConfig = None,
    ) -> LECResult:
        """运行逻辑等价性检查"""
        ...

    def analyze_non_equivalence(
        self, result: LECResult
    ) -> list[NonEqAnalysis]:
        """分析非等价点的根因"""
        ...

    def find_divergence_points(
        self,
        golden: DesignArtifact,
        revised: DesignArtifact,
    ) -> list[DivergencePoint]:
        """找到两个设计分叉的关键点"""
        ...

    def suggest_abstraction(
        self, design: DesignArtifact
    ) -> list[AbstractionSuggestion]:
        """建议模块级abstraction策略"""
        ...

    def incremental_lec(
        self,
        previous_result: LECResult,
        changed_modules: list[str],
    ) -> LECResult:
        """增量LEC，只重新验证变化部分"""
        ...

    # Property Checking
    def run_property_check(
        self,
        design: DesignArtifact,
        properties: list[Property],
        config: PropertyCheckConfig = None,
    ) -> PropertyCheckResult:
        """运行属性检查"""
        ...

    def generate_counterexample(
        self,
        failed_property: Property,
    ) -> CounterExample:
        """为失败属性生成反例trace"""
        ...

    # CDC/RDC
    def verify_cdc(
        self, design: DesignArtifact
    ) -> CDCResult:
        """CDC结构验证"""
        ...

    def verify_rdc(
        self, design: DesignArtifact
    ) -> RDCResult:
        """RDC结构验证"""
        ...

    # Low-Power
    def verify_power_intent(
        self,
        design: DesignArtifact,
        upf: DesignArtifact,
    ) -> PowerIntentResult:
        """UPF/CPF power intent验证"""
        ...

    # ECO Safety
    def assess_eco_safety(
        self,
        eco_plan: ECOPlan,
    ) -> ECOSafetyAssessment:
        """在执行ECO前评估LEC风险"""
        ...

    def generate_lec_checkpoint(
        self, design: DesignArtifact
    ) -> LECCheckpoint:
        """生成LEC checkpoint，支持增量验证"""
        ...
```

#### 工具适配

```python
class FormalToolAdapter(ABC):
    @abstractmethod
    def run_lec(self, golden: str, revised: str, config: dict) -> LECResult: ...
    @abstractmethod
    def run_property_check(self, design: str, properties: list) -> PropertyCheckResult: ...
    @abstractmethod
    def run_cdc_check(self, design: str) -> CDCResult: ...

class SynopsysFormalAdapter(FormalToolAdapter):
    """Formality adapter"""
    ...

class CadenceFormalAdapter(FormalToolAdapter):
    """JasperGold adapter"""
    ...

class SiemensFormalAdapter(FormalToolAdapter):
    """Design Compiler Formality / Questa Formal adapter"""
    ...
```

#### 与ECO流程的集成

```text
ECO Proposal
  → assess_eco_safety()     # 评估LEC风险
  → generate_lec_checkpoint()  # 保存当前验证状态
  → apply_eco()             # 执行ECO
  → incremental_lec()       # 增量LEC验证
  → if non-equivalent:
       → analyze_non_equivalence()  # 分析根因
       → rollback or debug
  → else:
       → ECO verified ✓
```

---

### 6.14 Module 14: Bump / RDL / PAD 设计

#### 功能描述
提供**Flip-Chip封装**相关的物理设计能力，包括PAD placement、bump assignment、RDL routing规划。这是先进封装（FCBGA、FCCSP、2.5D/3D IC）的关键后端能力。

#### 核心设计内容

**A. PAD Placement Planning**

```text
设计考虑：
- IO类型分类（power, ground, signal, analog, RF）
- PAD ring规划（side分配、corner处理）
- PAD间距约束（min pitch, min spacing）
- Wirebond vs Flip-chip选择
- Probe pad需求
- ESD保护需求
- 散热考虑（thermal pad）
```

**B. Bump Assignment & Optimization**

```text
设计考虑：
- Bump类型（C4, micro-bump, TSV）
- Bump pitch和pattern（full array, perimeter, staggered）
- Power/ground bump分配（电流密度、IR drop）
- Signal bump分配（SI、crosstalk、阻抗匹配）
- Ground-signal-ground（GSG）pattern
- High-speed IO bump placement（impedance control）
- Thermal bump（散热bump分布）
- Keepout区域处理
- Redundant bump策略
```

**C. RDL (Redistribution Layer) Design**

```text
设计考虑：
- RDL routing规划
- RDL layer stack-up
- RDL trace width/spacing
- RDL via设计
- RDL与bump的连接
- RDL与PAD的连接
- RDL DRC约束
- RDL impedance control
- RDL屏蔽（shielding）
```

**D. Package-Level Considerations**

```text
设计考虑：
- Package type（FCBGA, FCCSP, PoP, 2.5D interposer）
- Substrate layer map
- Package pin map
- Package parasitic estimation
- Package thermal model
- Package mechanical constraints
- Co-design with package designer
```

#### 硬核分析能力

| 能力 | 实现方式 |
|------|----------|
| **IO分析** | 从RTL/SDC提取IO信息，分类IO类型和速率 |
| **Bump需求估算** | 基于power budget和IO count估算bump数量 |
| **Power/Ground bump优化** | 基于电流密度和IR drop约束的优化分配 |
| **Signal完整性评估** | 评估bump pattern的SI影响 |
| **Thermal分析** | Bump分布对散热的影响评估 |
| **RDL congestion预估** | Bump assignment后的RDL routing难度评估 |
| **Package co-optimization** | 与package设计的协同优化 |
| **DRC-aware placement** | 考虑RDL DRC约束的bump placement |

#### Python API

```python
class PackageDesignPlanner:
    def __init__(self, design: Design, package: PackageSpec, db: DesignDB):
        ...

    # PAD Planning
    def analyze_io_requirements(self) -> IOAnalysis:
        """分析IO需求：类型、速率、电气要求"""
        ...

    def plan_pad_placement(
        self,
        pad_types: list[PadType],
        constraints: PadConstraints = None,
    ) -> PadPlacementPlan:
        """PAD placement规划"""
        ...

    def check_pad_drc(
        self, plan: PadPlacementPlan
    ) -> list[PadDRCViolation]:
        """PAD placement DRC检查"""
        ...

    # Bump Planning
    def estimate_bump_requirements(self) -> BumpRequirements:
        """估算bump需求：power/ground/signal数量"""
        ...

    def assign_bumps(
        self,
        bump_type: str,                # "C4", "micro_bump", "TSV"
        pitch: float,                  # bump pitch (um)
        pattern: str = "full_array",   # "full_array", "perimeter", "staggered"
        constraints: BumpConstraints = None,
    ) -> BumpAssignment:
        """Bump分配优化"""
        ...

    def optimize_power_ground_bumps(
        self,
        power_domains: list[PowerDomain],
        current_budget: dict[str, float],
        max_ir_drop: float,
    ) -> PGBumpOptimization:
        """Power/ground bump优化（考虑IR drop和EM）"""
        ...

    def check_bump_current_density(
        self, assignment: BumpAssignment
    ) -> list[BumpEMViolation]:
        """Bump电流密度检查"""
        ...

    def evaluate_si_impact(
        self, assignment: BumpAssignment
    ) -> BumpSIReport:
        """评估bump pattern的signal integrity影响"""
        ...

    def evaluate_thermal_impact(
        self, assignment: BumpAssignment
    ) -> BumpThermalReport:
        """评估bump分布对散热的影响"""
        ...

    # RDL Planning
    def plan_rdl_routing(
        self,
        bump_assignment: BumpAssignment,
        pad_placement: PadPlacementPlan,
        rdl_stackup: RDLStackup,
    ) -> RDLRoutingPlan:
        """RDL routing规划"""
        ...

    def estimate_rdl_congestion(
        self, plan: RDLRoutingPlan
    ) -> RDLCongestionReport:
        """RDL拥塞预估"""
        ...

    def check_rdl_drc(
        self, plan: RDLRoutingPlan
    ) -> list[RDL_DRCViolation]:
        """RDL DRC检查"""
        ...

    # Package Co-optimization
    def co_optimize_with_package(
        self,
        package_constraints: PackageConstraints,
    ) -> CoOptimizationResult:
        """与package设计协同优化"""
        ...

    def generate_package_bump_map(
        self, assignment: BumpAssignment
    ) -> PackageBumpMap:
        """生成package bump map文件"""
        ...
```

#### 工具适配

```python
class PackageToolAdapter(ABC):
    @abstractmethod
    def run_pad_planning(self, config: dict) -> PadPlanResult: ...
    @abstractmethod
    def run_bump_assignment(self, config: dict) -> BumpResult: ...
    @abstractmethod
    def run_rdl_routing(self, config: dict) -> RDLResult: ...

class SynopsysPackageAdapter(PackageToolAdapter):
    """IC Compiler II pad/bump planning, ICV pad/route"""
    ...

class CadencePackageAdapter(PackageToolAdapter):
    """Innovus pad planning, SSO Analyzer, PG Wizard"""
    ...

class ThirdPartyPackageAdapter(PackageToolAdapter):
    """Kandou, CST, Ansys等第三方封装分析工具"""
    ...
```

#### Bump/RDL与后端流程的集成

```text
Floorplan
  → analyze_io_requirements()
  → plan_pad_placement()
  → initial bump estimation
  → floorplan iteration (考虑bump位置)

Macro Placement
  → 考虑bump access
  → 考虑RDL routing channel

Power Grid Planning
  → optimize_power_ground_bumps()
  → check_bump_current_density()

Post-Route
  → finalize bump assignment
  → plan_rdl_routing()
  → RDL DRC check

Sign-off
  → EMIR sign-off（含bump EM）
  → SI sign-off（含package效应）
  → Thermal sign-off
```

#### Python API 整合示例

```python
class PackageAwareBackendFlow:
    def __init__(
        self,
        backend_flow: BackendFlow,
        package_planner: PackageDesignPlanner,
        formal_engine: FormalVerificationEngine,
        db: DesignDB,
    ):
        ...

    def run_package_aware_flow(
        self,
        design: str,
        package_spec: PackageSpec,
        constraints: dict,
    ) -> PackageAwareFlowResult:
        """执行考虑封装的后端流程"""
        ...

    def iter_floorplan_with_bump(
        self, floorplan: Floorplan
    ) -> FloorplanResult:
        """与bump assignment迭代的floorplan"""
        ...
```

---

### 6.15 Module 15: DFT (Design for Test)

#### 功能描述
提供完整的**可测试性设计（DFT）**能力，包括scan插入、ATPG、BIST、JTAG等，确保芯片制造后的可测试性和故障覆盖率。

#### 核心DFT功能

**A. Scan Chain Insertion**

```text
设计内容：
- Scan chain架构设计（scan compression: DFTMAX, JTAG, MBIST）
- Scan chain数量优化
- Scan chain长度均衡
- Scan chain ordering优化（timing-driven）
- Scan cell替换
- Scan enable同步
- Scan shift timing约束
- Scan test coverage预估
```

**B. ATPG (Automatic Test Pattern Generation)**

```text
设计内容：
- Stuck-at fault ATPG
- Transition fault ATPG
- Pattern compression（DFTMAX, X-compact）
- Pattern count优化
- Test time估算
- Test coverage分析
- Fault simulation
- Diagnostic pattern generation
```

**C. BIST (Built-In Self-Test)**

```text
设计内容：
- Logic BIST (LBIST)
- Memory BIST (MBIST)
- IO BIST
- BIST architecture设计
- BIST controller插入
- BIST timing约束
- BIST coverage分析
```

**D. JTAG / Boundary Scan**

```text
设计内容：
- JTAG controller插入
- Boundary scan cell插入
- TAP controller设计
- BSDL生成
- JTAG test coverage
```

**E. DFT-Aware Backend Flow**

```text
设计考虑：
- Scan chain routing congestion
- Scan timing closure (shift mode)
- Test mode clock tree
- Scan enable timing
- DFT area/power overhead
- Test pad planning
```

#### Python API

```python
class DFTEngine:
    def __init__(self, db: DesignDB):
        ...

    # Scan
    def analyze_scan_requirements(self) -> ScanRequirements:
        """分析scan需求：chain数量、coverage目标"""
        ...

    def insert_scan(
        self,
        strategy: str = "muxed",         # "muxed", "compressed", "partial"
        scan_chains: int = None,
        coverage_target: float = 0.95,
    ) -> ScanInsertionResult:
        """Scan插入"""
        ...

    def optimize_scan_chains(
        self,
        scan_result: ScanInsertionResult,
        objective: str = "timing",       # "timing", "area", "routing"
    ) -> ScanOptimization:
        """Scan chain优化"""
        ...

    def check_scan_timing(
        self, scan_result: ScanInsertionResult
    ) -> ScanTimingReport:
        """检查scan shift timing"""
        ...

    # ATPG
    def run_atpg(
        self,
        fault_model: str = "stuck_at",   # "stuck_at", "transition"
        coverage_target: float = 0.99,
    ) -> ATPGResult:
        """运行ATPG"""
        ...

    def estimate_test_time(
        self, atpg_result: ATPGResult
    ) -> TestTimeEstimate:
        """估算测试时间"""
        ...

    # BIST
    def insert_mbist(
        self,
        memories: list[MemoryInstance],
        algorithm: str = "march_c",
    ) -> MBISTResult:
        """Memory BIST插入"""
        ...

    def insert_lbist(
        self,
        coverage_target: float = 0.90,
    ) -> LBISTResult:
        """Logic BIST插入"""
        ...

    # DFT-Aware Backend
    def assess_dft_impact(
        self, design: DesignArtifact
    ) -> DFTImpactReport:
        """评估DFT对面积、功耗、timing的影响"""
        ...

    def plan_test_pads(
        self, dft_result: DFTResult
    ) -> TestPadPlan:
        """规划test pad"""
        ...
```

#### 工具适配

```python
class DFTToolAdapter(ABC):
    @abstractmethod
    def insert_scan(self, config: dict) -> ScanResult: ...
    @abstractmethod
    def run_atpg(self, config: dict) -> ATPGResult: ...
    @abstractmethod
    def insert_bist(self, config: dict) -> BISTResult: ...

class SynopsysDFTAdapter(DFTToolAdapter):
    """DFT Compiler, TetraMAX"""
    ...

class CadenceDFTAdapter(DFTToolAdapter):
    """Modus, Tessent"""
    ...

class SiemensDFTAdapter(DFTToolAdapter):
    """Tessent"""
    ...
```

---

### 6.16 Module 16: Low-Power Implementation

#### 功能描述
提供**低功耗设计实现**能力，基于UPF/CPF的power intent，实现power gating、retention、isolation、level shifting、multi-Vt等低功耗技术。

#### 核心低功耗技术

**A. Power Gating**

```text
设计内容：
- Power switch cell插入
- Power domain隔离
- Retention register插入
- Isolation cell插入
- Level shifter插入
- Always-on cell识别
- Retention/restore时序
- Power switch控制逻辑
- Inrush current控制
```

**B. Multi-Vt Optimization**

```text
设计内容：
- Vt assignment策略（LVT/HVT/ULVT/SLP）
- Timing-driven Vt swapping
- Power-driven Vt optimization
- Leakage power optimization
- Vt mix analysis
```

**C. Clock Gating**

```text
设计内容：
- Clock gating cell插入
- Integrated clock gating cell (ICG)
- Clock gating条件优化
- Gated clock tree
- Clock gating coverage分析
```

**D. DVFS (Dynamic Voltage Frequency Scaling)**

```text
设计内容：
- 多电压域设计
- Voltage/frequency level定义
- Voltage transition控制
- Performance monitor集成
- DVFS状态机
```

**E. UPF/CPF Implementation**

```text
实现内容：
- Power domain验证
- Supply net连接
- Power switch实现
- Isolation策略实现
- Retention策略实现
- Level shifter放置
- Always-on区域实现
```

#### Python API

```python
class LowPowerEngine:
    def __init__(self, db: DesignDB):
        ...

    def implement_power_intent(
        self,
        upf: DesignArtifact,
        strategy: str = "full",          # "full", "conservative", "aggressive"
    ) -> PowerIntentResult:
        """实现power intent（isolation, level shifter, retention）"""
        ...

    def insert_power_switches(
        self,
        power_domains: list[PowerDomain],
        switch_type: str = "footer",     # "footer", "header"
    ) -> PowerSwitchResult:
        """Power switch插入"""
        ...

    def insert_retention_cells(
        self,
        retention_strategy: str = "selective",   # "full", "selective"
    ) -> RetentionResult:
        """Retention register插入"""
        ...

    def insert_isolation_cells(
        self, power_domains: list[PowerDomain]
    ) -> IsolationResult:
        """Isolation cell插入"""
        ...

    def insert_level_shifters(
        self, domain_pairs: list[DomainPair]
    ) -> LevelShifterResult:
        """Level shifter插入"""
        ...

    def optimize_multi_vt(
        self,
        objective: str = "leakage",      # "leakage", "timing", "balanced"
        constraints: dict = None,
    ) -> MultiVtResult:
        """Multi-Vt优化"""
        ...

    def optimize_clock_gating(
        self,
        coverage_target: float = 0.80,
    ) -> ClockGatingResult:
        """Clock gating优化"""
        ...

    def analyze_power_state_machine(
        self, upf: DesignArtifact
    ) -> PowerStateReport:
        """分析power state machine"""
        ...

    def verify_power_intent(
        self,
        design: DesignArtifact,
        upf: DesignArtifact,
    ) -> PowerIntentVerification:
        """验证power intent实现"""
        ...

    def assess_power_overhead(
        self, power_result: PowerIntentResult
    ) -> PowerOverheadReport:
        """评估低功耗技术的面积/功耗/timing开销"""
        ...
```

#### 工具适配

```python
class LowPowerToolAdapter(ABC):
    @abstractmethod
    def implement_upf(self, config: dict) -> PowerIntentResult: ...
    @abstractmethod
    def optimize_multi_vt(self, config: dict) -> MultiVtResult: ...

class SynopsysLowPowerAdapter(LowPowerToolAdapter):
    """UPF implementation in FC/ICC2, PrimePower"""
    ...

class CadenceLowPowerAdapter(LowPowerToolAdapter):
    """CPF in Innovus, Joules, Voltus"""
    ...
```

---

### 6.17 Module 17: PDK & Design Rule Management

#### 功能描述
提供**PDK (Process Design Kit)和设计规则**的统一管理，将工艺信息纳入设计数据库，支撑所有物理设计阶段的设计规则检查。

#### PDK核心内容

**A. Technology Files**

```text
PDK组成：
- Technology LEF (tech LEF): 层定义、via定义、spacing规则
- Cell LEF: standard cell, IO cell, filler cell, tap cell, endcap cell物理信息
- Liberty (.lib): timing library, power library
- SPICE models: BSIM模型
- Technology file (.tf): Milkyway technology file
- Interconnect technology file (.itf): RC extraction参数
- DRC rule deck: Calibre SVRF, Assura rules
- LVS rule deck
- ERC (Electrical Rule Check) deck
- Antenna rule deck
```

**B. Design Rules Database**

```python
class DesignRuleDatabase:
    """设计规则数据库"""

    # Layer rules
    class LayerRule:
        layer_name: str
        min_width: float
        max_width: float
        min_spacing: float
        min_area: float
        min_enclosure: float
        direction: str                  # "horizontal", "vertical", "routing"
        resistance_per_sq: float
        capacitance_per_um: float

    # Via rules
    class ViaRule:
        via_name: str
        via_size: tuple[float, float]
        via_spacing: float
        via_enclosure: dict[str, float] # layer -> enclosure
        via_resistance: float
        via_current_limit: float

    # Antenna rules
    class AntennaRule:
        layer: str
        area_ratio_limit: float
        cum_area_ratio_limit: float
        side_area_ratio_limit: float
        diode_protection_factor: float

    # Density rules
    class DensityRule:
        layer: str
        min_density: float
        max_density: float
        window_size: float
        step_size: float

    # WPE (Well Proximity Effect) rules
    class WPERule:
        device_type: str
        min_distance: float
        stress_factor_model: Callable

    # LOD (Length of Diffusion) rules
    class LODRule:
        device_type: str
        sa_min: float                   # distance to STI edge
        sb_min: float
        sd_min: float
        stress_model: Callable

    # NDR (Non-Default Rules)
    class NDR:
        ndr_name: str
        width_multiplier: float
        spacing_multiplier: float
        applicable_layers: list[str]
```

**C. PDK Version Management**

```python
class PDKVersion:
    pdk_id: str
    foundry: str
    process_node: str                   # "28nm", "16nm", "7nm", "5nm", "3nm"
    version: str
    release_date: str
    changelog: str
    tech_lef: DesignArtifact
    cell_lef: list[DesignArtifact]
    liberty_libs: list[DesignArtifact]
    spice_models: list[DesignArtifact]
    drc_deck: DesignArtifact
    lvs_deck: DesignArtifact
    metal_stack: MetalStack
    supported_options: list[str]        # "multi_vt", "rf", "mim_cap", ...
```

**D. Metal Stack Definition**

```python
class MetalStack:
    layers: list[MetalLayer]
    default_track_pattern: dict
    preferred_routing_direction: dict
    min_pitch: dict
    metal_fill_rules: dict

class MetalLayer:
    name: str
    layer_type: str                     # "routing", "pad", "rdl"
    thickness: float
    min_width: float
    min_spacing: float
    pitch: float
    direction: str
    sheet_resistance: float
    cap_per_um: float
    current_density_limit: float
    is_prerouting: bool
```

#### Python API

```python
class PDKManager:
    def __init__(self, db: DesignDB):
        ...

    def register_pdk(
        self,
        pdk_path: str,
        foundry: str,
        process_node: str,
        version: str,
    ) -> PDKVersion:
        """注册PDK版本"""
        ...

    def get_tech_lef(
        self, pdk_id: str
    ) -> TechLEF:
        """获取technology LEF"""
        ...

    def get_cell_lef(
        self, pdk_id: str, cell_type: str = "standard"
    ) -> CellLEF:
        """获取cell LEF"""
        ...

    def get_liberty_lib(
        self, pdk_id: str, corner: str
    ) -> LibertyLib:
        """获取Liberty library"""
        ...

    def get_design_rules(
        self, pdk_id: str
    ) -> DesignRuleDatabase:
        """获取设计规则数据库"""
        ...

    def check_drc(
        self,
        layer: str,
        object: LayoutObject,
        pdk_id: str,
    ) -> list[DRCViolation]:
        """本地DRC检查（快速，不依赖Calibre）"""
        ...

    def get_metal_stack(
        self, pdk_id: str
    ) -> MetalStack:
        """获取metal stack信息"""
        ...

    def get_antenna_rules(
        self, pdk_id: str
    ) -> AntennaRules:
        """获取antenna规则"""
        ...

    def get_density_rules(
        self, pdk_id: str
    ) -> DensityRules:
        """获取density规则"""
        ...

    def query_rule(
        self,
        rule_type: str,
        layer: str = None,
        pdk_id: str = None,
    ) -> DesignRule:
        """查询特定设计规则"""
        ...
```

---

### 6.18 Module 18: SI Sign-off & Reliability Analysis

#### 功能描述
提供**Signal Integrity (SI)**和**Reliability**的sign-off分析能力，确保设计在真实工作条件下的信号完整性和长期可靠性。

#### SI Sign-off

**A. Crosstalk Analysis**

```text
分析内容：
- Glitch analysis（crosstalk-induced glitch）
- Delta delay analysis（crosstalk-induced delay）
- Victim/aggressor identification
- Crosstalk hotspot detection
- Shielding requirement analysis
- Spacing recommendation for critical nets
```

**B. SI-Aware STA**

```text
STA考虑：
- OCV (On-Chip Variation)
- AOCV / POCV derating
- SOCV (Statistical OCV)
- CPPR (Common Path Pessimism Removal)
- PBA (Path-Based Analysis) vs GBA (Graph-Based Analysis)
- SI-adjusted timing
- Crosstalk delay integration
```

**C. SI Fix**

```text
修复策略：
- Net shielding
- Spacing increase
- Layer promotion
- Buffer insertion（for delay fix）
- Driver sizing
- Slew rate control
```

#### Reliability Analysis

**A. HCI (Hot Carrier Injection)**

```text
分析内容：
- HCI degradation模型
- Transistor lifetime估算
- High-stress node identification
- HCI-aware design margin
```

**B. NBTI (Negative Bias Temperature Instability)**

```text
分析内容：
- NBTI degradation模型
- PMOS transistor aging
- Timing degradation over lifetime
- NBTI-aware signoff margin
```

**C. TDDB (Time-Dependent Dielectric Breakdown)**

```text
分析内容：
- Gate oxide breakdown模型
- Voltage acceleration factor
- BEOL TDDB (via/interconnect)
- Lifetime estimation
```

**D. EM (Electromigration) Reliability**

```text
分析内容：
- Metal EM lifetime
- Via EM lifetime
- Temperature-dependent EM
- RMS/average current vs peak current
- EM margin analysis
```

#### Python API

```python
class SIAnalyzer:
    def __init__(self, db: DesignDB):
        ...

    def run_crosstalk_analysis(
        self, design: DesignArtifact
    ) -> CrosstalkReport:
        """Crosstalk分析"""
        ...

    def detect_si_hotspots(
        self, ct_report: CrosstalkReport
    ) -> list[SIHotspot]:
        """检测SI热点"""
        ...

    def run_si_aware_sta(
        self,
        design: DesignArtifact,
        derating_scheme: str = "AOCV",
    ) -> SI_STAReport:
        """SI-aware STA"""
        ...

    def suggest_si_fixes(
        self, hotspot: SIHotspot
    ) -> list[SIFix]:
        """建议SI修复"""
        ...

    def compare_derating_schemes(
        self,
        schemes: list[str] = ["OCV", "AOCV", "POCV", "SOCV"],
    ) -> DeratingComparison:
        """比较不同derating scheme"""
        ...


class ReliabilityAnalyzer:
    def __init__(self, db: DesignDB):
        ...

    def analyze_hci(
        self, design: DesignArtifact, lifetime: float = 10.0  # years
    ) -> HCIReport:
        """HCI分析"""
        ...

    def analyze_nbti(
        self, design: DesignArtifact, lifetime: float = 10.0
    ) -> NBTIReport:
        """NBTI分析"""
        ...

    def analyze_tddb(
        self, design: DesignArtifact, lifetime: float = 10.0
    ) -> TDDBReport:
        """TDDB分析"""
        ...

    def analyze_em_reliability(
        self, design: DesignArtifact, lifetime: float = 10.0
    ) -> EMReliabilityReport:
        """EM可靠性分析（含lifetime估算）"""
        ...

    def estimate_timing_degradation(
        self,
        reliability_reports: list,
        lifetime: float = 10.0,
    ) -> TimingDegradation:
        """估算lifetime内的timing退化"""
        ...

    def recommend_reliability_margin(
        self,
        target_lifetime: float,
        operating_conditions: dict,
    ) -> ReliabilityMargin:
        """推荐reliability margin"""
        ...
```

---

### 6.19 Module 19: Chip Finishing & Tapeout Preparation

#### 功能描述
提供**芯片后处理（chip finishing）和tapeout准备**的完整能力，确保设计满足foundry的所有tapeout要求。

#### Chip Finishing

**A. Filler Cell Insertion**

```text
设计内容：
- Filler cell插入（gap filling）
- Filler cell类型选择（small/medium/large）
- Filler cell连接（VDD/VSS）
- Filler cell DRC检查
- Metal fill exclusion区域
```

**B. Metal Fill**

```text
设计内容：
- Metal fill插入（density filling）
- Float fill vs stitch fill
- Fill pattern generation
- Fill density verification
- Fill DRC检查
- Fill impact on parasitics
```

**C. Seal Ring**

```text
设计内容：
- Seal ring insertion（chip boundary保护）
- Seal ring corner处理
- Seal ring DRC检查
- Seal ring与PAD ring连接
```

**D. GDS Preparation**

```text
设计内容：
- GDS merge（design + IO ring + seal ring + IP）
- GDS cleanup（hierarchy flatten, cell merge）
- GDS layer mapping
- GDS boundary box
- GDS foundry check
```

#### Tapeout Preparation

**A. Final Verification Checklist**

```text
验证项：
- STA sign-off（all corners, all modes）
- Power analysis sign-off
- EMIR sign-off
- DRC clean
- LVS clean
- ERC clean
- Antenna clean
- Density clean
- Functional simulation pass
- Formal verification pass（LEC, CDC, UPF）
- Reliability sign-off
- Timing closure across all ECOs
- Design rule exception (DRE) review
- Waiver review and approval
```

**B. Foundry Deliverables**

```text
交付物：
- GDSII/OASIS（final layout）
- Tapeout checklist
- Design rule exception (DRE) report
- Waiver list
- Simulation report
- Timing report
- Power report
- EMIR report
- Reliability report
- Test coverage report
- Package drawing
- Bonding diagram (if applicable)
```

**C. Tapeout Milestone**

```text
Tapeout流程：
- Pre-tapeout review
- DRE (Design Rule Exception) meeting
- Waiver approval
- Final GDS submission
- Foundry acknowledgment
- Tapeout freeze
```

#### Python API

```python
class ChipFinishingEngine:
    def __init__(self, db: DesignDB):
        ...

    def insert_filler_cells(
        self, design: DesignArtifact
    ) -> FillerResult:
        """Filler cell插入"""
        ...

    def insert_metal_fill(
        self, design: DesignArtifact
    ) -> MetalFillResult:
        """Metal fill插入"""
        ...

    def insert_seal_ring(
        self, design: DesignArtifact
    ) -> SealRingResult:
        """Seal ring插入"""
        ...

    def merge_gds(
        self,
        design_gds: DesignArtifact,
        io_gds: DesignArtifact,
        seal_ring_gds: DesignArtifact,
        ip_gds: list[DesignArtifact],
    ) -> MergedGDS:
        """GDS merge"""
        ...

    def run_gds_cleanup(
        self, gds: MergedGDS
    ) -> CleanedGDS:
        """GDS cleanup"""
        ...


class TapeoutManager:
    def __init__(self, db: DesignDB):
        ...

    def run_tapeout_checklist(
        self, design_id: str
    ) -> TapeoutChecklist:
        """运行tapeout checklist"""
        ...

    def generate_dre_report(
        self, design_id: str
    ) -> DREReport:
        """生成DRE (Design Rule Exception)报告"""
        ...

    def generate_waiver_report(
        self, design_id: str
    ) -> WaiverReport:
        """生成waiver报告"""
        ...

    def prepare_foundry_deliverables(
        self, design_id: str
    ) -> list[DesignArtifact]:
        """准备foundry交付物"""
        ...

    def freeze_tapeout(
        self, design_id: str, tag: str
    ) -> TapeoutFreeze:
        """Tapeout freeze（打tag，锁定设计）"""
        ...
```

---

### 6.20 Module 20: Test & Yield Analysis

#### 功能描述
提供**测试策略分析**和**良率（yield）分析**能力，从设计阶段开始就考虑可测试性和良率优化，并将硅后测试结果反馈到设计流程。

#### Test Analysis

**A. Test Strategy Planning**

```text
分析内容：
- 测试覆盖率目标设定（stuck-at, transition）
- 测试时间估算
- ATPG pattern count预估
- Scan chain架构选择
- BIST覆盖率评估
- Memory test策略（MBIST算法选择）
- IO test策略（boundary scan, JTAG）
- Test cost分析
```

**B. Testability Analysis**

```text
分析内容：
- Controllability分析
- Observability分析
- Testability hotspot识别
- Untestable path分析
- ATPG coverage瓶颈定位
- Scan compression效率评估
```

**C. Post-Silicon Test Correlation**

```text
分析内容：
- Silicon test result导入
- Test coverage vs simulated coverage对比
- Fail log分析
- Yield correlation with design metrics
- Test escape analysis
```

#### Yield Analysis

**A. Yield Modeling**

```python
class YieldModel:
    """良率模型"""
    model_type: str           # "Poisson", "Murphy", "Seed", "Negative_Binomial"
    defect_density: float     # defects per cm^2
    critical_area: float      # cm^2
    systematic_yield: float   # 系统良率（非随机缺陷）
    random_yield: float       # 随机缺陷良率
```

**B. Critical Area Analysis**

```text
分析内容：
- Layer-specific critical area
- Via critical area
- Spacing-related yield loss
- Width-related yield loss
- Design rule violation impact on yield
- Layout density impact on yield
```

**C. Design-for-Yield (DFY)**

```text
优化策略：
- Critical spacing increase
- Redundant via insertion
- Via enclosure increase
- Wire widening for critical nets
- Cell selection for yield (larger spacing cells)
- Pattern density optimization
- CMP-aware design
```

**D. Yield Learning from Silicon**

```text
分析内容：
- Silicon test yield data导入
- Yield map分析（wafer map, lot map）
- Spatial correlation分析
- Defect Pareto分析
- Process window correlation
- Design vs process interaction
```

#### Python API

```python
class TestAnalyzer:
    def __init__(self, db: DesignDB):
        ...

    def plan_test_strategy(
        self,
        design: DesignArtifact,
        coverage_target: float = 0.99,
    ) -> TestStrategy:
        """制定测试策略"""
        ...

    def analyze_testability(
        self, design: DesignArtifact
    ) -> TestabilityReport:
        """可测试性分析"""
        ...

    def estimate_test_time(
        self, test_strategy: TestStrategy
    ) -> TestTimeEstimate:
        """估算测试时间"""
        ...

    def analyze_atpg_bottleneck(
        self, atpg_result: ATPGResult
    ) -> ATPGBottleneck:
        """ATPG覆盖率瓶颈分析"""
        ...

    def correlate_silicon_test(
        self,
        simulated: ATPGResult,
        silicon: SiliconTestResult,
    ) -> TestCorrelation:
        """硅后测试与仿真对比"""
        ...


class YieldAnalyzer:
    def __init__(self, db: DesignDB):
        ...

    def model_yield(
        self,
        design_area: float,
        defect_density: float,
        model_type: str = "Murphy",
    ) -> YieldEstimate:
        """良率建模"""
        ...

    def critical_area_analysis(
        self, design: DesignArtifact
    ) -> CriticalAreaReport:
        """Critical area分析"""
        ...

    def identify_yield_risk(
        self, design: DesignArtifact
    ) -> list[YieldRisk]:
        """识别良率风险点"""
        ...

    def suggest_dfy_optimizations(
        self, risks: list[YieldRisk]
    ) -> list[DFYOptimization]:
        """建议DFY优化"""
        ...

    def analyze_wafer_yield_map(
        self, wafer_data: WaferTestData
    ) -> WaferYieldAnalysis:
        """Wafer yield map分析"""
        ...

    def learn_from_silicon(
        self,
        silicon_results: list[SiliconTestResult],
        design_metrics: dict,
    ) -> YieldInsight:
        """从硅后数据学习良率规律"""
        ...

    def predict_next_gen_yield(
        self,
        design_features: dict,
        historical_data: list[YieldData],
    ) -> YieldPrediction:
        """预测下一代设计良率"""
        ...
```

---

### 6.21 Module 21: Design Lifecycle Management

#### 功能描述
提供**设计全生命周期管理**能力，从架构设计到硅后验证、产品维护的完整管理，包括版本演进、工程变更、产品生命周期跟踪。

#### Lifecycle Stages

**A. Design Phase Management**

```text
阶段定义：
- Architecture / Specification
- RTL Design
- Logic Synthesis
- Physical Design (Floorplan, PnR)
- Sign-off Verification
- Tapeout
- Silicon Bring-up
- Production
- End-of-Life (EOL)

每个阶段的：
- Entry criteria
- Exit criteria
- Deliverables
- Quality gates
- Approval requirements
```

**B. Engineering Change Management**

```text
变更类型：
- Functional ECO
- Timing ECO
- Metal ECO
- Test ECO
- Yield improvement ECO
- Bug fix ECO
- Foundry request ECO

变更流程：
- Change request (CR)
- Impact analysis
- Approval workflow
- Implementation
- Verification
- Regression testing
- Deployment
```

**C. Product Lifecycle Tracking**

```text
跟踪内容：
- Design revision history
- Silicon revision history
- Test program version
- Package version
- Characterization data
- Reliability data
- Field return analysis
- Failure analysis (FA) data
```

**D. Design Reuse & Derivative**

```text
管理能力：
- Design variant管理
- IP version管理
- Configuration management
- Derivative tracking
- Commonality analysis
```

#### Python API

```python
class LifecycleManager:
    def __init__(self, db: DesignDB):
        ...

    def define_lifecycle_stages(
        self, design_id: str
    ) -> LifecycleDefinition:
        """定义设计生命周期阶段"""
        ...

    def transition_stage(
        self,
        design_id: str,
        from_stage: str,
        to_stage: str,
        approval: list[str],
    ) -> StageTransition:
        """阶段转换（需审批）"""
        ...

    def create_change_request(
        self,
        design_id: str,
        change_type: str,
        description: str,
        impact_analysis: dict,
    ) -> ChangeRequest:
        """创建工程变更请求"""
        ...

    def approve_change(
        self,
        cr_id: str,
        approvers: list[str],
    ) -> ChangeApproval:
        """审批变更请求"""
        ...

    def implement_change(
        self,
        cr_id: str,
        implementation: ECOPlan,
    ) -> ChangeImplementation:
        """实施变更"""
        ...

    def track_product_lifecycle(
        self, product_id: str
    ) -> ProductLifecycle:
        """跟踪产品生命周期"""
        ...

    def analyze_field_returns(
        self, product_id: str
    ) -> FieldReturnAnalysis:
        """分析现场退货数据"""
        ...

    def manage_design_variant(
        self,
        base_design: str,
        variant_config: dict,
    ) -> DesignVariant:
        """管理设计变体"""
        ...
```

---

### 6.22 Module 22: Design Pattern Analysis & Knowledge Base

#### 功能描述
提供**设计模式分析**和**知识库**能力，从历史设计项目中提取成功模式，形成可复用的设计知识，反馈到当前设计流程。

#### Design Pattern Analysis

**A. Timing Pattern Mining**

```text
分析内容：
- Critical path topology模式
- Common timing bottleneck模式
- Successful fix patterns
- Timing closure recipe
- RTL coding pattern vs timing correlation
```

```python
class TimingPattern:
    pattern_id: str
    description: str
    topology_signature: str        # path topology特征
    root_cause: str
    typical_slack_range: tuple[float, float]
    recommended_fix: str
    success_rate: float
    applicable_scenarios: list[str]
```

**B. Floorplan Pattern Mining**

```text
分析内容：
- Successful floorplan patterns
- Module placement patterns
- Macro placement patterns
- Connectivity-driven placement patterns
- Congestion-aware patterns
```

**C. Power Pattern Mining**

```text
分析内容：
- Power reduction patterns
- Clock gating patterns
- Power domain patterns
- Multi-Vt optimization patterns
- Leakage reduction recipes
```

**D. EMIR Pattern Mining**

```text
分析内容：
- IR hotspot patterns
- EM violation patterns
- Power grid patterns
- Decap placement patterns
- Successful EMIR fix patterns
```

**E. DRC/LVS Pattern Mining**

```text
分析内容：
- Common DRC violation patterns
- Recurring LVS issues
- Successful DRC fix patterns
- Layout patterns causing violations
```

#### Knowledge Base

**A. Best Practices**

```text
知识类型：
- 工艺节点最佳实践
- Library使用最佳实践
- 工具参数最佳实践
- Constraint设置最佳实践
- ECO最佳实践
- Sign-off最佳实践
```

**B. Troubleshooting Guide**

```text
知识类型：
- 常见问题诊断流程
- 错误代码解释
- 修复方案索引
- 工具warning处理
- Corner case处理
```

**C. Design Rule Templates**

```text
知识类型：
- 各工艺节点设计规则模板
- 设计规则检查清单
- 例外处理模板
- Waiver审批模板
```

**D. Expert Experience**

```text
知识类型：
- 专家设计评审意见
- 历史项目经验总结
- 失败案例分析
- 成功案例分析
```

#### Python API

```python
class DesignPatternAnalyzer:
    def __init__(self, db: DesignDB):
        ...

    def mine_timing_patterns(
        self,
        designs: list[DesignArtifact],
        min_support: int = 3,
    ) -> list[TimingPattern]:
        """挖掘timing模式"""
        ...

    def mine_floorplan_patterns(
        self,
        designs: list[DesignArtifact],
        min_support: int = 3,
    ) -> list[FloorplanPattern]:
        """挖掘floorplan模式"""
        ...

    def mine_power_patterns(
        self,
        designs: list[DesignArtifact],
    ) -> list[PowerPattern]:
        """挖掘power模式"""
        ...

    def mine_emir_patterns(
        self,
        designs: list[DesignArtifact],
    ) -> list[EMIRPattern]:
        """挖掘EMIR模式"""
        ...

    def mine_drc_patterns(
        self,
        designs: list[DesignArtifact],
    ) -> list[DRCPattern]:
        """挖掘DRC模式"""
        ...

    def match_pattern(
        self,
        current_issue: DesignIssue,
        patterns: list,
    ) -> list[PatternMatch]:
        """匹配当前问题与历史模式"""
        ...


class KnowledgeBase:
    def __init__(self, db: DesignDB):
        ...

    def add_best_practice(
        self,
        category: str,
        content: str,
        tags: list[str],
        author: str,
    ) -> KnowledgeEntry:
        """添加最佳实践"""
        ...

    def add_troubleshooting(
        self,
        problem: str,
        diagnosis: str,
        solution: str,
        tags: list[str],
    ) -> TroubleshootingEntry:
        """添加troubleshooting条目"""
        ...

    def search_knowledge(
        self,
        query: str,
        category: str = None,
        tags: list[str] = None,
    ) -> list[KnowledgeEntry]:
        """搜索知识库"""
        ...

    def get_recommended_practices(
        self,
        context: dict,              # 当前设计上下文
    ) -> list[KnowledgeEntry]:
        """基于上下文推荐最佳实践"""
        ...

    def learn_from_project(
        self,
        project_id: str,
        lessons_learned: list,
    ):
        """从项目经验中学习"""
        ...

    def export_knowledge(
        self,
        format: str = "markdown",
    ) -> str:
        """导出知识库"""
        ...
```

#### 知识反馈到设计流程

```text
设计流程反馈机制：

1. Constraint设置阶段
   → 查询历史项目的constraint最佳实践
   → 推荐合适的uncertainty设置
   → 推荐false path / multicycle path模式

2. 综合优化阶段
   → 匹配timing pattern，推荐修复策略
   → 推荐compile_ultra参数组合

3. Floorplan阶段
   → 推荐成功的floorplan pattern
   → 基于历史数据预估congestion风险

4. ECO阶段
   → 匹配类似问题，推荐修复方案
   → 预估ECO成功率

5. Sign-off阶段
   → 推荐sign-off checklist
   → 推荐waiver审批经验

6. Post-silicon阶段
   → 分析silicon数据，更新yield模型
   → 提取经验反馈到知识库
```

---

## 7. 补充核心能力

## 7. 补充核心能力

### 7.1 Constraint / Intent Versioning

每一次SDC、UPF、floorplan、macro placement、ECO都要版本化。记录：
1. 修改原因
2. 修改者
3. agent推理
4. QoR前后变化
5. 是否回滚
6. 是否tapeout-safe

### 7.2 QoR Regression System

每个action必须自动比较：
```text
WNS / TNS / violating paths / area / cell count / buffer count
leakage / dynamic power / congestion / DRC count / LVS status
IR drop / EM violation / runtime / memory
```

并判断：`accepted / rejected / needs human review`

### 7.3 Formal / LEC Integration

后端ECO必须检查功能等价：
1. synthesis后RTL vs netlist
2. ECO前后netlist
3. scan insertion前后
4. low-power insertion后
5. metal ECO后

**没有LEC，agent不能自动接受逻辑ECO。**

### 7.4 CDC / RDC / Low-power Awareness

后端agent不能只看STA，需要理解：
1. CDC (Clock Domain Crossing)
2. Reset domain crossing
3. Isolation
4. Level shifter
5. Retention
6. Power switch
7. Always-on cell
8. Clock gating
9. Generated clock
10. Test mode clock

### 7.5 ECO Planning（分级）

```text
Level 0: report / diagnosis only
Level 1: safe physical ECO（自动执行）
Level 2: timing ECO with tool guidance（自动执行）
Level 3: netlist ECO requiring LEC（需人工确认）
Level 4: RTL feedback（需RTL owner确认）
Level 5: architecture-level change（需架构师确认）
```

### 7.6 Knowledge Base

沉淀：
1. 工艺节点规则
2. library特性
3. macro使用经验
4. 常见DRC/LVS修复
5. 常见timing pattern
6. 常见floorplan pattern
7. 工具warning/error
8. 项目历史QoR
9. 人工专家修复记录

---

## 8. Agent 形态设计

### 8.1 多Agent架构

不做"大agent"，而是多个专业agent：

```text
1.  Flow Orchestrator Agent
2.  Constraint Agent
3.  Synthesis QoR Agent
4.  Timing Diagnosis Agent
5.  RTL Insight Agent
6.  Floorplan Agent
7.  Macro Placement Agent
8.  Placement/Congestion Agent
9.  CTS Agent
10. Routing Agent
11. Power Agent
12. EMIR Agent
13. Signoff STA Agent
14. DRC/LVS Agent
15. ECO Agent
16. Report Writer Agent
17. Task Scheduler Agent          # 任务拆分、调度、资源管理
18. Log Monitor Agent             # 日志分析、异常检测、告警
19. Version Control Agent         # 设计版本管理、血缘追踪、release管理
20. Formal Verification Agent     # LEC、Property Check、CDC/RDC、Power Intent验证
21. Package Design Agent          # PAD/Bump/RDL设计、封装协同优化
22. DFT Agent                     # Scan插入、ATPG、BIST、JTAG
23. Low-Power Agent               # UPF/CPF实现、power gating、multi-Vt
24. PDK Manager Agent             # PDK管理、设计规则查询
25. SI/Reliability Agent          # SI sign-off、reliability分析
26. Tapeout Agent                 # Chip finishing、tapeout checklist、GDS merge
27. Test & Yield Agent            # 测试策略、良率分析、silicon correlation
28. Lifecycle Agent               # 设计生命周期管理、工程变更、产品跟踪
29. Knowledge Agent               # 设计模式挖掘、知识库管理、最佳实践推荐
```

### 8.2 Agent 协作示例

```text
用户目标：
"这个block 800MHz收敛，面积不能超过0.8mm²，功耗尽量低。"

Flow Orchestrator:
  → Constraint Agent 检查 SDC
  → Synthesis Agent 生成 3 组策略
  → Timing Agent 聚类 critical path
  → Floorplan Agent 生成 partition
  → Macro Agent 规划 SRAM
  → Place Agent 运行 place_opt
  → STA Agent 分析 post-place timing
  → ECO Agent 生成修复
  → Power/EMIR Agent 检查副作用
  → Report Agent 输出决策报告
```

---

## 9. 技术实现要点

### 9.1 数据解析引擎

| 格式 | 解析能力 | 说明 |
|------|----------|------|
| **Verilog/VHDL** | RTL结构解析 | 层次、实例化、端口、参数 |
| **Liberty (.lib)** | 完整timing/power模型解析 | NLDM, CCS, ECSM; 包含lookup table |
| **LEF** | Technology LEF + Cell LEF | 层定义、via定义、cell物理信息 |
| **DEF** | 布局布线数据 | Component, pin, net, via, region, group |
| **SDC** | 约束完整解析 | 所有标准SDC命令 |
| **UPF/CPF** | Power intent | Power domain, supply net, isolation, level shifter |
| **SPEF** | Parasitic数据 | R/C网络，reduced model |
| **SDF** | Timing annotation | Interconnect + cell delay |
| **SAIF/VCD/FSDB** | Activity数据 | Switching activity |
| **DDC** | DC/ICC2数据库 | Synopsys API或自定义解析 |
| **Calibre SVRF** | DRC/LVS规则 | Rule deck解析 |

### 9.2 算法引擎

| 算法类别 | 实现技术 |
|----------|----------|
| **图算法** | NetworkX-based timing graph分析，BFS/DFS/Dijkstra |
| **优化求解** | SCIP/Gurobi for LP/ILP; NSGA-II for MOO; simulated annealing |
| **ML模型** | scikit-learn / PyTorch for timing/power prediction |
| **几何算法** | Shapely/Clipper for physical layout operations |
| **并行计算** | multiprocessing / ray for multi-corner analysis |

### 9.3 性能考虑

| 场景 | 策略 |
|------|------|
| **大规模netlist (>10M cells)** | 增量分析、层次化分析、按需加载 |
| **Multi-corner分析** | 并行计算、共享timing graph |
| **设计空间探索** | 代理模型（surrogate model）、early termination |
| **DRC/LVS** | Violation聚类、优先级处理、增量检查 |

---

## 10. 关键技术难点

### 10.1 数据关联难

最大难点：`RTL → netlist → physical → timing → power → EMIR → DRC/LVS` 之间的名字变化、层次变化、优化变化。

解决方案：
1. 保存name mapping
2. 综合时限制过度flatten
3. 使用guide file
4. 建立fuzzy matching
5. 利用formal / equivalence mapping
6. 保存每阶段design snapshot

### 10.2 Agent 不能 hallucinate

后端设计不能接受"看起来合理"的建议。所有建议必须绑定证据：

```text
证据：
- report_timing path id
- instance list
- slack
- physical distance
- congestion map
- power density
- DRC bbox
- before/after QoR
```

### 10.3 自动修复必须有安全边界

```text
只读诊断
可回滚物理 ECO
需要人工确认的逻辑 ECO
需要 RTL owner 确认的 pipeline 修改
禁止自动执行的 signoff-risk 操作
```

---

## 11. 典型工作流

### 11.1 综合策略探索

```text
输入 RTL + SDC + library
  → 检查 SDC
  → 生成综合策略组
  → 运行 DC/Genus/Fusion
  → 解析 QoR
  → 路径聚类
  → 判断 trade-off
  → 输出推荐策略
```

### 11.2 RTL + 综合结果驱动 floorplan

```text
RTL hierarchy
  → netlist module area
  → critical path module crossing
  → macro connectivity
  → IO pin relation
  → power/clock domain
  → 生成 module connectivity graph
  → floorplan partition proposal
  → macro placement proposal
```

### 11.3 Post-place timing feedback

```text
post-place STA
  → 与 synthesis STA 对比
  → 识别恶化路径
  → 映射到 physical region
  → 判断 cell dominated / net dominated / congestion dominated
  → 生成 ECO / floorplan / RTL pipeline 建议
```

### 11.4 Sign-off closure

```text
post-route design
  → PrimeTime/Tempus signoff STA
  → Power analysis
  → EMIR analysis
  → DRC/LVS
  → Violation clustering
  → ECO proposal
  → Apply ECO
  → STA/Power/EMIR/DRC/LVS regression
```

---

## 12. 实施路线图

### Phase 0：基础框架 (Month 1-2)

**目标**：工具封装、数据流、报告解析、任务调度基础跑通

- [ ] Python flow framework
- [ ] DC/Genus synthesis adapter
- [ ] ICC2/Innovus place/route adapter
- [ ] PrimeTime/Tempus STA adapter
- [ ] Report parser（核心格式）
- [ ] 最小可用数据库（10张核心表）
- [ ] Run database + QoR dashboard
- [ ] **任务拆分引擎基础版（Task Decomposer）**
- [ ] **基础日志解析器（Log Parser）**
- [ ] **Git集成基础（脚本/代码版本管理）**
- [ ] LLM report summarizer

**输出**：自动跑flow → 自动收集report → 自动生成QoR summary → 自动比较不同run → 基础进度跟踪

### Phase 1：综合和时序诊断 (Month 3-4)

**最容易体现"硬核"的第一阶段**

- [ ] SDC checker（Constraint Consistency Analyzer）
- [ ] Synthesis strategy explorer
- [ ] Timing path parser
- [ ] Path clustering
- [ ] RTL hierarchy correlation
- [ ] Timing root-cause classifier
- [ ] Synthesis trade-off recommender
- [ ] **任务调度器完善（依赖DAG、并行多corner）**
- [ ] **日志异常检测（runtime/memory anomaly detection）**
- [ ] **进度可视化（Gantt图、依赖图）**
- [ ] **运行时间预估模型**

### Phase 2：Floorplan / Macro Planning (Month 5-7)

- [ ] Module connectivity graph
- [ ] Macro connectivity graph
- [ ] Floorplan partition proposal
- [ ] Macro placement scoring
- [ ] IO pin assignment suggestion
- [ ] Congestion risk estimation
- [ ] Early power grid risk estimation
- [ ] **设计版本管理完善（design commit/diff/tag/branch）**
- [ ] **大型设计数据库引用管理（DB name/cell name）**
- [ ] **版本血缘追踪（artifact lineage）**

### Phase 3：Post-place / Post-route Closure (Month 8-10)

- [ ] Placement timing evolution tracker
- [ ] Congestion-aware timing diagnosis
- [ ] CTS issue analyzer
- [ ] Routing detour analyzer
- [ ] ECO planner（分级）
- [ ] Pipeline feedback generator
- [ ] Side-effect checker
- [ ] QoR regression system
- [ ] **Formal Verification基础：LEC集成（RTL vs netlist, ECO前后）**
- [ ] **Incremental LEC支持**
- [ ] **Flow脚本版本管理（脚本版本diff/replay）**
- [ ] **里程碑tag管理（tapeout、signoff_approved）**

### Phase 4：Sign-off STA / Power / EMIR (Month 11-14)

- [ ] PrimeTime/Tempus signoff report parser
- [ ] SI/OCV/PBA analysis
- [ ] Power breakdown + clock power analyzer
- [ ] Voltus/RedHawk/PrimeRail EMIR parser
- [ ] IR hotspot root-cause analyzer
- [ ] EM fixing advisor
- [ ] Signoff ECO regression
- [ ] **Formal Verification完善：Property Check, CDC/RDC, Power Intent验证**
- [ ] **ECO安全评估（执行前LEC风险预估）**
- [ ] **PAD/Bump Planning基础：IO分析, bump需求估算, power/ground bump分配**
- [ ] **Release管理（完整artifacts集合的tagged release）**
- [ ] **审计轨迹（谁在什么时候做了什么变更）**

### Phase 5：DRC/LVS Fixing (Month 15-18)

- [ ] DRC report parser
- [ ] Violation clustering + type classifier
- [ ] Layout object correlation
- [ ] Repeated violation pattern mining
- [ ] LVS mismatch classifier
- [ ] Fixing candidate generation
- [ ] Tool-assisted patch flow
- [ ] Knowledge base accumulation
- [ ] **RDL Routing规划**
- [ ] **Bump/RDL DRC检查**
- [ ] **Package co-optimization（与封装设计协同）**
- [ ] **知识库版本化（best practices、troubleshooting经验版本管理）**

### Phase 6：扩展能力 (Month 19-24)

- [ ] **Formal Verification高级：Model Checking, abstraction策略**
- [ ] **Advanced PAD placement（wirebond, probe pad, ESD）**
- [ ] **High-speed IO bump placement（impedance control）**
- [ ] **Thermal-aware bump distribution**
- [ ] **Package parasitic estimation integration**
- [ ] **2.5D/3D IC support（TSV, micro-bump）**

---

## 13. 优先级排序

### 最高优先级（第一优先级）

**Timing Path Root Cause Analyzer** — 直接支撑综合修复、floorplan、post-place ECO、pipeline feedback、sign-off closure。

### 第二优先级

**Module Connectivity Graph** — 支撑floorplan、macro placement、partition、IO planning、timing-aware physical design。

### 第三优先级

**Constraint Analyzer** — 很多timing问题本质是SDC问题。

### 第四优先级

**QoR Regression DB** — 没有前后对比，agent的建议不可验证。

### 第五优先级

**EMIR Hotspot Root Cause Analyzer** — 先进工艺中power integrity往往比普通timing ECO更难后期修。

---

## 14. 风险与挑战

| 风险 | 影响 | 缓解策略 |
|------|------|----------|
| **工具版本差异** | 不同版本命令/参数/输出格式不同 | 抽象层+版本适配矩阵 |
| **大规模设计性能** | 10M+ cells分析耗时巨大 | 增量分析、层次化、分布式计算 |
| **Foundry rule复杂度** | 不同foundry/节点DRC规则差异巨大 | 规则模板化+foundry-specific adapter |
| **数据准确性** | 解析器正确性直接影响分析结果 | 全面单元测试+对标工具原生结果 |
| **工具license** | 分析引擎应避免不必要工具调用 | 本地分析优先，工具调用按需 |
| **工艺IP保密** | 工艺参数和规则属于foundry IP | 安全的数据隔离和访问控制 |
| **数据关联** | 跨阶段名字/层次变化 | name mapping + guide file + formal mapping |
| **Agent幻觉** | 后端不能接受"看起来合理"的建议 | 所有建议绑定证据链 |

---

## 15. 交付物清单

```text
backend_agent/
 ├── flows/
 │    ├── synopsys/           # DC / FC / ICC2 / PT / PrimePower
 │    ├── cadence/            # Genus / Innovus / Tempus / Voltus
 │    └── siemens/            # Calibre
 ├── parsers/
 │    ├── timing/             # STA report parser
 │    ├── qor/                # QoR report parser
 │    ├── power/              # Power report parser
 │    ├── emir/               # EMIR report parser
 │    ├── drc_lvs/            # DRC/LVS report parser
 │    └── def_lef_sdc/        # Physical/constraint file parser
 ├── analyzers/
 │    ├── constraint_analyzer.py
 │    ├── synthesis_tradeoff.py
 │    ├── timing_rootcause.py
 │    ├── rtl_insight.py
 │    ├── floorplan_planner.py
 │    ├── macro_planner.py
 │    ├── emir_analyzer.py
 │    ├── drc_lvs_fixer.py
 │    ├── eco_planner.py
 │    ├── power_analyzer.py
 │    ├── formal_verifier.py      # 形式化验证（LEC, Property Check, CDC/RDC）
 │    ├── package_planner.py      # PAD/Bump/RDL设计
 │    ├── dft_engine.py           # DFT（scan, ATPG, BIST）
 │    ├── low_power.py            # 低功耗实现（UPF, multi-Vt）
 │    ├── pdk_manager.py          # PDK与设计规则管理
 │    ├── si_analyzer.py          # SI sign-off分析
 │    ├── reliability.py          # 可靠性分析（HCI, NBTI, TDDB）
 │    ├── tapeout.py              # Chip finishing与tapeout准备
 │    ├── test_yield.py           # 测试策略与良率分析
 │    ├── lifecycle.py            # 设计生命周期管理
 │    ├── pattern_analyzer.py     # 设计模式挖掘
 │    └── knowledge_base.py       # 知识库管理
 ├── scheduler/
 │    ├── task_decomposer.py      # 任务拆分引擎
 │    ├── task_scheduler.py       # 任务调度器（DAG调度、并行管理）
 │    ├── log_analyzer.py         # 日志解析与分析
 │    ├── progress_tracker.py     # 进度可视化与追踪
 │    ├── runtime_estimator.py    # 运行时间预估
 │    └── notification.py         # 进度/异常通知
 ├── version/
 │    ├── design_vcs.py           # 设计版本管理（commit/diff/tag/branch）
 │    ├── flow_script_mgr.py      # Flow脚本版本管理
 │    ├── db_ref_manager.py       # 大型数据库引用管理（DB name/cell name）
 │    ├── lineage_tracker.py      # 版本血缘追踪
 │    ├── git_integration.py      # Git集成
 │    └── config_mgr.py           # 设计配置管理总入口
 ├── agents/
 │    ├── orchestrator.py
 │    ├── constraint_agent.py
 │    ├── synthesis_agent.py
 │    ├── timing_agent.py
 │    ├── floorplan_agent.py
 │    ├── macro_agent.py
 │    ├── signoff_agent.py
 │    ├── emir_agent.py
 │    ├── pv_agent.py
 │    ├── eco_agent.py
 │    ├── report_agent.py
 │    ├── formal_agent.py          # 形式化验证Agent
 │    ├── package_agent.py         # PAD/Bump/RDL设计Agent
 │    ├── dft_agent.py             # DFT Agent
 │    ├── low_power_agent.py       # 低功耗Agent
 │    ├── pdk_agent.py             # PDK管理Agent
 │    ├── si_agent.py              # SI/Reliability Agent
 │    ├── tapeout_agent.py         # Tapeout Agent
 │    ├── test_yield_agent.py      # Test & Yield Agent
 │    ├── lifecycle_agent.py       # Lifecycle Agent
 │    └── knowledge_agent.py       # Knowledge Agent
 ├── db/
 │    ├── schema.sql
 │    ├── graph_model.py
 │    ├── run_store.py
 │    ├── design_db.py
 │    └── query_api.py
 ├── pdk/
 │    ├── tech_lef_parser.py        # Technology LEF parser
 │    ├── cell_lef_parser.py        # Cell LEF parser
 │    ├── liberty_parser.py         # Liberty (.lib) parser
 │    ├── design_rules.py           # 设计规则数据库
 │    ├── metal_stack.py            # Metal stack定义
 │    └── pdk_registry.py           # PDK版本管理
 ├── knowledge/
 │    ├── best_practices/          # 最佳实践库
 │    ├── troubleshooting/         # 问题诊断库
 │    ├── design_patterns/         # 设计模式库
 │    ├── timing_patterns/         # Timing模式库
 │    ├── floorplan_patterns/      # Floorplan模式库
 │    ├── power_patterns/          # Power模式库
 │    ├── emir_patterns/           # EMIR模式库
 │    ├── drc_patterns/            # DRC模式库
 │    ├── silicon_learning/        # 硅后数据学习
 │    └── expert_experience/       # 专家经验库
 ├── reports/
 │    └── templates/
 ├── dashboard/
 │    └── web/
 ├── tests/
 ├── docs/
 └── examples/
```

---

## 16. 一句话总结

这个系统的核心不是 LLM 生成 DC/ICC2/PrimeTime/Calibre 脚本，而是：

> **把 RTL、约束、综合、floorplan、macro、placement、routing、STA、power、EMIR、DRC/LVS 统一成可查询、可推理、可回归验证的设计知识系统；再由 Agent 基于证据调用受控工具函数，形成后端设计闭环优化。**

真正价值：**从"工具命令自动化"升级到"后端设计决策自动化"。**
