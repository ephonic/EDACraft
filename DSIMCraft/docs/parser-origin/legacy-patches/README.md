> 目录整理说明（M90）：当前 parser 直接维护在 `parsers/`，使用 `dsim_*_parser` 构建目标。
> 下文和 `edacraft-parser.patch` 是早期适配的历史记录，不是当前源码生成方式；请勿向当前目录重复应用。
> 原始来源、目录映射与构建说明见 [parsers/README.md](../../../parsers/README.md)、[来源归档](../README.md)。

# Parser 适配记录

新增 RTL 阻塞内部延时：`verilog.y` 用 `unary_expression '=' procedural_delay expression` 识别 `q = #d expr`，`VeriBlockStmt` 校验接受 delay 节点，并重生成 yacc/lexer。SR/RR 冲突仍为 33/69；不加入会抢占普通 NBA 的新 `<=` 分支。门级 parser 保持独立且本批不改。当前原 ZIP + 累积补丁全部 108 文件重放一致，见 `validation/m4-sdf-model-preparation/parser-provenance.json`。

原始压缩包不变，原包 SHA256 及修改清单见 `validation/source-provenance.json`。
`edacraft-parser.patch` 相对原始解压目录生成，可在干净解压根目录使用 `patch -p1` 重放。
包内 `SHA256SUMS` / `SOURCE_MANIFEST.json` 描述原始快照；打补丁后的文件以本记录为准。

- `verilog.y`：增加过程 delay 的标准形态 `#number`、`#parameter`、`#(expression)`；记录语法恢复错误并输出位置，不在 Bison 错误回调中销毁仍在使用的 lexer。
- `veri_stmt.cpp`：过程 timing control 的类型校验同时允许 delay expression 和 event statement。
- `veri_parser.cpp`：无参数系统任务空指针保护；每次 parse 重置语法错误计数，拒绝包含已恢复语法错误的输入；init 重置 lexer 行列计数。
- `veri_exp.cpp`：将 lexer 已接受的 `'0` / `'1` 解析为一位 AST 数值；dsim 后端保留 `'1` 的上下文填充语义。
- `verilog_lex.cpp` / `verilog_yacc.cpp` / `verilog_yacc.hpp`：从随包 `.l/.y` 重新生成。原包生成文件未覆盖其当前 sized-cast 源码，重生成后原有 `rtl_semantic_memory` 回归通过。dsim 自身仍拒绝 cast，因为原 AST 会丢弃 cast 的精确信息。
- `veri_module.cpp`（M2）：ANSI 端口映射先剥离声明初始化赋值，且逐端口清空临时指针，避免将前一个端口重复用作当前端口；packed 位选连接不增加 unpacked 维度。新增层次用例覆盖两类问题。
- 顶层工程将历史 demo 设为 C++11，兼容其使用 `register` 的头文件，不修改原包 CMake。

重生成：

```sh
BISON=/opt/homebrew/opt/bison/bin/bison sh scripts/regenerate_parser.sh
```

本次生成器为 Bison 3.8.2、Flex 2.6.4（具体以工具版本为准）。原始及修改后的 `.y` 用同一 Bison 生成，均报告 33 个 shift/reduce、69 个 reduce/reduce 冲突，以及原有两条无效 generate 规则。本次没有增加冲突数；这仍是后续前端覆盖的风险，不能用当前小例代表完整语言支持。

## M2 控制语句增量

- `veri_stmt.hpp` / `veri_parser.hpp` / `veri_parser.cpp` / `verilog.y`：保留过程循环种类，区分 while/do-while；加入 repeat/forever，允许空循环体。`verilog.l` 识别新增关键字；生成文件同步更新。
- `veri_stmt.cpp`：过程 for/while/do/repeat/forever 不在语义解析阶段求值或展开，改为绑定全部头部/循环体；过程 case 和 if 绑定全部分支。generate 的独立类保持原路线。这同时修复了空循环头部和动态 case 标签作用域缺失导致的崩溃。
- `veri_exp.cpp`：将 `$time` 绑定为非恒定系统值，避免作为用户符号查找失败。
- 本批相对原 ZIP 的全部 11 个修改文件见 `validation/m2-control/source-provenance.json`；补丁已经在原 ZIP 干净解压目录重放并逐文件核对，见该目录的 `parser-patch-replay.log` 和 `parser-replay-sha256.json`。此前 `validation/source-provenance.json` 保留为历史记录。
- 重新生成仍为 33 个 shift/reduce、69 个 reduce/reduce 冲突和两条原有无效 generate 规则，日志见本批验证目录。

## M3 独立门级增量

