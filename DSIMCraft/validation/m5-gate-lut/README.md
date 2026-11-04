# 四态查找表：采用记录

本批采用小型纯组合输出查找表。生产修改仅在 `src/gate_compiler.cpp` 与 `src/rtl_compiler.cpp`；runtime、并行、波形和两个独立 parser 保持原样。SDF 数值层单独记录在 [SDF 批次](../m4-sdf-merge-semantics/README.md)。

真实设计独立七对交替 CPU 中位数 9.87→9.47s，配对收益中位数 **3.8579%，6/7 改善**，达到运行前设定的 ≥3%、至少5/7改善门槛。反馈五对配对中位数慢1.2285%，在预设3%回退限制内。原始慢样本保留，不声称全部负载均加速。

实际编译器重新生成后与筛选候选的完整预处理源码逐字相同，真实及反馈 ELF SHA 也相同。新同轮各三次 CPU 中位数：

| 负载 | 前版 | LUT | VCS |
|---|---:|---:|---:|
| 完整真实设计，300,909 单元，128 组完整 golden | 10.11s | 9.64s | 7.76s |
| 100k ff 反馈 | 3.85s | 3.83s | 5.59s |

真实 LUT/VCS CPU 为1.2423倍。固定一个逻辑CPU、零延迟、无波形、共享主机未锁频。VCS为既有SHA固定二进制，本轮重新运行；不把该比例推广到RTL、SDF或完整功能集。CPU与墙钟分开，所有轮次保留原始time输出和完整trace，复测不借用其他轮VCS分母。

验证：两平台各30项；179,648组全部四态、普通/紧凑网、输入输出及多输出别名、有序通知；24份完整生成C++跨平台逐字相同；18个完整有序流跨平台及前版一致；9个实际ASan/UBSan程序；15门级+3延时新native各三次对既有VCS三份参考。默认 `build/dsim` 已重建，RTL计数器及两个门级例的完整生成代码与已验证版本逐字一致，实际golden通过。普通RTL计数器生成SHA保持不变。

证据：

- `source-snapshot.json`：冻结候选227工程文件、108 parser文件和3波形依赖，源归档SHA `715cbcceed66d46f158f5b612e3f3686b9b8bcd5215546596fda171846285975`。
- `screen-evidence.json` / `screen-verified/`：239文件，热点、两个未采用试验、LUT初筛与独立复测。读取缓存未过3%初筛；发布防护只有初筛，没有独立复测，本批不采用。
- `linux-evidence.json` / `linux-verified/`：454文件，两平台一致性所需Linux生成结果、完整回归、实际编译器三方原始计时。
- `verify.py` / `analysis.json`：归档及逐文件SHA、原始计时/trace复算、预设门槛、实际生成代码与ELF身份、完整回归和实际sanitizer二进制校验。
- `verify-production.py` / `production-results.json`：默认编译器生成与实际执行证明。
- `production-snapshot.json`：采用后代码和更新文档的组合快照；历史候选与所有旧批次归档保留。

本批验证可运行 `python3 validation/m5-gate-lut/verify.py`，默认构建证明运行 `python3 validation/m5-gate-lut/verify-production.py`。证据归档路径在JSON中；原始记录全部保留。整体功能目标仍在进行，下一步是复杂度选表、常量传播及通知/队列成本，并继续一般SDF回标、自动分区和波形扩展。
