# M87 固定周期断言序列验收

实现提交 `f843dc1`。当前支持范围见 [sequence-delays](../../docs/sequence-delays.md)，不宣称完整 SVA、UVM 或新的 VCS 性能比例。RTL 与门级 parser 独立，DWF 编码未改。

- 8 个原始同源模型，VCS W-2024.09_Full64；7 个模型逐拍/最终 TRACE 一致，第 8 个独立双分区模型通过全部共同位波形核对。全部 1393 个共同信号位（按完整层次名/索引保留端口别名）完整 settled 时间线一致，无尾部排除，也没有仅一方 dump 的位。`vcs-wave/*/input.sv` 保留远端实际源，核对 permanent fixture SHA256。测试故意使一部分断言失败，VCS 自动位置诊断属于预期，不宣称诊断文字一致。
- 原生 serial/time-wheel/parallel 三后端，31 份完整 ordered 捕获，其中 7 份强制失败预测回放。所有后端完整 ordered 流相等。独立 `parallel` 模型实际 `partitions:2`，两输出最终为 3 和 1。最初含双输出显示的测试将依赖合并成一个分区，已去掉该耦合并重新完整验收；没有把 serial fallback 计为并行。
- 18 类负例明确拒绝且不生成 C++：非恒定/X/负数/超宽周期、总跨度和阶段上限、范围/重复/多时钟/序列 antecedent、后续阶段的副作用/文本/内存与非法采样深度等。最大 65536 拍和 256 条件合法边界通过 emit-only 编译。
- 15 个实际 ASan/UBSan 生成程序（含 7 回滚和实际两分区）完整输出和全部位时间线与原生相同；18 个 sanitizer 编译器拒绝、原生和 sanitizer parser 重复克隆/清理通过。ASan leak 检查关闭。
- 旧并发断言：41 捕获、8 回滚、23 拒绝；旧采样函数：27 捕获、6 回滚、14 拒绝，全部通过。旧 `##1` 拒绝项已替换为仍未实现的范围延迟。

复核：

```sh
python3 validation/m87-sequence-delays/verify.py
python3 validation/m87-sequence-delays/verify-extra.py
```

`tests/sequence_delays/regression.py` 是永久回归，已接入 CTest 和稳定发布。验收日志和波形选择性保留；生成 C++ 另保存 SHA256，原生可执行文件不入库。Linux 与稳定发布结果如下。

稳定发布已完成：

- macOS `/Users/yangfan/vibe-coding/dsim-test/releases/20261025T014257765739Z-98f344d67e55`，66 组发布检查全部 PASS。入口 `~/vibe-coding/dsim-test/bin/dsim` 已更新；binary SHA256 `dd041521fc0f12afab6801577f773ad83170befc00cd2e93a7cb4edd95b6414a`；source SHA256 `98f344d67e55fc6a7ca4a1b7dc44d17ccb7e434842704fbbc0d39c65e06f2448`。完整输入/运行时/二进制哈希及 31 份生成 C++、输出、ordered 波形已复核；安装入口重新编译运行 chain 通过。`git_dirty` 包含无关用户实验与验收文件；全部受跟踪编译输入与实现提交相同，指纹也记录了不参与编译的现有 `.DS_Store` 元数据。
- Linux `/apps/EDAs/own/dsim/releases/20261025T014331Z-f843dc1`，binary SHA256 `cf7c8723aa5a5e610f1ad6f86bbdda30d94ad3b804204898b9213adc54a4611a`。parser/sequence/concurrent/sampled/complex/gate 六组全部通过；31 份生成 C++ SHA256 与 macOS 逐份相同，输出与完整 ordered 波形一致。源包 manifest 的全部文件哈希已复核。两个安装入口 `/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` 已更新，加载 `syn.bash` 后通过实际入口编译运行 chain/samples，波形逐字节与验收版本相同。

新增发布复核：`verify-release.py <macOS release>`、`verify-linux.py`。实现已推送 GitHub；本目录保留验收及发布证据。
