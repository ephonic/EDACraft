# PG网络规划指南 (Power/Ground Network Planning Guide)

本系统提供完整的PG网络规划能力，包括PG pad、I/O pad和bond pad的摆放建议及计算方案。

## 核心功能

### 1. PG Pad数量计算
根据设计功耗和电流限制，自动计算所需的PG pad数量。

**计算公式：**
```
总电流 I_total = P_total / V_dd
每路电源所需pad数 N_per_supply = ceil(I_total / (2 * I_max_per_pad))
总PG pad数 N_total = (N_vdd + N_vss) * safety_margin
```

**参数说明：**
- `P_total`: 总功耗 (W)
- `V_dd`: 核心电源电压 (V)
- `I_max_per_pad`: 每个PG pad的最大电流承载能力 (A)
- `safety_margin`: 安全裕度 (默认1.2，即20%裕度)

**示例：**
- 设计功耗: 1.0W
- 电源电压: 0.9V
- 每pad电流限制: 0.1A

计算：
- I_total = 1.0 / 0.9 = 1.11A
- N_per_supply = ceil(1.11 / (2 * 0.1)) = 6 pads
- N_total = (6 + 6) * 1.2 = 14.4 → 15 pads

### 2. PG Pad摆放策略

提供四种摆放策略：

#### 2.1 Uniform（均匀分布）- 推荐
- **特点**: PG pad沿芯片四边均匀分布
- **优点**: 电流分布均匀，IR-drop最小化
- **适用**: 大多数设计，特别是高功耗设计
- **计算**: 
  ```
  周长 L = 2 * (W_die + H_die)
  可用长度 L_avail = L * 0.8  # 80%用于PG pad
  间距 spacing = L_avail / N_total
  ```

#### 2.2 Clustered（分组摆放）
- **特点**: PG pad分成多个小组（cluster），每组4-8个pad
- **优点**: 便于电源网络分区，减少全局布线拥塞
- **适用**: 大型SoC，多电源域设计
- **计算**:
  ```
  cluster_size = 4  # 每组4个pad
  num_clusters = ceil(N_total / cluster_size)
  cluster_spacing = L / num_clusters
  ```

#### 2.3 Peripheral（周边摆放）
- **特点**: PG pad集中在芯片边缘
- **优点**: 节省核心区域，便于封装连接
- **适用**: 面积受限的设计

#### 2.4 Corner（角落摆放）
- **特点**: PG pad集中在四个角落
- **优点**: 最短的电源路径到封装
- **适用**: 高频设计，需要最小化电感
- **计算**:
  ```
  pads_per_corner = N_total / 4
  每个角落L形排列
  ```

### 3. I/O Pad摆放

**摆放原则：**
1. I/O pad放置在PG pad之间
2. 高速信号pad靠近角落（减少串扰）
3. 时钟pad远离数字信号pad
4. 模拟pad分组放置，远离数字pad

**计算方法：**
```
可用槽位 = PG_pad_count + IO_pad_count
间距 = 周长 / 可用槽位
IO pad位置 = PG pad位置 + 间距/2
```

**优化建议：**
- 如果IO pad数量 > 200，考虑双排摆放或交错摆放
- 差分信号对应该相邻放置
- 电源敏感的模拟信号应该靠近PG pad

### 4. Bond Pad摆放

**特点：**
- Bond pad尺寸通常是PG pad的1.5倍
- Bond pad间距是PG pad的1.5倍
- 主要用于wire bonding封装

**计算方法：**
```
bond_pad_width = pg_pad_width * 1.5
bond_pad_pitch = pg_pad_pitch * 1.5
间距 = 周长 / num_bond_pads
```

**设计规则：**
- 最小bond pad间距: 60um (typical)
- Bond pad到芯片边缘: 至少50um
- Bond pad到active circuit: 至少20um

### 5. IR-Drop估算

**简化模型：**
```
平均距离 d_avg = Σ distance(pad_i, center) / N_total
电阻 R = d_avg * R_per_um  # R_per_um ≈ 0.0001 Ohm/um
每pad电流 I_pad = I_total / N_total
IR-drop = I_pad * R
```

**阈值建议：**
- < 20mV: 优秀
- 20-50mV: 可接受
- > 50mV: 需要优化（增加PG pad数量或使用clustered摆放）

**优化方法：**
1. 增加PG pad数量
2. 使用clustered摆放策略
3. 加宽power strap
4. 增加power mesh密度

### 6. EM (Electromigration) 检查

**电流密度计算：**
```
J = I_pad / (strap_width * 10)  # 假设strap宽度10um
```

**EM限制：**
- 典型限制: 0.001 A/um
- 如果 J > limit，需要：
  - 加宽power strap
  - 增加PG pad数量
  - 使用多层金属并联

## 使用方法

### 命令行接口

