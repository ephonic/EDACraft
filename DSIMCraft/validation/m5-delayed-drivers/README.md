# 延时驱动内核与新版真实性能热点

本批采用可选的延时驱动内核基础，继续保持 0.13.0 开发版本。尚无从 SDF 文件到运行时通道的自动回标，不计为完整非零延迟门级仿真；未新增 CPU 加速结论。接口与边界见 [说明](../../docs/delayed-drivers.md)，独立复核结果为 [PASS](analysis.json)。

生产差异仅为运行时的 `DSIM_TIMING_ENABLED` 条件代码、CMake 测试登记和三个测试/适配源文件。RTL/gate 两个 parser、门级函数及安装器、SDF parser/绑定、压缩编码器均未改变。新增通道保存已请求值、该驱动已提交值与取消代次；驱动事件与进程 timer 共享稳定时间堆，通过独立槽保存值，不阻塞固定敏感进程。支持异步零延时、替换尚未提交请求/保留变化的显式策略、取消与槽复用、别名/多驱动、检查点、预测事务及并行 worker。

两种策略是内核 API 定义，不能直接等同于 VCS 的所有模块路径/脉冲选项。调用方须独占登记的 signal/driver；不能绕过通道直接修改同一驱动。取消远期事件采用惰性回收，内存仍取决于待消费事件的高水位。完整目标精度、路径/条件选择、pulse reject/error、RETAIN 和 timing checks/notifier 属于后续注解层。

| 验证 | 结果 |
|---|---|
| 本地完整 CTest | 26/26，261.30s；最终源的两个新增核心目标重建后再次 2/2 |
| Linux 完整 CTest | 26/26，491.49s，冻结后的最终源 |
| VCS 微例 | 3 组新编译，各 native/VCS 三次；另对既有同输入 VCS 三次；全部 trace 一致，annotation 均零 errors/warnings |
| 完整有序波形 | 与已采用固定敏感列表版本相比，18 条流的字典和完整事件序列一致 |
| ASan/UBSan | 9 个实际二进制：核心 5 个、驱动适配程序 1 个、时序开关开启的既有 checkpoint/parallel/fixed-wait 3 个 |
| TSan | 新延时并行用例通过，1/2/4 worker、5 个 quantum，另有一次参考运行 |
| 关闭时序开关 | 普通、wave、parallel、wave+parallel 四配置的旧/新预处理代码及 O2 汇编逐字一致；普通配置另在 Linux GCC 复核 |

微例适配器直接指定整数延迟，覆盖 2ns 路径拒绝 1ns 窄脉冲、显式保留脉冲与 12 种四态转换。VCS 使用已有相同 Verilog/SDF：默认策略、`+pulse_r/0 +pulse_e/0` 和 12-transition 路径。原始参考源码/日志 SHA 在 [reference.json](reference.json)；新命令、编译、三次 trace 和 annotation 在证据包 `build/delay-verification/`。这是内核事件差分，不是 SDF 注解集成验收，也没有重新声称此前 15 组门级用例进行了 fresh VCS 比较。

性能仍以最近同核测量为基线：真实 300,909 单元/128 golden 的 CPU 为当前 14.57s、同轮 VCS 9.10s，约 1.60 倍；本批不替换它。新增固定反相/固定敏感列表版本的 300ns 活动前缀 profile，正常/Callgrind 均匹配前 6 组 golden，总 Ir 为 4,061,598,688。set 源文件自身 17.37%、drive 源文件自身 15.15%（另有 vector 归因 5.28%）、run_to 8.33%、ReadyQueue::push 4.31%。这里只记录指令归因，正确性任务同期运行，没有 CPU 加速或 VCS profile 比较。原始 `brk segment overflow ... 0x484e000` 警告保留，不将插桩计时作为性能结论。下一候选按 [plan1017.md](../../plan1017.md) 评估安全跳过单驱动重复写入，再做完整真实设计 A/B。

保留初次失败和修正：测试误以为普通 run 边界会永久冻结拓扑，改为显式 freeze 后验证；预处理逐字检查发现仅定时器语句换行不同，将关闭分支恢复原行而保持严格检查；macOS 不支持 leak sanitizer，改为 `detect_leaks=0`，不声称通过 LSAN；profile 驱动修正 generated SHA 的字典字段；采集包中的测试用绝对 symlink 被安全提取器拒绝，最终包将链接内容物化。初次包和日志未覆盖。

最终源包 `/tmp/dsim-delayed-drivers-v2-source.tar.gz`，SHA256 `28120755dc5f2b0e381391333dad00abcf9c1a90d1514430298a6a02158f2753`。冻结 158 个工程源文件、108 个 parser 文件、3 个不变原型依赖及驱动/参考输入。Linux 目录 `/tmp/dsim-delayed-drivers-1018-ULwVaq` 已 terminal 0。profile 独立目录 `/tmp/dsim-fixed-wait-profile-1018-eT6s6W`，使用上一批已采用的实际生成源，仅将 `run()` 改为 `run_until(300000ULL)`。

最终证据包 `/tmp/dsim-delayed-drivers-v2-evidence.tar.gz`，SHA256 `88182f928b933a2f81bbbab15658ace1ba99ef27f5ac2330562c249e27489288`，1160 文件、42,913,952 字节展开内容。原始文件逐项核验，提取于 `remote-verified/`；[analyze.py](analyze.py) 从哈希、源差异、原始 trace、波形、汇编和 sanitizer 符号重算验收。旧源/证据归档、已有 sanitizer 二进制与波形原型均保留。完整 SDF、自动并行分区、压缩扩展和整体 VCS 功能/性能目标仍在进行。
