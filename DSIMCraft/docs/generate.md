# RTL generate

RTL 前端消费 parser 第二遍已经选定的分支和循环副本，建立独立的词法作用域，再生成普通信号、连续驱动、原语、过程和模块连接。门级网表仍使用独立的结构 parser，没有把大网表送入 RTL parser。

支持显式 `generate/endgenerate` 及模块级隐式 generate；常量 `if/else if/else`、`case`（多标签/default）、命名/普通块、带 `begin/end` 的 `for`；外部声明和头部声明的 genvar、嵌套循环、正向/倒序及非单位步长、零次迭代和空体。局部 wire/reg/logic、参数/localparam、逐迭代 genvar 快照及词法遮蔽进入同一展开流程；块中的语句仍受各自已有语言限制。

```verilog
module lanes #(parameter N=4)(input [N*8-1:0] a,
                              output [N*8-1:0] y);
  for (genvar i=0; i<N; i=i+1) begin: lane
    localparam [7:0] K=i;
    assign y[i*8+:8]=a[i*8+:8]^K;
  end
endmodule
```

同一个局部声明在不同循环副本中具有不同信号 ID。嵌套块可以读写所在模块的外层信号；子模块仍有自己的词法边界。参数化子模块、延迟过程/连续赋值、隐式敏感列表、并行依赖、VCD/DWF 层次和检查点使用展开后的信号与过程。无需在运行时解释 generate 循环。直接嵌套的条件链不会额外增加一层 genblk。

修复了旧 parser 的循环副本共用符号表、默认 case 分支遗漏作用域、匿名块遗漏词法作用域、inline genvar 未注册及空循环体处理问题。常量关系运算改为按共同宽度和双方符号属性比较，避免用减法进位判断大小；无尺寸十进制零恢复 signed 属性，genvar 保持 signed 整数。独立数值用例覆盖 8/32/65 位、负数/零边界、混合符号及 X。

范围仍有限：

- 条件/循环判定须为已知常量；每个循环最多展开 100,000 次，重复 genvar 值提前诊断。
- 循环头使用赋值表达式，例如 `i=i+1`；尚无 `i++`、`i+=1` 或无 `begin/end` 的循环体支持。
- 信号范围仍要求 descending packed，unpacked 数组和完整运行时 signed 运算仍未支持。生成负索引的块名可展开，不代表其负常量在所有表达式中可用。
- 普通隐式 `genblkN` 名称已覆盖，显式名字与隐式名字冲突时的完整 IEEE 消歧命名尚未覆盖；跨 generate/模块的显式层次表达式引用仍有限制。
- 不包含 generate 内函数/任务、接口、class、UDP 或完整 SV 支持；结构门级 parser 的语言范围没有扩大。

验收：三组真实编译设计，串行/时间轮/双线程，ordered/settled 的 VCD/DWF 共 38 捕获、两类实际失败预测回放、6 类诊断。嵌套宽四态输出有独立整数/位级预期；IR 检查各副本参数、选中分支和层次。实际 VCS 三例的全部 907 条物理位时间线相同。VCS 将 generate 名字压在 VCD 名称中，比较器仅对这三组无转义名字的设计连接层次组件，要求双向名字集合相等，不丢弃信号或时间点。同源 Linux 四项定向回归通过；三组完整 serial CPP 与本地相同，实际 GCC 程序也通过同样 907 物理位对照。macOS parser 单测及三设计重复解析经 ASan/UBSan 通过，非 Linux sanitizer。记录见 [本批验收](../validation/m10-generate/README.md)。
