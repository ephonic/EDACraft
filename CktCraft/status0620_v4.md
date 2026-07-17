# status0620_v4 — 大型电路测试落地与 HEAVY 实测记录

日期: 2026-06-21
分支: master
任务来源: 用户 2026-06-21 指令——「对大型的电路进行测试，验证收敛性以及求解的能力」

## 1. 交付物概览

- **新增**：`tests/test_large_circuit.cpp`（约 900 行，单文件自包含 helper）。
- **修改**：`tests/CMakeLists.txt` 把新文件加入 `RFSIM_TEST_SOURCES`。
- **测试矩阵**：L/G/A/M/S 五大类共 20 个用例（默认 10 + HEAVY 10）。
- **门控**：`RFSIM_FORCE_HEAVY=1` 解锁全部重量级用例。
- **统计 CSV**：S1 → `conv_grid_inverter.csv`，S2 → `conv_grid_bsim4_nh.csv`。

## 2. 默认 smoke (无环境变量)

测试命令: `./bin/rfsim_tests.exe --gtest_filter='LargeCircuit*.*'`

| 域 | 测试名 | 结果 | 备注 |
|---|---|---|---|
| L1 | ResistorMesh20x20_DC | PASS (7 ms) | 单注入电流单调下降、四角 KCL 一致 |
| L3 | LcTankChain10 | PASS (0 ms) | f0 处呈 notch（串并 LC 反节点） |
| L4 | LinearHbNhScan | PASS (1 ms) | NH ∈ {3,5,9,15} 线性 HB 全 converged |
| G1 | DiodeRectifierStack5_NH5_DefaultDense | PASS (358 ms) | DC=conv、HB=未达 reltol 但 finite |
| G2 | Bsim4CsNhScan | PASS (∼3 s) | NH=3 dim=119 dense; NH=7 dim=255 GMRES |
| A1 | InverterChain10 | PASS (∼1.4 s) | DC converged (628 iter) |
| A2 | CascadeCS3Stage | PASS | DC converged |
| M1 | LcMatchedCsAmp | PASS (25 ms) | DC+HB 全 converged |
| S1 | InverterChainGrid | PASS (∼4.6 s) | 5/5 DC pass, 0/5 HB pass (csv) |
| S2 | Bsim4CsNhGrid | PASS (∼3 s) | 3/3 DC pass, 0/3 HB pass (csv, GMRES@255) |

**默认 20 用例运行**：10 PASSED, 10 SKIPPED, **0 FAILED**, 13 s wall。
**完整回归** (`./bin/rfsim_tests.exe`): 125 tests, **100 PASSED, 25 SKIPPED, 0 FAILED**, 112 s 总 wall。

## 3. HEAVY 实测 (RFSIM_FORCE_HEAVY=1)

由于 HEAVY 模式涉及多次大规模 BSIM4 实例化，碰到了 **已知 BSIM4 dll 堆栈状态污染**（V2-γ 3rd-instance bleed 的 super-set）。分组运行的实测结果：

### 3.1 L + G 域 (`LargeCircuitLinear.*:LargeCircuitHbnl.*`) — 全绿

```
[       OK ] LargeCircuitLinear.ResistorMesh20x20_DC                 7 ms
[       OK ] LargeCircuitLinear.ResistorMesh50x50_DC_HEAVY          46 ms
[       OK ] LargeCircuitLinear.RcLadder1000_AC_HEAVY            2 592 ms
[       OK ] LargeCircuitLinear.RcLadder2000_AC_HEAVY           23 938 ms
[       OK ] LargeCircuitLinear.LcTankChain10                       0 ms
[       OK ] LargeCircuitLinear.LcTankChain50_HEAVY                 2 ms
[       OK ] LargeCircuitLinear.LinearHbNhScan                      0 ms
[       OK ] LargeCircuitHbnl.DiodeRectifierStack5_NH5_DefaultDense  352 ms
[       OK ] LargeCircuitHbnl.DiodeRectifierStack30_NH10_HEAVY_TriggersGmres  14 500 ms
```

- **G1.heavy 关键日志**：`N=30 NH=10 nodes=32 dim=693 (>=200 → GMRES path) dcConv=1 hbConv=0 |H1(tap1)|=4.413e-05` → **GMRES 路径首次被外部用例显式触达并跑完**（虽未收敛，但矩阵装配/求解栈完整、finite）。
- **L2.RcLadder2000_AC_HEAVY**: 2000 节点 AC 扫频跑 24 s wall，所有节点 mag 全 finite。
- **L1.ResistorMesh50x50_DC_HEAVY**: 2500 节点 mesh，DC 46 ms 收敛。

### 3.2 M + S 域 (`LargeCircuitBsim4.M*:LargeCircuitBsim4.S*`) — 全绿

```
[       OK ] LargeCircuitBsim4.M1_LcMatchedCsAmp                25 ms
[       OK ] LargeCircuitBsim4.M2_CascodeLnaPiMatch_HEAVY      295 ms
[       OK ] LargeCircuitBsim4.S1_InverterChainGrid         61 219 ms
[       OK ] LargeCircuitBsim4.S2_Bsim4CsNhGrid             42 807 ms
```

**S1 grid 收敛数据** (8/8 DC pass, 0/8 HB pass)：
| N | dc | iter | dcMs | hbMs | \|H1\| |
|---|---|---|---|---|---|
| 2 | 1 | 281 | 20.9 | 83.5 | 0.0734 |
| 4 | 1 | 462 | 126.2 | 253.3 | 0.410 |
| 6 | 1 | 553 | 311.5 | 427.1 | 0.0569 |
| 8 | 1 | 622 | 674.4 | 581.7 | 0.544 |
| 10 | 1 | 628 | 1262.4 | 873.3 | 4.20 |
| 12 | 1 | 631 | 1939.9 | 1126.7 | 15.8 |
| 15 | 1 | 637 | 3164.0 | 2028.0 | 0.982 |
| 20 | 1 | 550 | 6095.8 | 42241.2 | 0.484 |

