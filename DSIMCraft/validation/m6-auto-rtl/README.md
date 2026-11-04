# 普通 RTL 自动并行编译接入

冻结472文件，源压缩包SHA256 `45f3f760bafdd1aebccb85e64bd57a9c7f69e571c03985b1797685ae7d223867`，见[source.json](source.json)与[相对467变更](source-changes.json)。默认关闭 `--threads`；本批没有新的性能测量，也没有完成整个VCS功能目标。

## 已执行及独立复核

- `parallel_compiled` CTest PASS，176.21s：17配置、51实际程序，串行/1/4内核；288捕获、192完整编码流对照、327个别信号有序流比较。包含8类RTL及root MIPD、ff IOPATH、IC+IOPATH+HOLD三种SDF场景各通用/专用作业/组合优化后端；90次既有VCS参考检查。归档于[local](local)，2262文件[manifest](local-manifest.json)，[独立复算](local-verification.json)。不要求独立信号间全局有序交错相同。
- 生成程序屏障证明两个OS线程实际重叠执行；12个非法CLI或dump-task组合拒绝，保护既有输出。
- 10项内核/parser相关CTest全通过，4.19s；串行语言、148捕获dump-task回归2项通过，95.75s。日志分别为[parallel-regressions.log](parallel-regressions.log)、[default-regressions.log](default-regressions.log)。不把这13项称为完整112项套件。
- 4个实际生成程序的macOS ASan/UBSan：32捕获/16完整比较，含层次循环、258位延时NBA、部分端口多驱动和SDF输入延迟；[实际结果](generated-sanitizers/results.json)。独立的语义遍历/自然静止API sanitizer通过；不宣称Linux sanitizer或LSan。
- 1个实际生成的部分端口/多驱动程序TSan通过，含并行波形和4个异步压缩线程；4捕获/2完整比较，见[结果](thread-sanitizer/results.json)。
- 16类默认关闭程序的完整CPP、语义IR（仅SDF三项生成耗时字段除外）与冻结467编译器相同；替换冻结467 runtime后，完整Clang预处理也相同，见[默认关闭验证](serial-full-identity/results.json)。旧编译器在层次循环用例会崩溃，因此该用例不参与旧版身份声明。
- 新VCS W-2024.09三类RTL各三次：独立过程、层次参数/匿名原语delay、258位四态delay，1644物理位时间线比较全通过。75原始文件归档SHA256 `e42292b4800b9fa075caed1f4b739e80442a1c592e15f2e1422a6f9561029660`，原进程终止0且已消失；[归档核对](vendor-reference-archive.json)、[独立比较](vendor-verification.json)。不声明完整有序VCS流等价或速度收益。

## 保留的失败与修正

首次自动RTL回归在层次子模块`repeat`展开时崩溃。旧467同样崩溃，UBSan定位到模块AST复制遍历中的空节点。修正`VeriLoopStmt`复制的可选init/judge/iter节点，保留循环类型及父节点；新增五类层次循环、两种参数和三次重复语义遍历，正常及ASan/UBSan通过。原失败在[initial-failure.json](initial-failure.json)。

后继SDF测试夹具添加独立域时缺少空白造成语法失败；修正后发现ff旧oracle使用ps tick、物理读取器使用fs，明确按夹具固定1ps换算。两次失败原样保存在`automatic-sdf-probes-failure.json`与`automatic-sdf-fixed-failure.json`，没有删去ff或改用仅stdout检查。线程重叠探针的初版替换标记也匹配到API内部的`engine.run()`，改为匹配生成main独立行后通过。

## Linux验证

原任务 `/tmp/dsim-auto-rtl-linux-1018-RQuJRF2C`、PID2577992实际终止0且已消失；5027文件归档SHA256 `15db40487b49fbdf4b62adf5e3d83ec0a1ddcaf7fed860719032249635679cb2` 下载/manifest核对PASS。同源13项受影响CTest全通过，371.73s；288并行捕获与本地完整一致、51份整个生成CPP逐字相同，148dump捕获也与本地完整一致。重发射两份原始全量SDF后，确认仅runtime替换、语义IR及整个GCC预处理身份相同；没有新的全量仿真或计时。见[Linux独立验收](linux-verification.json)。该任务登记112项，仅执行上述13项，不声称完整112项或Linux sanitizer。

上一批467的完整110项原任务 `/tmp/dsim-dump-tasks-linux-1018-F7pGRFlw`、PID3265210仍在运行，未重启。两任务的功能验证曾重叠，均不提供性能数据。

## 使用边界与后续

每个gate scope和端口当前作为一个原子域；不会按名义IOPATH或RTL正delay自动切边。相互独立域可以并行执行，真实全量网表的内部并行、安全lookahead、自动预测器及增量回滚仍待推进。`--threads`暂不支持dump系统任务，但显式CLI波形/异步压缩可用。每个事件前沿的全局结束事务与同步成本未优化。详见[功能说明](../../docs/automatic-parallel.md)。

复算：`python3 validation/m6-auto-rtl/verify_local.py`。Linux原任务实际终止且原shell消失后才能取回归档；不得因观察超时重新启动。源码与原始设计文件保持冻结身份。
