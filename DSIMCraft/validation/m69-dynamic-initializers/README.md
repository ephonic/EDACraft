# M69：动态数组声明初始化与稳定版发布

实现一维整型动态数组声明中的 `new[n]`、`new[n](array)` 和数组深复制，支持静态启动初始化、显式静态局部一次初始化、自动任务/函数/块逐次初始化、声明顺序、固定源声明顺序复制及宽/四态/两态默认值。声明初始化复用既有过程赋值路径、Sim 容器、激活帧和检查点；初始化函数的存储/副作用进入分区图，独立 worker 实际双分区。RTL parser 对普通 packed 声明逐项登记符号，使后一个初始化式可引用前一个变量；gate parser 保持独立。

功能提交 `ee73b88`。六共享模型覆盖模块/块/静态/自动局部、形参依赖和 const-ref 源、固定/动态源、96 位元素、顺序和函数副作用、挂起/取消/复用及真实双分区。三后端 ordered/settled、VCD/DWF 共 **78 次捕获、6 次实际失败预测恢复、5 类拒绝**。18 项不同定向检查最终通过；16 项受影响回归首轮 15 通过，旧 function_effects 的 `$bits(void function)` 诊断预期过期，M68 同样输出 `unsupported array query operand`，修正测试后完整重测 48.11 秒通过。新增功能 188.04 秒，parser 语义单测 0.64 秒。这些是回归耗时，不是与 VCS 的速度比较。

实际 VCS W-2024.09 六最终同源模型 TRACE 和 **704 条全部导出观察位 settled 时间线**一致，无位排除。其中 160 位固定数组通过五条只读观察线映射，其余直接对应；动态内容经 scalar/TRACE 观察，不代表所有动态位 dump。五诊断中 VCS 拒绝四类、接受四态源到两态目标的初始化，后者为 dsim 的转换欠缺，不能计入对齐。原始输入、编译/运行日志、VCD 与严格比较结果均保留。

ASan/UBSan 七份实际生成程序、七次 sanitized compiler 生成、完整 ordered 流/stdout 和新 parser 语义/克隆/重复清理单测通过，leak 关闭。Linux 对 1106 冻结输入干净构建、六动态内核及 parser 七检查通过，六串行/一实际并行程序 14 捕获、五诊断通过。七完整 CPP、七完整 ordered 流/stdout 跨平台一致；Linux 再核对全部 704 条 VCS 位时间线。首次包遗漏独立 DWF 解码 helper，补齐后重新干净构建的 final 目录才计最终结果。冻结后仅修正一条未在 Linux 执行的旧测试诊断预期；编译器、运行时和共享模型均未变化，差异见 `post-freeze-changes.json`。源包 SHA256 为 `6bb448ed07c21a66fdc0dc2f49cd0e8a55d7b291f4cb65b3e0d23c5ac07f53bf`。

稳定版已发布至 `/Users/yangfan/vibe-coding/dsim-test/bin/dsim`，指向版本目录，编译器使用该目录冻结的八个运行时头文件。发布检查包括静态/自动/宽 RTL、实际双分区和门级 CLI/SDF binding 五项；四份 CPP、完整 ordered DWF 流与 stdout 和已验收构建一致。额外注入构建目录失败，确认旧入口和二进制保持不变。完整版本/输入 hash、二进制 hash 与日志索引见 `release.json`、`release-identity.json`、`publish-failure.json`。此版本的二进制 SHA256 为 `8e0e7ec6a0c21a0aed080dac46537092a90fd7bf25d0d65a386cfb4669dd8ce3`。

```sh
ctest --test-dir build -R '^(rtl_dynamic_initializers|rtl_semantic_memory)$' --output-on-failure
python3 validation/m69-dynamic-initializers/verify.py
python3 scripts/publish_stable.py
```

仍缺更完整元素转换、从未调用子程序的静态初始化、自引用声明绑定、动态 aggregate/enum、多维/数组返回/assignment pattern、固定数组声明初始化及动态元素波形。普通标量静态初始化仍要求常量。此前 VCS 索引求值/扩容/NBA 等差异保留，队列/关联数组/class/约束、完整 SVA/覆盖率/UVM 未因此补齐。本批未新测速、未跑全量 CTest 或 Linux sanitizer。详细边界见 [功能说明](../../docs/dynamic-initializers.md)，稳定入口后续按 [发布流程](../../docs/stable-release.md)更新。
