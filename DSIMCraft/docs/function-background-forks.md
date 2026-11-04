# 函数中的后台 fork

M223 接通函数内的 `fork ... join_none`。函数本身保持零时间执行并返回，
子进程交给调用者所属的调度器，可使用延时、事件等待、阻塞任务、循环及嵌套 fork。

```systemverilog
function automatic void start(input int value);
  int saved = value;
  fork
    begin
      #2;
      $display("%0d", saved);
    end
  join_none
endfunction
```

后台子进程归属实际调用进程。调用者的 `wait fork` 和 `disable fork` 因而可等待
或取消这些子进程，另一个调用者的子进程独立。自动变量存储由子进程持有，
函数返回及后续调用不会复用仍在使用的存储；静态变量仍共享原来的变量。
模块初始化器的函数调用也能创建后台进程。

类方法、静态类方法、函数返回值和后台进程再次调用启动函数均走相同机制。
这是 UVM process guard 的队列监听与逐对象监视所需要的运行路径，
不只支持无延时子句。`ref` / `const ref` 的既有物理绑定可被后台帧保存；
对应正例已与 VCS 对照，VCS 会为这种直接引用捕获输出 SV-IATRA 警告。

函数直接使用 `join`、`join_any`、延时、等待或 `wait fork` 仍拒绝。
这些控制可以放在 `join_none` 的子进程中。`$finish` / `$stop` 在函数中的
支持属于剩余工作，不随本功能开放其他系统任务。

默认、共享函数体及时间轮模式接入同一运行时。`--threads` 对包含函数后台 fork
的设计保守使用单个仿真内核，因为子进程的所有者随调用者变化；IR 会标明
`serial-fallback`。这里不声称实现了这些后台进程的多核执行或新增性能收益。

REPORT-GAP13 的 UVM 结果来自打桩库。未修改的完整公开 UVM 仍先阻塞于
`uvm_event.svh:268` 的事件句柄赋值，完整 UVM 编译及 `run_test` 尚未完成。
