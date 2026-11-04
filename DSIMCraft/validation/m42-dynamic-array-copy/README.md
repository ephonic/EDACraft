# M42 动态前缀子数组复制与 VCS 对照

补齐静态 unpacked 数组的动态前缀过程复制：`row=a[i]`、`a[i][j]=row`、`a[i]<=#delay b[j]`。包含阻塞/NBA/延迟NBA、逐维声明顺序、宽字、net源、两态默认值、函数/automatic任务、组合/时钟依赖、分区和失败预测回放。修复RTL parser对delay中函数调用的误拒绝，新增公开入口三轮语义分析/清理检查。RTL与门级parser保持分开；没有修改调度内核、parallel头或词法语法生成文件。

每个前缀索引求值一次，完整位宽/四态逐维检查，任一无效即使整个子数组读取返回源元素默认值（四态X、两态0），目标不写入；后续索引副作用仍执行。动态复制共享已有存储器信号ID表，每个赋值点只保存声明顺序偏移表；先取样全部源字，再写入或排NBA。NBA入口捕获目标地址；阻塞赋值内delay等待后求目标地址。缓冲沿用可复制进程状态进入检查点。索引函数可能添加局部存储器，lowering保存owned MemoryIR，避免vector扩容使引用失效。动态读写集合保守覆盖整个存储器和索引，专用always中的读/partial-write限制仍在；模块数组端口连接继续只接受静态前缀。

六模型在tests/dynamic_array_copy：共同源indexed覆盖三维声明方向、动态源/目标、net源、函数局部数组及always_comb索引/元素敏感性；bounds覆盖130位数据/索引、高位非零/X、负/常量越界、四态/两态默认值及无效首索引后的函数副作用；timing覆盖动态NBA源值/目标地址入口取样、delay函数、重叠交付和always_ff；parallel覆盖一个模型的两个真实独立分区。native专用intra_delay覆盖阻塞赋值内delay的源入口取样、恢复时才求目标、automatic挂起隔离；effects检查带副作用NBA的索引与delay各一次。六例×串行/时间轮/threads2×ordered/settled×VCD/DWF为72捕获，timing/intra_delay在1ns实际失败预测回放后再核对完整ordered逐信号事件，共74次。并行模型另外核对实际partitions=2及八步数学输出，NBA独立时间线验证5号行于2ns收到10/11、4号行于3ns收到20/21。

远端10.131.254.103使用source /apps/EDAs/syn.bash及VCS W-2024.09，参数-full64 -sverilog -debug_access+all -top top -top dump，simv -no_save。四共同源字节相同，自检/TRACE与全部2591条直接导出位的settled时间线一致，无名称别名或位排除。全部2008个native数组位经同源packed观察信号逐位逐时刻核对，2591已包含这些观察信号，两数字不作为独立位数相加。verify.py拒绝未列出的数组字或未比较的其余信号。VCS同刻瞬态未称对齐；native三个后端/两波形格式及跨平台ordered比较均保留同刻变化。

六个原始探针在probes目录，源码/hash、编译/运行状态及原始日志保留。invalid与原M41 subarray接受/TRACE一致，关闭M41的动态前缀拒绝差异。四个可观察差异没有计入VCS对齐PASS：effects无delay阻塞赋值共享计数器VCS为1、dsim为10，IEEE1800-2017 10.4.1未指定左右求值相对顺序；nba和delayed中VCS按元素重复调用索引/delay，两字计数1010/210210，dsim每个表达式一次为10/210；intra_timing保持M41差异，VCS整体阻塞赋值内delay没有等待而dsim等待，分别1ns/4ns打印。四共同源避免依赖未指定的相对顺序和这些已记录边界，两个native专用模型不混入VCS共同源数目。

本地八项既有CTest全部通过264.25秒，另新增六模型74捕获回归通过；既有array_copy八模型99捕获/三次回放/16类拒绝通过。M41十份完整实际生成C++重生成字节一致，见m41-identity.json。macOS ASan/UBSan通过parser单测、六语料各三轮清理和六份最终实际生成程序（含真实双分区）；对照完整ordered逐信号事件，leak检测关闭。sanitizers保存实际C++、波形、hash及日志，final-identity.json逐项确认消费的是最终生成程序。

Linux同源干净构建九项CTest全部通过341.73秒，退出0；919文件hash逐项核验，七份完整实际生成C++跨平台字节一致，六模型完整ordered逐信号事件（保留同刻变化）及stdout跨平台一致，Linux四共同源再次对照相同VCS2591直接位/2008数组观察位通过。见results.json、platform-identity.json、platform-waveforms.json和linux-vcs-results.json。源清单919文件，包SHA256为1f3c6987e0c74bdf57e202768567916b68961a0a3996564b1972b8a9bb0a8116，source-manifest.json/source-archive.json记录来源；冻结后所列源码不再修改。plan1017.md及本批验收输出不在冻结清单。

复跑：`ctest --test-dir build -R '^rtl_dynamic_array_copy$' --output-on-failure`；`python3 validation/m42-dynamic-array-copy/verify.py`核对默认build产物；`python3 validation/m42-dynamic-array-copy/verify.py validation/m42-dynamic-array-copy/local`可核对随仓库保存的捕获。run-vcs.py/run-probes.py接受输入、输出目录；run-sanitizers.py消费已完成生成的实际CPP；run-linux.py消费带dsim-source-manifest.json的干净解包源。大型历史产物发布范围见[验收记录说明](../README.md)。

仍缺array slice/条件表达式/拼接/赋值模式、整数组初始化、连续数组赋值/形参、动态/关联数组和队列、变量inout/ref、一般层次数组表达式、多维readmem、package/interface/class、完整SVA/UVM及事件区域等。M35/M36/M38及本批原始VCS差异继续保留。未跑全量CTest、Linux sanitizers或新速度测量，不称全部SV/VCS功能或性能已对齐。
