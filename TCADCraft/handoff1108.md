# TCADCraft 交接手册：2026-11-08

本手册记录截至 2026-11-08 的数值开发、发布边界和接续方法。
仓库位置为 https://github.com/ephonic/EDACraft/tree/main/TCADCraft 。
本机工作区为 `G:\vibe-codeing\tcad`。较早的 `handoff1105.md` 是历史快照，
其中“仍运行”“等待启动”等描述不再代表当前状态。

## 1. 当前结论与用户授权

- 本次发布版本为 **0.3.0rc2**，标签为 `tcadcraft-v0.3.0rc2`。
  用户已明确要求准备交接手册并把新发布版本更新到 GitHub `main/TCADCraft`。
- 数值开发基线为 `6f399e367db4a0848b7406768e203ee7daa143ce`，
  分支 `optimization/sheet-ordering-20261106`。发布在单独工作树中进行，
  已合入发布准备时 GitHub `main` 的 `87e42ef6589761f94bc471ba2ff366fd40b78d54`，
  保留其他项目更新。发布提交的最终身份以标签和本地 publication receipt 为准。
- 最近的 z／时间步矩阵已经完成计算、独立审计、封存和提交；
  **没有尚在运行的本批数值脉冲**，不要重复启动。
- 发布包通过干净 sdist 构建、独立 wheel 安装、石墨烯／MoS2 示例及
  **1127 项新执行测试，0 跳过，0 失败／错误**。
  这是发布范围的定向验证，不是全套开发测试或全面器件验收。
- 本次 GitHub 发布不替换远端 `/apps/EDAs/own/tcad/current`。
  全面二维逻辑／存储器件支持和全面 Sentaurus 等价仍未完成。

## 2. 目录、身份和保护边界

| 位置 | 用途 |
| --- | --- |
| `EDACraft/TCADCraft` | 原始工作区；保留 1078 文件受控身份及历史原始证据，不在此覆盖开发 |
| `development_worktrees/edacraft-sheet-ordering-20261106/TCADCraft` | 独立数值开发工作树；本轮数值提交为 `6f399e3` |
| `release_worktrees/edacraft-tcad-0.3.0rc2/TCADCraft` | 新发布工作树；版本、README、发布说明、手册和二进制由此发布 |
| `release_artifacts/tcadcraft-0.3.0rc2/attempt2` | 本轮构建输入、策略、启动回执及下载的原始发布产物 |
| `two_dimensional_material_followup_plan.json` | 本地当前状态及后续工作计划；不是自动求解器 |
| `tcadcraft_release_20261108.published.json` | 发布后的 commit、tag、远端 refs 核查回执 |

本手册的仓库文件路径均相对于 `TCADCraft/`；本机工具脚本路径相对于工作区。
主手册同时保存为工作区 `handoff1108.md` 和仓库 `TCADCraft/handoff1108.md`。

冻结数值候选位于远端：

```text
yangfan@10.131.254.103
/tmp/tcad_sheet_geometric_integration_20261107_run0/candidate
```

它与矩阵记录的 291 个候选源文件和 7 个受控测试源文件一致；
复用的研究原生库 SHA-256 为：

```text
318988172b59c2ea14f627ecc9aa422ae86c2f4984784002a20475cb9a5d13b4
```

新发布 wheel **重新构建了原生扩展**，不能把上述复用库的哈希写成新包哈希。
发布包原生库 SHA-256 为 `318988172b59c2ea14f627ecc9aa422ae86c2f4984784002a20475cb9a5d13b4`，由发布验证报告及产物实际身份确认。
数值源与开发基线一致，只有 `tcad/__init__.py` 中的包版本赋值改变。

当前生产符号链接的已验证目标是：

```text
/apps/EDAs/own/tcad/releases/0.2.0-native.20261024T165510Z
```

新版本已发布到 GitHub，不等于已安装到该生产目标。不要把临时构建环境
或研究候选目录当作生产目录。发布构建前后均核对生产目标和受控文件哈希。

## 3. 已实现功能与适用边界

新增发布功能：

1. coupled sheet `reused_gmres` 支持显式 `linear_ordering='MMD_AT_PLUS_A'`
   或 `'GEOMETRIC_ND'`，默认仍为 `'COLAMD'`。非默认排序要求迭代后端。
2. 几何排序使用不可变置换，正确映射矩阵、右端和解；缓存身份包含排序、
   置换及稳态／BE 存储算子，包括精确 dt。
3. `SheetTransient.clear_linear_cache()` 仅丢弃本驱动的可选线性因子引用，
   不改变已接受物理状态、时间和驱动；下一次求解按原门槛重建。
   其他对象可能仍共享该因子，Python 内存分配器也不保证立即归还 RSS。
   它不是清除物理 Schur 模型数据的接口。
