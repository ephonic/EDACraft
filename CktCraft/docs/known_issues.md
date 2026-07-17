# Known Issues — rfsim simulator

> 本文档收录已识别但暂未根治的 KNOWN-LIMITATION，所有条目均有对应 status / plan
> 文档作为深度参考，并指明 SKIP gate / 复现路径。CI 行为：默认 100/100 PASS；
> 真正触发条件下的失败用例需要显式环境变量打开。

---

## KI-1 — HB-NL BSIM4 高 NH × 强非线性场景频域 Newton 不收敛

| 项 | 内容 |
|----|------|
| 触发用例 | `LargeCircuitBsim4.S2_Bsim4CsNhGrid`、`LargeCircuitBsim4.CascodeChain5` 等 BSIM4 + NH≥3 + V<sub>ds</sub> 大摆幅组合 |
| 现象 | DC OP 收敛，HB Newton 0/N 接受率，autoHomotopy 全 ε 段失败 |
| 直接根因（已证实，2026-06-21 之前） | (1) F/J 不一致：残差缺 jωQ 项 — `src/assembly/hb_jacobian.cpp:399-402` vs `:424-439`；(2) FFT 时域采样 N=2(NH+1) 偏少 → 卷积混叠 — `:246`；(3) HB warm-start 仅填 DC，k≥1 全零 — `src/solver/hb_nonlinear.cpp:577-588` |
| 已部署缓解 (V2-δ S1, 2026-06-21) | A. **AC 小信号 warm-start**：`HbNlOptions::acWarmStart`（默认 true）— 显著扩大可收敛 NH 范围；B. **Armijo 比较式修正**：从 ‖F‖ 线性比较改为 ‖F‖² 比较；C. **evalTimeSamples bad-gate** 由 100V 收紧到 20V clamp，保 FFT 周期性；D. **RFSIM_HBNL_VERBOSE** 环境开关用于现场诊断 |
| 未完工缓解 | 路径 B（4× FFT oversampling + jωQ 残差补全）— Sprint S2；路径 A（trust-region/LM）— Sprint S3 |
| 复现 | `set RFSIM_FORCE_HEAVY=1 & ctest -R S2_Bsim4CsNhGrid -V` |
| 主参考 | `plan0621-v4.md` §1.1-1.4；`status0620_v2.md:93` 历史 TODO |

### 诊断开关

```cmd
:: 每外层 Newton 一行 ‖F‖ 轨迹 + AC warm-start 状态
set RFSIM_HBNL_VERBOSE=1

:: 加打印 source/gmin schedule + α/dxMax + safestep 触发点
set RFSIM_HBNL_VERBOSE=2
```

---

## KI-2 — N≥15 BSIM4 多实例段错误 / 挂起（跨 CRT 堆腐败）

| 项 | 内容 |
|----|------|
| 触发用例 | `MultiDevice.EightFingerBalanced`、`MultiDevice.C3Bis*`、`LargeCircuitBsim4.A1_InverterChain15_HEAVY`、`LargeCircuitBsim4.A3_NmosPullupBuffer20_HEAVY`、`LargeCircuitBsim4.S1_InverterChainGrid`（实例数 ≥3 且 NodeId=4 特异性叠加） |
| 现象（v5 基线，2026-06-20） | 单测试单跑 PASS；与其他 HEAVY 同跑或 N≥15 时 segfault；非统计性 flake |
| 主根因（已证实，2026-06-21 S2） | bsim4.dll 由 OpenVAF 编译，链 **UCRT (ucrtbase + VCRUNTIME140)**；原 host 由 MinGW64 GCC 编译，链 `msvcrt.dll`（NT4 时代 CRT），**两套独立堆**。`osdi_library.cpp` 的"intentionally leak the message buffer" workaround 是该问题的现场补丁证据 |
| 已部署根治 (Sprint S2, 2026-06-21) | **A. host 完全切换到 MSVC `/MD`**（与 dll UCRT 对齐，共享同一 ucrtbase 堆）：`CMakeLists.txt` MSVC 分支 + `build.bat` 重写 + `cmake/SuiteSparseKLU.cmake` KLU `/W0` 降噪；**B. 删除 `osdi_library.cpp:32-37` 的 msg leak**，恢复 OSDI spec 规定的 `std::free(msg)`；**C. 解锁 `EightFingerBalanced` 与 `SelfBiasedCascodeStack5` 测试**（之前 `RFSIM_FORCE_C14/C2_STACK5` gate），它们现在是 KI-2 回归红线 |
| 残留风险 | A3_NmosPullupBuffer20_HEAVY / S1_InverterChainGrid 在同一进程内反复 setup/teardown 累积 ≥8 次 BSIM4 实例时仍偶发 SEH 0xc0000005 flake（单独跑 PASS）。OSDI v0.3 spec 缺 destroy hook，dll 内部 setup sub-alloc 全部 process leak，累积到 N=20 段压力可能撞出 dll 内部边界 bug。归 S3 |
| 跨 CRT 根治证据 | (1) `MultiDevice.EightFingerBalanced` 26 ms PASS（v5 默认 SKIP）；(2) `LargeScaleBsim4.SelfBiasedCascodeStack5` 56 ms PASS（v5 默认 SKIP）；(3) `A1_InverterChain15_HEAVY` 4.86 s PASS（v5 挂死）；(4) `A3_NmosPullupBuffer20_HEAVY` 9.13 s PASS（v5 挂死，flake 见上）；(5) `S1_InverterChainGrid` 21 s PASS 含 N=20 段（v5 挂死） |
| 残留 flake 修复 (S2+, 2026-06-21) | **路径 A：每用例前 `OsdiLibrary::reload()` FreeLibrary+LoadLibrary**，让 dll 内部 sub-alloc 全局状态归零。改 `BsimLib::reload()` + `LargeCircuitBsim4` / `MultiDevice` / `LargeScaleBsim4` 三 fixture 的 `SetUp` 调用。证据链与设计见 `docs/flake_investigation_0621.md`。该 workaround **彻底消除"同进程累积型" flake**：`gtest_repeat=N` 下 N=10/15 多实例用例连续稳定 PASS。残留仅"N=20 单进程冷启动"——已独立成 KI-3 |
| 未完工修复 | OSDI destroy hook（spec-level，需上游 OpenVAF 配合）；dll 内部 NodeId=4 假定性 OOB 二分（PageHeap E2 实验）— Sprint S3 |
| 主参考 | `plan0621-v4.md` §2；`status0620_v5.md` v5 baseline；`status0621-v2.md` S2 落地清单；`status0621-v3.md` 路径 A 落地；`docs/flake_investigation_0621.md` 调查全过程 |

