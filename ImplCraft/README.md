# ImplCraft - 集成电路后端设计自动化平台

ImplCraft 是一个完整的集成电路后端设计自动化平台，提供从 RTL 综合到签核验证的完整流程，支持 Synopsys、Cadence 和 Siemens EDA 工具链。

## 🎯 核心特性

### 完整的后端流程
- **RTL 综合**: Design Compiler 集成
- **DFT 插入**: BIST、扫描链、修复逻辑、ATPG 模式生成
- **布局规划**: 芯片尺寸估算、宏单元布局
- **物理实现**: 布局、时钟树综合、布线、优化
- **寄生参数提取**: StarRC SPEF 生成
- **静态时序分析**: PrimeTime 签核
- **物理验证**: Calibre DRC/LVS
- **ECO 修复**: 自动修复流程

### 多工具链支持
- **Synopsys**: DC + ICC2 + PT + StarRC
- **Cadence**: DC + Innovus + Tempus + Pegasus
- **Siemens**: Calibre (DRC/LVS)

### DFT 引擎
- **SRAM BIST**: 内存内置自测试架构
- **修复逻辑**: Spare row/col、修复寄存器插入
- **扫描链**: Full scan、partial scan、scan compression
- **ATPG**: Stuck-at、transition fault、测试压缩

### Web 管理平台
- 可视化项目配置（设计文件、设计库、EDA 工具路径）
- 流程配置（阶段顺序、并行执行、检查点）
- 实时执行状态监控
- 脚本生成和管理
- Git 集成

## 📦 项目结构

```
ImplCraft/
├── src/                          # 核心源码
│   ├── tools/                    # EDA 工具适配器
│   │   ├── base.py               # 基础适配器类
│   │   ├── dc_adapter.py         # Design Compiler
│   │   ├── icc2_adapter.py       # ICC2
│   │   ├── pt_adapter.py         # PrimeTime
│   │   ├── starrc_adapter.py     # StarRC (寄生参数提取)
│   │   ├── calibre_adapter.py    # Calibre (DRC/LVS)
│   │   ├── innovus_adapter.py    # Innovus
│   │   ├── tempus_adapter.py     # Tempus
│   │   └── pegasus_adapter.py    # Pegasus
│   ├── analysis/                 # 分析引擎
│   │   ├── dft_engine.py         # DFT 引擎 (BIST/扫描/修复/ATPG)
│   │   ├── eco_routing_engine.py # ECO 修复引擎
│   │   ├── error_checker.py      # 错误检查
│   │   └── rtl_advisor.py        # RTL 优化建议
│   ├── flow/                     # 流程管理
│   │   ├── orchestrator.py       # 流程编排器
│   │   └── stages.py             # 阶段定义
│   └── db/                       # 数据管理
│       ├── design_state.py       # 设计状态
│       └── config_loader.py      # 配置加载
├── web/                          # Web 平台
│   ├── backend/                  # FastAPI 后端
│   │   ├── main.py               # 主应用
│   │   └── api/                  # API 端点
│   │       ├── config.py         # 项目配置 API
│   │       ├── execution.py      # 执行流程 API
│   │       ├── designs.py        # 设计管理 API
│   │       └── scripts.py        # 脚本管理 API
│   └── frontend/                 # 前端界面
│       ├── index.html            # 主页面
│       ├── css/style.css         # 样式
│       └── js/app.js             # 应用逻辑
├── tests/                        # 测试套件
└── configs/                      # 配置文件示例
```

## 🚀 快速开始

### 环境要求
- Python 3.10+
- FastAPI
- PyYAML
- SQLAlchemy

### 安装

```bash
cd /share/home/yangfan/backend_scripts/ImplCraft

# 安装依赖
pip install fastapi uvicorn sqlalchemy pyyaml

# 运行测试
python -m pytest tests/ -v
```

### 启动 Web 平台

```bash
cd /share/home/yangfan/backend_scripts/ImplCraft

# 启动服务器
uvicorn web.backend.main:app --host 0.0.0.0 --port 8000 --reload

# 访问界面
# http://localhost:8000
```

## 🖥️ Web 界面使用

### 1. 仪表盘
- 查看设计项目概览
- 监控活跃设计数量
- 查看通过/失败阶段统计

### 2. 设计管理
- 创建新设计项目
- 查看设计详情
- 管理设计配置

### 3. 项目配置 ⚙️

#### 项目配置页签
- **项目名称**: 设置项目标识
- **工作目录**: 指定项目根目录
- **设计文件**: 添加 RTL 文件路径
- **设计库**: 配置标准单元库、IO 库路径
- **EDA 工具路径**: 配置 ICC2、PrimeTime、Calibre、StarRC 路径

#### 流程配置页签
- **流程阶段**: 启用/禁用阶段、调整执行顺序
- **执行选项**:
  - 并行执行：允许多阶段并行
  - 自动继续：失败后自动继续
  - 启用检查点：保存中间状态

#### 设计配置页签
- 创建多个设计配置（不同 PDK、不同约束）
- 配置顶层模块、时钟周期、目标利用率

