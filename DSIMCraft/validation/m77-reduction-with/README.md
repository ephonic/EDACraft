# M77：数组归约 with 表达式

补入 `sum/product/and/or/xor` 的无副作用 `with` 映射，默认 item、命名迭代变量、词法遮蔽/嵌套、映射表达式自定结果位宽/符号、标量/数组外部读依赖，以及固定/动态数组、automatic 和固定/open 值参数、动态 const-ref 参数。沿用现有四态运算、数组存储、依赖、调度及快照；不新增运行时状态，RTL/gate parser 继续分离。

- [VCS 记录](vcs/results.json)：10.131.254.103，`source /apps/EDAs/syn.bash`，W-2024.09_Full64。六组源逐字节/SHA256 核验，保留编译/运行日志与 VCD；共享 TRACE 期望来自实际 VCS。[逐位比较](vcs-bit-results.json) 检查全部3,159条公开物理位（23根只读数组 observer，零排除），固定数组字用只读 observer 暴露。动态堆元素通过归约输出和 TRACE 检查，不计作直接导出并逐位核验的数组字。
- [原生检查](native-results.json)：六共享模型及一个独立原生作用域模型，串行/时间轮/双线程、ordered/settled、VCD/DWF，共87次完整流比较、3次失败预测回滚、实际双分区；15类错误输入拒绝；另检查 Verilog 模式的 with 标识符。
- [sanitizer](sanitizer-results.json)：七模型经 ASan/UBSan 编译器生成并实际编译/运行 instrumented C++，完整 C++、stdout、ordered 波形与原生一致。[最终编译器检查](final-compiler-sanitized.json) 核对七个完整 C++ 身份及全部拒绝分支。[parser 检查](parser-sanitized.log) 包括 repeated parse、参数/generate 克隆、嵌套作用域与清理；关闭泄漏检测。
- [既有回归](regressions.log)：无 with 数组归约、streaming、assignment patterns、open/动态数组形参、enum、packed aggregate、旧前端、gate CLI 和 parser 内存。旧无 with 拒绝测试改为非数组 receiver，保留其明确拒绝用途。

实测类型/作用域：8位数组 ff+2+3，普通sum为04，`with(int'(item))` 为260；布尔映射的sum为1位，会溢出。命名迭代参数不是普通实参，也不读取/修改外部同名变量。不同名嵌套可读取外层迭代值，同名嵌套就近遮蔽。单元素原样四态映射保留Z，空动态数组按映射结果位宽返回0。`[15:8]` 元素的 packed 选择保留原下标，另检查 packed bit 迭代值的越界选择。[独立查询](iterator-query-results.json) 核对原下标/越界片选；标量/一位 packed 向量的 dimensions 另作原生检查，保留 [VCS 对查询组合的拒绝日志](probes/iterator-dimensions-vcs.log)，不计作 VCS 对齐。

边界见[功能说明](../../docs/reduction-with.md)：用户函数调用及带副作用映射明确拒绝；迭代变量只读，不逃出作用域；仍缺动态子数组前缀、packed 多维迭代选择、enum/aggregate 元素、定位/排序、queue/关联容器及完整验证语言。[VCS 默认迭代变量选择的作用域差异](probes/shadowed-select/README.md) 与 M76 的动态归约隐式敏感性差异保留，共享时序使用明确 scalar refresh 依赖；未把原始差异计为对齐通过。没有新增性能结论，未运行全量 CTest/Linux 原生构建。

M77 实现提交 `f073ebe`；后续 M78 用户报告修复一并发布。M78 最终 sanitizer 编译器再次核对本批七模型完整 C++ 与15类拒绝；未把本批功能推广为完整验证语言。

复现：`python3 tests/reduction_with/regression.py build/dsim build/rtl-reduction-with`，然后运行本目录 `verify.py`、`run-sanitizers.py` 和 `verify-compiler-sanitized.py`。

稳定发布与 M78 合并：`2bafbcab4657f8b2f3df925110afc15479beadb3`，入口 releases/20261024T040222070894Z-bdce241a045f/dsim，[56项发布检查](release.json)通过。[53模型身份](stable-identity.json)包括本批6模型对原生和47旧模型对 M76 稳定版，完整生成 C++、stdout、同模式完整波形流一致。未修改运行时头文件；M78 对报告用例另作39个程序身份核验。
