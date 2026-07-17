# PDK 端到端状态（真实 PDK 加载）

日期：2026-07-17。在 level=54 路由 + `.lib` corner 基础设施完成后，尝试加载真实 TSMC 28nm PDK。

## TL;DR

| 维度 | 状态 |
| --- | --- |
| level=54 路由 + 简单 PDK 参数集（自建网表） | ✅ DC OP 收敛，器件导通（A/B 对比 bit-identical） |
| 真实 PDK `toplevel.l` + TT corner | ❌ 受阻于 HSPICE `.lib` 自引用嵌套语义（corner 块 `.lib` 同文件） |
| 本次修复（lexer + 路径 + 递归保护） | ✅ 解析不再崩溃，回归 157/0/51 无退步 |
| 剩余阻塞 | `.lib` 文件重入语义（file+block 粒度，非 file 粒度） |

## 本次诊断与修复

### Bug 1：lexer 不认单引号字符串

PDK `.lib './crn28.l' X` 用单引号。原 lexer 只认双引号 → 单引号路径被拆成多 token → `.lib` 失效。
**修复**：`lexString` 支持 `"` 和 `'`（记录开引号字符，匹配同类闭引号）。

### Bug 2：`.lib` 路径相对 CWD 而非当前文件目录

`toplevel.l` 里 `.lib './crn28.l' X`，`./crn28.l` 应相对 `toplevel.l` 目录（HSPICE 语义）。
**修复**：`resolveLibPath(path)` 优先相对 `filename_` 目录解析，再回退 CWD。

### Bug 3：`.lib` 自引用无限递归 → 栈溢出（exit 127）

PDK 文件 `cln28hpcp_hv..._2p1.l` 内 corner 块 `.lib 'cln28hpcp_hv..._2p1.l' setup_hv18`（引用同文件）。
**修复**：`libLoadingFiles_` 集合记录正在加载的文件；重复则跳过（warn）。

## 剩余阻塞：深度自引用嵌套的子解析器状态传播

修复后 PDK 不再崩溃（exit 0），`.lib` 文件缓存基础设施已就位（同文件只解析一次，按块名查询），但深度嵌套（3+ 层 `.lib 'samefile' BLOCK`）的子解析器 `.lib` 展开仍需迭代：

```
TTMacro_MOS_MOSCAP（embedded_usage.l）
  → .lib 'hv.l' TT_hv18          ✓ 缓存命中，展开 TT_hv18 块
    → .lib 'hv.l' MOS_hv18        ✗ 子解析器展开 TT_hv18 行时，嵌套 .lib 的子解析器状态传播未完整
      → .model nch_hv18.1 ...     ✗ 未到达
```

**已实现**：`loadLibFileToCache`（文件→块定义缓存，只解析一次）+ `parseLibSelect` 从缓存取块展开。这正确处理了文件粒度自引用（不再重解析）。

**待迭代**：子解析器（展开块内容的临时 Parser）在处理块内嵌套 `.lib` 时，其 `parseLibSelect` 调用需要正确传播 `libLoadingFiles_` + 路径解析上下文，使第 3+ 层嵌套也能从缓存取块。当前 1-2 层嵌套工作正常（单元测试 + 简单 PDK 验证），3+ 层需调试子解析器状态。

## 仍验证可用的 PDK 能力

- **level=54 路由**：`.model nch nmos (level=54 ...)` → bsim4va，3 单元测试 + 简单 PDK 参数集 DC OP 验证（A/B 对比 bit-identical with 直接 file=）。
- **`.lib` corner 选择**：同文件块 + 跨文件块 + 文件缓存，3 单元测试 + 浅层嵌套工作正常。
- **表达式参数求值**：多遍 `.param`（C2），简单表达式链验证通过。
- **`.lib` 文件缓存**：同文件只解析一次，自引用不重载（关键 PDK 基础设施）。

## 当前回归

**182 tests, 157 PASSED / 0 FAILED / 51 SKIPPED**（无退步）。
本次 lexer/路径/递归/文件缓存修复均被现有测试覆盖（无新退步）。

## 后续（独立 sprint）

PDK 完整端到端需 `.lib` 文件重入语义（file 缓存 + block 选择）。这是解析器架构调整，工作量中等（重构 `parseLibSelect` 为"文件缓存 + 块查询"模型），需配套测试覆盖自引用嵌套。
