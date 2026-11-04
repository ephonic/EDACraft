# M101 cases / final / bind 验收

原始病例、根因和支持边界见 [用例复核](../../docs/cases-review-20261025.md)。`tests/cases_archive/inventory.json` 保留11个顶层归档和1个follow-up的输入及oracle来源；5个不同输入不改写、不移除bind/final观察器。`run-vcs.py` 在103上对原样输入重新编译运行，`verify-vcs.py` 核对来源哈希及全部3754行输出；6个专项模型的输出oracle也来自该轮VCS。`reference/` 下完整原始日志留在工作区，结构化复核见 vcs-alignment.json。

`tests/final_bind/regression.py` 验证8模型、49份全信号VCD、8次预测失败回放、9项拒绝；两个模型必须实际两分区，调度器kernel另验双分区结束输出和全局finish重放。`tests/cases_archive/regression.py` 检查5组2759次采样/423384位观察及完整transport顺序。旧comb_partial回归31份VCD/7次回滚/6项拒绝通过；parser重复清理单测增加绑定/参数化克隆/final标志及失败清理。sanitizer.json记录5份实际生成程序ASan/UBSan通过。

本批只执行针对性检查，不声明完整SystemVerilog/VCS兼容或新的速度结论。发布身份及实际安装入口复核见 release-summary.json。

实现源 `3ceff4243fd65fd83d2be20439473c46abac5e8c`。macOS 发布 `20261025T122958527099Z-f2798b13255d`，Linux 发布 `20261025T123003Z-3ceff42`，两端各7项针对性发布检查通过；每端新final/bind与既有comb_partial共80份VCD、15次回滚及15项明确拒绝，原始五组全部独立oracle/完整VCS输出通过。跨平台68份C++、80份完整VCD及97份非编译输出逐字节相同。

616项本地发布输入、1576份源码包文件分别核对到Git，八份运行时快照各端核对；实际安装入口重新生成13份C++，各端编译运行原始u13用例1536行输出对齐。5份sanitizer生成程序与实际两端入口生成的无波形C++哈希一致。保留原始归档与harness排除记录，未跑完整历史suite、未新增性能测量。
