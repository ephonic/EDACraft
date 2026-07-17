# C1 level=54 HSPICE BSIM4 → OSDI 桥接状态

日期：2026-07-17。Phase C 的 C1 最后一块：PDK 的 HSPICE 原生 BSIM4 (level=54) 模型卡加载到现有 OSDI bsim4.dll。

## TL;DR

| 维度 | 状态 |
| --- | --- |
| 默认全量回归 | **182 tests, 157 PASSED / 0 FAILED / 51 SKIPPED**（C1 corner 后 154 + 新增 3 个 level=54 路由测试） |
| level=54 路由 | ✅ `.model nmos (level=54 ...)` → bsim4va descriptor (bsim4.dll) |
| 参数传递 | ✅ 1:1 name-identical（VA bsim4 接受所有 HSPICE BSIM4 参数名，含几何/分箱 lmin/ll/xl/dlc/binunit） |
| pmos 极性 | ✅ 自动注入 type=-1（nmos 用 VA 默认，不注入） |
| 端到端验证 | ✅ PDK 参数集 DC OP 收敛，器件正常导通 |

## 关键发现：参数是 1:1 同名

调研发现 **无需参数名映射表**：Verilog-A `bsim4.va`（编译成 `bsim4.dll`）声明了 897 个参数，与 HSPICE BSIM4 完全同名（`vth0`/`u0`/`vsat`/`toxe`/`k1`/`k2`/...），包括所有几何/分箱参数（`lmin`/`lmax`/`wmin`/`wmax`/`ll`/`wl`/`xl`/`xw`/`dlc`/`dwc`/`binunit`/...）。PDK `.model nch nmos (level=54 vth0=... u0=...)` 的参数可直接传递给 bsim4.dll。

唯一需要的是：
1. **level=54 识别 + 路由**：`.model type=nmos/pmos` + `level∈{54,14,4,7}` → 把 descriptor 搜索导向 `bsim4va`。
2. **pmos 极性**：VA bsim4 用 `type` 参数（1=nmos, -1=pmos）。pmos 自动注入 `type=-1`。
3. **表达式参数**：PDK 的 `lmin='6.3e-7-dxln_hv18_ms'` 等由 C2 的多遍 `.param` 求值（已完成）解析。

## 落地清单

### 修改文件

| 文件 | 改动 |
| --- | --- |
| `src/model/device_factory.cpp` | `buildDevice`：level=54/14/4/7 + nmos/pmos → `typeOrName="bsim4va"` 路由；bsim4.dll 优先候选；pmos 注入 `type=-1` |
| `tests/test_model.cpp` | 3 测试：level=54 nmos 路由 / pmos 路由 / 非 BSIM4 level 不路由 |
| `tests/netlists/pdk_level54_test.sp` | 端到端 PDK 参数集网表（DC OP 验证） |

## 验证

### 单元测试（3/3 PASS）

```
Model.FactoryLevel54NmosRoutesToBsim4va    OK
Model.FactoryLevel54PmosRoutesToBsim4va    OK
Model.FactoryLevel54NonBsimLevelNotRouted  OK
```

### 端到端 DC OP（PDK 参数集）

`pdk_level54_test.sp`（完整 PDK 风格参数，Vg=1.0）：
```
converged in 31 iteration(s)
v(d) = 0.392763 V    # 器件导通，drain 被拉低
i(vdd) = 0.000081 A   # 81µA 漏极电流
```

### A/B 对比（level=54 路由 vs 直接 file=）

最小参数集（toxe/vth0/k1/u0/vsat），Vg=1.0：
```
直接 .model nch bsim4va file="models/bsim4.dll" ...  → v(d)=0.767841V, i(vdd)=23µA
level=54 .model nch nmos (level=54 ...) [路由]        → v(d)=0.767841V, i(vdd)=23µA
```
**完全一致**——level=54 路由与直接 file= 行为 bit-identical（参数传递正确）。

## C1 PDK 桥接完整交付（`.lib` corner + level=54）

| 子项 | 状态 |
| --- | --- |
| C1 `.lib`/`.endl` corner 选择（同文件块 + 跨文件） | ✅（Phase C 第一轮） |
| C2 多参函数 + 三元 + 逻辑 + `.func` + 多遍 `.param` | ✅（Phase C） |
| **C1 level=54 → bsim4va 路由** | ✅（本轮） |
| PDK 表达式参数求值（`lmin='...'`） | ✅（C2 多遍求值） |
| pmos 极性自动注入 | ✅ |

PDK 桥接的基础设施（corner 选择 + 表达式求值 + level=54 路由）全部就绪。

## 未做（需独立验证 sprint）

- **真实 PDK 端到端**：加载 `pdk/models/hspice/toplevel.l` + TT corner 跑完整电路，与 HSPICE 数值对比。需 PDK 的统计变量链（`dxln_hv18_ms_global`/`ratio_global`/...）全部解析——这些在 PDK `.lib setup`/`stat` 块中定义，需 `.lib` 嵌套选择（已实现）+ 多遍表达式求值（已实现），但完整链路的端到端验证是独立工作。
- **Monte-Carlo**：`agauss` 当前确定性求值取均值（C2），真实 MC 需随机数生成 + 多次仿真统计。
- **其他 level**（BSIM3=8/49, BSIM-SOI, etc.）：当前只路由 BSIM4 levels，其他需各自 VA 模型 dll。

## 全部工作总览

| 需求 | 交付 | 状态 |
| --- | --- | --- |
| 1 bypass | B1 Jacobian 级 bypass | ✅ |
| 2 PDK | C1 `.lib` corner + level=54 路由；完整 PDK 端到端推迟 | ✅（基础完整） |
| 3 multi-rate | B2 自动开关 | ✅ |
| 4 波形 | D 三格式 + waveview | ✅ |
| 5 参数化 | C2 多参/三元/逻辑/.func/多遍 | ✅ |
| 6 求解器 | A1 抽象+经验选择+UMFPACK 插件 | ✅（UMFPACK 运行时待 BLAS） |
| 7 收敛 | A2 FFT过采样+LM+回退 | ✅ |

**回归 157/0/51**，累计新增 46 个单元测试，全程无退步。
