# RTL 时间单位与波形时间轴

M46 新增[条件事件控制](conditional-events.md)，条件读参与分区合并，源取样与待求值任务随快照恢复；真实 VCS 范围见 [M46](../validation/m46-conditional-events/README.md)。

M45 新增[表达式事件控制](event-expressions.md)：依赖变化在 Active FIFO 排定合并求值，以缓存的四态结果判断值变化/最低位边沿；选择和 automatic 作用域在入口重取样。缓存与待求值任务随检查点恢复，实际 VCS 探针区分同刻毛刺与入口基线。

M44 新增[命名事件的延迟 NBA 触发](named-events.md)：`->> #delay e` 在入口求值并排定，当前过程立即继续，到期进入 NBA。查询时间戳、排队触发和订阅基线随检查点恢复；同刻持续查询及隐式过期的通知行为已用实际 VCS 探针核验。

0.10.0 增加物理时间基准。RTL 与门级 parser 仍分离；当前有限 SDF 运行时见[sdf-runtime.md](sdf-runtime.md)。

预处理保留 `` `timescale unit/precision `` 与 `` `resetall ``，按模块声明记录有效单位；状态跨输入文件和 include 继承，关闭的条件编译分支不生效。directive 必须在模块外。默认使用 `1s/1s`，可用 `--timescale 1ns/1ps` 设置默认值，源文件中的显式声明覆盖它。`resetall` 恢复 CLI 默认，不清除宏。`-E` / `--emit-preprocessed` 保留这些声明，输出可再次编译。

elaboration 在实际实例化的模块中选最细 precision；未实例化的模块不参与选择。IR 的 `global_precision_fs` 和各 scope 的 `time_unit_fs` / `time_precision_fs` 为整数 femtosecond。预处理依赖报告中的 `declared_min_precision_fs` 只是所有已声明模块的最小精度，不等同于 elaboration 的全局精度。

常量过程延迟按以下顺序编译：保留十进制原文 → 按所在模块的单位和精度精确舍入（半数向上）→ 转成全局 tick。转换复用 SDF 的十进制换算函数，不经浮点中间值，检查 uint64 溢出；运行时继续检查绝对时间相加溢出。支持整数、整数参数、小数和科学记数法的独立 literal。暂不支持 real 参数或 real 算术，其他表达式里的 real literal 明确拒绝，避免原 lexer 将 `1.25` 静默截成 `1`。

运行时整数表达式延迟现已接入 `#d`、`#(d+8'd1)`、`q = #(d) rhs` 与 `q <= #(d) rhs`。延迟在语句入口求值一次，后续变量变化不修改已排定事件；阻塞内部延迟同时保存 RHS，NBA 保存 RHS 和目标切片后立即继续。按所在模块 unit 转成全局 tick，检查缩放和绝对时间溢出。与 VCS 探针对齐：含任意 X/Z 位时延迟为零；已知宽整数取低 64 位再缩放。零过程延迟进入 Inactive，零 NBA 延迟进入当前 NBA。延迟表达式的信号读集合参与自动并行依赖合并，等待中的状态与既有队列共同回滚。常量 literal 继续原有直接常数代码路径；未使用运行时延迟的程序不定义 `DSIM_DYNAMIC_DELAY_ENABLED`。验证入口为 `tests/time/dynamic_delay.py`，覆盖采样、部分写、混合 timescale、双线程依赖与 pending-event 回放。signed/real 延迟表达式仍受既有语言边界限制。

阻塞赋值内部延时 `q = #5 expr;` 已接入：进入语句时按目标上下文宽度采样右值，将四态值保存在该进程状态中，延时结束后赋值并继续执行。`#5 q = expr;` 则在等待后读取右值。`#0` 通过 Inactive 区恢复；常量部分选/拼接目标、宽值、循环及层级模块精度共用既有赋值路径。采样值与 PC 一起随检查点恢复，拒绝预测后的 stdout 与 ordered/settled VCD/DWF 已做实际生成程序对照。RTL grammar 只增加阻塞内部 delay 分支，普通 NBA 保持原解析路线。

