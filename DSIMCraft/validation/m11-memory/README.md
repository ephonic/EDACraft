# M11：RTL 存储器与文件初始化

生产实现位于 `src/rtl_compiler.cpp` 和 `include/dsim/runtime.hpp`，支持边界见 [memory.md](../../docs/memory.md)。RTL parser 与门级 parser 继续分开；本批没有修改二者源码。存储器复用现有 Signal、部分写入、NBA、波形、并行和回滚设施；没有引入自动预测器。

新增一维 reg/logic 存储器，支持动态/常量地址、非零下界、正反向声明、标量/80 位四态元素、字内 packed 选择与拼接、组合敏感依赖、延迟 NBA/阻塞内部 delay、generate 作用域及常量元素事件。`$readmemh/$readmemb` 支持常量文件名、可选动态区间、注释/下划线、X/Z、十六进制 @ 地址、宽字及倒序加载。动态索引查只读 ID 表；动态整字写直接使用 set/NBA，避免部分写入临时容器。尚未测量存储器与 VCS 的性能差距。

本地验证：

- `tests/memory/regression.py` 四例通过：50 次 VCD/DWF、ordered/settled、serial/time-wheel/双线程捕获，7 类编译拒绝，5 类非法文件诊断，2 个真实失败预测及事务回放；并行 RAM 还独立检查全部 32 个字的写回时刻和值。原始日志 `local-memory.log`，结果 `local-results.json`。
- 7 项既有定向 CTest 通过：generate、动态 packed 选择、专用 always、动态/连续 delay、普通 RTL 流程、独立门级源流程。见 `local-affected.log`，不代表完整 130 项均执行。
- 4 个实际生成程序的 macOS ASan/UBSan 运行通过（design/file_io/narrow 串行、parallel 真双线程，关闭 leak 检测），捕获与普通执行相同。见 `*-san.log`。不是 Linux sanitizer。
- `--emit-ir` 的存储器信号导出实际执行通过。

实际 VCS 四例 TRACE 和 **1312 条可观察物理位时间线**相同。`verify.py` 双向检查比较范围内的全部名字/索引和值，不删时间点。VCS 默认不导出 unpacked 元素，因此明确排除 native 独有的数组元素名，并在 `vcs-results.json` 逐项列出；design/parallel/file_io 用 packed 观察信号连接全部存储器元素。narrow 对照标量事件/端口及其他已声明可观察量，未宣称数组本体全名相同。合法宽度文件的装载逐位相同；VCS 对部分超宽文件项警告并停止装载，native 截断，该边界差异已记录在功能文档。原始源、数据、VCS 编译/运行日志和波形保留在 `vcs/`。

Linux：远程 `/tmp/dsim-m11-memory-lwRrPy` 的同源任务 **1841488 退出 0**，从源码构建编译器；`rtl_memory`、`compiled_regression`、`gate_source_cli` 3 项通过，共 86.24 秒。499 个打包源码文件 SHA 验证通过，包 SHA256 `ea22164d3d64686a2aa11fb98a03c71e6c6750f06a28ede0cf26f0aabf48ceaa`，工作区文件与 manifest 相同。Linux 四个完整 serial CPP 与 macOS 字节相同，实际执行的波形/TRACE 也重新对照同四组 VCS；见 `linux/`、`source-manifest.json` 和 `vcs-results.json`。

复查：

```sh
python3 tests/memory/regression.py build/dsim build/rtl-memory
python3 validation/m11-memory/verify.py
python3 validation/m11-memory/verify.py validation/m11-memory/linux/source/build/rtl-memory
```

未完成：多维数组、数组端口/切片/整体赋值、负地址、运行时字符串、紧凑大 RAM 和细粒度动态依赖、完整 signed、函数/任务、完整层次引用、UDP/specify/完整 timing checks、自动预测和内部自动分区。没有新的整体 VCS 速度比。
