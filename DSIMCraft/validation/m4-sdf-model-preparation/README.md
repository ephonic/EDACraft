# 全量 SDF 模型准备与 RTL 内部延时

新增独立 `dsim_sdf_models`，按原始 SDF 的精确路径 / 检查身份生成专用测试模型，复用现有 SDF parser 和提供的 Liberty tokenizer。功能代码保持一致；specify 被替换为零初值声明，补入两条直接端口条件别名。它不是厂商签核库。RTL 与门级 parser 保持分离。

原始 300,909 单元网表、1.2GB Liberty、完整 SDF、宽测试平台均保持哈希。111 种模型生成 336 条唯一声明，覆盖全部 1,744,700 项：867,982 IOPATH、790,222 INTERCONNECT、86,496 时序检查；17,124 条条件项均为检查事件。实际生成及编译完整 C++，执行 128 笔输出与本轮重新编译的 VCS 逐项相同。

这里使用默认非负检查模式：23,051 条负 limit 更新夹零，VCS 注解同样报告 23,051 NNTC 错误、0 warnings。没有关闭检查或删除 SDF 项，也不能称为零错误注解、完整负检查模式或签核等价。首次默认事件预算退出保留，以显式 `--max-events 2000000000` 成功执行。native 单次 CPU 115.09s 是未经固定 CPU / 重复采样的观察；不能与 VCS 内部 CPU 打印相除作为速度比。

RTL 新接入 `q = #constant expr`：在入口采样 RHS，等待后赋值；覆盖 `#0`、拼接目标、256 位四态、循环、模块精度、实际检查点与失败预测恢复。尚未接入延时 NBA、动态 delay 或连续赋值 delay。新增 grammar 分支曾影响普通 NBA，宽值完整回归发现后已撤回该 NBA 分支，失败日志保留。

最终源码两平台各 55/55 完整回归通过；统一五种流程在 macOS 原生及 Linux 新编译 VCS 差分全部通过，包括 RTL 内部 delay。17 组模型准备案例逐项比对实际 VCS 完整警告流；仅 negative 案例有预期 1 条 NNTC。实际模型准备的三组 ASan/UBSan 和实际生成 RTL 回滚程序的 ordered/settled 完整波形通过；不宣称远端缺少 sanitizer 库的平台通过该检查。原 ZIP 加累积补丁的 108 个 parser 文件逐个重放一致。

`source.json` 标识最终 409 文件源码及归档身份，`changes.json` 对照上一批。远端 `/tmp/dsim-sdf-models-1018-QqIIpBwp` 以最终编译器重新生成完整模型及 C++，均与先前已执行程序逐字一致；`linux/milestone-metadata.json` 记录原始输入、编译器与二进制哈希。`linux/` 保留全量生成源码、原始日志、VCS 注解、17 组微例及五种流程波形。完整网表和 Liberty 仍在原授权路径，不复制入证据包。

性能采样使用 GDB 运行自己的子进程，原始 MI 与函数栈观察单独保留。首次脚本因目标 stdout 与 MI 响应共享行而中断，保留 `full-gdb-initial.*`；修正响应识别后重新采样，完整正常退出，共 252 个样本。另按保留的 MI 修正 C++ lambda 名称中花括号的解析，保留修正前 JSON。`Sim::set` 60 次、输入延时 handler 29 次、路径选择 28 次、`publish_compact` 21 次、`drive` 20 次、`drive_after` 与堆调整各 14 次。采样执行独立于未插桩计时，不把栈次数换算为 CPU 占比。具体差异与优化顺序见 [性能归因](../../docs/performance-gap.md)。

运行 `python3 validation/m4-sdf-model-preparation/verify.py` 重新核对源码、归档后文件、输入身份、覆盖计数、功能模型一致性、128 笔输出、NNTC 类型、两平台回归及实际流程。`verification.json` 记录最终核对结果。
