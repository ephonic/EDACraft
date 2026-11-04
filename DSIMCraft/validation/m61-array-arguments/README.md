# M61：固定 unpacked 数组形参

补齐 task/function 的固定大小数组 input/output/inout/ref：多维与动态前缀子数组、声明顺序映射、默认/命名/经典调用、入口取样与返回复制、实时引用、事件、取消/复用、分区及检查点回滚。RTL AST 形参保留维度，绑定/克隆/清理同步；命名类型形参 grammar 复用固定维度声明，Bison 47 冲突未增。门级 parser 保持独立，运行时和调度器无需修改。

引用沿用 M60 的不可变激活帧；值形参使用现有扁平数组存储，生成 C++ 在入口和出口批量转移元素，不在运行时遍历 AST。动态前缀每次传输仅计算一次，input/inout 入口复制、output/inout 返回重算实际地址；ref 入口固定每个实际元素的存储。数组形参的 `$bits`/维度查询、foreach、整体赋值、enum/packed 成员身份接通。修复声明 `[N]` 曾被解释为 `[N:0]` 的错误，现在为 `[0:N-1]`；同时避免未知声明范围错误路径解引用 end iterator。

## 测试与 VCS 对齐

- 七组模型：copy/functions/elements/events/control/types/parallel。三种执行后端、两种波形模式和两种格式，共 90 次捕获；6 次真实预测失败后的回滚重放，包括分配前恢复和已挂起的数组参数；24 次正常/取消调用存储有界，实际两个分区。
- 11 类编译拒绝、2 类非法 ref 动态前缀运行诊断；另加二维形参/整体数组赋值/foreach/`$bits`/`[N]` 的独立探针。
- 真实远端 VCS W-2024.09：七份完全相同 SV，TRACE/自检和 1554 条完整物理位 settled 时间线一致，无排除位。32 条只读 wrapper 观察线补齐 VCS 默认 dump 省略的 1074 位数组元素；所有映射逐条列于 `observers.json` 和 `vcs-results.json`。
- `probes/semantics.sv` 验证复制时点，`ref-bounds.sv` 确认不同界限/方向可引用等价形状数组；额外 multidim-probe 与 VCS 的 `TRACE multidim 39 39 31 31 140` 一致。额外探针为 TRACE 检查，不计作新增完整波形模型。
- 首轮 native 类型用例暴露命名类型数组声明和 formal 元素聚合识别两个缺口，已修复；初始失败日志保留，未算通过。

## 回归和可复现核验

本地 16 项不同定向 CTest 通过：受影响 14 项 255.52 秒全部通过，包含数组复制/动态子数组/模块端口/net 数组/多维/查询/foreach、默认调用、automatic 子程序、ref、事件函数及三个 ref 内核；parser 语义单测通过；新 `rtl_array_arguments` 91.82 秒通过。未跑全量 CTest。

macOS ASan/UBSan：七个最终实际程序（parallel 实际两分区）、完整 ordered 流、每份语料三轮 parser 清理和完整 parser 语义单测通过，leak 检测关闭。运行时代码未变，此批没有新增直接内核；既有三个 ref 内核纳入定向回归。

冻结 1280 文件，源包 SHA256 `efa7c60ec68db6dda9fe66e0ad64776fe445ab60344c93953dfca01fdf07612c`。Linux 干净构建、四项 parser/既有 ref 内核检查、七串行及一个实际双分区程序 16 捕获；结果及八份完整 C++/七 ordered 流和 stdout 跨平台比对见 `linux/`，最终状态见 `results.json`。未跑 Linux sanitizer。

`source-manifest.json` 固定输入哈希；`source-changes.json` 列出相对 M60 的变化；`final-identity.json` 绑定八份完整生成 C++，其中七份与实际 sanitizer 输入一致。`verify.py` 可重做严格 VCS 位检查；未保存商业工具二进制或 csrc。

## 剩余边界

尚缺开放数组 `[]`、动态数组/队列/关联数组、const ref、递归、数组返回、数组字面量/assignment pattern，以及值形参的任意元素转换和完整类型等价规则。元素类型须等价，固定维度要求非负 bounds。未知/越界 ref 前缀显式终止，这项诊断策略不称作与 VCS 相同。M60 的 join_any/join_none 直接访问外层 ref 限制及 M47/M55 已知差异继续保留。

本轮功能优先，没有新增性能测量，不宣称全部功能/性能与 VCS 对齐。
