# M164：DPI-C function 的真实执行

输入仍是用户 REPORT-GAP2（实际路径 rtl-tests/complex，SHA256 0a316c371261b0ab962f0a46a7e4818d6df74d70f4c051dc044720b798eba366）。本批接通原始 q11 的 C 调用和公开 UVM 的 DPI export 语法阻塞，完整边界见 [DPI 文档](../../docs/dpi.md)。未修改公开 UVM 2020.3.1 仍不能原生编译运行：globals:124 的 export 之后，下一处语法首错为 uvm_object.svh:70 extern；没有删库、移除关键字或将预处理成功算成运行成功。

实现贯通 parser 克隆元数据、ABI 参数与结果、C 共享库加载、作用域 API 和嵌套 SV 回调。export 函数即使没有 SV 调用点也编译执行，自动生命周期使用原内核的激活帧。普通/context 调用在进入 C 前退出预测并恢复，随后正式执行一次；pure 以用户无副作用合同为前提。手工 checkpoint 不能撤销 C 外部状态。含 DPI 模型暂串行回退，不能以 --threads 请求宣称真实多分区。

新增六个模型在默认/时间轮/请求双线程三种路径执行，VCD、DWF、独立 writer、ordered/settled 波形逐信号一致，共110捕获；2回退/1提交、23编译拒绝、5运行时拒绝。导出检查负数、97位四态、65位bit、字符串、repeat局部控制、无参void、多实例作用域切换和嵌套context；C原型与真实C定义一起编译检查。原始q11字节不改，提供C库后输出 PROBE_DPI: 6。相关 class_access、automatic_subroutines、package_exports、waveform_selection、gate_source 五组开发回归通过。

开发失败保留在 dev：初次同层返回符号查找导致类型冲突；合成单参数列表使用非法空第二子节点导致崩溃；回调在collapse_ports前生成使信号编号错位。修正后完整新组重跑。首次Mac C库未加undefined dynamic_lookup导致链接失败；随后明确平台参数。首次负数测试误用未显式定宽的大十进制常量，改为64位后验证ABI；不把测试oracle修正说成语言加速。

103唯一只读连接以255返回，服务器无响应；未修改远端进程/入口，未重启M161超时构建。本批没有新VCS/Intel或速度/压缩率结论。用户 experiments/matvec16 未修改。最终发布、sanitizer与实际入口证据继续记录在本目录；原始模型/动态库/波形放在外部证据归档，不提交生成二进制或公开UVM展开源码。

ASan/UBSan 前端六正例/19签名反例、完整parser恢复清理、六实际生成程序和真实C库均通过；replay也无sanitizer诊断，输出和已验收replay逐字节波形相同。首次sanitizer脚本最后错误地将replay与连续运行的文件逐字节比较，被额外的空horizon时间标记拦截；所有信号时间线一致，改为同一replay参考后审计已完成的执行，不重跑已通过程序。保留失败日志并由 finalize-sanitizers.py 复核，没有把它当作模拟器修复。没有LSan声明。TSan 验证非DPI真实双分区+独立writer，以及DPI context回调/已插桩C库+独立writer（明确1分区回退）通过。


最终本地验收：实现冻结f3e10bc982753805c08e6a05fdb8fb3c34dd7ca5（a85ad740的仿真实现不变，补发布脚本DPI白名单与ABI头输入绑定）；1875源码成员、1044发布输入全部与Git源包匹配。Mac六组615捕获与mandatory parser/格式/原生DB通过，22CPP和开发验收仅默认C库绝对路径不同。Mac稳定20261029T061645038811Z-843dfb2c26c9已激活；实际入口重编译原始q11/r02省略--top通过，C回调及完整/所选范围异步波形与候选相同。初次发布命令因白名单漏dpi被CLI拒绝，未创建候选或激活；修脚本后才构建并跑完六组。

实际入口公开UVM预处理1888084字节/166依赖/原SHA，326文件与固定参考归档一致；native仍在object:70 extern正常拒绝且不生成部分CPP。完整目标继续，103未更新；没有把语法首错推进当作UVM运行验收。外部证据目录为~/vibe-coding/dsim-test/evidence/m164-dpi，保存源码、开发/发布原始记录及逐成员哈希归档。
