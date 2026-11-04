# M38 显式变量连续赋值与 VCS 对齐

本批补齐模块级 assign 到 logic/reg/bit、整数、enum、packed 聚合和宽变量，覆盖静态位段、静态多维数组元素、成员及混合 net/变量拼接。RHS 按总目标宽度取样一次，保留 signed 扩展、截断、两态转换及未写入位。单值常量 delay 接入原有惯性驱动队列、时间轮、并行和检查点；绑定时一次拆分 net/变量列表，投递时不重新拆分。不增加影子 net 或额外适配过程，RTL 与紧凑门级 parser 保持分离，词法/语法生成文件未改。

变量写入检查改为 O(W log W) 静态区间扫描，允许不相交位分别驱动，拒绝连续赋值/端口/过程/声明初始化的重叠。W 是变量写区间数，此复杂度不涵盖原有 always_comb/latch/ff 专项检查。过程动态 packed 成员选择修正为该成员的最长静态前缀，允许另一成员连续驱动。原有冲突诊断文本继续含 variable port driver conflicts。本轮 runtime 头改变，因此不声称旧里程碑完整生成 C++ 的字节身份仍保持。

输入在 tests/variable_assign，basic/parts/delay/types/effects/parallel 均含独立 TRACE 预期或错误标志。六例 × serial/time-wheel/threads=2 × ordered/settled × VCD/DWF 共72次捕获，delay/types 在1ns挂起事件期间做实际失败预测回放并比较完整 ordered 波形，合计74次。parallel 实际两个独立分区，另以数学预期核验全部输出时间点及错误标志。17类拒绝、128组独立写区间组合和4096个不相交位连续赋值纳入测试。

实际 VCS 为 10.131.254.103 的 W-2024.09，环境 source /apps/EDAs/syn.bash，命令 -full64 -sverilog -debug_access+all -top top -top dump，运行 simv -no_save。六组共同源逐字节核验，TRACE/自检及全部812条直接导出物理位时间线一致，无路径映射或位排除。VCS不导出的全部4个数组字、16位，经同源 packed image 信号逐位逐时刻核验，单列不计直接导出位。范围表见 tests/variable_assign/observers.json；原始输入、日志、退出状态、VCD和离线比较分别在 vcs、vcs-results.json、verify.py。

边界探针保留双方源码hash、原始命令/退出状态与日志：单值延迟/X/Z、带延迟重复左值及两态 X→Z 脉冲取消均一致，多值变量 delay 双方拒绝。两态取消探针在5.5ns为1、6.5ns为0，确认先按四态 RHS 取消，再在投递时作两态转换。另有一项明确差异：无延迟 assign {v,v}=8'h96，native 为6而VCS为9；带延迟同类赋值双方为6。共同 parts 模型的重复左值使用0.1ns延迟，无延迟原始形态单列为 repeat-immediate，未计入已对齐四组探针。run-probes.py 的 PASS 表示原始边界及已知差异均按预期保留，汇总状态为 PASS_WITH_KNOWN_DIFFERENCES，不表示该边界已解决。

macOS ASan/UBSan parser单测、六语料各三轮清理、六个实际生成程序及完整 ordered 波形均通过，包含真实双线程，leak检测关闭；见 sanitizers、run-sanitizers.py 和 local/dsim-m38-parser-san-test.log。四种普通/紧凑/标量/IEEE延迟内核及三种对应时间轮内核验证新增变量/混合投递、取消、宽值和检查点。初次回归的并行初始X数学预期曾使用错误的 reader 原始位编码，修正为 (255,255) 后重跑；失败日志保留 local/initial-regression.log，不计为模拟器语义修复。

最终本地、Linux干净构建和源码身份验收状态见 results.json、source-manifest.json、source-archive.json、final-identity.json、platform-identity.json、linux-vcs-results.json。source包不含验收输出及plan进度记录；冻结后不再修改所列源码。七份实际生成 C++ 比较覆盖六个串行模型和真正双分区模型。当前编译器重跑的M37六组共同源仍保持1623条直接位+16数组观察位与历史原始VCS一致，见 m37-retained-vcs-results.json；未将历史M37边界探针计作本轮新运行。

可复跑：cmake --build build --target dsim；ctest --test-dir build -R '^rtl_variable_assign$' --output-on-failure；python3 validation/m38-variable-assign/verify.py。远端原始差分入口 run-vcs.py、run-probes.py 接受输入/输出目录。源码归档和两端逐文件hash、构建/测试日志均保留于本目录。

仍缺动态连续左值、运行时 delay、一般非默认强度、数组端口/ref、命名类型模块端口、package/interface/class、完整SVA/UVM和事件区域；M35/M36已知差异仍保留。本轮未跑全量CTest、Linux sanitizers或新仿真速度测量，不能宣称全部SV/VCS功能或性能已经对齐。

最终验收：本地六项定向CTest 131.53 秒、Linux同源干净构建六项 225.43 秒全部通过、退出0；七份完整实际C++跨平台字节一致，Linux实际812直接位+16数组观察位再次匹配VCS。冻结源码831文件，源包SHA256 324c88c943f8a7ee256e8db373d88423430e41f7953c981d2564b6d2fa897d81，冻结后所列文件未改变。
