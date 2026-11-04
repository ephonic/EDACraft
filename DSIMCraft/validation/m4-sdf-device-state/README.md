# DEVICE / IOPATH 交错回标修正

原实现按源顺序覆盖同一张路径表，实际 VCS 对照发现错误：两个输入先后变化的 `late-device` 在旧443编译器中于229ps输出，VCS在240ps输出。本批18个独立场景各执行三次VCS，保留54次原始波形、TRACE、注解日志及未改动的csdf缓存身份；两份归档和独立核对见[oracle-verification.json](oracle-verification.json)。

生产注解为每个展开的路径记录IOPATH/DEVICE来源。尚无另一来源更新时，ABSOLUTE替换原值；另一来源曾更新时，ABSOLUTE与当前有效值按MAXIMUM合并。INCREMENT读取并修改当前有效值。初始模型值不视为一次IOPATH更新：初始31、首次DEVICE7仍为7；初始31、DEVICE增量2为33。交错IO19、DEVICE7、IO3保留19；随后DEVICE增量−2为17。这个规则不是两段运行时延迟，也不是两张独立表求和。

完整1/2/3/6值先合并基本转换，再推导X转换。IO(7,23,11)、DEVICE(19,3,29)的1→X为23，不能对已展开12项直接取max。条件、边沿、ifnone和路径输入时间戳保持原模型语义。没有修改运行时、波形、并行实现及RTL/门级parser。

冻结源码446文件，归档SHA256 `20336452e4367d90a28be3b09d509c3616773aebe0ac9aec1f71da35a6e6a9bf`，身份见[source.json](source.json)。相对443修改五个生产/CMake文件和旧流程的一个等价控制，新增三个测试文件。实际CLI的18场景×五后端通过：540份完整ordered/settled VCD/raw/Zstd捕获、270次直接vendor物理位比较、40次不混合来源场景的旧443完整C++身份。独立重解码全部54份原VCS波形及全部native捕获，见[本地核对](local-validation.json)。VCS对照是物理时间稳定态位及TRACE；native各后端/codec另作完整事件流对照，不能称为VCS delta顺序一致性证明。

本地既有99项已全部通过（789.61s），另18新流程单独完整执行；446源Linux完整100项也全部通过（994.27s），详细日志逐项保存。13264份原始文件归档`02d53c892919a9da3adefca95896d35b5037ed2f94e586c13d27ced1647920f7`独立核对PASS：540份DEVICE跨平台完整流/270次vendor物理位、252份全局波形与既有Linux记录一致，见[Linux核对](linux-verification.json)。该回归使用上述实际VCS生成的冻结参考，没有新增vendor运行、Linux sanitizer或性能结论。旧437失败结果保留。后继450另修正同定义模型通配范围，见[模型身份修正](../m4-sdf-model-alias/README.md)；primitive DEVICE及一般脉冲等仍未支持。

`alias_inputs.py`另生成21个vendor探针，分别区分同体模型、注释/空白、不同精度/单位、初始路径、功能体和边沿，覆盖PORT/DEVICE/IOPATH。它们收集模块合并的证据，不参与这18项既有参考的生成或覆盖，也不代替native支持。
