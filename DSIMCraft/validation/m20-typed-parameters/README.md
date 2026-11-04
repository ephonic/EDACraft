# M20：类型化值参数与常量上下文

修复 M19 分离 int/integer token 后的 `parameter int`/`localparam int` 入口退化。新增 bit/byte/shortint/int/longint/integer/time/logic/reg 值参数的目标宽度、声明符号和两态转换；默认值、命名覆盖、位置覆盖、继承声明类型、依赖参数与参数化克隆共用转换路径。接入端口尺寸、generate、delay/NBA 和静态局部参数，RTL 与门级 parser 保持独立。功能及剩余边界见 [类型化值参数](../../docs/typed-parameters.md)。

普通常量一元/二元/条件表达式在运算前获得目标位宽，移位量、比较和拼接保留自身尺寸边界。修复命名参数调用的单元素 comma 包装丢失上下文问题；`longint` 的 `32'hffffffff+2` 覆盖现在得到 64'h0000000100000001。未知条件三目表达式逐位合并并按 VCS 将共同 Z 位转 X。常量除余支持多字有符号整数，零除/未知操作数传播 X；移位超过宽度时填充而非取模，清除旧移位整字 UB。带尺寸数字允许高位截断，130 位十六进制不再误报越界。补齐归约 AND/OR、NAND/NOR、逻辑非的一位 unsigned 结果与四态控制值，宽 OR 不再保留原位宽，位反转将 Z 转 X；新增 1792 项四态归约独立真值表。elaboration JSON 为参数增加 `signed`、`two_state`。这些是编译展开期变换，不增加仿真热点分支。

六组正式用例 values/overrides/context/constant_ops/generate/parallel，三后端（serial/time-wheel/两线程）、ordered/settled、VCD/DWF 共 **74 次捕获**、**2 次实际失败预测回放**和 **9 类明确拒绝**通过。两域输出有独立时刻/数值预期；并行实跑两分区、九窗口。参数 IR 的宽度/符号/两态转换有独立预期，130 位除余另用 Python 整数核对。parser 单测新增反复克隆/清理、继承类型/依赖参数，8/32/64/65/130 位 signed/unsigned 除余网格、32/64/130 位移位边界和多基数字面量截断。

实际 VCS W-2024.09 六组 TRACE 和 **2025 条可观察物理位时间线**一致，比较器严格核对身份、物理位与 1ps 时间轴，包含 VCS 导出的所有普通信号。只逐项排除两个 VCS 不导出的 inline for 计数器，没有排除其他普通信号。列表与输入 SHA256 见 `vcs-results.json`，原始输入、编译/执行日志和 VCD 在 `vcs/`。

六组原始输入各三次解析清理、parser 单测及四个实际生成程序（values/constant_ops/generate 串行和 parallel 双线程）通过 macOS ASan/UBSan，关闭 leak 检测；运行程序波形与正式基线核对。文件身份见 `sanitizer-runtimes.json`。Bison 生成 39 个 shift/reduce conflicts（上一批 29），生成日志保留；常见受支持声明由 parser/执行回归覆盖，不宣称完整 SV grammar。最终本地编译器重新发射六份完整 C++，与实际运行版本字节一致，见 `final-identity.json`。

```sh
ctest --test-dir build -R '^(rtl_typed_parameters|rtl_semantic_memory)$' --output-on-failure
python3 validation/m20-typed-parameters/verify.py
python3 validation/m20-typed-parameters/run-sanitizers.py
```

575 文件冻结源包 SHA256 为 `93e7b65030fc99fec26f512b9eeeeb07114fe3dd1c93a2e3f165bd352ac77437`，进入 M21 之前已与工作区逐文件核对一致。Linux /tmp/dsim-m20-linux-WE4T1V 干净构建，首轮九项中八项通过；NOTZ 的独立测试期望曾把 ~ 的上下文扩展误写成先运算再补零，更正为 VCS 对应 1111111x。原 Python 进程已加载旧断言，保留首轮失败日志，脚本更正后重新启动 typed-parameters/parser 两项通过 111.10 秒，最终退出码 0。生产源码与正式 SV 输入在该更正中未改动，最终 575 文件 manifest 再核对。七份完整生成 C++ 与 macOS 字节相同，Linux 实跑 TRACE/2025 条位时间线也匹配实际 VCS。记录见 linux/ 和 platform-identity.json。

本地 12 项既有 CTest 通过 280.75 秒，另三项编译/检查点/门级 CLI 通过 93.05 秒；补入归约修复后再跑七项相关 CTest，通过 144.04 秒。最终新增六例仍通过 74 捕获、2 回放及9拒绝。局部测试断言修正的原失败保留在 local-new-initial.log；最终结果 local-regression.log。

本批未运行完整 CTest 集、Linux sanitizer 或新的速度测量。类型参数/参数数组、完整类型/尺寸 cast、常量用户函数/automatic/递归、完整层次引用、事件区、SV testbench 和精确时序，以及自动预测策略和总体性能目标仍未完成。
