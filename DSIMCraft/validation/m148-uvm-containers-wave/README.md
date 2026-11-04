M148 对用户的 `~/vibe-coding/dsim-test/rtl-tests/complex/REPORT-GAP.md` 做依赖复核，补齐 integral queue、int-key associative array，并落实用户追加的独立线程压缩波形要求。功能范围与边界见 [容器](../../docs/uvm-containers.md)及[波形管线](../../docs/waveform-format.md)。完整 class/约束随机/UVM 尚不能运行；报告中的性能和全面替代结论不能作为本批产品保证。

实现冻结以 source-proof.json 为准；源码包每个成员同时匹配 Git blob 和 SHA 清单。RTL 与门级 parser 保持分离。

验收包含原始 q05 和五个泛化容器模型：队列两端插入/删除、有界溢出、追加/复制、参数表达式宽度和单次副作用、signed int 键排序/游标/复制、foreach/reduction、宽四态值、重叠 automatic 调用、实例参数克隆、真实双分区和事务恢复。动态存储不作为可变 VCD 声明导出；标量 TRACE/原生内核检查负责观测容器内容。

独立波形线程接收不可变事件批次，自己编码、压缩、校验和写盘。RTL、SDF、真实并行和 dump 控制按 ordered/settled、1/17/16384事件块验证同步/异步逐字节身份；带 commit/rollback、非法配置、线程所有权、缓冲背压、异常/析构排空、既有文件保护、索引窗口与截断恢复。保持开放 DWF1 格式，未宣称 FSDB 二进制兼容或压缩/吞吐优势。

发布前额外运行既有动态数组、动态数组形参及 reduction-with 组，加上完整 RTL parser、格式 parser 和原生 DB 检查。首个候选被旧 negative 用例拦截：错误文本从 “one unpacked dimension” 变为 “single unpacked dimension”。恢复旧文本后重新打包和双端验证，未激活失败候选；原始错误保存在 initial-diagnostic-regression.log。

VCS 原始六模型的 TRACE 和全部544个导出声明位 settled 时间线一致，无声明位遗漏；原始 q05 不含可导出标量，另外五模型负责波形对照。四个最终生成程序 ASan/UBSan 和独立 writer ASan/UBSan/TSan 检查见 sanitizers.json，完整 parser 日志另列。macOS 关闭 LeakSanitizer，不能表述为泄漏检查通过。普通预测回滚并不保证撤回已经提交到文件的历史；后台队列只接收已提交变化。

两端五组回归每端共410份捕获通过，原始 parser/格式/原生 DB 检查通过；新容器组95捕获、23编译拒绝、1运行时拒绝，波形组72捕获、36对同步/异步文件逐字节一致。跨平台23份生成 C++、23份stdout及全部95份容器捕获一致。最终两端回归、发布入口结果见 final-audit.json 和对应 JSON，可执行 `python3 validation/m148-uvm-containers-wave/audit.py` 复核收据。源码冻结为 `750516dc98c1b127eea1eee4ece838e2f088156e`，验收文档后续单独提交。

Mac 稳定入口 `~/vibe-coding/dsim-test/bin/dsim` 对应 `20261028T161204273678Z-b0f4c8a6a2eb`；103 的 `/apps/EDAs/own/dsim/bin/dsim` 和 `/apps/EDAs/own/dsim/dsim` 对应 `20261028T161234Z-750516d`（Intel）。三个实际入口分别重新编译 queues.sv 并开启独立线程运行，生成 C++、stdout及DWF字节与验收版本一致。切换及原入口记录见 mac/linux-stable-entry.json；切换失败会恢复原链接。

生产代码与 runtime 冻结后才构建候选，不在运行中的发布流程中修改检查脚本。首次 VCS 辅助打包误包含 AppleDouble `._*.sv`，这些文件被 VCS 拒绝；清理后只对六份真实源文件作同源比较。关联数组未知键写探针暴露 VCS 的 DT-IV，候选已改为运行时报错并加入回归。未以这些失败试验作为正向通过证据。

四份原始归档（冻结源码、Mac/Intel自有模型及日志/捕获、VCS源输入及文本/VCD）按 evidence-index.json 和逐成员SHA清单镜像至本地 `../dsim-test/evidence/m148-uvm-containers-wave/archives` 及103的 `/apps/EDAs/own/dsim/evidence/m148-uvm-containers-wave/archives`。不包含VCS生成代码或二进制。用 verify-evidence.py 指向任一archives目录复核，mirror-local/remote.json留存实测结果。
