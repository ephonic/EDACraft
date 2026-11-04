# SDF 实际延迟的 VCS 参考探针

为下一步实际回标准备独立 oracle，不计为 dsim 已支持延迟仿真。输入先由当前 native `--sdf-check` 解析，再用 VCS W-2024.09 默认优化编译，另有明确列出的脉冲选项。主批 9 例、补充 2 例，每例三次；8 个独立预期均匹配，3 个选项探针保留实际观察，所有结果确定。探针与其他正确性任务并行，没有性能结论。

| 项目 | 独立输入与观察 |
| --- | --- |
| corner | SDF 1ns，rise `(1.125:2.25:3.375)`、fall `(2.125:3.75:5.375)`；MINIMUM/TYPICAL/MAXIMUM 的输出时间分别匹配对应分量 |
| 模型精度 | 模型 1ns/10ps、TB 1ps/1ps，0.125/0.135ns 分别落到 **130/140ps**；不是全局 1ps 下的 125/135ps |
| 合并 | 先 ABSOLUTE rise/fall 3/5ns，再 INCREMENT -1/+2ns，得到 2/7ns；不能先丢弃负增量 |
| 12 transition | `(01,10,0Z,Z1,1Z,Z0,0X,X1,1X,X0,XZ,ZX)` 分别指定 1–12ns，隔离输入的全部四态转换按相应延迟发生 |
| INTERCONNECT | 同一个 DUT 输入到两个接收 pin 分别 1/3ns，两个零延迟 buffer 的输出分别晚 1/3ns；不能只给整个 net 一个延迟 |
| 默认脉冲 | 2ns 路径、1ns 输入脉冲被拒绝，5ns 输入脉冲正常通过 |

仅 `+delay_mode_transport` 或仅 `+transport_path_delays` 在本探针中仍拒绝 1ns 窄脉冲，annotation 日志仍记录 `+pulse_r/100, +pulse_e/100`。补充 `+pulse_r/0 +pulse_e/0` 时，窄脉冲的两个输出沿分别出现在 22/23ns。不能只凭 transport 选项名称推断模块路径已保留全部脉冲；此项限定于本安装与此模型，未推广到所有延迟对象或 VCS 版本。原 `vcs1017.md` 快照保持不变，本探针补充它未覆盖的明确微例。

所有观察从 10ns 后开始，跳过初始化 time-0 事件；初次输入变化晚于标注，避免把初始化竞争当作延迟语义。每例保存一份 annotation 报告、三次运行 trace，不把三次 trace 算作三次重新标注。所有 annotation 报告均为零 errors、零 warnings；VCS 编译保留了主机 Linux 版本警告。

主批源与驱动 SHA 见 [source-snapshot.json](source-snapshot.json)，补充选项批见 [pulse-options/source-snapshot.json](pulse-options/source-snapshot.json)。原始 Verilog、SDF、解析摘要、VCS 命令/编译日志、三次 trace 及 annotation 日志随 [0.13.0 证据](../m5-compiled-process/README.md) 保存：`remote-verified/build/sdf-delay-probes/` 与 `remote-verified/build/sdf-pulse-options/`。主包 `/tmp/dsim-sdf-delay-probes.tar.gz`、补充包 `/tmp/dsim-sdf-pulse-options.tar.gz` 可在已构建项目目录解包后运行各自的 `run-sdf-*.py` 驱动。

native 的实际延迟事件、目标模型精度、12 transition 选择、取消/脉冲及 per-receiver INTERCONNECT 尚需实现并用同输入差分；COND/specify 匹配、RETAIN、timing checks/notifier 与复杂竞争继续属于完整回标范围。
