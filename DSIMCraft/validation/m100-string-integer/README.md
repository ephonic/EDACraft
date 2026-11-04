# M100 字符串整数方法验收

实现范围、参数规则和两类已观察的 VCS 差异见 [功能说明](../../docs/string-integer.md)。`tests/string_integer` 含六个模型；五个用于同源输出/完整物理位对齐，`boundaries` 专门记录宽 putc 实参与格式化事件通知的已知不同结果，不混入通过数量。

回归检查 serial、time-wheel、threads=2 的 ordered/settled 全信号流；parallel 模型必须实际产生两分区。每模型还编译无波形版本，并注入失败预测验证输出与完整 ordered 波形回放。拒绝用例检查 const ref 修改、void 返回值误用、参数数量和类型以及尚未实现的实数方法。

`run-vcs.py` 在103上编译原始输入加独立 dump wrapper；`verify-vcs.py` 检查源码哈希、完整功能输出、位集合和 settled 时间线。边界差异采用显式预期，不忽略失败或单边波形位。实际生成程序的 ASan/UBSan 由 `sanitize.py` 复核。发布结果完成后写入本目录 JSON。

开发候选验收：六模型、42份VCD、六次失败预测回放及10个拒绝用例通过；parallel 实际两分区。五个同源模型全部608物理位及完整输出与VCS一致，boundaries 的差异按独立预期保留。原始VCS三组探针的源码及结果见 probes，哈希逐一核对；不会将差异改写为通过。稳定版本与生成程序sanitizer结果另记。

发布实现源 `86cbed8266f6c52918af83f4e04a76fefa4b9066`。两端各七项发布检查（RTL parser、格式 parser、原生DB单测、新方法、既有字符串、字符串子程序、门级source）通过。每端三个字符串组22模型、119份VCD、14次回滚、46项明确拒绝；跨平台87份C++、119份完整VCD、162份非编译输出逐字节相同。六份实际生成的无波形程序ASan/UBSan通过，哈希与两端稳定版一致。

macOS发布 `20261025T114149428103Z-210ee24b418f`，Linux发布 `20261025T114154Z-86cbed8`；574项本地发布输入和1533份打包源码分别与Git逐字节匹配，每端8份不可变运行时快照核对。实际安装入口重新生成六模型C++并运行重叠ref用例，输出及完整波形一致。两端各自再对照VCS验收五模型/608位；差异模型保留原始不同结果。身份及证据见 release-summary.json、vcs-macos-release.json、vcs-linux-release.json。只做针对性检查，未运行完整历史suite、未新增性能测量。
