# 文档导航

从[项目首页](../README.md)开始使用，构建和回归见[开发指南](../CONTRIBUTING.md)。各专题文档列出支持范围与差异；历史里程碑中的限制以对应较新文档为准。

## RTL 与 SystemVerilog

| 主题 | 文档 |
| --- | --- |
| 前端与兼容入口 | [前端设计](frontend-design.md)、[关键字、端口、genvar 与 top](frontend-compatibility.md)、[实例数组](instance-arrays.md) |
| 类型与位选择 | [命名类型](named-types.md)、[整数类型](integral-types.md)、[packed 聚合](packed-aggregates.md)、[存储与视图](packed-storage.md)、[unpacked 成员状态](unpacked-state.md)、[升序 packed 范围](ascending-packed.md)、[动态部分选择](indexed-selects.md)、[枚举](enums.md) |
| 数组与数据操作 | [多维数组](multidim-arrays.md)、[动态数组](dynamic-arrays.md)、[数组形参](array-arguments.md)、[关联数组值传递](associative-values.md)、[类型别名与数组返回值](array-aliases.md)、[赋值模式](assignment-patterns.md)、[流式拼接](streaming-concatenation.md)、[数组归约](array-reductions.md)、[定位与去重](array-locators.md)、[foreach 接收者](foreach-receivers.md)、[下标接收者与子数组](foreach-selections.md) |
| 文件级类型 | [编译单元 class / typedef](compilation-types.md)、[文件级 import](compilation-imports.md) |
| 类属性 | [类权限](class-access.md)、[属性 ref](object-scalar-references.md)、[static](class-static.md)、[const 属性](const-properties.md) |
| 层次与组织 | [package](packages.md)、[interface/modport](interfaces.md)、[virtual interface](virtual-interfaces.md)、[虚接口子程序](virtual-interface-calls.md)、[generate](generate.md)、[层次引用修复](report-v3.md) |
| 子程序与生命周期 | [子程序](subroutines.md)、[automatic](automatic-subroutines.md)、[ref](ref-arguments.md)、[const ref](const-ref.md)、[字符串](strings.md)、[字符串转换](string-casts.md)、[无括号函数体](nonansi-bodies.md) |
| 过程与敏感性 | [编译式进程](compiled-processes.md)、[always 过程](always-procedures.md)、[组合部分写入](comb-partial-writes.md)、[组合位敏感性](comb-bit-sensitivity.md) |

## 调度、验证与运行时

| 主题 | 文档 |
| --- | --- |
| 时间与事件 | [时间语义](time-semantics.md)、[表达式事件](event-expressions.md)、[命名事件](named-events.md)、[条件事件](conditional-events.md)、[连续赋值延迟](continuous-delays.md) |
| 并发与取消 | [mailbox / semaphore](ipc.md)、[fork/join](fork-join.md)、[join_any/join_none](fork-control.md)、[命名块 disable](named-disable.md)、[automatic fork](automatic-fork.md) |
| 随机验证 | [约束随机化](constraint-randomization.md)、[约束 foreach / 类内队列](constraint-foreach.md) |
| 断言 | [并发 property 与采样函数](concurrent-assertions.md)、[固定周期序列](sequence-delays.md)、[验证功能范围](systemverilog-verification.md) |
| 并行与回滚 | [分区与预测回滚](parallel-and-rollback.md)、[automatic 并行](automatic-parallel.md)、[时间队列](time-queue.md) |
| 文件与波形 | [系统函数](system-functions.md)、[dump 任务](wave-dump-tasks.md)、[波形格式说明](waveform-format.md) |

## 门级与时序

| 主题 | 文档 |
| --- | --- |
| Parser 与来源 | [组件划分和构建](../parsers/README.md)、[原始来源归档](parser-origin/README.md) |
| 门级基础 | [标量门](scalar-gates.md)、[四态查表](gate-four-state-lut.md)、[门级批处理](gate-batches.md) |
| SDF | [解析](sdf-parser.md)、[绑定](sdf-binding.md)、[运行时](sdf-runtime.md)、[互连](sdf-interconnect.md)、[条件路径](conditional-paths.md) |
| 时序模型 | [时序检查](timing-checks.md)、[模型](timing-models.md)、[SDF 模型准备](sdf-model-preparation.md) |

## 质量、发布与历史

- [功能状态与 VCS 差距](vcs-feature-status.md)、[性能测量边界](performance-gap.md)。
- [统一编译与 VCS 差分流程](tool-flow.md)、[稳定版发布](stable-release.md)。
- 用户报告修复：[RTL](rtl-report-fixes.md)、[complex](complex-report-fixes.md)、[REPORT2](report2-review.md)。
- [验证归档及原始产物恢复](../validation/README.md)、[最新 M90 验收](../validation/m90-ascending-packed/README.md)。
- [原始计划](../plan1017.md)、[截至 M90 的旧首页](history/README-m90.md)。

其余专题 Markdown 继续保留在本目录，可用 `rg --files docs` 查找。

- [运行参数和动态格式化](testbench-io.md)：plusargs、sformatf/sformat 与支持边界。

- [通用文本文件 I/O](file-io.md)：FD/MCD、EOF/定位、格式化读写及预测事务边界。

- [Modport prototype imports](modport-prototypes.md): task/function signatures, per-view defaults and interface call validation.

- [Clocking 采样与驱动](clocking.md)：采样 skew、输出调度、默认时钟和周期等待。
