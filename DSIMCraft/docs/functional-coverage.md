# 功能覆盖率

M199 根据 REPORT-GAP6 增加真实 covergroup 采样。RTL parser 生成保留作用域与克隆所有权的 AST，编译器生成采样表达式和事件等待代码；命中计数、实例句柄和采样开关归 Sim 所有，随 checkpoint 恢复。RTL 与门级 parser 仍独立。

```systemverilog
bit clk, valid;
bit [3:0] opcode;
covergroup cg @(posedge clk);
  option.per_instance = 1;
  op: coverpoint opcode iff (valid) {
    bins low = {[0:7]};
    bins high = {[8:15]};
  }
endgroup
cg coverage;
initial begin
  coverage = new();
  // 也可声明无事件 covergroup 并显式调用 coverage.sample()。
end
```

支持模块级 covergroup、类内嵌 covergroup 的显式 sample()、无参数构造、类字段（含 this.field）、参数化作用域克隆、句柄别名、start/stop/set_inst_name。覆盖点为至多 32 位的 packed integral 表达式，可用标量/区间 bins、bins[]、自动 bins、稀疏枚举自动 bins、default/ignore_bins/illegal_bins、coverpoint iff。自动 cross 支持命名覆盖点、iff、命中阈值及权重；default/排除 bins 不参与覆盖率分母。单个展开 bins 或自动 cross 限制 65536 项，超限明确报错。非法 bin 命中在 dsim 中终止并报告错误。

covergroup、命名 coverpoint 和 cross 均可查询 get_coverage()/get_inst_coverage()。同源 VCS W-2024.09 探针用于核对类型计数累加、per_instance、at_least、weight、goal 与 NBA 同拍采样：get_coverage 合并同一运行时类型的命中计数，未开启 per_instance 时实例查询返回 0；goal 不缩放查询值。当前 goal/merge_instances 保留为元数据，尚无覆盖率数据库报告或全局 $get_coverage 聚合。

事件采样目前支持模块级的单一标量 posedge/negedge；`--threads` 在存在 covergroup 时采用单分区执行。串行、时间轮、线程请求入口、VCD/同步与异步压缩波形、计数回滚/提交通过独立回归。

仍缺：带参数构造/with function sample、ref 采样参数、类内嵌事件采样、动态 option 赋值、bin-level iff、定长 bin 数组、transition/wildcard/XZ bins、binsof/intersect 等自定义 cross、strobe/复杂采样事件、宽于 32 位的覆盖点、查询的输出计数参数、覆盖数据库导出及全局覆盖率 API。未实现形式明确拒绝，不表示完整 IEEE 功能覆盖率或完整 UVM。未修改公开 UVM 仍阻塞于静态单例 handle/null 常量求值。

回归：`python3 tests/coverage/regression.py build/dsim /tmp/dsim-coverage build/CMakeCache.txt`。冻结验收与 VCS/消毒器证据见 [M199](../validation/m199-functional-coverage/README.md)。
