M152 根据 REPORT-GAP 继续补齐 UVM 基础：virtual class、pure virtual function/task 和动态 `$cast`。实现及边界见 [专题文档](../../docs/abstract-casts.md)。完整 UVM 仍不能编译运行，本批不作性能或压缩率结论。

六个正例保留原始源文件与 VCS 捕获，四个模型输出完全一致；targets 与 conversions 的五条不同输出分别保存在 `known-reference-differences.json`，不把它们计作完整对齐。包括目标选择副作用、枚举数组元素检查及 129 位枚举值。无实现 super 纯虚调用也单列参考差异。新增 regression 同时检查原值保留、X/Z、向下/向上转换、动态接收者、ref、宽值、包、模块克隆、虚任务、回滚和异步所选波形。

VCS 构建目录保留在 103；仅归档自有 SV/C++、文本日志与波形，不导出 vendor 生成 C/C++ 或可执行程序。发布与 sanitizer 的最终结果追加在本目录，失败的探索过程不计为通过。旧 SDF time0 monitor 差异继续保留，不将完整 waveform_dump 检查计为通过。


最终实现冻结为 `2c9748969f8574b6021b199610bd519a2041722a`。Mac 稳定版 `20261028T204216450329Z-1eab6ff855c6` 与 103 Intel 稳定版 `20261028T204341Z-2c97489` 已激活；Mac 一个、103 两个实际入口均重新编译并核验完整/范围选择的异步压缩波形。两端各七组共 879 捕获及完整 RTL parser、格式 parser、原生 DB 必要检查通过。新 class_casts 组各 110 捕获、11 编译拒绝、5 运行时拒绝、1 回滚/1 提交；该组 19 份生成 C++ 逐字节、110 份解码捕获跨平台一致。并非全部七组生成代码均做了跨平台逐字节比较。

VCS 同源六模型中四个输出完全一致，两个模型共五条 TRACE 差异保留。波形四模型完整一致；合计比较 1088 位，960 位一致、128 位存在差异，另 16 位数组元素在参考捕获中缺失，未计通过。9 个编译拒绝及 5 个运行时错误与 VCS 一致；2 个无实现 super 纯虚调用由 dsim 拒绝、VCS 接收。对应源文件哈希、完整 delta 和捕获限制均保存在 JSON 中，不能将六模型概括为完全对齐。

完整 parser、六个正例/十一个反例的前端、六份最终生成程序、五个运行时错误程序及窄/宽堆内核通过 ASan/UBSan；旧真实双分区程序和新虚任务/回滚程序配合异步接收线程通过 TSan。macOS 关闭 LeakSanitizer，未宣称泄漏检测或性能提升。首次 Linux 打包缺 cmake 文件由配置检查拦截，补全归档后重新 staging，失败候选未激活。最终源码归档 1893 个成员与冻结 Git 内容一致。

真实 UVM 验收仍为 **INCOMPLETE**。103 安装的 UVM 1.2 与 IEEE 2020-2.0 最小 component smoke 均在 VCS 通过；dsim 首先遇到加密分发中的 `protected 宏。为分离分发格式与语言缺口，另固定 [Accellera 官方 2020.3.1](https://github.com/accellera-official/uvm-core/tree/78c06547a2a0a29b3dc9dcafae62b75b2ff61544)，提交 `78c06547a2a0a29b3dc9dcafae62b75b2ff61544`，保留 LICENSE/NOTICE，不修改库源。该公开源码同源最小 smoke（UVM_NO_DPI）在 VCS 编译/运行通过、UVM_FATAL 为 0；dsim 在 `uvm_tlm_defines.svh:303` 报 `line continuation outside a macro definition`，尚未进入完整类语义检查。下一步先修复该真实预处理阻塞，再沿实际编译诊断补齐参数化/编译单元类、qualifier/static/extern、对象容器、约束随机、IPC、虚拟接口等依赖，最终验收完整 component/sequence/driver/scoreboard 流程。本轮抽象类完成不代表 UVM 已可运行。

原始证据归档包括 source、mac、linux、sanitizers、vcs 与公开 uvm-reference 六份；本机 `~/vibe-coding/dsim-test/evidence/m152-abstract-casts/archives` 和 103 `/apps/EDAs/own/dsim/evidence/m152-abstract-casts/archives` 镜像，`evidence-index.json` 与逐成员 SHA256 可独立复核。VCS 归档包含自有 smoke SV 和测试文本日志，未包含 vendor 生成代码或程序。先运行 `verify-evidence.py <archives目录>`，再运行 `audit.py` 核对本批范围。旧 SDF 初始化 monitor 差异仍未计作通过。
