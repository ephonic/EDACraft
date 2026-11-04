# 关联数组的值传递与回写

函数和任务的整张关联数组支持 `input`、`output`、`inout`，与已有
`ref` / `const ref` 区分：值参数拥有独立存储，output/inout 在正常返回时
替换调用者的数组。延时期间调用者看不到形参修改；automatic 子程序的递归或并发调用各自保留副本。

```systemverilog
typedef int map_t[string];
task automatic collect(output map_t values);
  values["count"] = 12;
  #2;
endtask
```

支持模块变量、自动局部变量、类的关联数组字段及多维子数组实参。
索引类型、剩余维数与元素类型必须兼容；保留类键身份、枚举与聚合类型检查。
深复制关联树及队列叶存储，类句柄元素仍指向同一个对象。
共享自动任务返回时先保存被调者的值，再切换调用者帧执行回写，避免递归覆盖。
任务递归使用 `--shared-functions`。关联数组函数返回值、混合未打包容器维度、
动态数组元素 ref 及类的标量字段 ref 仍有缺口。

另外修复了迟创建类特化的虚分派表缺项：存在虚调用时，将新发现的类注册到
下一次 lowering 的起点，直至类集合收敛，最后生成代码。类型顺序采用稳定 ID；
不以设计名或 UVM 路径选择实现。

原始完整 UVM 已生成并编译本机验证程序，但运行仍被类标量字段 ref 阻塞，
尚不能宣称完整支持 UVM。测试和 VCS 对照见
[M231 验证记录](../validation/m231-associative-values/README.md)。
