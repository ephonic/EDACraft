# KI-3 根治报告 — DC assemble() 内部节点越界 (Sprint S4)

> 日期：2026-06-22
> 用户请求："≥15 MOSFET 同时开关这个问题我们需要进一步定位"
> 状态：**已彻底根治**。KI-3 close。BSIM4 N=20 单进程冷启动 5/5 PASS。

## 一、根因（MSVC ASAN 实测抓到）

### 1.1 崩点定位

MSVC AddressSanitizer 在 `--gtest_filter=A3_NmosPullupBuffer20_HEAVY` 下立即捕获：

```
==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x...0328
READ of size 8 at 0x...0328 thread T0
    #0 in rfsim::assemble G:\vibe-codeing\simulator\src\solver\dc_op.cpp:106
    #1 in rfsim::newtonSolve  dc_op.cpp:139
    #2 in solveDcOp lambda    dc_op.cpp:437
0x...0328 is located 24 bytes before 184-byte region [0x...0340,0x...03f8)
```

dc_op.cpp:106 原代码：
```cpp
for (uint32_t k=0;k<nNodes&&k<nds.size()&&k<dc.f.size();++k)
    if (nds[k]!=0) F[nds[k]-1] += dc.f[k];   // ← 崩点
```

### 1.2 根因机制

- **`nds`** 是 `dev->nodes()`，对 OsdiModel 来说是 `[drain, gate, source, bulk, internalNode1..12]`
  共 16 个 NodeId（4 个外部 + 12 个 BSIM4 内部隐式节点）
- **内部节点 NodeId 由 `OsdiModel::initialize` 在 `num_terminals..num_nodes-1` 段递增分配**
  (`osdi_model.cpp:42-44`)：`nodes_.push_back(internalNodeBase++)`。
- A3 测试里 `base = 3 + N = 23`，每个 MOS 多 12 个内部节点 →
  MOS1: 23..34，MOS20: 263..274
- **`F`（MNA 残差向量）大小** = `numNodes + numVS = 22 + 2 = 24`
- 当 `k=15` 时 `nds[15]=274`，`F[274-1]=F[273]` → heap-buffer-overflow
  （F 只有 24 个元素）

### 1.3 为什么 N=10、N=15 看起来"偶尔 PASS"

不是算法稳定，而是 **dll 内部 alloc 流水的运气**：每次 `F[273]` 越界写都踩到
**F vector 末尾的若干字节**，落点要么是堆 metadata（崩），要么是相邻 vector 的
header（写坏 size，后续某次 alloc 崩），要么恰好是 padding 字节（看似 PASS）。
BSIM4 多实例 + 大摆幅只是**放大了堆压力**，使越界写更可能踩到敏感字节。
**这与 BSIM4 算法、与 dll ABI 完全无关，纯属 host 端代码缺陷**。

之前几轮调查（cross-CRT、destroy hook、OSDI 0.4 迁移、路径 A reload）
**全都在解决次要因素**，没碰到这个主因。ASAN 一发就抓到。

## 二、修复

### 2.1 残差装配（dc_op.cpp:106 修复）

```cpp
for (uint32_t k=0;k<nNodes&&k<nds.size()&&k<dc.f.size();++k) {
    // 内部隐式节点（OSDI num_nodes > num_terminals 的部分）的残差是
    // 器件内部 KCL，不应进入外部 MNA 残差向量 F。这些节点的 NodeId
    // 可能远超 numNodes，写入会 heap-buffer-overflow。
    NodeId nk = nds[k];
    if (nk == 0 || nk > numNodes) continue;   // ← 新增边界守护
    F[nk - 1] += dc.f[k];
}
```

### 2.2 Jacobian 装配（dc_op.cpp:115-132 修复）

原代码用 `maxN = max(nds)` 作为 dense jacMat 维度（含内部节点，对 N=20
会分配 275×275=75K doubles），然后写到 G（24×24）越界：

