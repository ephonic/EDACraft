# 类成员数组的 ref / const ref

M222 支持把类实例的一维动态数组或队列字段作为 `ref`、`const ref`
实参传入函数或任务。引用绑定实际字段，不使用复制出入：多个形参可指向同一
字段，`new[]`、整体赋值、删除和队列方法后的结果立即通过其他引用可见。

```systemverilog
class item;
  logic [64:0] value[];
  function void get_value_array(ref logic [64:0] result[]);
    result = value;
  endfunction
  function void copy(item rhs);
    rhs.get_value_array(value);
  endfunction
endclass
```

普通元素访问、部分位写入、字符串、类句柄和已支持的 unpacked struct 元素沿用
原有元素类型/默认值规则。`const ref` 不能重新赋值或转传给可写形参。
支持嵌套转发和延时任务；直接修改类字段会唤醒等待对应引用的进程。
调用者随后重新赋值自己的对象句柄，不会改变已捕获引用的对象身份。

有界队列可传入无界队列引用形参，原队列容量仍限制插入和整体赋值。
此规则同样适用于普通队列。形参自身声明了容量时，实际容量必须相同；
动态数组与队列不能互相绑定，元素必须为等价类型。

运行时用 `(对象索引, 字段索引)` 保存引用，并复用对应的通知信号。
数组重分配不留下指向旧 vector 的地址，检查点保存和预测回滚可恢复引用与等待状态。
内部信号不作为新用户波形变量导出。

本轮范围是一维完整动态数组/队列变量。关联数组、数组切片引用、多维堆数组和
通过类数组引用的非阻塞赋值尚不支持；后者明确报错。VCS W-2024.09 也以 NYI
拒绝测试中的 ref-port 非阻塞赋值，不能据此认定语言本身禁止。

`hold(choose().data)` 的副作用探针单独保存为 native-only：当前 dsim 对接收者
求值一次，VCS 对该探针调用 `choose()` 两次。正向 VCS 对照使用显式临时句柄，
不把该差异计作已对齐。

未修改的完整 Accellera UVM 2020.3.1 已越过 `uvm_reg_item.svh:281`，下一阻塞
为 `uvm_event.svh:268` 的事件句柄赋值。完整 UVM 编译和 `run_test` 仍未完成。
