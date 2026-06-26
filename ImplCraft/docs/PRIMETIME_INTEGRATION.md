# PrimeTime 工业级集成

## 概述

PrimeTime 适配器已重构为工业级架构，支持完整的 STA sign-off 流程和 ECO 修复。所有配置选项均通过 YAML 文件驱动，实现了配置与脚本生成的完全分离。

## 核心特性

### 1. 时序分析（Timing Analysis）

#### Setup/Hold 分析
```yaml
pt:
  timing:
    enable_cppr: true           # Common Path Pessimism Removal
    enable_si_analysis: true    # Signal Integrity
    max_paths: 200              # 每个 path group 报告的最大路径数
    slack_lesser_than: -0.1     # 只报告 slack 小于此值的路径
    nworst: 5                   # 每个 endpoint 报告的最差路径数
```

#### Path Group 分析
- **Setup timing** (`-delay_type max`)：建立时间分析
- **Hold timing** (`-delay_type min`)：保持时间分析
- 支持多 path group 并行分析
- 自动识别 clock group 并分组报告

#### 时序 Derate
```yaml
timing_derate:
  late_factor: 1.05             # Late timing derate
  early_factor: 0.95            # Early timing derate
```

### 2. 功耗分析（Power Analysis）

```yaml
pt:
  power:
    enable_power_analysis: true
    vcd_file: "waveform.vcd"    # 或 saif_file: "activity.saif"
    vcd_strip_path: "tb_top/dut"
    power_mode: "averaged"      # averaged | time_based
```

#### 功耗报告类型
- **Dynamic power**：动态功耗（开关功耗）
- **Leakage power**：漏电流功耗
- **Internal power**：内部功耗
- **Switching power**：开关功耗

#### 功耗优化建议
```yaml
pt:
  power:
    enable_power_prediction: true  # 功耗预测
    power_opt_effort: "high"       # low | medium | high
```

### 3. Parasitic 反标（SPEF Back-annotation）

```yaml
pt:
  spef_file: "route_opt.spef"   # SPEF 文件路径
  spef_format: "auto"           # auto | SPEF | DSPF
```

#### 特性
- 自动检测 SPEF/DSPF 格式
- 支持分段反标（partial back-annotation）
- 电容耦合保留（`-keep_capacitive_coupling`）
- 零电阻完成（`-complete_with zero`）

### 4. ECO 修复（Engineering Change Order）

#### Setup ECO 修复
```yaml
pt:
  eco:
    enable_eco: true
    fix_setup: true
    setup_opt_margin: 0.1       # Setup 优化余量
    fix_setup_groups: ["reg2reg", "reg2output"]
    fix_drc_buffer_list: ["BUFFX4", "BUFFX8"]
```

#### Hold ECO 修复
```yaml
pt:
  eco:
    fix_hold: true
    hold_opt_margin: 0.05       # Hold 优化余量
    fix_hold_groups: ["reg2reg"]
    fix_hold_buffer_list: ["DEL020D1", "DEL040D1"]
```

#### DRC 修复
```yaml
pt:
  eco:
    fix_drc: true               # 修复 max_transition/max_capacitance
```

#### 功耗修复
```yaml
pt:
  eco:
    fix_power: true             # 功耗优化
    fix_leakage: true           # 漏电流优化
    eco_power_priority: ["HVT", "RVT"]  # VT 优先级
```

#### ECO 物理模式
```yaml
pt:
  eco:
    eco_physical_mode: "placement"  # placement | none
    lef_library: "stdcell.lef"    # LEF 库文件
    final_def: "routed.def"       # DEF 文件
```

### 5. VT 控制（Threshold Voltage Control）

```yaml
pt:
  vt_groups:
    "HVT": "slow"               # HVT -> slow corner
    "RVT": "typical"            # RVT -> typical corner
    "LVT": "fast"               # LVT -> fast corner
  dont_use_patterns:            # 禁用的 cell pattern
    - ".*DLY.*"
    - ".*FILL.*"
```

### 6. 报告生成（Report Generation）

#### 标准报告
- `analysis_coverage.rpt`：分析覆盖率
- `vios.rpt`：所有违例
- `threshold_voltage_group.rpt`：VT 分布
- `clock_timing_summary.rpt`：时钟时序摘要
- `power.rpt`：功耗分析
- `switching_activity.rpt`：开关活动

#### Path Group 报告
- `${group_name}_max.tim`：Setup timing 报告
- `${group_name}_min.tim`：Hold timing 报告

### 7. Session 管理

```yaml
pt:
  save_session: true
  session_name: "top_session"   # Session 名称
  report_path: "./PT/report"    # 报告输出路径
  output_path: "./PT/out"       # 输出文件路径
```

#### Session 操作
- **保存 session**：`save_session ./PT/out/top_session`
- **恢复 session**：`restore_session ./PT/out/top_session`
- **ECO session**：`save_session ./PT/out/top_eco.session`

