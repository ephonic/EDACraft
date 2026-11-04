# 原始新增 memory cases

`sram`、`unrolled`、`banking` 的 DUT/TB/向量逐字节来自用户新增的 cases 归档，来源与 SHA 见 `origins.json`。不执行归档内脚本，不替换展开 TB，不调整原始 180 秒编译预算。运行结束必须分别得到 `SRAM_BRIDGE_PASS checked=4480`、`MEMORY_BATCH_PASS checked=3840`、`MEMORY_BANKING_PASS checked=640`，原始独立比较语句全量执行。

标量扩展仅支持常量零边界、宽度一，VCS 会为部分写法给出 INAV 警告；不代表完整标量选择兼容。大 initial 的检查还包含独立生成的 17000 次存储、前向分支与延迟，串行/time-wheel/真实双分区全波形比较及预算/检查点边界恢复。仍然循环或反复触发的过程须保留旧生成路径。

M146 将无回跳、只执行一次的 initial 分块门槛由 16384 降至 4096 条指令，覆盖原始 banking TB 的约 5500 条指令。继续保留所有既有保守条件和 256 指令分块，不对循环/反复触发过程禁用优化，不按设计名称选择路径。banking 的 16 个设计和 23040 次比较原样运行；这修复编译预算，未声称 runtime 加速。
