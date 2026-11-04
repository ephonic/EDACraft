# M13：integer/int 与过程静态局部变量

生产实现位于 `src/rtl_compiler.cpp` 及独立 RTL parser 的语法、过程块作用域和整数数组描述。门级 parser、runtime 值/信号/事件布局未改。支持范围和限制见 [integer-and-locals.md](../../docs/integer-and-locals.md)，计划见 [plan1017.md](../../plan1017.md)。

新增默认 signed 的 32 位四态整数，以及命名/匿名过程块中的静态 packed 变量、整数和一维数组。支持词法同名遮蔽、常量声明初始化一次执行、循环重入保持、delay/NBA、敏感依赖、波形、并行与已有失败预测回放。生成程序直接使用既有 Signal ID，运行时不做词法查找。

修复整数降序数组范围元素数。收紧编译期常量识别：parser 为整数保存的历史求值结果不能冻结运行时循环、数组地址、packed 索引或 generate 内部累加。RTL 语法新增匿名块声明，生成 parser 已更新，lexer 保持原版；原始和新语法均为 33 个已有 shift/reduce conflicts。

本地验证：

- 六例 **74 次捕获**：VCD/DWF、ordered/settled、serial/time-wheel/双线程，另含两组真实失败预测回放。整数数组四个字的值/时刻及双独立域六个时刻的输出有独立整数预期。parallel 实际为两分区、六窗口。见 `local-integer.log`、`local-results.json`。
- 六类非法/未支持声明明确退出 1：局部变量逃逸、多维数组、负下界、运行时声明初始化、unsigned 整数及 automatic；不是将崩溃当作诊断通过。
- 九项既有定向 CTest 通过，共 127.87 秒：signed、memory、generate、indexed selects、always SV、preprocessing、普通编译 RTL、独立门级源流程、parser 语义单测。见 `local-affected.log`，未执行完整 CTest 集。
- 三个实际生成程序通过 macOS ASan/UBSan（scopes/memory 串行，parallel 真双线程），捕获与普通程序相同；独立 parser 语义单测及最终六组源码各三次解析/清理也通过 ASan/UBSan。关闭 leak 检测。见 `*-runtime-san.log`、`*-parser-san.log`；未运行 Linux sanitizer。
- 最终编译器再次生成六个完整 serial CPP，与上述实际运行程序逐字节相同。

实际 VCS 六组 TRACE 和 **1649 条可观察物理位时间线**通过。`verify.py` 对全部比较名字/位索引和完整时间线作双向检查。匿名声明块的名字与 VCS 不同，三条完整作用域映射写入脚本及 `vcs-results.json`，这些信号仍参与逐位比较。VCS 不导出 unpacked 元素，native 独有数组字逐项枚举；memory 中有 packed 观察值和四字独立时刻检查，不宣称数组本体的 VCS 全名对齐。

VCS W-2024.09 对首个 generate 用例报告“不支持 generate 内 block 变量静态初始化”。原始源和失败日志保留在 `vcs/generate-static-initializer-rejected/`，`vcs-extra-exit.code` 保留 255；最终 generate 对照使用局部声明后的过程赋值，`vcs-final-exit.code` 为 0。未把旧失败源回写成通过。源、最终编译/运行日志和波形在 `vcs/`。

源码包包含 515 个源码/测试文件，SHA256 为 `831e023f261496e54b3335cd8157c14fa9f5f18ed7f58daf7d21535e213325f5`，逐项摘要见 `source-manifest.json`。Linux 原任务 **3059963 退出 0**，515 文件 manifest 校验、从源码构建及四项定向 CTest 全部通过，共 104.85 秒。Linux 六个完整 serial CPP 与 macOS 字节相同，真实执行的 TRACE/1649 可观察位另行对照同六组 VCS 通过。日志、生成代码和波形在 `linux/`，总结果见 `results.json`。工作区与 manifest 再次逐项核对通过，生产编译器已重建。

复查：

```sh
python3 tests/integer/regression.py build/dsim build/rtl-integer
python3 validation/m13-integer/verify.py
python3 validation/m13-integer/verify.py validation/m13-integer/linux/source/build/rtl-integer
```

仍缺显式 unsigned 整数/整数端口、其他整数类型、automatic 生命周期、非恒定声明初始化、for 内声明、增减运算、break/continue、块外层次引用、函数/任务及完整时序/SV 能力。本批没有新的整体 VCS 速度测量。