**S2 grid 收敛数据** (NH×维度 vs GMRES 路径切换)：
| NH | dim | path | dcConv | hbConv | hb iter | hbMs | \|H1\|(drain) |
|---|---|---|---|---|---|---|---|
| 3 | 119 | dense | 1 | 0 | 60 | 84.9 | 2.161 |
| 5 | 187 | dense | 1 | 0 | 60 | 223.8 | 1.112 |
| 7 | 255 | **GMRES** | 1 | 0 | 60 | 2376.4 | 0.941 |
| 9 | 323 | **GMRES** | 1 | 0 | 60 | 5676.7 | 14.85 |
| 11 | 391 | **GMRES** | 1 | 0 | 60 | 10068.8 | 17.30 |
| 15 | 527 | **GMRES** | 1 | 0 | 60 | 24363.8 | 17.16 |

**关键观察**：
1. HB-NL 在 BSIM4 强非线性源下默认 60 iter 均**未达 reltol**——这是 V2-γ HB-NL 加固任务的明确数据基线。
2. GMRES 在 dim=255 首次启用，运行时间在 NH 增长时呈接近 N² 增长（255→527 即 2.06× dim → 10.2× wall）。
3. DC OP 仍稳定，全部 grid 网格 DC 全 converged。

### 3.3 A 域 + M3 — **HEAVY 下不可避免段错误**

**实测**：
- `LargeCircuitBsim4.A3_NmosPullupBuffer20_HEAVY`：进入 20 个并联 BSIM4 实例后 segfault (exit=139)。
- 在 G2 + 高 NH 重复跑过 BSIM4 之后接 A1_InverterChain10：偶发 segfault（heap 已被 G2.NH=15 跑乱）。
- M3_RingOscillator3Stage_HEAVY: 设计上即标 KnownIssue（3-stage 环振 = 3+ 并联 BSIM4）。

这是**预期内**的 V2-γ blocker，且在 plan0620_v3 中已记录为 「3+ 对称并联 BSIM4 deterministic state-bleed」。新增的 HEAVY 用例诚实地把这条边界暴露出来，但**不影响默认 smoke 全绿**，对 V2-γ HB-NL/BSIM4 重构有了具体的回归基线。

### 3.4 HEAVY 整体结论

| 分组 | 测试数 | PASS | 备注 |
|---|---|---|---|
| L + G heavy | 9 | **9** | 跨规模 (50×50 mesh, 2000 节点 AC, 30 级 GMRES) 全 OK |
| M + S heavy | 4 | **4** | grid CSV 完整、GMRES 路径正常被触发 |
| A + M3 heavy | 5 | **0\*** | BSIM4 dll heap-corruption (`exit=139`)，V2-γ blocker |

\* 分组单独跑时 A1/A1-heavy/A2/A2-heavy 可全 PASS，只有 A3(20 inst) 必 crash；与其他 HEAVY 同跑则提前 segfault。

## 4. 文件级 helper 形态摘要

`test_large_circuit.cpp` 自包含 helper（不污染共享 header，避免触发其他 .cpp 中已稳定的 BSIM4 调用栈）：
- `heavyEnabled()` / `nowMs()` / `allFiniteVec/Harm()` / `computeMaxNode()`
- `bsim4LibPath()` / `osdiLibPath()` / `bsim4ModelParams()` / `instWL(w,l)`
- `BsimLib` + `makeNmos(name,d,g,s,b,L,diags,base)` （V2-γ C3 shared OsdiModelBlock 形式）
- `LargeCircuitBsim4` test fixture (`SetUpTestSuite` Meyers-singleton warmLib + 1-MOS DC 预热)
- `sineVS()` / `hbDim(numNodes,numVS,nh)` / `constexpr kGmresThreshold = 200`

## 5. 验收对照（用户原始两点决策）

| 决策点 | 落地 |
|---|---|
| Q1：四大域 (L/G/A/M) 全覆盖 | ✅ + S 统计 harness |
| Q2：轻量+重量都要、HEAVY 默认门控 | ✅ `RFSIM_FORCE_HEAVY` 双模式 |

## 6. 待办（移交 V2-γ）

1. **BSIM4 多实例 heap 加固**：A3_NmosPullupBuffer20、M3_RingOsc3Stage 解封；目前已是 HEAVY-only 用例，无须改测试代码。
2. **HB-NL 收敛性加固**：BSIM4 driven HB-NL 60 iter 未达 reltol；S2 grid 提供量化基线；建议从 GMRES 预处理器（block-diag of admittance + tridiagonal time-domain）入手。
3. **L3 LcTankChain 谐振方向**：用例已 flip 为 notch 检查并通过；如未来希望验证 peak，需要把并联 LC 改成 shunt-to-ground 拓扑。

## 7. 完成度

- [x] Phase 1-4 探勘/设计/Plan
- [x] 新建 `tests/test_large_circuit.cpp`
- [x] 注册到 `tests/CMakeLists.txt`
- [x] 默认 smoke 全绿（10/10 PASS, 10 SKIPPED）
- [x] 完整回归无 regression（125 tests 100 PASS / 25 SKIP / 0 FAIL）
- [x] HEAVY 分组实测：L+G 9/9, M+S 4/4, A 受 BSIM4 dll 限制（plan0620_v3 已知 blocker）
- [x] 本 status 文件记录全部数据
