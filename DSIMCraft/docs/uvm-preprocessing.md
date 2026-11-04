# UVM 预处理与前端诊断

M153 继续使用固定的 Accellera UVM 2020.3.1 提交 `78c06547a2a0a29b3dc9dcafae62b75b2ff61544`，不修改库、不启用 UVM_EMPTY_MACROS；UVM_NO_DPI 仅与同源 VCS smoke 一致。源码/许可证与 SHA256 清单保存在 M152 的公开 reference 归档。

新增的通用规则包括宏体内 `//` 注释末尾续行、宏展开结果中的条件编译、跨展开边界共享条件栈、非选中分支不展开，以及宏引号内拼接/嵌套宏和替换字符串形参。普通源码里的字符串与注释不作为宏调用处理；独立门级结构 parser 不变，共用预处理回退也应用这些规则。CRLF 按原有输入归一化处理；VCS W-2024.09 在该注释续行 fixture 的 CRLF 源码报语法错误，单列参考差异。普通替换字符串中的嵌套宏仍有参考差异：VCS 会展开 `LABEL`，native 保留该宏文本；独立探针六行输出中此行不同，详见 `string-reference-difference.json`。不宣称完整 IEEE 预处理兼容。

先前库预处理阻塞被解除后，RTL parser 的语法恢复继续归约了不完整的 class/generate，导致空指针。现在已判失败的模块项在错误恢复点终止，保留第一次语法错误、源映射和后续重复解析能力；不以忽略声明或生成空模型接受不支持的输入。

验收区分三个阶段：公开包及 component 的 dsim `-E`；将这份完整展开 SV 交给 VCS 编译并运行 smoke；最后用 native dsim 编译原始包。前两步通过只证明所测预处理与参考运行链路，不能视作 native UVM 可运行。M153 原始结果见 [记录](../validation/m153-uvm-preprocessing/README.md)。

M154 已加入类前向声明及执行绑定；不修改同一公开库，native 首错从 `base/uvm_base.svh:42` 移到 `base/uvm_object_globals.svh:714` 的 `uvm_core_state m_uvm_core_state[$];`。这表明前向声明的语法阻塞已解除，不代表原始包已完成语义分析或运行。下一步继续命名类型队列和对象容器，再推进参数化/编译单元类、static/extern/local/protected 及验证运行时依赖；完整 UVM 仍未通过。新证据见 [M154 记录](../validation/m154-class-forward/README.md)。
