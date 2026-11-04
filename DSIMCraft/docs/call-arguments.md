# 子程序默认与命名实参

M63 新增[无尺寸数组 input/inout 值形参](open-arrays.md)，支持固定数组实参；动态分配与动态数组引用仍未接通。

M62 已支持 [const ref 只读引用](const-ref.md)，固定数组形参见 [M61](array-arguments.md)；后文相关未支持描述是历史边界，以新文档为准。

M61 新增[固定 unpacked 数组形参](array-arguments.md)，支持数组和动态前缀子数组的值传递及引用，默认/命名绑定继续沿用。

模块和 generate 词法作用域内的函数/任务支持 ANSI 默认形参、命名调用、位置参数后接命名参数，以及空位置和 `.name()` 使用默认值。经典形参声明可按名称调用，但不能声明默认值。RTL parser 与紧凑门级 parser 继续独立。

```systemverilog
integer base=7, result, copied;
function integer add(input integer x=base, input integer y=2,
                     output integer z=copied);
  begin z=x+y; return z; end
endfunction
initial begin
  result=add(.y(5));       // x=base，输出复制到 copied
  result=add(3, .y());     // y=2
end
```

绑定先于执行完成；无论命名实参书写顺序如何，求值按形参声明顺序进行。默认表达式在**子程序声明所在的外层作用域**解析，避免同名调用者局部变量改变含义。默认值不是声明时的快照：每次调用仅计算实际使用的默认输入/inout，显式覆盖的默认表达式不执行。默认 output 目标在返回时求地址并复制；默认 inout 在入口取值、返回复制。任务参数在入口取样，跨 delay 保持。函数结果在输出复制前捕获。

已有 signed、宽四态/两态、enum 和 packed 聚合转换、generate 克隆、部分目标与地址副作用、delay/NBA 单次求值、敏感依赖、共享状态分区以及检查点回放均沿用编译路径。单个拼接实参保留为一个表达式；连续空位置可分别绑定默认值。未知名称、重复/冲突绑定、名称后的位置参数、过多参数和没有默认值的省略参数报错。子程序允许混合调用不改变模块端口规则：模块连接仍禁止位置与名称混用，并检查重复名称。

启动对齐：先注册并挂接以事件控制开头的 always/always_ff 等待，再施加声明初值；initial 入口事件等待随普通进程启动时挂接。always_comb/always_latch 仍启动执行一次。新回归区分 X→1/0 初始化沿与后续实际沿；不是完整事件区域或任意前置控制流启动顺序的兼容证明。M29 原始传统 @* 差异探针另用新编译器重新运行，保留旧证据。

M31 已增加[非递归 automatic 调用](automatic-subroutines.md)和跨进程挂起隔离。M60 已支持[可写 ref](ref-arguments.md)。仍不支持 const ref、递归、常量函数、数组形参、任意动态并发重入、层次调用、package/interface 或完整验证语言。默认值类型/目标检查随实际使用路径执行，尚无对未使用默认值的完整声明期诊断。ANSI 相邻形参的隐式方向/类型继承并非本批新增范围。函数输出/双向参数继续要求过程表达式上下文。

验收：`ctest --test-dir build -R '^rtl_call_arguments$' --output-on-failure`。实际 VCS 同源比较、完整位时间线、回放及运行边界见 [M30](../validation/m30-call-arguments/README.md)。本批没有新的性能测量。

定向回归修复了负常量过程 delay 绕过显式拒绝、误进无符号运行时转换的路径。负常量 delay 继续属于未支持项；独立 VCS 探针将 `#(-1)` 视为零，本轮没有将该项计入兼容结果。