### 复现实验

```cmd
:: KI-2 已根治（cross-CRT），下面这些 v5 挂死的用例在 MSVC /MD host 下都应 PASS
set RFSIM_FORCE_HEAVY=1
set RFSIM_FORCE_C3BIS=1
rfsim_tests.exe --gtest_filter=MultiDevice.EightFingerBalanced:LargeScaleBsim4.SelfBiasedCascodeStack5:LargeCircuitBsim4.A1_InverterChain15_HEAVY:LargeCircuitBsim4.S1_InverterChainGrid

:: 残留 flake 复现（A3/S1_Grid 在累积进程内可能崩；单测通常 PASS）：
rfsim_tests.exe --gtest_repeat=5 --gtest_filter=LargeCircuitBsim4.A3_NmosPullupBuffer20_HEAVY
```

诊断建议：若需确认崩点是 dll 内部 OOB 还是仍残留 cross-CRT alloc/free，启用 Windows
**Application Verifier / PageHeap (Full)** 给 host exe (`gflags /p /full rfsim_tests.exe`)，
跑累积场景，崩点的栈帧一端是否还在 bsim4.dll 内即可二分。

---

## KI-3 — BSIM4 N≥15 单进程冷启动不稳定（host workaround 无能为力）

| 项 | 内容 |
|----|------|
| 触发用例 | `LargeCircuitBsim4.A3_NmosPullupBuffer20_HEAVY` (N=20)、`A1_InverterChain15_HEAVY` (N=15)、`S1_InverterChainGrid` (含 N=12/15/20 段) |
| 现象 | **单进程冷启动**：~50-80% 概率首次即 SEH 0xc0000005（A3 单跑 5 次仅 1 次 PASS）；与 KI-2 累积型不同，**新进程里也会崩**。崩点栈仍在 host `solveDcOp` → BSIM4 eval 链 |
| 与 KI-2 区别 | KI-2 是 cross-CRT 主因（S2 MSVC 切换根治）+ OSDI destroy-hook 缺失累积型（S2+ 路径 A reload workaround 根治）。KI-3 是 BSIM4/OpenVAF 在 N≥15 多实例 + 大摆幅 + 低 gmin 下的**算法/dll 内部固有不稳定**，host 侧任何 reload/warmup 都无法消除 |
| 调查证据 | 见 `docs/flake_investigation_0621.md` 第五节"E1-E15"。warmup+reload 组合实测：A3 冷启动 0/3 PASS；纯 reload 实测：A3 单进程首次 ~20% PASS；`gtest_repeat=3` 后两轮 PASS（reload 起作用）。结论：reload 解决累积型，**不解决**冷启动 |
| 已部署缓解 | S2+ 路径 A `OsdiLibrary::reload()`（每用例前 FreeLibrary+LoadLibrary），消除累积型；本 KI-3 残留 |
| 未完工修复 | (1) **OpenVAF 上游**：BSIM4 v4.8 在 N≥15 大摆幅下的 Newton limiting 内部断言路径稳定性；(2) **算法层**：HB-NL 在低 gmin × 大摆幅下的 trust-region/LM 替代 line search（plan0621-v4.md KI-1 路径 A，S3）；(3) **PageHeap Full 二分**确认 dll 内部具体越界点（需 Windows Debugging Tools 安装，S3） |
| SKIP gate | `A3_NmosPullupBuffer20_HEAVY` / `A1_InverterChain15_HEAVY` 走 `heavyEnabled()` gate (RFSIM_FORCE_HEAVY=1)；CI 默认不参与。`S1_InverterChainGrid` 在 HEAVY 下扩展网格到 N=20，CI 默认仅 N∈{2,4,6,8,10} |
| 主参考 | `docs/flake_investigation_0621.md`；`status0621-v3.md` S2+ 落地清单 |

---

## 红线与回归基线

- 默认 ctest 必须 **102/102 PASS**（S2+ 路径 A 解锁 EightFingerBalanced + SelfBiasedCascodeStack5 后，比 v5/S1 的 100 多 2 项；不含 HEAVY / FORCE_* 用例）。
- `RFSIM_FORCE_HEAVY=1` 下，除 KI-1 / KI-3 明示用例（A3/A1_15_HEAVY/S1_Grid 的 N≥15 段）外其余必须 PASS。
- KI-2 已通过 S2 (MSVC /MD) + S2+ (路径 A reload workaround) 双管齐下根治。
- 任何 PR 增删 KI 条目时同步更新 `plan0621-v4.md` §3 优先级矩阵和本文件。
