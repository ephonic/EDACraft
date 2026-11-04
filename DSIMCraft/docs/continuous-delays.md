# RTL 连续赋值与原语 delay

RTL parser 已修正原语实例分组：支持有名、无名、混合和同声明多个实例，保留各自的完整端口组；裸 `#2`、`#D` 与括号形式可接在实例列表前。本批已通过本地72次编译、432份完整捕获及原始SDF无名buf的216份捕获，另验证两层参数展开和72组组合层次；Linux六项定向CTest、660份跨平台完整捕获、110份完整CPP身份及两个新VCS构建/六次运行对照已独立审计通过，见[验证记录](../validation/m4-primitive-groups/README.md)。门级网表parser保持独立。

开发版已接入 `assign #D net=expr`、带赋值的 `wire/tri #D net=expr`、既有标量逻辑原语的常量 delay，以及 `bufif0/1`、`notif0/1`。支持一至三个常量延迟值、模块时间单位/精度舍入、整数参数、小数和科学记数法 literal；逻辑原语只接受一至两个值，三态原语允许关断值。动态 delay、一般常量算术表达式、min:typ:max、非 strong 驱动、原语数组/多输出和无赋值的 net declaration delay 仍未接入。

连续赋值在输入变化时采样完整右值，不挂起求值进程。相同右值不推迟待交付事件；不同右值取消原待交付事件，回到本驱动已提交值时取消短脉冲。每个驱动独立维护状态，多驱动解析不会替代该驱动的提交值。延迟交付进入 Active，延时 NBA 仍按其独立规则在 NBA 提交。

默认 `--continuous-delay-mode vcs` 对齐实测 VCS W-2024.09：按采样 RHS 的最低位选择延迟，0 用 fall、1 用 rise、Z 用 turn-off、X 用三个值的最小值，再整体交付向量。packed 一位、位选、部分选、拼接和带赋值的 packed 声明均按此规则。它不是逐位分开交付，也不是各位延迟取最大值。16 种标量和 64 种向量转换、960 条观察已在三次 VCS 运行中完全一致，见 [探针证据](../validation/m4-continuous-delay/vcs-vector-probe/verification.json)。

`--continuous-delay-mode ieee` 保留 [IEEE 1800-2017，10.3.3](https://fpga.mit.edu/6205/_static/F25/documentation/1800-2017.pdf) 描述的向量选择：转为全零用 fall、全 Z 用 turn-off，其余用 rise；显式一位 packed vector、part select 和拼接保持向量规则，标量及 bit select 仍按四态选择。IR 的 `continuous_delay_mode` 记录所选模式。这里只描述已实现的选择规则，不表示完整 IEEE 语言支持。

切片、拼接、重复目标及 257 位值由一个完整 RHS 通道交付，再原子更新各目标驱动。待交付值、取消代次、目标映射、时间顺序和可复用载荷池随 Sim 检查点复制；实际生成程序的预测拒绝/重放与 ordered/settled 波形已通过本地检查。

生成器只在实际实例化的 RTL 使用非零 delay 时定义 `DSIM_CONTINUOUS_DELAY_ENABLED` 和 `DSIM_TIMING_ENABLED`，显式 IEEE 模式另定义 `DSIM_CONTINUOUS_DELAY_IEEE_MODE`。未启用连续 delay 时不增加通道字段或交付分支；修正后的 runtime 替换实际旧完整 SDF 程序后，同一 Clang 的预处理结果逐字相同。最终新 Linux 编译器已重读原始全量输入，默认/标量两版完整生成程序均仅差整个 runtime 替换，同 GCC 预处理逐字身份已通过独立核对。

底层 API 为 `continuous_driver(parts,width)`、`initialize_continuous(channel)` 和 `drive_continuous(channel,value,rise,fall,turnoff,scalar)`。在拓扑安装期登记通道、完成所有 net 连接后初始化为 X，再开始观察和运行；驱动身份须独占，后续经通道更新。生成器自动完成此顺序。该 API 不提供普通 Verilog 自动并行代码生成。

修正版本地定向验证通过 12 组默认用例、84 份捕获及两组显式 IEEE 模式对照；新语法支持 `wire [N:0] #D q=expr`。普通/紧凑/标量/IEEE 内核、实际生成预测重放、12 组显式并行全局结束配置的本地 ASan/UBSan 通过。最初 425 源 Linux 71 项虽全部通过，新 VCS 对照仍发现向量语义差异，已保留失败并修正；修正版 macOS 完整72/72（345.94s）、Linux完整72/72（468.38s）、12组新VCS各三次及六例公共/四例定向完整流程均通过，原始证据独立核对PASS，见[修正版证据](../validation/m4-continuous-vcs/README.md)。本批不声明仿真提速。
