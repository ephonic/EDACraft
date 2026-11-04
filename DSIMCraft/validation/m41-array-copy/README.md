# M41 静态 unpacked 数组整体过程赋值与 VCS 对照

接通整数组和常量前缀子数组的阻塞/NBA过程复制，含延迟NBA、阻塞赋值内delay、宽字、net源、类型检查、函数/automatic任务、组合/时钟过程、线程和回滚。各维按声明顺序映射，秩/维度大小/元素位宽/signed/enum身份检查后生成静态信号ID表。先保存全部源字，再写目标或排入NBA，避免复制过程中混用新旧值。进程缓冲按赋值位置复用；函数使用每次调用的局部缓冲。缓冲在可复制进程对象中，沿用已有检查点恢复，不引入新调度内核或运行时AST解释。

RTL与紧凑门级parser保持分离，runtime/parallel和词法语法生成文件未改。沿用现有数组AST，新增parser公开入口整体复制、多维子数组和automatic函数数组的三轮清理单测。M40六份完整实际生成C++重生成字节一致，见m40-identity.json。数组过程目标必须为变量，automatic目标上的NBA继续禁止；读写集合包含每个元素，接入always_comb敏感依赖、always_ff及单驱动检查、独立域分区。

共同源六例在tests/array_copy：basic覆盖方向/signed/XZ/self-copy/NBA，matrix覆盖三维逐维映射和静态子数组/延迟NBA，types覆盖130位、enum、packed struct与vector复制、net源和两态目标，effects覆盖automatic函数和两个重叠任务/always_comb，timing覆盖延迟NBA重复进入、显式delay后复制和always_ff，parallel覆盖两独立分区和按数学预期核对每个输出。另有native专用intra_delay/intra_parallel，验证整数组阻塞赋值内delay、130位入口取样、automatic挂起隔离、真双分区。八例×三后端×两模式×VCD/DWF为96捕获，timing/effects/intra_delay在1ns真实失败预测回放后再核对ordered流，共99次；16类拒绝、NBA管线2/3/4ns分别交付10/20/30的独立时间线、两个parallel模型及跨写法完整波形一致性均通过。

真实VCS为10.131.254.103的W-2024.09，source /apps/EDAs/syn.bash，使用-full64 -sverilog -debug_access+all -top top -top dump，运行simv -no_save。六共同源字节相同，TRACE/自检和全部1317条直接导出位的settled时间线一致，无路径映射或位排除。全部1056个导出的native数组位另经同源packed观察信号逐位逐时刻核对，1317已包含观察信号，两数字不相加作独立VCS导出位。observers.json覆盖每个静态可见数组字；automatic临时数组不导出，功能由返回值/外部结果自检核验。verify.py拒绝未列出的数组字或未核对的其他信号。VCS同刻瞬态顺序没有宣称对齐；native三个后端与VCD/DWF的ordered流保留同刻变化并完整互比。

11个未修改原始边界探针在probes/native和probes/vcs，8个在接受/拒绝及TRACE层面一致：方向、两态转换、普通/延迟NBA，以及秩、宽度、signed、enum身份的错误拒绝（错误码/文字未称一致）。按VCS实测，允许同宽同符号两态/四态整体复制，由目标执行X/Z转0；这比严格state等价条件宽松，见docs/array-copy.md。三项差异明确保留：subarray的动态前缀VCS接受、dsim拒绝；timing和仅增加packed观察信号的timing-observed中，VCS没有在整数组阻塞赋值内delay等待，故1ns打印xx xx 01 02，dsim在4ns打印01 02 01 02。原始run.log保留实际$finish时间。先前“观察方式影响”的判断已否定；不将这两项算作对齐，也不忽略dsim的delay去迎合该结果。六共同源使用延迟NBA及显式delay后复制；两个native专用模型另外验证阻塞赋值内delay。verify.py同时检查11个探针的源码hash、实际状态和预期差异清单，差异不隐藏。

macOS ASan/UBSan parser单测、八语料各三轮清理、八个最终实际生成程序和完整ordered事件（保留同刻变化）通过，含两个真实双线程模型，leak检测关闭。sanitizers保存实际完整C++、hash和日志。早期sanitizer运行在生成文件仍更新时抓到了旧effects/timing/parallel程序，最终身份检查拒绝；缺失的两份新输入和三个最终程序已重新运行，原始失败日志保留，runtime-results.json与final-identity.json逐项核对。入口run-sanitizers.py、verify-sanitizer-ordered.py。

本地原九项定向CTest通过177.75秒，随后最终新增八模型数组回归单独复验75.94秒通过；此前八项既有回归的生产代码未再改变，不把第一版数组回归冒充最终八模型执行。898文件源包在source-manifest.json/source-archive.json逐项冻结，包含最终测试/文档/校验器，排除本批验收输出和plan1017.md；冻结后所列源码不再修改。Linux同源干净构建七项CTest 242.5 秒全部通过、退出0。十份完整实际C++跨平台字节一致，八模型全部ordered逐信号事件（保留同刻变化）跨平台一致；Linux六共同源1317直接位/1056数组观察位再次对照相同原始VCS通过。见results.json、platform-identity.json、platform-waveforms.json与linux-vcs-results.json。

复跑：ctest --test-dir build -R '^rtl_array_copy$' --output-on-failure；python3 validation/m41-array-copy/verify.py。run-vcs.py/run-probes.py接受输入和输出目录，原始源/日志/状态/VCD均保留。范围见[数组整体赋值](../../docs/array-copy.md)。仍缺动态前缀、array slice/条件表达式/拼接/赋值模式、整体声明初始化、数组连续赋值/形参、动态/关联数组和队列、变量inout/ref、一般层次数组表达式及多维readmem。package/interface/class、完整SVA/UVM/事件区域和M35/M36/M38历史差异未解决。本批未跑全量CTest、Linux sanitizers或新速度测量，不称全部SV/VCS功能或性能已对齐。

最终冻结包SHA256 4ffc1d350614856b31f4b1be6bcef4f9361a6ca2a7487665530c739c16dfbfa8，898个所列源码与本地及Linux清单逐项一致。所有共同源比较均限定settled位时间线，三个原始边界差异和native专用用例未混入共同源PASS数量。
