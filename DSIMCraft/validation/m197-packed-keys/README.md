# M197：packed struct/union 关联键

为公开 UVM 的 `uvm_reg_map_addr_range` 接通 packed 聚合关联键，复用任意位宽整数键存储。foreach 索引及 locator 返回队列保留规范 aggregate 字段信息，整张映射复制按每一维检查键身份。元素按值转换可在同宽 packed 聚合/位向量之间进行，保留 ref 和 unpacked struct 的现有严格检查。

新增四个执行模型覆盖 160 位范围、signed/union/嵌套字段、33/65/129 位模块克隆、类类型参数、多维属性存储、遍历/游标/locator/复制及预测恢复。新增反例保留不同键类型的映射复制拒绝；unpacked struct 键仍是明确功能缺口。

未修改公开 UVM 已越过 packed 键，首错推进至 `uvm_cmdline_processor.svh:343` 的 string 队列 `push_back` 被按标量字符串方法处理。完整 UVM 仍不能运行。本批无性能结论。

## 冻结验收与 Mac 稳定版

生产实现 `5dd521be` 已推送 main，1346 个输入、源码 SHA256 `0c0d6ae7ece86e5fffea70d14b1185429f3b5bb8a312149c9cc8cb7db2be35b8`。Mac 稳定入口已更新至 `20261031T092634020074Z-0c0d6ae7ece8`。四个新增模型使用实际入口重新编译/执行，CPP、解码与本批异步编码波形均与冻结候选一致；公开 UVM 前后复验保持同一后续阻塞。

| 验收 | 结果 |
| --- | --- |
| integral_keys | 11 模型、202 捕获、15 拒绝、2 运行错误、2 回滚/2 提交 |
| multidim_associative | 9 模型、164 捕获、13 拒绝、1 回滚/1 提交 |
| typed_containers | 14 模型、256 捕获、23 拒绝、2 回滚/2 提交 |
| 合计 | 34 模型、622 捕获、51 拒绝、2 运行错误、5 回滚/5 提交 |
| mandatory | RTL semantic memory、format parser bundle、native Liberty DB 通过 |
| 前端 ASan/UBSan | 4 新模型、15 拒绝、重复解析/失败清理通过，4 CPP 与冻结候选一致 |
| VCS W-2024.09 | 4 个未修改同源执行模型 TRACE 一致；16 个边界探针中 14 个接收/拒绝一致，2 差异单列 |
| 跨端参考 | 109 CPP、622 解码捕获，编码字节摘要另存；Linux 尚待比对 |

包含两组约束模型，没有通过关闭 Z3 跳过约束验收。普通及消毒前端的公开 UVM 预处理仍为 166 依赖、1,888,084 字节、SHA `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`。生成模型运行时未做本批消毒验证，runtime 未修改，leak 检查未启用。

另执行三份值转换/别名探针的生成原生代码，均与 VCS 的 TRACE 一致。开发构建执行四新模型 74 捕获和原生 parser 清理，最终冻结批补入 ref 反例并完成全组验收。

## 保留的 VCS 差异与下一处缺口

`oracle-frontends.json` 分列 VCS 接受而 dsim 拒绝的 unpacked struct 键、不同 packed struct 类型的 ref 绑定；未将这两项计作对齐成功。整张映射的不同键身份复制则在双方共同拒绝；按值的 packed 队列转换在双方通过。原版 UVM 尚未完整编译运行。

下一处 string 队列问题已有同源独立复现 `next-blocker.sv/json`：VCS 输出 `TRACE string_queue beta alpha 2`，dsim 拒绝 push_back。后续需同时处理方法接收者的 unpacked 维度、string 元素转换、空元素默认值、class 属性及容器复制/快照中的字符串保存，不能只绕过方法检查。

## 103 发布流程

103 以 Intel 和原有 Z3 静态库构建，stage PID `1284942`，日志 `/tmp/dsim-m197-publish.log`。三组选定回归、109 CPP/622 解码波形跨端比对、四个实际入口模型、公开 UVM 前后复测及根目录别名全部通过后才完成激活；失败保留旧版或回滚。激活器额外核对完整模型/捕获数及四份 solver 语料，避免漏测。最终结果目录 `/tmp/dsim-m197-final`，日志 `/tmp/dsim-m197-finalize.log`；当前 Intel 编译进程仍运行，未将候选计为发布成功。

收据包括 Mac 发布/入口、三组结果、普通/消毒公开 UVM、VCS/接收差异和发布验证脚本。原始 CPP、波形、测试源及日志保存于 `~/vibe-coding/dsim-test/evidence/m197-packed-keys/mac`，内容清单见 `archive-catalog.json`。

103 验收现已完成：`linux-final.json`、`linux-entry.json` 与 `cross-platform.json` 记录双端稳定发布通过，109 CPP、622 解码捕获及本批编码字节跨端均一致。Linux 稳定入口为 `20261031T092707086202Z-0c0d6ae7ece8`，根目录别名验收通过。上文的运行中状态为当时快照。
