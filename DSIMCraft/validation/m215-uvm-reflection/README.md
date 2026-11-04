# M215：UVM 类型查询与字符串控制/流操作

2026-11-02。继续以原版 Accellera UVM 2020.3.1 为验收入口，功能优先；
本轮不进行 runtime 优化，也不以单方编译耗时判断与 VCS 的快慢。

实现范围：

- `$typename` 支持已绑定类型参数、基本数据类型、变量、类型别名、具名枚举/
  struct/union、类及参数化类、固定/动态数组/队列/关联数组的已支持类型元数据，
  以及函数返回类型和数组/packed 选择。不执行查询操作数中的函数或索引副作用。
  保留包/模块/编译单元限定名和原始 packed 维度；在 Verilog 模式下拒绝该 SV 查询。
- 字符串条件表达式允许有副作用的函数和对象方法。已知选择只执行选中分支；
  X 选择按 VCS 验证的顺序执行两分支，同值保留，不同值返回空字符串。
- `{>>{string_queue}}` 按元素顺序拼接动态长度字符串；支持类的字符串队列属性，
  以及队列、字符串函数调用和字符串字面量组成的流列表。保留纯 packed 字面量
  的原有流语义。接通 UVM `m_uvm_string_queue_join(ref string i[$])`。

未修改公开库使用固定提交 `78c06547a2a0a29b3dc9dcafae62b75b2ff61544`。
预处理仍为 166 个依赖、1,888,084 字节、SHA256
`a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`。
`--shared-functions --emit-only` 已越过原 `$typename(T)`、字符串条件分支和
字符串队列流操作阻塞，下一首错为：

```
class method elaboration failed: do_execute_op
uvm_ref/src/reg/sequences/uvm_reg_mem_hdl_paths_seq.svh:67:2123
expression requires an integral value, not an unpacked array or declaration
```

这是 `uvm_field_queue_string` 宏展开路径的后续问题，尚未修复。
进一步已提取整字符串队列 `===/!==` 最小复现（`probes/queue-case-equality.sv`）；
103 VCS 输出同内容相等、不同长度不等，dsim 在该比较处拒绝，见 `next-gap.json`。
**原版完整 UVM 尚未生成原生程序，更未通过 run_test/phase/objection 验收。**
`UVM_NO_DPI` 不表示库中所有 DPI 声明/导出均已删除。

`tests/type_reflection/` 五组独立同源用例对照 103 VCS W-2024.09，涵盖类型名称、
数据容器、packed 选择、惰性字符串条件表达式、字符串队列流拼接。
默认内联、共享函数、共享函数+timewheel 三模式验证完整 TRACE 和完整有序波形，
另验证 9 项拒绝及输出保护。实际结果见本目录 JSON。
`sanitize-generated.py` 的 ASan/UBSan 范围是生成的程序，编译器前端未在该脚本内消毒。

字符串动态/固定数组存储、左向字符串流、混合 integral/string 的动态流、
未声明类型的参数查询及一般算术表达式类型推导仍有边界，会继续补齐。
命名之外的匿名聚合类型、复杂类型参数文本尚未覆盖完整标准；不能据此声称
完整 `$typename` 或完整 UVM 支持。

受影响回归包含 strings、streaming、system_functions 和 M214 的 uvm_call_values。
首次 streaming 回归在 Verilog 模式拒绝用例中失败：该用例先使用 SV `logic`，
解析在抵达流表达式前已失败；M214 稳定版同样复现。将该负例的变量声明改成
Verilog `reg`，使其实际验证“流表达式需要 SystemVerilog”这一约束，再复验。

发布使用冻结 Git 源树、完整输入哈希、独立 runtime 头文件和原子入口切换。
生产源码提交 `c10bf30324373f5b67c8da24a2c32caa665c8033` 已推送 GitHub。
双端稳定入口已激活并通过入口实际编译/原生运行：

- Mac：`~/vibe-coding/dsim-test/bin/dsim`，release
  `20261102T000834290698Z-644e6e801374`。
- 103：`/apps/EDAs/own/dsim/bin/dsim` 与 `/apps/EDAs/own/dsim/dsim`，release
  `20261102T000921491780Z-644e6e801374`。

两端 1,529 项冻结输入逐项 SHA256 相同，汇总 SHA256
`644e6e80137413406b8bb68b637e91dee6355eeaf65b3efc176722174383a5b4`。
五组本轮用例和七组既有调用用例均通过三模式原生执行：本轮 15 份捕获、
既有 22 份捕获（含预测失败回放）。跨端 38 份完整 C++、37 份完整解码波形
事件流一致，见 `cross-platform.json`。VCS 对照五组同源输入的全部 TRACE 和
源文件哈希一致，见 `vcs.json`。

五组 ASan/UBSan 已通过的生成程序与冻结生产编译器的输出逐字一致，见
`frozen-asan-identity.json`。前端未在该脚本内消毒。发布 mandatory parser /
format / native DB 及 preprocess、gate_source 组均通过；完整收据保留在各
release 目录，仓库记录收据 SHA、输入哈希和实际入口结果。

双端稳定入口的原版公开 UVM 复验仍在上述队列比较处拒绝；该结果是明确的
功能缺口记录，不能计为原版 UVM 编译/仿真通过。
候选 `*-candidate.json` 的 `PASS_PENDING_ACTIVATION` 保留为历史阶段状态，
实际激活以 `*-release.json` 与 `*-entry.json` 为准。
原始日志、模型和波形的本地持久存档及 Linux 归档位置见 `*-evidence.json`。
没有重跑 C910 或新增 VCS 性能比较；M214 的 C910 最小 RV64 TEST PASS 仍是历史基线。
后续编译性能比较须使用同一设计、输入、编译选项目标、机器条件与完整计时范围。