4. 完整轨迹分析按同一物理区间比较 BE 电流，保留栅阶跃、符号积分、
   状态末时刻比较及三档时间步观测阶，并降低记录加载内存。

现有二维经典路径支持石墨烯 Dirac DOS、MoS2 抛物能带 FD 面密度／量子电容，
片层 phi/Fn/Fp DD、理想／电阻／热发射／Dirac 边缘接触、单能级陷阱和 BE 瞬态，
以及局域栅或三维矩形介质 Poisson 耦合和有限尺寸、网格对齐侧电极。

面密度单位是 m^-2，面电荷 C/m^2，面电流 A/m，端口总电流 A。
片层没有任意“有效厚度”换算。模型主要限定等温、均匀能带、常迁移率、
矩形对齐几何和代表性参数，尚未实测标定。

GCC 原生 core 使用 float128／113 位尾数，**Python/SciPy 片层求解仍是 float64**。
量子电容和密度梯度不等于自洽 Schrödinger–Poisson 或 NEGF。
默认 Schur 路径保留 1024 片层／100000 总节点限制；更大网格需要显式 coupled，
其可行规模仍受稀疏因子分解资源限制。默认直接线性求解器没有改变。

主要源码入口：

```text
tcad/material/sheet.py
tcad/solver/sheet_drift_diffusion.py
tcad/solver/sheet_dielectric.py
tcad/solver/sheet_transient.py
tcad/solver/_sheet_linear.py
tcad/solver/_sheet_ordering.py
benchmarks/sheet_refinement_trace.py
```

## 4. 最新数值完成项

最新报告：`docs/optimization/20261108-geometric-z-time512/README.md`。
完整矩阵固定 x83/y9，在 z113/121/129 三个网格上各有 n128/256/512 三档时间步。
每条轨迹为 60 ps，正／负／读出各 20 ps；dt 为
0.15625／0.078125／0.0390625 ps，分别 384／768／1536 动态步。

| 项目 | 最新结果 |
| --- | --- |
| 矩阵完整脉冲 | 9 条，其中 7 条继承、2 条本轮新跑 |
| 新增动态步／完整场 | 3072／8；完整场时刻 0、20、40、60 ps |
| 新增独立物理及账本检查 | 2,089,230 |
| 原 54 空间端点判据 | n128、n256、n512 全部 54/54 |
| 全场时间指标／原支持时间指标 | 60／162 |
| 原支持 | 固定 65×9×65，不用新采样替换旧判据 |
| signed mixed 指标 | 两对相邻 z × 四时刻 × 五场 × 两次时间减半，共 80 |
| 高于分析下限的 mixed 指标 | n128→256 为 26/40，n256→512 为 24/40 |
| 轨迹指标 | 三网格合计 90 项，均可分辨且两次时间步增量下降 |
| 工作进程 | 本批计算进程均退出，结果已封存 |

两个新工况的资源和独立检查结果：

| 工况 | 步数 | 墙钟 s | 峰值 MiB | 最大非线性残差 | 独立检查 |
| --- | ---: | ---: | ---: | ---: | ---: |
| z113 n512 | 1536 | 2376.526 | 758.293 | 9.79042e-13 | 1,010,231 |
| z121 n512 | 1536 | 2994.914 | 888.074 | 9.77744e-13 | 1,078,999 |

均为单次数值测量，不作普适速度提升声明。每个工况冻结 6000 s 墙钟／CPU、
4 GiB 峰值 RSS、48 GiB 地址空间、单数值线程。各网格初态的 39 个数组和
262 个标量与自身 n128 父级逐位一致；每个新轨迹拒绝 13 类破坏输入／结果。
这不宣称不同 dt 的首个 BE 状态逐位一致。

体电势全场观测时间阶约 1.0097–1.0136；区间导电电流阶约 0.86，
不能写成所有物理量均已进入一阶渐近区。mixed 场先作有符号数组相减再取范数，
最大归一化 mixed 增量约从 9.22707e-7 降到 4.57026e-7。
低于分析下限的项不可解释为物理脱耦。

最新 n512 的 z121→z129 原支持体电势增量约为
208.35056／162.10304／184.61186 microV（20／40／60 ps），低于原末级
250 microV 门槛；粗一级增量仍约 546.61／425.21／484.27 microV。
原判据要求末级差和适用的增量下降比，并非要求粗一级也小于末级门槛。

原始证据目录：

```text
EDACraft/TCADCraft/docs/validation/sheet_geometric_z_time512_20261108
```

其 `run_manifest.json` SHA-256：

