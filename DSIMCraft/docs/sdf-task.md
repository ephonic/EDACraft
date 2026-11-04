# 静态 `$sdf_annotate`

M212 将 RTL 中的静态时间 0 注解接到现有 SDF 绑定器和门级定时后端。RTL、结构网表和 specify 元数据继续使用各自的 parser。只接受一个已展开的结构网表根实例；不把放行实例语法等同于完成定时注解。

```verilog
initial begin
  $display("annotating");
  $sdf_annotate("delay.sdf", dut, , "annotation.json", "TYPICAL");
end
```

```sh
dsim --gate-netlist net.v --gate-top design --liberty cells.lib \
     --gate-models cells.v tb.sv -o simv
./simv
```

`dut` 是 TB 中类型为 `design` 的实例，可以使用相对层次名，例如 `wrapper.dut`。文件名和文本选项必须是字符串字面值或可在展开时求值的字符串参数。空的可选实参会保留位置。第五参数支持 `MINIMUM`、`TYPICAL`、`MAXIMUM`、`TOOL_CONTROL` 或空串；后两者沿用 `--sdf-corner`，默认 typ。显式 `--gate-model-corner` 继续独立选择未被 SDF 更新的 specify 初始值。

SDF 在编译时静态绑定，文件路径相对编译命令的工作目录。第四参数的日志在实际执行该语句时写出，内容为注解表 JSON；其路径也在编译时固定。日志产生文件 I/O 状态，遵循其他 I/O 过程的预测限制。SDF 文件加入 `--emit-deps`；编译器输出和日志不得覆盖任何已知输入，符号链接、硬链接也做相同检查。预处理和依赖文件在注解校验完成后才写出。

第三参数是配置文件，不是日志。103 的 VCS W-2024.09 对不存在的第三参数接受并完成默认注解；dsim 对这个场景显式提示后使用默认注解。真实存在的配置文件尚未实现，会拒绝，不会忽略其内容。VCS 对第四参数使用字符串参数的一个初始测试夹具报 IAFSDFA，最终共享测试使用日志字面值；未将此夹具计为两端通过。

当前支持 initial 的无条件、未挂起前缀：顺序 begin/end、普通赋值和 display/write 可位于注解之前。条件、循环、task 调用、fork、wait、延迟（包括 `#0`）、always/final 中的注解不支持。遇到这些调用明确报错，不会提前执行或当作空操作。未展开的 generate 分支不参与注解。

目前还不支持多次重注解、一个结构设计的多个实例使用独立定时表、从 TB 默认作用域注解整个层次、scale_factors/scale_type 和真实配置文件。不能混用源任务和 `--sdf-annotate`。这些限制以及原有 SDF/Liberty 支持边界仍然生效；不是完整 VCS/SDF 兼容声明。
