# SDF 标量延迟交付后端

`--gate-scalar-timing` 是实验性编译选项，要求同时指定 `--sdf-annotate` 和功能门级仿真输入。默认关闭；仅完成存储/语义验证不构成默认采用或提速结论。

```sh
build/dsim --gate-netlist net.v --gate-top dut --liberty cells.lib \
  --gate-models models.v --sdf-annotate design.sdf --gate-scalar-timing tb.v -o simv
```

开启时生成 `DSIM_SCALAR_TIMING_ENABLED`，IR 中记录 `scalar_timing: true`。一位延迟通道只保存输入/已提交输出的四态编码与原有取消代际，交付槽保存通道、代际和标量载荷，不为每个通道/交付槽存放完整 `V`。宽向量通道使用独立的通用值表；向量交付载荷有自己的可复用值池，消费或惰性清除失效事件时归还。所有事件继续共用原来的定时堆、顺序号和 Active FIFO，槽位总数/ID 编码不变。

INTERCONNECT 和 IOPATH handler 使用 `get_scalar` 与 `drive_scalar_after`。接口编码与 `V::bit(0)` 一致：0/1/X/Z 为 0/1/2/3；它与 compact 槽内部的位平面编码不同，内核在发布处转换。路径选择仍在原来的路径进程位置读取输入时间戳，未提前到单元求值处。固定等待、过程数量、事件预算及取消策略不变。

一位 compact 目标只有一个驱动、且连接已建立时，交付直接进入原来的 `publish_compact`；别名、多驱动和通用 net 继续走原解析接口。路径戳、逐变化时序检查、波形和跨分区通知仍由同一发布路径产生。`Sim` 检查点同时复制标量记录、向量表、交付池和空闲槽，因此局部预测和全局结束窗口可恢复未提交事件。没有新增自动预测器或普通 Verilog 自动并行。

显式 C++ `drive_after` 接口仍接受通用 `V`，一位通道自动使用标量记录，宽通道保留原尺寸转换。新的 `get_scalar` 要求一位信号，`drive_scalar_after` 要求一位通道和合法四态码；二者只在上述宏下提供，且该宏要求 `DSIM_TIMING_ENABLED`。相同输入请求仍不推迟已有事件，零延迟仍异步进入 Active，返回该驱动自身的已提交值仍取消待提交脉冲。

可与 `--gate-batch` 组合，仍为单线程执行。SDF parser、RTL/gate 两套 parser、时间精度、模型和波形格式均未改。性能验收须使用完整原始 SDF、同核交替样本和全部输出核对；不能沿用上一批紧凑接收端的 10.20% 作为本后端收益。证据与当前进度见 [验证记录](../validation/m5-scalar-timing/README.md)。
