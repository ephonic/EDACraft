# 无尺寸数组值形参

automatic task/function 支持以固定 unpacked 数组或子数组作为 `input/inout` 无尺寸 `[]` 实参。支持多维 `[][]`、混合固定维度 `[][2:1]`、命名类型、宽两态/四态元素、默认/命名/经典声明及嵌套转传。RTL parser 与门级 parser 继续分别维护。

```systemverilog
function automatic integer sum(input integer words[]);
  integer result = 0;
  foreach (words[i]) result += words[i];
  return result;
endfunction
```

每个无尺寸维度按实际元素数量重编号为 `[0:size-1]`，源数组按声明顺序复制；固定维度保留声明的范围。支持 `$left/$right/$low/$high/$size/$increment/$dimensions/$unpacked_dimensions`、`$bits`、索引、foreach 和现有数组操作。解析阶段保留未绑定维度，延迟形状查询的折叠；编译器按调用点确定固定形状，之后生成已有数组/激活帧代码。同一子程序的不同调用点可以使用不同长度，嵌套调用继续传递已确定的形状。

input/inout 在入口只求值一次源地址并取样全部元素，input 的局部更新不会回写实际数组。inout 在返回时重新求值目标地址并复制结果；挂起期间实际数组的外部修改不会改变已取样形参。副作用索引、取消复用、事件等待、并行分区和检查点沿用既有实现。

M65已补充[一维动态数组实参](dynamic-arguments.md)。以下描述M63固定形状实参的值形参支持。尚不支持动态数组变量、`new[]`、resize/delete、空数组或长度在同一调用点随运行改变、动态数组返回。`output ...[]` 需要动态分配而明确拒绝；`ref/const ref ...[]` 要求动态数组实际类型，固定数组不能绑定，仍拒绝。默认静态子程序的无尺寸形参暂不支持。M70允许[值形参等位宽两态/四态转换](array-state-conversion.md)，其他元素类型限制仍保留，固定 bounds 仍须非负，最多 1048576 个元素。

已知差异：无尺寸数组值参数函数用于事件表达式时，dsim 独立探针可以运行，当前 VCS W-2024.09 独立探针运行超时；不计为对齐通过。主对照模型以固定数组值参数函数触发事件，并单独核对无尺寸任务形参上的等待/唤醒。

VCS 对多维变量大小数组的直接第二维查询有限制，对照模型使用 `$size(a[0])` 等子数组查询；本批未宣称该诊断限制完整对齐。递归、动态容器、class/随机约束、完整 SVA/覆盖率和 UVM 仍待补齐。未新增性能测量。

回归：`ctest --test-dir build -R '^rtl_open_arrays$' --output-on-failure`。实际 VCS 同源结果与验证范围见 [M63](../validation/m63-open-arrays/README.md)。
