# 编译式 SDF 延迟与时序检查运行时

`--sdf-annotate` 将模型匹配后的 IOPATH 表、逐接收输入 INTERCONNECT 延迟及九类常用时序检查编译进门级仿真程序。RTL 测试平台、结构门级网表、Liberty 功能与 specify 元数据使用各自的前端。单元功能仍来自 Liberty；模型 Verilog 的功能体只用于独立 VCS 对照，不由该元数据 reader 编译。

```sh
dsim --gate-netlist design.v --gate-top dut --liberty cells.lib \
  --gate-models models.v --sdf-annotate delay.sdf tb.v -o simv
```

SDF 实例路径相对于 `--gate-top`。同一个 gate top 在测试平台中的每个实例安装独立状态并使用同一份静态注解；暂不提供按测试平台实例选择注解文件或运行时 `$sdf_annotate`。指定 `--wave-support` 可同时记录 VCD / DWF。全局 tick 自动取实际 RTL scope 与已用时序模型的最细精度；此入口不能传 `--sdf-tick`。

支持：scalar / 已展开的 bit pin、parallel/full path、可选 posedge/negedge、1/2/3/6/12 延迟表、独立 SDF 与模型初始 min/typ/max、ABSOLUTE / INCREMENT，以及此前已验证的逐次模型精度舍入和负路径夹零。未被 SDF 更新的 specify 路径使用实际模型基值。四态输出转换使用完整 12 项表。

实际输入沿在解析值发布时记录，包含时刻及前后四态值。输出功能先求值到私有 raw net，再按匹配输入沿的最新时刻选择路径；同一时刻的合格路径取最小延迟。VCS 对照确认 0 时刻初始化（包含 #0 变化）不按输入边沿过滤，后续时刻按边沿选择。每个输出保持独立驱动身份、待交付事件和取消状态；输入不变值不推迟已有交付，短脉冲可取消。有限微例已对照 VCS，不能由此推断所有 specify/pulse 语义已完整兼容。

有限的[条件路径与ifnone执行](conditional-paths.md)已通过432组合源两平台各92项、九类新VCS各三次及实际回滚验收，见[独立核对](../validation/m5-sdf-jobs/verification.json)。新增PORT/DEVICE实际回标已修正新VCS发现的多驱动PORT及DEVICE/IOPATH交错更新差异，范围与验收见下文。路径极性、显式 pulse 声明、RETAIN / pulse threshold仍不支持，编译时明确失败。九类常用timing-check默认执行，具体事件/边沿/条件匹配、负limit模式及其余检查/notifier限制见[时序检查](timing-checks.md)；用户主动传 `--no-timingchecks` 可明确跳过检查，不能据此声称运行了检查/notifier。此前“部分 ABSOLUTE 成零后 INCREMENT”的四组 VCS 读回限制仍保留，不猜测结果。

路径的输入沿历史、raw 输出前值及待交付事件均随检查点恢复。自动预测器和自动分区不在此入口中。关闭 SDF 路径时，不启用额外沿记录状态；8 组合的完整 runtime 预处理结果与前一冻结版本相同。该批不改变零延时性能结论，也没有一般 SDF 性能测量。

## 接收端互连已接入

INTERCONNECT 绑定到实际叶单元输入，默认分配独立私有接收 pin、驱动通道和取消状态；同一物理源的其他接收端保持自己的延迟。输入延时按新值选择 rise/fall/off/X-min，再交给接收单元功能和已有 IOPATH。波形字典记录实际私有 pin；输入历史、待交付事件和取消代际随已有检查点恢复。结构驱动数与源网是否为顶层input共同决定ABS规则：多驱动或顶层input使用MAXIMUM，普通内部单驱动使用末次非零ABS更新；INC修改当前接收有效值，按接收模型精度逐次量化。ABSOLUTE写零保留已有正MIPD，INCREMENT可清零。新增12场景/36次VCS及本地216捕获已验证顶层input与内部单驱动的区别，见[顶层输入更新](../validation/m4-sdf-root-input/README.md)；该新修正的Linux五项定向CTest、248跨平台捕获及原始全量三版代码身份已独立验收通过。

实验选项`--gate-fold-zero-inputs`默认关闭，仅用于SDF门级代码生成。最终rise/fall/off三值全零的IC/PORT复用源网，省去私有槽、延迟通道及作业，接收引脚保留波形别名；IOPATH和检查仍执行，IR记录`zero_input_pins_folded`。九例实际三后端及生成回滚/本地sanitizer已通过；原始全量设计候选与默认通用后端的功能验证均已通过。scalar/jobs候选六轮配对CPU改善中位数35.39%，默认通用后端测速及独立复测待做，开关仍关闭，见[零输入验证](../validation/m5-zero-input-fold/README.md)。

