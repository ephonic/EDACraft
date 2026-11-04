# M199：REPORT-GAP6 功能覆盖率

本批实现 covergroup 真实采样、bins 命中、自动 cross 和覆盖率查询，含类内嵌接收者、参数化模块克隆、checkpoint 状态与单分区调度。支持边界见 [功能覆盖率](../../docs/functional-coverage.md)。报告原始 q03_covergroup.sv 作为 report_gap6.sv 原样纳入回归。

VCS W-2024.09 同源测试核对类型聚合、per_instance、at_least、weight、goal、显式/自动/枚举 bins、cross 及 NBA 同拍采样；每项按源文件 SHA 和实际 TRACE 判定，不以 VCS 的退出码代替成功检查（VCS 的 $fatal 可能返回 0）。此前类型均值和 goal 缩放假设已被对照推翻，最终实现以实测查询行为为准。

计划验收三组 coverage、clocking、class_objects，另执行 parser 重复清理及 ASan/UBSan 前端和生成运行时。只在冻结候选全部通过后更新稳定入口；最终状态见 progress.json 与平台收据。完整公开 UVM 仍不能运行，没有本批性能结论。

Mac 验收完成：1375 冻结输入，SHA `3c9dbb4fd121376fa72b5ef8497ba8f6301f5689c6df2d6437275444b5a01b64`，生产提交 `e7250bed`。三组 33 模型、603 捕获、47 编译拒绝、6 运行拒绝、3 回滚/3 提交及三项 mandatory 通过。coverage 为14模型/254捕获/11编译拒绝/3运行拒绝；clocking 含65次预算恢复。100份CPP及603份波形摘要见 mac-reference.json。

14 新模型的同源 VCS TRACE 全部一致，源码 SHA 见 vcs.json。前端和14个生成程序 ASan/UBSan通过，含覆盖率回滚/提交与异步压缩波形，leak 检查关闭，见 asan.json。Mac 稳定入口 `20261031T105638861098Z-3c9dbb4fd121` 已激活，14个实际入口用例的CPP、解码及压缩字节均匹配冻结候选。原版公开UVM前后复测仍首错于单例求值。

103 Intel 候选按同源三组、跨端摘要和实际入口门槛验收；当前阶段见 progress.json。原始输出、生成CPP和波形存于外部证据目录，清单及摘要见 archive-catalog.json。

首个103候选在跨端生成CPP门槛被拒绝，未激活：6份CPP只在coverage注册顺序不同，源因为按AST指针地址遍历类型。修正为按parser ID排序，重新冻结验收。603份解码信号轨迹相同；既有class/order的4份DWF压缩字节不同，但解压后的完整元数据/事件记录相同，编码差异单列记录，不冒充字节相同。初次检查见initial-cross-platform.json。

排序修正候选最终完成双端验收：生产 `25ee6a2b3db1e333f419177dcdb5aa76effdcae1`，1375输入，SHA `5c4ef1674b18fb86948633659df94ed55b34ca30aac8958a213b3e808f82426d`。两端再次各跑33模型/603捕获/47编译拒绝/6运行拒绝/3回滚3提交及mandatory；修正后的14个模型再次通过前端/生成运行时ASan/UBSan。

Mac 稳定入口现为 `20261031T111303862274Z-5c4ef1674b18`，103 Intel 稳定入口为 `20261031T111313497591Z-5c4ef1674b18`。两端各14个真实入口用例与自身冻结CPP/波形/压缩字节一致，103根目录别名也通过。跨端100份CPP完全相同，603份解码波形相同；4份既有class/order压缩文件字节不同，但其完整解码元数据和事件记录相同，见cross-platform.json。首候选的拒绝及编码差异记录保留，未跳过生成代码门槛。

完整公开UVM前后复测仍失败于 `uvm_cmdline_processor.svh:150` 的单例handle/null常量求值；本批只关闭报告原始covergroup探针及上述支持范围，没有宣称覆盖率全标准或完整UVM。