- `gate_netlist_parser.hh/.cc`：增加显式仿真模式和端口元数据查询。仿真按结构 token 流严格检查，拒绝时序近似 parser 会跳过或简化的语义；原有时序模式保留。读取一次源文件，metadata/建网复用同一 source view；修复仿真模式下的层次空连接及 X/Z 常量映射。
- `liberty_db.hpp` / `liberty_parser.cc`：保留输出 pin 的 `three_state` 表达式，供独立门级适配层编译使用。
- `liberty_binary.cc`：FTLib v13 在原有布局尾部追加每个 pin 的 three_state 字符串 ID，保留 v5–v12 读取。自研 roundtrip 测试覆盖 plain/gzip、ID 重映射及 v12 字段缺省。
- 本批相对原 ZIP 共修改 16 个第三方文件，包括保持不变的前批 11 个 RTL parser 文件；新增差异均位于独立 gate/Liberty 路线。当前可重放补丁、来源与校验见 `validation/m3-gate/source-provenance.json`、`parser-patch-replay.log` 和 `parser-replay-sha256.json`。

## M3 结构宽连接增量

- `gate_netlist_parser.hh/.cc` 的显式仿真分支直接展开总线、部分选、嵌套拼接、复制及四态数值常量；宽结构 assign 用共享复制单元，层次 net 端口按位绑定。Liberty 提供真实标量 pin 方向；空结构模块保留未驱动端口。接受可选 wire/tri 声明及内部升序范围；原时序模式继续使用原有建网路线。
- 当前补丁相对原 ZIP 仍为 16 个第三方文件；相较 0.5.0 仅 gate parser 的 `.cc/.hh` 有变化，其他 14 个文件不变，没有修改/重新生成 RTL grammar。来源、干净重放和校验见 `validation/m3-connections/`。前批 `validation/m3-gate/` 的补丁校验对应其不可变源码归档。

## M3 Liberty ff/latch 增量（0.7.0）

- 相较 0.6.0 仅更新 `liberty_db.hpp`、`liberty_parser.cc`、`liberty_binary.cc`。独立 gate parser 两个文件和全部 11 个 RTL parser 文件保持不变；相对原 ZIP 的修改总数仍为 16。
- 保留 ff/latch 类型、两个状态名、latch data_in、clear_preset_var1/2；对多个状态组、bank/statetable、重复或未知顺序属性保存不支持标记，交由门级功能绑定明确拒绝。
- FTLib v14 在 v13 尾部追加六个 cell 字段；读写覆盖 plain/gzip、ID 重映射、多库、v12/v13 缺省，保留 v5–v13 读取。旧缓存丢失的信息不伪造为完整 ff/latch。
- 修复旧版二进制 loader 的多库悬空指针：目录装载完成后重新查询库指针。原崩溃栈及修复后的回放证据见 `validation/m3-sequential/binary-multilib-before.log` 与该批 CTest。
- 当前可重放补丁与原 ZIP 清单见 `validation/m3-sequential/source-provenance.json`、`parser-patch-replay.log`、`parser-replay-sha256.json`。前批归档保留各自不可变的补丁校验。

## M2 预处理与字符串增量（0.8.0）

- `verilog.l` 的普通字符串和历史 `line 指令文件名改用排除未转义引号的模式，修复同行多个字符串的最长匹配；不扩充尚未支持的转义语义。
- `verilog.y` 错误回调保存第一个语法错误行，`veri_parser.cpp` 在每次入口重置；dsim 预处理 source map 将此行及后端行号映射回 include/原始源码。
- 同步重生成 `.lex/.yacc` 三文件，冲突仍为 33 SR、69 RR 和两条原有无效 generate 规则。本批相较 0.7.0 共六个 RTL 文件变化；独立 gate parser 和 Liberty 不变，相对 ZIP 仍为 16 个修改文件。
- 新 token 预处理器位于自研 `src/preprocessor.cpp`，不替换门级 parser，不调用原包的历史预处理近似实现。原 ZIP 干净重放、逐文件 hash 和远端冻结验证见 `validation/m2-preprocessor/`；历史 0.7.0 字符串失败记录保留。

## SDF / 并行基础批次：常量读取越界

- ASan 完整回归发现 `62'd1` 的声明宽度大于实际分配的 `_val` words，`VeriNum::get_certain_bit` 按声明宽度读取高位时越界。新增 `_vbits` 边界检查，把缺失高 words 视为零填充；原有四态存储路线不变。
- 相较 0.8.0 只新增 `veri_num.cpp` 差异；原 16 个修改文件内容保持不变，独立门级 parser 没有修改。当前总共 17 个第三方文件与原 ZIP 不同，补丁已在干净原包重放；清单见 `validation/m4-sdf/source-provenance.json`。
- SDF 为独立自研 `src/sdf.cpp/.hpp`，没有把 SDF 或大门级网表送入 RTL parser。

## SDF 绑定按需门级名称（0.11.0 / 0.12.0）

- 仅修改 gate_netlist_parser.hh/.cc，增加显式仿真模式下的叶实例与结构 scope/端口观察接口；普通解析不保存时序路径。大网表继续独立 token/Network 路线，未修改 RTL grammar。
- 相对原 ZIP 仍为 17 个第三方文件；0.12.0 的驱动存储和输出等价优化全部位于自研 runtime/gate compiler，未修改第三方 parser。干净补丁重放清单见 validation/m5-driver-inline/parser-replay-sha256.json。
