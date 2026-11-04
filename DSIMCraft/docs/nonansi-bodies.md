# 无括号函数声明

函数头可以省略零端口的括号，函数体可以没有输入或局部声明。
原有规则仅覆盖至少一条声明的非 ANSI 函数，导致公开 UVM 的
`function void reset_report_handler; m_rh_init(); ... endfunction` 被拒绝。
本批为各返回类型和生命周期补齐无声明分支，保持原有非空声明列表，
不增加 parser 的 86 个 shift/reduce 冲突。

支持隐式一位、packed 范围、内建类型、typedef 和参数化类返回值，
automatic/static 生命周期、类构造器、虚方法及类外 extern 定义。
参数化类返回值的显式生命周期同时支持有/无局部声明。
空函数体、多个顶层语句及 endfunction 名称检查沿用已有 AST 和执行链路。
task 原先已有对应无声明规则，本批保留并复测。

```systemverilog
class Handler;
  int count;
  function new; count=1; endfunction
  function void reset; count=0; count+=2; endfunction
  function int get; return count; endfunction
endclass
```

`tests/nonansi_bodies` 四模型包括真实执行、函数返回与实参、构造器、
动态派发和预测恢复，检查74次捕获、同步/异步压缩波形及用户选定时间/信号范围。
四个原样源码的输出和四个拒绝边界均与 VCS 一致。
ASan/UBSan 覆盖完整 parser、前端、生成程序与回放；
程序及异步波形与普通执行相同。不据此声称所有子程序语法或完整 UVM 已支持。

未修改公开 UVM 2020.3.1 的首错推进到 `uvm_transaction.svh:443`
的 `const` 属性。受约束随机、IPC、virtual interface/clocking 和 coverage 等仍待补齐。