本地/Linux 完整各41项通过，29组既有VCS参考的输出与全部私有接收pin稳定态位一致，完整native VCD/DWF一致；native测试平台只替换了尚不支持的XMR monitor，未声称原始TB完全相同。4组实际生成程序覆盖拒绝预测回滚/接受提交及相同run_until边界的完整ordered/settled流；输入/输出互连串联的boundary/replay两程序另经实际ASan/UBSan通过。两平台额外通过非零5ps IOPATH接在MIPD后的组合检查，该组合检查自身未单独新跑VCS。新功能没有修改runtime/波形/并行header、RTL或gate parser；11份既有不含IC的完整SDF生成C++与冻结Linux基线逐字相同。证据见validation/m4-interconnect-runtime。

范围限普通叶输入、已验证的1/2/3/6/12值及ABS/INC/corner组合；6/12值MIPD按前三值处理，不能借用IOPATH十二转换表。层级scope目标、inout、条件/沿输入、label/RETAIN/显式pulse threshold、稀疏两值与多驱动已有非零再显式ABS零仍明确拒绝。未覆盖的标准细节和复杂corner/alias组合不作全面兼容声明。自动分区和自动预测器仍待实现。

统一流程中的非零IOPATH组合例已另外完成新VCS差分：在相同cells.v/net.v/native-tb.v上，INTERCONNECT后接5ps specify路径，完整TRACE和顶层a/x/y及两个私有接收A位的物理时间波形匹配，首次注解0errors/0warnings。该补充验证与之前只检查+5ps公式的composed.py证据分开保留。

## PORT / DEVICE 支持范围

PORT编译到叶输入的私有接收通道，按目标精度量化并保留独立取消/检查点状态；6/12值沿用MIPD前三值规则。根据VCS探针，多驱动接收输入的重复ABSOLUTE更新按MAXIMUM合并，普通内部单驱动按最后一次非零更新，已通过[六场景四后端核对](../validation/m4-sdf-port-policy/local-validation.json)。后继12场景证明顶层input即使只有一个外部驱动仍使用MAXIMUM，PORT与INTERCONNECT一致；本地实际三后端已通过，见[新增验证](../validation/m4-sdf-root-input/README.md)。

DEVICE更新指定输出的全部module paths，未指定输出时只枚举外部输出；条件、边沿、ifnone及路径输入时间来源保持原模型定义。446源已修正DEVICE/IOPATH交错更新：每条展开路径记录两类来源，首次及单来源ABSOLUTE替换，另一来源曾更新时ABSOLUTE与当前有效值MAXIMUM合并，INCREMENT修改当前有效值；基本转换合并后再推导X。初始模型值不计为IOPATH更新。实际18场景各三次VCS以及五native后端的540份捕获、270次直接物理位比较通过，见[独立核对](../validation/m4-sdf-device-state/local-validation.json)。这是编译期更新规则，不增加运行时阶段；尚未证明一般稀疏/显式12值混合等全部组合均兼容。

例如，实际模型`BUF`有输入`A`、输出`Z`及`(A=>Z)`路径时，可以在一个叶单元上同时指定输入和输出路径延迟：

```lisp
(DELAYFILE (SDFVERSION "3.0") (TIMESCALE 1ps)
  (CELL (CELLTYPE "BUF") (INSTANCE u0)
    (DELAY (ABSOLUTE
      (PORT A (3) (5) (7))
      (DEVICE Z (11) (13))))))
```

该文件通过现有`--sdf-annotate`入口编译；省略DEVICE中的`Z`表示该叶单元的全部外部输出。源文件中的PORT/DEVICE种类和更新数量会分别出现在gate IR的`port_delay_pins`/`port_delay_updates`与`device_delay_updates`字段中。

scope/inout输入、没有module path的primitive DEVICE、RETAIN/pulse threshold等仍明确拒绝。原437源新VCS的32组中26组通过三次重复，6组不一致，完整失败波形已保留；混合PORT/INTERCONNECT两种顺序均通过。后继443/446分别修正多驱动PORT和DEVICE混合更新。450源进一步按模型完整token及时间单位/精度的身份，扩展同定义叶模型的通配回标；显式实例与裸拓扑绑定保持严格类型检查。21场景各三次新VCS、三native后端378份完整捕获及绑定边界检查通过；原32配置也重新对照84份原始VCS波形通过，其中112个程序经当前完整CPP身份复用446实跑捕获，16个改变程序由450实际编译执行。原437失败结果不回写。一般模型等价及完整vendor兼容仍未证明，见[模型身份修正](../validation/m4-sdf-model-alias/README.md)。本批未更换runtime、波形、并行实现或RTL/gate parser，没有新速度结论。
