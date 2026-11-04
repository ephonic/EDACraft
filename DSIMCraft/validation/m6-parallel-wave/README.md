# 并行全局 VCD/DWF

新增生产 `include/dsim/parallel_waveform.hpp`，接入实际 ConservativeSim / AutoConservativeSim 的窗口提交；串行 WaveCapture 与全局捕获共用 wave_detail::Capture 的声明、过滤、ordered/settled 与 native 编码器。RTL、gate、SDF parser 和标量/SDF/队列执行路径不变。

最终冻结435文件：`ea5bf4812338e44a174812a02b3c54c91f785e7f1bbe7a0c91ae2e5f60bc326d`，`/tmp/dsim-parallel-wave-fixed-frozen-1018`。相对已冻结432源只改 CMake、parallel.hpp、waveform.hpp，新增 parallel_waveform.hpp、parallel_wave.cpp、parallel_wave.py。完整清单见 source.json。

每种 generic/compact 后端覆盖42组：7场景（直接/事务普通执行、结束于6/0、异常窗口、自动正延迟图、scope过滤）×ordered/settled×3种worker/窗口配置。每组实际生成同一全局文件的VCD/raw/Zstd，共126份捕获，两后端252份。独立Python整数四态模型逐事件核对宽值、Active/NBA、多驱动、结束后未执行NBA、分区顺序和提交边界；自动图另核对手算延迟目标时间线。检测字典别名、精度、文件保护、失效订阅及关闭后继续推进。

初次定向测试中的手动预运行事务与并行内核的拓扑冻结约定冲突（simulation topology is frozen），该不合法fixture已移除；生产全局结束的窗口回滚/重放和异常回滚继续逐事件测试，未修改独立oracle。

修正版两种实际后端的本地ASan/UBSan均通过（6.13s），各126捕获并含部分挂接清理回归；初版完整94项通过（399.44s）仅保留为历史，最终修正版完整94项正在重新执行；未宣称Linux验收或性能收益。既有432源的Linux/SDF/VCS验收单独保留在m5-sdf-jobs，本批不混用它作为435源完整验收。


异常挂接探针发现：第一分区成功挂接后第二分区因事务拒绝，早先分区遗留回调可访问已释放Source。实际ASan复现heap-use-after-free，已在start异常路径撤销所有已成功挂接的分区并释放订阅；相同探针修正版ASan/UBSan退出0。加入永久attachment回归，原探针/前后日志保留。初版435（17f63f…）另留source-initial.json，不混称最终修正版；最终版本重新构建与验证。


最终435源已完成本地完整94/94（405.80s），原会话93447正常退出0；verify_local.py --capture独立核对PASS（local-validation.json）。252份常规全局VCD/raw/Zstd捕获及252份实际ASan/UBSan捕获全部按独立整数模型重算，并验证generic/compact完整流一致、别名/精度和部分挂接清理。所有原始捕获与日志保存于local及capture-manifest.json。本次只称本地验收；为避免干扰正在运行的SDF性能消融，未启动435源Linux构建/回归。普通Verilog自动并行、百万信号分组索引和异步压缩仍未完成。


后继Linux定向验证已完成：复用442冻结源5bc5ce39，所有既有include头及global-wave测试/reader与435逐项哈希相同；只配置并构建generic/compact两个目标。实际两项均通过（0.74s），源进程1861167退出且shell.exit=0；1024文件归档f9267c92c1db2cf0222489ba1e34cfd8e8260f5bbb0b0f4869e32fc87c4eb834下载并逐文件核对。252份VCD/raw/Zstd完整流按独立模型重算，并与435本地Mac归档逐事件相同，含部分挂接清理，见[targeted-linux/verification.json](targeted-linux/verification.json)。不把这两项称为435或442的Linux完整套件，没有Linux sanitizer或性能收益声明。
