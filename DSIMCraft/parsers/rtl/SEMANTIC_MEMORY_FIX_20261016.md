# 第二轮语义遍历内存与参数、端口修复

已修复可复现的内存错误，并恢复选定 top 时的自动第二轮语义遍历。未选 top 的 `parse()` 保留语法树收集用途。此次没有写入 fsyn 源码。

## 根因与改动

1. `VeriVarDecl::declare_var_symbols` 和 `VeriIntDecl::declare_int_symbols` 把整个 `VeriAssignExp` 强制转换成 `VeriPrimaryExp`，实际应转换赋值左侧 `lval`。错误转换读取假的字符串布局，随后还可能通过 `set_var` 写入错误偏移。完整 barr 层次在修复前由 ASan 报告异常巨大的字符串分配，堆栈指向 `VeriVar` 构造与该转换。不能把崩溃仅归因于被破坏的 range 节点。
2. 声明赋值在左侧符号注册前调用普通赋值处理，提前报找不到符号。声明初始化现在由声明处理器负责，正常赋值仍执行原处理。
3. `align_bits` 在 32 位整数边界右移 32 位，UBSan 已复现；正的 32 位有符号常量扩展到 64 位时，原填充逻辑把低字改成全 1。另修复 `bit == bits` 的越界取位与初始化值的声明宽度截断。
4. 节点池清空后没有清掉回收 ID 队列，可能让回收 ID 与新计数器分配的 ID 冲突。清理只遍历实际 toss 数量，移除按虚表地址猜测是否应该 delete 的规避代码，恢复正常虚析构。
5. 符号表清理后没有清空桶指针；模块清理又先清理符号表再 delete，可能重复释放。修复重复清理，并在 parser 重新初始化时释放旧模块容器、清空文件状态；模块容器清理也释放桶数组并重置模块列表。
6. 端口映射原来没有安排在模块遍历尾部执行。恢复尾部映射，修复空端口、空实参、过多位置实参的边界检查；命名端口按名字匹配并写入 `port_ref`，允许乱序与显式空连接，拒绝未知或重复名字、混合连接和非法形参类型。修复 array 端口检查中颠倒的空指针条件，以及模块克隆后父指针未更新的问题。
7. 实例化的参数覆盖原来没有进入子模块语义作用域。现在按头部参数顺序，或无参数头时按模块级 parameter 顺序，接受位置和命名常量覆盖，排除 localparam。每个参数注册后再求后项默认值，支持 `W=8,V=W+1`；实例覆盖先于默认值生效，并检查未知、重复、过量及无法求常量的实参。修复 `IS_TRUE=0` 布尔枚举的错误判断。
8. 表达式实参的逗号包装节点此前没有安排末尾取值，造成 `.W(N)` 包装后丢失常量结果。恢复逗号表达式取值并保护空列表。
9. `parse()` 不再丢弃语义遍历的返回值。选定 top 后，未知符号、端口和参数错误都会返回失败；未选 top 不再产生无意义的 missing-top 错误。模块实例符号注册失败也立即返回。
10. LeakSanitizer 在完整 barr 上进一步发现端口与独立 wire/reg 声明合并时泄漏初始化指针数组。用临时所有权保护注册过程，只在新建符号时转移数组；数字节点继续由节点池管理。

## 验证

新增 [semantic_memory.cpp](test/semantic_memory.cpp)，通过 `-DVERILOG_BUILD_TESTS=ON` 构建。测试默认关闭，不改变 fsyn 的构建选项。

- 数值宽度覆盖 1、31、32、33、63、64、65、256，检查正负数扩展和边界取位。
- 连续三次解析验证 64 位声明、初始化值 17/19、节点池重置和重复清理。
- 乱序命名端口、位置端口、空模块/空连接、独立端口声明，以及过量、重复、未知和非法形参。
- 同一模板四个实例分别得到 33、17、65、9 位端口，内部依赖 localparam 的线网分别再加 2 位；验证两个实例之间覆盖值隔离及依赖默认值。
- 通过公开 `parse()` 检查语义错误和缺失 top 的返回值；未指定 top 的多模块收集成功。
- 完整 barr 层次和现有 `test020` RTL，各连续三次自动第二轮遍历及清理。

远端使用 Clang 22、Debug、`-fsanitize=address,undefined -fno-omit-frame-pointer`。最终启用 `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1`、`UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1`，三项验证均返回 0，没有 sanitizer 或泄漏报告。最终实际生产 CMake 快照位于远端 `parser_memory_20261016/production_v9`，不是早期忽略语义错误的诊断遍历。

日志与返回值：[validation.json](../scratch/ftimer_pt_20261011/round32_evidence/parser_memory_20261016/production_v9/validation.json)、[单元回归](../scratch/ftimer_pt_20261011/round32_evidence/parser_memory_20261016/production_v9/ctest_lsan.log)、[完整 barr](../scratch/ftimer_pt_20261011/round32_evidence/parser_memory_20261016/production_v9/barr_full_lsan.log)、[test020](../scratch/ftimer_pt_20261011/round32_evidence/parser_memory_20261016/production_v9/test020_lsan.log)。

## 范围与剩余限制

这些结果验证本次内存修复与所列语义场景，不能视为完整 Verilog 语义实现。现有复杂前向声明搜索尚未补齐：未找到符号的 lookup 请求目前会重试并返回明确错误；部分常量拼接和生成语义也有既有空实现，仍需单独完善。未执行全套 fsyn 综合/PPA 回归。

此次只修改 parser 和 FT 的 SDC 应用/回归文件。最终审计发现 fsyn 工作区在会话期间另有变化：`timing_pipeline.cpp` 当前 SHA256 为 `1ab688defc03da88c77375aa086b39e457587c4a0df3ff6f601bee461141ffcb`，与开始快照不同；没有覆盖或回退这些变化，因此不声称 fsyn 目录的全局哈希不变。
