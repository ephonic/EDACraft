# M191：clocking 的采样与驱动

新增独立 owned AST 和 clocking 命名空间，支持命名/default clocking、input #1step/#0、output 常量 skew、@(cb)/@(instance.cb) 与词法默认时钟的正整数常量 ##N。输入可用别名与单维 packed 采样值位选，65/129 位和升序维度保留原范围。输出 RHS 在发出驱动时求值；非时钟时刻的驱动等到下个事件，#0 和未来 skew 使用 Re-NBA。#0 输入在设计 NBA 后、clocking 输出驱动前采样。

等待者使用进程 generation，取消和 fork 槽复用不会误唤醒。输入缓冲、等待和待驱动值随 checkpoint 保存；覆盖预测回滚、提交和 65 个预算切点。含 clocking 的 --threads 2 目前保守退回串行，避免跨分区采样次序失真。

边界：正输入 skew、output #1step、复杂/复合事件、modport clocking、部分输出驱动、动态/零 ##N、net/动态容器/对象输出仍未接入；同一时隙多个时钟边沿明确运行时拒绝。covergroup 和完整公开 UVM 仍未实现完成；本批不作性能结论。最终验收、发布和原版 UVM 首错以 JSON 收据为准。

开发阶段八个 clocking 模型、210 捕获、21 拒绝、1 回滚/1 提交、65 预算切点和重复边沿运行时诊断通过。VCS 九个同源模型（含合法原始报告探针）输出与 dsim 一致，详见 vcs.json。ASan/UBSan parser 重复清理、八模型与一次回放、21 编译拒绝通过，未启用 leak 检查，详见 asan.json。原版公开 UVM 预处理 1,888,084 字节、166 依赖保持一致，原生首错仍为 uvm_report_handler。

Mac 冻结候选已通过三组共 26 模型、278 捕获、58 编译拒绝及 mandatory 检查，1299 输入，生产提交 0fa34e41；稳定 20261031T022217693133Z-7957428ac302 已激活，八模型实际入口的 CPP 和异步波形与候选一致。另修正旧 masked_kernel 中遗漏既有 budget resume 标志的大小断言，当前 Ready 为 12 字节；此冻结后测试设施修正未改变生产运行时，Mac 全目标构建及 native/reference 两内核测试、103 Intel 同内核执行通过，见 build-check.json。

公开 UVM 当前异常来自 veri_class.cpp 的 veri_resolve_type（调用上下文中的类型名查找），不是 clocking 语法；后续应最小化泛型/类成员展开时的词法类型可见性。此处是定位入口，尚未声称根因已修复。
