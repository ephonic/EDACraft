# 字符串键与类关联数组

RTL 前端支持一维 `int table[string]`、`logic [128:0] words[string]` 和 enum/class-handle 元素。类属性可以声明 int 或 string 键关联数组，实例独立拥有存储，继承后的属性仍由原对象持有。门级 parser 保持独立。

```systemverilog
class Store;
  int counts[string];
  function int total();
    int sum;
    foreach (counts[key]) sum += counts[key];
    return sum;
  endfunction
endclass
```

支持元素阻塞读写、packed 部分写、size/num/exists/delete 和 first/last/next/prev。string 键按无符号字节字典顺序排列，空字符串是有效键；游标失败保持原索引值。foreach 自动推导 string 索引，支持 `foreach (object.counts[key])`；循环使用独立有效标志，空键不会被当作终止值。函数/automatic task 的局部数组和循环状态隔离。

同键类型、兼容元素类型的数组可以整体赋值，包括独立变量和类属性之间。复制到两态元素时逐元素清除 X/Z。数组内容复制后独立，class-handle 元素仍共享所引用对象。缺失元素读取返回其类型默认值，不插入键。对象堆、关联数组和循环状态参加 checkpoint/预测恢复；修改通知接入现有调度依赖，涉及对象堆的过程保守放在同一分区。

非零八进制转义可用于字节键；动态 string 字面量中的嵌入 NUL 转义目前明确拒绝。

当前边界：仅一维 int/string 键；不支持通配索引、string/aggregate 元素、数组形参/返回、关联元素 ref 或 timed/NBA 赋值。游标实参限完整局部或静态 string/32 位整数变量，暂不支持类属性作为游标实参；类关联数组 reduction 尚未接通。类中的 queue、动态/固定 unpacked 数组仍是后续工作。动态元素和堆内部字段不直接导出为 VCD 声明，应使用 SV 观察量；已有用户指定波形范围与独立压缩线程继续适用。

这项功能补齐公开 UVM 的部分容器依赖，不能据此宣称完整 UVM 可运行。未修改的 Accellera 2020.3.1 包仍在 static 类方法处拒绝；约束随机、IPC、虚拟接口、clocking、覆盖率和 DPI 等继续补齐。
