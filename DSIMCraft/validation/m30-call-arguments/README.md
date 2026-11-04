# M30：默认/命名实参与启动事件对齐

静态函数/任务新增 ANSI 默认值、命名调用、位置后接命名调用、连续空位及命名空位。默认值在声明外层词法作用域绑定，每次调用仅求使用到的默认值；输入/inout 入口取样，输出/inout 返回复制。修复单个拼接实参及连续空位扫描；模块连接禁止位置/名称混用及重复名称。运行时继续直接 C++ 执行，RTL 和紧凑门级 parser 分开，运行时源码未改。

启动阶段先挂接 always/always_ff 入口事件等待，再施加声明初值；initial 入口等待在普通进程启动时挂接。保留 always_comb/always_latch 初次执行。针对声明初始化和入口控制的修正不代表完整事件区域兼容。

六个共同输入位于 [tests/call_arguments](../../tests/call_arguments)，包含独立预期，覆盖默认值求值次数和声明序、调用者遮蔽、输出动态下标、延时任务与 NBA、signed/enum/packed/宽两态、generate 克隆、隐式敏感依赖、两条独立并行通道、初始化与后续边沿。串行、时间轮、双线程分别比较 ordered/settled VCD/DWF，含两次失败预测回放，共 74 次捕获；25 类错误拒绝。两条通道以独立时间线核对，实际分为两个分区。

远端 10.131.254.103，`source /apps/EDAs/syn.bash` 后使用 VCS W-2024.09，`-full64 -sverilog -debug_access+all -top top -top dump`。不修改共同输入；源字节、TRACE 和导出的全部 **2,993 条物理位时间线**一致，无任何位排除。两个 generate 函数返回变量只使用逐项明确的名称对应，仍比较全部位。脚本 [run-vcs.py](run-vcs.py)、[verify.py](verify.py)；原始日志/波形在 [vcs](vcs)。记录不作为默认优化配置或任意输入的完整兼容证明。

M29 原始 [启动差异输入](../m29-function-effects/probes/startup-sensitivity/input.sv) 由当前编译器重新生成并运行，全部256位与保存的同输入 VCS 波形一致。新结果见 [probes/m29-startup/results.json](probes/m29-startup/results.json)，旧差异证据保留。

macOS ASan/UBSan 检查 parser 单测、六组输入各三轮清理，以及六个实际生成程序（包含真双线程）；关闭 leak 检测。独立预期和全后端捕获避免仅靠双边实现互比。最终定向 CTest、Linux 干净构建、生成程序跨平台身份及 sanitizer 结果见 [results.json](results.json)。Bison 仍为47个shift/reduce，无reduce/reduce。

范围及剩余缺口见 [docs/call-arguments.md](../../docs/call-arguments.md)。不支持 automatic/ref/递归/常量函数、数组形参、完整并发重入、层次调用、完整验证环境和全部事件区；未使用默认值的完整声明期诊断尚缺。本轮没有全量 CTest、Linux sanitizers 或新的性能测量。

最终结果：本地15项不同定向CTest均有最终通过记录，保留首轮失败及修复后的日志；Linux同源干净构建六项全部通过（395.01秒，退出0）。七份实际生成完整C++跨平台逐字节一致，Linux实际波形再次匹配同组VCS的2993条位时间线。最终701文件源包SHA256：`ecff996eddecb10bba8ee80dc0e0abc5af708d288e0bab3fb3b806331568ec9a`，逐项身份及生成程序身份见 source-manifest.json、final-identity.json、platform-identity.json。
