# M33 foreach 与 VCS 对齐

补齐现有静态单维 unpacked 数组和 packed/整数位维度的 foreach，支持多个索引、跳过维度、声明方向、隐式自动作用域和只读索引。按静态形状生成固定 PC 与现有检查点计数器，不逐元素展开 AST。RTL parser 与紧凑门级 parser 保持分开。详细范围见 [foreach](../../docs/foreach.md)。

多索引仍是一个循环边界：continue 进入下一组索引，break 退出整个 foreach。索引每轮由剩余计数和各维步长计算，避免末端 32 位自增溢出；隐式索引不导出静态波形，但进入依赖与检查点。编译存储按进程隔离自动索引，保留同一静态任务词法作用域及循环体静态变量的共享；不能把整个循环体一起私有化。当前无 fork/递归，未实现一般动态栈。

六组共同输入位于 tests/foreach：

| 模型 | 主要验证 |
|---|---|
| traversal | 升序存储器、降序 packed、外部同名变量、INT_MAX 附近合法索引 |
| multi | unpacked/packed 双索引、跳过/尾部省略维度、整个 foreach 的 break、continue 与嵌套 |
| overlap | 同一静态任务两进程重叠挂起，私有索引产生112233，共享静态局部产生123456 |
| functions | automatic 局部数组、命名 packed 形参、continue/break/return、always_comb 依赖 |
| elaboration | 参数化实例形状、generate 克隆、延时迭代和组合输出 |
| parallel | 两个真实独立分区，索引/位写入及累加值的独立逐时刻数学预期 |

串行/时间轮/双线程 × ordered/settled × VCD/DWF 共72次捕获，加 overlap/elaboration 从1ns开始的两次失败预测回放，共74次。两组检查点均处于延时遍历过程中；恢复后完整 ordered 波形与打印一致。25类负例检查只读索引的阻塞/NBA/递增/选择/拼接/复合赋值/输出写回、索引重名、过多/全空索引、作用域、非法目标、复杂数组和函数时间控制；拒绝不能崩溃。全空索引、packed聚合等未支持范围的拒绝不等同于宣称VCS也拒绝全部这些结构。

实际 VCS W-2024.09 在10.131.254.103执行，先 source /apps/EDAs/syn.bash；使用 -full64 -sverilog -debug_access+all 与独立dump wrapper。六组输入逐字相同，TRACE及全部924条VCS导出物理位时间线一致。仅共享静态局部 calls 使用一项明确的作用域对应：VCS top.walk.unnamed$$_0.body.calls → native top.walk.$unm_blk_1.body.calls，全部32位仍比较；generate 的点分名称仅按相同完整层次路径解析。VCS未导出的11个存储器字共29位另按完整独立时间线核验，不计入VCS一致位数；其他缺失声明或任何位变化均为失败。原始输入、命令、状态、日志和VCD在 vcs/，校验见 verify.py。

probes/ 保留方向/跳维/多索引退出/整数位维度/遮蔽的实际VCS与native探针、空索引语法错误、VCS const索引拒绝，以及静态局部共享探针。初始 functions 输入使用普通 for(integer k=...)，native额外导出其32位隐式索引而VCS不导出；原始输入和双方VCD在 probes/inline-for-dump/。这是既有普通for波形导出边界，未计为本批修复。最终共同输入将该控制变量显式声明在模块作用域后重新运行双方，所有导出位比较。初期 overlap 的同Active区立即读取、functions 的 always_comb 变量重复初始化检查已更正；VCS亦拒绝该重复驱动，不通过关闭检查运行。

本地九项既有定向CTest通过；最终索引存储修正后，新功能、automatic子程序、parser和编译总回归四项重新通过，共十项不同测试。macOS ASan/UBSan通过最终parser单测、六组输入各三轮清理和六个实际生成程序（含真实双线程，关闭leak检测）。最终状态见 results.json。

Linux使用最终745文件源包干净构建并运行六项定向CTest，核对七份实际完整C++跨平台字节身份，并以Linux实际波形再次校验924条VCS位时间线及29位数组独立预期。初次验证源包的脚本路径指向旧用例目录，已在启动构建后停止该作业；最终冻结包已更正，superseded-linux-launch.log仅记被取代的作业，不冒充最终验收。源/归档/生成物身份见 source-manifest.json、source-archive.json、final-identity.json 和 platform-identity.json。

以前M32、M31共同输入分别保持968/1272条既有VCS位时间线一致，M32另有96位数组独立预期；当前编译器重新生成的七份M32完整程序与该批冻结程序字节一致。runtime.hpp与parallel.hpp保持M32版本，Bison维持47个shift/reduce、0个reduce/reduce。未运行全量CTest、Linux sanitizers或新的性能测量，不声称完整SV或整体速度已对齐VCS。

仍缺动态/关联/队列、多维/复杂数组、数组形参及端口、packed聚合/成员/层次foreach目标、标签循环、一般动态重入；此前ref/递归/常量函数、package/interface/class、完整SVA/UVM及完整时序/事件区域也未齐。

复验：

```sh
ctest --test-dir build -R '^rtl_foreach$' --output-on-failure
python3 validation/m33-foreach/verify.py
```
