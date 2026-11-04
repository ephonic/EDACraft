# 近时间队列的生产接入

基于已修正 VCS 连续向量 delay 的 425 文件版本 d862b917，接入实际 `--time-wheel` 编译选项，默认关闭。427 文件冻结归档：`fb428999f23437814f42195754c1a0f7824973e5f19cde884f2c5bd2b2f0c206`，完整文件身份见 `source.json`。

修改 CMake、编译器入口/接口和生成运行时，新增 `tests/timing/time_wheel.cpp` 与 `.py`。RTL、门级、SDF parser 均保持基线内容。运行时当前 SHA256 为 `d38e0ab5abfe7687065d33e09b5fbb798d80500923cfa5624174832daa6c1a09`。`candidate.json` 是接入前的构造记录，里面 `production_modified:false` 仅描述当时暂存阶段；目前生产运行时和 CLI 已接入。

本地 10 项内核已通过，实际 CLI 的 9 类 RTL/SDF、108 份 ordered/settled × VCD/raw/Zstd 捕获及 4 份检查点/拒绝预测重放捕获通过。初次测试使用尚未支持的 integer 声明而失败，日志保存在 `macos-targeted-initial.log`，输入与输出保存在 `build-time-wheel/time-wheel-flow-initial`；改用受支持的 packed reg，保留相同 for 循环与延迟覆盖。复测见 `macos-flow.log`，完整 83 项见 `macos-ctest.log`。

`local_checks.py` 已完成 6 个实际内核的本地 ASan/UBSan、实际生成的 boundary/replay 四份捕获核对，以及默认/标量两种完整 SDF 程序在 feature-off 下的同 Clang 预处理逐字身份。完整原 SDF 的 scalar 程序仅替换整个生产 runtime 并加选项宏，在本地 Clang/O1 执行全部 128 笔输出匹配，见 `full-local/results.json`。这不是新编译器重新生成完整网表的证明，也不是 Linux 性能结果。

完整83/83已在原会话30426正常退出0（385.35s）。`verify_local.py --capture` 已保存捕获并对源码、实际编译标志、stdout/stderr、全部事件流、回放变换、sanitizer与完整SDF程序变换/输出独立核对PASS，结果为 `local-validation.json`。新生产源427的Linux验证仍未运行。

Linux 脚本已准备但尚未启动。`launch_linux.py` 要求标量独立性能复测已正常终止并核对通过，以避免构建干扰计时。后续执行干净 83 项、启用时间轮的六种实际 VCS 公共流程、当前编译器重新生成完整 SDF 的默认/标量 feature-off 身份，以及启用时间轮的通用/标量两种 O2 编译与各 128 笔执行。`fetch_linux.py` 只抓取正常终止任务；`verify.py` 核对原始证据、跨平台完整事件流及实际 C++ 生成等式。Linux 未验收前不发布性能收益，整体 VCS 功能对齐仍在进行。

标量独立复测已终止并审计后，427源Linux任务已实际启动于/tmp/dsim-time-wheel-integration-1018-7h2O9leh（原会话57108）。完整83/83已观察通过（488.15s），六类启用时间轮的新VCS公共流程也通过；默认/标量全量新编译器生成身份已完成，当前同一任务继续执行两种实际O2队列程序各128笔。尚未完成归档/独立审计，不发布队列性能收益。以上“尚未启动”为历史状态。

Linux原任务57108现已正常退出0。934个原始文件归档SHA256为bcf72fa8f4ffb2ac478f9c1b6858714a7db8fda3b07ffd308f71320f59bd99e3，已下载逐项核对；以冻结427根执行verify.py独立核对PASS：两平台各83项、108跨平台完整捕获/4回放、六类VCS共581顶层物理位、实际新编译器全SDF的default/scalar两种队列O2程序各128输出，以及关闭选项的完整CPP/GCC预处理身份。见verification.json。仍默认关闭，无队列性能计时结论。
