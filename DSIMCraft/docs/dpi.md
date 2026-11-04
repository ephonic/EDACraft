# DPI-C function 接口

独立 RTL parser 支持模块、interface、generate 和 package 内的 `import "DPI-C" function`、`export "DPI-C" function`，包括 C 名称映射、`pure` 和 `context`。导入使用真实 C ABI 调用动态库，导出生成可由 C 调用的函数入口；不会跳过函数体或用占位返回值替代。

例如 C 文件提供 `int add_one(int x) { return x+1; }`，SV 声明 `import "DPI-C" function int add_one(input int x);`，编译时使用：

```sh
cc -shared -fPIC helper.c -o helper.so
dsim tb.sv --dpi-lib ./helper.so --dpi-header generated.h -o simv
./simv
```

`--dpi-lib FILE` 可重复指定，编译器保存绝对路径，并保护库文件不被输出覆盖。运行时同名选项覆盖整组默认库列表。库在仿真启动时加载，函数首次调用时解析；缺失的库或符号会报错。C/C++ 插件自行编译为与模型相同架构的共享库；本批没有自动编译 C 源文件。macOS 插件若引用模型的回调符号，可加 `-Wl,-undefined,dynamic_lookup`。模型自动导出回调和作用域符号；独立编译生成 CPP 时，macOS 使用 `-Wl,-export_dynamic`，Linux 使用 `-Wl,--export-dynamic -ldl`。Linux 的 C 插件若使用 `RTLD_DEFAULT`，应在任何头文件前定义 `_GNU_SOURCE`，或编译时添加 `-D_GNU_SOURCE`。

`--dpi-header FILE` 输出导入/导出的 C 原型。仓库 `include/dsim/svdpi.h` 和稳定版本的 `runtime/svdpi.h` 提供当前标量、packed-vector、scope ABI 子集。它不是完整的 IEEE svdpi.h；不能据此推断所有 DPI API 已支持。

支持 input/output/inout 的 byte、shortint、int、longint（含 unsigned）、标量 bit/logic、string，以及 packed bit/logic 向量，包括超过64位和显式 `[0:0]`。integer/time 参数按四态向量传递，不当作 C int/long long。packed 向量每32位一个最低有效字优先的 `svBitVecVal` 或 `{aval,bval}`；X/Z 保留。普通函数可返回原子整数、标量 bit/logic、string 或 void，packed-vector 返回暂拒绝，建议使用 output 参数。

`context` 调用在声明所在实例/包的作用域执行，支持 `svGetScope`、`svSetScope`、`svGetScopeFromName`、`svGetNameFromScope`，允许 C 调用导出的 SV function。嵌套回调恢复原作用域，自动函数进入独立生命周期帧。普通/pure 导入没有可调用 SV 的上下文。外部线程调用、仿真启动前回调及完整标准 scope API 尚未支持。相同 C 导出名称可绑定多个实例，但本版本要求转换合同中的宽度、方向也相同；不匹配会拒绝，避免宽度不同的 packed 指针越界。string 导出结果保存在接收线程的字符串存储中，下一次同名结果/参数返回可能使旧指针失效；C 端需及时复制。

预测执行遇到普通/context 导入时，在进入 C 前触发屏障：恢复 SV checkpoint，执行修正，再在正式执行中调用一次。外部计数器和异步波形回归检查没有重复 C 副作用。`pure` 根据调用方承诺允许预测，调用者必须遵守无副作用、仅输入参数的合同。任意用户手工 checkpoint/load 无法撤销 C 的文件、堆或外部状态，本批没有给 C 提供事务回滚。

包含 DPI 声明的模型目前对 `--threads` 使用串行内核，`--parallel-stats` 明确报告1分区；独立波形接收/压缩线程仍可使用。无 DPI 的独立设计继续验证实际双分区。

real/shortreal 的输入、output/inout 及返回值使用 C double/float ABI，见 [实数执行](real-values.md)。仍缺：DPI task、可暂停 C/SV 调用、open/unpacked array 及完整 array API、chandle、aggregate/ref 参数、compilation-unit 声明等。完整 UVM 2020.3.1 原生编译/运行尚未完成，不能把语法首错推进视为 UVM 支持完成。

ABI 依据：[IEEE 1800-2017 Annex H](https://fpga.mit.edu/6205/_static/F25/documentation/1800-2017.pdf)。实际用例、拒绝边界和预测/波形检查见 [tests/dpi](../tests/dpi)。
