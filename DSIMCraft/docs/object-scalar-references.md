# 类属性 ref 引用

实例的整个单值属性可以作为函数或任务的 `ref` / `const ref` 实参。
支持 integral、四态/宽向量、string、real、枚举、类句柄及整个未打包 struct。
类型须等价；打包位选择、struct 子字段和动态数组元素引用仍有边界。

引用保存对象和字段的身份。调用者重新绑定对象句柄后，已传入的引用仍指向
原对象；多个引用共享同一属性，修改立即可见。直接写属性和经引用写入都能
唤醒相应等待者，任务取消后不执行后续写入。引用缓存随 checkpoint 一起复制，
失败预测恢复对象值、别名和等待状态。

```systemverilog
class State;
  int value;
endclass
task automatic change(ref int value);
  value = 7;
  #2;
  value = 9;
endtask
```

当前拒绝把 const 属性传给 nonconst ref；VCS 接受该探针，记录为差异。
带副作用的接收者表达式按一次求值；同源 VCS 探针为两次，亦保留差异。

未修改的完整 Accellera UVM 2020.3.1 已通过基本 run_test 和真实
sequence/driver 集成，后者覆盖 factory override、config_db、sequencer、
analysis port/imp、scoreboard 和 objection，三笔数据总和为 303。
这些测试均使用 `UVM_NO_DPI` 和原生 `-O0` 功能验证，不能据此推断全部 UVM 支持。
`uvm_field_*` 自动化仍被左值流式赋值阻塞；DPI/VPI 等能力仍需继续补齐。
见 [M232 验证记录](../validation/m232-scalar-refs/README.md)。
