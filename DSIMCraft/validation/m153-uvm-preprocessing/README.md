M153 针对真实公开 UVM 补通宏预处理，并修复后续 RTL 语法错误恢复崩溃。范围与剩余缺口见 [专题](../../docs/uvm-preprocessing.md)。完整 REPORT-GAP/UVM 目标继续，本批不作速度或压缩率主张。

使用与 M152 相同的未修改 Accellera 提交与自有 component smoke；通过 `public-uvm.py <dsim> <公开库目录> <输出目录> [--vcs]` 区分预处理、参考执行及 native 编译。不得将 VCS 执行 dsim 展开源码计为 dsim native UVM 通过。

实现冻结 `c45dc968df22e46e41ccbbe5b79cf96747e04eb7`，1893 个归档源码成员与 Git 一致。Mac `20261028T212328789466Z-c981cb415f40`、103 Intel `20261028T212345Z-c45dc96` 已激活；Mac 一个与 103 两个真实入口都重新编译/运行，完整及用户所选范围的异步 DWF 与候选参考一致。各端六组回归、18 个预处理模型/30 个拒绝、源映射及覆盖保护检查通过；四组波形相关回归各端共 573 份捕获，另包含门级实际 CLI 与 mandatory RTL parser/格式 parser/原生 DB 检查。

跨平台逐字节比较全部 18 个预处理 fixture 的展开文本、这些 fixture 与 class_casts 的全部 42 份生成 C++；class_casts 全部 110 份解码捕获一致。这里不声称所有 573 捕获都重新做了跨平台比较。class_casts 的 24 份生成 C++ 与 M152 原样一致，全部 runtime header 未改；没有新 runtime 测速。完整 parser、18 正例/30 反例前端及真实公开 UVM 预处理/失败编译通过 ASan/UBSan，未启用 LSan，未重新运行 TSan 或声称新增生成程序 sanitizer 通过。

公开 UVM 输入来自固定提交 `78c06547a2a0a29b3dc9dcafae62b75b2ff61544`；Mac/103 实际源树的 326 文件逐项核验与公开归档相符，保留 LICENSE/NOTICE。两端都完整生成 1,888,084 字节、166 依赖的相同预处理输出（SHA256 `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`）。将最终展开 SV 交给 VCS W-2024.09，真实最小 component smoke 通过、UVM_ERROR/UVM_FATAL 均为 0。native 编译原始源码仍正常返回 1，在 `base/uvm_base.svh:42` 的 `typedef class uvm_cmdline_processor;` 拒绝，未执行 UVM。

四组新增 LF 宏 fixture 与 VCS 输出一致。CRLF 注释续行参考输入在 VCS 报语法错误，native 保持既有行尾归一化后可运行，单列 `vcs-preprocess.json`。另有普通替换字符串中的嵌套宏差异：`probes/string-probe.sv` 六行输出仅第三行不同，native 为字面宏文本，VCS 为 `blockword`，见 `string-reference-difference.json`。不得将整个预处理语言表述为全面对齐。错误恢复崩溃在开发验证中由真实公开包及 UBSan 复现后修复，失败诊断归档，不计通过；未发布该失败候选。

六份归档 source/mac/linux/sanitizers/vcs/uvm-reference 镜像位于本机 `~/vibe-coding/dsim-test/evidence/m153-uvm-preprocessing/archives` 和 103 `/apps/EDAs/own/dsim/evidence/m153-uvm-preprocessing/archives`；索引和逐成员哈希均验证通过，共 7765 个成员。保护测试留下的文本别名以普通文件快照归档，避免恢复时创建链接；首版导出被成员检查拦截，修正 exporter 后重新归档。VCS 归档仅包含自有输入、公开 UVM 展开 SV 与文本日志，不导出 vendor 生成代码或程序。运行 `verify-evidence.py <archives目录>` 与 `audit.py` 可独立核验。

完整目标仍 **INCOMPLETE**。下一步依实际 UVM 编译推进类前向声明、参数化/编译单元 class、访问/存储限定符、对象容器与随机/IPC 等依赖，最终必须验证 native component/sequence/driver/scoreboard。波形独立接收线程与范围选择已持续纳入发布检查；M149 旧 SDF time0 monitor 差异、M152 动态转换参考差异仍保留，未计为已修复。
