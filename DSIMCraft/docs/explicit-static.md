# 显式 static 局部声明

M58 支持过程 begin/fork 及 task/function 局部声明的 `static`，包括现有整数/logic/bit、命名整数/enum/packed 类型、固定局部数组和静态命名 event。它覆盖 automatic 作用域的默认生命周期，而不改变同块其他声明或子程序形参。

```systemverilog
task automatic work(input integer n, output integer value);
  static integer calls=0;
  integer saved=n;
  calls++;
  #n;
  value=calls*10+saved;
endtask
```

不同调用点、重叠调用和派生 fork 共享 `calls`，而 `saved` 和形参按激活隔离。默认值按四态 X、两态 0 建立；常量初始化在仿真启动时只执行一次，退出/取消/重新进入不会重置。静态数组字、部分选择及 NBA/延迟 NBA 使用普通持久信号存储。静态命名 event 支持既有阻塞/NBA 触发和等待，automatic 局部 event 本身仍不支持。

RTL parser 为声明保留互斥的 lifetime 属性，模块参数化克隆后不丢失。parser 会为调用复制子程序体，编译器以模块/生成实例加声明源位置识别静态存储，避免按复制节点或调用槽分配；不同实例保持隔离。普通静态初始块使用已有词法作用域。门级 parser 独立，未修改。运行时和调度器未改。

静态读写参与过程依赖，独立模块仍可分为两区，实际共享存储会约束分区。写入持久静态局部的 automatic 函数不满足事件回调的无副作用约束，事件源/iff 中仍明确拒绝。波形使用词法子程序名字导出静态变量一次，自动局部继续隐藏，已有网线层次别名仍保留。检查点/失败预测恢复静态值与挂起事件状态。

本批只补局部声明限定。module/for 头部 lifetime、显式 task/function static 限定、递归/ref/动态容器、整数组声明初始化及读取变量/调用的静态初始化仍有缺口。M47 默认静态函数事件限制和 M55 逃逸局部直接事件等待差异保留。

验证：`ctest --test-dir build -R '^rtl_explicit_static$' --output-on-failure`。同源 VCS 使用只读层次观察线导出其默认 VCD 略过的静态局部；全部位参与严格比较，映射明列于 [验收证据](../validation/m58-explicit-static/README.md)。本批没有新的性能测速。
