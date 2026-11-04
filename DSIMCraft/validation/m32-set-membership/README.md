# M32 集合匹配与 VCS 对齐

接通整数/packed 的 `inside`、`==?` / `!=?` 和 `case (selector) inside`，包括运行时标量集合、动态闭区间、现有单维 unpacked 变量数组、四态和多字值，以及 parameter/localparam/generate 常量展开。RTL parser 独立扩展，紧凑门级 parser 不改；直接生成 C++，不新增运行时 AST 解释器。

右侧 X/Z/? 为通配，左侧未知值不被自动通配；已知不匹配优先于其余未知位。集合全部成员共同决定比较宽度和符号；case inside 的上下文包含全部分支。选择表达式只取样一次，按分支顺序取第一个真匹配，X 不命中；数组字、动态边界和函数读取纳入敏感集合与分区依赖。支持函数内分支、立即断言、delay/NBA 单次取样和检查点回放。实现范围及限制见 [功能说明](../../docs/set-membership.md)。

六个共同输入位于 tests/set_membership：

| 模型 | 主要验证 |
|---|---|
| wildcard | 256 组两位四态组合，独立逐位参考检查三种运算 |
| membership | 动态/反向区间、数组成员及数组字变化触发、混合符号、130 位通配 |
| elaboration | 参数、未定宽填充值、优先级、generate 条件与展开 |
| control | 选择函数单次取样、重叠分支、默认、未知标签、函数内 case inside |
| effects | 函数副作用、敏感依赖、阻塞/NBA 延迟取样 |
| parallel | 两个真实独立分区，逐时刻独立数学预期 |

串行/时间轮/双线程 × ordered/settled × VCD/DWF 共 72 次捕获，加 control/effects 两次失败预测回放，共 74 次。回放从 1ns 开始，完整 ordered 波形和 TRACE 与普通执行相同。20 类负例检查空集合、错误分隔符/范围、开放 $、非整数集合、复杂数组、casez inside、普通 case 范围、unique、延时函数/任务及未定义符号；拒绝不能崩溃。

实际 VCS W-2024.09 在 10.131.254.103 执行，先 source /apps/EDAs/syn.bash，使用 -full64 -sverilog -debug_access+all。六组输入逐字相同，TRACE 和全部 968 条 VCS 导出物理位时间线一致，无名称映射。VCS 未导出 membership 的 set_values[2:4]，即使单独请求 dump 这些字；这 96 位不计入 VCS 一致位数，另检查完整逐时刻预期（3、9→14、12）及全部本地后端/格式一致。verify.py 明确限定这三个字，其他缺失信号均为失败。输入、dump wrapper、命令、编译/运行状态及原始 VCD 保存在 vcs/。

probes/ 保留先执行的 VCS 四态/符号/单次取样探针与反向范围未知值探针及原始日志。范围使用 >= 和 <= 四态结果求与，已知反向范围无匹配，但未知选择值仍可能为 X；不把它强制折叠为 0。集合成员的求值顺序在语言中未指定，当前实现从左到右，不承诺工具间具有副作用的成员顺序一致。

最终验收数量和状态见 results.json。本地十项定向 CTest 包含新功能、automatic/实参/类型/过程/always、parser、编译总回归及门级回归；macOS ASan/UBSan 包含 parser 单测、六组输入各三轮清理及六个实际生成程序（包括真实双线程，关闭 leak 检测）。Linux 用冻结源包干净构建并执行六项定向 CTest，核对 728 个源文件和七份完整实际 C++ 身份，再以 Linux 实际波形比较同源 VCS。source-manifest.json/source-archive.json、final-identity.json/platform-identity.json 保存身份校验结果。前两批 M31/M30 共同输入用当前编译器重跑，分别核验 1272/2993 条既有 VCS 位时间线。

Bison 保持 47 个 shift/reduce、0 个 reduce/reduce，与 M31 相同。runtime.hpp 新增按机器字比较的通配相等和范围 helper，parallel.hpp 不改；未做新的性能测量。没有运行全量 CTest 或 Linux sanitizers。

仍缺非整数集合、开放范围、复杂/动态数组、unique/priority case、模式匹配和约束随机化；此前 ref/递归/常量函数、package/interface/class、完整 SVA/UVM 和完整时序/事件区域等也未齐，不宣称完整 SystemVerilog 或全部 VCS 功能。

复验：

```sh
ctest --test-dir build -R '^rtl_set_membership$' --output-on-failure
python3 validation/m32-set-membership/verify.py
```
