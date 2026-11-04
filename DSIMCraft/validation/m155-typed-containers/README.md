# M155：命名类型、枚举与对象容器

本批沿 REPORT-GAP 的真实公开 UVM 首错补命名 integral/enum/class 类型容器。支持 queue/dynamic/int-key associative array、enum 元素身份及 pop 后枚举方法、class 句柄元素/默认空值/共享对象/浅复制、派生向基类整体拷贝、pop 后虚方法及固定 class 数组。构造器和容器变更仍在原生运行时执行，常量解释器排除对象/new，包函数回到真实 runtime。RTL 和门级 parser 保持独立，波形线程和格式未改变。

实现冻结 `c71c736a2d1c504c488529dbfc392cd8a37c9e10`，1927 个源码文件逐字节匹配 Git blob，归档另含清单。Mac/103 Intel 各十一组回归、1562 份捕获及 parser/格式 parser/原生 DB 检查通过。新 typed_containers 组各有九个正例、164 捕获、16 个 native 编译拒绝、1 回滚/1 提交和实际两个分区；全部 28 份生成 C++、stdout 及 164 份解码捕获跨平台一致。另与开发验收的全部 28 份 C++ 相符，不把新组跨平台比较扩大成全部 1562 份都跨平台比过。

九个不改字节的正例在 VCS W-2024.09 输出相符，九模型全部 909 个 native 导出位的 settled 时间线一致，无缺失位，也没有静默取声明交集。动态容器/对象内部状态通过实际 SV TRACE 和导出观察信号验证，不声称 dump 了全部堆。16 个 native 拒绝例中 VCS 拒绝 11 个，接受另外五个：enum queue push 整数、push 不同 enum、pop 赋给另一 enum、enum dynamic array 的整数数组 new[] 初值，以及 queue-of-fixed-array 声明。这五项接收差异仍未修复。最初参考脚本误预期全部拒绝，原始结果如实失败并保留；分类比较读取实际 VCS 编译返回值。

RTL parser 单元、九正例/16 拒绝前端、实际未改的公开 UVM 预处理/失败编译，通过 ASan/UBSan；八份实际生成程序及真实预测 replay（1 回滚/1 提交）也通过。两个实际双分区程序与独立 DWF writer 同时执行通过 TSan。sanitizer 程序 stdout/异步 DWF 和已验收输入相符，前端生成代码与正式 Mac 相符。未启用 LSan，不新增 runtime 性能或压缩率结论。旧 class_objects 的 handle_array 负例由实际固定 class 数组执行覆盖替代，拒绝例改为非法 handle packed select。

Mac 稳定版为 `20261028T225826775208Z-4be7701718d8`，103 Intel 为 `20261028T230413Z-c71c736`。Mac `~/vibe-coding/dsim-test/bin/dsim` 及 103 `/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` 已激活。三个真实入口重新编译并运行 rollback SV，生成 C++、stdout、完整异步 DWF 逐字节匹配验收输入；用户指定 observed/tick 2..3 的波形只包含 5、7。阶段收据保留切换前状态，实际激活另见 activation 收据。

固定 Accellera UVM 2020.3.1（`78c06547a2a0a29b3dc9dcafae62b75b2ff61544`）两端全部 326 文件与公开归档逐 SHA 相符，LICENSE/NOTICE 保留。预处理仍为 1,888,084 字节、166 依赖，SHA256 `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`。native 首错从 uvm_object_globals.svh:714 移至 uvm_misc.svh:71 的 `uvm_config_db#(uvm_object)`，正常退出 1、不产生部分 C++。**原始 UVM 仍不能编译/运行**；参数化/编译单元类、类属性容器、容器形参/返回、string/aggregate 元素、随机求解、IPC、虚拟接口/clocking/覆盖率/DPI 等仍待补齐。M152 动态转换、M153 宏字符串以及旧 SDF time0 参考差异未计为修复。

波形使用自有 DWF1P001。一个专用接收线程独占变化量编码/Zstd/CRC/写盘/索引；仿真线程提交不可变四态快照，队列有界背压，后台异常返回，关闭时排空并 join，错误预测不输出。两端管线组各 72 捕获/36 对同步异步文件身份、范围组各 232 捕获/62 对文件身份通过。用户可选择层次、深度、信号 include/exclude 和时间窗口；命令见[波形接口](../../docs/waveform-format.md)。不声明 FSDB 二进制兼容、百万信号长期规模验收或压缩吞吐收益。

原始证据镜像位于本机 `~/vibe-coding/dsim-test/evidence/m155-typed-containers/archives` 与 103 `/apps/EDAs/own/dsim/evidence/m155-typed-containers/archives`，包括 source/mac/linux/sanitizers/vcs/uvm-reference 六份归档。每端均有 16137 个成员，逐 SHA 通过。全部成员为普通文件；VCS 仅导出自有 SV/capture、文本日志和 VCD，vendor 生成 C/C++/csrc/daidir/程序留在远端。远端首次启动 wrapper 引用旧目录名，在编译前实际退出；源码快照已经校验，随后由正确的冻结入口继续构建，未重新抽取覆盖源码。开发阶段定位的包函数常量求值错误和 VCS 接收差异均保留，不计为通过。`verify-evidence.py <archives目录>` 和 `audit.py` 可复核。完整 REPORT-GAP/UVM 目标继续，下一真实编译阻塞为参数化类类型应用。
