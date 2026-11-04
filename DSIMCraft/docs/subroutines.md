# 静态用户函数与任务

M45 的[表达式事件控制](event-expressions.md)可用于 task，包括 automatic 形参驱动的动态位/数组字选择与组合边沿。事件表达式中调用用户函数仍明确拒绝，普通过程表达式里的函数支持保持原范围。

M44 允许子程序使用词法外部[静态命名事件](named-events.md)：task 可挂起等待，函数可发出阻塞/NBA/延迟 NBA 触发并立即返回。静态局部事件可用，automatic 局部事件和 event/ref 形参仍拒绝。

支持模块和 generate 词法作用域中的静态 `function` / `task`，无参数任务支持 `tick;` 和 `tick()`；M78 修复前一种形式的空指针，见 [用户 RTL 报告](rtl-report-fixes.md)。ANSI 与经典形参声明均可使用；参数化模块和 generate 实例分别保存自己的子程序状态。RTL parser 负责绑定和克隆，门级紧凑 parser 保持独立。

函数支持 input/output/inout 形参、void 返回类型和阻塞写词法外部变量；[复制及副作用细节](function-effects.md)。值函数支持 input 形参、默认 1 位返回值、integer 返回值及 signed/unsigned packed 宽返回值，通过函数名赋值返回；支持局部静态变量、条件、case、已有过程循环和嵌套函数调用。整数形参默认 32 位 signed，显式 unsigned 和 time 形参见后继[类型扩展](integral-types.md)；packed 形参按声明转换。调用实参先计算再写入形参，函数结果参与上下文位宽转换；未赋值的静态返回变量保留上次值。函数表达式支持四态条件分支与逻辑短路，生成代码显式排序带状态的操作数。

```verilog
function integer sum(input integer n);
  integer total;
  begin
    total = 0;
    for (int i = 0; i < n; i++) begin
      if (i == 2) continue;
      total = total + i;
    end
    sum = total;
  end
endfunction

task step(input integer n, output integer result);
  begin
    #2;
    result = sum(n);
  end
endtask
```

任务支持 input/output/inout、局部静态变量、嵌套任务/函数、delay、事件等待、阻塞赋值及 NBA。input/inout 在调用入口采样，output/inout 在任务返回时复制给实际目标；目标的动态数组地址在返回时求值。任务体内联为调用进程的 PC 指令，可以跨 delay/event 挂起恢复。静态形参和局部变量由同一实例的各调用点共享，不提供 automatic 并发激活存储栈。

连续赋值和传统 `@*` 只把函数调用实参计入隐式敏感集合；`always_comb` 还包含函数体读取的外部信号。任务体不向隐式敏感集合递归展开。并行分区依赖另外记录子程序实际触及的共享状态，避免把共享静态子程序误判为独立域。

函数编译为 C++ 表达式中的固定 PC 执行代码，任务编译进调用进程，运行时不遍历 parser AST。静态状态使用现有 Signal 存储，接入 VCD/DWF、检查点和失败预测回放；普通 RTL 独立域并行可与受支持子程序共同使用。

M31 已增加[非递归 automatic 函数/任务](automatic-subroutines.md)，包括每次入口初始化、跨 delay/event 的调用隔离和循环块生命周期。

尚未支持：递归/相互递归、完整并发激活语义、常量函数展开、函数中的任务调用/时间控制/NBA/系统任务、层次子程序调用、数组形参及完整 SV 子程序类型/默认参数/ref 语义。已识别结构明确拒绝，原 parser 仍有语法覆盖限制，不代表完整 IEEE 或 VCS 兼容。

验证入口：

```sh
ctest --test-dir build -R '^rtl_subroutines$' --output-on-failure
python3 validation/m15-subroutines/verify.py
```

本批五例包含静态状态、宽 signed 形参、整数循环、动态 output 目标、任务等待/NBA、参数化 generate、两独立域、波形及失败回放。实际 VCS 比较也包含其导出的函数/任务形参、局部变量和返回变量；具体覆盖与限制见 [M15 验收](../validation/m15-subroutines/README.md)。本批未做新的速度测量。

子程序已支持提前 `return` 和复合赋值，详细出口及目标求值规则见 [过程操作说明](procedural-actions.md)。

形参及函数返回值已扩展到 `integer unsigned` 和 `time`，详细符号/位宽及兼容边界见[类型与端口说明](integral-types.md)。

两态 bit/byte/shortint/int/longint 形参与函数结果、任务复制转换已接入，见[两态类型说明](two-state-types.md)。

M28 已增加 [typedef/enum/packed 聚合形参及返回类型](type-signatures.md)，保留符号、范围和类型身份，涵盖任务复制和 return。

M29 增加 [函数输出形参及副作用](function-effects.md)，含空 ANSI 函数/任务形参表、函数语句调用及 `void'(f())`，非过程表达式禁止 output/inout 函数。

静态子程序新增 [ANSI 默认值、命名与空位实参](call-arguments.md)，包括调用作用域遮蔽、延时任务取样及输出默认目标。

默认与命名实参见 [M30 扩展](call-arguments.md)；automatic 支持边界见 [M31 扩展](automatic-subroutines.md)。

M41 范围更新：静态变量数组及常量前缀子数组的整体过程复制已接通，覆盖阻塞/NBA、net 源、宽字和 automatic 局部数组；当前类型规则、赋值内 delay 的实际 VCS 差异及仍缺范围见 [数组整体赋值](array-copy.md)。此前文中“整体复制仍缺”的描述以此范围更新，整体声明初始化、数组形参及动态数组仍缺。

M42范围更新：静态数组的动态前缀子数组过程读写/NBA已接通，含越界/未知索引与取样时点，见[数组复制](array-copy.md)；模块端口连接仍要求静态前缀，数组形参及动态容器尚缺。

M43 新增[wait(condition)](level-wait.md)，含函数实参敏感集合、automatic task 挂起/重入、NBA 唤醒及失败预测回滚；同时接通 function logic/reg 默认/显式 signed/unsigned 与 packed 返回范围。wait fork/wait_order 及完整事件区域仍缺，验收见 [M43](../validation/m43-level-wait/README.md)。

M79 按用户 v2 报告接通 ANSI function/task 首组 named typedef 形参的缺省 input 方向，例如 `function automatic logic[16:0] f(req_t q)`。支持首组同类型多个名字、已有 packed struct/enum typedef 语义及后续显式方向组；未扩展为所有省略方向/数据类型和匿名 struct 形式。原始 t08 源与额外 function/task/enum 自检见 tests/rtl_report/v2，验收见 validation/m79-random-functions。
