# M176：时间语义与 UVM 基础类型（开发验证，未发布）

本地及103稳定入口仍为 M175。本批补齐实际公开 UVM 暴露的四类通用能力，
未修改公开库源码，没有使用替身库。完整 UVM 仍不能编译运行。

- 原生时间常量、timeunit/timeprecision：定义作用域、CU/编译指令/本地声明优先级、
  参数覆盖、类参数特化和实例克隆；时间值保持 realtime，延时按局部 precision
  取整再转换到全局 tick。支持声明中的 `timeunit 1 ns / 100 ps`，
  表达式中的 `1 ns` 仍拒绝。全局精度计入未实例化设计元素及有效 timescale。
- 匿名 enum 变量：模块、类、过程及 packed struct；每个声明保留独立类型身份，
  标签先绑定、变量顺序初始化；保留枚举方法、容器元素和参数化克隆语义。
  不以生成 typedef 或文本替换实现。inline 枚举端口/形参/返回类型尚未补齐。
- 动态数组/队列的 positional assignment pattern，包括空模式 `'{}`、重复模式、
  函数返回值、泛型类句柄及 packed struct 元素。支持 packed 容器成员及切片写入。
  keyed/default、关联数组模式、动态 unpacked struct/real/string 容器仍有缺口。
- 包级、模块级和 automatic 局部 const 标量、字符串、实数及类句柄：
  保留只读变量与可变 pointee 的区别，拒绝赋值/递增及 writable ref/output。
  非类 const 当前要求声明初始化，const 数组尚未完整支持。

同时允许静态变量用运行时表达式初始化，保留 pre-initial 执行和依赖分区。
原 integer/time 的“运行时初始化不支持”拒绝用例改为实际执行正例，另验函数副作用、
函数内部 automatic 局部变量及只执行一次；静态初始化直接引用 automatic 变量仍拒绝。
修正整数常量求值器对 `enum.name()` 字符串比较误查 packed width 的问题。

## 原生验证

四组17模型、310份波形捕获、32项编译拒绝、两次预测回滚/提交通过。
比较 serial/time-wheel/threads=2 三种后端请求，ordered/settled 两种模式，
标准文本 VCD、同步 DWF 与独立线程 DWF 的逐信号值；同步/异步 DWF 字节一致。
threads=2 请求通过不代表所有模型都实际分为多个分区。
回放与用户指定层次、信号和时间范围的波形检查通过。
对应摘要为 `native-*.json`；53份生成C++和32个输入文件的SHA在 `bindings.json`。

完整 parser 增加时间和匿名枚举的重复克隆/清理检查，通过正常及 ASan/UBSan 构建。
17模型前端、32拒绝、17生成程序和两份回放的 ASan/UBSan 均通过；
生成 C++ 与正常构建相同，异步 DWF 与正常构建字节一致。
integer/time 的两份静态运行时初始化模型另经 ASan/UBSan 执行，
前端生成代码和异步波形与原生回归相同，见 `sanitizer-initializers.json`。
不包含 LSan 或本批新 TSan 结论。详见 `sanitizer-*.json`。
原有声明、容器、类常量和延时回归见 `guards.json`。
`*-initial.json` 保留本批早期五模型检查，不作为当前17模型的验收结果。

## 问题 cases 复查

复跑 `dsim-test/cases` 中2026-10-28/29的八个近期 rtlagent-dual 问题归档，
完整保留原输入、archive SHA校验、每步180秒预算与旧日志。
累加存储的三份归档、gather/lut各两份及retained-memory均编译运行通过，
40888个观察点逐个匹配冻结预期，见 `reported-cases.json`。
retained-memory本机本次编译60.974秒，未重新测VCS，不能据此做速度比。
这是当前开发版对既有问题的复验，不计作本轮新增修复或全部cases完成。
原有 `$fatal` 退出策略负控归档不属于这八个有效比较归档。

复现：`python3 validation/m176-time-literals/cases.py build-m176/dsim ../dsim-test/cases <out>`，
每次创建新的 replay 目录，保留原归档记录。

## VCS 差异与远端状态

首轮同源五个时间模型中三个通过，另外两个尚未对齐：
`lexical` 的实数精确相等断言失败；`precedence` 的物理值相同、写法不同的
重复精度声明被 VCS 拒绝。`lexical-detail.sv` 已提交103用于打印各个真实值，
结果尚未收齐，不能把差异归为舍入问题或算作通过。

首轮12拒绝源中 VCS 拒绝10个，接受两个。声明中的单位前空格已补齐为原生正例
`spaced.sv`，当前同名拒绝用例检查的是表达式空格；低于1fs的 `0.1fs`
仍为已知差异，当前整数fs tick表示不支持。不能把12个原生拒绝称为12个VCS一致。
原始结果和拒绝源分别保留在 `vcs-initial.json`、`vcs-initial-negative-sources.json`。
新17模型及空格修复尚无本轮 VCS 对照结果。

103上已有诊断任务的 SSH 会话仍无返回；额外只读 echo 探测在20秒内无输出，
客户端被该次探测的 timeout 结束，见 `remote-readonly-probe.json`。
这不证明原VCS作业已终止，因此没有重复启动编译，也没有替换远端稳定入口。
本批没有新增性能结论或稳定版发布。

## 公开 UVM

未改动 Accellera 2020.3.1、使用 `UVM_NO_DPI`；正常/ASan 预处理保持
1888084字节、166依赖及原SHA。
原来的时间常量、匿名 enum、空队列返回与包级 const 阻塞已越过，当前首个语法错误为
`uvm_sequencer_base.svh:426` 的 `all_sequencer_insts[int unsigned]`。
见 `public-normal.json` 和 `public-asan.json`。首错移动不代表其前面全部内容已通过语义检查；
factory/phase/objection/sequence 仍未完成公开库原生执行验收。
后续继续补齐 typed associative index、IPC、virtual interface/clocking、coverage
及完整约束随机，完整 REPORT/UVM 目标仍在推进。

复现每组：`python3 tests/<group>/regression.py build-m176/dsim build-m176/check-<group>`，
其中 group 为 time_literals、anonymous_enums、runtime_array_patterns 或 const_variables。
在加载 VCS 环境的103上运行：
`python3 validation/m176-time-literals/vcs.py tests/<group> /tmp/dsim-m176-vcs-<group>`。
Sanitizer：`python3 validation/m176-time-literals/sanitize.py build-m150-asan/dsim <accepted> <out> <group>`。
