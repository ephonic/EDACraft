# 整张关联数组的 ref / const ref

M227 支持把整张关联数组按 `ref` 或 `const ref` 传给自动函数/任务。实际存储可为
模块变量、自动局部变量或类成员；支持嵌套转发和有延时的任务，保持原数组身份。

```systemverilog
class Store;
  int entries[string];
endclass
function automatic void put(ref int items[string]);
  items["ready"] = 1;
endfunction
// put(store.entries) 修改类成员本身。
```

引用要求维数、索引类型、容器边界和元素类型等价。已验证 string、整数、宽整数及
class 索引，整数/class 元素、多维整图和整数队列叶。const ref 禁止修改数组元素、
结构或转交可写引用；函数间转发和 foreach/exists/delete/整数组赋值沿用既有操作。

类成员引用缓存对象/字段的稳定身份，接收者变量重绑后，已传入的引用仍访问旧对象。
成员写入会同时通知引用上的等待者；代理缓存与激活帧随 checkpoint 恢复。
未使用新引用能力的模型不启用运行时代理路径。

接收者副作用仍有已知差异：`hold(choose().entries)` 在 dsim 求值一次，VCS 探针
求值两次，与 M222 动态数组引用的边界一致。本轮单列该探针，不计为对齐。

仍未支持关联数组的值传递、output/inout、函数返回和选中子数组的 ref 绑定；
字符串元素的关联数组签名仍有限制。VCS 接受本轮部分拒绝形式，包括选中子图、
静态 ref、值实参及有界队列叶的形态，不能视为同等拒绝。完整分类见验收目录。

未修改 Accellera UVM 2020.3.1 已越过 resource_pool:178 的 spell checker 实参，
下一实际阻塞为 objection:459 的 `process::kill()`；`process::await()` 也是后续已知缺口。
完整 UVM 仍未生成原生模型或跑通 run_test。本轮无新性能或 C910 结论。
