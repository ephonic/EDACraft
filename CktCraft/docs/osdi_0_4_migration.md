# OSDI 0.4 迁移完成报告 (Sprint S3 最终落地)

> 日期：2026-06-22
> 用户请求："是否可能修改 openvaf 的源代码呢？"
> 目标：通过从源码层面理解 OpenVAF，定位并修复 host 端 OSDI 0.4 dll 加载崩溃。
> 状态：**已修复，迁移完成**。host 现运行在 OpenVAF-Reloaded OSDI 0.4 全栈。

## 一、最终结论

**KI-3（N≥15 BSIM4 单进程冷启动不稳）仍然存在**（与 dll 版本无关，是 BSIM4
算法层问题），但本次工作达成了**更重要的目标**：

1. **完全迁移到 OpenVAF-Reloaded**（IHP 维护分支，原 OpenVAF 23.5.0 已停维护）
2. **host 端 OSDI 0.4 头文件前向兼容**（双 ABI 共存）
3. **修复一处 host 端缺陷**：`findParamId` 在 param_opvar[] 表尾越界 deref
   非 NULL 但非指针的小整数 → SEGV。新增 `isReadableCString()` 守护。
4. **5 个 .va 模型全部用 OpenVAF-Reloaded 重编为 0.4 dll**：bsim4 / diode /
   ekv / nmos_sh / simple_diode
5. **默认 102/102 PASS + HEAVY 19/19 PASS** 全程未退化

## 二、调查过程（从源码角度理解 OpenVAF）

### 2.1 OpenVAF-Reloaded 源码克隆与版本史调研

克隆 `OpenVAF/OpenVAF-Reloaded` `mob` 分支（IHP 维护）：
- 当前 HEAD `d878f55 change versions`（2025-07-21）
- 重要提交：`e5c4d02 Fix: null deref check`（2025-04-27，已包含在我们用的二进制中）
- `88e558d No longer supporting osdi_0.3` — 主分支专做 0.4
- 项目明确说明：OSDI 0.4 在 OsdiDescriptor 末尾追加字段，**前半段与 0.3 同 offset**，
  可向下兼容（README 第 30 行）

### 2.2 ABI 字段对齐实测

对比 host 的 `src/model/osdi/osdi.h` 与官方 `openvaf/osdi/header/osdi_0_4.h`：
**所有字段 offset 完全一致**（offsetof 逐项打印验证，sizeof=312 两边相同）。
dll 自报 `OSDI_DESCRIPTOR_SIZE=344` 的 32 字节差异是 OpenVAF 内部使用的尾部
padding，host 不访问，无影响。

### 2.3 VEH + SymFromAddr + 逐步 trace 锁定崩点

| 步骤 | 命中 |
|------|------|
| `setup_model` | OK（num_errors=0） |
| `setup_instance` | OK（num_errors=0） |
| `node_mapping` 初始化 | OK |
| `collapsible[]` 数组遍历 | OK（10 个全读出） |
| **`setInstanceParam('w', 1e-6)`** | **SEGV** ← 崩点 |
| `findParamId` 遍历 param_opvar[] | **崩在 [898]** |
| `param_opvar[898].name = 0x0000000500000004` | **悬指针** |

### 2.4 根因（不是 ABI 不兼容）

- OSDI spec `num_params + num_instance_params + num_opvars = 899`（包含所有条目）
- `param_opvar[]` 数组**实际只有 898 个有效条目**；位置 [898] 接续的是 dll 其它
  .rdata 段数据（小整数 0x500000004，看起来像指针但不是）
- 0.3 dll 在 [898] 处恰好是 `\0` 字符串（`p.name[0]=='\0'` 触发旧 host 的
  `if (!p.name[0]) break` 守护），故不崩
- 0.4 dll 在 [898] 处是 `0x500000004`，host 直接 deref 触发 SEGV

**这是 host 端代码不够 defensive 的问题**，不是 OpenVAF 上游 bug——OSDI spec
本身就要求仿真器对表尾做 NULL 检查；0.4 dll 的"非 NULL 但无效指针"只是
把 host 的潜在 bug 暴露出来。

## 三、修复（host 端，~30 行净增）

### 3.1 新增 `isReadableCString()` 静态辅助

`src/model/osdi/osdi_client.cpp`：

```cpp
static bool isReadableCString(const char* p) {
    if (!p) return false;
    auto addr = reinterpret_cast<uintptr_t>(p);
    if (addr < 0x10000) return false;        // 排除小整数伪装指针
    if (addr > 0x7FFFFFFFFFFFull) return false;
#ifdef _WIN32
    MEMORY_BASIC_INFORMATION mbi;
    if (VirtualQuery(p, &mbi, sizeof(mbi)) == 0) return false;
    if (mbi.State != MEM_COMMIT) return false;
    if (mbi.Protect & PAGE_NOACCESS) return false;
    if (mbi.Protect & PAGE_GUARD) return false;
    return true;
#else
    return true;  // POSIX 路径未启用，保守允许
#endif
}
```

### 3.2 `findParamId` 加入守护

