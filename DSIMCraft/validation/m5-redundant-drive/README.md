# 重复单驱动写入候选：已撤回

**未采用候选优化。** 四态与事件正确性验证通过，但真实设计收益未能复现，已将运行时逐字恢复为上一批已验收版本；只保留 CMake 登记和独立行为回归 `tests/redundant_drive.cpp`。采用决定见 [decision.json](decision.json)，原始数据独立复核见 [analysis.json](analysis.json)。总体性能与功能目标继续进行。

候选在连接已定型、无 alias、仅有相同驱动身份、存储值和当前解析值都等于归一化请求时跳过重复 drive。没有新增状态字段。直接 set/NBA、首次驱动、新身份、多驱动和待定连接必须回退；完整条件见 [等价分析](../../docs/redundant-drive.md)。生产运行时 SHA256 恢复为 `ac4c2bcd3cb2839f6d10ffa64bd9a90ec25183b26230bfaf8e64b4edd471bced`，两个 parser、SDF 和波形编码器均未更改。

## 性能结果与撤回理由

所有工具固定 CPU 0，自有任务串行；完整输入相同、两个 native 版本均重新生成并用相同 C++17/O2 编译。主实验各预热一次，三次旋转顺序；真实设计为原 300,909 单元、111 模型、完整 1.2GB Liberty 和同一 128 组 golden，所有运行逐笔核对完整 256 位输出。反馈采用独立预期模型，三类 RTL 同样检查输出。

| CPU 秒中位数，首轮三次 | 原版 | 候选 | VCS |
|---|---:|---:|---:|
| 真实门级设计 | 14.32 | 13.67 | 10.29 |
| 100k ff 非规则反馈 | 8.76 | 7.01 | 7.98 |
| RTL clock 20M | 2.80 | 2.76 | 2.95 |
| RTL fanout 64 / 1M | 2.78 | 2.81 | 2.99 |
| RTL arithmetic 20M | 0.40 | 0.39 | 0.46 |

真实设计首轮原版/候选三次分别为 `[14.32,14.38,13.74]` / `[13.67,13.83,13.00]`，看似降低 4.54%；反馈原版 `[6.73,8.76,9.02]`、候选 `[6.68,7.01,9.04]`，波动明显。因而使用**同一批二进制、同一核**另做预热和五次交替 A/B、B/A 配对复测，没有重新生成或编译。

| CPU 秒中位数，五次配对复测 | 原版 | 候选 | 候选变化 |
|---|---:|---:|---:|
| 真实门级设计 | 13.25 | 14.41 | 增加 8.75% |
| 100k ff 非规则反馈 | 6.70 | 6.59 | 减少 1.64% |
| RTL fanout | 2.75 | 2.81 | 增加 2.18% |

真实复测原版 `[13.09,12.99,13.39,13.25,13.31]`，候选 `[15.89,14.12,14.21,14.75,14.41]`，五对均慢；fanout 两轮中位数也均慢。故不采用，保留全部样本，不筛选有利轮次。固定 CPU 不等于主机独占或锁频，结果不能证明具体 cache/分支原因，也不能推出普适比例。复测没有 VCS 计时，禁止用它的中位数与首轮 VCS 分母混算。

恢复后的生产版本在首轮为 **14.32 / VCS 10.29s，约 1.39 倍 CPU**；这是原运行时重新测量，不是本候选带来的改善。上一批 14.57 / 9.10s 的 1.60 倍属于另一轮，差值不能归因于优化。首轮真实原版/候选 RSS 为 86,728/87,268 KiB，没有内存收益结论。生成/编译命令、成本、wall、RSS、输入和二进制 SHA 均在 `remote-verified/build/performance/results.json`；复测在 `remote-verified/build/performance-repeat/results.json`。真实及反馈 VCS 二进制来自既有、SHA 核对的构建，本轮均重新运行；三类 RTL VCS 本轮新编译并运行。

## 正确性与保留测试

| 检查 | 结果 |
|---|---|
| 候选本地 / Linux 完整 CTest | 各 27/27，262.59 / 484.03s |
| 新独立行为测试 | 同一 fixture 在原版和候选均通过；1/7/64 位、全四态、独立逐位解析模型、通知与唤醒、身份/别名/直接 set/NBA、恢复与延时预测 |
| 补充边界 | 原版/候选均验证 alias 其他节点修复、多驱动被直接 set 遮蔽、未定型连接；见 `supplemental.cpp` 和日志 |
| 门级 VCS 参考复核 | 15 组新 native 各三次，对相同输入既有 VCS 各三次 |
| 延时驱动微例 | replace/preserve/twelve 三组新适配程序各三次，对上一批相同 VCS 三次；非自动 SDF 回标 |
| 完整有序波形 | 与上一批已验收版本相比 18 条字典及完整事件流相同 |
| ASan/UBSan | 16 个实际二进制：8 个核心/适配目标、4 类生成模型各 baseline/replay 两个；生成波形逐事件相同 |
| TSan | 两个实际并行目标，包括固定敏感 relay 与延时驱动分区；通过 |

macOS sanitizer 使用 `detect_leaks=0`，不声明 LSAN 通过。旧 sanitizer 二进制、历史归档与波形原型均未覆盖。恢复后的默认构建重建，核心 8/8、counter CLI 的四条输出通过，生成模型中嵌入的运行时逐字核验为原版；Linux 另将保留的新测试对原版运行时独立编译运行通过。日志另记在 `production-*.log`，不将候选的完整 CTest 冒称为恢复版本的新完整运行。

## 冻结与复核

候选源包 `/tmp/dsim-redundant-drive-source.tar.gz`，SHA256 `d383bbaf1bcfc28ecbb37a7a009632093313ac89e25a6762bcac4d240297a9ad`。冻结 159 个工程文件、108 个 parser 文件、3 个原型依赖及五个驱动/参考文件。Linux 目录 `/tmp/dsim-redundant-drive-1018-KlFuNC`，主流水线和五次复测均 terminal 0。

证据包 `/tmp/dsim-redundant-drive-evidence.tar.gz`，SHA256 `be58e1528109b00bb8ccca1aa814bf9b4e6528f217f272945b2430395ca7db41`，1441 文件，展开 112,178,064 字节；安全提取到 `remote-verified/`，每项 SHA 核验。[analyze.py](analyze.py) 复核源差异、完整波形、独立输出 oracle、原始 user+sys/RSS 和中位数、同二进制配对顺序及实际 sanitizer 符号。

撤回后的生产源码另包为 `/tmp/dsim-redundant-drive-production-source.tar.gz`，SHA256 `7d50442262e323b6b421a17abbe215e9b8e3c1f8a7f35378ba619f4f5426d6c3`，清单在 [production-snapshot.json](production-snapshot.json)。相对已验收延时驱动版本，只增加 CMake 测试登记和新测试，不包含候选运行时；保留候选包便于复现实验。

下一候选优先检查标量四态值传递、驱动解析和调度的数据访问成本；完整 Liberty 功能建模成本单独评估，不改换简化输入。功能侧继续实际 SDF 编译回标、逐接收 pin INTERCONNECT 和精确延迟合并，自动分区及压缩格式扩展仍未完成。
