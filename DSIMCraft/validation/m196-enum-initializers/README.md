# M196：无符号枚举初始化

修复无尺寸负数赋给同宽或更宽无符号枚举时被过度拒绝的问题，并在范围检查前拒绝实数。规则依据 VCS W-2024.09 的 29 份独立探针，接收/拒绝全部一致；三份未修改执行模型的 TRACE 也一致，详见 [语义说明](../../docs/enum-initializers.md)。

新增包内覆盖率类型、别名/类属性/方法、无符号零扩展、32/65/129 位克隆及枚举隐式递增执行覆盖，保留窄基类型负数、截断、重复值及递增溢出拒绝。恢复枚举旧回归：移除已经支持的匿名枚举拒绝断言，加入稳定发布组选项；共用回归继承发布器的命令时限，默认保持 180 秒。

未修改公开 UVM 的预处理内容不变，已越过 `UVM_CVR_ALL=-1`；首错为 `uvm_reg_map.svh:130` 的 packed struct 关联键。完整 UVM 仍未编译运行。此批没有性能结论。

上一批 103 显式保留 Z3 的修正版本已成功发布，见 [M195 最终验收](../m195-forward-alias/README.md)。

## Mac 稳定版本

生产实现 `4d0c6c1c3dfb8be4ff0027af89d97f75084a84f6` 已推送 main。1342 个冻结输入，源码 SHA256 `d35fe03a9ba3ec779c990d797fb62609163d3202072b456de426a48a61567d47`。稳定入口已更新为 `20261031T090649676079Z-d35fe03a9ba3`，三个新增模型通过实际入口重新编译/执行，CPP 及异步波形与候选一致，公开 UVM 前后复验保持相同后续阻塞。

| 检查 | 结果 |
| --- | --- |
| anonymous_enums | 7 模型、126 捕获、13 编译拒绝 |
| enums | 4 模型、50 捕获、36 编译拒绝、2 回滚 |
| mandatory | RTL semantic memory、format parsers、native Liberty DB 全部通过 |
| 合计 | 11 模型、176 捕获、49 编译拒绝、2 回滚 |
| 前端 ASan/UBSan | 3 新模型、13 拒绝、29 份边界接收/拒绝、完整原生 parser 重复清理通过；3 CPP 与冻结候选一致 |
| VCS W-2024.09 | 29 探针接收/拒绝一致，3 个同源执行模型 TRACE 一致 |
| 跨端参考 | 35 CPP、176 解码捕获，压缩字节摘要另存 |

生成模型运行时未做本批消毒验证，生产 runtime 未修改；leak 检查未启用。开发构建也单独执行两组回归。旧枚举回归的非整型常量检查、匿名枚举支持断言在本批同步修正，没有删除仍需拒绝的真实溢出反例。

103 使用 Intel 和现有 Z3 路径构建，同组 **11 模型/176 捕获/49 拒绝/2 回滚**及 mandatory 全部通过；35 CPP、176 解码捕获和本批编码字节均跨端一致。三个实际入口模型、公开 UVM 前后复验及根目录别名通过，稳定入口已激活 `20261031T090649974228Z-d35fe03a9ba3`。见 [最终结果](linux-final.json)、[跨端比对](linux-cross-platform.json)、[入口复验](linux-entry.json)、[发布收据](linux-release.json)。

收据包括 `mac-release.json`、`mac-entry.json`、两组回归、`asan.json`、`vcs*.json`、`public-uvm*.json` 和发布验证脚本。下一处真实缺口的 VCS 同源复现见 `next-blocker.sv/json`。原始证据另存 `~/vibe-coding/dsim-test/evidence/m196-enum-initializers/mac`，索引见 `archive-catalog.json`。
