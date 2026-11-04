# 真实设计性能基线与直接回调候选评估

本批**未采用**模型专用直接回调，工程保持已验收的 0.13.0。候选正确性通过，但未获得稳定收益，已恢复与前批冻结包逐文件相同的全部 153 个实现/测试/脚本文件、108 个 parser 文件和 3 个波形原型依赖。[决策记录](decision.json) 固定恢复后的源码 SHA；[候选源码](candidate-gate_compiler.cpp) 与所有原始证据保留。候选原理见 [模型专用回调](../../docs/model-specific-handlers.md)。

本批主要进展是接通报告中的真实 30 万单元设计，完成原版/候选/VCS 的 128 组完整黄金向量核对，并建立同输入的真实仿真成本。当前实际差距约 **2.24 倍 CPU**，后续优化以此负载及其 profile 为主要依据。

## 串行交替测量

GCC 11.5、原生 `-std=c++17 -O2`、VCS W-2024.09 默认优化，同一 `10.131.254.103` 主机；自己的计时任务串行。各预热一次后轮换三次，共享主机没有独占 CPU 或锁频。每行属于自身同轮实验，不混用不同轮次 VCS 数值。

| 负载 | 0.13.0 CPU 秒 | 直接回调候选 CPU 秒 | VCS CPU 秒 |
| --- | ---: | ---: | ---: |
| 非规则反馈 1 万 ff /200 周期 | 0.38 | 0.39 | 0.89 |
| 非规则反馈 10 万 ff /200 周期 | 6.23 | 5.99 | 4.61 |
| 六模型组合图，1536 单元 /2000 轮 | 0.18 | 0.18 | 0.53 |
| 真实 barr_modmult，128 组黄金向量 | **13.78** | **13.77** | **6.14** |

首轮 10 万档候选中位数改善约 3.85%；固定 CPU 0、同二进制、预热一次后交替五次，原版/候选变为 **6.07/6.39 秒**，候选较慢约 5.3%。真实设计和组合负载基本持平。证据不足以采用这项变换；不宣称稳定加速，也不将它作为新产品开关。三次原始范围及固定 CPU 各次值保留在 [分析](analysis.json) 与 `remote-verified/build/` 下。

真实设计墙钟为原版/候选/VCS **13.829/13.819/10.523 秒**，峰值 RSS 为 **108340/108544/195200 KiB**。CPU 与墙钟分别报告，VCS 启动/许可成本包含在执行命令内。1.23 倍是前批理想反馈网络的另一轮数据；真实设计得到的 2.24 倍是当前更重要的性能差距。

生成 C++ 字节数、编译命令、生成/编译日志及复用二进制的前后 SHA 均保留。真实输入的首轮生成/编译与其他正确性作业重叠，其计时不用于编译加速结论。

## 真实 256 位门级接入

保留原始 300,909 个具名单元、111 种模型和完整 Liberty，在结构网表末尾追加适配顶层，RTL-facing 端口按 64 位 limb 驱动；内部 256/257 位连接完整展开。功能绑定有 335,872 个运行时候选 net、20,197 个存储实例。没有用行为 RTL parser 处理大网表。

原 `gate_sim/golden.txt` 的 128 组输入/输出由报告中的 RTL 产生。测试平台把输入展开为标量/64 位赋值，直接读取实际 DUT 的全部 256 位结果；原版、候选及 VCS 各 128/128 一致，随后每工具预热一次加三次性能运行均重新核对全部输出。该设计是近似 Barrett 实现，golden 不等同于精确 `a*b mod p`。

native 使用原完整 Liberty 的理想布尔/存储语义；VCS 使用报告中原 Verilog 单元模型，包含零延迟 specify 路径。均未标注 SDF，时钟 10ns、固定 drain；这是新的同输入 TB，不套用报告原 TB 的数值。完整 RTL 的任意宽度运算、真实 SDF 时序行为仍待补齐。

初次 VCS 编译因未带 timescale 的网表先于单元模型而触发 ITSFM；native 生成/编译已完成。按原报告 filelist 顺序先读单元模型，再读网表和 TB，复用既有 native 产物继续验证成功。保留初始脚本、失败报告/日志/计时及修复驱动，不把失败归为 native 功能问题，不重复运行已完成的生成。

