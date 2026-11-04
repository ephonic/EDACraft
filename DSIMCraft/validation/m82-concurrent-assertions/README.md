# M82 单时钟 property/SVA 验收

目标是原 RTL 报告 B3 与实际并发断言语义。报告 hash 和逐字节原始 t04 来源见 origin.json；实现范围和剩余缺口见 [docs/concurrent-assertions.md](../../docs/concurrent-assertions.md)。RTL 和门级 parser 保持独立，DWF 不修改，用户 experiments/matvec16 不纳入提交。没有新的性能对标结论。

## 同源 VCS 和原生运行

11 份共享源包括原报告、前向命名 property 和两个参数化实例、重叠/非重叠蕴含、真实失败、X/Z 条件、Active 阻塞修改和 NBA 采样、异步取消、同沿 NBA 撤销复位、同槽时钟脉冲合并、动作可见值、Reactive/Re-NBA 顺序与实际双分区。VCS W-2024.09_Full64 在授权主机实际运行；输入字节、编译命令、原始日志和 VCD 位于 vcs，run-vcs.py 是该主机使用的执行脚本。未复制远端技术指南。

verify.py 核对全部源 hash、输出和所有原生公开物理位的完整 settled 时间线：11 源输出一致，964 位通过，无排除位。VCS 之间的同时间槽中间 delta 顺序不作为等价声明。原始 t04 本身有时间推进，参与完整波形比较。

native-frozen 包含 11 模型、三后端、41 份完整 ordered VCD 和 8 次实际失败预测后的回滚。parallel 模型实际两个分区，one/two 最终结果都为 1；回滚比较全部 stdout 和完整 ordered 信号流。22 类负例及 Verilog 模式下 property/endproperty 普通名称通过；随后增加的 join_none 动作拒绝由 probes/action_fork.sv 和 fork-guard.json 单独原生/ASan 核验，现行永久回归及稳定发布检查包含全部 23 类。最终编译器重新生成 33 份后端 C++，逐字节等于已执行的原生验收程序，见 final-codegen.json。这一补充的拒绝检查不改变有效模型的生成代码。

## 所有权与调度

使用已有 AST 条件/时序节点所有权，新增字符串/延迟元数据在模块复制时一并克隆；完整 parser 重复解析、实例克隆、清理检查见 parser 日志。运行时独立保存采样、待观察时钟、尝试、Reactive/Re-NBA、动作结果，均随 Sim checkpoint 复制。复位表达式有依赖索引，采样只保留实际被读的信号。未使用 property 的生成模型不启用新增字段。

## 开发中发现并修正的差异

初始实现错误地执行空成功 pass 动作、忽略时间零声明初始化的采样起点，并对同一轮调度的多个边沿分别求值。VCS 探针确认后分别修正；最终 shared-source 输出及完整位时间线均通过。Reactive 模型验证动作 NBA 在设计观察过程运行前提交。新 grammar 恢复到原有 57 个 shift/reduce 冲突，无新增 reduce/reduce。

保留初始测试脚本沿用旧字符串测试的结果 49、过时 function/memory 拒绝假设，以及编辑中的 compiler/runtime 参数不同步导致中间编译失败记录。这些不是验收结果；以 native-frozen、最终 C++ 身份核验、独立 fork guard 及稳定发布为准。

## Sanitizer、既有回归与发布

20 个实际程序 ASan/UBSan 通过：11 个模型、8 个失败预测回滚及一个实际双分区程序。全部核对 C++/stdout/完整 ordered VCD；22 类基础拒绝及 fork 补充拒绝通过，leak 检测关闭，选项和程序 hash 见 sanitizer-artifacts.json。原生及 ASan 的完整 parser 重复克隆/清理通过。受影响 8 项 CTest（automatic subroutines、selection checks、named events、expression/conditional/function events、event NBA、checkpoint）最终全部通过；checkpoint 在最终运行时头文件构建后另行复测通过。稳定发布结果在完成后追加。未宣称完整 SVA、完整 IEEE 调度区、全量 CTest 或 Linux 本地构建。


M82 稳定发布完成：实现 `9da62cc`，61 项发布检查全部通过，入口更新到 `20261024T113956172915Z-79455fe7426b`。source SHA256 `79455fe7426b4bf59fff270452572f82dd4cf975e932a96d963d8cb203a7937b`，binary SHA256 `b39949cb30f1c0f3b3c2c8f1e5497e6f434f4c76ce5398d1ef28cf4899b2ff22`。53 个先前根模型、31 个随机、27 个 package 和31个 string 程序完整输出/ordered 波形保持一致，4个 v2 程序输出一致；41个新增 property 程序完整 C++/输出/ordered VCD 与原生验收一致，全部输入和运行时快照 hash 复核。20个实际 ASan/UBSan 程序和8项受影响 CTest 通过。完整证据见 validation/m82-concurrent-assertions；完整 SVA 仍缺，不新增性能结论。
