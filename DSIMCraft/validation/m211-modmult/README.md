# M211：103 modmult 三模式核对

实现冻结 `493cc75e53a4058a0a572de4c6135d7c15b7c04d`。RTL 与门级仍走独立 parser。本批修正显式源文件 filelist 的 `+libext+` 兼容、`-F` 内 SDF 路径，以及 SDF 路径输出在时间 0 多触发一次过程事件的问题。初始化路径驱动延后到所有电气连接建立之后、过程事件控制启动之前；普通/条件路径、generic/scalar/jobs/dictionary 共用，不修改正时间延迟和输入通道策略。

## 真实算例

原路径 `/home/yangfan/digi/cases/designs/modmult/mul` 已空。`prepare.py` 显式记录 RTL 到保留目录的映射，不改原测试平台。重新编译的 VCS RTL GOLDMODE 产生的全部文件与原 `golden.txt` 逐字一致。使用固定 VCS golden 的原版 CHKMODE，103 Intel dsim 已完成 128 笔比较、errors=0；新编译 VCS CHKMODE 同样通过。

独立 GOLDMODE 的双方自报 PASS 并不代表输入相同。原 TB 在同一拼接中多次调用会修改 LFSR 的无参数函数；本机 VCS W-2024.09 实测只调用一次，dsim 逐次调用，128 组输入和输出均不同。`function-probe.sv` 独立复现：同一拼接的三次调用，VCS count=1、dsim count=3；拆成独立语句后双方 count=3。本记录描述实测，不认定标准规定或其他 VCS 版本均应采用某一行为。

`portable-stimulus.py` 在独立目录加入循环生成 256 位刺激的函数，替换三个含重复调用的拼接，不改原 TB。该副本重新用两边工具编译执行，128 组输入和 128 组输出的完整 golden 逐字一致。它是修正刺激可移植性的独立实验，不冒充原 TB 的 GOLDMODE 已逐字对齐。

门级、SDF 的原有 VCS 二进制各通过 128 笔。完整 SDF 的 300,910 个 CELL、1,744,700 条记录全部解析通过，包括 867,982 IOPATH、790,222 INTERCONNECT 和 86,496 条检查；这是 parser 验收，尚非 dsim 全量定时仿真。原网表 31,596,843 字节、SHA256 `97a77a063064713f509620334561221a8061bf414669259b8861752721572ad9` 未找到，其他候选网表不同，未替代原输入。原 SDF_SIM TB 的 `$sdf_annotate` 仍遇到 module namespace 参数错误；CLI 注解已有实现，系统任务自动接入尚待补齐。因此本批总体状态保持 PARTIAL。

## 验证与发布

新 VCS 十二转换微例确认旧版多出的 `TRACE t=0 z=x`，修正后的完整 top.A/top.Z 物理波形与新编译 VCS 一致。本地七组 SDF 场景、预处理/SDF CLI、路径集成及路径回滚/提交，共 11 项 CTest 全部通过。四种后端的实际生成程序及失败预测恢复经过 ASan/UBSan，所有值、时间和完整解码记录一致；初次控制程序少了 105/250 的观察边界，失败记录保留，确认全部值记录相同后用相同边界的控制程序重测通过。

Linux 已通过完整 11 场景 SDF 路径基线与候选发布的 parser/格式/原生 DB、预处理、gate_source 检查。四种后端和失败预测的 8 次完整捕获也已通过，生成 C++ 与 Mac 对应的四份相同，八份完整解码波形跨端相同。SDF CLI 的首次 Python 3.9 测试因 Path.hardlink_to 不存在而失败，保留原日志；使用已有 Python 3.13 执行相同冻结脚本和断言后通过，未改仿真器或降低检查。最初重复全部平台矩阵的长任务显式取消，已通过子例及取消进程的 PID/start 身份保留在 `scope-selection.json`，未完成的整组不计 PASS。Linux 不宣称运行了 ASan/UBSan。实际更新后的 103 稳定入口重新编译原版 RTL CHKMODE，128 笔、errors=0；完整原 SDF 再次解析并与先前 JSON 相同。验收状态见 `focused-acceptance.json`、`final.json` 和最终发布收据。

发布输入 1497 项，SHA256 `a17864b11901d483b6b7ea7682a42e0381ba5d6ba1661034ce90f827f32eb414`，两端完全相同。首次本地候选在检出完成前启动，git_dirty=true，激活检查拒绝，记录保留；干净的固定工作区重新构建后已更新 Mac 稳定入口，并从真实入口编译执行带 `-F`/`+libext+` 的 SDF 模型。103 的同源 Intel 稳定版本 `20261101T081820785299Z-a17864b11901` 也已激活，根目录和 bin 两入口重新生成代码相同，实际入口编译运行完整 TRACE/输出时间线通过。

完整原始日志、生成 C++ 和波形外置于 `~/vibe-coding/dsim-test/evidence/m211-modmult`；仓库保留执行脚本、结果摘要和哈希。单次 `/usr/bin/time` 原始记录不作为速度对比，特别不使用不同 GOLDMODE 刺激的运行时间相除。

运行与结果对应：`prepare.py`/`report.py` 核对实际设计；`portable-stimulus.py` 和 `function-probe.sv` 隔离刺激差异；`sanitize.py` 检查真实生成后端；`resume-acceptance.py` 保留 Python 版本恢复过程；`activate.py` 负责入口验收失败时恢复旧链接。`modmult.json` 的总体 PARTIAL 与单项 PASS 有不同边界，不能将 parser、保留 VCS 程序或微例通过当作完整门级/SDF 已通过。

双端外置证据目录、完整清单 SHA256 和文件数见 `archives.json`；其中 Mac 为定向矩阵/消毒及跨端捕获，Linux 为实际设计、Intel 四后端、实际安装入口和完整 SDF 原始输入。清单不将未完成的宽矩阵记为通过。
