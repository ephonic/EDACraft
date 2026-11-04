# 已采用：编译式时序检查与联合回放

默认SDF入口新增SETUP/HOLD/SETUPHOLD、RECOVERY/REMOVAL/RECREM、WIDTH/PERIOD/SKEW，覆盖specify初值、事件/边沿/条件身份、按模型精度换算的SDF覆盖、实际接收输入、逐解析变化、窗口历史与事务诊断。RTL/gate parser继续独立，格式原型和108个vendor parser文件未变。语言与检查边界见[使用说明](../../docs/timing-checks.md)。

- macOS/Linux最终各49/49完整通过（199.34秒及Linux日志所列时长，均为并行正确性作业，不作性能测量）。初始失败及后续修正日志保留，最终验收仅使用采用核心；没有新增性能实验或VCS效率比例。
- 21组新VCS编译参考，文件字节逐份匹配后合并：九类检查、普通条件/X条件、WIDTH threshold、独立数据上升/下降边沿、负值默认模式、零时间差、四态事件、显式01事件、组合检查拆分覆盖，以及3ps INTERCONNECT+2ps IOPATH+HOLD。两平台全部原生违例类型/时刻匹配完整VCS警告流，不能只用可能合并的notifier monitor计数代替诊断。
- 20组VCS注解0错误/0警告；负limit一组VCS报告SDFCOM_NNTC、统计1错误/0警告并以0运行，native显式提示夹零、IR计数为1，违例流一致。此组是默认非负模式对照，不是负检查延迟参考/数据模式成功，也不称所有21组注解零错误。
- 每组native无波形/VCD/DWF诊断及TRACE一致，完整native波形解码一致；此处没有把生成VCS波形等同逐位VCS波形差分完成。VCS诊断oracle和输入身份见vcs-reference目录、macos-vcs-checks.json、linux-vcs-checks.json。
- 四组实际生成程序（setuphold、width、独立边沿、联合IC/IOPATH/check）在相同run_until边界拒绝预测/回放、接受提交，完整ordered/settled DWF及stdout一致。紧凑/普通信号内核另直接测试每次变化、X/Z、历史恢复与拒绝诊断事务；严格失败检查未匹配边沿、缺少组合半项、notifier及NOCHANGE，不覆盖既有CPP/IR。
- ASan/UBSan实际运行两个生成replay程序（setuphold与联合IC/IOPATH/check）及紧凑/普通信号内核；生成程序的完整诊断、ordered/settled波形与未sanitized版本一致。不是整编译器sanitized声明。

差分过程中修正了检查条件X/Z应禁用、紧凑存储的X/Z逻辑码转换、未限定时序事件忽略X↔Z、单独setup/hold与组合检查的零时间差边界、组合检查实际阶段诊断、检查边沿精确匹配等问题。先前“未限定模型事件可接受更窄SDF边沿”的候选已撤销：VCS原输入明确报两条无法匹配警告；旧输入与错误日志保留，新合法模型的正/负数据边沿各有声明，严格负例保留原不匹配形式。Verilog `edge [0z]`被该VCS拒绝的测试平台保留，验收的显式事件为`edge [01]`，不称这两个模型输入相同。

真实严格检查使用原始300,909单元网表、1.2GB Liberty、111模型和flattened SDF，输入前后校验SHA，未关闭timing checks、删除条目或改写网表。当前首个诊断：SDF第1662320行HOLD在DFQD1BWP6T16P96CPD中没有精确匹配的模型检查；SDF数据事件为posedge D，既有占位模型为未限定D。原始vcs1017报告也说明模型由gen_libmodels.py生成占位检查。该问题属于模型身份缺口，不能放宽匹配或把VCS未注解的约束当成已运行；真实完整timed程序尚未生成/运行。早期宽松候选越过HOLD而停在SETUP的诊断属于候选历史，不作为当前结果。

下一整体里程碑将处理标准单元模型/条件路径和完整时序；自动正延迟分区、自动预测器与大规模波形索引继续保留在总体计划中。SDF检查事件通道是已实现的共同基础，不代表上述自动化功能已完成。原始报告的设计为近似Barrett，仿真golden采用RTL/VCS向量，不能用精确a*b%p替代。

采用源为production-source.json/production-snapshot.json，两平台证据为macos-evidence.json/linux-evidence.json；服务器原目录/tmp/dsim-timing-checks-1018-fhfeZBBM。归档保留native程序/源码/输入/波形/日志，VCS可执行与csrc/daidir依赖仍在服务器，不声称精简归档可独立运行VCS。运行`python3 validation/m4-timing-checks/verify.py`核对源码、证据与最终结果。整体VCS目标保持进行中。
