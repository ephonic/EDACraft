# M54 重叠 fork 激活

生成 C++ 执行路径支持静态存储分支的重叠 join_any/join_none。编译模板保存初始闭包，重叠时分配独立 PC、重复计数器、延迟取样、分组、等待点及命名控制目标；只读映射区分每个激活。静态变量按 SV 规则共享。分支树全部完成或取消后复用槽，避免每轮追加进程。可增长的闭包表采用稳定地址存储，避免分支启动时移动正在执行的函数；无 detached fork 的设计继续使用原表。详见[功能范围](../../docs/dynamic-fork.md)。

wait fork 等待所有活跃直接子进程，存活孙进程不阻塞该等待，但会阻止其父槽过早复用。disable fork 与词法命名块 disable 取消对应后代；克隆的静态命名目标仍按词法身份跨活跃调用生效。已发起 NBA 保留。新增执行记录、订阅、PC 和池归 Sim 所有，检查点可恢复分配之前的进程数和分配后的等待状态。

审查用例复现了表达式操作数在分支启动前变化时，旧求值任务误唤醒新等待的问题。修复为 fork 分支实际进入表达式等待时重取样；先断言时间0没有触发，再于1ns真正改变操作数，双方四分支均正确唤醒。ctest-initial.log 保留初次失败，最终重新构建并完成53项定向回归。RTL/parser 和门级 parser 均未改。

真实 VCS W-2024.09，10.131.254.103，source /apps/EDAs/syn.bash：9份字节相同源文件的 TRACE、自检和 **1028条物理位 settled 时间线**一致，无别名或位排除。包括批量分支、join_any 尾部分支、孙进程仍存活时重启、命名事件/条件/普通表达式等待、包围命名块取消、克隆分支内命名目标取消、延迟 NBA 保留、双分区和150次启动后的槽复用。legacy.sv 与 M53 当时被拒绝的原始 overlap 探针字节相同，该具体缺口已对齐。

9模型×串行/时间轮/双线程×VCD/DWF×ordered/settled 共108捕获，any/events/nested 各一次实际失败预测恢复，共 **111捕获、3回滚**。完整逐信号 ordered 事件流和 stdout 在各后端一致，parallel 实际 partitions=2。直接 kernel/wheel/compact 检查点覆盖尚未分配时回滚、已有多个定时分支时恢复，以及准确的独立进程数。recycle 的150次启动检查进程数有界。automatic 父存储在编译阶段明确拒绝，重叠分支访问 automatic 变量在分配前明确拒绝；没有把这两项当作支持。

macOS 最终 **53项定向 CTest** 全通过，422.96秒。ASan/UBSan：9个实际最终生成程序、9语料各三轮 parser 清理、parser 语义单测和3种直接内核通过，含真实双线程；leak 检测关闭。10份完整 CPP（9串行、1双线程）重生成字节相同，sanitizer CPP hash 与最终程序相同。

Linux 从冻结1159文件源包干净构建 **9项定向 CTest** 全通过，287.52秒，退出0；包括3种新内核、新旧 fork、named disable、automatic 子程序及 compiled/gate 回归。10份完整 CPP、9份完整逐信号 ordered 流/stdout 跨平台一致，再对照同样的 VCS 1028条物理位时间线。源包SHA256 `335a7fe4bfff8d71c0a57c80d0cb258d8127e1e595a1cf937963a7ae6599cdc0`；source-manifest.json 在构建前后核对，plan1017.md和验收输出不在清单。保留代码、IR、日志、退出码、波形，不保存仿真可执行文件。

仍缺 automatic 动态变量帧、父帧逃逸与共享寿命、递归、process 对象、外部/层次任务 disable、完整 SV 事件区域/验证语言/SVA/UVM 及既有精确时序能力。本轮功能优先，未新测速，未跑全量 CTest 或 Linux sanitizer。

复跑：`ctest --test-dir build -R '^(rtl_dynamic_fork|dynamic_fork_kernel|dynamic_fork_wheel|dynamic_fork_compact)$' --output-on-failure`；`python3 validation/m54-dynamic-fork/verify.py`。
