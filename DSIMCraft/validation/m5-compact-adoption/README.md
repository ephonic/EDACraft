# 复现后接入紧凑 SDF 接收端

独立五对固定 CPU0 复测已完成，每次完整 128 笔输出与首轮相同。五对 CPU 耗时下降为 11.29%、11.03%、5.24%、8.40%、10.20%，配对中位数 **10.20%**；RSS 中位数从 758,428 KiB 到 634,660 KiB，下降 **16.32%**。进程 CPU 中位数为 136.19s/122.61s。共享主机、未锁频率，本轮未运行 VCS，不能沿用首轮 VCS 分母生成新的速度比。复测全部 52 个原始证据文件已归档校验，12 次预热/正式运行的输出及 GNU time 原始数据已独立复算。

满足此前 3% 门槛后，接入冻结候选的两个生产改动：私有 INTERCONNECT 接收端使用 compact 槽并保留 Z→X 初始路径戳；延迟驱动注册避免强制 fallback。注册改动也影响 IOPATH 输出通道，因此没有拆开采用。`integration.json` 核对当前 runtime 除注册函数外与全局结束冻结版本逐字相同，注册函数及门级生成器与已测候选精确相同；两个 parser 及其他生产代码未改。

组合源码 414 文件，`/tmp/dsim-compact-adopted-source.tar.gz`，SHA256 `9798097b1cb9fa49b4c14f2e6337724de1fdb13f2087cae6f2bdb19440ecbfa9`。保留全局结束原冻结包 e84e416f… 及其 macOS 60 项证据。组合版本 macOS **60/60**（285.36s）、Linux 干净构建 **60/60**（386.84s）均通过；Linux 仅在原性能进程正常结束并核对 PASS 后启动，远端目录和终态由 `../m5-global-finish/linux-inflight.json` 记录。

`prove_serial.py` 对实际被测紧凑候选的完整真实 SDF C++ 替换整个当前 runtime，未启用并行宏的 macOS 预处理结果逐字相同，SHA256 `3250ef4253fdf27b7cb208bfa7f1e64162f102721ae1d8a5ac2e86bbe667cb40`。最终 Linux 编译器也已实际重新生成全量 C++，与被测候选仅差整个并行宏内 runtime 新增；同机预处理结果逐字相同，SHA256 `f58efe4e164526fab7c415abbd99f909602f33c44e35e23d3486ecb3367e984a`。两个预处理器的平台输出不相互比较。完整程序保持 790,222 个 INTERCONNECT、867,982 个 IOPATH 和 86,496 个未关闭检查，23,051 个负 limit 更新仍按原非负模式夹零。原始输入在前后校验一致。

最终 `verification.json` **PASS，默认采用**。核对全部 414 当前源码、本地 856 个证据、原生普通/ASan 运行各 96 份完整波形、两端完整回归、Linux 全量生成的 12 个原始证据及配对改动身份。最终 macOS ASan/UBSan 的实际内核/96 原生捕获及 compact 延迟驱动均通过；无 Linux sanitizer 声明。全量证据包 SHA256 `ce2557a0acc7a5a3b457eea2a8ac51da4a4012557d90d01629d660168a873ded`。后续改变默认源码后，可用 `verify.py --source-root /tmp/dsim-compact-adopted-frozen-1018` 核对本冻结版本。整体 SDF 专用传播、普通 Verilog 自动并行、自动预测器及大波形索引继续推进。
