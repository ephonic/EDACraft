# 集合匹配、通配相等与 case inside

M35 增加 [unique/unique0/priority 限定及检查](selection-checks.md)，包含 case inside；此前未实现限定符的说明属于 M32 当时范围。当前诊断语义及 VCS 差异以该说明为准。

M34 已扩展到[静态多维 unpacked 变量数组](multidim-arrays.md)。下文原有单维示例继续适用；当前多维范围和限制以该文档为准。

支持整数和 packed 值的 `inside`、`==?` / `!=?` 以及 `case (selector) inside`。RTL parser 独立扩展，紧凑门级 parser 不改；生成程序直接执行 C++，不遍历 AST。

```systemverilog
logic [7:0] opcode;
integer allowed[0:2];
logic hit;
always_comb hit=opcode inside {8'b10??_0001,[8'h20:8'h2f],allowed};
initial begin
  case (opcode) inside
    [8'h10:8'h1f],8'h80: $display("first group");
    8'b11??_????:       $display("second group");
    default:           $display("other");
  endcase
end
```

`==?` 只把右侧 X/Z/? 位作为通配，左侧未被通配遮盖的 X/Z 可能产生 X；确定不匹配的已知位优先决定 0。`!=?` 对 0/1 结果取反，X 仍是 X。支持 64 位以内及已有多字四态位宽。

`inside` 左值只取样一次，右侧支持单值、动态闭区间和现有单维 unpacked 变量数组；数组展开为成员并计入完整读取依赖。整个集合共同决定比较位宽及符号，而非逐项各自决定。标量成员按不对称通配比较；范围按 `>=` 和 `<=` 的四态结果求与，各成员结果求或；真匹配可提前结束。已知反向范围不匹配，未知比较仍可能产生 X，本批保留实际 VCS 的该行为。值/范围的求值顺序在语言中未指定，实现选用左到右；不宣称不同工具对有副作用的集合成员有统一顺序。

`case inside` 选择表达式只取样一次，按分支顺序执行第一个结果为 1 的分支，0/X 都不命中，支持 default 和多个标签/范围。比较上下文包含全部分支标签；保留普通 case/casez/casex 原行为。函数内 case inside、普通立即断言、短路/条件表达式、默认实参、delay/NBA 单次取样、always_comb 依赖和分区均沿用现有编译路径。

常量 inside/通配比较接入 parameter/localparam、范围/尺寸查询和 generate 条件；结果自定宽1位且 unsigned，外部宽上下文不扩散到其操作数。无符号/有符号混合、未定宽填充值和130位值经过实际 VCS 对照。generate for 的头部仍采用原先支持的 `g=g+1` 形式。

边界：未实现非整数/运行时 string 集合、开放 `$` 范围、复杂/动态/多维数组、一般数组形参、tagged pattern、unique/priority 限定 case 和约束随机化。空集合、错误范围、casez inside 等未支持结构被明确拒绝；不把本批算作完整 SystemVerilog 验证语言支持。

验收入口：`ctest --test-dir build -R '^rtl_set_membership$' --output-on-failure`。六组共同输入覆盖256组两位四态穷举、范围/数组/多字、常量展开、函数分支、敏感依赖、延时取样、双线程和失败预测回放；实际 VCS 全部968条导出物理位时间线一致。VCS 未导出的三个数组字（96位）另用逐时刻独立预期及全后端/格式对照核验，不计入VCS一致位数；无名称映射。证据见 [M32](../validation/m32-set-membership/README.md)。本批没有新的性能测量。
