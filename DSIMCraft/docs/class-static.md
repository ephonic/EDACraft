# static 类成员与类作用域

RTL 前端支持 class 中的 `static` 属性、`static function`、`static task`，并保留与 `function static` 局部生命周期声明的区别。静态方法采用 automatic 调用帧，不接收 `this`；实例属性/实例方法仍需要对象接收者。静态属性在构造器之外分配和初始化，不随 `new` 重置；继承访问绑定原声明，参数化类按规范特化共享，模块实例内声明的类各自独立。

支持 `C::member`、包限定名、typedef 类别名，以及 `C#(...)::member`。静态属性复用标量/string/宽四态、固定数组、动态数组、queue、关联数组存储与调度路径；范围、类型和容器限制沿用各自专题。通过空句柄访问静态成员不会解引用对象，但接收表达式仍须求值；读写、更新、静态方法和容器方法保留其副作用。静态属性参与依赖、分区、checkpoint/预测恢复和用户选择的波形输出。参数化静态存储在信号重排后仍保留唯一的波形路径。

本批保留一项 VCS 行为差异：将有副作用的 `pick().x` 作为 `ref` 实参时，dsim 求值一次，参考 VCS W-2024.09 本用例求值两次；引用写入的数值相同，但调用计数不同。该差异明确保留，不能将全部对照用例称为完全对齐。

另有两项接收性差异：VCS 接受本轮 `static function` 模块作用域声明与 `static function static` 类方法用例，当前 dsim 明确拒绝；不能将十个 native 拒绝例全部称为 VCS 同样拒绝。

仍未补齐 local/protected/extern/out-of-block 方法、类作用域中任意嵌套类型应用、完整约束随机/IPC/virtual interface/clocking/coverage/DPI 等能力。未修改公开 Accellera 2020.3.1 包的语法首错推进到 `uvm_misc.svh:377` 的 `endfunction : to_string`，完整 UVM 仍未原生编译运行。不能将 static 声明通过等同于 UVM 可用。
