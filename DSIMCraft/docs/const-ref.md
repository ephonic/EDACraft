# const ref 只读引用

M63 新增[无尺寸数组 input/inout 值形参](open-arrays.md)，支持固定数组实参；动态分配与动态数组引用仍未接通。

automatic task/function 支持 `const ref`，覆盖完整标量、packed 变量、固定 unpacked 数组、动态前缀子数组和完整数组元素。支持 ANSI/经典声明、默认值、命名调用和嵌套转传。RTL 与门级 parser 继续分开维护。

```systemverilog
task automatic observe(const ref integer value, output integer result);
  wait (value == 3);
  @(value);
  result = value;
endtask
```

形参保持实际变量的实时别名，不在入口复制值。调用者或其他可写别名修改实际变量后，读取和等待能看到变化。动态元素/子数组的地址在入口只求值一次；索引后来变化不会重新绑定。引用调用者的 automatic 局部变量时沿用父激活帧保活、取消和检查点恢复。

只读约束覆盖赋值、位/成员/数组元素写入、增量及复合更新、拼接目标、数组整体赋值，以及转传给可写 `ref/output/inout`。允许向 `input` 和 `const ref` 转传。其他别名仍可修改实际变量，`const ref` 本身不是冻结对象。

实参必须是类型等价的变量；固定数组按声明顺序匹配维度和元素。表达式、字面常量、net、类型转换及 packed 部分选择不支持绑定；这一批已在实际 VCS W-2024.09 上核对变量、表达式、常量和 net 的接受/拒绝行为。未知或越界动态引用采用明确运行诊断，不宣称其错误策略与 VCS 一致。

已知兼容差异：实际 VCS 接受把 const ref 形参转传给 output/inout，并在返回时改写实际变量；独立探针从 `1,1,2` 变为 `9,17,18`。dsim 对该路径维持只读拒绝，未将其计为 VCS 对齐。

仍缺开放/动态数组、递归、数组返回、动态容器及完整 SV/UVM 验证体系。引用函数作为事件表达式回调仍保守拒绝；直接在 join_any/join_none 分支访问外层引用的标准限制仍未完整实现。既有 M47/M55 事件差异保留。本批没有新增性能测量。

定向回归：`ctest --test-dir build -R '^rtl_const_ref$' --output-on-failure`。VCS 同源对照及实际验证范围见 [M62 证据](../validation/m62-const-ref/README.md)。
