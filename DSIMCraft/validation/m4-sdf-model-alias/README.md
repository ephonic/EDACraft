# 模块定义身份与SDF通配回标

原437的四个通配配置仍有差异：VCS将完全相同的S/D单元模型合并，`CELLTYPE D / INSTANCE *`随之影响S源单元；原dsim仅匹配D名称，漏掉源端延迟。新增21场景覆盖PORT、DEVICE和IOPATH，分别改变注释/空白、时间精度、单位、初始路径、功能和边沿。每个场景实际运行VCS三次，63次原始结果归档`098a9da3793883c66425a8ec8975ea1a0b125b557d81dc813a0fa1a019bca913`，位于`../m4-sdf-device-state/alias-v2-evidence`；定向参考独立解码核对后冻结，未覆盖原437失败结果。

时序模型reader保留预处理后完整token定义身份：忽略模块声明名、注释和空白，时间单位与精度参与身份。功能体、端口顺序、specify路径/初值/条件/边沿/检查等token必须相同。注解消费者据此建立实际已用叶模型的同定义组，仅对`INSTANCE *`扩展目标；同一接收端不重复加入，目标使用稳定名称索引顺序。裸拓扑绑定仍严格按CELLTYPE匹配，指定实例只更新该实例，类型不符/不存在仍报错。报告的`wildcard_alias_targets`统计额外目标。

每个实例继续保留自身运行时状态。本批没有减少仿真事件，没有新速度结论；RTL/gate parser及runtime/parallel/wave头均未修改。功能体仍不由时序元数据reader编译。一般布尔等价、不同声明语法/内部重命名的模型归并、primitive DEVICE及完整SDF语义仍待实现。

450文件源码SHA256为`e953573c2bf8037078400076a3e1ba493572f97ab3b2bec290a5f3af722beeca`，见[source.json](source.json)。实际新CLI的21场景×三后端全部通过，378份完整ordered/settled VCD/raw/Zstd捕获、189次直接vendor物理位比较、45次负例整个CPP与446相同。另有五项绑定边界检查、模型身份单元测试、五项reader/binding/numeric CTest及四配置PORT/DEVICE完整流/八份回滚捕获通过。

[本地核对](local-validation.json)还重新对照原32配置的84份VCS原始波形：16个发生通配变化的程序实际由450编译执行；112个未变程序由450重新发射整个C++，逐字匹配已执行446版本后复用其捕获。全部32配置通过，原六项失败均有对应修正证据。这个执行/身份复用范围明确记录在结果中，不表示128个程序全部重新编译执行，也不表示重新运行了原32组VCS。原始112次发射及完整身份清单见`original-case-proof/`、`original-proof-manifest.json`。

Linux450原任务已正常结束0，3796份原始文件归档`cac1179c73ac1dbd651f76ce811409830988b3346b390b35855549113d34c0a3`已下载并独立核对：六项受影响CTest通过，378份新21场景及144份原六失败配置捕获跨平台完整一致，原始全量SDF两版完整C++/IR身份保持。见[linux-verification.json](linux-verification.json)。前继446完整100项与此分开记录；不是450完整102项。`prove_full.py`未重编译或重跑那两个全量仿真程序，只证明与已验收源码相同。普通网表自动并行、自动预测器和更大范围波形/语言功能继续推进。
