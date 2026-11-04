# 前置 class 别名与 process 索引（M195）

支持公开 UVM 源码使用的前置声明与后续 typedef 组合：

```systemverilog
typedef class Handle;
class Client;
  Handle item;
  function Handle pass(Handle value); return value; endfunction
endclass
class Store #(type T=int); T value; endclass
typedef Store#(int) Handle;
```

变量、属性、形参、返回值和其他 typedef 保留共享的语义类型绑定；后续定义完成时统一获得规范 class 身份。别名链、参数化目标、类属性初始化、ref 参数、赋值/转换、队列及 class 关联键使用同一绑定。模块和参数化类克隆重新建立绑定，不跨实例复用语法节点。循环别名、缺失定义、非标量 class 目标及错误 ref 类型会拒绝。

这是公开库兼容扩展：实测 VCS W-2024.09 对独立 module 和 package 中的上述最小结构均报 IPD/SV-UFCD。不能将扩展语料记为 VCS 同源对齐。直接定义同名 class 的原有前置声明能力保留。尚未完成的别名用于类模板实参时明确拒绝，避免按未绑定类型缓存错误特化；需要先完成 typedef 定义。提前 extends 不完整别名及需要即时成员布局的使用仍有限制。

另补 `process` 首次出现于 `array[process]` 的类型绑定，包括参数化类属性。沿用 class 键的类型检查、存取、游标及 foreach；已有同名可见声明仍优先，未将任意未定义标识符当作类型。

未修改 Accellera UVM 2020.3.1 的预处理保持 1,888,084 字节、166 依赖。原生编译越过 event_pool 别名及 tlm_fifo 的 process 索引，下一处错误为 `uvm_reg_model.svh:300` 的无符号枚举 `UVM_CVR_ALL=-1` 检查。完整 UVM 仍未编译运行。

受影响发布回归脚本可通过 `DSIM_TEST_COMMAND_TIMEOUT` 设置每条命令超时（默认仍为 180 秒），发布器传入 `--command-timeout`，解决外层组时限调长而内层模型编译仍固定 180 秒的问题。该调整不将任何超时计为通过，也不改变生成模型的优化选项。

语料见 `tests/class_forward/{alias_types,alias_chain,alias_clones,alias_package,process_keys}.sv`；最终验收见 [M195 记录](../validation/m195-forward-alias/README.md)。没有性能结论。