### 4. 执行流程 ▶️

#### 执行控制
- **开始执行**: 启动完整流程
- **暂停**: 暂停当前执行
- **继续**: 恢复执行
- **停止**: 终止执行

#### 流程阶段
可视化显示每个阶段状态：
- 🟡 等待 (pending)
- 🔵 运行中 (running)
- 🟢 完成 (completed)
- 🔴 失败 (failed)
- ⚪ 跳过 (skipped)

**支持的阶段**:
1. Synthesis - RTL 综合
2. Floorplan - 布局规划
3. Placement - 布局
4. CTS - 时钟树综合
5. Routing - 布线
6. DRC - 设计规则检查
7. LVS - 版图原理图对比
8. ECO Fix - 工程变更修复

#### 执行日志
实时查看执行日志和进度

### 5. 脚本管理 📝
- 生成 Tcl 脚本
- 预览脚本内容
- 执行脚本
- 查看执行日志

## 📡 API 文档

启动服务后访问：`http://localhost:8000/api/docs`

### 主要端点

#### 项目配置
```
GET    /api/config/project          # 获取项目配置
PUT    /api/config/project          # 更新项目配置
GET    /api/config/flow             # 获取流程配置
PUT    /api/config/flow             # 更新流程配置
GET    /api/config/designs          # 列出设计配置
POST   /api/config/designs          # 创建设计配置
DELETE /api/config/designs/{name}   # 删除设计配置
```

#### 执行流程
```
GET    /api/execution/status        # 获取执行状态
POST   /api/execution/start         # 开始执行
POST   /api/execution/pause         # 暂停执行
POST   /api/execution/resume        # 继续执行
POST   /api/execution/stop          # 停止执行
GET    /api/execution/stages        # 获取所有阶段
GET    /api/execution/stage/{name}  # 获取阶段详情
```

#### 设计管理
```
GET    /api/designs                 # 列出所有设计
POST   /api/designs                 # 创建设计
GET    /api/designs/{id}            # 获取设计详情
PUT    /api/designs/{id}            # 更新设计
DELETE /api/designs/{id}            # 删除设计
```

#### 脚本管理
```
GET    /api/scripts/{design_id}     # 列出脚本
POST   /api/scripts/generate        # 生成脚本
GET    /api/scripts/preview/{id}    # 预览脚本
POST   /api/scripts/execute         # 执行脚本
GET    /api/scripts/log/{id}        # 查看日志
```

## 🔧 DFT 引擎详解

### 使用示例

```python
from src.analysis.dft_engine import (
    DFTEngine, DFTConfig, DFTTool,
    SRAMSpec, ScanChainConfig, BISTConfig,
    ATPGConfig, ScanArchitecture, BISTArchitecture
)

# 定义 SRAM
srams = [
    SRAMSpec(
        name="sram_256x32",
        depth=256,
        width=32,
        has_redundancy=True,
        spare_rows=2,
        spare_cols=1
    ),
    SRAMSpec(
        name="sram_1024x64",
        depth=1024,
        width=64,
        has_redundancy=True,
        spare_rows=4,
        spare_cols=2
    )
]

# 配置 DFT
config = DFTConfig(
    tool=DFTTool.DFT_COMPILER,  # Synopsys DFT Compiler
    design_name="my_soc",
    srams=srams,
    scan=ScanChainConfig(
        architecture=ScanArchitecture.FULL_SCAN,
        num_chains=4,
        clock_domain="clk",
        scan_enable_signal="scan_en"
    ),
    bist=BISTConfig(
        architecture=BISTArchitecture.MARCH,
        algorithm="march_c_plus",
        bist_controller_type="shared",
        max_srams_per_controller=8
    ),
    atpg=ATPGConfig(
        fault_model="stuck_at",
        coverage_target=0.99,
        max_patterns=50000
    )
)

# 创建引擎
engine = DFTEngine(config)

# 生成所有脚本
scripts = engine.write_all_scripts("output/dft")

# 打印摘要
print(engine.get_summary())
```

### 生成的脚本

DFT 引擎会生成以下脚本：

1. **scan_insertion.tcl** - 扫描链插入脚本
2. **bist_insertion.tcl** - BIST 插入脚本
3. **repair_insertion.tcl** - 修复逻辑插入脚本
4. **atpg_patterns.tcl** - ATPG 模式生成脚本
5. **dft_flow.tcl** - 主流程脚本
6. **{sram_name}_repair_wrapper.v** - SRAM 修复 Verilog 封装

### 支持的工具

- **Synopsys DFT Compiler**: 扫描插入、ATPG
- **Siemens Tessent**: 扫描插入、BIST、ATPG
- **Cadence Genus DFT**: 扫描插入

## 🛠️ 工具适配器

### Design Compiler
```python
from src.tools.dc_adapter import DCAdapter
from src.db.design_state import DesignState, DesignConfig

config = DesignConfig(
    design_name="top",
    clock_period_ns=2.0,
    libraries=LibraryConfig(std_cell_libs=["/path/to/lib.db"]),
    rtl_files=["/path/to/top.v"]
)
state = DesignState(config)
adapter = DCAdapter(state)
script = adapter.generate_script()
```

