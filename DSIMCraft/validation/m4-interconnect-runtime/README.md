# 已采用：编译式接收端 INTERCONNECT 与统一运行流程

常用逐接收输入延迟已进入默认编译器：结构驱动计数、接收有效ABS/INC状态、模型精度量化、私有接收pin、独立取消/交付以及已有IOPATH串联。RTL/gate parser继续分开；runtime、波形、并行header和旧原型未改。

- macOS/Linux完整各41项通过（330.08/286.43秒）；同一候选编译源归档SHA见source-snapshot.json。
- 29组已冻结VCS参考：顶层输出及全部私有输入稳定态位匹配；native VCD/DWF完整流一致。native TB仅将不支持的XMR monitor换为输出monitor，原始结构/lib/模型/SDF/刺激保留，不称原始TB完全相同。
- 4组实际生成程序：相同run_until边界、拒绝预测回滚及接受提交的完整ordered/settled DWF和stdout一致。
- 两份实际输入/输出互连boundary/replay程序ASan/UBSan通过，全部波形与对应非sanitized程序一致；不是整编译器sanitized声明。
- 11份既有不含IC的完整SDF生成C++与冻结Linux基线逐字相同。生产源与41项候选的编译源差异仅main.cpp帮助字符串，已核对精确替换；随后两平台重建并运行统一流程。
- scripts/run_flow.py最终版三种模式在两平台通过；Linux为新VCS编译对照，TRACE及选定位波形一致：RTL18位、门级4位、SDF5位。最终SDF例含非零5ps IOPATH接在INTERCONNECT后；首次注解0errors/0warnings。所有native完整VCD/DWF流一致。
- 失败流程另验证具体诊断、继续下一例与最终非零退出。每阶段wall/CPU/RSS、文件大小是单次观察，不能推断一般性能或压缩率。

真实原始300,909单元网表分别尝试零延迟接口与flattened SDF入口，两者均明确停在256位mul_a触发的顶层1..64位限制，未进入SDF执行。没有重写原始网表、删SDF项、关闭检查或宣称全量SDF通过。下一整体里程碑为多字RTL/门级宽接口，然后推进真实条件路径与检查、自动分区/自动预测。现有预测API不等于自动预测器，本批没有新的VCS性能比。

INTERCONNECT边界详见docs/sdf-runtime.md：普通叶输入与已覆盖数值组合；scope/inout目标、条件/沿/label/RETAIN/显式pulse threshold、稀疏两值、多驱动已有非零后显式ABS零仍明确拒绝。其余未覆盖标准细节不作全面兼容声明。

证据归档描述为macos-evidence.json/linux-evidence.json，生产源为production-source.json及production-snapshot.json。原候选和旧证据保持不变。Linux原目录/tmp/dsim-interconnect-runtime-linux-1018-tYxdP6；此处linux-verified保留完整native生成程序、输入、波形及日志，VCS流程的csrc/ELF依赖仍在原目录，不声称这个精简证据归档能独立运行VCS。

运行python3 validation/m4-interconnect-runtime/verify.py可核对生产源、两平台归档/文件清单与最终流程结论。
