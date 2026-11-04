# Testbench 控制波形

RTL testbench 现可调用 `$dumpfile`、`$dumpvars`、`$dumpoff`、`$dumpon` 和 `$dumpall`。预处理后的真实任务 token 自动启用 native 波形后端，无需显式传 `--wave-support`；字符串、注释及仅包含相同拼写的普通/转义标识符不触发启用。构建需要 libzstd。RTL 与门级结构 parser 仍分开。

```verilog
initial begin
  $dumpfile("run.vcd");
  $dumpvars(0, top.dut);
  #100 $dumpoff;
  #20  $dumpon;
  #10  $dumpall;
end
```

`$dumpvars(depth, targets...)` 支持已展开模块作用域和完整信号；相对名称从调用作用域向上解析，绝对名称从顶层解析。转义标识符的点保留在同一组件中。depth=0 表示所有下层，depth=1 仅所选层；信号目标不扩展到其他声明。depth 可为不超过64位的无符号表达式，运行时必须为已知的0..10000。无参数/空括号选择整个顶层；只有depth时也以顶层为起点。未知目标、选位/部分选、表达式目标、错误参数数目和空文件名明确拒绝。

首次选择同刻的多个 `$dumpvars` 合并；后续时刻的追加选择忽略。`$dumpfile` 接受常量字符串，首次捕获建立后修改文件名忽略；单独调用不创建文件，缺省文件名为 `verilog.dump`。已有文件受到保护。显式运行参数 `--waveform PATH` 优先于 testbench 文件名。

任务默认输出 VCD，默认采用 settled 模式。相同任务可直接生成压缩格式：

```sh
dsim top.v -o simv
./simv --waveform run.dwf --wave-format dwf --wave-compression-jobs 4
./simv --waveform ordered.dwf --wave-format dwf --wave-mode ordered
```

两种格式复用相同选择、控制和采样流；DWF 保持既有四态平面/XOR、块 Zstd、CRC、检查点/索引及有界异步压缩。ordered 模式从首次调用的实际值开始，保留其后同刻的所有实际值变化；首次同刻的声明集合在时间槽结束时确定，该时间槽的 ordered 变化暂存在内存中。settled 模式合并每个时间槽的变化。百万信号下首次时间槽缓存的进一步分组/限额仍待扩展。

`$dumpoff/$dumpon/$dumpall` 在时间槽结束时写控制/快照，首次选择前忽略。当前兼容 VCS W-2024.09 探针观察到的缺省策略：dumpoff 只将标量流写为X，向量保留；同刻 off/on/off 不写控制并继续记录。每种控制在同刻至多请求一次，相反请求取消未写出的控制。这是已测试行为，其他同刻控制排列还需要扩大参考覆盖。

文件创建、选择、控制、值及时间槽通知使用同一事务提交顺序。请求捕获调用时的时间及已求值参数；提交时使用已提交值历史，不读取已经推进到未来的 `Sim` 状态。预测成功后写出；预测失败时丢弃请求和值，校正重放后写出。该接入不代表普通 RTL 自动预测或自动并行已完成。

VCS 对照范围为16组原始 testbench、各三次运行，参考包含完整物理位历史及控制记录。native 默认捕获已通过这批219个物理位历史及控制记录对照。ordered VCD/DWF 在 native 间比较全部事件；**未证明与 VCS 的同刻瞬态顺序完全等价**：VCS 可能在首次/恢复捕获时暴露优化求值的中间值。`$dumpflush/$dumplimit`、动态文件名、数组/生成层次目标等仍未接通。467冻结源本地任务捕获及Linux完整110项、148跨平台捕获已独立验收通过，见[验证记录](../validation/m6-dump-tasks/README.md)。本批不包含压缩吞吐或仿真加速测量。
