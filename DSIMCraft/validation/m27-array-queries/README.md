# M27：静态数组查询与多控制位计数

实现 `$dimensions/$unpacked_dimensions/$left/$right/$low/$high/$increment/$size/$countbits`，范围见 [功能说明](../../docs/array-queries.md)。RTL/SV 与门级 parser 保持分离。静态查询在展开时折叠，动态维度只计算选择实参，保留完整宽度与 X/Z；查询对象/索引/函数实参不执行。countbits 的实参与动态控制位单次求值、LSB 转换及去重已接入 C++，宽值按64位字匹配与 popcount，不新增状态或事件布局。

## 本地验收

- 四个共同模型：constants、effects、vectors、parallel。serial/time-wheel/双线程，ordered/settled，VCD/DWF 共48捕获；effects 的一次实际失败预测回放另捕获1份，合计49。
- 256种四位四态值逐项检查 0/1/X/Z、组合/重复及动态控制位；130位值覆盖跨字及末字掩码。
- 参数实例/generate 重绑定、成员/数组字、负返回/符号扩展、无效/未知/超宽维度、未执行索引/函数实参、控制/值地址副作用、delay/NBA、立即断言；独立检查真实两个分区及两域输出时间线。
- 两个额外原生模型验证 countbits 参数常量/generate、标量对象、函数返回查询及控制位后置表达式。它们不计入共同 VCS 模型。
- 32类拒绝输入检查非崩溃退出及诊断。新功能/parser 两项最终 CTest 通过43.23秒，十项已有类型/子程序/编译/门级定向 CTest 通过175.92秒。
- parser 单测、六组输入各三轮清理以及六个实际生成程序通过 macOS ASan/UBSan；含真实双线程，关闭 leak 检测。波形或原生 TRACE 与正常运行一致。
- Bison 仍46个 shift/reduce 冲突，无 reduce/reduce；7份完整实际运行 CPP 经最终编译器重新发射，字节相同。

原始记录见 `local-final-ctest.log`、`local-existing-ctest.log`、`sanitizers.log`、`sanitizer-runtimes.json`、`final-identity.json`。首轮及中间日志保留，正式结果以最终输入/完整 CPP 身份检查为准。

## 实际 VCS 对照与边界

10.131.254.103 上 source `/apps/EDAs/syn.bash`，实际 VCS W-2024.09，四例使用同一份 SV 输入与 `-full64 -sverilog -debug_access+all -top top -top dump`。检查编译、完成 TRACE 及无 Fatal，不能仅凭退出0判定成功。

四例 TRACE 与 **1588条物理位时间线**逐项相同：constants 188、vectors 261、effects 683、parallel 456。无普通设计信号、函数局部量或供应商临时量排除，无名称映射。明确枚举 **27个 VCS 未导出的数组字**（constants 16，effects 5，parallel 6）；它们的内容不包含在1588位比较中，共同源另检查维度/宽度及地址副作用，不能据此声称这些数组的全部内容已被波形对照覆盖。`verify.py` 强制校验实际VCS输入字节、信号身份集合和逐位时间线。

`semantics.sv` 的8行额外 TRACE 与实际 VCS 相同，记录于 `semantic-probe.json`。另保留下列限制/差异，不计入共同通过数：

- VCS 拒绝 `localparam C=$countbits(...)` 和 generate 的 countbits 常量；也拒绝对64位越界维度的参数求值。dsim 的 `native_constants.sv`、parser 单测和独立边界模型通过。初始/第二轮完整输入、诊断保留。
- VCS 拒绝部分标量对象、标量选择/表达式以及函数返回表达式的数组查询；dsim 的原生边界模型分别验收，原始 `semantics-initial.sv` 和 `effects-vcs-third.sv`/诊断保留。
- `control-effects.sv` 的后置控制位表达式存在实际输出差异：`countbits(source++,ctl++)` dsim 为30、VCS为2；`countbits(value,ctl++,1'b1)` dsim为2、VCS为1。双方 source/ctl 更新一致，VCS输出相当于使用递增后的控制位；没有据此推断供应商内部根因。该探针没有错误的自检预期，四行完整输出和两行差异保留于 `control-effects-results.json`。随后修改控制变量的共同源中间尝试也失败，原输入和日志保留；最终共同用例保留动态控制位覆盖，副作用差异由独立原生模型单独验收。

`run-vcs.py`、`vcs/`、`vcs-results.json`、`verify.log` 保存可重查证据。最初负范围 unpacked 数组源同时超出 dsim 既有布局范围，不声称支持该声明。

## 同源 Linux 与限制

最终662文件源清单和归档见 `source-manifest.json`、`source-archive.json`，SHA256 `7d252bf70a699f022fcb70607fb386101cb089b1346e7b7e723f24b29ea593f6`。最终 Linux 目录 `/tmp/dsim-m27-final-linux-2tlu6xgt` 干净构建、新功能/parser/编译总回归三项 CTest 通过86.91秒、退出0。最终源清单及归档哈希在远端再次验证；七份完整实际运行 CPP 与 macOS 字节一致，Linux 实跑 TRACE/1588位时间线也再次匹配同一组 VCS。记录见 `linux/`、`platform-identity.json`、`linux-vcs-results.json` 和 `linux-collect.log`。初版归档后只修正文档状态摘要，生产源码与测试输入不变，初版清单/启动记录保留。

未跑完整 CTest 集、Linux sanitizer或新的速度测量；没有把内联 popcount 当作已测性能收益。复杂表达式/cast 的完整维度和边界类型传播未验收；完整多维/端口/整体/动态数组、字符串/typename、package/interface、类型参数/端口、automatic/递归、并发 SVA、class/randomization/UVM、完整时序/事件区和自动预测仍未齐。
