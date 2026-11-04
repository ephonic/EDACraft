# 复合赋值与子程序 return

支持过程语句和 `for` 初始化/迭代列表中的 `+=`、`-=`、`*=`、`/=`、`%=`、`&=`、`|=`、`^=`、`<<=`、`>>=`、`<<<=`、`>>>=`。右侧沿用现有四态算术、signed/unsigned 共同类型、上下文位宽和赋值截断；算术右移使用目标表达式的 signed 属性。普通 packed 变量、常量/动态位选、固定宽度部分选择、一维数组字/字内选择及拼接左值均可使用。

```verilog
reg signed [79:0] total = -80'sd17;
integer i;
initial begin
  for (i = 0; i < 5; i += 1) begin
    #1;
    total += i;
  end
  total >>>= 2;
end
```

读改写的动态数组地址和 packed 选择基址在执行入口保存，读和写复用同一个值。索引中的用户函数只执行一次；语句 `++/--` 也使用这条路径。未知或越界目标沿用现有数组不写入、packed 选择局部裁剪规则。选择后的值为 unsigned；完整 signed 数组字保留其 signed 属性。

静态用户函数和任务支持 `return`。函数 `return expression;` 按返回变量声明转换宽度和符号，再退出本次调用；裸 `return;` 保留当前返回变量值（实际 VCS 接受但给出省略表达式警告）。任务只支持裸 `return;`，仍执行 output/inout 的返回复制。嵌套调用的 return 只退出当前子程序，可以从循环、case 和条件内部退出；任务可以在 delay/event 恢复后返回。已经排定的 NBA 和延迟 NBA 继续交付。

```verilog
function integer find(input integer n);
  begin
    for (int i = 0; i < 8; i += 1)
      if (i == n) return i * 3;
    return -1;
  end
endfunction

task update(output integer result);
  begin
    #2;
    result = find(3);
    return;
    result = 99; // 不执行
  end
endtask
```

编译器把 return 降为已有 PC 跳转，任务出口位于形参复制之前，函数出口位于返回值读取之前；没有新增运行时 AST 解释器。复合赋值/return 接入现有进程依赖、独立域自动并行、VCD/DWF 和检查点/失败回放。RTL parser 新节点支持参数化模块/generate 克隆与语义绑定，门级紧凑 parser 不变。

仍不支持：把复合赋值作为带返回值的表达式、复合赋值自身的内部 delay/NBA 形式、非恒定部分选择宽度、return 退出普通 initial/always、任务 return 携带表达式，以及 automatic/递归/常量函数/void/ref 等完整子程序语义。不能把本批范围视为完整 SystemVerilog 兼容；其他子程序边界见 [subroutines.md](subroutines.md)。

验证入口：

```sh
ctest --test-dir build -R '^rtl_procedural_actions$' --output-on-failure
python3 validation/m16-procedural-actions/verify.py
```

实际验证覆盖全部十二种运算符、宽 signed/四态、单次求值的动态目标、三种提前返回位置、任务嵌套/事件等待/NBA、参数化 generate、真实两分区、两组失败回放；范围和原始证据见 [M16](../validation/m16-procedural-actions/README.md)。本批没有新的速度测量。

后继批次已支持前置/后置 `++/--` 的[表达式结果](increment-expressions.md)。

M49 补齐[阻塞赋值内部事件控制及 repeat](intra-event-assignments.md)，复用现有取样值、循环计数和事件等待生成路径；非阻塞内部事件及复合赋值时间控制仍缺。
