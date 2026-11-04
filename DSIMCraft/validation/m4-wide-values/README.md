# 已采用：多字RTL、原始门级宽接口与联合流程

多字四态后端已经接入默认编译器，覆盖无符号运算、端口、选择/拼接、NBA、网解析、格式输出、DWF/VCD、检查点与手工并行消息。根据实际表达式自动选择后端，普通窄程序保留24字节V；宽尾部不可变共享。RTL与门级parser保持独立，仅RTL lexer补齐未定宽x/z literal。原ZIP+累积补丁回放108个文件逐项一致。

- macOS/Linux各45项累计通过：首次完整回归44项通过，compiled_regression中的两个旧65位拒绝预期已改为真实超限输入，该项单独重跑通过。编译核心未为该测试修正而改变；不将其描述成单次45/45零失败运行。初始日志保留。
- 两平台各23,496项Python任意整数/逐位四态对照，包含跨word与混合上下文；测试宽度至1024位。实现上限1,048,576位为保护边界，尚无百万位复杂算术性能保证。
- 五组实际生成流程：宽算术、宽四态端口/多驱动/NBA、256位零延迟门级、256位INTERCONNECT+IOPATH、只有中间拼接超过64位。三模式TRACE及native完整VCD/DWF一致；Linux新编译VCS的完整TRACE和选定位通过，SDF注解0errors/0warnings。
- 三组实际生成程序在相同run_until边界进行拒绝预测重放/接受提交，完整ordered/settled DWF与stdout一致；257位含X/Z的通道在1/2/4 workers下与串行逐值逐时刻一致。手工分区和预测API不代表自动分区、自动预测器或收益。
- 实际ASan/UBSan运行：独立23,496项数值探针、并行程序、三个实际生成boundary/replay程序。不是整编译器sanitized声明；原数学/波形原型不变。

真实原始300,909单元网表、1.2GB Liberty不变，直接使用256/257位顶层端口，实际native编译和运行完成；128笔完整输出匹配同一直接接口测试平台新编译的VCS，同时匹配既有分块封装VCS参考。原激励和输出monitor按64位片段映射到宽信号，没有改写原始网表。单次编译191.74s、运行8.68s仅为正确性阶段wall观察，不用于性能验收或计算新VCS比例。

验证中保留两次失败：初始TB名称替换误伤1'b1字面量，已修复生成器并加快速前端检查；首次新VCS命令缺省timescale不一致，保留日志后使用显式-timescale=1ns/1ps。另保留原数学参考假设：简单a*b%p与110笔输出不同，但native/新旧VCS的128笔完全一致。此数据证明仿真器兼容，不证明该输入集满足该数学公式，也不作设计错误结论。

严格全量SDF实际返回非零：`SDF runtime does not implement HOLD (use --no-timingchecks to disable checks explicitly)`。没有使用该关闭选项、删SDF项或输出timed程序成功声明；本批完整真实时序尚未运行。下一里程碑先接通SETUP/HOLD等时序检查，再推进条件路径及完整时序流程，按同一原始输入重新验收。

候选编译源见candidate-source.json/source-snapshot.json，最终采用源码见production-source.json/production-snapshot.json。两平台证据归档描述见macos-evidence.json/linux-evidence.json；linux-verified保留native源码、程序、输入、波形、阶段日志与真实严格诊断。VCS二进制及csrc/daidir依赖仍在原服务器目录，不声称证据归档可独立运行VCS。服务器根目录为/tmp/dsim-wide-values-1018-9q4oob8l。

运行 `python3 validation/m4-wide-values/verify.py` 核对采用源与归档哈希、两平台累计45项、五组新VCS流程及真实128笔结果。语言与功能边界见[多字值说明](../../docs/multiword-values.md)；整体目标仍未完成，本批无新性能比例和压缩率结论。
