# 并行全局结束与事务窗口

本批在独立 Sim 的保守并行 API 中实现显式 `enable_global_finish()`。worker 窗口内的打印、解析通知与原生波形先缓冲；发现结束后按 `(tick, partition ID)` 选择边界，回滚并重放有效前缀，只提交结束前效果。较晚的推测异常随其窗口丢弃，较早的异常报错；外部 sink 部分提交失败不重放。默认保守模式继续拒绝 local finish，不承担完整窗口检查点开销。

生产修改限于 `include/dsim/runtime.hpp` 的并行宏内事务接口和 `include/dsim/parallel.hpp` 的协调协议。普通 Verilog 编译器、RTL/gate parser、SDF parser 和原生波形格式未改；自动 Verilog 并行代码生成、全局波形合并和 Time Warp 未完成。API 顺序由物理分区 ID 定义，有竞争的模型不能假定改变分区后保持任意串行调度等价。

冻结包 `/tmp/dsim-global-finish-source.tar.gz`，414 文件，SHA256 `e84e416fd874611e06ddcfe6a401a895585e60a776b688fa4c4a112354078783`。`source.json` 和 `changes.json` 记录逐文件身份及相对上一批 411 文件的改动。

macOS 构建及完整回归 **60/60** 通过（228.89s）；新增测试包括 360 组独立预期的结束时间线、1/2/4 worker、不同窗口、同刻/零时刻结束、正延迟通道、注册状态、token 生命周期与异常先后。实际原生波形 96 份，ordered/settled × VCD/raw DWF/Zstd DWF，与独立串行内核按结束边界执行的完整输出及逐事件波形一致。最终实际单元及原生 96 捕获 ASan/UBSan 通过，单元 TSan 通过；不是 Linux sanitizer 结论。原生捕获已独立保存在 `macos-wave/`，687 个本地证据文件由 `local-evidence-manifest.json` 校验，后续可继续复用根 build 目录。

`prove_serial.py` 对上一批真实完整 SDF 生成程序整体替换旧/新 runtime，并按编译器规则展开 wide 头；未开启并行宏时完整 C++ 预处理结果逐字相同，SHA256 `bf26e8623319a0d7b4ce6d2c4ff9833c1cf760cca978c221348e5076f09a935b`。该证据说明本冻结版本不改变默认串行完整 SDF 执行代码，不代表全局结束模式有性能收益。

Linux 干净构建及完整回归已完成 **60/60**（386.84s）。执行的是独立复测通过后接入紧凑接收端的组合源码 9798097b…；相对上述 e84e416f… 原冻结版只变更延迟驱动注册和接收端创建，未覆盖或改写全局结束逻辑。组合版 macOS 也已 **60/60**（285.36s），其原始证据单独保存在 `../m5-compact-adoption/`。因此本目录初始 macOS 与最终 Linux 的源身份分别记录，不能称两者都是 e84e416f…；当前默认两端同源验收见接入目录。

`verification.json` 已 PASS，核对初始 414 文件、本地 687 个证据、Linux 178 个原始证据、三组实际原生捕获各 96 份及默认串行执行身份。Linux 原始证据包 SHA256 `b79855f28ea0d73bb25b8a06a3679f44dace8c20e8dc2e36dcc3c25354c661a9`。核对历史版本可运行 `verify.py --source-root /tmp/dsim-global-finish-frozen-1018 --integrated-source-json ../m5-compact-adoption/source.json --integrated-source-root /tmp/dsim-compact-adopted-frozen-1018`。所有 Linux 构建/回归均在原性能进程正常结束后开始。

首次测试计数器把输入通道变化计入自身变化，以及首次波形测试使用错误 NBA API，均已修正并保留初始失败日志；最终完整回归和 sanitizer 使用修正后的源码。全局波形合并、普通 Verilog 自动并行编译接入及乐观反消息仍未完成。
