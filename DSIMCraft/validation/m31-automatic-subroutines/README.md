# M31 automatic 子程序与 VCS 对齐

新增非递归 automatic 函数/任务：每次入口初始化 output、返回变量、局部标量和单维数组；四态 X、两态 0；局部初始化读取实参、前序整数声明及函数副作用；嵌套过程块每次入口初始化。任务跨 delay/event 的局部状态按调用点和调用进程隔离。接通默认/命名实参、符号/两态/宽值、enum/packed 类型与退出复制；补齐命名、隐式一位、packed 和内建返回类型语法。RTL parser 与紧凑门级 parser 保持独立。

当前不支持 fork/递归/动态进程，采用有界编译激活槽足以覆盖该子集；不是通用动态栈。状态保留依赖、检查点及回放，automatic 临时量不导出静态层次波形。没有改动 runtime.hpp/parallel.hpp，也没有新性能测量。

六个同源输入位于 tests/automatic_subroutines：

| 模型 | 主要验证 |
|---|---|
| lifetime | 重复入口、未写 output/返回值、整数声明顺序、两态/多字/数组清零或 X、局部初始化副作用 |
| overlap | 两进程重叠延时任务、局部数组/形参隔离、inout 返回复制、循环重复调用 |
| blocks | 循环块每次入口初始化、延时挂起、初始化函数副作用 |
| types | typedef/enum/packed/two-state、经典与 ANSI、默认/命名目标、void；隐式一位和 packed 三种声明形式、byte 返回 |
| events | 重叠事件等待、外部 delay/NBA 单次取样、动态默认输出地址 |
| parallel | 同一 automatic 任务在两个真实独立分区中执行，无共享局部状态 |

串行/时间轮/双线程 × ordered/settled × VCD/DWF：72 次捕获，另有 overlap/events/blocks 三组失败预测回放，共75次。回放从1ns开始，此时任务已在 delay/event 上挂起；检查点恢复局部值、PC、等待和输出事务，完整 ordered 波形及打印与普通执行一致。parallel 必须报告 partitions=2，另有两域逐时刻独立数学预期。25类负例检查 automatic 变量 NBA、递归/ref/fork/显式 static、函数时间控制/任务/系统任务、重复 lifetime 和类型/目标边界；拒绝进程不能崩溃。

实际 VCS W-2024.09 在 10.131.254.103 上执行，先 source /apps/EDAs/syn.bash；使用 -full64 -sverilog -debug_access+all，top 与独立 dump wrapper。六组源文件逐字相同，TRACE 和全部1272条导出物理位时间线相同，无信号/位排除或名称映射。automatic 私有状态双方都不导出；其行为通过返回值、自检、并发调用和回放独立验证，不把不可见局部位计入位数。完整输入、命令、编译/运行状态和原始 VCD 在 vcs/，verify.py 校验源身份、声明身份、每位变化及 TRACE。

probes/lifetime.sv 是先执行的 VCS 生命周期探针，原始结果在 vcs-probe/。该探针函数内含 $fatal，native 当前明确拒绝函数系统任务；不宣称原样 native 通过。最终六组共同输入均将系统任务检查放在调用者中。初期 blocks 用例误用保留字 before，已改为 stamp 并重新执行双方；语法边界检查发现 automatic 命名返回类型抢占隐式返回声明，已拆分共同前缀并补入三种形式的正例。最终 Bison47个shift/reduce，与M30一致，无reduce/reduce。

同一 integer 声明现在逐项分析、注册和初始化绑定，单遍处理；运行时初值未知时 parser 数值占位保持有效32位X。普通 int/logic/命名类型的同一声明内前序项引用尚未同步扩展。仍缺 ref、递归、常量函数、完整数组、显式 static 局部、层次调用、package/interface/class、完整SVA/UVM、动态进程和完整时序/事件区域，尚无未使用默认值的完整声明期诊断。

最终验收状态与数量见 results.json。保留本地定向CTest、ASan/UBSan parser单测/六组输入各三轮清理及六个实际生成程序日志（含真实双线程，关闭leak检测）；Linux使用冻结源包重新干净构建和六项定向CTest，并核对七份完整实际C++及同源VCS波形。source-manifest.json/source-archive.json 和 final-identity.json/platform-identity.json 用于核对工作区、源包、Linux源码及实际生成物。此前M30共同输入也以当前编译器重跑，2993条VCS位时间线另记 prior-m30-vcs-results.json。未跑全量CTest、Linux sanitizers或新性能测量。

复验：

```sh
ctest --test-dir build -R '^rtl_automatic_subroutines$' --output-on-failure
python3 validation/m31-automatic-subroutines/verify.py
```
