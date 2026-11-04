# M58 显式 static 局部声明验收

状态：**PASS_SCOPED**。补齐 begin/fork 和 task/function 局部变量的显式 static 限定，覆盖现有整数/logic/bit、命名/enum/packed 类型、固定数组及静态命名 event。automatic 子程序不同调用点和重叠调用共享同一静态声明，其他自动变量/形参独立，模块实例间隔离。常量初始化仅启动时一次，取消和重新进入不重置；静态目标支持 NBA/延迟 NBA。

RTL parser 声明保留互斥的 static/automatic 属性，绑定/参数克隆/清理及 grammar/lexer/生成文件同步，Bison 冲突仍为 47。编译器按实例与声明源位置共享存储，避免 parser 为调用复制 AST 导致节点身份变化；波形按词法名字导出一次，保留原有网线层次别名。写入持久静态变量的 automatic 函数不会被误判为安全事件回调。未改门级 parser、runtime 或调度器。范围见 [功能说明](../../docs/explicit-static.md)。

## 验证范围

- [六组共同输入](../../tests/explicit_static)：跨调用点静态函数状态、嵌套块、参数化双实例隔离，静态/自动局部重叠，130 位/四态/两态/enum/数组默认值，延迟 NBA，join_any/取消/返回，静态命名 event 的共享/NBA 触发，以及实际两分区。
- 串行/时间轮/双线程，VCD/DWF ordered/settled 全逐信号流一致，**77 次捕获**；四个挂起期间与一个分配前的失败预测，**5 次实际恢复**。12 次调用后检查进程不超过 16、信号槽不超过 100；9 类非法或尚未支持用法明确拒绝，包含带静态副作用的合法事件函数这一保留缺口。
- 真实 VCS W-2024.09：六份模型 SV 字节相同，TRACE 和 **1293 条物理位 settled 时间线一致，无位排除**。VCS 默认 VCD 略过 automatic 子程序中的静态局部，使用 [16 条只读层次观察线](observers.json) 导出全部 **525 位**，其余 768 位按原名比较。观察线只读取模型状态，不改共同输入或驱动；[比较脚本](verify.py) 要求全部物理位身份/时间线严格一致，映射在 [结果](vcs-results.json) 明列。[VCS 日志](vcs) 含源、观察模块、命令及运行状态。
- 最终本地 **15 项不同定向 CTest** 通过：11 项受影响回归 225.59 秒，automatic 子程序/网线数组/parser 单测最终分别 56.64/48.15/0.28 秒，新功能最终输入 66.55 秒。不是全量 CTest。
- macOS ASan/UBSan：六个最终实际生成程序（含真实双线程）和完整 ordered 流、六语料各三轮 parser 清理、完整 parser 语义单测以及 kernel/wheel/compact 三内核通过；leak 检查关闭。所有程序与最终生成 C++ 的哈希再次核对，见 [sanitizers/results.json](sanitizers/results.json)。
- Linux 按最终冻结的 **1221 文件**另目录干净构建，parser 单测和三个帧内核共 4 项 CTest，以及六串行/一个真实双分区程序、14 个波形捕获通过。**7 份完整 C++ 字节相同，六个完整 ordered 流和 stdout 跨平台一致**，再核对相同 1293 条 VCS 位时间线通过。见 [Linux 结果](linux/results.json)、[跨平台比较](linux/cross-platform.json)。未做 Linux sanitizer 或全量回归。

## 开发期间发现的问题

初轮静态声明使用 AST 指针身份，因 parser 对每个调用复制子程序体导致未共享；改为实例和声明源位置后关闭这一实际错误。波形去重仅作用于共享静态变量，避免丢失原有网线别名。初轮 12 项既有回归 11 通过、1 项失败（248.03 秒），原因是旧 automatic 子程序测试仍预期拒绝显式 static；边界更新后通过。新增测试还修正了会使分区合并的诊断语句、空 task 负例语法及 iff 诊断断言；原始失败日志保留，不计通过。

首个 Linux 冻结版本（1220 文件）自然完成并通过，但其 control 模型仍使用隐式 for 索引；最终另目录重新构建 1221 文件的验收输入，前次结果单列 [initial](linux/initial)，没有中断进程。

## 既有边界

[原始 inline-for 探针](probes/inline-for.sv) 的 native/VCS TRACE 都为 `TRACE control 156 12 0`，native 额外导出 `top.$unm_blk_1.i` 的 32 位，VCS 默认 dump 没有该索引；尝试内部层次名也被 VCS XMRE 拒绝。原始 [两侧波形及日志](probes/inline-for) 保留，记录为 **TRACE 一致、波形导出未对齐**，不算主对齐通过。最终主模型将计数器显式声明在模块作用域，全部位参与比较；没有删除差异位。

module/for 头部 lifetime、显式 task/function static 限定、递归/ref/动态容器、整数组声明初始化、非恒定静态初始化和 automatic 局部 event 仍缺。M47 静态/带副作用函数事件限制和 M55 逃逸局部直接事件等待差异保留。本批没有新性能测速，不宣称完整 SV 或 VCS 全功能/性能对齐。

## 复现与证据

入口：`ctest --test-dir build -R '^rtl_explicit_static$' --output-on-failure`。[VCS](run-vcs.py)、[sanitizer](run-sanitizers.py)、[Linux 模型](run-linux.py) 运行器及 [Linux 构建驱动](linux/driver.py) 保留。完整覆盖汇总于 [results.json](results.json)，七份最终程序哈希见 [final-identity.json](final-identity.json)。

[source-manifest.json](source-manifest.json) 与 [source-changes.json](source-changes.json) 记录最终冻结源，1221 个文件归档后哈希再次核对一致。源包 SHA256：`8edfe73bb5cff085f6e6729b4c6e12639779efd01b7c629e1a5bcb6d5c764f1b`。原始日志保留工具空白和失败记录。