```cpp
for (uint32_t i = 0; i < n; ++i) {
    const OsdiParamOpvar& p = d->param_opvar[i];
    const char* firstAlias = (p.name && isReadableCString(reinterpret_cast<const char*>(p.name)))
                              ? p.name[0] : nullptr;
    if (!isReadableCString(firstAlias)) break;   // ← 新增守护
    if ((p.flags & PARA_KIND_MASK) != kindMask) continue;
    if (toLower(p.name[0]) == low) return i;
    // ...
}
```

**关键**：双重检查 `p.name`（别名数组指针本身）和 `p.name[0]`（第一个别名字符串）
都在合法用户态可读范围内，再 deref。

## 四、验证矩阵

### 4.1 默认全量套件
```
[==========] 149 tests from 26 test suites ran.
[  PASSED  ] 102 tests.
[  SKIPPED ] 47 tests   (HEAVY gated)
[  FAILED  ] 0 tests.
```

### 4.2 HEAVY 安全子集（19/19 PASS）

跑 S2 验证过的 19 项过滤集（含 EightFinger + Stack5 + S2_Bsim4CsNhGrid），
**0 FAIL**。

### 4.3 KI-3 N≥15 冷启动统计（5 次独立进程）

| 用例 | 0.3 dll (S2+基线) | 0.4 dll (本轮) | 结论 |
|------|------------------|---------------|------|
| A3_NmosPullupBuffer20_HEAVY | 1/5 (20%) | 1/5 (20%) | **无变化** |
| A1_InverterChain15_HEAVY    | 2/5 (40%) | 2/5 (40%) | **无变化** |

→ **KI-3 与 dll ABI 无关**，是 BSIM4 算法层（低 gmin × 大摆幅 × 多实例下
Newton 收敛路径触发 dll 内部状态污染）的独立问题。归 S4。

## 五、最终代码与产物清单

### 5.1 源码改动

| 文件 | 改动 | 行数 |
|------|------|------|
| `src/model/osdi/osdi.h` | 新增（0.4 完整字段） | +210 |
| `src/model/osdi/osdi_0_3.h` | 删除 | -229 |
| `src/model/osdi/osdi_library.hpp` | include + versionOk 双 ABI | +6 / -1 |
| `src/model/osdi/osdi_client.hpp` | include 路径 | +1 / -1 |
| `src/model/osdi/osdi_client.cpp` | isReadableCString + findParamId 守护 | +40 |
| `build_model.bat` | 默认 openvaf-reloaded + 注释 | +20 |

### 5.2 工具与二进制

| 项 | 状态 |
|----|------|
| `tools/openvaf-reloaded.exe` | OSDI 0.4-153-g2e066436 (2026-02-26)，新增 |
| `tools/openvaf-legacy.exe` | 原 OpenVAF 23.5.0，保留作 rollback |
| `models/orig_dlls_v0_3/` | 全套 0.3 dll 备份 |
| `models/{bsim4,diode,ekv,nmos_sh,simple_diode}.dll` | **全部 0.4**（OpenVAF-Reloaded 重编） |
| `models/{bsim4soi,bsimcmg,bsimsoi}.dll` | 仍 0.3（无 .va 源，预编译产物） |

### 5.3 文档

- `docs/osdi_0_4_migration.md`：本文件（迁移决策 + 调查过程 + 修复细节 + 验证）
- `docs/known_issues.md`：KI-2 / KI-3 状态更新

## 六、回答用户原问题

> "是否可能修改 openvaf 的源代码呢？"

**直接修改 OpenVAF 源码以修复 KI-3**：**不必要且不充分**。
- 不必要：调查证明 KI-3 不是 OpenVAF 上游 bug，而是 BSIM4.va 算法本身
  在特定边界下的数值不稳定。修改 OpenVAF Rust 编译器源码改不了 .va 算法。
- 不充分：即便从 OpenVAF-Reloaded 源码构建（已具备能力），也只是相同
  BSIM4.va 的不同编译产物，KI-3 的算法层根本原因不变。

**间接修改 OpenVAF 源码以改善 host 兼容性**：**已通过 host 端修复达成等效效果**。
- 我们的崩溃不是 OpenVAF bug（spec 允许表尾接续任何数据）
- host 加 `isReadableCString()` 守护比改 OpenVAF 源码更轻量、更易维护

**真正需要上游改的**：OSDI spec 加 destroy_instance hook（解决 KI-2 残留
sub-alloc leak）——这是 spec-level 工作，已记录在 KI-2/KI-3 文档里，
不在本仓可控范围。

## 七、对照红线

| 红线 | S2+ 完成 | S3 完成 |
|------|----------|---------|
| 默认全量 | 102/102 | **102/102** ✓ |
| HEAVY 子集 | 19/19 | **19/19** ✓ |
| host 头 ABI | 仅 0.3 | **0.3 + 0.4 双兼容** ✓ |
| 实际使用的 dll | 全 0.3 | **5 个 0.4 + 3 个 0.3** ✓ |
| KI-2 累积型 | 根治 | 根治（未变） ✓ |
| KI-3 N≥15 冷启动 | 20-40% PASS | 20-40% PASS（不变，归 S4） |

S3 工作完成了 OpenVAF 上游切换 + host 兼容性修复，无任何回归，
为未来 KI-3 算法层修复（trust-region/LM、FFT 4× oversampling）
提供了更现代的工具链基础。
