# 约束 foreach 与类内队列

约束 `foreach` 使用独立 AST、隐式只读索引和词法作用域，生成求解表达式，不生成过程调度 PC。每次 `randomize` 在 `pre_randomize` 后按当前容器内容构造合取；空容器产生真约束。命名约束模式、内联约束、`randomize(null)`、失败时保留随机字段及 checkpoint 沿用既有随机化链路。

```systemverilog
class Region;
  int unsigned first, last;
endclass
class Policy;
  rand bit [7:0] start;
  Region in_use[$];
  constraint no_overlap {
    foreach (in_use[i]) !(start <= in_use[i].last && start+3 >= in_use[i].first);
  }
endclass
```

本轮支持遍历状态数组：模块/过程作用域中的固定未打包数组、动态数组和队列，以及已有整数/字符串键关联数组、类内关联数组和新增的类内队列。固定维度保留上下界方向，支持省略索引；嵌套循环允许同名索引遮蔽。索引绑定、参数化类特化和重复清理都有独立检查。

类内队列使用对象堆中的独立 vector 存储，复制 Sim 时随堆一起保存、恢复；队列修改通过堆依赖信号通知调度器。支持构造初始化、继承、元素/packed 子选择、`$`、有界队列、值复制、push/pop/insert/delete、size 和过程 foreach；不同对象的队列独立，同一句柄的别名共享队列。普通队列与类内队列共用元素更新逻辑。

M208 新增[类动态数组](class-dynamic-arrays.md)的 size/元素求解和符号元素下标。当前边界：随机对象图；类内固定数组、嵌套容器、packed 维度 foreach、类内队列的完整 ref/方法集合及 timed/NBA 元素写入仍有限制。不能将这部分进展解释为完整 UVM 支持。M183 已进一步补齐[编译单元级类与 typedef](compilation-types.md)，未修改 UVM smoke 当前首错进入 chandle 语义分析；完整库仍未展开运行。

复现与本轮验证见 [M182](../validation/m182-constraint-foreach/README.md)。
