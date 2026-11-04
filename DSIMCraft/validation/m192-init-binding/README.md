# M192：运行期初始化与默认实参的前向类调用

生产提交 `389b67cf6d55b91e988ff92f3fe97b693ef82d35`，冻结 1310 输入，SHA256 `b9700afe7ca8714bee5d99e15e6dccc74bfaf0608ed41e9a3582a7279218e6f5`。

原公开 UVM 的 resource_pool::set_precedence 默认值调用 get_default_precedence，经 coreservice::get 展开 uvm_init，再过早展开 report_object。此时 report_handler 的前向声明尚未完成。签名默认值现延后绑定，调用处克隆仍即时处理；外围整型/字符串等初始化中的调用也延后绑定，保留常量和参数路径。作用域、前序形参及运行时求值规则不变。详见 [实现边界](../../docs/runtime-initializer-binding.md)。

## 验收

- `before.json`：三个新增源在原 M191 稳定二进制上均可复现 `unknown integral type Handler`。
- `mac-release.json`：冻结候选 mandatory parser/format/liberty-DB 通过，class_forward 23 模型/416 捕获/17 拒绝、call_arguments 6 模型/74 捕获/24 拒绝。合计 29 模型、490 捕获、41 拒绝；含三次预测回滚及已有一次提交、真正两个并行分区。不是全库全语言回归。
- `mac-reference.json`：90 份 CPP、490 份独立解码波形的内容摘要；同端同步/异步压缩波形编码一致。
- `mac-entry.json`：稳定入口已更新到 `20261031T031251037385Z-b9700afe7ca8`，三个新增模型实际入口重编译/运行，CPP 和异步波形与候选一致。`activate.py` 在失败时恢复旧链接。
- `vcs.json`：三个原样源码在 VCS W-2024.09_Full64 上执行，TRACE 对齐；没有宣称 VCS 全量波形相等或加速。
- `asan.json`：ASan/UBSan 前端、四个模型与一次回放、17 诊断和 parser 重复清理通过；未启用 leak 检查。
- `modport-prototypes.json`：额外八个模型、40 捕获、44 拒绝、8 回滚/8 提交/2 恢复通过；未计入两组发布的 490 捕获。
- 本地主工作区完整构建通过，日志归档为 `dsim-m192-all-build.log`。

## 公开 UVM 与 Linux 状态

`public-uvm.json` 与 `public-uvm-asan.json`：原版 Accellera 2020.3.1 的预处理结果仍为 1,888,084 字节、166 依赖，SHA256 `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`。`uvm_report_handler` 首错已越过，当前为关联数组索引类型限制，完整 UVM 仍不能原生编译运行。

103 上 M191 候选构建通过、回归组 1200 秒超时，未激活，旧收据已改为超时状态。M192 已启动独立冻结源码的 Intel 构建，候选 `20261031T031539671615Z-b9700afe7ca8`；组时限 14400 秒。当前未激活，Linux 仍为 M190。`finalize-remote.py` 在两组回归、90 份 CPP/490 份解码波形跨端一致、补跑 Linux 未完成的 clocking 全组以及实际入口检查通过后才更新 bin 入口，并验证根目录兼容入口。日志 `/tmp/dsim-m192-linux-publish.log`、`/tmp/dsim-m192-finalize.log`，最终结果写 `/tmp/dsim-m192-final/`。不能把后台运行计为通过；最新阶段见 `linux-pending.json`。

本批没有性能结论。后续继续有类型的关联数组索引、UVM 展开，以及 covergroup、virtual interface 等缺口。RTL 和门级 parser 保持独立。
