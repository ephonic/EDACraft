# M28：命名类型值参数与静态子程序签名

本批将已有 integral/enum/packed struct/union typedef 接入 parameter/localparam、函数返回值和函数/task 形参。修复直接常量拼接参数初始化被旧缓存检查提前拒绝、函数 `return` 绕过 enum 赋值检查，以及缺少参数初始化值被静默忽略的问题。类型绑定在实例/generate/子程序克隆中重新计算；静态存储和直接 C++ 路径复用现有实现，RTL 与紧凑门级 parser 保持独立。

支持范围及未完成项见 [类型签名说明](../../docs/type-signatures.md)。没有新增速度测量，不以编译期类型处理推断提速。

| 输入 | 独立检查 |
| --- | --- |
| values | signed 与非零下界、130 位两态、enum/别名参数、常量成员、mixed/all-two-state 聚合、ANSI/经典函数、嵌套调用与 return、delay/NBA |
| effects | typed task input/output/inout、经典 enum 输出、带副作用函数实参单次取样、宽两态转换、跨 delay 保持和 NBA |
| hierarchy | 不同宽度实例、体内 typed 参数覆盖、generate 类型遮蔽与本地函数、过程局部 typed localparam |
| parallel | 两个真实独立分区，typed 参数/函数/task、不同节拍输出的独立预期 |

每例串行、时间轮和双线程配置各捕获 ordered/settled × VCD/DWF，48 次；effects 再执行一次实际失败预测回放，总计 **49 次捕获、1 次回放、26 类拒绝检查**。拒绝项涵盖未知/越域类型、运行时参数、数组/追加维度、缺失初始化、错误 signing、scalar 选择、enum 参数/输入/return/任务复制类型不符和只读参数。旧 named-types 回归中“typedef 值参数必须失败”的负例改为真正未支持的 `parameter type`；首次旧负例失效不计为功能验收通过。

实际 VCS 使用 `10.131.254.103`、`source /apps/EDAs/syn.bash`、`-full64 -sverilog -debug_access+all -top top -top dump`，输入逐字节相同。核对退出码、无 Fatal 和完成 TRACE，再比较 settled 物理位时间线。四例 **1,586 条位时间线一致**，无信号/位排除。values/effects/hierarchy/parallel 分别为 742/333/151/360 条。

有四个明确名称对应：VCS 在 generate 内函数返回变量名中重复生成域前缀，例如 `top.u.gen[0].clear_unknown.gen[0].clear_unknown` 对应 `top.u.gen[0].clear_unknown.clear_unknown`。完整四项列于 [vcs-results.json](vcs-results.json)，所有对应位仍逐位比较，不作为过滤项。

保留的差异：[原始并行输入及波形](probes/default-formal) 中，尚未调用的两个全两态 packed-struct 形参 `top.u.add.x`、`top.v.add.x` 初始 dump 为 dsim 0 / VCS X，共 **34 位**；调用后相同。保留完整 SV、双方原始 VCD、VCS 日志、源/C++ 摘要及逐位差异 JSON。未据此认定 VCS 内部原因，也不宣称原始初始波形一致。共同并行用例增加零时刻初始化调用，仍检查所有信号和后续节拍。

Bison 为 **47 个 shift/reduce 冲突**（M27 为 46），无 reduce/reduce；没有把它描述为无冲突 parser。解析器仍存在历史语法限制。

复现：

```sh
cmake --build build --target dsim test_verilog_semantic_memory -j 8
ctest --test-dir build -R '^rtl_type_signatures$' --output-on-failure
python3 validation/m28-type-signatures/verify.py
ASAN_OPTIONS=detect_leaks=0 build-control-sanitized/parsers/test_verilog_semantic_memory
python3 validation/m28-type-signatures/run-sanitizers.py
```

本地和 Linux 定向回归、sanitizer、冻结源与实际 C++ 身份记录见 [results.json](results.json)。波形差分只覆盖共同输入，不推广为完整 SystemVerilog 或 VCS 功能兼容。未跑完整 CTest、Linux sanitizer 或新性能测量。类型参数、模块命名类型端口、package/interface、automatic/递归/常量函数、完整数组/验证环境及完整时序/事件区仍待补齐。
