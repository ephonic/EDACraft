# DWF1 压缩波形原型验证

2026-10-17，本机 Python 3.14.4 / `compression.zstd` / Icarus 捕获 VCD。代码与格式说明见 [dwf.py](../../experiments/waveform/dwf.py) 和 [设计](../../docs/waveform-format.md)。这是独立实验原型，尚未接入 dsim 原生仿真器，不更改 0.8.0 冻结的运行时、RTL 或门级前端。

已实现四态位平面、整向量专用码、变化 XOR、时间差和 ID 编码、独立熵压缩块、每块完整检查点、时间索引、CRC、VCD 双向转换和窗口查询。raw/DEFLATE/Zstandard 均有读取路径，压缩后更大则回退 raw。

| 捕获负载 | VCD 字节 | DWF+Zstd 字节 | VCD / DWF | Python 写入 MiB/s | 窗口查询中位数 ms | 最多读取块 / 总块 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 现有四态门级 seq_feedback | 130,292 | 8,051 | 16.18× | 1.91 | 4.14 | 1 / 7 |
| 生成 RTL，32 路 256 位活动数据 | 7,552,300 | 124,023 | 60.89× | 29.57 | 8.47 | 2 / 11 |
| 生成 RTL，2048 位稀疏更新 | 8,264,471 | 24,123 | 342.60× | 53.72 | 6.91 | 1 / 4 |

三种 codec 每组写入三次，4096 个事件一块，Zstd/DEFLATE level 3。MiB/s 的分子是输入 VCD 字节数，时间含 Python VCD 解析和文件写入；查询时间包含打开文件、读取字典/索引、检查点和解码，oracle 扫描在计时之外。使用热文件系统缓存，没有 fsync。没有测量原生仿真 overhead、峰值 RSS、生产设计、FST 或 VCS 波形速度。稀疏负载和移位相关的宽总线有很强冗余，不能把上述压缩比当作一般保证。

同一 VCD 直接整文件 Zstd(level 3) 的大小分别为 16,059 / 143,129 / 144,987 字节；这项基线没有时间索引、检查点或值解析，压缩时间单独记录，不与含 Python 解析的 DWF 吞吐混为一项。全部原始数据见 [results.json](measurements/results.json)，准确摘要见 [summary.json](summary.json)。

验证包括：

- 手写独立 VCD 的 X/Z、混合向量、同 ID 别名、层次/范围、dump 开关、comment、重复时间及同时间 0→1→0；每块 1/7/16384 事件，覆盖同一 tick 跨块。
- 独立整数生成的 1/2/7/8/9/64/65/256/1024 位四态事件，与三个 codec 全量回放及 VCD 往返比较，每种另测 80 个随机窗口。
- 截断、元数据/数据/索引 CRC 损坏、非法 varint、越宽数据、未知值流、倒退时间、real/event 拒绝和声明长度受限解压。
- 三个实际捕获的 VCD，对每个 codec 检查全部有序事件及导出 VCD 的语义等价，合计 270 个窗口查询；`analyze.py` 另逐个重放这 270 个查询，校验所有输入和原型源码 SHA256。

原始 capture.vcd、仿真源文件、Icarus 日志、三种 .dwf、导出 VCD、整文件压缩基线及版本记录均在 `measurements/`。`verify.log`、`benchmark.log`、`analysis.log` 均以 PASS 结束。压缩格式保留源 VCD 已记录的顺序，无法恢复 VCD 未捕获的 delta/事件区/毛刺。索引依赖正常关闭文件；百万信号检查点、选择信号跳读和半文件恢复仍为下一阶段工作。

复现：

```sh
python3 experiments/waveform/verify.py
python3 experiments/waveform/benchmark.py --output /tmp/dsim-waveform-repeat --repeat 3 --block-events 4096
python3 validation/m6-waveform/analyze.py
python3 experiments/waveform/dwf.py pack input.vcd output.dwf --codec zstd
python3 experiments/waveform/dwf.py unpack output.dwf restored.vcd
python3 experiments/waveform/dwf.py window output.dwf 100 110
```

Zstd 需要 Python 3.14 标准库；`--codec zlib` / `raw` 不依赖它。格式名称和字节布局仍可能变化，尚不承诺作为稳定交换格式。