### ICC2
```python
from src.tools.icc2_adapter import ICC2Adapter

adapter = ICC2Adapter(state, sub_stage="placement")
script = adapter.generate_script()
```

### StarRC
```python
from src.tools.starrc_adapter import StarRCAdapter

adapter = StarRCAdapter(state, sub_stage="spef")
script = adapter.generate_script()
```

### Calibre
```python
from src.tools.calibre_adapter import CalibreAdapter

# DRC
adapter = CalibreAdapter(state, sub_stage="drc")
script = adapter.generate_script()

# LVS
adapter = CalibreAdapter(state, sub_stage="lvs")
script = adapter.generate_script()
```

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_dft_engine.py -v
python -m pytest tests/test_adapters.py -v
python -m pytest tests/test_flow.py -v
```

**测试覆盖**:
- 204 个测试用例
- 工具适配器测试
- DFT 引擎测试
- 流程编排测试
- 分析引擎测试

## 📊 流程编排

### 完整流程

```python
from src.flow.orchestrator import FlowOrchestrator
from src.db.design_state import DesignConfig

config = DesignConfig(
    design_name="my_chip",
    clock_period_ns=2.0,
    pdk=PDKConfig(tech_file="/path/to/tech.tf"),
    libraries=LibraryConfig(
        std_cell_libs=["/path/to/sc.db"],
        ndm_libs=["/path/to/ndm.ndm"]
    ),
    rtl_files=["/path/to/top.v"]
)

orchestrator = FlowOrchestrator(
    config=config,
    work_root="/path/to/work",
    dry_run=True  # 仅生成脚本，不执行工具
)

# 运行完整流程
state = orchestrator.run()

# 查看状态
status = orchestrator.get_flow_status()
print(status)
```

### 流程阶段

**Synopsys 流程**:
1. synthesis - Design Compiler 综合
2. dft_insertion - DFT 插入
3. create_lib - ICC2 库创建
4. floorplan - 布局规划
5. placement - 布局
6. cts - 时钟树综合
7. routing - 布线
8. route_opt - 优化
9. starrc_extraction - StarRC 提取
10. primetime - PrimeTime 时序分析
11. drc - Calibre DRC
12. lvs - Calibre LVS

**Cadence 流程**:
1. synthesis - Design Compiler 综合
2. dft_insertion - DFT 插入
3. create_lib - Innovus 库导入
4. floorplan - 布局规划
5. placement - 布局
6. cts - CCOPT 时钟树
7. routing - NanoRoute 布线
8. route_opt - ECO 优化
9. starrc_extraction - StarRC 提取
10. tempus - Tempus 时序分析
11. drc - Pegasus DRC
12. lvs - Pegasus LVS

## 📝 配置示例

### 项目配置 (JSON)

```json
{
  "name": "MyChip Project",
  "design_files": [
    "/path/to/rtl/top.v",
    "/path/to/rtl/core.v"
  ],
  "design_libraries": [
    "/path/to/libs/sc_28nm.db",
    "/path/to/libs/io_28nm.db"
  ],
  "working_directory": "/share/projects/mychip",
  "eda_tools": {
    "icc2_path": "/usr/local/synopsys/icc2",
    "pt_path": "/usr/local/synopsys/pt",
    "calibre_path": "/usr/local/mentor/calibre",
    "starrc_path": "/usr/local/synopsys/starrc"
  }
}
```

### 流程配置 (JSON)

```json
{
  "enabled_stages": [
    "synthesis",
    "floorplan",
    "placement",
    "cts",
    "routing",
    "drc",
    "lvs"
  ],
  "stage_order": [
    "synthesis",
    "floorplan",
    "placement",
    "cts",
    "routing",
    "drc",
    "lvs",
    "eco_fix"
  ],
  "parallel_execution": false,
  "auto_continue": true,
  "checkpoint_enabled": true
}
```

### 设计配置 (YAML)

```yaml
name: my_chip
top_module: top
clock_period_ns: 2.0
target_utilization: 0.7
pdk_name: smic28nm
config_path: /path/to/config.yaml
work_root: /path/to/work
```

## 🎓 使用场景

### 场景 1: 新设计项目
1. 在"项目配置"中设置工作目录和 EDA 工具路径
2. 添加 RTL 文件和设计库
3. 在"设计管理"中创建新设计
4. 在"执行流程"中启动完整流程
5. 监控执行状态和日志

### 场景 2: 调试失败阶段
1. 在"执行流程"中查看失败阶段
2. 查看阶段日志和错误信息
3. 在"脚本管理"中预览和修改脚本
4. 重新执行修改后的脚本

### 场景 3: DFT 插入
1. 定义 SRAM 规格和修复策略
2. 配置扫描链和 BIST 参数
3. 配置 ATPG 目标和覆盖率
4. 使用 DFT 引擎生成脚本
5. 执行 DFT 流程

## 🔒 许可证

本项目仅供内部使用。

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系

如有问题，请联系项目维护者。

---

**ImplCraft** - 让芯片后端设计更简单
