# M159：string 键与类关联数组

实现冻结 `6976c483a715cfd79f87053cd3eafab233714ff6`，1820 个源码成员与 Git 绑定。按 REPORT-GAP2 和真实 UVM 依赖补齐 string 键关联数组，以及类属性中的 int/string 键关联数组：独立对象存储、元素/packed 更新、方法、整体复制、foreach 隐式 string 索引和空键、automatic 调用隔离、依赖通知及 checkpoint/预测恢复。复制到两态元素时逐元素清除 X/Z，class-handle 复制保留别名。另修正隐式 typed packed 函数参数分隔、packed 类型类参数列表、索引元素 enum 方法、非零八进制转义及 getc 的有符号 byte 结果。RTL/门级 parser 继续独立。

Mac 和 103 Intel 各七组、904 捕获以及 mandatory RTL parser/格式 parser/原生 DB 检查通过。新组九模型、28 份 C++、146 完整捕获、13 native 拒绝边界、1 回滚/1 提交、2 checkpoint 和真实双分区通过；copy 模型只有动态容器/句柄，无可导出标量，只比较输出，不计波形。全声明有序 VCD/DWF/单线程异步 DWF 跨后端一致，同模式 sync/async DWF 逐字节一致，另验收用户指定范围。28 份 C++ 和146捕获跨平台完全一致。

九份相同源 SV 输出与新鲜 VCS 一致，含空键、高位字节排序、129 位四态、游标失败不修改索引、句柄共享和混合状态转换。lifetime/rollback/parallel 三个有时间推进模型的全部256个 native 可见声明位时间线对齐，未取交集忽略缺失位；其它六模型只计 TRACE 对照。动态数组内容、string 和堆内部字段不直接作为 VCD 声明导出，不声称完整堆波形。13个 native 拒绝边界包含合法但暂不支持的 SV，不能当作与 VCS 拒绝性全部一致。

完整 parser、新前端九正/十三拒绝、七份新普通生成程序、预测回放、额外旧 enum 容器程序及宽堆内核通过 ASan/UBSan；实际双分区与独立异步 writer 通过 TSan。LeakSanitizer 关闭，不宣称泄漏检查。公开 UVM 的预处理/正常失败编译路径也通过 ASan/UBSan。本批没有性能测量，也没有运行全量 all-target 构建；既有 masked_kernel Ready 尺寸断言限制保留。

首轮正式候选被一维整数/动态数组误走多维路径的回归拦截；第二轮被 packed 类实参分隔解析和旧诊断文本回归拦截。两个候选在 Mac/103 均未激活，正式修订后全部七组重跑通过。开发中无导出信号、未截断129位 oracle、测试打印合并分区、辅助脚本路径和过早读取未生成参考 CPP 的失败单列在 failures.json；不计作产品验收通过。VCS 实测还发现混合状态复制需要逐元素转换，本轮已修复。

三个入口均重新编译/运行，完整与所选范围异步 DWF 核验通过：Mac `~/vibe-coding/dsim-test/bin/dsim` → `20261029T022210778038Z-426b462cea0a`；103 `/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` → `20261029T022213Z-6976c48`。Mac 974 项发布输入与冻结 Git 绑定，103 在构建前后核对完整源码清单。五个源码/自有结果/sanitizer/VCS文本归档共9789成员双端逐哈希校验；VCS生成 C/C++、csrc、daidir 或二进制不导出。

未修改的 Accellera UVM 2020.3.1 在两端实际稳定入口预处理仍为1888084字节/166依赖，SHA保持；native 语法首错从 uvm_misc.svh:96 string 键推进到 :322 static function。**完整 UVM 仍不能原生编译运行**，不能用首错推进替代执行验收。原始报告 r02 也仍被队列 `q={1,2,3}` 初始化阻塞，本轮未改写该原始用例。下一步继续 static 类成员、约束随机、IPC、virtual interface/clocking、coverage/DPI 和队列等依赖。其它边界见 [功能说明](../../docs/string-associative.md)。本批 audit 仅表示此增量已验收，完整目标仍继续。
