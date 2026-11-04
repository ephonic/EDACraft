# M188：原生 process 身份与随机状态

实现 `process` 内建类型和 `process::state` 枚举，接通 `self()`、`srandom()`、`get_randstate()`、`set_randstate()`。类型经 typedef、包、子程序参数/返回值、对象属性和队列传递，仍使用同一个规范类型。词法声明优先于内建回退。

句柄绑定真实执行进程，包括 fork 分支和 final。获取句柄不消耗 PRNG；随机状态属于目标进程，保持与普通类对象随机流的区别。fork 编译槽重用前保存旧 incarnation 的状态并解除绑定，旧句柄不会重新指向新分支。句柄、绑定、存档和 PRNG 都由 Sim/checkpoint 拥有，不使用宿主全局表。仅使用该功能的模型启用 `DSIM_PROCESS_HANDLES_ENABLED`，普通 RTL/门级模型不增加句柄字段。

随机状态字符串采用 dsim 自有、带版本且完整校验的 `DSIM-RNG1:` 编码，支持本工具内的精确恢复，不宣称能交换 VCS 随机状态或产生相同随机数。空句柄、损坏的状态和非执行上下文都明确报错。

范围：`status/kill/await/suspend/resume` 尚未实现，执行到对应功能的编译阶段明确拒绝。枚举存在不代表进程控制已完成。直接在模块/包声明初始化中使用 self 在语义阶段拒绝；经函数间接调用的无进程上下文由运行时拒绝。完整原版 UVM 仍未运行，不作性能结论。

验证脚本：`tests/process_handles/regression.py` 覆盖身份、随机流恢复、跨进程操作、fork 槽复用、类型传递、final 和预测回滚；比较串行/时间轮/双线程请求及 ordered/settled 的 VCD、同步/异步压缩波形。双线程是请求模式，不据此声称本组具有两个并行分区。`vcs.py` 对未改源码执行功能对照，并把 VCS 接受而本轮 dsim 未实现的反例单列。`sanitize.py` 检查前端、运行模型、回放、错误路径和 parser 反复清理。双端稳定发布与跨端结果见本目录最终收据。

原版 UVM 2020.3.1 未修改。1888084 字节预处理内容和 166 个依赖维持既有哈希；首错已从 `process` 推进到 `unknown integral type uvm_report_handler`。`public-uvm.py` 固定记录这条边界，不能解读为 UVM 全量通过。

最终结果：生产提交 `bb04d7f8` 已推送 GitHub。1277 项输入、源码摘要 `9943b7789e2013cdef9d9d2a6f98d4323657f710197d1e4b1e77b7176d4a6c50` 一致。Mac 稳定 `20261030T155321768001Z-9943b7789e20`、103 Intel 稳定 `20261030T155607313020Z-9943b7789e20` 均已激活。每端 process_handles/ipc/random_functions 三组共 26 模型、341 波形捕获、57 编译拒绝、13 运行时错误路径、报告中的 6 次回滚，以及 mandatory parser/liberty-db 检查通过；每端六个实际入口模型的生成代码和波形均与本端候选一致。

98 份生成 CPP 和 341 份独立解码信号序列跨端一致；13 份既有 IPC rollback 的压缩文件编码字节差异列在 cross-platform.json，解码后序列一致，新 process 用例没有跨端编码差异，同端同步/异步编码一致。ASan/UBSan 六模型、一次回放、18 编译拒绝、4 运行时错误以及反复 parser 清理通过，未启用泄漏检查。

VCS 六个未改源码模型通过，另一个用户 process 类及 typedef 的词法遮蔽用例两工具均通过。18 个编译拒绝中，11 个为共同拒绝；7 个为 VCS 接受而 dsim 本轮尚不支持的边界：五个进程控制接口、`process #(int)` 写法、动态 string 实参作为 srandom seed，均在 vcs.json 单列。未宣称完整 SystemVerilog/UVM 支持，也未进行速度比较。