```bash
# 基本用法
python3 -m src.pg_network \
    --power 1.5 \
    --voltage 0.9 \
    --die 2900 1900 \
    --num-io-pads 150 \
    --strategy uniform

# 高级用法
python3 -m src.pg_network \
    --config config/project_default.yaml \
    --power 2.0 \
    --voltage 0.9 \
    --io-voltage 1.8 \
    --pad-size 80 80 \
    --pad-pitch 100 \
    --max-current 0.08 \
    --strategy clustered \
    --num-io-pads 200 \
    --num-bond-pads 50 \
    --power-domains 2 \
    --generate-script \
    --output-dir ./pg_output \
    --verbose
```

### Python API

```python
from src.analysis.pg_network_advisor import (
    PGNetworkAdvisor,
    PowerConfig,
    PadSpec,
    PadType,
    PlacementStrategy,
)

# 创建配置
power_config = PowerConfig(
    vdd_voltage=0.9,
    vddq_voltage=1.8,
    total_power_w=2.0,
    core_power_w=1.4,
    io_power_w=0.6,
    num_power_domains=2,
)

pad_spec = PadSpec(
    pad_type=PadType.PG_PAD,
    width_um=80.0,
    height_um=80.0,
    pitch_um=100.0,
    max_current_a=0.1,
)

# 创建advisor并规划
advisor = PGNetworkAdvisor()
plan = advisor.plan_pg_network(
    power_config=power_config,
    pad_spec=pad_spec,
    die_width_um=2900.0,
    die_height_um=1900.0,
    num_io_pads=150,
    num_bond_pads=50,
    placement_strategy=PlacementStrategy.UNIFORM,
)

# 查看结果
print(plan.summary)
print(f"需要PG pad: {plan.total_pg_pads_needed}")
print(f"IR-drop: {plan.estimated_ir_drop_mv:.2f} mV")

# 生成ICC2脚本
advisor.generate_pg_script(plan, "pg_network.tcl", tool="icc2")
```

## 输出文件

### pg_network_report.txt
人类可读的报告，包括：
- PG pad数量需求
- 摆放策略
- IR-drop分析
- 建议和警告

### pg_network_plan.json
机器可读的JSON格式，包括：
- 完整的pad摆放坐标
- 所有计算参数
- 分析结果

### pg_network.tcl (可选)
ICC2 PG网络创建脚本，包括：
- PG ring创建
- PG mesh创建
- PG pad创建
- PG连接

## 设计建议

### 低功耗设计 (< 0.5W)
- 使用uniform策略
- 最少4个PG pad (2 VDD + 2 VSS)
- 简单的PG ring即可

### 中等功耗设计 (0.5W - 2W)
- 使用uniform或clustered策略
- 8-20个PG pad
- PG ring + PG mesh
- 考虑添加decap cell

### 高功耗设计 (> 2W)
- 使用clustered策略
- 20+ PG pad
- 密集的PG mesh
- 多层金属并联
- 添加大量decap cell
- 考虑power gating

### 高频设计 (> 500MHz)
- 使用corner策略减少电感
- 增加PG pad数量
- 使用宽金属strap
- 添加高频decap

## 集成到Flow

PG网络规划应该在floorplan之后进行：

```
1. Synthesis → 获取功耗估算
2. Floorplan → 确定die size
3. **PG Network Planning** → 规划PG pad摆放
4. Placement → 标准单元摆放
5. CTS → 时钟树综合
6. Routing → 布线
```

## 验证检查清单

- [ ] PG pad数量满足电流要求
- [ ] IR-drop < 50mV (或设计要求)
- [ ] 无EM违规
- [ ] I/O pad不与PG pad重叠
- [ ] Bond pad间距满足封装要求
- [ ] 多电源域正确隔离
- [ ] Decap cell数量充足
- [ ] PG ring/mesh连接完整

## 常见问题

**Q: 如何确定每个PG pad的电流限制？**
A: 查看foundry提供的pad spec文档，通常在0.05A - 0.2A之间。

**Q: 如果IR-drop超标怎么办？**
A: 
1. 增加PG pad数量
2. 加宽power strap
3. 使用clustered策略
4. 增加power mesh层数

**Q: I/O pad和PG pad可以共用吗？**
A: 不可以。PG pad专门用于电源/地，I/O pad用于信号。但I/O cell中通常包含PG连接。

**Q: 如何验证PG网络质量？**
A: 使用专门的PDN分析工具（如RedHawk, Voltus）进行详细的IR-drop和EM分析。

## 参考标准

- IEEE Std 1801-2018 (UPF) - 电源意图规范
- JEDEC JESD47 - 集成电路可靠性测试
- Foundry Design Rule Manual - 具体工艺规则

## 版本历史

- v1.0 (2026-06): 初始版本，支持基本PG网络规划
