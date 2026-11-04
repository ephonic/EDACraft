# M66 动态数组元素 NBA

2026-10-23。为一维整型动态数组接入完整元素的即时、延迟和事件控制非阻塞赋值，
涵盖两态/四态、96 位有符号元素、input/inout 自动形参和局部数组、任务返回、fork 取消、
自动槽复用、分区与失败预测。RTL/gate parser 保持独立；本批修改 RTL compiler/runtime，
沿用已有 NBA/延迟/事件队列，未修改 parser grammar 或拆换调度器。

普通/延迟 NBA 绑定发出时的元素分配；替换分配后跳过旧目标。
VCS 探针确认，同长度 `new[n](self)` 保留目标，整体赋值（含 self assignment）重新分配。
事件 NBA 取样索引和 RHS，在事件成熟后解析当前数组存储；允许发出时为空、触发前分配。
运行时分配代次与调用身份分别防止旧更新写入新分配或复用的自动变量槽。

## 实际 VCS 核对

六最终同源模型 sample/targets/events/lifetime/control/parallel 在
10.131.254.103 的 VCS W-2024.09 编译执行。
`verify.py` 核对全部 **675 条已导出物理位 settled 时间线及 TRACE**，无位排除、无 wrapper 映射。
动态元素仍不导出波形声明，由共同的 scalar 读取/TRACE 观察；不是所有动态存储位的完整 dump。

保留六条独立 VCS 探针及三类非法索引运行探针，原始输入、日志、源 hash 和结果均保存：

- 重新分配、同长度自初始化、整体自赋值的待交付目标身份。
- 事件控制取样索引一次，在触发后解析当前存储，空数组触发前分配成功。
- ref 形参延迟 NBA 在 dsim 原生扩展用例通过，VCS 编译报 NYI。
  原生扩展单独测试，不能计为六模型对齐。
- 一个延迟 NBA 索引函数探针中 dsim 调用一次、VCS 调用两次。
  保留兼容差异，原生回归锁定一次求值；不计对齐通过。
- 三个未知/负数/越界的延迟 NBA 索引用例两端编译成功、运行失败；不声称诊断文本完全一致。

八类编译拒绝中 VCS 拒绝五类，编译接受三类（always_comb timing、事件源 mutation、
function 内 NBA）。这些沿用当前限制，见 `diagnostic-comparison.json`，未当作功能对齐。

## 本地验证

六同源模型执行串行、时间轮、threads=2，ordered/settled VCD/DWF：72 次基础捕获。
sample/targets/events/lifetime/control 在 1ns 检查点执行实际失败预测，另在 control/lifetime
分配前预测恢复，合计 **79 捕获、7 次失败预测**；12 次取消调用保持存储有界，
已发出 NBA 在取消后仍交付。parallel 确认实际两分区，两个结果均为 42。
ref 原生扩展另跑三后端，索引函数差异和三类运行错误单独核验。

29 项不同本地定向 CTest 最终通过：19 项受影响内核重建后检查（9.17 秒）、
三种新内核（3.10 秒）、六项受影响 RTL（首轮五通过，一项旧负预期修正后 24.91 秒通过），
最终新功能回归 83.84 秒通过。旧 delayed_nba 回归把合法事件 NBA 误列为拒绝，
改为隐式事件控制的真实边界并清除旧生成文件后重测；保留原失败日志。

ASan/UBSan：六最终同源生成程序及完整 ordered 流、两份原生独立程序、
六语料各三轮 parser 清理、完整 parser 语义单测、三种新内核通过，leak 检测关闭。
新内核覆盖分配与调用身份、宽/两态值、回滚、事件前分配/resize，以及 25 次自动帧复用。
初轮内核夹具将 `V(2)` 当作多位尺寸，实际默认一位被截断，已改用显式 32 位尺寸；
函数内 NBA 诊断预期亦改为先触发的既有函数语句限制。
首轮事件目标假设经 VCS 独立探针纠正，运行时增加描述符调用身份后重新核验。
这些初轮问题不计最终通过。

最终源和生成代码 hash 见 `source-manifest.json`、`source-archive.json`、`final-identity.json`。
Linux 最终 1454 文件冻结源干净构建、四项 parser/新内核检查、六串行/一实际双分区程序
14 捕获、两份原生独立探针、三类运行错误和八类编译拒绝通过。
12 份完整 C++、六完整 ordered 流/stdout 及五份独立程序的 stdout/stderr 跨平台一致，
再核对全部 675 条 VCS 位时间线。最终源包 SHA256：
`8e1235b49cdeae4bad912526567938d8538e99365bba4ea1a6763c8c4eb6b22f`。
Linux 验证范围和跨平台结果见 `linux/` 与 `results.json`。
未跑全量 CTest、Linux sanitizer 或新增性能测量。

## 仍待补齐

动态元素 packed/member 选择、拼接目标、元素 scalar-ref 绑定、整体数组 timed/NBA、
多维动态容器、数组返回/声明初始化/assignment pattern、固定/动态形参互转和更完整转换，
以及动态元素波形声明仍待补齐。递归、队列/关联数组、class/约束、完整 SVA/覆盖率/UVM
继续不具备完整支持，M47/M55/M60/M62/M63 的既有边界保留。