## 配置与脚本生成分离

### 架构设计

```
┌─────────────────┐
│  YAML Config    │  configs/FullSystem.yaml
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Config Loader   │  src/config/loader.py
│ (load_pt_config)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PTStageConfig   │  src/config/pt_config.py
│ (Dataclass)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PT Adapter      │  src/tools/pt_adapter.py
│ (Script Gen)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TCL Script      │  work/primetime/PT/run.tcl
└─────────────────┘
```

### 配置层（Configuration Layer）

**文件**: `src/config/pt_config.py`

```python
@dataclass
class PTStageConfig:
    design_name: str
    spef_file: str
    spef_format: str
    timing_derate_late: float
    timing_derate_early: float
    enable_cppr: bool
    enable_si_analysis: bool
    max_paths: int
    # ... 50+ 工业级配置选项
```

**职责**:
- 定义所有配置参数
- 提供默认值
- 验证配置合法性
- 序列化/反序列化

### 脚本生成层（Script Generation Layer）

**文件**: `src/tools/pt_adapter.py`

```python
class PTAdapter(ToolAdapter):
    def generate_script(self) -> str:
        sections = []
        sections.append(self._gen_header())
        sections.append(self._gen_host_options())
        sections.append(self._gen_libraries())
        sections.append(self._gen_read_design())
        sections.append(self._gen_spef())
        sections.append(self._gen_timing_derate())
        sections.append(self._gen_update_timing())
        sections.append(self._gen_path_group_analysis())
        sections.append(self._gen_power_analysis())
        sections.append(self._gen_constraint_reports())
        sections.append(self._gen_eco_fixing())
        sections.append(self._gen_session_save())
        return "\n".join(sections)
```

**职责**:
- 读取配置对象
- 生成 TCL 脚本片段
- 组装完整脚本
- 处理条件逻辑

### 优势

1. **配置复用**: 同一配置可生成多个脚本变体
2. **测试友好**: 配置对象易于单元测试
3. **类型安全**: Dataclass 提供类型检查
4. **文档自动生成**: 配置结构即文档
5. **版本控制**: YAML 配置易于 diff 和 review

## 使用示例

### 1. 基本 STA Sign-off

```yaml
pt:
  spef_file: "route_opt.spef"
  timing:
    enable_cppr: true
    max_paths: 100
  report_path: "./PT/report"
```

### 2. 带 ECO 修复的完整流程

```yaml
pt:
  spef_file: "route_opt.spef"
  timing:
    enable_cppr: true
    enable_si_analysis: true
    max_paths: 200
  power:
    enable_power_analysis: true
    vcd_file: "waveform.vcd"
  eco:
    enable_eco: true
    fix_setup: true
    fix_hold: true
    fix_drc: true
    setup_opt_margin: 0.1
    hold_opt_margin: 0.05
    eco_physical_mode: "placement"
  save_session: true
```

### 3. 多角多模分析（MCMM）

```yaml
pt:
  scenarios:
    - name: "func_ss"
      corner: "ss"
      spef_file: "route_opt_ss.spef"
      sdc_file: "constraints_ss.sdc"
    - name: "func_ff"
      corner: "ff"
      spef_file: "route_opt_ff.spef"
      sdc_file: "constraints_ff.sdc"
```

## 测试覆盖

所有 69 个测试通过：

```bash
pytest tests/test_industrial.py::test_pt_script_generation -v
pytest tests/test_flow.py::test_flow_orchestrator_dry_run -v
```

## 与 DC 适配器的对比

| 特性 | DC Adapter | PT Adapter |
|------|-----------|-----------|
| 配置分离 | ✅ | ✅ |
| 模块化生成 | ✅ | ✅ |
| YAML 驱动 | ✅ | ✅ |
| 工业级特性 | DC-T, MCMM, Power | ECO, SI, Power |
| Session 管理 | N/A | ✅ |
| 报告类型 | QoR, Timing, Area | Path Group, Power |
| ECO 支持 | N/A | ✅ (Setup/Hold/DRC) |

## 参考资源

- **配置文件**: `configs/FullSystem.yaml` (PT 部分)
- **适配器代码**: `src/tools/pt_adapter.py`
- **配置定义**: `src/config/pt_config.py`
- **测试用例**: `tests/test_industrial.py::test_pt_script_generation`
- **原始工业脚本**: 参考 DCICC Flow 4.6 的 `runpt.tcl`

## 下一步

1. **Calibre 集成**: 将 DRC/LVS 适配器也重构为模块化架构
2. **MCMM 支持**: 在 PT 中实现多角多模分析
3. **自动 ECO 验证**: 添加 ECO 修复后的自动验证流程
4. **报告解析**: 实现 PT 报告的自动解析和 QoR 提取