M49 新增[阻塞赋值内部事件控制](intra-event-assignments.md)：`q = @event rhs` 与 repeat 形式，先取样 RHS、等待后计算动态目标；重复次数在 RHS 之前求值。非阻塞内部事件赋值仍明确拒绝。

非阻塞赋值内部延时 `q <= #5 expr;` 现已接入：语句执行时采样右值并排队，当前进程立即继续。到期事件进入该时刻的 NBA 队列，在 Active/Inactive 工作之后提交；`#0` 直接进入当前 NBA 队列。同一进程发出的多次更新全部保留，不使用门级脉冲取消策略。常量部分选/拼接目标记录固定目标位置，到期时只替换目标切片，保留届时其余位。支持四态、多字宽值及模块精度舍入；待更新值、目标位置、定时顺序和可重用事件池随仿真检查点复制，预测失败时恢复。

编译器仅在实际实例化的 RTL 使用延时 NBA 时定义 `DSIM_DELAYED_NBA_ENABLED`，为底层 `Sim` 开启 `assign_nba_after(id,value,ticks)` / `assign_parts_after(parts,value,ticks)`。未使用此功能的程序继续使用原 Timer 布局和调度分支。RTL grammar 与语义校验单独扩展，门级 parser 不变。实现验证入口为 `tests/time/delayed_nba.py`、`tests/time/delayed_nba_kernel.cpp`，本批验收记录在 [延时 NBA](../validation/m4-delayed-nba/README.md)。

开发版另接入连续赋值及标量原语的常量非零 delay、rise/fall/turn-off 选择与短脉冲取消，详见[连续延迟](continuous-delays.md)。新 VCS 实测发现向量规则与初版不同，修正版默认按 VCS 最低位选择，显式 `--continuous-delay-mode ieee` 保留标准文本的向量选择；12 组用例/84 捕获和两组 IEEE 对照定向验证通过，最终两平台完整回归进行中。动态连续赋值/原语 delay、无赋值的 net declaration delay、赋值内部 event/repeat 控制仍待接入；当前未支持的输入会非零退出。阻塞内部延时与统一流程的验证入口见 `tests/time/intra_assignment.py`、`rtl-delays`。

例如子模块 `10ns/1ns` 中 `#0.15` 先变成 2ns；若顶层精度为 1ps，就是 2000 个全局 tick。子模块此时 `$time` 为 0，因为它按子模块的 10ns 单位取整。`$time` 返回 64 位整数；`$realtime` 和一般 real 类型尚未实现。

`%t` 按调用模块的单位解释操作数，默认显示到全局精度。支持 `$timeformat(units, digits, suffix, width)` 的四个常量参数：units 为 -15 至 0、digits 为 0 至 15、width 为 0 至 1000、suffix 为常量字符串。格式化缩放使用十进制字符串，避免大 uint64 乘物理单位溢出。取整半数、未知操作数等边界按本批 VCS W-2024.09 探针校验；该受限接口不等于完整 real 格式化支持。

生成模型自动将实际全局精度写入 VCD / DWF。运行时 `--wave-timescale` 只能填写与编译精度相同的值，填不同值会在创建文件前报错，不能重新标记原始 tick。直接使用底层 `WaveCapture` 的独立 writer 测试接口仍可指定标签；生成的 RTL 模型总是传入编译精度。

底层 `Sim::print` 省略 caller unit 时按该内核 tick 精度解释数值；生成模型始终显式传入所在模块的单位。

时间格式属于 Sim 快照状态，失败预测不会泄漏格式变化或打印；同进程手工分区并行要求所有内核物理精度相同。普通 RTL 的 `--threads` 编译会合并共享全局副作用的过程，见[自动并行](automatic-parallel.md)。

验证入口为 `tests/time/regression.py`、`tests/time/runtime.cpp`、`scripts/compare_time_vcs.py`，证据见 [本批记录](../validation/m4-timescale/README.md)。

M43 新增[wait(condition)](level-wait.md)，含函数实参敏感集合、automatic task 挂起/重入、NBA 唤醒及失败预测回滚；同时接通 function logic/reg 默认/显式 signed/unsigned 与 packed 返回范围。wait fork/wait_order 及完整事件区域仍缺，验收见 [M43](../validation/m43-level-wait/README.md)。
