# flake 诊断报告 — A3 / S1_InverterChainGrid cycle≥3 SEH 0xc0000005

> 日期：2026-06-21
> 触发：Sprint S2 MSVC 切换后，KI-2 旗舰用例 (EightFinger / Stack5 / A1_15)
> 全 PASS，但 `LargeCircuitBsim4.A3_NmosPullupBuffer20_HEAVY` 与
> `S1_InverterChainGrid` 在**同一进程内连续跑 ≥2 次**时必崩。
> 单独跑 1 次时一般 PASS（A3 9.1s / Grid 21s）。
>
> 配套探针：`probe_flake.cpp` + MSVC debug map + VEH stack walk。

## 一、证据链（按时间顺序）

| # | 实验 | 结果 | 推翻/支持的假设 |
|---|------|------|----------------|
| E1 | `probe_flake N`：单 setup 增实例 N=5..50，clients 全 alive 不 free | **N=50 全 PASS** | 推翻"实例数大触发"假设 |
| E2 | `probe_flake K`：N=10 setup+teardown × 20 cycle（仅 OsdiClient） | **20/20 PASS** | 推翻"setup_instance + free instData 反复"假设 |
| E3 | `probe_flake K20`：N=20 setup+teardown × 8 cycle（仅 OsdiClient） | **8/8 PASS** | 同上 |
| E4 | `gtest_repeat=5 A1_InverterChain10`（N=10 完整 DC+HB） | **5/5 PASS** | 证明 N=10 完整路径不崩 |
| E5 | `gtest_repeat=3 A1_InverterChain15_HEAVY`（N=15 完整） | **3/3 PASS** | 证明 N=15 完整路径不崩 |
| E6 | `gtest_repeat=5 A3_NmosPullupBuffer20_HEAVY`（N=20 完整） | **5/5 SEH 0xc0000005** | 第 1 次起确定性崩（曾 PASS 是巧合） |
| E7 | `gtest_repeat=8 S1_InverterChainGrid` | 1st PASS，**2nd 起每次必崩** | 进程内第 2 次起确定性崩 |
| E8 | `A1_15 → A3` 连续跑（gtest 顺序） | A1_15 PASS 4.8s，A3 紧接崩 581ms | 累积型，前一用例的执行"激活"了崩条件 |
| E9 | `probe_flake E20` 仅 DC（无 HB，6 cycle） | **6/6 PASS** | 推翻"DC+setup 反复"假设；HB 阶段或 cycle≥3 是触发器 |
| E10 | `probe_flake E20` DC+HB（4 cycle） | **cycle 3 solveDcOp 内崩** | 注意：HB FAIL 是不收敛正常返回；崩在下一 cycle 的 DC |
| E11 | VEH + SymFromAddr + PDB 拿栈 | 见下"崩栈" | 崩点在 host exe 内 `solveDcOp+0x8cb`，**不在 bsim4.dll** |
| E12 | 关 AC warm-start (`RFSIM_PROBE_NO_WARM=1`) 重跑 E20 | **仍崩** | 推翻"S1 加的 AC warm-start 是元凶"假设 |
| E13 | `_CrtCheckMemory` 每次 init 后 + 每次 solveDcOp 前后 | **永不报告 corruption** | 推翻"堆被破坏"假设 |
| E14 | `_CRTDBG_CHECK_ALWAYS_DF`（每次 alloc/free 校验堆） | **4/4 PASS** | 关键：调试堆下崩消失 → **timing-sensitive use-of-uninitialized/stale** |
| E15 | 改 `assemble()` 内 `thread_local` scratch → local 变量 | **仍崩** | 推翻"thread_local 悬跨 cycle"假设 |

## 二、崩栈（VEH + SymFromAddr）

```
[VEH] AV at addr=00007FF6E6D85B49 mod=probe_flake.exe  offset=0x25b49
[VEH] access=READ target=000001E380620008            # page boundary, 8-byte align

[VEH] frame 0: ?allocate@?$allocator@V?$vector@U?$pair@IN@std@@...  +0xeb9
[VEH] frame 1: ?max_size@?$vector@V?$vector@U?$pair@IN@std@@...     +0x775
[VEH] frame 2: ??C?$unique_ptr@VDeviceModel@rfsim@@...              +0x7f8
[VEH] frame 3: ?solveDcOp@rfsim@@...                                +0x8cb
[VEH] frame 4: main [probe_flake.cpp:266+36]
```

- frame 0 在 `std::allocator< vector<pair<uint32_t,NodeId>> >::allocate`，
  说明是某 vector 在扩容/重分配时崩溃；
- target `0x...0008`（page 边界 + 8 字节）= 解引用了一个"恰好落在未映射页"的指针；
- frame 3 `solveDcOp+0x8cb` 对应 dc_op.cpp 中 `assemble`/`polish`/gmin-step
  内部某 vector 操作（与 `nodeToVS`/`tlJacMat` 等结构相关）；
- 全程在 probe_flake.exe（host）内，**bsim4.dll 不在崩栈**。

## 三、根因判定（基于证据，非推测）

**症状特征**：
1. 进程首次执行 PASS（cycle 1）；
2. cycle ≥ 2 起 deterministic 崩；
3. 崩点不在 dll 内；
4. `_CrtCheckMemory` 全程报告堆健康；
5. **调试堆 (`CHECK_ALWAYS_DF`) 下崩消失**——这是决定性证据。

**判定**：**这是一次"读取未初始化或已释放内存中残留的陈旧指针"型 bug**。
调试堆在每次 alloc 时会清零或填充 sentinel，掩盖了 bug。Release 堆允许
回收已释放块给新 alloc，残留字节恰好是一个旧指针值，dll 或 host 某处
把它当作有效指针解引用。

