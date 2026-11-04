# dsim 0.13.0 RTL 测试报告（v3 复测）

- v1: 2026-10-24, 二进制 20261024T024217767796Z-6a75b0556da2
- v2: 2026-10-24, 二进制 20261024T040222070894Z-bdce241a045f（修复版, sha256 43212ce7...）
- v3: 2026-10-24, 二进制 20261024T104159778536Z-e55af7d0b056（sha256 524e3f6d...）
- 复测探针: /tmp/dsim_regress/t01..t13 + h_* + deep* 系列

## v3 复测结果（相对 v2）

### 新修复（5 项 + 诊断）
| v2 缺陷 | v3 结果 |
|---------|---------|
| `package`/`import` 不支持 | ✅ 完全修复：多包、`pkg::` 限定访问、包内参数/typedef/函数均正确；与 struct/enum 组合集成通过 |
| `$random` 不支持 | ✅ 修复：含种子参数可复现（同种子同序列） |
| `$urandom`/`$urandom_range` 不支持 | ✅ 修复：边界正确（range(10,20) 落在界内） |
| struct 作 function 形参 | ✅ 修复 |
| `string` 类型 / enum `.name()` | ✅ 修复：`.len()`、拼接 `{a,"_",b}`、`==`/`!=` 比较均正确 |
| `--top` 不存在模块名报 unknown err | ✅ 修复："top module not found 'xxx'" |

### 仍不支持（v3 清单，报错均清晰带行列）
1. **并发断言**（`property`/`assert property`）— 语法错误
2. **`interface`/`modport`** — 语法错误（本轮新测，未支持）
3. 层次引用未打包数组元素（`u.mem[0]`）— "hierarchical observation requires a scalar or packed variable"
4. 层次引用 + 枚举方法组合（`dut.st.name`）— "member base is not a packed aggregate"
5. package 内可变变量 — "mutable package variables are not supported yet"（明确声明未支持）
6. 波形仍为专有 DWF 二进制容器，非标准文本 VCD

### 回归（7/7 通过）
fifo / alu(1029) / uart / fir(201) / cdc / svfeatures / fifo-task版 TB 全部 PASS；
package+struct+enum+hier-ref 集成设计（pkg_dut）PASS。

### 三轮累计观察
- 仿真语义始终正确：三轮共 7 处疑似失败全部为测试侧预期/typo 错误，dsim 计算无误
- 诊断质量逐版提升：v1 空消息/崩溃 → v2 行列+具体消息 → v3 明确"未支持"声明（如 mutable package variables）
- 语言覆盖快速收敛：v1 报告 13 项缺口，v3 仅剩 6 项（并发断言、interface、数组层次访问为影响最大的三项）

## 附：v1 缺陷复测结果（13 项，v2 时点）

### 已修复（7 项）
| # | v1 缺陷 | v2 结果 |
|---|---------|---------|
| A1 | **task 定义 → SIGSEGV 崩溃** | ✅ 完全修复：无参/带参/output 参数/内含 `@(posedge)` 时序控制的 task 全部正确执行；真实 FIFO TB（task tick/write/read）端到端通过 |
| B5 | 层次化引用不支持 | ✅ 大部分修复：标量/打包变量（`u.shadow`）、参数（`u.W`）可观测；⚠️ 未打包数组元素（`u.mem[0]`）仍不支持，报错清晰 |
| B7 | 复制个数拒常量表达式 `{(W-1){..}}` `{2*W{..}}` | ✅ 修复 |
| B8 | always_ff 目标带声明初始化器被拒 | ✅ 修复 |
| B10 | assert 动作块内非阻塞赋值被拒 | ✅ 修复 |
| B11 | `input var logic` 端口不支持 | ✅ 修复 |
| C12 | 空/unknown 错误消息 | ✅ 大幅改善：语义错误给出具体消息+行列（"identifier is unknown or not visible in this scope '$random'"），语法错误同时报拼接文件与原始文件名行号 |

### 未修复（仍不支持，但报错已清晰化）
| # | 项 | v2 报错形态 |
|---|---|----------------|
| B2 | `package`/`import` | 语法错误（行列正确） |
| B3 | `property`/`assert property` 并发断言 | 语法错误（行列正确） |
| B4 | `$random`/`$urandom`/`$urandom_range` | "identifier is unknown or not visible in this scope" |
| B6 | struct 作 function 形参 | 语法错误（行列正确） |
| B9 | enum `.name()` / `string` 类型 | "unknown integral type string" |

### 未变
- D14 波形：仍为专有 DWF 二进制容器（`DWF1P001` 头 + zstd/raw 负载），非标准文本 VCD（即使扩展名 .vcd）

### 新发现（v2 新增小问题）
- `--top <不存在模块名>` → `error[6305][0:0]: unknown err.`（应报 "top module not found"；v1 该场景为静默无输出+rc=0，v2 至少报错退出，但消息仍不可读）

## 附：v2 时点设计回归（6/6 通过）

| 设计 | 结果 |
|------|------|
| sync_fifo 16x8 | 6/6 PASS |
| alu 16bit 16op | 1029/1029 PASS |
| uart_tx 8N1+校验 | 10 字节全对 |
| fir4 3 级流水 | 201 样本对拍全对 |
| cdc_async_fifo+pulse_sync | 182 字节跨域 + 11/11 脉冲 |
| sv_features | PASS |
| （新增）fifo task 版 TB | ALL PASS |

## 附：v2 时点结论

修复版解决了 v1 最严重的问题：编译器崩溃、验证工作流关键的层次化引用、以及诊断消息质量。仿真语义保持正确（两轮共 5 处疑似失败均为测试侧预期错误，dsim 计算全部正确）。剩余缺口集中在 SV 高级特性（package/并发断言/随机系统函数/struct 形参/string）与标准 VCD 导出。
