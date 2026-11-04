# SDF 专用作业与条件边沿修正

432文件最终源SHA256为`1076ce437cc65a49f720a42e51ba7ea7cbd773973fb3d6c989f3796531ee1dd4`，冻结根为`/tmp/dsim-sdf-jobs-vcs-frozen-1018`。相对430基线，新增实际CLI/kernel两份测试，修改生产runtime、编译器/入口、CTest，以及条件边沿选择和两份条件测试。两个Verilog parser和SDF parser保持分离且未改。最初尚未修正条件边沿的432源4039774保存在source-initial.json及独立源包，不作为最终验收。

新增默认关闭的`--gate-sdf-jobs`，要求标量SDF后端。IC/IOPATH共享handler转为独立拥有的作业，去除通用Process和fixed-wait站点；初始化位置保持进程注册顺序，后继唤醒仍占原Active FIFO位置，保留step、合并唤醒、自触发、定时交付及取消。Ready大小仍为8字节，新tag使用原padding；batch扫描不会跨越作业。普通门/RTL过程协议和原始输入不变；未减少事件数量，没有性能收益声明。

初始八类CLI定向已通过：四后端192份完整ordered/settled×VCD/raw/Zstd捕获、16份实际生成边界/拒绝预测回放，以及五档预算失败的stdout/stderr一致，见targeted-initial.log；本批完整92项包含修正后的条件九例/四后端/216捕获和16回放，正在执行。四种实际内核（generic、compact、wheel、batch）本地ASan/UBSan已通过。local-checks.json核对默认/标量完整旧SDF的同Clang预处理：只对Ready声明的一处换行作精确替换后，整个程序逐字相同；不称原始预处理字节完全相同。最初未处理该换行，以及小例错误展开宽值include的辅助检查失败分别保留，未放宽其他代码比较。

full_local.py仅对实际旧完整scalar CPP作整个runtime/path头替换与六处生产作业生成替换，macOS Clang/O1已实际编译执行全部128笔并匹配。CPP SHA256为`2f2c8012d0c43cd152ad8ef2b374f2f4ced2ab10c64bd8605c561630c79d3bac`，见full-local/results.json。这不是最终新编译器的全量生成证明，也不是性能计时。

430旧批Linux五项通过，但实际新VCS在edge用例发现条件为真、源边沿不匹配时仍须选择ifnone。旧源默认错误地抑制fallback，未验收；原始失败和VCS证据见../m4-conditional-paths/failures。当前生产path.hpp及独立oracle已修正，后继完整92项和新VCS九例重新验证。其余八类VCS各三次及输出选择时刻探针已独立观察通过，但不替代当前源的整批对照。

最终432源的Linux任务已启动，原会话45045，根`/tmp/dsim-sdf-jobs-1018-JOOGQrfl`。范围为干净完整92项、实际新VCS九类/选择时刻探针、六类混合流程，以及当前编译器重读完整原SDF生成默认/标量身份与jobs/jobs-wheel两种O2程序各128笔。仅观察同一任务，不因观察超时重启；性能复测已终止并审计，此任务无性能测量。完成前不称Linux或新VCS整批通过。

最终432源macOS完整92/92已在原会话96153正常退出0（452.89s）。实际jobs-wheel/checks预测回放程序也通过本地ASan/UBSan，两份Zstd捕获与边界对照逐事件一致；verify_local.py --capture已保存并独立核对所有源码、完整日志、192+216常规捕获及16+16回放、实际生成替换、五档预算和原始128输出，local-validation.json PASS。Linux仍跟踪原任务45045，不称已完成。


最终Linux原任务已正常退出0，3549份原始证据归档18ffbeb1c43ea8d9c562079d7783bf567b7c82b0f46a39e72817b307d81ee860已下载。以/tmp/dsim-sdf-jobs-vcs-frozen-1018执行verify.py独立核对PASS，verification.json为最终状态：两平台各92项、408完整常规捕获/32回放、九类新VCS各三次/选择时刻探针三次、六类公共流程581物理位，以及实际全量重生成jobs/jobs-wheel各128笔。完整生成CPP及IR、关闭选项预处理身份已重算；不是性能数据，默认关闭。后继消融见../m5-sdf-ablation。