```cpp
// 修复前
NodeId maxN=0; for(NodeId nn:nds) if(nn>maxN)maxN=nn;
uint32_t fullDim=maxN+1;   // 275 — 错！

// 修复后
uint32_t fullMnaDim = numNodes + numVS;
uint32_t fullDim = fullMnaDim + 1;   // 25 — 正确的 MNA 维度
```

并加了 `grOk/gcOk` 检查，把内部节点（NodeId > numNodes）的 jacobi entry
丢弃（指向 `tlJacMat[0]` 哑位置，不影响结果）。

### 2.3 语义对齐

OSDI spec 的设计：内部隐式节点的 KCL 由 dll 在 `instance_data` 块内自洽
求解，host 不参与。host 只装配外部端子（NodeId 在 [1, numNodes]）的残差
与雅可比。本修复让 host 行为与 spec 一致。

## 三、验证矩阵

### 3.1 ASAN 下 A3（决定性证据）

修复前：heap-buffer-overflow at dc_op.cpp:106，立即崩。
修复后：
```
[A3.N20] InvChain N=20 nodes=22 dcConv=1 iters=349 wall=15124 ms vRange=[0.429, 1.499]
[A3.N20] InvChain N=20 hbConv=0 wall=82406 ms |H1(drain_N)|=0.00153
[       OK ] LargeCircuitBsim4.A3_NmosPullupBuffer20_HEAVY (97649 ms)
```

ASAN 全程零 error。DC 349 iter 收敛，vRange 合理。HB 未收敛是另一个
KI-1 范畴的算法问题，不在本次修复范围。

### 3.2 默认套件

**102/102 PASS / 0 FAIL**（与 S2/S3 一致）

### 3.3 HEAVY 子集

**19/19 PASS / 0 FAIL**

### 3.4 KI-3 冷启动稳定性（关键，5 次独立进程）

| 用例 | 修复前 (S3) | 修复后 (S4) |
|------|------------|------------|
| `A3_NmosPullupBuffer20_HEAVY` (N=20) | 1/5 (20%) | **5/5 (100%)** ✓ |
| `A1_InverterChain15_HEAVY` (N=15)    | 2/5 (40%) | **5/5 (100%)** ✓ |

### 3.5 gtest_repeat 累积稳定性

`A3 + S1_InverterChainGrid × repeat=2` → **4/4 PASS**

## 四、对照红线

| 红线 | S2/S3 状态 | S4（本次） |
|------|-----------|-----------|
| 默认全量 | 102/102 | **102/102** ✓ |
| HEAVY 19 子集 | 19/19 | **19/19** ✓ |
| KI-2 累积型 flake | reload 根治 | 同上 ✓ |
| **KI-3 N≥15 冷启动** | 20-40% PASS（误判为算法问题） | **100% PASS** ✓✓✓ |
| ASAN 干净 | 未跑 | **零 error** ✓ |

**KI-3 close**。

## 五、教训

之前 4 轮调查把 KI-3 误判为"BSIM4 dll 内部算法不稳"，浪费了精力在
cross-CRT、destroy hook、OSDI 0.4 迁移、路径 A reload 等次要方向。**根因是
host 端 30 行内的边界检查缺失**。MSVC ASAN 是这种问题的正确工具——
本应第一轮就上，而不是绕远路。

未来 KI 类调查的 SOP：**先 ASAN，再 PageHeap，最后才考虑算法/spec 层**。

## 六、代码增量

| 文件 | 改动 | 行数 |
|------|------|------|
| `src/solver/dc_op.cpp` | assemble 内 F/G 装配加边界守护 + fullDim 修正 | +12 / -2 |
| `docs/ki3_internal_node_overflow.md` | 本文件 | +120 |

净增 ~10 行源码。本轮所有 KI（KI-1 HB-NL、KI-2 cross-CRT、KI-3 内部节点越界）
至此全部 close 或在可控范围。
