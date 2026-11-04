# 有界异步DWF块压缩

456文件冻结源SHA256 `ddbc689dc61bc2b98a1df463497412eb4be8c33f6f6490198fe94e19c31511cc`，见[source.json](source.json)。RTL/gate parser保持独立，事件内核与并行窗口逻辑不变。新增实际波形CLI `--wave-compression-jobs 1..16`，默认1走原同步路径；大于1使用独立后台Zstd上下文，文件/索引按原块顺序提交。

待提交块上限为2×线程数、原始长度计费总和64MiB，两者均施加背压；这不是RSS上限。后台异常返回调用者，close排空并join线程。保持`DWF1P001`及META/BLK1/INDX/CRC，完整恢复只承诺已完整提交的前缀。详见[格式与使用](../../docs/waveform-format.md#有界异步块压缩2026-10-18)。

本地新`wave_async`定向CTest实际通过：114份完整捕获、69对文件逐字节相同，覆盖scalar别名/极小块、1024位四态独立PRNG oracle、RTL及SDF实际生成程序的预测回滚/提交、generic/compact并行窗口的channels/direct/finish/finish0/failure、损坏拒绝与截断恢复、五个非法CLI组合。114计数不包含另外四份宽值预算文件及六份独立writer参考捕获。jobs=2/4/16在64KiB嵌入预算下均达到3份/49,935字节峰值，显式超预算与注入后台异常验证通过。

[旧默认身份](default-verification.json)另验证12对旧454/new默认文件，涵盖ordered/settled、raw/Zstd、1/17/16384块事件数；未传新选项，完整文件逐字节相同。[本地sanitizer](sanitizer-verification.json)实际执行ASan/UBSan正常/异常内核及TSan正常内核，退出0并核对插桩符号；八份完整捕获解码及字节一致。此处sanitizer范围是独立队列内核，不是生成事务程序或Linux。

456完整本地105项回归已正常结束，1308.20秒；原PID58435消失。详细LastTest、105个唯一通过名、完整新波形及源身份已保存并[独立审计PASS](local-validation.json)，不会被后继CTest覆盖。后继457只增加[统一流程配置](../m6-async-flow/README.md)，native编译源/运行头及原105项命令和属性全部相同；新正式CTest单独通过，不将其称为457一次完整106项执行。

原454性能任务终态并审计后启动的456 Linux集成`/tmp/dsim-async-wave-linux-1018-9w808KsP`现已实际退出0且原PID2336724消失，完整105项CTest通过（2610.21秒）。27,721份原始证据归档SHA256 `94b8039d784ff6f77f68347b89ec6a3ac55a6d57f3210f244fb6249e10eab665`已下载并[独立审计PASS](linux-verification.json)：114份跨平台完整流、额外4份宽值流、69对同平台字节身份，以及原始全量设计三版关闭波形的整个CPP/IR身份。该批不重复执行全量128仿真，不声明Linux sanitizer。归档中的五个文件链接从归档内目标内容安全物化，内容哈希一致；原始归档不修改。原SSH观察连接未及时退出时，按原PID消失、shell.exit=0及工作目录无剩余进程独立确认终态，见linux-terminal-observation.json；没有重启任务。原始454零输入通道六轮固定CPU性能测量使用不同冻结源、关闭波形，不含此实现。尚无本候选性能、RSS、压缩率提升或VCS波形性能比结论。
