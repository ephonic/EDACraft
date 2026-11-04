# SDF 模块路径延迟表去重

生产CLI新增默认关闭的`--gate-path-dictionary`。每条弧保留自己的输入、边沿及条件/ifnone元数据，12转换延迟数组按实际全局tick去重后共享；输入时间戳、最新源/同刻最小选择、溢出、剩余延迟和事件投递保持原规则。没有修改runtime、原path selector、RTL/gate parser、波形或并行头文件；新selector仅在启用选项时加入生成C++。

已验收432源的完整原始SDF生成程序有867,982条路径弧、1,805种不同的12转换表（源CPP身份及统计见`table-study.json`）。原普通弧104字节，候选元数据12字节；不含哨兵的静态数据按这些实际计数从90,270,128降至10,589,064字节。这是表布局计算，不能当实际RSS或CPU收益；新内核通过编译期sizeof断言核对布局。

442文件候选源`5bc5ce3964515357f32d025e7aa8951880a9c1e945808b7586fcde4c1010ab75`已冻结。两种实际内核的随机/手写对照及ASan/UBSan通过；实际CLI九例/四后端/开关两态的72次完整C++身份、432份完整捕获、24份生成回放和16份实际sanitizer生成回放通过。原始全量表变换副本执行128笔匹配，独立恢复整个旧C++一致；见[针对性核对](local-checks.json)。既有97项也已全部通过（911.31s），完整详细日志与清单已保存，见[回归核对](local-suite.json)。这些是442冻结源的结果，不替代后继PORT修正源验收。

验证入口：

- `tests/path_dictionary/regression.py`：实际CLI的四后端×开关两态；关闭时完整C++与旧437编译器逐字相同，启用时独立解码字典并恢复旧布局后完整C++逐字相同；完整IR只排除明确新选项与三个耗时字段。ordered/settled×VCD/raw/Zstd、stdout/stderr和预算边界逐项对照。
- `tests/path_dictionary/checkpoint.py`：实际生成程序保留待交付MIPD/路径事件，在拒绝预测后恢复并接受提交；`--sanitize`对实际生成程序插桩。
- `full_local.py`：在已验收的全量jobs程序上仅转换静态表与selector入口，独立还原整个C++后执行全部128笔。它不能替代新编译器从原始网表/Liberty/SDF重新生成整个设计的Linux验收。

没有新性能收益或默认采用结论。原时间轮/jobs五程序消融已结束，该候选不在其中。442源的Linux新编译器全量重生成已正常结束0，原始归档`4e09670dd9ed59de8e79c10d9ae4ce90859d93c074ec7ffbf8fd97ce3bf2257e`已下载独立审计PASS：原始网表/Liberty/SDF生成dictionary和dictionary-wheel，各执行128笔；867,982弧/1,805表，独立展开后整个C++恢复旧432 jobs身份，整个IR只排除三个实际耗时和明确新选项字段后相同，检查未禁用。见[全量核对](full-verification.json)。不包含Linux完整测试套件或性能测量。新的PORT/DEVICE VCS对照发现语义差异，后继集成须采用修正源，不能把442的这些通过称为完整vendor兼容。
