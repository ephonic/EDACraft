# 编译门级的固定敏感列表

已采用实现及最终验收见 [本批记录](../validation/m5-fixed-wait/README.md)。本轮真实设计 CPU 中位数降低约 22.9%，共享主机、模式与范围按该记录限定。

门级每个组合/sample 进程只有一个终生不变的输入列表。原 `arm_wait(site)` 每次增加 process generation，再把同一 generation 写入列表的所有 watch。新的 `add_fixed_wait(process, events)` 在 elaboration 注册完全相同顺序的 watch；它们和进程的 generation 都保持零。`arm_fixed_wait(handle)` 只恢复 waiting。原 `set()` 的 waiting/generation/edge 判断逐字不变。

等价条件是该进程永不切换敏感列表，也不进入动态或延时等待。运行时用 `WaitKind` 记录这一约束：只允许尚未使用等待 API 的编译进程绑定一次固定列表；通用闭包、已有固定/动态列表、先前调用过 delay/wait 的进程均被拒绝。固定进程随后调用普通 wait、注册其他 site 或 delay 也会报错。空列表合法，表示只能由初始排队或显式 enqueue/NBA 唤醒。新增枚举利用 Process 的已有 padding，目标平台上 Process/Watch 仍为 24/16 字节。

对满足条件的进程，原实现每次重新等待后所有 watch 都与 process 的 generation 相同；新实现也恒等相同。重新等待前后的 waiting/queued 状态、边沿掩码、watch 顺序、进程 ID、创建顺序和队列顺序均不变，因此每个信号变化唤醒的进程和顺序相同。重复输入仍逐项登记，由 waiting 和 queued 阻止重复入队；不做去重或组合锥融合。反馈进程继续先 arm 再求值，保留零延迟自触发与预算保护。commit 与 sample 的 NBA 位置不变。

固定列表省去 gate 的 WaitSite/WaitRef 元数据及反复遍历和写回，不删除实际 watch，也不省略任何信号事件。一般 RTL、多个动态 site 和延时等待仍使用原 generation 协议。模式防护增加的成本必须通过长周期普通 RTL A/B 检查，不能只报告门级收益。

检查点直接复制模式、waiting、队列和 watch；不可变固定列表没有外部指针缓存。生成 model context 的 handle/状态仍由拥有者注册快照。回滚时连同队列和可观察输出恢复。并行分区各自拥有内核，固定等待不引入跨分区共享可变表；1/2/4 worker、多个 quantum 的确定性输出与线程检查单独验收。

这是零延迟门级路径的已验收优化，不是实际 SDF 回标或自动并行分区。今后的时序功能如果需要让 sample/comb 进程改变等待方式，必须选择普通等待模式或重新证明固定列表约束，不能绕过防护。
