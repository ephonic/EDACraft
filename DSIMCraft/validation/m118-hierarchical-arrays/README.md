# M118：AXI4 层次内存引用的缺少源文件诊断

用户报告 `complex/axi4/tb.sv` 编译时报 `hierarchical instance is not elaborated: mem`，随后确认命令是 `dsim tb.sv`。已在原始文件重现：没有提供定义 `axi4_slave` 的 `rtl.sv`，实例没有 elaborated hive，成员查找先抛出了关于 `mem` 的误导性错误。

修复在 RTL parser 的成员解析中区分“缺少模块定义”和“实例未完成展开”，现在定位实例声明并报告：

```
tb.sv:15: ... unresolved module axi4_slave (instance dut); include its RTL source in the compilation or file list
```

正确编译方式：在用例目录执行 `~/vibe-coding/dsim-test/bin/dsim --top tb rtl.sv tb.sv -o simv`，再执行 `./simv`。也可以通过 `-f` 文件列表提供两个源文件。不自动按文件名猜测缺失模块的来源。

103 上 VCS 对 `tb.sv` 单文件同样报告 `Cannot find cell in liblist`，指出 `axi4_slave`、`tb.dut` 和第 15 行；同时提供两个原始文件时，VCS 和 dsim 均输出 `AXI4_TEST: ALL PASS`。随机序列可不同，各自用完整内存模型核对；这不是跨模拟器随机序列一致性的声明。

原始两个文件已不改写地加入 `tests/hierarchical_arrays/axi4/`。回归覆盖缺少 RTL 的诊断/源位置/既有输出保护，以及 RTL-first、TB-first、通用驱动参考路径、时间轮和并行五个完整运行，全部要求通过 t1–t8 和最终 ALL PASS。接口与已有层次引用回归另行运行。

实现冻结 `3dae119`。本次仅改变未定义模块的失败诊断；与 M117 的四个性能负载生成代码逐字节相同，因此沿用 M117 完整 runtime 测量。Mac/Linux 稳定入口更新到该修复；发布和复现结果见同目录 JSON。
