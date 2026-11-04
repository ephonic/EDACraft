# 顶层输入的重复 SDF 更新

新 VCS 的12场景各三次原始运行，确认顶层 input 的 MIPD ABSOLUTE 使用 MAXIMUM：9→3保留9，不随外部寄存器、assign、buf、跨模块或多驱动形式改变。内部单驱动9→3仍为3。覆盖 PORT/INTERCONNECT、ABS3/INC20/ABS4（顶层23、内部4）、三值更新、四态及短脉冲。36次原始结果零注解错误/警告，269文件归档 SHA256 `e5b704a4425917327b8efb03d6cbf57593d6509d919714c500648c6ac50e328e`，见[vendor审计](vendor-verification.json)。

461文件冻结源 SHA256 `4a09b7a4ed389f5e65e3d43153d9e037ea8f64f2d04dfcf88164c154151b88c7`，见[source.json](source.json)。只改编译期 SDF 消费者，分别记录 root input 和结构驱动数；普通内部单驱动继续末次更新。ABS零保留与INC规则保持。没有改 runtime、波形、并行或 RTL/gate parser，二者仍独立。新增两个正式 CTest；总清单108项，本批不声称执行完整108项。

首轮 native 回归在第三例 root-buffer 失败：现有 RTL parser 不支持无名 `buf(a,stimulus)` 的参数组。原始输入和失败日志保留，不将这一语法称为已支持。native 对此唯一场景增加实例名 `buf buffer_driver(a,stimulus)`；另三次实际 VCS 证明全部物理位与 TRACE 和原无名 fixture 相同，27文件归档 SHA256 `5ed186056acecf6e91b0379f998ee5b37de5164e688f49b60ce6bec12d33bb96`，见[命名适配审计](named-buffer-verification.json)。未通过更换驱动方式回避原语的 Z→X 行为。

[本地独立审计](local-validation.json)PASS：12例×3实际编译后端，216完整 ordered/settled VCD/raw/Zstd 流，279次明确列出的 VCS 物理位比较；Zstd 使用4个压缩线程。36份新旧CPP除输入延迟表外完全相同，内部三例的9份CPP逐字相同；旧编译器 root-reg 的错误 TRACE 实际复现。未导出的 vendor 叶输出不算独立对照点；跨 native 后端比较完整有序事件，vendor比较物理值历史，不声称 vendor delta 顺序一致。

实际生成的8配置 boundary/replay 共32捕获，以及2配置 macOS ASan/UBSan 的8捕获通过；后者检查实际插桩符号及编译/运行日志。41/45/75ps 边界覆盖待交付输入事件、接受提交和拒绝预测回滚；boundary/replay完整流和文件逐字相同，二者所有物理位历史与不分段运行相同（分段运行会增加空时间标记）。旧零输入9场景162捕获/192次vendor物理位、两个PORT优先级场景48捕获以及 timing_models CTest另通过。不是完整本地108项或Linux sanitizer。

Linux 原任务 `/tmp/dsim-root-input-linux-1018-QhEzqx9u`已正常退出0且原PID1221593消失，3,380份证据归档SHA256 `2ff23e5d56787d35dd890b6ecb7c096a4cf554fcad5088400460a0baba267700`已下载并[独立审计PASS](linux-verification.json)：五项受影响CTest（332.54秒）、两个PORT对照、248份跨平台完整捕获，以及三份原始全量设计CPP/IR与已执行454程序逐字一致。没有重复执行原始128笔，不作新速度或默认采用结论。原454/456/457结果各自保留，不能回写旧失败为PASS。

root inout、一般scope接收端、完整稀疏值/显式十二值混合、primitive DEVICE、RETAIN/完整脉冲、负检查延迟数据和自动预测器/自动并行仍未完成。本批不为这些范围作兼容声明；零输入折叠的独立复测与默认采用判断继续作为性能主线。
