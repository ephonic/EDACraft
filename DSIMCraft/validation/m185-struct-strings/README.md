# M185：未打包结构体的字符串成员

本轮使用独立的不可变字符串成员表保存值，字符串不编码为整数。成员偏移仅为内部地址；`$bits` 的相应路径保留明确诊断。普通整数、原有字符串和门级模型不启用新的运行时字段。

支持默认空字符串、嵌套结构体、成员读写与字符串方法、整体独立复制、位置/命名赋值模式、函数输入及返回、整个结构体的 ref 任务、固定数组元素和已知条件选择。混合 bit/logic 成员保持各自的两态/四态转换。预测回滚恢复完整值；时序用例直接检查试运行发生变化、校正回调恢复原值、重放再次发生变化，随后验证提交。

VCS 拒绝对含字符串结构体的整体、任何成员和数组使用 NBA；dsim 同样拒绝这些路径。仍缺动态结构体容器、相应实例类属性、字符串成员 ref、含字符串结构体的 `$bits`、未知条件的结构体合并和结构体成员波形导出。当前波形中排除此类整体变量，普通观测信号仍输出标准 VCD、同步/异步压缩 DWF。

最终生产提交为 `d01c6d87`。四个新模型覆盖 serial/time-wheel/threads=2、ordered/settled、VCD/DWF/异步 DWF，合计 76 捕获、14 拒绝、4 回滚、1 提交；parallel fixture 实际使用两个分区。既有 packed 结构体、未打包结构体和字符串组分别为 63、52、31 捕获，发布验收合计每端 222 捕获。ASan/UBSan 覆盖 parser 重复清理、四模型和四回放及全部拒绝用例，未开启 leak 检查。

未修改的 Accellera UVM 2020.3.1（UVM_NO_DPI）预处理仍为 1888084 字节、166 依赖、SHA256 `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`。已越过 string 结构体成员，当前原生编译错误为 `extends requires a previously declared class: uvm_resource_db`。完整 UVM 尚未展开或运行，下一步定位参数化继承的名称和类型解析。

`mac-stage.json` / `linux-stage.json` 保存源输入和二进制收据；`*-reference.json` / `cross-platform.json` 保存生成 C++ 与独立解码波形比较；`*-entry.json` 保存实际稳定入口复验；`vcs.json` 区分共同拒绝和当前功能边界（12 共同拒绝中 `$bits` 是 VCS 自身 NYI，不视作语言非法）；`sanitizer.json` / `public-uvm-*.json` 保存最终结果。跨端 86 份生成 C++ 原字节一致，222 捕获独立解码一致；旧 unpacked_state/storage/replay.dwf 一处编码字节差异单列。两端各四个实际安装入口模型的 CPP 和异步压缩波形与候选逐字节一致。最终状态及稳定路径以 `progress.json` 为准。

首轮候选使用尚未收紧的成员 NBA，已由最终候选替换；VCS 越界数组成员读取探针另有运行时诊断，不计最终同源正例。验证过程中修正了 VCS 环境变量/解码依赖缺失，以及 sanitizer 回放误用普通运行波形基线的问题，并重新执行。原始不兼容探针、解码依赖错误和回放基线错误的留存日志不作为产品通过证据。原始日志、CPP、SV、波形和 sanitizer 输出存放于外部证据目录及不可变 release；目录位置见 `archive-locations.json`。

仅声明本轮选定发布目标及回归通过。全量构建既有 masked Ready 尺寸静态断言问题未在本轮处理；本轮没有性能对比或完整 VCS/UVM 支持结论。
