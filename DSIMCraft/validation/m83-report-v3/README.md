# M83 v3 报告修复验收

实现 `ca9b596`。修复层次固定数组元素/运行时索引读取、层次 enum 方法与 packed struct 成员、包内唯一共享可变状态，以及 `.vcd` 文件名自动选择已有文本 writer。保持 RTL/gate parser 分离，未改 DWF 编码，未提交 experiments/matvec16。边界见 [docs/report-v3.md](../../docs/report-v3.md)。interface/modport、完整 SVA 和其他列明限制仍未完成，没有新的性能对标结论。

## 输入及功能检查

REPORT v3 原文与 hash 已冻结；h_arr、h_deep、deep3 三原探针仅统一顶层名，原文件/变换后 hash 见 origin.json。7 模型在串行、时间轮和并行路径的25次完整 ordered 波形/输出一致，4次实际失败预测回滚通过，10类拒绝检查通过。parallel 模型实际两个分区，one/two 最终均为19。跨模块包状态用例的写者、读者、顶层与包任务观察同一值，包存储不按实例复制；共享依赖保持一个分区。最终编译器重生成21份有效模型完整 C++，逐字节等于执行的程序，见 final-codegen.json。

格式选择另外检查 hierarchy/parallel × 三后端 × 自动 VCD/自动 DWF/显式格式优先两种参数顺序，共24次完整信号流。检查实际文件头，自动 `.vcd` 为文本；显式覆盖优先于后缀。归档保存这些原始文件和规范后缀的同字节副本，独立解码比较全部 ordered 信号事件。

## 同源 VCS

实际 VCS W-2024.09_Full64 在授权主机运行7份同字节源；编译命令和原始日志保留。全部自检输出一致，728个共同公开物理位作完整时间线比较。其中727位完整一致；原始 h_deep 的 top.u.wen 在26ns `$finish` 同刻有已知端口适配尾部差异，26ns之前一致，完整原始两条时间线保留在 vcs-differences.json 与 vcs-alignment.json，未删除该位或宣称全波形相同。VCS top dump 不包含一些 unpacked word、subroutine 局部和独立 package 作用域；每一 native-only 位都列明，不冒称这些位已作 VCS 波形比较。二维数组另有显式 packed observer 和同源自检；三后端及回滚仍对所有 native 公开信号比较完整 ordered 流。

另行运行 v3 原始 interface 探针：VCS 也拒绝，因为 modport m/s 未声明 clk 却访问 b.clk。补入 input clk 的有效版本单独保存；dsim 尚缺 interface/modport，并未因此免除实现工作。

## Sanitizer 和既有检查

12个实际 C++ 程序通过 ASan/UBSan：7模型、4回滚及真正双分区程序；对应生成代码、全部输出和完整 ordered 波形一致，10类拒绝也由 sanitizer 编译器执行。编译选项、二进制/源码 hash 见 sanitizer-artifacts.json，leak 检测关闭。共享包符号的重复 parser 解析/克隆/清理检查在原生及 sanitizer 下通过。

开发过程中保留了过时 TRACE 前缀、暂不支持的显式包全局 static 语法、并行探针因 `$fatal` 副作用合并为单分区、旧 enum.name 拒绝文本预期等中间失败日志；最终以 native/results.json、sanitized/results.json、final-codegen.json 和发布检查为准。并行探针改为无副作用条件自检并在 VCS 同源重跑，不把 serial fallback 当作并行验证。旧 enum 测试检查无格式字符串的 display 诊断，现与已存在 string/name 支持一致。

发布与最终受影响回归结果在完成后追加。

已执行的受影响检查：enum_methods（修正旧诊断后）、array_queries、重新构建后的 wave_writer、parallel_wave_generic、parallel_wave_compact、parallel_finish_wave 共6项通过。waveform_dump_tasks 的16组主用例和多项额外检查通过后，在旧 SDF root-buffer extras 的 TRACE 预期处失败：额外时间零 `z=x`。上一稳定版 M82 对完全相同输入与本轮输出逐字节一致，见 baseline-sdf；不将完整 waveform_dump_tasks 计作通过，也不通过删除实际事件来掩盖。尚未完成该历史差异的独立 VCS 根因分析。

interface-probe/vcs-compile.log 是原始 interface 用例的实际两项 modport 可见性错误；vcs-valid.log 是加入 clk 后的实际 `D4 INTERFACE PASS`，二者源都保留。dsim 尚不能运行修正后的有效 interface 用例。

额外 integration 用例把用户 pkg_dut 集成测试写死的 `sn = "RUN"` 恢复为 `sn = dut.st.name`。原生和实际 VCS 均输出 `PKG_INTEGRATION PASS (st=RUN packed=14bff)`；与7模型/728位对照分开记录，仅声明输出和自检，不计作额外完整波形比较。

M83 稳定发布完成：实现 `ca9b596`，62项发布检查全部通过，入口更新到 `20261024T121303184886Z-436e883cea0d`。source SHA256 `436e883cea0d77ffa3f9b66fe0b8d0769a18783643e10013b0f4b709dc7e39e2`，binary SHA256 `8ed526d3cc550f6cf3b0601c522dcab9f9593494ecd6b606c0479dce6494b15d`。53个原有根模型、31随机、27 package、31 string、41 property 程序的完整输出/ordered波形保持一致，4个v2程序输出一致；25个新程序完整C++/输出/ordered VCD与原生验收一致，全部源码输入/运行时快照/二进制hash复核。旧程序因公共wave头变化不宣称C++与旧版相同。全部证据见validation/m83-report-v3，已知finish尾差、SDF旧回归失败与interface/完整SVA缺口继续明确保留，不新增性能结论。
