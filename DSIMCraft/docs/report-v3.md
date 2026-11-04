# v3 报告修复与当前边界

v3 报告保存在 [原文](../validation/m83-report-v3/report-v3.md)，来源 hash 见 origin.json。这里按用户列出的六项检查实际组合能力；不把单项语法支持等同于完整 SystemVerilog 支持。

| 项目 | 当前实现与限制 |
| --- | --- |
| 并发断言 | M82 已发布单时钟直接/命名 assert/assume/cover property、布尔蕴含、disable iff 和采样/Observed/Reactive/Re-NBA；本报告 deep3 进入回归。完整 sequence、重复、多时钟、采样函数等仍缺，见 [支持范围](concurrent-assertions.md)。 |
| interface/modport | M84 已接通 interface 类型、参数化实例、共享存储、端口转发及 modport 方向/可见性约束，修正版 bus_if/master/slave 通过。virtual interface、clocking block、interface 数组和 subroutine 视图等仍缺，见 [支持范围](interfaces.md) 与 [验收](../validation/m84-interfaces/README.md)。 |
| 层次未打包元素 | M83 将向下已展开模块实例的数组读取接入现有内存选择：多维固定数组、运行时索引、完整元素后的 packed 多维/位/片选、符号扩展、X/Z 和越界读、组合依赖。对应真实实例存储，不复制数组。普通模块仍不支持层次写入、实例数组索引、generate/向上/绝对路径、整个层次数组的复制/端口/ref，以及完整动态数组方法组合。原有非负内存边界限制保留。 |
| 层次枚举方法 | M83 保留层次接收者的 enum 身份，接通 name/name()、first/last/num/next/prev 及其链式调用；也支持完整层次固定数组元素的 enum 方法，以及层次 packed struct 成员读取。实例克隆后重新绑定，无共享悬空字段指针。 |
| 包内可变变量 | M83 为每个包建立唯一信号/内存存储；支持模块、包 subroutine 的 import/qualified 读写、整数/四态/两态/enum/packed struct、固定数组和已有 string 子集；声明常量初始化、延迟任务及 NBA、依赖分区和 checkpoint 复用已有机制。支持缺省 static 生命周期，未实现显式包/全局生命周期限定符、非恒定标量声明初始化和完整 package 能力，见 [packages.md](packages.md)。包内 net/模块端口明确拒绝。 |
| 标准文本 VCD | M83 修复 `--waveform result.vcd` 未指定格式时仍选 DWF 的入口问题；现自动选择已有标准文本 VCD writer。`.dwf` 选 DWF；其他后缀保留既有默认。显式 `--wave-format vcd/dwf` 优先于后缀且不依赖参数顺序。`$dumpfile/$dumpvars` 原有默认文本行为保留，DWF 编码本身没有变化。串行、时间轮和真正并行归并共用选择逻辑。 |

测试入口：`python3 tests/report_v3/regression.py build/dsim <output>`。共享源在 `tests/report_v3`，包含 h_arr、h_deep、deep3 探针（仅统一顶层名以运行公共回归）、二维索引/enum/aggregate 组合、跨模块包状态与独立双分区。检查完整输出和所有公开信号的完整 ordered VCD，失败预测后回滚必须逐条一致。格式检查对自动选择与显式覆盖逐字节检查文件签名，并独立解码比较完整信号流。VCS 对照及实际 sanitizer/发布记录位于 [M83](../validation/m83-report-v3/README.md)。

原始 deep4_if 直接交给 VCS W-2024.09 也会报两项 Signal not visible via modport，因为 m/s 都未声明 clk。加入 `input clk` 后 VCS 输出 D4 INTERFACE PASS；原始负例与有效正例均保留在 M83/interface-probe。M84 的 dsim 现同样拒绝原始缺失 clk 的 modport，并通过修正版；8个同源接口模型的425个共同物理位完整时间线与实际VCS一致。
