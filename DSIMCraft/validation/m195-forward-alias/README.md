# M195：前置 class 别名与 process 关联键

生产实现 `1287aa828e04b0657126dcb4653ad04ed8f63d8b` 已推送 main。本批优先解除未修改公开 UVM 的类型展开阻塞，不宣称完整 UVM 或性能提升。

- 前置 class 到后续参数化 typedef 的共享语义类型绑定，覆盖别名链、属性初始化、变量/形参/返回值、ref、赋值/转换、队列、class 键及克隆隔离。
- 内建 `process` 首次出现在关联索引声明中时按类型解析，支持参数化类属性、读写、foreach、游标及类型检查。
- 发布器将命令超时传到受影响回归，保留默认 180 秒；修复 Linux 外层时限增大而内部仍固定 180 秒的验收问题。

## 本地冻结验收

Mac 冻结源码 `/private/tmp/dsim-m195-src`，1333 输入，SHA256 `2fa1cebc0287cbc9a9fd2476a2b158b815a902aee3c148d9e525ca173c6870cb`。稳定入口 `~/vibe-coding/dsim-test/bin/dsim` 已切换至 `20261031T074949092417Z-2fa1cebc0287`。

| 验收 | 结果 |
| --- | --- |
| class_forward | 28 模型、506 捕获、23 编译拒绝、1 回滚/1 提交 |
| typed_containers | 14 模型、256 捕获、23 编译拒绝、2 回滚/2 提交 |
| mandatory | RTL semantic cleanup、format parser bundle、native Liberty DB 全部通过 |
| 总计 | 42 模型、762 捕获、46 编译拒绝、3 回滚/3 提交 |
| 实际稳定入口 | 五个新增模型重新编译/执行，CPP 与冻结候选一致，异步波形解码一致；公开 UVM 入口复测保留相同后续阻塞 |
| 跨端参考 | 129 CPP、762 解码波形摘要，编码字节摘要另存；Linux 跨端比对现已通过 |

开发构建另外完整执行同一 28 模型组。前端及原生 parser 的 ASan/UBSan 通过；五新模型 90 捕获、23 反例，15 CPP 与发布候选相同，重复解析/失败清理通过。该次生成模型以常规 O2 编译执行，未宣称运行时消毒检查；生产 runtime 未修改。leak 检查未启用。

## VCS 与原版 UVM

VCS W-2024.09 三份未修改同源正例 `process_keys/signatures/runtime_init` TRACE 一致。独立 module/package 的前置 class→typedef 探针均在 VCS 报 IPD/SV-UFCD，作为**源码兼容扩展差异**保留，不计为 VCS 对齐通过。循环别名、非 class 目标及未完成别名用作模板实参会明确拒绝；其余边界见 [实现说明](../../docs/forward-class-aliases.md)。

公开 Accellera UVM 2020.3.1 仍为原版 166 依赖、1,888,084 字节，预处理 SHA `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`。普通前端、消毒前端及稳定入口均越过 event_pool 与 process 索引，首错为 `uvm_reg_model.svh:300`：`UVM_CVR_ALL=-1` 的无符号枚举范围检查。未输出原生 C++，完整 UVM 仍不能运行。

## 103 状态

M192、M193、M194 的 Linux 候选已确认失败：分别在 call_arguments、integral_keys、multidim_associative 中触发内部 180 秒模型编译超时，未激活。保留 [原始失败摘要](linux-observed.json)，未修改它们的冻结源码或收据。

M195 首个 Linux 候选两组和跨端 129 CPP/762 捕获通过，但配置复核发现未携带现有稳定版的 Z3；多维组因此只运行 7 模型/128 捕获，漏掉两份 solver 语料。候选曾临时切换入口进行实际入口复验，已停止该流程、撤回候选并恢复 M190，见 [撤回记录](linux-withdrawn.json)。不将它计为发布成功。

修正候选沿用现有 `/apps/EDAs/own/dsim/deps/z3-4.15.4`，Intel 构建、两组选定回归及 mandatory 全部通过；129 CPP、762 解码捕获跨端一致，本批编码字节亦一致。额外 multidim_associative **九模型/164 捕获/13 拒绝/一次回滚提交**通过，包含 constraints 和 sparse_constraints。五个实际稳定入口模型、公开 UVM 前后复测及根目录别名检查通过。

103 稳定入口已激活 `20261031T081112764104Z-2fa1cebc0287`。见 [最终结果](linux-final.json)、[跨端比对](linux-cross-platform.json)、[多维回归](linux-multidim.json)、[入口复验](linux-entry.json)、[发布收据](linux-release.json)。被撤回的首候选仍保留历史记录，不计为成功。

后续继续无符号枚举初始化语义与原版 UVM 展开，同时保留 covergroup、virtual interface、完整约束/SVA/DPI/VPI 等缺口。不能根据首错推进推断功能完备率或速度。

## 收据与原始证据

`mac-release.json`、`mac-entry.json`、`mac-reference.json`；两组结果；`asan.json`；`vcs.json`；普通/消毒 `public-uvm*.json`；`progress.json` 和发布脚本。原始 CPP、波形、输出、VCS 日志与测试源保存在 `~/vibe-coding/dsim-test/evidence/m195-forward-alias/mac`，由内容 SHA 清单核验，目录见 `archive-catalog.json`。
