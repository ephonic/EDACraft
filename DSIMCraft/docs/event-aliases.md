# 类成员与自动局部事件的复制

M224 支持在类成员事件及自动局部事件之间做立即阻塞赋值，也可以把模块的静态
事件绑定给上述目标。复制保存的是同一个事件对象的身份；多个变量可引用它，
任一别名触发时，等待该对象的进程都会收到同一次事件。

```systemverilog
class notification;
  event pulse;
  function void copy(notification rhs);
    pulse = rhs.pulse;
  endfunction
  function void reset();
    event fresh;
    pulse = fresh;
  endfunction
endclass
```

`@(obj.pulse)` 在进入等待时捕获事件对象。随后给 `obj.pulse` 绑定另一事件，
已经等待的进程仍跟随旧对象。`->> #delay obj.pulse` 同样在发出时保存目标，
不会因句柄随后重绑而改向。`wait(obj.pulse.triggered)` 则按当前变量值重新判断。

自动函数、任务及显式 `automatic event` 块声明会在激活时创建独立事件，
局部变量复制给类成员后，变量离开作用域仍保留事件身份。重置会创建新对象；
旧等待者可继续通过另一个旧别名被唤醒。

`null` 可赋给这些事件变量。VCS 对照确认，等待空事件会永久阻塞，普通和 NBA
空触发是空操作，查询空事件的 `.triggered` 会报错。类 `%p` 输出中的空事件
显示为 `null`。空类对象的字段访问仍报错。

本轮保留明确边界：普通模块事件作为赋值目标、声明时的事件别名/初始化、事件
数组、带延时的句柄赋值、事件形参和返回值尚未接入。VCS 接受其中的模块目标和
带延时赋值，不能把 dsim 的这两项诊断算作同等拒绝。事件不是整数，不允许把
句柄当作数字、选择其位，或对句柄做 NBA 赋值。

运行时按索引保存事件状态、等待订阅与别名通知，均随 checkpoint 恢复。
模块事件被类字段引用时也会通知相应的状态依赖，保证 `.triggered` 等待能唤醒。
未使用新能力的模型保持原有事件路径；本轮没有新增速度或多核性能结论。

未修改完整公开 UVM 已越过 `uvm_event.svh` 的事件复制/重置，下一阻塞为
`uvm_printer.svh:1501` 的运行期字符串重复表达式。完整 UVM 仍未编译运行。
