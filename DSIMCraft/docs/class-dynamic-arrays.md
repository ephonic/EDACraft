# 类动态数组

M208 支持类属性的一维整数、packed、字符串与已有结构元素动态存储。每个对象独立保存数组，支持默认空数组、构造函数内分配、`new[N]`、`new[N](source)`、整体值复制、`size()`、`delete()`、`foreach`、元素与 packed 选择读写。下标沿既有类队列路径转换为 32 位整数，VCS 对照包含宽下标截断；转换后的越界写不追加元素。动态数组状态和对象随机流随 checkpoint 恢复。

```systemverilog
class Packet;
  rand byte unsigned data[];
  rand int count;
  constraint legal {
    data.size() inside {[2:8]};
    count == data.size();
    foreach (data[i]) data[i] == i + 10;
  }
endclass
```

随机一维整数动态数组接入 Z3。先处理数组外的长度约束，再固定求得长度并联合求解标量与数组元素；foreach 内的长度作为状态。这个顺序参考 [Accellera 约束语义](https://www.accellera.org/images/eda/sv-ec/att-1295/01-Constraints.pdf)。未启用长度约束时保留当前长度；长度阶段不提前写回标量。支持多个长度关联、整数符号元素下标、合法枚举域及常量 packed 选择。

支持继承与实际派生类型、内联约束、具名 randomize 属性列表、randomize(null)、rand_mode/constraint_mode、前后回调。任一阶段 UNSAT 返回 0，不写随机字段或数组，也不执行 post_randomize；pre_randomize 的普通副作用保留。长度必须在 0 到 1048576 内。

M209 已进一步接通[类句柄动态数组及随机队列](class-handle-arrays.md)。目前不支持 randc 数组、动态实数数组、类内固定/多维数组、std::randomize 数组、数组 reduction/locator 的符号求解、同一约束原子内混合长度与随机元素、数组 ref 及 timed/NBA 元素写。M209 已补类动态整数/packed 容器的系统查询；约束内仍用 size()。有未知位的实际约束状态继续明确报错。符号下标选择未知状态数组可能保守地诊断其他元素的未知位。

本批未宣称完整 UVM：原始 Accellera UVM 2020.3.1 的首个阻塞推进到 `uvm_tlm2_generic_payload.svh:372` 的 `local rand uvm_tlm_extension_base m_rand_exts[]`，需要随机对象图能力。验收脚本和记录见 [M208](../validation/m208-class-dynamic-arrays/README.md)。