[结构核算](real-structure-analysis.json) 从精确的 baseline C++/IR 重新计算：335,795 个 Network net 之外只有 **77 个新匿名输出 net**，占全部 net 不到 0.03%。删除此类输出对本真实设计可直接减少的状态很少；不能据理想反馈网络的十万个悬空 QN 推断真实设计收益。重算脚本为 `analyze-structure.py`。

## 验证与证据

- 候选本地/Linux CTest 各 **22/22**，分别 282.19/421.72 秒；15 组 gate/VCS 各三次，18 条完整有序波形流与固定 0.13.0 一致。
- ASan/UBSan 编译器、18 个生成波形模型和 4 对生成基线/回滚程序通过；[清单](sanitizer-provenance.json) 记录 27 个实际二进制及 sanitizer 符号。运行时/并行实现未改变，前批线程检查证据继续适用，没有将其重复记为本批新 TSAN。
- 候选只修改 `GateDesign::cpp()` 后缀。解析/展开前缀、RTL 编译语义、SDF/binder、全部 parser 与原生 codec 不变；生成 C++ 的 runtime/model 函数前缀和 RTL main 与基线相同，变化限于 install handler。
- [引用](baseline-reference.json) 固定前批源码包 `/tmp/dsim-process-source.tar.gz`，SHA256 `ed04a8c4662a763355d99ef2d737c8d2ca618307bb49b2bff42d012c6880be5e`。候选覆盖包与 [清单](candidate-snapshot.json) 可重建同版本隔离实验。
- 原始证据 [归档](evidence-archive.json)：**1,581 个文件，23,076,395 字节**，SHA256 `1d5fc408ef6d399f23fbb76bb93a6cd17cf4903869a7908f116222d111a91fa1`；输入/库/二进制/源码哈希、计时、完整 trace、波形、失败均在 `remote-verified/`。完整 1.2GB Liberty 保留原路径与前后 SHA，没有复制进证据包。
- `python3 validation/m5-model-handlers/analyze.py` 独立重算原始 CPU/RSS、各轮 oracle、15 组 VCS、18 条有序流及真实 128 组输出，不只读取 PASS 标签。

六模型 oracle 初次把 COMPLEX 的 Liberty `A B ^ C` 错分组为 `(A&B)^C`；给定库与独立 Verilog 参考明确为 `A&(B^C)`。保留 [初始失败](initial-mixed-oracle-failure.json) 和初始生成器，只修正 oracle，网表未改；修正后小规模 native/Icarus 及全规模 native/VCS 均一致。这是验证器修正，不计为仿真器功能修复。

真实基线另采集 300ns 活动前缀：普通/Callgrind 输出均匹配原始前 6 组 golden，5,215,023,753 条 Ir；set/drive/组合 handler/run_to/unary 自身分别约 13.53/11.80/7.26/6.48/4.45%。另有字符串 compare/strlen/memcmp，下一候选优先对门级固定反相操作生成直接调用，保留显式 1 位归一化和 X/Z，再评估标量值传递及驱动/等待布局。该候选尚未实施或证明加速。

profile 使用原版 0.13.0，C++ 只将 main 的 run 改为 run_until(300000)，tick=1ps，属于活动前缀诊断，并非完整 128 组的 CPU 测量。Valgrind 发出一条 brk segment overflow 警告，原样保留；没有硬件 cache/周期计数结论。[独立 profile 归档](profile-evidence-archive.json) 有 13 个文件、4,245,952 字节，SHA256 `4faba94d8291d8459a83edb16136ac27e540d47075d45ee4df3fa2a3e5fa7ebb`，独立保存于 `profile-verified/`，没有覆盖已封存的计时证据。

当前源树继续开发后，可把前批冻结源包解到另一目录，再将该源目录作为 analyze.py 的可选参数，校验旧源码和独立证据；本地 sanitizer 二进制仍取此工作区的专用不可变构建目录。

SDF 延时事件/取消与实际回标、自动分区、压缩编码仍按总计划推进，整体目标保持进行中。

后续从恢复的固定原版另做 [固定反相专用化](../m5-unary-specialization/README.md)，已经独立验收采用；本目录已撤回的模型专用 handler 未重新引入。
