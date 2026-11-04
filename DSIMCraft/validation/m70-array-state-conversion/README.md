# M70: 数组值传递与状态转换

补齐等位宽 packed 整型动态数组复制/声明初始化、固定及动态数组 input/output/inout 值参数的两态/四态转换。X/Z 复制到两态元素时清零，回写按目标存储转换，保留深复制、声明顺序和自动激活帧。ref/const-ref 继续严格类型等价；普通复制与值参数还校验 signedness、atomic base kind、enum/aggregate 身份和形状。复用原有 Sim 容器和调度器，RTL/gate parser 分离，无 grammar 改动。

五共享模型和一原生构造模型共 78 捕获：串行/时间轮/并行三后端，VCD/DWF 两种格式及 ordered/settled 两种模式；六次真实失败预测回放、八类编译拒绝和真实双分区通过。Sanitized compiler 七次生成与验收 CPP 逐字节一致；七份生成程序 ASan/UBSan 的完整 ordered 流/stdout 通过，leak 关闭。

真实 VCS W-2024.09 五份同源模型的全部 480 条导出物理位 settled 时间线和 TRACE 一致，无位排除；其中 64 位固定数组通过八条只读层次观察线映射，其余 416 位直接对应。动态元素通过 scalar/TRACE 观察，并非完整动态容器 dump。

跨状态 new[n](source) 不算同源对齐：原生逐元素转换，而当前 VCS 对 8/32/96 位构造读出不同值；12 个独立复制/构造探针、7 个形参探针各重复运行三次，保留原始结果，不推断通用分配或布局规则。完整构造模型原始配置也重复三次保留；ELEMENTWISE_REFERENCE 显式分配及逐元素标量复制配置在两端 TRACE 与预期一致。八条 dsim 拒绝中 VCS 拒绝七条，接受变位宽构造；该功能仍未补齐。

入口脚本 run-vcs.py/verify.py 重放共享源及严格位比较；run-constructor-reference.py 区分构造器和参考配置；run-sanitizers.py 校验真实生成器与完整 ordered 流。probes 目录保留输入、命令和实际日志。完整 SV/VCS 功能、性能对齐及动态元素波形声明均未宣称完成。

本地七项定向 CTest 全部通过：新功能 62.90 秒，六项旧回归 441.55 秒。Linux 最终 1108 冻结输入干净构建、六动态数组/NBA 内核及 parser 语义单测七项通过；六串行和一实际双分区程序共 14 捕获、八诊断通过。七完整 CPP、完整 ordered 流/stdout 跨平台一致，Linux 再核对全部 480 条 VCS 观察位。最终源包 SHA256 为 `33610290684ae8a4744bbdd6683fb1c5a2df8f489f0b111274a3dc044aeef8f5`。初包后统一修正测试空白和文档、补充参考 runner，最终重新冻结并干净构建的 final2 才计最终结果；编译器/运行时/模型未在验收后更改。所有冻结输入 hash 再次通过。

仍缺变位宽和更一般的类型转换、动态 aggregate/member 与 scalar ref、多维容器、数组返回/assignment pattern、动态元素波形，以及此前队列/关联数组/class/约束/完整 SVA/覆盖率/UVM 等缺口。原有 VCS 调度/索引/扩容差异保留；本轮未新测速、未跑全量 CTest 或 Linux sanitizer。

功能提交 `f7578b0e04ae820edf24037743f225f0cf0d4987`。稳定入口 `~/vibe-coding/dsim-test/bin/dsim` 已更新，发布目录 `20261023T051808428537Z-29dc08bc1881`；八份 RTL 程序和门级 CLI/SDF 检查通过，八完整 CPP、ordered 流/stdout 与验收构建一致。二进制 SHA256 `3d1605d51015595a3bc9e7488c24e13baa8680e133c8bb3002efcb4e0540b5c5`，输入 SHA256 `29dc08bc1881f2db507fc75f9a4eca1fc778e6825bee2118576b434fb06e2188`。发布元数据的 dirty 状态来自当时未提交的验收证据及已有无关未跟踪实验；编译器及发布输入已在功能提交中，输入 hash 均核实。旧发布保留，后续通过验收的批次继续运行 publisher 更新同一入口。

```sh
ctest --test-dir build -R '^rtl_(array_state_conversion|dynamic_arrays|dynamic_arguments|dynamic_initializers|array_arguments|open_arrays|ref_arguments)$' --output-on-failure
python3 validation/m70-array-state-conversion/verify.py
python3 validation/m70-array-state-conversion/verify-cross-platform.py
python3 scripts/publish_stable.py
python3 validation/m70-array-state-conversion/verify-release.py
```
