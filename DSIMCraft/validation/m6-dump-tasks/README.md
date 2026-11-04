# Testbench dump 系统任务接入

467文件冻结实现源码位于`native/source.json`，SHA256 `c56ac234ef38672df1ca10f93e4c9c5f432fe383fe3ac33eb64d3e856ae197fa`。原语464基线仍由根目录`source.json`标识，用于先前VCS参考探针的来源记录，不把两批源码混为一批。

实际实现包括dumpvars专用目标语法、原始层次组件/含点转义标识符、参数深度及无参数形式；前端绑定模块或完整信号。预处理后的任务token自动启用波形后端，RTL与门级结构parser继续独立。$dumpfile/$dumpvars/$dumpoff/$dumpon/$dumpall已接通VCD和原有DWF压缩/异步写出；文件名、深度、作用域和控制请求同值/时间通知按事务顺序提交，失败预测不创建文件，校正重放后写出。另补上实际测试平台所需的正整数literal/parameter重复拼接，含多字四态值。

`inputs/`含16组判别：全设计、延后启动、层次深度、子作用域、多个信号、同刻/延后重复dumpvars、off/on/all及同刻控制、首次选择前控制、改文件名、仅dumpfile、默认文件名和省略参数。本地16次Icarus编译/运行只用来检查探针输入，Icarus不是VCS参考。VCS原任务正常退出0，387份原始文件归档SHA256 `52cc1edec5e96090f03564d33dbeb8fb4595fe2d7fd6064c97a2c235b7278900`已下载并[独立审计PASS](vendor-verification.json)：16例、48次原始VCS运行，45份完整捕获在三次重复中物理位历史和控制一致。

[本地原始证据](native/local/results.json)已复制为不可变记录，并由[audit_native.py](audit_native.py)重新解码[审计PASS](native/local-verification.json)：

- 16例实际由compiler自动启用波形支持，不传--wave-support；75份默认/ordered VCD、raw/Zstd DWF捕获，219个VCS物理位历史和42条控制记录相同。
- 含点转义层次/信号目标与258位四态重复拼接由Python整数独立核对；首次dumpvars同刻x→0→1→0在ordered模式逐次保留，settled模式仅保留最终值。
- 原始无名buf顶层输入及内部三值SDF两例，默认/jobs-folded/wheel三后端共12份实际任务捕获，54次已有VCS物理位核对；不把它称作新VCS运行。
- 三组实际生成程序的普通分段、失败预测/校正重放及成功预测提交，共54份ordered/settled VCD/raw/Zstd DWF完整捕获相同。验证函数在提交前实际检查目标文件尚未创建，未把文件操作提前到预测阶段。
- 合计148份捕获、107次完整事件流比较；12类非法/未支持任务在编译阶段拒绝，两个动态非法depth在运行阶段拒绝且不创建文件；已有文件保护检查通过。普通/转义标识符及字符串/注释不误启用后端，宏展开的真实任务自动启用。

五项受影响本地CTest已通过，随后增加首次同刻跳变保留后，最终148份任务捕获重新通过。当前公共语义检查及全部既有检查经macOS ASan/UBSan通过；四个实际生成程序（失败回滚、成功提交、多字转义路径、首次同刻跳变）经ASan/UBSan执行32份捕获/16次完整比较通过，见[sanitizers/results.json](sanitizers/results.json)。未声称LeakSanitizer或Linux sanitizer。Bison3.8.2/Flex2.6.4隔离重生成三个文件逐字一致，原有33SR/69RR及两个generate警告不变。

原始失败保留：464不支持dump任务，前端最初把timescale直接交给公共parser，以及隐式端口词法/嵌套参数问题；运行时首次发现重复拼接未支持，测试脚本首次使用错误的比较函数签名，同刻关闭最初过早生效丢失该刻更新。均修正后实际重跑，没有删除失败或放宽物理历史/完整流比较。初次重生成遗漏verilog前缀的工具调用失败也已记录，未替换生产文件。

Linux467原任务`/tmp/dsim-dump-tasks-linux-1018-F7pGRFlw`、shell PID3265210已正常退出0且消失。完整110项CTest全部通过（3246.98秒），33,738份原始证据归档SHA256 `04af3454ad22b30c10e934035490205c1266b1379fababa651b5bd43456e87d1`下载并逐文件核对，[独立审计PASS](native/linux-verification.json)：148份跨平台完整捕获、全部生成CPP身份、219个VCS物理位历史/42控制/54次SDF物理位及54份事务捕获通过，两份原始全量SDF关闭功能时仅替换runtime，整个GCC预处理与已执行454程序相同。没有新增全量仿真、计时或Linux sanitizer；不将467完整110项称为后继473的完整112项执行。默认VCS捕获物理历史及控制已对齐该16例；**VCS同刻瞬态/优化求值顺序完全等价仍未证明**，其他同刻控制排列也需要扩大覆盖。普通RTL自动并行、自动预测器、dumpflush/dumplimit及百万信号首次槽缓存分组仍待继续。使用与限制见[任务控制波形](../../docs/wave-dump-tasks.md)。
