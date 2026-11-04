# M91：混合 packed 存储与 VCS 对齐

实现提交 `a5442b8267900147fcd3a40347d3bbe33893d741`。修复 M86 引入的成员写入转换回归：unpacked struct 的两态成员转换不再错误套用于 packed struct/union。混合 packed 底层保留 X/Z，bit 视图读取时转换；独立两态存储保持转换。编译期决定路径，没有引入运行时类型判断。

上一稳定版可复现原始 `values.sv` 和新增 `storage_views.sv` 的失败，见 `baseline.json`。原有断言未修改，新增直接/嵌套成员、固定数组、一次求值、130 位 union、拼接与选择、延迟 NBA，以及独立 bit/全两态 packed/unpacked bit 存储的保护检查。

## 已完成验证

- 原生完整聚合组：5 模型、63 份 ordered/settled 捕获、3 次失败预测回滚、19 类拒绝；原有双分区和原生边界检查通过。见 `native-check.json`。
- 六组相关 CTest 通过：packed_aggregates、complex_report2、assignment_patterns、ascending_packed、complex_report、interfaces，总耗时约 211 秒。见 `related-tests.json`。
- 实际 VCS W-2024.09_Full64：5 份同源模型 TRACE 全部相同，1,236 个共同物理位的完整 settled 时间线一致。见 `vcs-check.json`。
- VCS 层次声明 `gen[i].x` 与 native 分层 scope、以及 unpacked struct 单独成员 dump 做显式映射，逐位映射完整记录。VCS 未 dump 的 40 个固定数组位单列为 native-only，不计入共同位。其余 VCS 位全部纳入比较。
- ASan/UBSan：8 个实际程序的输出及完整有序波形通过（串行、时间轮、并行、回滚各两份），6 份 sanitized compiler 生成 C++ 与原生完整相同；leak 检测关闭。见 `sanitizer-check.json`。
- Linux 源码包包含 1,459 份文件，逐项 SHA256 全部匹配实现提交。见 `source-package.json`。

Linux 稳定发布已完成：10 组检查全部通过，两个别名均指向 `/apps/EDAs/own/dsim/releases/20261025T061523Z-a5442b8/bin/dsim`；二进制 SHA256 `83af42754ea001e21df10575d1bded02480017ef492e682fa7a3e4eadf92027b`。1,459 份安装构建源码 hash 再核对通过；加载 syn.bash 后通过实际安装入口重编译4模型，完整 C++ 与整份 VCD 均一致。见 `linux-check.json`。macOS 稳定发布也已完成，73 项检查全部通过，release=`20261025T062855729111Z-5875755616ae`，binary SHA256 `339dbe741656540ec030f82364f7005bacce9c4233b1b5a4427210afb5e613a6`，source SHA256 `5875755616ae967182f9ae2ec62f11545cf93369c4496c6e8cfc254ba0ad94a9`。501 项发布输入全部匹配提交 828183d，8 份运行时快照匹配；git_dirty 包含计划、验收记录和用户未跟踪实验目录，不表示编译输入偏离提交。见 `stable-release.json`。

本地实际入口也重编译4模型，完整 C++ 与整份 VCD 均一致，见 `installed-local-check.json`。本地 `~/vibe-coding/dsim-test/bin/dsim` 和 Linux `/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` 均已更新。

跨平台与本地候选版：18 份完整 C++、79 份执行输出、63 份完整 ordered/settled 波形逐项相同，编码文件字节也相同。见 `linux-artifacts-check.json`、`stable-artifacts-check.json`。

首次本地发布检查在新增聚合组停止：回归脚本默认在编译器旁寻找 CMakeCache，但发布二进制目录不包含缓存。64 项先行检查已通过，稳定入口未切换。提交 `828183d` 增加显式缓存参数，并将聚合组前移；通过发布目录二进制加显式缓存完整运行 63 捕获后重新发布。见 `initial-publication.json`。该提交不改编译器、parser、运行时或构建目标；Linux 使用实现提交 a5442b8 的冻结源码包，本地使用包含发布入口修正的版本，两者编译器输入相同。

## 复现与证据

```sh
ctest --test-dir build --output-on-failure -R '^rtl_packed_aggregates$'
python3 validation/m91-packed-storage/verify-vcs.py \
  --native build/rtl-packed-aggregates --vcs /path/to/vcs-evidence \
  --output /tmp/m91-vcs-check.json
```

`run-vcs.py` 在已加载 VCS 环境的远端读取 `/tmp/dsim-m91-vcs-inputs/*.sv`；`run-sanitizer.py` 接受 compiler/native/cache/output 参数。`check-installed.py` 通过实际安装入口重新编译，`export-artifacts.py` 导出完整 C++、stdout 和波形事件流身份。

生成程序、波形、日志按[仓库归档规则](../README.md)不重复提交。VCS 完整原始输入、日志与波形归档在本机及 Linux 的稳定 evidence 目录，具体路径和 SHA256 见 `vcs-archive.json`。结构化结果和复现脚本随 Git 保存。

完整 SystemVerilog、VCS 功能和性能差距仍存在；packed enum 自增、部分越界动态写入、极端 64 位下标等既有差异未在本批修改。不新增性能比值。
