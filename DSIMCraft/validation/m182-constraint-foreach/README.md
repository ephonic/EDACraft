# M182 约束 foreach 与类内队列

本轮接通独立约束 foreach AST、索引词法作用域、克隆/重复清理、当前状态容器遍历和求解合取；同时补齐 UVM 非重叠区间约束所需的类内对象队列。支持范围及边界见 [功能说明](../../docs/constraint-foreach.md)。

五个实际执行模型覆盖：当前对象队列的非重叠约束、pre/post callbacks、失败原子性及模式/null 检查；固定数组方向/省略索引、动态数组和关联数组；类队列构造、继承、复制/别名、边界、packed 选择与方法；堆状态预测回滚；嵌套字符串/无符号关联索引的同名遮蔽、类特化和 96 位约束。三种请求后端、VCD/DWF/异步 DWF 的 ordered/settled 解码与编码一致性检查另行记录，不把请求两线程等同于实际双分区。

新前端仍为 86 shift/reduce、0 reduce/reduce。公开未修改 UVM 2020.3.1 预处理仍为 1888084 字节、166 依赖，SHA256 a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d。原 smoke 从 uvm_mem_mam.svh:495 的 foreach 推进到展开行 85799 的编译单元级 class 声明；此处尚未完成整库语义分析、展开或运行。

仅用于定位后续工作的诊断变体：把 smoke 的类移入模块，公开库不变，首个语义错误是 `unknown integral type chandle`。这份变体不计为原始 smoke 或真实 UVM 通过，源码 SHA 和诊断保存在 development-notes.json；后续除了编译单元类型，也需要补齐基础类型及完整库展开依赖。

初轮开发记录：区间分配测试缺少末端长度限制，修正正例为 start <= 32-length 后与 VCS 对照；嵌套类型模型只有类句柄、未提供可导出信号，增加 observed 后重新执行波形验证；只遍历 packed 整数的形式明确保留为当前前端边界。早期失败日志归档，不计入最终通过数。

通用全量构建在已有 masked_comb_regions_native_test 的 sizeof(Ready)==8 静态断言处失败（当前为 12）。已用修改前 HEAD 的 runtime.hpp 单独编译复现相同错误；本轮不改该调度布局。所选发布构建目标、受影响回归及 sanitizer 单独记录，不能宣称全量测试通过。

复现：

```sh
python3 tests/constraint_foreach/regression.py BUILD/dsim OUTPUT BUILD/CMakeCache.txt
python3 validation/m182-constraint-foreach/sanitize.py ASAN_BUILD/dsim OUTPUT ASAN_OUTPUT
```

生产实现 `de430e17bcd2feb792b5572ce2afefdf34979aa8` 已推送。冻结发布输入 1236 项，SHA256 为 `284d04eda9214216db7fb731e242e74324076dc6a2bbae01a31062a5606e31a1`。

| 验证 | 结果及证据 |
| --- | --- |
| 新增功能 | 5 模型、92 捕获、15 前端拒绝、回滚/提交各 1 次；[native.json](native.json) |
| ASan/UBSan | 5 模型、15 拒绝、1 个回放；泄漏检查关闭，外部 Z3 未插桩；[sanitizer.json](sanitizer.json) |
| 同源 VCS | 5 个最终源文件的 TRACE 全部通过，记录绑定源码 SHA256；[vcs-final.json](vcs-final.json) |
| 既有随机化 | 12 模型、220 捕获、37 编译拒绝/1 运行时诊断、回滚/提交各 2 次；[randomization.json](randomization.json) |
| 既有容器 | 6 模型、110 捕获、11 拒绝、回滚/提交各 1 次，含实际双分区；[containers.json](containers.json) |
| 既有对象与访问限制 | 11 模型、139 捕获、15 编译拒绝/2 运行时诊断，另 24 个访问反例；[objects.json](objects.json)、[access-negatives.json](access-negatives.json) |
| 公开 UVM | 正常构建、sanitizer 与 Mac 稳定入口得到相同预处理及首错；[public-native.json](public-native.json)、[public-asan.json](public-asan.json)、[public-mac-entry.json](public-mac-entry.json) |
| 原始 REPORT-GAP4 | M182 稳定入口重查 35 个原始文件，22 发射/13 拒绝，源码及接收结果与 M181 相同；这不是 22 个运行通过；[gap4-native.json](gap4-native.json) |

Mac 稳定入口已更新为 `20261030T095026303424Z-284d04eda921`。冻结源码新建发布构建，完整执行约束 foreach、约束随机化、容器三组共 422 份捕获及 mandatory parser/格式/原生 Liberty DB 检查；实际安装入口再编译运行五模型，生成 CPP 和有序 async DWF 与发布验收逐字节一致，另复查所选波形窗口。见 [mac-stage.json](mac-stage.json)、[mac-reference.json](mac-reference.json)、[mac-activation.json](mac-activation.json)。

103 Intel 稳定入口已更新为 `20261030T095014373746Z-284d04eda921`，同样三组 422 捕获与 mandatory 全部通过。77 份 CPP、422 份独立解码波形及本批编码字节跨端全部一致；五个实际入口模型的 CPP/async DWF 和所选窗口复验通过，未修改公开 UVM 的预处理与首错在四种构建/入口完全一致。见 [linux-stage.json](linux-stage.json)、[cross-platform.json](cross-platform.json)、[linux-activation.json](linux-activation.json)、[public-linux-entry.json](public-linux-entry.json) 和 [finalization.json](finalization.json)。发布脚本 [finalize-remote.py](finalize-remote.py) 在完整 stage PASS 及跨端检查后切换入口；实际入口失败恢复旧链接，等待期间如已有更新部署则拒绝覆盖。

原始产物保存于本机 `~/vibe-coding/dsim-test/evidence/m182-constraint-foreach`，不把生成程序、C++ 或波形提交主分支。开发阶段失败、未覆盖范围和已有全量构建错误单列于 [development-notes.json](development-notes.json)。本轮没有重新测量性能。

最终汇总由 `python3 validation/m182-constraint-foreach/collect.py` 核验冻结输入、同源 VCS、sanitizer、双端发布、原始报告和真实 UVM 首错后生成 [progress.json](progress.json)。103 原始 VCS 日志、源码 bundle、发布及实际入口产物保存在 `/apps/EDAs/own/dsim/evidence/m182-constraint-foreach` 和对应 releases 目录。