```text
8d0dcc6ea8f82aca0977343f5c40feb732756bc1d8c001ef93f72e9f8cf2c529
```

本地收尾回执：`sheet_geometric_z_time512_20261108_final_audit.json`。
70 个原始封存文件、24 个报告 manifest 项，连同报告 manifest 及三个概览文件，
数值提交共核对 28 个提交文件。报告不包含全部原始场／运行归档。

## 5. 其他已完成对照与保留失败

| 研究 | 状态／定位 |
| --- | --- |
| refined x69/75/83，n128/256 | 原 54 判据两档均通过；`20261107-geometric-x83-time` |
| coarse x65/69/75，n128/256 | 仍为 52/54；20／60 ps 末级体电势差超限；`20261107-geometric-x75-time` |
| y9/17/33，n128/256 | 原 54 判据通过；mixed 低于分析下限不证明脱耦；`20261107-geometric-y-time256` |
| x65/y33/z113 三档时间步 | 完整轨迹和观测阶已封存；`20261107-geometric-time512` |
| 旧 MMD y17／y33 大网格 | 内存／超时失败及单独预算重放保留，不删除或按完成比例计通过 |
| 原始 stage524 | 双配置完整脉冲及局部 z 探针已完成；详见 0.3.0rc1 的历史验证说明 |

以上研究均在 `docs/optimization/` 下。每个报告的状态对应当时封存快照，
后续通过不应回写旧报告，也不能把重放、故障注入或重叠阶段审计累计为新模拟。
245 个求解器和 25 个轨迹开发测试是继承证据；本轮发布新测试数单独记录。

## 6. 固定验收原则

- 非线性最大行缩放残差 <=1e-12；真实原系统行缩放线性最大范数 <=1e-14，
  保持原 correction、iteration 和 single-refresh 策略。
- 原空间比较固定采样、归一化和指标：场尺度 0.025 V、电荷 1e-18 C、
  电流 1e-7 A、占据率尺度 1；末级归一化差 <0.01、适用下降比 <0.7，
  分析下限 1e-8。完整函数以封存提取脚本为准。
- 完整共同网格差和原 54 项判据分开报告。局部接触节点数不是统一全局 h，
  不据此推 Richardson 空间阶或绝对误差界。
- 三档 dt 的观测阶、相邻空间／时间增量及 mixed 下降是描述性证据；
  不直接相加成绝对误差预算，不自动标记整体时空收敛。
- 相邻完整场时钟匹配仍使用 1e-24 s 门槛；三档累计时钟跨度单独报告，
  不为三档跨度修改原相邻门槛。
- 不修改已封存结果、原保护源和标定脚本。原保护源文件数为 1078；
  `bench/tcadcraft/calibration/ferroelectric_hysteresis.py` SHA-256 保持
  `2adbb676a0f78b7c600eed78e32a60f0c7a2014e1630772c1e0aea991907c09d`。

## 7. 发布构建、安装与复现

本轮远端独立构建目录：

```text
/tmp/tcadcraft_release_0_3_0rc2_20261108_run2
```

流程：冻结输入文件哈希 → sdist → 干净解包 → wheel → 独立 venv 安装 →
在源树外验证版本／113 位 SI 原生库 → README 石墨烯及 MoS2 示例 →
全部 `test_sheet*.py` 和 constants／precision 测试 → ldd 与哈希 → 归档。
测试辅助 `benchmarks/` 单独复制，产品 `tcad` 必须来自安装后的 wheel。
venv 使用已提供的系统依赖，属于独立包安装验证，不是完全隔绝依赖的环境。

新执行测试：**1127 passed，0 skipped，0 failures/errors**。
历史研究的物理检查／测试没有借本次打包再次计为新数值结果。
元数据检查未传外部标定参数，不暗示重新完成了实验标定。

发布文件：

```text
binaries/linux-x86_64/tcad-0.3.0rc2-cp313-cp313-linux_x86_64.whl
binaries/source/tcad-0.3.0rc2.tar.gz
binaries/linux-x86_64/compatibility.json
binaries/SHA256SUMS
docs/releases/0.3.0rc2/RELEASE_VERIFICATION.json
docs/releases/0.3.0rc2/targeted_tests.xml
docs/releases/0.3.0rc2/numerical_source_identity.json
docs/releases/0.3.0rc2/VALIDATION.md
```

安装：

```bash
git clone https://github.com/ephonic/EDACraft.git
cd EDACraft/TCADCraft
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install binaries/linux-x86_64/tcad-0.3.0rc2-cp313-cp313-linux_x86_64.whl
python -c "import tcad; print(tcad.__version__)"
(cd binaries && sha256sum -c SHA256SUMS)
```

