# 数组定位与去重

未打包数组支持 `unique`、`unique_index`、`find`、`find_index`、
`find_first`、`find_first_index`、`find_last`、`find_last_index`、`min` 和 `max`。
结果是队列，可赋值、作为数组实参或由队列类型函数返回。
固定数组、动态数组、队列和整数键关联数组支持一个剩余未打包维度。
固定数组的索引结果保留实际声明下标，包括降序范围；关联数组保留实际键。
自赋值先取得输入快照，再写回结果。

`with` 使用默认 `item` 或显式迭代器名。find 系列要求谓词；
unique/min/max 可以用表达式投影键，包括字符串及类句柄的属性、虚方法返回值。
类方法的零实参调用可省略括号，真实公开 UVM callback 库使用此形式。

```systemverilog
int a[5:1] = '{5,3,5,2,3};
int q[$], indices[$];
initial begin
  q = a.unique();
  indices = a.find_index(x) with (x == 3); // indices 4 and 1
  q = a.min with (-item);                 // one element: 5
end
```

定位返回值的遍历顺序、unique 选取哪个重复代表不应作为可移植合同。
first/last 按数组声明的左右方向，关联数组按键顺序。
min/max 返回一个元素；空输入返回空队列。
unique/min/max 的键必须具备关系运算，类句柄需显式投影到可比较的键。

仍缺多维结果、字符串键索引结果队列、实数键和嵌套容器等能力。
`with` 迭代器当前只读；VCS 接受部分修改迭代器的表达式，尚未对齐。
原生支持定位结果直接 `.size()`，本轮 VCS 不接受该链式写法；可先赋值到队列再查询。
去重目前逐项比较，没有本批性能提升结论。

`tests/array_locators/regression.py` 四个模型覆盖数值、类 getter、函数返回和实参、
关联键、预测恢复，以及完整与用户选定信号/时间范围的异步压缩波形。
74 次捕获和九个拒绝边界通过；四个相同执行源码的输出与 VCS 一致。
ASan/UBSan 完整 parser、四个前端/生成程序、拒绝例和预测回放通过，
生成程序及异步波形与正常执行一致。不声称全部模型实际双分区或完整 UVM 已支持。
