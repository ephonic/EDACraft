# M94 — REPORT4 实际安装入口复核

结论见 [REPORT4 复核](../../docs/report4-review.md)。本轮只新增测试和文档，没有修改编译器、运行时或门级 parser。

输入：本地 `~/vibe-coding/dsim-test/rtl-tests/complex/REPORT4.md`，远端指定目录不存在。原文 SHA256 和当前本地二进制身份保留于 `baseline.json`；p21 原文复制到 `tests/report4/p21_sra_cond.sv`，p27 和字面量正例复用 `tests/report3` 的文件。原探针的作者自带诊断原样保留。

`tests/report4/models.json` 定义五份源及 top，`expected.json` 的全部输出来自真实 VCS 同源执行。新增 `signed_contexts.sv` 包含独立数值检查和十组动态状态，覆盖 signed/unsigned 三元分支、cast/function 边界、32/64 位、负除数、移位宽度边界、X/Z 条件、未知操作数及除零。

本地实际稳定入口通过三后端、ordered/settled 共 32 份标准文本 VCD 捕获和两次失败预测回滚。`vcs-check-local.json` 检查全部功能输出及 1564 个共同物理位的完整 settled 时间线；无不同位、无 VCS-only 位。动态字符串按原功能边界不伪装成数值波形；字符串结果由完整输出和数值观测检查。`--threads 2` 在本批模型可以回退单分区，本轮不据此声称测得并行加速。

Linux 的实际 `/apps/EDAs/own/dsim/bin/dsim` 在加载 VCS 环境后同样通过五模型、32 份捕获和两次回滚；`vcs-check-linux.json` 的 1564 位也全部一致。两平台所有 17 份生成 C++、32 份运行输出和 32 份完整 VCD 文件逐字节相同，见 `cross-platform-check.json`。`installed-check.json` 复核两端二进制哈希、远端兼容入口及八份运行时快照；当前编译器实现与发布提交 b457afb 相同。

VCS 边界记录：首次扩展模型取 `32'h80000000 / 32'hffffffff` 时，VCS 自身以 Floating point exception 退出，未计入通过数。保留该次原始源码、日志和哈希。共享模型将该处除数改为 -3 后，两工具仍使用逐字节相同的修改后源码。见 `vcs-overflow-failure.json`，不删除失败记录或将部分运行当成完整对齐。

复现本地实际入口：

```sh
python3 tests/report4/regression.py ~/vibe-coding/dsim-test/bin/dsim /tmp/dsim-report4 build/CMakeCache.txt
python3 validation/m94-report4/verify-vcs.py --native /tmp/dsim-report4 --vcs /path/to/vcs-evidence --output /tmp/report4-vcs.json
```

正常 CMake 构建也可执行 `ctest --test-dir build -R '^rtl_report4$' --output-on-failure`。远端在加载 `/apps/EDAs/syn.bash` 后，将相同五份源放入一个输入目录，执行 `run-vcs.py --inputs INPUT --output OUTPUT`；该工具只额外添加独立的 dump 模块，不改写输入设计。

CTest 注册检查通过。稳定发布脚本已将本组加入必过检查和输入哈希清单，今后发布时会自动防止这两项回退。

本次没有改 C++ 实现，未重复全库回归或 sanitizer。现有稳定版本仍为 M93 实现提交 b457afb，原完整发布验收见 [M93](../m93-report3/README.md)。原始报告和全部生成程序/日志/波形保存在 `~/vibe-coding/dsim-test/evidence/m94-report4`，不将编译产物写入 Git。
