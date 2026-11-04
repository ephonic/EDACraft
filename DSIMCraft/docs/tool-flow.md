# 统一编译、波形与 VCS 差分流程

在工程根目录运行：

```sh
python3 scripts/run_flow.py tests/flow/manifest.json
# 在 VCS 主机上，先 source /apps/EDAs/syn.bash
python3 scripts/run_flow.py tests/flow/manifest.json --vcs
```

需要把编译器和验收工具送到另一台主机时，使用 `python3 scripts/package_source.py /tmp/dsim-source.tar.gz`。包中包含独立波形解码器及脚本依赖，并附逐文件 SHA256 清单；排除 macOS 的资源元数据和 Python 缓存，避免接收端 CMake 将资源文件误认成 C++ 源码。

入口按同一份 JSON 清单依次处理 RTL、门级零延迟、门级 SDF。每次创建独立 `build/flow/run-*` 目录，保存输入及二进制 SHA256、完整命令、生成 C++/IR、stdout/stderr、波形和 `results.json`。某例失败后仍继续其余例；最终退出码非零，报告保留失败阶段与诊断路径。超时会终止该阶段的整个编译/运行进程组。

每例先编译一次启用波形能力的 native 程序，再分别运行不输出波形、VCD、压缩 DWF 三种模式。三次 TRACE 必须相同，有 `expected_trace` 时还必须匹配固定参考；独立解码器比较 native VCD/DWF 的完整字典和事件流。Linux/macOS 每个阶段独立记录 wall、user/system CPU、峰值 RSS；两种波形均记录实际文件大小。这里只运行一次，极小程序的 CPU 可能被计为零，不能据此声称性能收益或压缩率普遍成立。

`--vcs` 使用清单指定的 Verilog 功能模型与源文件独立编译。辅助模块捕获 VCD；SDF 情况对指定测试平台实例执行 `$sdf_annotate`，要求首次注解日志零 errors、零 warnings。比较完整 TRACE 和选择的稳定态位波形，时间统一为 fs。未指定 `wave_bits` 时比较 native 顶层全部位；指定时逐个检查键存在且值/时间相同，不取两个字典的交集。内部 delta 顺序、未选择的 VCS 信号和一般设计等价性不在此检查的结论内。native 的两种格式仍比较完整流。

最小清单：

```json
{
  "cases": [{
    "name": "design",
    "sources": ["tb.v"],
    "top": "top",
    "gate_netlist": "design.v",
    "gate_top": "dut",
    "liberty": ["cells.lib"],
    "gate_models": ["models.v"],
    "sdf": "design.sdf",
    "corner": "typ",
    "vcs": {
      "sources": ["tb.v", "design.v", "models.v"],
      "sdf_instance": "top.d"
    }
  }]
}
```

输入字段中的文件路径相对于清单目录。只运行 RTL 时省略所有 gate/SDF 字段；零延迟门级省略 `gate_models` 和 `sdf`。`sources` 始终只交 RTL parser，`gate_netlist` 交独立结构 parser，Liberty 与模型元数据各走自己的 reader。SDF 路径相对于 `gate_top`，VCS 的 `sdf_instance` 是完整测试平台实例路径；当前 native 不提供 SDF 相对层级重定位。

可选 `dsim_args`、`run_args`、`vcs.compile_args`、`vcs.run_args` 原样传给对应工具，不经 shell；其中额外路径应写绝对路径。`trace_prefix` 默认 `TRACE `，必须至少捕获一行。`wave_bits` 为键数组，例如 `["top","d","fast","A",null]`；最后一项为位索引，scalar 用 null。scope capture 目前要求普通层级标识符，不接受转义名称。测试平台若已有 dump/annotation，请避免重复，示例的 VCS_REFERENCE 分支默认不启用。

每例可另设`wave_compression_jobs: 4`和`wave_block_events: 4096`：前者要求整数1–16，后者要求整数1–1,000,000；省略时沿用原生默认同步压缩和块大小。两项只传给DWF运行，不影响无波形、VCD及VCS对照；不要通过所有运行共用的`run_args`设置这两个波形选项。报告的`wave_controls`保留显式配置，阶段命令保留实际参数。布尔、浮点、字符串及越界值在编译前拒绝，失败例仍保留诊断并继续后续案例。六类实际RTL/门级/SDF流程的1/4/16线程配置已在两平台各通过18次编译、54次模式运行、12对DWF文件逐字节身份，36份跨平台捕获完整一致；新增`tool_flow_async`本地正式CTest已通过，Linux实际执行相同脚本。见[流程验收](../validation/m6-async-flow/README.md)，尚无异步压缩性能收益结论。