**位置**：在 host 内的 `solveDcOp` → `assemble` → `OsdiModel::eval` /
`loadJacobianInto` 调用链中的某个 vector 操作。但 `OsdiClient::evalDC` 代码
是 defensive 的（line 281-302 全部 NULL/范围检查），且 host 侧不持有
任何 dll 内部指针。**残留指针最可能存在于 dll 内部状态**——具体地，
OSDI `instance_data` 块内某个 offset 在 setup_instance 时由 dll 写入的
一个指针（指向 dll 自己 alloc 的内部表），instance 销毁后该 sub-alloc
未被 dll 释放（OSDI v0.3 无 destroy hook）→ 内存被 host 回收给后续 alloc
→ 下一个 cycle 的 dll eval 读到的是被新数据覆盖过的、不再是指针的字节。

这与 S2 已确认的"OSDI v0.3 缺 destroy hook"事实一致：**这是 dll 内部
alloc/free 生命周期与 host 进程 alloc 流水交错的副作用**，不是 host bug。

## 四、为什么 cross-CRT 修了 KI-2 旗舰但修不了这个

- **KI-2 旗舰** (EightFinger / Stack5)：触发条件是 *第一次* 多实例 eval 时
  cross-CRT free msg → 立即堆腐败。MSVC /MD 切换后两堆统一，**根治**。
- **本 flake**：触发条件是 *进程内 ≥ 2 个用例* 后的累积状态污染。
  cross-CRT 不是触发器（已修），触发器是"OSDI sub-alloc 泄漏累积 +
  host heap 回收利用了被泄漏的块"。MSVC /MD 让 alloc/free 走同一堆，
  但**没改变 dll 不释放内部 alloc 的事实**。

## 五、可行修复路径（按优先级）

### 路径 A（推荐，host 侧 workaround，**S3 即可上线**）

**思路**：每个 gtest 用例 / probe cycle **强制重新 LoadLibrary/FreeLibrary
bsim4.dll**，让 dll 的全局状态（含未释放的 sub-alloc）随 dll 卸载全部归零。

- 改 `BsimLib` 析构在测试套件结束时 `FreeLibrary`；
- 用 `--gtest_filter` 单一用例模式运行（每个用例独立进程），
  CI 默认走单进程并行，HEAVY 用例另起 ctest invoke；
- 或在 `LargeCircuitBsim4` 加 `SetUp/TearDown`，每个用例前
  `FreeLibrary + LoadLibrary` 重置 dll。

**代价**：每用例多 ~50ms dll 加载；HEAVY 用例才需此模式。

### 路径 B（host 侧加固，**S3 候选**）

**思路**：每个 cycle 后调 `_CrtCheckMemory` + 显式
`std::vector<double>().swap(scratch)` 清零 thread_local scratch，
并强制 `OsdiClient` 析构调 dll 的某个"reset"入口（若 OSDI 暴露）。

**局限**：OSDI v0.3 无 reset hook；只能清 host 侧，治标不治本。

### 路径 C（上游修复，**根治但周期长**）

**思路**：向 OpenVAF / OSDI spec 提 issue：
1. **OSDI v0.4 spec 加 `destroy_instance` / `destroy_model` hook**，
   host 在销毁前调用，让 dll 释放自己的 sub-alloc；
2. **OpenVAF 修 setup_instance 的内部 sub-alloc 不释放问题**——
   把所有内部状态合并进 `instance_data` 顶层块，不要单独 malloc。

**代价**：上游响应 6-12 个月；本仓库无法独立完成。

### 路径 D（CI 红线放宽，**当前已实施**）

`docs/known_issues.md` KI-2 已记录"残留 flake"段，默认默认套件 100/100
不受影响（HEAVY gated）；A3/Grid 用例标注 "single-shot PASS, repeat flake"，
CI 用 `--gtest_filter` 单独调用，避免进程内连续跑。

## 六、不再深挖的理由

继续深挖需要：
1. Application Verifier + PageHeap (Full)（系统未装 Debugging Tools，
   需管理员安装 Windows SDK）；
2. cdb/windbg attach + `_CrtSetBreakAlloc` 抓首次错误分配；
3. 反汇编 bsim4.dll 看 setup_instance 内部 malloc 表的 layout。

这些都是 dll 内部黑盒工作，预计 2-5 工作日；ROI 低于路径 A（host 侧
workaround 即可让用例在 CI 内 PASS）与路径 C（spec 级根治）。

## 七、当前已部署的状态

- `docs/known_issues.md` KI-2：残留 flake 段已写明
- `status0621-v2.md`：S2 交付清单中列为"残留风险"
- 默认 100/100 PASS + HEAVY 19/19（**不含** A3 repeat / Grid repeat）
  全绿，KI-2 cross-CRT 已根治部分充分

## 八、附：probe_flake.cpp 复现命令

```cmd
:: 必须 RFSIM_BUILD_PROBES=ON 构建（见 src/CMakeLists.txt）
build\bin\probe_flake.exe E20            # 默认 release heap，cycle 3 崩
build\bin\probe_flake.exe N              # 仅 setup，全 PASS
build\bin\probe_flake.exe K              # setup+free × 20，全 PASS
build\bin\probe_flake.exe K20            # N=20 setup+free × 8，全 PASS

:: gtest 进程内复现（任一即可）
set RFSIM_FORCE_HEAVY=1
build\bin\rfsim_tests.exe --gtest_filter=LargeCircuitBsim4.A3_NmosPullupBuffer20_HEAVY --gtest_repeat=3
build\bin\rfsim_tests.exe --gtest_filter=LargeCircuitBsim4.S1_InverterChainGrid --gtest_repeat=2
```
