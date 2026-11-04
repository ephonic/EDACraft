# Package/import 支持范围

支持 package 声明与可选匹配的 endpackage 标签；包有独立、共享的符号表，不参与 top 推断，也不会按模块实例复制。RTL 与门级 parser 保持分开。

- 包内共享可变变量（M83，默认 static 生命周期）、parameter/localparam、现有 integral/enum/packed struct/packed union typedef、typedef 别名、task/function。
- 模块、generate 声明区和过程声明区的 `import p::*`、`import p::name`，以及逗号分隔的多项 import。
- M133：模块和 interface 名称后的多条 header import，在参数默认值和端口类型之前绑定；支持参数覆盖、ANSI/non-ANSI、generate/重复实例。导入独立属于每个实例，包内可变存储仍共享。普通模块端口可使用现有 integral/enum/packed aggregate typedef，包含 grouped identifiers、限定包名及显式 `var` 的已有类型子集。
- M134：包作用域的 `export p::name`、`export p::*`、`export *::*`，支持列表、重复导出、导出先于 import、多层/菱形导出。保持原声明身份：typedef 属性、包函数词法环境、共享变量/固定数组及任务/NBA 使用同一底层对象。显式导出按直接 import 规则选择指定包；通配导出只转出已经实际导入的名称，不转出未引用的候选。Verilog 模式仍允许 `export` 作为标识符。
- `p::name` 的类型、常量、enum literal、可变变量/固定数组读写、函数表达式和任务调用；支持作用域分隔符周围空白。
- 首次使用时绑定通配导入。同名通配候选冲突时拒绝；本地声明可遮蔽尚未使用的候选；已经绑定的名称不能被后续声明重新定义。显式导入的重复同一符号有效，不同符号冲突时拒绝。
- 包函数按包的词法环境解析，不捕获调用模块中的同名参数或函数。包内静态 subroutine 的局部存储跨模块实例共享；automatic 调用复用已有独立激活帧、引用参数和分区依赖。
- 包的 `timescale` 同时决定其 task 延迟和全局最低精度，支持较模块更细的包精度。复用现有事件、NBA、checkpoint 和回滚，不增加运行时状态。

报告原始 t03（枚举、import、double 函数）保持源文件内容执行。其 `integer x` 省略 input 的首组 ANSI 形参入口一并补齐；同样支持首组内置 packed 形参。此前 named typedef 首组隐式 input 支持继续保留。后续每组重新指定类型但省略方向等完整 ANSI 推导尚未覆盖。

M145 支持 `package automatic` / `package static`：包变量始终共享静态存储，包的默认生命周期只作用于其 task/function；显式 `automatic` / `static` 子程序声明覆盖包默认值。未指定包生命周期时仍为 static，默认值不会泄漏到后续包或模块。静态子程序的局部变量跨调用持久保存，automatic 调用使用既有独立激活帧；现有 ref、NBA 限制、延时、分区与预测恢复规则继续适用。详见 [生命周期范围](package-lifetimes.md)。

M147 新增编译单元显式/通配 import，详见 [文件级导入及边界](compilation-imports.md)。

仍不支持 class、escaped qualified 名称或任意多段 `::` 路径。包依赖须在前面声明；不提供递归/前向包依赖求解。包 subroutine 内仍受现有 subroutine 限制（例如递归调用、constant function 用于 elaboration 不支持）。新增 named module port 不扩展 string/class 端口、typedef 后追加 packed 维度、显式 `wire T` 组合或完整 ANSI 类型/方向推导。本批不是完整 SystemVerilog package 实现，也不新增性能对标结论。

M133 的同源功能对照、实例克隆/清理和发布记录见 [验收](../validation/m133-header-imports/README.md)。正文区 import 不会追溯影响其前面的 header；导入的名称不会泄漏到父模块或兄弟实例。

验收与原始 VCS/ASan/UBSan 记录见 [M80](../validation/m80-packages/README.md)。

M83 将包内变量绑定到唯一包作用域，支持现有整数/四态/两态、enum/packed aggregate、固定数组和 string 子集；跨模块、包任务/function 共享，NBA、延迟及 checkpoint/分区依赖复用现有信号。标量声明初值仍要求现有常量初始化；显式全局生命周期限定符尚未实现，net 和模块端口明确拒绝。组合测试和边界见 [v3 修复](report-v3.md)。

M134 的功能对照与发布记录见 [验收](../validation/m134-package-exports/README.md)。显式 export 要求本包有来自指定包的实际或候选 import；该检查依据 [IEEE 1800 §26.6 的早期委员会提案](https://www.accellera.org/images/eda/sv-ec/att-5653/package_exports_bolded_alt1.htm)。VCS W-2024.09 对缺少 import 或仅从其他包路径导入的显式 export 更宽松，本实现仍拒绝这两类输入，不宣称负例完全兼容。通配 export 不要求真的存在 import，也不会触发任何导入。