M149增加用户范围字段，例如：

```json
{
  "wave_scopes": ["top.cpu", "top.bus"],
  "wave_include": ["*data*", "*valid"],
  "wave_exclude": ["*debug*"],
  "wave_depth": 2,
  "wave_start": 1000,
  "wave_end": 8000,
  "wave_async": true,
  "wave_buffer_bytes": 8388608
}
```

范围传给VCD/DWF两个阶段，无波形阶段不带这些参数。列表必须非空且元素是非空、无NUL字符串；深度为0–10000，时间为0–UINT64_MAX整数，布尔不视作整数。非法配置在编译前拒绝。起止时间按编译tick解释，区间包含两端，进入窗口时输出已有状态，不改变仿真执行。具体选择和dump交互见[波形范围](waveform-format.md#用户指定输出范围m149)。启用范围时，VCS对照默认检查全部所选声明位，并将参考时间线裁剪到相同物理时间；显式`wave_bits`仍按用户列举的键验证。

门级清单可设 `partition_report: 4`，在同一次编译和三种波形模式执行中生成并保存 `partition_analysis`，并可继续执行 VCS 差分。该字段仅分析 gate-only 零延迟域及正延迟边，生成程序的执行方式仍为 serial；它不是线程数开关。具体边界见[并行说明](parallel-and-rollback.md)。

SDF 清单可设置 `prepare_sdf_models: true`，由编译器同目录的 `dsim_sdf_models` 先生成 SDF 专用测试模型，再同时供 native/VCS 使用；独立阶段记录 CPU/RSS、工具与模型哈希和逐类型覆盖报告。功能源只经词法预处理，原始 SDF 不改。详见[模型准备](sdf-model-preparation.md)。清单中的 `sdf-prepared` 演示条件别名与错误占位检查的替换；`rtl-delays` 验证采样式阻塞赋值内部延时；开发版新增 `rtl-sdf-delays` 将延时 NBA、连续赋值、三态原语和 SDF 串接，本地三模式通过，VCS 验证待执行。

只有用户主动设置 `disable_timingchecks: true`，两工具才明确关闭检查；报告不把这种运行称作 timing-check 支持。native VCD/DWF 比较现使用 `scripts/compare_waveforms.py`，逐条比较完整有序事件，不保留完整历史；内存仍包含信号字典、块索引、当前解码块和 VCD 行。`--vcs` 的稳定态位时间线比较仍保留历史，不能据此宣称全流程均为有界内存。自动并行、自动预测器和一般 SDF 性能仍是后续里程碑。

## 本轮实际结果

本地RTL、门级零延迟和SDF三种模式通过；Linux VCS差分三种模式通过。清单中的SDF例已升级为INTERCONNECT后接非零5ps IOPATH，另在两平台通过，VCS侧完整TRACE及选择的5个位匹配、注解0errors/0warnings。VCD和DWF的native完整流一致。失败流程另外验证了保留具体诊断、继续下一例并最终返回非零。

首批真实原始300,909单元网表曾停在256位mul_a的顶层1..64位限制（历史证据validation/m4-interconnect-runtime）。后续[多字值后端](multiword-values.md)已解除该限制：原样网表与Liberty、直接256/257位接口实际编译运行，128笔输出匹配同一测试平台新编译的VCS；没有拆分或改写原始网表。原既有分块激励/monitor映射到原始宽端口，保留刺激顺序。本次没有验证原始完整设计的大波形或全量SDF执行。

宽值五种流程在两平台通过，Linux另新编译VCS：宽RTL算术、四态端口/NBA、256位零延迟门级、256位INTERCONNECT+IOPATH SDF、仅中间表达式超过64位；native无波形/VCD/DWF的TRACE一致、完整VCD/DWF解码一致，VCS比较完整TRACE和选定位。实际回滚/提交和1/2/4 worker通道另行验证。严格全量SDF的诊断与输入哈希见[本批记录](../validation/m4-wide-values/README.md)，功能兼容与数学算法正确性、单次观察与配对性能验收分别记录。

九类常用时序检查现已接通。[模型准备批次](../validation/m4-sdf-model-preparation/README.md)随后解除占位模型的HOLD/条件身份阻塞，原始完整SDF已实际运行且128输出匹配新VCS；没有关闭检查。默认非负模式仍夹零23,051次负检查更新，VCS亦报告相应NNTC，不作为零错误注解或完整负检查支持。完整真实设计的大波形、条件IOPATH和自动并行仍需后续验收。
