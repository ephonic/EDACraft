# SDF 条件路径执行

开发版 `--sdf-annotate` 已把叶单元 specify 的 `if (...)`、`ifnone` 与 SDF `COND`、`CONDELSE` 接入实际生成程序。原有 SDF 独立流式 parser、条件词法身份匹配、目标模型精度、ABSOLUTE/INCREMENT 和十二种转换延迟表继续使用；RTL 与门级 parser 没有合并。

条件在准备调度输出变化时求值。条件的最低位为 1/X/Z 时启用，为 0 时禁用；这与 timing-check 条件的真值规则分开实现。多个启用路径仍按最近输入时间选取，同刻取本次输出转换的最小延迟。`ifnone` 只考察相同源/目的端点、且匹配本次源边沿的显式条件，不受其他输入路径的条件影响。新VCS对照确认条件成立但边沿不匹配时仍选择 `ifnone`，早期相反实现已修正。没有对应条件的 `ifnone` 等同无条件路径，带边沿的 `ifnone` 或同端点同时声明无条件路径会明确报错。

条件可使用现有标量端口、常量位选端口、直接端口别名链、0/1/X/Z 单比特常量、括号、`!`/`~`、逻辑/位运算及相等比较。读取输出状态的条件使用实际延迟端口值，避免读取内部原始求值信号。一般内部组合网的 elaboration、算术/关系/三目/多比特条件表达式、specparam 条件常量等仍未接入；未知/多驱动/循环别名和未支持表达式会拒绝生成，不会静默当作无条件路径。

条件谓词编译为按模型复用的本机函数，只读当前 Sim 值。已有输入时间戳、路径输出历史、延迟通道和待交付载荷负责时序状态，并随检查点恢复。只有实际模型使用条件路径/ifnone 时才生成 `DSIM_CONDITIONAL_PATH_ENABLED`；无条件路径保留既有代码生成分支。IR 的 `gate_design.conditional_module_paths` 和 `path_conditions` 记录实际使用。

本地九类用例覆盖四态真值、重叠条件、case equality、端口别名、边沿/ifnone、增量、输出状态条件、缺省无路径和无条件路径并存；每类在通用/标量与堆/时间轮四种后端实际编译，共216份完整ordered/settled × VCD/raw/Zstd捕获及16份检查点/拒绝预测回放捕获。三类实际内核、生成的标量＋时间轮回放也通过本地ASan/UBSan。完整回归及Linux/VCS进度见[本批记录](../validation/m4-conditional-paths/README.md)。

语义依据为本地已下载的 [IEEE 1800-2017](https://fpga.mit.edu/6205/_static/F25/documentation/1800-2017.pdf) 30.4.4、30.5.3。输出选择时刻探针现已由VCS W-2024.09连续三次确认19/107/219/319ps；八类非edge条件用例各三次通过，edge差异已据原始TRACE修正。旧430批未整体验收，当前432组合源正在执行完整本地/Linux92项与新九例VCS对照，见[后继记录](../validation/m5-sdf-jobs/README.md)。完整pulse/RETAIN、PORT/DEVICE、负检查延迟信号和普通Verilog自动并行等仍需后续工作。


修正边沿/ifnone后的432组合源现已完成Linux原任务并从3549份证据独立核对PASS；九类新VCS各三次、全部五个顶层物理位与选择时刻探针三次均通过，两平台各92项及实际全SDF两作业版本各128笔通过。旧430失败结论保留，不改写为通过。最终证据见[432组合验收](../validation/m5-sdf-jobs/verification.json)。
