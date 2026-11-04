# foreach 静态数组遍历

M34 已扩展到[静态多维 unpacked 变量数组](multidim-arrays.md)。下文原有单维示例继续适用；当前多维范围和限制以该文档为准。

支持 `foreach (array[i])`、`foreach (array[i,j])`、跳过维度 `foreach (array[,j])` 和尾部省略索引。目标为现有的静态单维 unpacked 数组、packed 向量或内建整数；一个 unpacked 数组加一个 packed 位维度可同时遍历。每个维度从声明左边界走向右边界，较后维度变化更快。

```systemverilog
logic [7:0] data[2:4];
initial begin
  foreach (data[i]) data[i] = i;
  foreach (data[i,j]) begin
    #1;
    if (j == 3) continue;
    if (i == 4 && j == 1) break;
    data[i][j] = 1;
  end
end
```

索引隐式声明在循环局部作用域，具有自动生命周期，可遮蔽外部同名变量，按固定数组索引的 int 语义读取。索引只读：直接赋值、选择/拼接目标、递增、复合赋值、NBA，以及 output/inout 写回均拒绝；同一循环的索引必须互异且不能与目标数组同名。支持多索引、嵌套 foreach、普通循环、函数 return 和任务调用。`continue` 进入下一组索引，`break` 退出整个 foreach，多索引不产生额外的可见循环边界。

编译器在展开后读取静态维度，计算总次数与步长，用一个现有可检查点计数器生成固定 PC 循环；不按元素展开 AST，不增加运行时数组解释器。每轮由计数值计算只读索引，不在末端对 32 位索引加减，覆盖 INT_MAX 附近的合法边界。循环次数只依赖数组形状，不读取数组值；实际元素读写继续进入现有敏感集合、单写规则和并行依赖。

隐式索引不导出静态 VCD/DWF 层次，但仍属于仿真状态、进程依赖与检查点。同一静态任务从两个进程重叠执行时，foreach 索引按进程隔离，循环体中的静态局部变量保持共享；M56 接通 [fork 重叠执行和索引保活](foreach-fork.md)，递归仍不支持。delay/event/NBA 沿用现有过程语义；失败预测恢复计数器、索引、PC 与输出事务。已有 automatic 函数/task 也可使用 foreach。

当前目标限于直接变量标识符。动态/关联/队列、多维 packed、复杂数组、数组端口/形参、packed 聚合、成员/选择/层次目标、循环语句标签等未补齐。全空索引明确拒绝。普通 for 隐式计数器的静态波形导出仍有既有差异，不能将本批 foreach 自动索引对齐推广到全部循环。

回归入口：`ctest --test-dir build -R '^rtl_foreach$' --output-on-failure`。六组共同输入涵盖方向、多个/省略索引、嵌套控制、函数、参数化/generate、重叠静态任务、双线程与回放。实际 VCS 与完整验收证据见 [M33](../validation/m33-foreach/README.md)。本批没有新的性能测量。
