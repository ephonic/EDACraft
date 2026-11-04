# M147：编译单元 package import

实现冻结：`a5557f39ff7dd06c224c000e25de549dee7acf53`。源码包 SHA256 为 `55af9ecafbf93e6d85105822e6adef6eb467a9a818d3ecebe2e044a894bafdc9`，1829 个成员逐字节匹配该 Git 提交及归档清单。RTL 与门级 parser 保持分离。本轮功能优先，没有 runtime 性能测量。

新增文件级显式/通配/列表 import，支持后续 module/interface 的参数、ANSI/non-ANSI 端口类型、正文和子程序。文件级作用域独立于实例层次，包原声明及可变存储保持共享；本地声明可以遮蔽外层显式或通配导入。后置 import 不追溯影响前面的模块，package 不捕获 $unit。模块展开顺序与源码顺序不同的通配绑定通过暂存引用及结束校验处理；暂存引用不能充当真实绑定。详见 [范围](../../docs/compilation-imports.md)。

两端均完成以下五组及 RTL parser、格式 parser、原生 DB mandatory 检查：

| 回归 | 波形捕获 | 拒绝例 |
| --- | ---: | ---: |
| compilation_imports | 25 | 18 |
| header_imports | 26 | 15 |
| package_exports | 16 | 17 |
| packages | 27 | 13 |
| unit_lifetimes | 20 | 17 |
| 合计 | 114 | 80 |

新组覆盖五个模型、串行/时间轮/双线程、5 次预测提交/5 次回滚、2 次 checkpoint 恢复和真实双分区，以及多源文件顺序和显式导入的本地遮蔽。25 组 C++/stdout/完整有序波形跨平台一致。VCS W-2024.09 对五个相同源文件的输出及全部 480 个声明位 settled 时间线与两端一致；没有未比较位，没有以共同子集掩盖声明遗漏。

16 个 VCS 拒绝输入、1 个接收输入与 dsim 相同，全部错误日志检查了实际 VCS 诊断码，排除许可证/编译器基础设施失败。反序多文件是额外 dsim 拒绝例，未列入 VCS 对照数。保留三个实测差异：

- 前面的未实例化模块引用通配导入名称，可能在 VCS 中建立文件级绑定；dsim 只收集实际展开的设计单元，后续冲突通配使用仍可能被拒绝。
- 同样的未实例化引用与后续显式导入冲突，VCS 拒绝而 dsim 当前可能接受。
- VCS 接收文件级 `export p::name`；dsim 本轮只支持文件级 import，继续拒绝 export。

首轮诊断脚本错误地预期 VCS 拒绝文件级 export，被真实结果拦截。保留首轮输出，修正对照分类后完成验收；没有修改输入或将该差异计为通过。完整 parser 和 6 份实际生成程序通过 ASan/UBSan，包含包共享存储、延迟调用、回滚、checkpoint、词法绑定及分区。macOS 首次 `detect_leaks=1` 在执行测试前被 sanitizer 拒绝，保留记录，改为 `detect_leaks=0` 完成；没有声称通过 LeakSanitizer。六个旧 RTL 模型生成 C++ 与八个 runtime 头均与 M146 逐字节相同。

发布入口已激活，均从真实入口重新编译、执行并核对 C++/stdout/完整有序波形：

- Mac：`~/vibe-coding/dsim-test/bin/dsim` → `20261028T150605715734Z-f17e2f18b3d4/dsim`，SHA256 `a69e7c132de01cb842177133b2a681d9a6e3bcfba968eddb076b4e16266eb88e`。
- 103 Intel：`/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` → `20261028T150610Z-a5557f3/bin/dsim`，SHA256 `5368acf3336541a07224349afbd4d1878a9884387f9d66e24840626e57bf4255`。

发布构建仍只执行一次；新增 `--check-jobs` 将独立回归写入各自目录并行执行，默认保持串行。本轮每端最多三组并行，未在运行中改动调度进程，也未混用变化中的源码。

原始源码、生成程序、波形、日志和 sanitizer 证据已按每个成员的长度/SHA256 归档，镜像位置为 `~/vibe-coding/dsim-test/evidence/m147-compilation-imports/` 和 103 `/apps/EDAs/own/dsim/evidence/m147-compilation-imports/`。VCS 生成代码及厂商二进制始终留在远端临时目录，没有导出。归档索引见 [evidence-index.json](evidence-index.json)，最终审计见 [audit.json](audit.json)。