这是 Linux x86_64／CPython 3.13 host-built wheel，不是 manylinux 认证包。
运行时需要兼容 libc、libstdc++、libquadmath；实际 ldd 和平台见 compatibility。
其他 Python ABI／平台自行从源码构建并验证。原生 Windows 不支持，使用 WSL2／Linux。

源码构建：

```bash
TCAD_USE_PETSC=0 TCAD_USE_LAPACK=0 python -m pip install '.[dev]'
python scripts/release_check.py
```

发布前两次输入审计分别拦截辅助 C++ 源文件和校验说明文件缺失；
失败记录保留，最终 attempt2 补全打包清单并通过全部源文件哈希核查。
没有放宽数值判据或修改求解源。详情见 `docs/releases/0.3.0rc2/packaging_attempts.json`。

新 sdist 纳入 compact 优化报告的 `.py/.npz` 等复现材料。
最终构建报告、下载链接、校验和及本交接手册在构建完成后补入 Git 仓库；
它们不会改变已经验证的 wheel 数值代码。完整 raw validation 归档不随包发布。

## 8. 接手时先核对什么

1. `git` 检查独立开发／发布工作树的 HEAD 与工作区，避免在原保护目录直接开发。
   发布版本与研究候选哈希要区分。
2. 读取 `two_dimensional_material_followup_plan.json`；已完成状态没有
   `active_execution`。启动新任务前再确认不存在同一任务实例。
3. 核对本地最新 final audit、raw manifest 和报告 MANIFEST，而非只读进度日志。
   旧 PID 可能复用；任何进程控制必须核对命令行、所属目录和实际身份。
4. 对发布核对 `tcadcraft_release_20261108.published.json`、远端 `main`／tag
   和 `RELEASE_VERIFICATION.json`。不要用浏览器缓存页面推断 Git refs。

PowerShell 常用入口：

```powershell
Set-Location 'G:\vibe-codeing\tcad'
$env:PYTHONIOENCODING = 'utf-8'
Get-Content handoff1108.md -Encoding UTF8
Get-Content sheet_geometric_z_time512_20261108_final_audit.json -Encoding UTF8
Get-Content tcadcraft_release_20261108.published.json -Encoding UTF8
git -C development_worktrees/edacraft-sheet-ordering-20261106 status --short
```

不要重新执行已封存的 prepare／watch／record／finish 来“更新状态”；
这些脚本有目录不存在、父 HEAD、哈希和未封存前提，部分还会追加观察文件。
普通核查只读 JSON 和哈希。不要对巨大工作区根目录执行完整 `git status`。

最近一批工具是工作区的
`{prepare,audit,diagnose,record,status,watch,finish}_sheet_geometric_z_time512_20261108.py`。
对应冻结副本在 raw 证据内。新研究必须采用新目录／策略／脚本名，
保留旧输入、失败和原判据；先冻结策略及预算，再启动，最后审计、封存和提交。
本地可用 Python 为 `G:/msys64/mingw64/bin/python.exe -B`。
使用 UTF-8 读取中文，避免 PowerShell 默认编码覆盖文档。

## 9. 下一步优先级

1. 联合 x/y/z 空间控制和明确的物理观测量容差预算。现有独立局部细化通过，
   但不构成整体空间／时空误差界。首先据原模型与资源记录设计少量有辨识力的
   交叉组合，避免无目标重复跑相同网格。
2. 按目标器件扩展二维材料和接触：非均匀能带、密度／温度相关迁移率、
   必要散射／复合、异质界面、垂直接触及隧穿；明确来源、量纲和适用范围。
3. 逻辑：完整 FET 转移／输出／端口电荷／瞬态，以及电路耦合反相器增益和延迟。
4. 存储：按目标实现陷阱／铁电／电荷存储与二维沟道自洽耦合，验证写擦读、
   保持、多级、扰动；耐久预测必须有退化模型和循环数据。
5. 量子：限域和子带目标使用自洽 Schrödinger–Poisson，
   准弹道／弹道或相干隧穿目标再选相应输运模型，必要时 NEGF。
   经典 DD 对扩散主导二维材料器件可用，但不能覆盖全部量子输运。
6. 更新功能／适用范围／验收矩阵，逐项完成器件商业／实验对照及规模／恢复验证。

用户此前明确暂时单列的四项：真实非零 a/c 材料标定、独立三温实测、
完整 200 ps 商业／原生三温剖面、一般复杂物理时空及能量／熵完整闭合，
仍保持未完成。不要把本轮等温 MoS2 数值控制当成这些问题的完成证据，
也不要因为缺这些数据停止已获授权的二维功能开发。
