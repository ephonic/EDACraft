# Sentaurus Newton 诊断日志

`audit_sentaurus_newton_diagnostics` 支持 W-2024.09 单器件 Poisson，或 Poisson / Electron / Hole 联立系统。在商业命令的全局 `Math` 中开启 `PrintRhsPerEquation CNormPrint` 后，可读取逐方程 RHS 最大值、自由度索引及坐标，以及逐方程最大更新误差、顶点、坐标和报告变量值。

```python
from tcad.validation import audit_sentaurus_newton_diagnostics

report = audit_sentaurus_newton_diagnostics(log_text, initial_rhs_tolerance=1e-35)
print(report['history']['rejected_table_indices'])
print(report['failures'])
```

只移除已完整识别的诊断行，再调用现有严格收敛审计；原日志行号保持。未知格式、缺失或重复方程、非有限值、数值下溢、负范数和 RHS 汇总不一致均不能获得通过。原有 `audit_sentaurus_nonlinear_convergence` 接口和行为保持。

`following_c_norm` 表示紧随该迭代行打印的诊断，不推断未输出的内部 Newton 状态。RHS 的 `imax` 与 C-norm 的 `vertex` 分别保留，不混同两种编号。坐标单位为日志报告的微米。当前不支持混合模式实例列及其他方程系统。

诊断不放宽迭代上限、更新误差或 RHS 退出条件。失败后重试成功仍会拒绝；`diagnostics_valid` 仅表示诊断格式检查通过，收敛结论应读取 `valid` 和 `history`。这些结果不证明物理根因、剖面精度或一般器件对齐。

NewtonPlot 在迭代表内输出的完整 `writing <filename>.tdr (TDR format) ... done.` 行会被记录为对应迭代的 `newtonplot_output`（文件名及原始行号），再从收敛审计输入中移除。每个迭代最多接受一次此消息；重复、未完成、带错误或未知格式的输出仍会拒绝。此接口只解析日志，不读取该文件，也不证明文件存在、状态精度或文件与迭代的物理对应关系。原始 TDR、官方转换结果和网格／字段验证应另行核验。

空间字段的单位元数据检查与物理验收须分开。W-2024.09 的本仓库均匀低场控制中，正常 Plot 与同状态 NewtonPlot 的解数组、迁移率及单元电流逐值相同；单元电流数值仍无法按所标记的 A/cm² 直接通过独立 SG 验收。不要以两类输出相同、单位标签正确或数值比值稳定为由自动换算这类电流。使用已核验的密度、电势、单元迁移率、官方常数及几何重建 SG 通量，并与 `ContactCurrentFlux` 交叉核对；八个低场点在原 1e-8 相对预算下通过。相关边界、常数来源和完整证据见 320 低场控制 (`validation/hfs_low_field_probe_20261030/ACCEPTANCE.md`; historical archive, not bundled)。该控制也观察到 0.99—1.01 V/cm 之间的迁移率分支，尚未证明确切阈值或修复原失败迭代。

## 低场临界参考必须保留偏置路径

在相同材料、514 顶点／512 三角形网格及 W-2024.09 数值设置下，直接到达、从 0.99 V/cm 接近、从 1.01 V/cm 接近和复现原完整历史这四条路径，在最终 1 V/cm 的总电流最多相差约 3.3065e-4。四条路径全部 34 张非线性表通过严格审计，17 份状态通过原 1e-8 端电流／守恒门槛；原历史的重复控制与旧参考共同数组逐值一致。这说明该临界数值配置存在路径敏感性，不能证明材料物理迟滞或精确阈值，也没有授予原生临界对标资格。

临界对标的参考身份应包含完整外部偏置序列、初始解来源、是否再执行固定偏置联立求解、材料／网格散列、边界条件、RefDens、数值精度及停止条件。原生侧应记录相应预热和延续策略；不能只凭最终电压相同，把不同路径的剖面视为等价参考。严格收敛与独立物理验收仍分别执行，所有失败保留，直接电流与 I/q 也分别判定。

证据和四条可重放参考身份见 324 路径控制 (`validation/hfs_commercial_paths_20261030/ACCEPTANCE.md`; historical archive, not bundled)及其 `reference_protocol.json`。正常终点与额外一次固定偏置联立求解后的电势、密度、迁移率和端电流逐值相同；部分导出向量存在极小差异，完整数组相等标志仍为 false，不能扩大为所有输出逐值一致。

## 复合配置与停止条件也属于参考身份

原生与商业对标应逐项绑定 SRH、寿命、产生项及初始解来源。325 控制发现：商业未启用复合，而旧原生控制包含有限寿命 SRH。采用同对象内部全精度零偏置延续后，数值上可忽略 SRH 的直接 Newton 控制密度差约 5.0e-11，I/q 差 1.489e-8；后者仍超过原 1e-8 门槛。有限 SRH 组仍有明显差异。此证据要求补齐配置身份，不证明其解释所有临界差异；1e100 秒寿命也不是通用的显式关闭复合接口。

收敛标志应同时保留实际停止路径、请求更新容差、最后外迭代更新量及返回态方程残差。325 有限 SRH 的 Gummel 目标在 300 步经原有最终方程审计返回，最后载流子更新约 8.97e-18，并未小于请求的 1e-19；不能把方程审计通过写成更新量门槛通过。两组超时、两个近零状态的导出 SG 验收失败及未运行项均保持，不能由部分返回授予完整路径资格。详见 325 验收 (`validation/hfs_native_paths_20261030/ACCEPTANCE.md`; historical archive, not bundled)与 limits_audit.json。

## 路径、可观察量与本构剖面分别授予资格

326 补齐未启动 Newton 控制后，与 325 合并共有 60 次不同调用。数值上可忽略 SRH 的控制沿四条完整路径执行，30 份状态独立物理审计全部通过；from_below、from_above、replay_history 三条完整路径的所有非零密度与 I/q 检查通过原门槛。直接路径 I/q 差 1.48898e-8，仍超过 1e-8；直接安培资格也没有获得。

电流与密度合格不能替代实际本构剖面一致：from_below 和 from_above 最终两种载流子迁移率与商业匹配到约 1e-16 相对量级；replay_history 的电子迁移率仍有 46/256 面差超过 1e-12，最大约 1.25e-7；直接路径为 63/256 面。对应证据使用实际面快照及商业同区间的三角形对。不得仅凭总电流通过，宣称所有局部迁移率分支或完整器件模型已对齐。

合并 52 份非零 Newton 比较的直接安培资格仍为 0；finite_srh 四个近零状态的 SG 审计失败与两次 Gummel 超时保持。三路径资格限于本轮均匀经典控制、固定材料与网格及明确偏置历史；不外推为一般冷启动或默认产品资格。可重放身份和逐项边界见 326 验收 (`validation/hfs_native_newton_paths_20261030/ACCEPTANCE.md`; historical archive, not bundled)与 qualified_control_protocol.json。

## 延续平台可提前做严格方程审计，不能用更新量大小替代残差

327 隔离候选把受限稳态一维经典正 cutoff 的平台审计触发扩为载流子更新 128 倍、电势更新 2 倍请求容差，平台窗口和最小迭代数保持。审计后的 Poisson 与连续性门槛仍不超过请求容差的 100 倍（本控制 1e-17）；后续修正、验收及回滚源码保持。90 次延续调用（60 Gummel、30 Newton）完成，原 325 两次中断保持为旧失败；Newtons 检查的完整状态数组与旧控制逐值相同，已有三条路径资格保持。不能由此宣布最后更新量小于请求容差、所有 Gummel 商业路径通过或一般冷启动解决。

四条旧 Newton 路径的独立高精度固定系数 SG 串联重建表明：直接路径通量差在冻结场下由面迁移率差异解释到所报精度，其他输运上下文贡献约 1e-16。交叉替换迁移率只作代数归因，不是自洽解，不授予对齐；分支选择原因仍需独立控制。详见 327 验收 (`validation/hfs_warm_plateau_20261030/ACCEPTANCE.md`; historical archive, not bundled)与候选用法。

## 临界分支控制必须记录输入表示精度

328 隔离候选为直接 PyDeviceSimulator 增加全字符串均匀间距和 set_dirichlet_potential_decimal，避免这些输入先舍入为 binary64。其余材料、热电压、密度及初值保持原接口。预冻结 2×2 网格／电势精度控制共 120 次 Newton 调用，全部返回并通过原物理预算；旧 binary64 的 30 份主数组和 HFS 快照与 327 逐值相同。三组精度改变相对旧表示的 90 次比较全部 cutoff 分支不变，直接 I/q 差仍约 1.49e-8、电子迁移率 63 面不同；完整历史回放仍 46 面不同。提高这两项输入精度没有消除该差异；其他输入、实际准费米驱动力离散构造及预测／初值需分别核查。详见 328 验收 (`validation/hfs_decimal_ingress_20261030/ACCEPTANCE.md`; historical archive, not bundled)；高层十进制网格重放、非均匀坐标和一般完整对齐仍未获得资格。

## 用节点观测区间核查面驱动力，区分分支与迁移率结论

329 新增纯 Python `tcad.validation.hfs_gqf.audit_hfs_gqf_face`。在经典同质一维、无量子项、接触准费米驱动的范围，按二进制导出观测区间传播 phi 和 carrier+RefDens，独立核查面力、严格 cutoff 和 CT 迁移率。商业原单位必须先取舍入区间再换算；节点 eGradQuasiFermi 不能直接替代修正面驱动力。跨 cutoff 的区间始终不可判定，不能通过。

328 的 30 个原生状态和 324 的 17 个商业状态共 24,064 个面，全部分支可明确分类且与观测相符；80/120 位重放结论一致。原生力和迁移率全部相容。直接 63 面／历史回放 46 面的最终分支差异，其重建力区间均在 cutoff 两侧；在该观测模型内不能仅用节点导出分辨率解释，后续仍需核查预测／初值和非线性路径。商业 506 个电子迁移率未通过严格单次舍入区间检查，间隔最多约 0.32844 raw binary64 ULP，全部保留，不能放宽区间后称为完整本构一致。详见 329 验收 (`validation/hfs_gqf_interval_20261030/ACCEPTANCE.md`; historical archive, not bundled)。该审计不证明商业内部公式或 libquadmath 误差界，不新增完整对齐资格。

## 外推设置的因果核查必须有成对干预与日志证据

330 新增 audit_extrapolation_deck_pair，验证基准全局 Math Extrapolate(Order=2) 与仅删除该指令的对照，其余代码 token、原始材料／网格与完整偏置历史分别绑定。API 的 valid 不代表日志已确认或物理通过。12 项单元测试与四组成对实际 deck 通过。

8 个商业作业与 34 次 TDX 无重试完成，68 表严格收敛、34 状态 SG/KCL 全过；全局二阶外推与关闭设置的配置由日志分别明确回显。原配置 17 状态所有字段与 324 逐值同；关闭后 17 对所有共享字段及四路径打印迭代轨迹（去计时／行号）均同。本轮由单步 Quasistationary 块组成，不能外推到多步块／瞬态，也不能推断未打印的内部预测公式。当前不能仅凭 header 的外推设置解释原生差异；应核查初始化、边界处理、Newton 数值路径及常数兼容。直接 I/q 差仍 1.48898e-8、电子 63 面不同，历史回放仍 46 面；完整对齐未获资格。详见 330 验收 (`validation/hfs_extrapolation_pair_20261030/ACCEPTANCE.md`; historical archive, not bundled)。

## NewtonPlot 初始场与行后 C-norm 不能按邻接位置视为同一状态

331 对直接路径已有 8 份 NewtonPlot 作官方转换。目标问题 i0 场仍为平坦内区、仅接触覆盖新电压，与原生延续初态结构相同；两者仍有电势零点和载流子尾数差，未证明全精度一致。五步三变量的 7,710 节点加法关系全部满足 snapshot_i = snapshot_(i-1) + NewtonStepUpdate_i 的观测区间检查，其中 1,590 个低于导出分辨率。不能用 i0 更新字段预测下一步。15 个行后 C-norm 打印值中，8 个只与下一索引快照相符、7 个与两者都相符；原始行号与 following_c_norm 语义必须保留。

新增纯 Python audit_newton_update_transition 与 10 测试；相容加法不自动证明时序、阻尼或收敛。本轮直接路径的实际电子／空穴分支在 i2 已与最终逐面相同，后续保持；完整迁移率与方程仍须继续迭代。原生内部前两步尚未采集，不能定位两者首次分歧。尤其失败截断可能触发边界补救与回滚，返回数组不能替代内部轨迹。详见 331 验收 (`validation/hfs_initial_trace_20261030/ACCEPTANCE.md`; historical archive, not bundled)。本轮未改变数值求解器或完整对齐资格。

## 原生实际轨迹首次在第二次更新后出现 63 个电子面分歧

332 在同一 Linux/PETSc/quad 核心的隔离副本中采集真实 x/F/J、方向、搜索与更新，以及主残差内实际 HFS 面值；没有截断回滚或额外方程求值。关闭／开启诊断各三次求解，全部返回字段和历史与原 328 逐值相同。3,855 坐标更新及下一状态连接、4,096 面记录核查通过。初态和第一次更新后原生／商业分支逐面同，第二次更新后出现电子 63 面差异并保持至最终（活动面原生168／商业107）；空穴均相同。第一步连续场更新已有差，分支相同不能证明全部数值相同。

实际 alpha 均1，限幅没有改方向。首步实际 PETSc 电势方向与独立高精度固定线性解最大差约4.50e-18 V，小于该步原生／商业更新差约2.10e-14 V；不能仅通过提高这一线性系统的求解精度宣称首步对齐，也不能排除后续敏感分支影响。首步100/160位离线解回放通过；第二步仅160位，未作两种精度回放。原离线失败及更正、取证限制均保留。下一步比较首步方程／Jacobian与常数定义。参见332验收 (`validation/hfs_internal_trace_20261030/ACCEPTANCE.md`; historical archive, not bundled)，本轮没有修复63面差异或授予完整对齐。

## 密度加法更新的隔离候选消除固定直接路径63面差异

333 首先核查相同首步方向的 n*expm1(du) 与 n*du：后者相对商业更新误差分别缩小约2389倍（电子）和209444倍（空穴），100/160位结果一致。隔离候选在保持log-Jacobian/PETSc、常数、物理、搜索与门槛时，将更新改为u+log1p(alpha*du)，非正乘子在方程组装前拒绝。关闭模式3状态/历史逐值复现328，两模式初始x/F/J和方向相同。

6次调用均收敛，10项helper边界检查、两模式7710坐标更新及连接、6状态独立SG/KCL通过。候选6个同更新次数剖面的分支均与商业同，最终电子/空穴完整迁移率最大相对差约1.79e-16/9.38e-17，密度5.19e-16，I/q2.01e-16；基线63面与I/q1.49e-8仍保留。直接安培仍9.59e-6，不授予资格。参见333验收 (`validation/hfs_update_coordinates_20261030/ACCEPTANCE.md`; historical archive, not bundled)与候选用法。

这只解决隔离候选的固定直接路径，支持更新坐标的受控因果解释，不证明商业内部变量。候选开关TCAD_ADDITIVE_DENSITY_333未进入正式API或产品默认；四路径、一般冷启动与正式选项回归未完成。生产、282、328、332保持，历史46面等缺项不关闭。


## 334：密度加法候选通过四条冻结路径

复用333数值二进制，关闭／开启各30次，共60次调用均收敛，无编译、商业／TDX或数值重试。关闭30个状态及历史逐值复现328，direct两模式各3个状态也复现333。四条固定历史、全部17个完成商业输出均纳入：候选密度／I/q通过17/17（旧15/17），完整双载流子迁移率及逐面分支17/17（旧13/17），最终direct63面与replay_history46面电子差异均为0。最大密度相对差5.33e-16，I/q9.36e-15，门槛未变。

60状态独立SG/KCL、85,504面记录、82,497个113位post坐标及同数下一raw连接全部通过。Newton原生steady_equation_audit全部返回unsupported_solver_formulation，明确保留不可用，不能替代完整方程审计。直接安培仍约9.59e-6，0/17通过；329亚ULP失败保留。生产、旧282与328/332/333源／扩展、原商业快照身份保持。

见334验收 (`validation/hfs_additive_paths_20261030/ACCEPTANCE.md`; historical archive, not bundled)及候选用法。隔离环境开关仍未成为正式API或产品默认，也未部署。后续为显式选项与更广HFS／掺杂PN冷启动／正性搜索及物理回归；绝对安培常数兼容、原318表58、Newton独立方程审计与完整对齐仍开放。四项研究继续排除。


## 335：显式每实例密度更新选项及PN反例

隔离候选新增set/get_newton_log_density_update，exponential保留原默认，additive显式选择，旧333环境开关在新候选无效。C++/double包装/Cython/高层及配置clone完整接线；22项接口、2项零预算检查通过。四路径60返回状态与轨迹逐值/逐字节334，继承17/17密度/Iq/完整迁移率/逐面分支；绝对安培仍未过。

504既有默认测试全过，另36项三轴非均匀additive HFS独立oracle全过。新PN冷启动exponential9/9、additive5/9，4个加法策略失败（反偏无源/有限SRH，零偏和反偏光生）均由配对8次诊断复现，末尾连续10次alpha=0停滞。共582不同测试578通过/4失败；不得授予一般器件资格。首次包装漏接构建失败及72项测试漏设ledger入口失败均保留，已分别补齐，不涉及放宽门槛；总pytest内部调用数未完整计数。

见335验收 (`validation/hfs_density_option_20261030/ACCEPTANCE.md`; historical archive, not bundled)及CANDIDATE_USAGE.md。候选/tmp/tcad335_density_recovery_20261030/source；主数值源码、默认与生产保持。下一步根据已采集的PN轨迹核查方向限幅/步长搜索，不必重生成旧商业参考。直接安培、Newton方程审计、原318表58及更广矩阵仍开放，四研究排除。


## 336：统一原始方向备选修复四个PN冷启动反例

旧335候选扩大步长窗口的8次对照仍全部失败。新隔离候选仅在经典MB稳态一维additive旧限幅搜索不下降时，按统一比例缩放原始Newton方向，保正性及1 V电势界，再按原RMS下降门槛搜索；原方程、残差容差与默认策略不变。四反例收敛迭代为13/13/7/8，582测试全部通过；两策略四路径60状态与轨迹精确335，四默认PN诊断精确335。8个独立SG/KCL诊断通过，132缩放方向坐标和2277post-next连接通过。

独立113位更新重建仍有8个1 ULP差异，600位参考及单独原生helper定位到log1pq舍入，严格门槛明确未过。不能将582测试通过扩大为所有数值门槛通过。候选/tmp/tcad336_descent_build_20261030/source；主数值源码、默认及生产未改。直接安培、Newton完整方程审计、原318表58、329亚ULP与一般复杂器件继续开放，四研究继续排除。

见336验收 (`validation/pn_step_window_20261030/ACCEPTANCE.md`; historical archive, not bundled)与同目录CANDIDATE_USAGE.md。下一步新建受控阶段核查原表58的avalanche掺杂路径，不重生成旧商业参考，不覆盖既有证据。


## 337：失败表58与活动雪崩资格须区分

五份318失败迭代状态分别由335 additive/336 exponential/336 additive求解，15次全部4迭代收敛，独立80/120位Poisson/连续性/SG/KCL按原预算通过；新旧additive五状态/缓存/轨迹精确相同，336备选未进入。然而最大GQF驱动力仅4.6783e4 V/m，原生固定1e5 V/m雪崩下限使所有Gii=0；商业捕获源项含正值，不能宣称活动雪崩或原表58对齐。非零HFS截断+雪崩目前还被接口明确拒绝，本轮声明连续HFS，未绕过保护。

下一修复应显式配置雪崩场下限，保留旧默认并在Newton/Gummel/缓存/瞬态一致接线，以低场非零源项独立oracle验收；不把下限当材料标定或以拟合求通过。见337诊断验收 (`validation/avalanche_seed_replay_20261030/ACCEPTANCE.md`; historical archive, not bundled)。生产/默认及数值源码未改，四研究继续排除。


## 338：显式雪崩场下限与低场非零源项

隔离候选新增原生set/get_ii_field_floor、高层set/get_impact_field_floor，有限正值且每实例、配置clone重放；默认1e5 V/m保留。6源修改，C++/double/Cython/高层完整接线，Gummel/稳态Newton/经典瞬态及缓存源项使用同一值，完整重建不混旧对象。1040不同测试单次全过：旧582、旧活动雪崩320、新96稳态+24隐式序列+18接口。

五份318真实商业失败状态的15次诊断全收敛：默认两组10状态/113缓存/轨迹精确337；显式1 V/m组五状态3～4迭代，Gii最大3.768e22 m^-3 s^-1非零，独立80/120位Poisson/连续性/SG/源项/接触半单元/KCL按旧预算通过。源项激活不代表商业参考通过；1 V/m不是材料参数拟合。四路径60状态/轨迹精确336，继承17/17密度/Iq/迁移率/分支，直接安培仍未过。

初诊断驱动漏传dx_m等参数，三组在solve前KeyError、0求解，原记录保留；completion仅补配置完成原15调用，同二进制、无重建/重跑测试/数值重试。候选/tmp/tcad338_floor_build_20261030/source；主数值源码/默认/生产保持。见338验收 (`validation/avalanche_floor_option_20261030/ACCEPTANCE.md`; historical archive, not bundled)及使用说明。下一步独立验证非零HFS截断+活动雪崩的迁移率/源项/Jacobian/接触守恒后再放开保护；原表58、8个1ULP、绝对安培、329及一般复杂器件仍开放，四研究排除。


## 339：空矩阵修复与非零HFS截断／雪崩底层Jacobian

新隔离候选仅修复SparseMatrix::finalize合法空矩阵的越界访问。零源项导数夹具原SIGSEGV完整保留；修复后6个边界控制及原1040测试单次全通过。1产品对象编译／1扩展链接、13对象SHA复用；候选/tmp/tcad339_empty_matrix_repair_v3_20261030/source，主数值源码／默认／生产保持。

576规定状态覆盖三轴、四力组合、接触力切换、两坐标、三个正HFS截断、两个雪崩下限与稳态／BE。80/120位独立残差、完整Jacobian、非零源项及其导数全部过预声明1e-24归一化门槛；432状态活动源项。完整J最大误差5.68e-32，源项导数3.05e-31；截断两侧覆盖，未触碰恰好跳变面。漏HFS截断、裸迁移率、错误接触力、漏迁移率导数负控制均在可区分子集检出。

公开组合保护仍保留：还缺器件层接触半单元电流／缓存／完整求解路径验收，不能将底层组装诊断当作商业对标通过。全部构建/夹具/manifest失败保留，339验收 (`validation/cutoff_impact_jacobian_20261030/ACCEPTANCE.md`; historical archive, not bundled)含精确边界与调用统计。商业表58、直接安培、8个ULP、329和一般复杂器件继续开放，四研究排除。


## 340：稳态正 HFS 截断/雪崩及准费米分支停滞修复

隔离候选放开经典同质均匀一维等温MB常数迁移率的稳态正HFS截断与雪崩组合。现有受限分支跨越遗漏GQF密度依赖，导致3个零源反例连续10次零步长；按两个载流子的实际接触策略/RefDens/DOS识别分支后均8迭代收敛，最终严格门槛不变。其余726个完整状态/缓存/历史精确首轮。

1775回归全部通过；729五节点自洽状态在80/120位独立Poisson/SG/生成率/接触半单元修正/连续性/KCL验收通过，720组活动源、9组零源，486个已有x/z总电流API用例通过。首轮1747过/28失败完整保留：24合法替代根、3真实停滞、1拒绝消息匹配。独立oracle显式改为解析初值的分支条件求根，并验证原未冻结方程和原容差；最终27替代根，不声明解唯一或与Sentaurus选中同一分支。

候选`/tmp/tcad340_gqf_branch_repair_20261030/source`，binding `816613ad43a9b4abe056844e9686c9a0589d516c43ddbbb6d332f41d5937423f`；完整来源和二进制本地回收。共2单对象构建/2链接/2pytest，新增实际solve下界1464，总内部调用未知，无商业/TDX/自动重试/部署。主数值源码和默认保持；正截断瞬态仍拒绝。下一步新阶段验证隐式序列与原商业表58有效路径/分支。直接安培、8ULP、329、公共完整审计与一般复杂器件仍开放，四研究排除。340验收 (`validation/cutoff_impact_device_20261030/ACCEPTANCE.md`; historical archive, not bundled)。


## 341：正截断与雪崩固定 BE 瞬态及源项输出

隔离候选支持经典同质均匀一维等温 MB 常数迁移率的正 HFS 截断+雪崩固定 BE 瞬态，要求雪崩开启、三块均不冻结且无自适应误差控制。逐时刻 `G_ii` 复用 Newton 实际源项核重建并公开导出，预检查前清空旧尝试历史。891 序列/3564 时刻/2673 区间通过 80/120 位独立 Poisson、通量、源项、BE 存储、位移电流与接触/KCL 核验，覆盖 126 次时间分支变化；729 既有稳态与额外默认兼容记录保持。

首次 pytest 2670 通过/9 失败；有理数证明定位为测试的 binary128 文本直接转 double 中点误解码。仅修正测试解码，以相同产品二进制定向复验 9 项均通过，原失败保留。跨两会话 2679 不同 nodeid 通过，累计 2688 项，不声称单次完整全绿。一次完整构建，零商业/TDX/部署；候选 `/tmp/tcad341_clock_completion_20261030/source`，binding `03397c238149a7df1139bb4eeb88b4c08bd11df0960c5575bf5d4fada18236ad`。主数值源码及生产未集成。下一步是商业表 58 有效路径及分支对照；既有严格 ULP、安培常数和复杂组合缺项仍开放，四项研究范围继续排除。341 验收 (`validation/cutoff_impact_transient_20261030/ACCEPTANCE.md`; historical archive, not bundled)。


## 342：原材料活动雪崩两条新商业延续路径

保持318的网格/材料/物理与严格门槛，预声明直接及1mV递进两条新路径，实际商业2、TDX6、原生/构建/部署0。转换6剖面，80/120位独立SG/Canali/源项/连续性/端电流/KCL分类一致，物理通过6；严格路径[]，完整合格新路径[]。原表58失败保留，退出0不覆盖拒绝表，不授予新原生商业对齐。4活动剖面记录与生成率点值/接触半沉积定义相符，差4.22e-14；用正确半宽积分无需拟合缩放。平衡源相消和局部CurrentDensity单位仍开放；一次后处理派生字段横向相同断言失败保留，新completion不改物理门槛。主数值来源与生产保持；四研究排除不变。342记录 (`validation/active_avalanche_paths_20261030/ACCEPTANCE.md`; historical archive, not bundled)。


## 343：完整小偏压活动雪崩商业与原生控制

新目标平衡→-1mV×30→同偏压再次联立，原318材料/模型/严格门槛保持。商业1、TDX3，34表全通过，3剖面80/120位独立物理全过；两活动源记录是同一偏压及重复。原生默认指数路径61调用全收敛，61状态独立物理通过，3对应剖面通过既有掺杂器件预算；-30mV密度/生成率/安培差3.87235e-6/8.29593e-6/8.76753e-6。严格密度/Iq/安培/迁移率门槛仍失败。显式加法初始平衡60迭代失败，后续停止。另2次预声明instrumentation复算，输出与原件精确相同；初始x/F/J/方向相同，首个差异来自有限更新与选步，正密度/正步长下仍失败，未宣称修复。总原生64=原比较62+诊断2，产品构建/自动数值重试/部署0。原表58及-.4V未关闭，生产/341候选身份保持；四研究继续排除。详见343验收 (`validation/active_prefix_benchmark_20261030/ACCEPTANCE.md`; historical archive, not bundled)。下一步在新目录修复加法冷启动全局化并保留回归。


## 344：固定加法线搜索权重候选拒绝

新隔离候选固定初始行权重，仅用于经典一维加法RMS全局化，不改变物理/最终门槛。1对象编译、1链接、13对象复用，2初始求解中指数5迭代通过且与343输出精确相同，加法56样本后缩步停滞仍失败；按预声明条件停止，完整路径/pytest/商业/TDX/自动数值重试/部署0。80/120位独立审计通过1状态。未授予修复资格，未改主数值/默认/生产；四研究排除不变。下一步验证显式记录的加法准费米信赖方向修正。344记录 (`validation/additive_fixed_merit_20261030/ACCEPTANCE.md`; historical archive, not bundled)。


## 345：限定雪崩/HFS组合的加法准费米信赖步修复

新信赖方向d=expm1(g)+exp(g)*t使有限电势响应保持有界准费米耦合，实际更新仍n*(1+alpha*d)，小步一阶Newton一致。最终仅经典一维稳态等温MB/对数/未冻结/无量子、显式加法、HFS启用正截断且雪崩启用；默认和其他组合保持341。343原加法60迭代失败→5迭代收敛，两策略完整61调用路径共122状态80/120独立物理全过，两个初始另审计，既有剖面预算双策略通过，严格常数/本构仍失败。首次过宽候选2677过2PN反偏回归失败保留；独立scope_completion预算后最终单次2679全过，244路径状态/缓存文件精确首次，默认122文件精确343。345累计两编译/链接、248显式调用不含pytest内部，两pytest累计5356过2失败；商业/TDX/自动数值重试/部署0，未新跑C++瞬态序列。最终隔离来源/tmp/tcad345_additive_qf_scope_20261030/source，主数值/生产保持。旧表58/-.4V/严格兼容/ULP/329/公开完整审计/复杂组合仍开，四研究排除不变。345验收 (`validation/additive_qf_trust_20261030/ACCEPTANCE.md`; historical archive, not bundled)。


## 346：完整−400 mV新路径对标

原318物理输入及严格容差保持，商业平衡→1mV×400→同偏压复算407表全严格通过，6剖面80/120独立物理全过。345候选原生1mV至−30mV、后5mV至−400mV，双策略各209调用共418全收敛且独立物理通过，12对应剖面过原预算，244前缀状态/缓存文件精确345。原全1mV原生计划因资源耗时估计低明确停止，130调用中129返回且物理通过、1中断，不授予完整路径资格；新计划418独立预算，累计548发出/547返回。无新编译/pytest/部署，复用未改345来源和2679回归。原342失败路径/表58、严格常数本构、ULP/329、局部CurrentDensity/公开完整审计/复杂组合仍开放，四研究排除不变。346验收 (`validation/millivolt_full_bias_20261030/ACCEPTANCE.md`; historical archive, not bundled)。


## 347：参考电荷约定的严格剖面对齐

仅QE切换1.602176634e-19→文档参考1.602192e-19，默认SI保持，无材料拟合。配对相同商业初值的SI/参考各12状态均独立物理过；SI10活动剖面四严格门槛全失败，参考全过，错误电荷负控制4拒绝。随后解析冷启动双策略各209完整路径418状态80/120物理全过，12比较密度过2e-8，10非平衡的密度/Iq/安培/迁移率严格全过，HFS分支差0。累计442调用全收敛/物理通过。初次绑定CPP缺失导致14对象中13过1失败；新目录Cython生成、13对象SHA复用、追加1编译1链接2标量探针；SI首次清单自包含前置拒绝0调用，新包12完成。合计15对象尝试14成功1失败，商业/TDX/pytest/部署0。仅914来源隔离参考构建，量子/WKB硬编码及一般组合未验收；原表58/ULP/329/局部CurrentDensity/公开完整审计仍开放，四研究排除不变，完整对齐false。347验收 (`validation/reference_charge_20261031/ACCEPTANCE.md`; historical archive, not bundled)。


## 348：显式常数模式配置与二进制身份

主源码加入SI/legacy-charge配置、精度×常数双缓存隔离、CMake PUBLIC定义、native_constants及require_constants_profile；默认SI不变。分支SI2691、参考12、主源码SI12在独立completion全部通过，切回SI0编译/0链接且SHA精确恢复。首轮缺oracle目录导致1851测试FileNotFoundError完整保留，修正仅验证驱动目录准备；累计3555通过/1851失败，不宣称累计全绿。42对象/3链接、36显式求解全收敛/80/120物理过，72结果/缓存精确347。主源码未合并全部分支修复，主源码参考二进制及完整CMake编译尚未验收；无商业/TDX/部署，完整对齐false，四研究排除保持。348验收 (`validation/constants_profile_20261031/ACCEPTANCE.md`; historical archive, not bundled)。


## 349：主源码参考扩展及双模式 CMake 实编译

主源码 legacy-charge 扩展14对象/1链接、12项pytest通过；SI与legacy-charge完整CMake各27对象/16程序及16项CTest均通过；两个故意混用消费者/核心常数的测试程序均按预期报告身份不一致。新增C++身份测试，默认SI/数值算法/容差不变。共70对象/37链接，未部署生产。主源码尚未集成全部已验证求解器分支修复，未运行主源码分支专属2679回归，完整Sentaurus对齐仍false。详见349验收 (`validation/native_build_profiles_20261031/ACCEPTANCE.md`; historical archive, not bundled)和差异清单。


## 350：主线线性求解器修复集成

修正Python PETSC=7误选原生IR_BICGSTAB的映射，加入成对后端预校验和异常传播；集成GMRES预算/breakdown/尺度、空矩阵finalize及PETSc缓存结构/独立所有权修复。旧82反例19过/63失败，旧空矩阵SIGSEGV保留；新SI95、现有8文件325、legacy28共448pytest全过，两套CMake各18项共36CTest通过，实际PETSc对象10次已知方程/缓存/复制检查通过。109翻译单元/46链接，默认SI/数值门槛不变，无部署。全部主线回归/其余分支集成及完整Sentaurus对齐仍未完成。旧硬编码7意图PETSc的脚本应改用SolverType.PETSC（8）。350验收 (`validation/linear_contracts_main_20261031/ACCEPTANCE.md`; historical archive, not bundled)。


## 351：主线带状主元与图重排序

集成验证分支的binary128带内主元、行列平衡、对称图重排序与事务化try_banded_direct；其余线性求解代码、物理和默认常数保持。旧6场景2通过/4路径断言失败，六项数值解均合格；新候选460pytest、两配置各25共50CTest全部通过。两配置8192阶系统在128 MiB内存上限下成功求解或保持原解安全拒绝；非一般图内存定理。实际PETSc扩展对象状态探针通过。116编译/50链接归档，无生产部署、新商业或容差放宽。Newton有界API调用、Gummel其他修复的集成、全部主线回归及完整Sentaurus对齐仍未完成。351验收 (`validation/banded_direct_main_20261031/ACCEPTANCE.md`; historical archive, not bundled)。


## 352：Newton接入有界带状求解

只对GMRES、大于2000物理节点、稳态经典一维，在主方向和缺陷修正调用先尝试try_banded_direct，失败保留原GMRES；其余Newton源码、物理、默认常数和收敛/KCL门槛不变。最终381pytest、两配置各34共68CTest通过；首次33过/1初值未触发方向的夹具失败保留，仅修订载流子短波初值，生产源码两阶段相同。128MiB原生9场景验证三轴和载流子路径及5项排除条件；PETSc扩展回归分开验收。累计127编译/71链接归档，无新商业/部署，完整Sentaurus对齐仍未完成。352验收 (`validation/newton_banded_main_20261031/ACCEPTANCE.md`; historical archive, not bundled)。


## 353：按实例选择 Newton 对数密度更新

主线支持 exponential（默认）/additive，原生、double 转发、Cython、Simulator 与配置回放一致。加法 log1p 更新拒绝非正密度因子，配套有界下降搜索；经典稳态 MB 未冻结对数系统采用准费米信赖步、一维 RMS 下降，并收紧载流子相对残差验收，物理组装和调用者容差保持。最终 465 pytest、两套共70 CTest 通过。首次漏接 double 接口的扩展编译失败保留，独立补齐只改转发/测试，不改 Newton 数值源码。HFS/II cutoff 特定 345 转换、瞬态加法运行资格、其他集成和完整商业对齐仍开放；无新商业/部署。353验收 (`validation/newton_density_main_20261031/ACCEPTANCE.md`; historical archive, not bundled)。


## 354：Gummel 自动带状重试的内存边界

自动重试使用 try_banded_direct，拒绝不分配 n×n；缓存失效清除并恢复原后端，稠密兜底限于不超过1024行，显式DENSE_DIRECT保持。旧4097行反例触及稠密分配，新代码在128MiB限制下正常拒绝，8个分支控制通过；物理组装、请求容差保持。565 pytest、两配置86 CTest通过，扩展PETSc与无PETSc原生证据分开。弱反应链和其他分支集成、完整回归/商业对齐仍开放。354验收 (`validation/gummel_banded_main_20261031/ACCEPTANCE.md`; historical archive, not bundled)。


## 355：单接触连续性链保留隐式SRH汇

电子/空穴单接触稳态一维链显式携带已有 dR×cell-width，修复弱汇被矩阵相对残差掩盖、错误解仍报告收敛的问题。组装、调度和数值容差保持；旧12场景失败，新589 pytest、86 CTest通过，另136原生精度/配置子控制通过。首次扩展600秒超时原件保留，依赖和对象哈希核验后独立增量续建，无干净构建声明；没有数值源码重试。long double 仅授予原生链资格。亚皮伏电流、HFS/II等集成仍开放。355验收 (`validation/reaction_chain_main_20261031/ACCEPTANCE.md`; historical archive, not bundled)。


## 356: transactional existing HFS/II parameter configuration

Invalid HFS driving and II coefficients now reject before state changes; Cython translates II exceptions. Public II mesh validation commits enable only after successful coefficient validation. SI/legacy: 368 selected pytest, 2 targeted CTest (176 native controls) passed. Physics assembly and Jacobians are byte-preserved outside the setters. Raw solver-option/Auger guards and coupled HFS/II branch integration remain open; no full main regression, new commercial result, or complete Sentaurus alignment is claimed. See 356 acceptance (`validation/transport_parameter_guard_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 357: raw model options and Auger parameter contracts

Enabled Gummel/Newton HFS, II coefficient/floor and Auger options now validate before solving. Auger setters reject invalid values before assignment, with Cython exception translation. SI/legacy: 390 selected pytest and 688 native controls passed; 4 selected CTest repeated the manually linked native executables. Two setup failures (fixture compilation and standalone library paths) are retained. No CMake target build, full regression, new commercial comparison, production deployment, or complete Sentaurus alignment is claimed. Six coupled HFS/II interfaces remain open. See 357 acceptance (`validation/raw_option_guard_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 358: explicit avalanche field cutoff

Device, double facade, Cython and public Simulator now expose a finite positive II field cutoff with the historical 1e5 V/m default. The value reaches existing Gummel and steady Newton source/Jacobian operators. SI/legacy: 526 selected pytest, 786 native controls including 48 new FD combinations, and 6 selected CTest passed. Original numerical operators and binary hashes were preserved when correcting test references. Setup failures and nine initial reference failures are retained. The frozen parent Newton resistor stalls with or without II; its root cause remains open. Five coupled HFS/II interfaces, full main regression and complete Sentaurus alignment remain open; no production deployment or new commercial comparison. See 358 acceptance (`validation/ii_field_floor_main_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 359: bounded descent fallback for exponential density updates

The classical steady 1D Newton resistor stall without II is fixed by a uniformly bounded original-direction fallback after the clipped direction search fails. Exponential updates retain their mapping; II/BTBT exponential paths and additive arithmetic remain unchanged. New Newton checks: 34 per profile all passed. Selected regression: SI 348 passed; legacy 339 passed and 9 native Fermi spectral energy audit failures, individually reproduced on the frozen parent legacy binding. Four native programs passed, including 48 inherited II Jacobian FD combinations. Thirteen initial test-request failures and old regression failures are retained; final validation reuses identical bindings. The preexisting legacy Fermi energy gap, II-enabled resistor, five HFS/II interfaces and complete Sentaurus alignment remain open. No new commercial run or production deployment. See 359 acceptance (`validation/newton_stall_main_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 360: SI charge contract for cut-cell spectral kernels

The preexisting nine legacy-charge native Fermi energy failures are fixed. Fourteen SI cut-cell/spectral headers now use their own SI elementary charge instead of inheriting the separate classical legacy QE profile. Flux, electrostatic work, Poisson and charge/energy rows share the same SI convention as the unchanged Python models and independent auditors. Classical global QE and all CPP numerical sources remain byte-identical. Selected dual-profile regression: 1704 passed, zero failed/skipped/xfail, including exact frozen-parent classical results and exact SI face/coupled states in both profiles. Four native programs passed, including 48 inherited II Jacobian FD combinations. The legacy session was manually checkpointed after 704 passing cases (exit 2); the remaining 143 passed in disjoint isolated batches with identical bindings. The optional scaled binary was built after a retained collection error. This is an incremental dependency-checked build, not complete main/long-double/commercial qualification. II-enabled Newton stall, five HFS/II interfaces and complete Sentaurus alignment remain open. No production deployment. See 360 acceptance (`validation/si_transport_charge_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 361: HFS explicit cutoff and linear-density mobility derivatives

Device, facade, Cython and public Simulator now expose a finite nonnegative HFS low-field cutoff, default zero. Assembly, returned current, steady audits and Newton KCL use the same strict-below branch; equality remains active. Four GradQuasiFermi mobility Jacobian carrier entries now apply the linear-density chain factor. The frozen parent failed 18 FD entries. Final selected dual-profile coverage: 940 passing pytest nodes and 10 native programs, including 240 FD scenarios across HFS and II. The first two boundary fixtures failed because zero-budget Gummel without carrier BCs initialized returned density to 1e6, so matching DOS to the requested guess did not eliminate the offset. Final fixed carrier boundaries and returned-state assertions resolve the fixture without changing numerical code, binding hashes or tolerance. Earlier failures, compile/packaging/collection errors are retained; cumulative sessions are not all green. This is an incremental, bounded numerical/API qualification. Four other HFS/II device APIs, II-enabled Newton stall, HFS/II source-current consistency and complete Sentaurus alignment remain open. No new commercial comparison or production deployment. See 361 acceptance (`validation/hfs_cutoff_main_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 362: classical HFS/II source-current consistency

Classical Gummel/Newton avalanche generation now uses the same saturated SG mobility as continuity and returned current; Newton includes its potential and density derivatives. The frozen parent failed the independent generation reference by up to 44.51%. Final dual-profile selected regression: 1128 pytest passed, including 192 new controls, plus 10 native programs and 720 FD scenarios (576 new). Two intentionally obsolete HFS/II charge snapshots per profile were replaced by independent physics controls; existing test functions and tolerances are unchanged. Initial native FD fixtures crossed a cutoff discontinuity and failed; moving only that new fixture threshold away from the jump retained identical numerical sources, binding and object hashes. All failure evidence is retained. Quantum coupling, general converged HFS/II devices, II-enabled Newton stall, four remaining device APIs and complete Sentaurus alignment remain open. No new commercial comparison or production deployment. See 362 acceptance (`validation/hfs_ii_current_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 363: carrier-specific HFS contact driving policy

The HFS quasi-Fermi-at-contacts setter/getter now reaches Device, double facade, Cython, public Simulator and recipe replay. Default True preserves the existing driving. False selects transport-potential field driving only on the corresponding carrier Dirichlet contact edges; interior edges retain their configured driving. Continuity, returned currents/audits, classical II source, Newton residual/Jacobian and steady KCL share that selection. Final dual-profile selected regression: 1434 pytest passed (306 new), plus 12 native programs and 2256 FD scenarios (1536 new). Both implicit default and explicit True exactly preserve 48 frozen profile cases. Initial asymmetric Gummel fixture failures from cancellation in double-exported near-equilibrium states are retained; switching only that new fixture to a single Newton return kept numerical sources, binding/object hashes and tolerances unchanged. Cumulative sessions are not all green. Nondefault general converged/quantum/transient devices, II-enabled Newton stall, three remaining APIs and complete Sentaurus alignment remain open. No new commercial comparison or production deployment. See 363 acceptance (`validation/hfs_contact_main_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 364: bounded HFS reference density integration

HFS reference-density setter/getter now reaches native solvers, double facade, Cython, public Simulator and configuration replay. Shifted GQF carrier densities affect only saturated mobility; SG flux factors keep actual carrier densities. Continuity, returned currents/audits, classical II source, Newton residual/Jacobian and steady KCL agree. Nonzero active references are bounded to homogeneous 1D classical isothermal MB with constant mobility; unsupported configurations reject before solve. Both zero defaults preserve frozen parent states exactly. Dual-profile selected regression: 2136 pytest, 14 native programs, 6864 FD scenarios; existing tests and tolerances unchanged. General converged nonzero-reference devices, nonzero transient runtime, II-enabled Newton stall, quantum HFS/II consistency, two remaining II APIs and complete Sentaurus alignment remain open. No production deployment or new commercial comparison. See 364 acceptance (`validation/hfs_reference_main_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 365: II quasi-Fermi driving and independent reference densities

II driving (0 ElectricField default, 1 GradQuasiFermi) and electron/hole reference-density setters/getters now reach native solvers, facade, Cython, Simulator and recipe replay. GQF alpha forces use shifted densities, independently of HFS controls; SG currents keep actual densities. Source residual/Jacobian include full alpha potential/density derivatives and existing saturated current derivatives. Active GQF II is bounded to homogeneous 1D classical isothermal MB with constant mobility. Default field/zero-reference states exactly preserve the frozen parent. Dual-profile selected regression: 2972 pytest, 16 native programs and 19152 FD scenarios, with inherited tests and tolerances unchanged. Zero electric field can still produce GQF ionization, verified independently. Transient avalanche remains explicitly unsupported and its rejection is tested for both modes. Previously listed HFS/II APIs are complete; II-enabled Newton stall, quantum source/current consistency, general converged GQF devices and complete Sentaurus alignment remain open. No commercial comparison or production deployment. See 365 acceptance (`validation/ii_driving_main_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 366: Pair-weighted II globalization for cold classical bars

The original II-enabled, no-HFS cold Newton resistor now converges. A common electron/hole scale is used only in the classical 1D avalanche RMS merit; full residual/Jacobian, per-species convergence and KCL gates remain. HFS/BTBT/quantum/FE/LK paths retain their old merit. Dual-profile final selected coverage combines 3116 unique passes from the full runs and affected-file completion; the first full runs contained two failures of old non-converged-state snapshots, explicitly retired in favor of independent physical acceptance. All first failures and exploratory failures remain archived. Native coverage reran 16 programs and 19152 inherited FD scenarios. General HFS/II/high-generation convergence, reversed additive updates, enabled zero-II descent eligibility, quantum source/current consistency and complete Sentaurus alignment remain open. No production deployment or new commercial comparison. See 366 acceptance (`validation/ii_newton_stall_main_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 367: Exact-zero avalanche amplitudes retain source-free descent

The exponential fallback guard now distinguishes an enabled nonzero-II source from exactly zero electron and hole amplitudes, for any legal B. Equations/Jacobian, validation, GQF scope, nonzero-II/BTBT guards, additive policy and convergence gates are unchanged. All 192 parent zero-II baseline cases failed while disabled II converged. Final selected coverage combines 3340 unique passes from the full runs and affected-file completion, with independent equations and exact returned-state/audit equivalence. History metadata is exact; arrays are compared numerically after normalization because raw cancellation residuals differ. Two earlier sets of 192 test-comparison failures remain archived. Sixteen native programs reran 19152 inherited FD scenarios. General HFS/strong-II, reversed additive updates, quantum source consistency and complete Sentaurus alignment remain open. No deployment or new commercial comparison. See 367 acceptance (`validation/zero_ii_descent_main_20261031/ACCEPTANCE.md`; historical archive, not bundled).


## 368: Additive avalanche density trust in both bias directions

For the existing classical 1D, nonzero-II, no-HFS paired-merit scope, additive relative density increments now use direct [-0.9,5] bounds instead of log/QF clipping. The potential block retains its direction with a 1 V maximum; prescribed/immobile identity corrections are preserved. Equations/Jacobian, full source, merit, line search and physical convergence gates are unchanged. Both profiles pass 3278 targeted tests; 96 new independent converged equation checks cover both polarities, both II driving modes and two coefficient sets. The parent failed all 48 reverse-bias baseline cases. The first full suites were interrupted after two native FD wall-time limits; all original records remain. Final selection excludes 39 Fermi and 96 zero-II full-history nodes per profile, without changing their definitions or treating them as freshly passed. Sixteen native programs completed 19152 inherited FD scenarios with the same numerical source/objects/bindings and larger execution budgets. Uniform-direction and regularized-gradient failed alternatives remain archived. General HFS/II, arbitrary high-generation convergence, quantum source consistency and complete Sentaurus alignment remain open. No deployment or new commercial comparison. See 368 acceptance (`validation/reverse_ii_main_20261031/ACCEPTANCE.md`; historical archive, not bundled).

## 369: Optional returned-state Newton SG equation audit

`PyDeviceSimulator.solve(audit_newton=True)` and `Simulator.run(..., audit_newton=True)` optionally reassemble Poisson and each carrier SG row on the actual returned classical 1D Newton state, including failed-state rollback. Homogeneous bands and a constant mobility model are required; HFS, BTBT, quantum, FE, Ohmic contacts, active traps, thermal coupling and frozen blocks remain unsupported by this audit. Nonzero electric-field/GQF II, optical generation, SRH and Auger are covered. The SG row gate is separate from Newton's stopping metric and does not establish energy or experimental validity. Default solver outputs and Gummel audits remain unchanged. Both profiles pass 3624 selected tests, including 346 new independent checks. The same 270 inactive nodes omitted in368 remain outside this run; native FD was not rerun. No numerical convergence expansion, new commercial comparison or deployment is claimed. See 369 acceptance (`validation/newton_returned_audit_20261031/ACCEPTANCE.md`; historical archive, not bundled).

## 370: Partial additive HFS/II convergence repair

Classical 1D nonzero-II HFS additive updates now enter the existing paired RMS merit and relative-density trust path. Equations, Jacobian, source, update formula, line search, fallback and physical convergence gates are unchanged; exponential HFS retains its frozen-parent results. Of 96 parent additive failures across both profiles, 90 now pass independent returned-state equations and KCL. Six strong positive-bias p-type GQF cases still fail and are explicitly checked as unresolved, without convergence qualification. Both profiles pass 3962 selected tests (338 new); two native programs rerun 576 inherited HFS/II current Jacobian FD scenarios. The same 270 inactive old nodes remain omitted. Four isolated diagnostics retain all failed alternatives; only the minimal scope guard and a comment enter the numerical source. The CPP file also changed LF to CRLF; normalization and reversal of those two edits restore exact parent bytes. HFS remains unsupported by the public Newton audit. General HFS/strong-II convergence, quantum source consistency and complete Sentaurus alignment remain open. No new commercial run or deployment. See 370 acceptance (`validation/hfs_additive_ii_20261031/ACCEPTANCE.md`; historical archive, not bundled).

## 371: Signed diagonal fallback closes the selected additive HFS/II matrix

After rejection of the original clipped direction, classical 1D nonzero-II HFS additive Newton now compares signed diagonal regularization with its original bounded fallback. Poisson and continuity shifts follow their respective equation signs, in thermal-voltage / relative-density coordinates. Only a lower full-source fixed-base merit replaces the original result; each shifted linear system has an actual residual gate. Full equations, original Jacobian, source, update mapping and final convergence/KCL gates remain unchanged. The six unresolved parent p-type positive-bias GQF configurations now pass independent equations, completing the selected 96-configuration additive matrix across both profiles and three axes. Both profiles pass 3974 selected tests: 3956 preserved parent nodes, six explicitly replaced failure nodes and 12 new trace/tighter-tolerance nodes. Two native programs rerun 576 inherited HFS/II current Jacobian FD scenarios. The same 270 inactive nodes remain omitted. The least-squares timeout, a diagnostic macro compile failure and unsuccessful alternative schemes remain archived; cumulative trials were not all green. Removing the new trigger and fallback restores exact parent CPP bytes, including CRLF. HFS public Newton audit support, default exponential HFS convergence, general HFS/strong-II and quantum source consistency remain open. No complete Sentaurus alignment, new commercial run or deployment is claimed. See 371 acceptance (`validation/hfs_regularized_20261031/ACCEPTANCE.md`; historical archive, not bundled).

## 372: Direct log-coordinate trust for the selected exponential HFS/II matrix

Classical steady 1D Boltzmann nonzero-II HFS exponential Newton now uses the paired fixed-base RMS and direct bounded log-density increments in [-5,5], retaining `u += alpha*du`. Original uniform and signed backup eligibility is extended with policy-specific bounds; the selected successful probe does not hit these exponential backup branches, so their successful-path coverage remains open. Full residual, original Jacobian, sources, update mapping and final physical gates are unchanged; reversing eight direction/merit edits and comments restores exact parent CPP bytes. The 32 frozen parent x-axis failures are explicitly replaced by independent physical success; all 96 selected exponential configurations across both profiles and three axes qualify, and 96 additive frozen states remain exact. All 4212 selected tests pass: 3942 preserved nodes, 32 replaced failure nodes and 238 new file nodes. Strict 1e-10 physical tolerance, insufficient-budget failure, actual primary trust steps and default/explicit policy equivalence are checked. Two native programs rerun 576 inherited FD scenarios; the same 270 inactive nodes remain omitted. The first isolated candidate passes only 7/16 exponential cases; the selected candidate passes 16/16. Diagnostic archive-name errors and collection corrections remain recorded, with no numerical rerun or parent archive overwrite. HFS public Newton audits, general strong-II convergence and quantum source consistency remain open. No complete Sentaurus alignment, new commercial run or production deployment is claimed. See 372 acceptance (`validation/hfs_exponential_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 373: Optional HFS Newton returned-state SG audits

The existing classical 1D Newton audit now accepts HFS by removing its single HFS exclusion. Original nonlinear equations, Jacobian, sources, update mapping and convergence gates are unchanged; reverting that condition restores exact parent CPP bytes. Newton and Gummel sources and both profiles' objects remain exact. All 4958 selected tests pass: 3954 preserved parent nodes, 256 upgraded budget-audit nodes, two retired HFS unsupported nodes, and 748 new file nodes. Independent checks cover 192 converged HFS configurations with complete default/audited equality except audit metadata and exact frozen parent thin results; 384 failed primary/hybrid returned states; 144 cutoff/contact/driving/reference-source configurations; 22 unsupported combinations; and six isolation/forwarding/replacement probes. The audit scores actual returned fields and never changes the convergence verdict. Its original SG gate remains distinct from Newton stopping and independent physical validation. The same 270 inactive nodes remain omitted. Only two DeviceSimulator objects are compiled, with 26 reused objects and 28 fresh dependency checks; no native program or FD rerun is claimed. Parent artifacts and 4695 remote files are reverified. General strong-II convergence, quantum source consistency and unhit search coverage remain open. No full Sentaurus alignment, commercial run or deployment is claimed. See 373 acceptance (`validation/hfs_newton_audit_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 374: Fixed-Q quantum HFS/II source-current consistency

Gummel and Newton avalanche sources now use the same DG-shifted electron/hole transport potentials and saturated SG currents as continuity. Newton's source derivatives hold Q fixed under the existing Picard linearization. Returned generation is rebuilt with the same flux Q as returned currents. The frozen parent counterexample has a normalized generation discrepancy of 0.7647601856884292 in both profiles and is rejected by the independent reference. Final selected regression passes all 5284 nodes, including 4958 unchanged parent nodes and 326 new nodes. Returned-state checks cover 285 nonzero-Q states and three explicitly classified uniform-floor failed-state zero-Q controls. No device convergence is claimed for these low-budget states. The 1152 fixed-Q source cases pass 17280 FD columns / 86400 entries including zero-source controls. The same matrix passes full Newton residual/source-Jacobian insertion and independent Gummel row checks. The inherited 576 classical full-operator FD cases also pass; 192 classical HFS frozen states and 36 classical/quantum II-off controls remain exact. The same 270 inactive nodes remain omitted.

An initial baseline JSON serialization failure and subsequent reference-test failures (39, then three) remain archived. Decimal intervals propagate binary64 observation cells near SG cancellation; the three remaining failed-state fixtures are explicitly zero-Q controls. Production numerical sources, objects and bindings remain unchanged throughout reference revisions. Final regression passes both complete selected sessions. Native construction compiles ten extension targets, reuses 18 objects, performs 28 dependency checks and links two extensions; four main and two assembly native programs are built. Source identity contains 901 files; final and native-build source identities differ only in the new test reference. The native, reference and assembly remote verification sets contain 4758, 5502 and 953 files respectively, with overlap and no mismatches. Quantum Newton KCL current consistency, fixed-point/strong-II device convergence, quantum returned-state audits and unhit search branches remain open. No full Sentaurus alignment, new commercial comparison, deployment or research qualification is claimed. See 374 acceptance (`validation/quantum_ii_current_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 375: Quantum Newton x-1D KCL guard uses the actual Picard transport state

The convergence guard now uses electron phi+Qn, hole phi-Qp and saturated HFS SG currents matching the current continuity residual. Complete lagged Q, fresh DG fallback and empty-mask zero Q follow the residual state selection without refreshing or committing Q. The original 1e-8 A/m2 / 1% mixed threshold and applicability exclusions remain. Outside the extracted guard and call, Newton CPP is exact; classical guard equations, quantum refresh, residual/Jacobian/source operators and line search are unchanged. Both profiles pass 1152 native scenarios, 3456 assembled continuity-difference checks and 7488 state-selection/exclusion checks. Each old-formula misclassification direction has 144 counterexamples; the parent formula is reconstructed independently, with no extra parent native execution. All 5284 selected pytest nodes pass unchanged, retaining 192 exact classical HFS and 36 classical/quantum II-off frozen controls from sealed parent oracles. The same 270 inactive nodes remain omitted. Eight extension targets are compiled, 20 objects reused and 28 fresh dependency checks performed. Eager and main native checks initially crash because the new fixture omits bandgap initialization; one SI crash is also replayed under GDB. A single set_bandgap fixture initializer fixes both profiles without changing numerical core, references or tolerances. The initial main attempt runs no pytest; the final reference run passes both selected sessions using the exact built core and bindings. Six native programs are compiled/linked across these attempts, and only the final pair contributes passing cases. Final and native-build identities differ only in that new test initializer. No FD rerun is claimed. Quantum DG fixed-point/contact-Q consistency, general strong-II device convergence, quantum returned-state audits and unhit search branches remain open. No new commercial run, deployment, research acceptance or complete Sentaurus alignment is claimed. See 375 acceptance (`validation/quantum_newton_kcl_20261101/ACCEPTANCE.md`; historical archive, not bundled).

The eager failure manifest contains an empty-file self-hash because it was opened before file enumeration. The original is preserved; the collector validates that known self-entry, every other file and the actual manifest hash independently, resuming existing downloads without numerical reruns. Main and final export manifests are unaffected.


## 376: Probe undamped DG equations before quantum Newton success

After the original mixed-Q gate and existing post-step refresh, Newton temporarily disables lagged-Q selection, assembles the physical DG residual and evaluates the original block-absolute / scaled-infinity gates and applicable KCL. It uses the candidate fixed-Q system's existing scales; it does not assemble dQ/dn. Rejection schedules the original damped outer refresh. RAII restores selection on success, failure and exceptions without committing Q. Existing transient, frozen and inactive-row constraints remain. Outside one include and this return guard CPP bytes are exact; the Newton class header, classical flow, source/residual/Jacobian and globalization remain unchanged.

Both float128 profiles pass 288 manufactured mixed-Q gate counterexamples and 1728 independently reconstructed DG/SG/HFS/II continuity rows, including 216 active-II rows. Forty-eight cases pass total KCL but fail individual carrier equations. The largest mixed norm is about 8.84935e-35; the smallest physical norm is about 9.7329e-4 against 1e-8. Additional checks comprise 576 equilibrium controls (288 actual uniform public solves) and 874 state restorations including 10 exception/nonfinite/size/original-flag contract checks. These do not add unique scenarios. The parent stopping criterion is reconstructed using actual assembled residuals and a real production damped refresh; no full parent solve false-success trajectory is claimed.

All 1576 selected pytest nodes pass unchanged, including 192 exact classical HFS and 36 classical/quantum parent controls. Remaining parent nodes, FD, full main suite, CMake/CTest, long double and performance are not rerun. Two Newton objects are compiled, 26 extension objects reused, 28 fresh dependency checks performed and two extensions linked. Initial probe and main native fixtures fail compilation in both profiles due to nonexistent yy/zz fields; preserved failures run no pytest. Correct yx/zx fields and added nonfinite/restoration checks pass against the exact built core and bindings. Across all attempts eight native compilations are attempted, four succeed and link/run. Final and build identities differ only in the new native fixture. Production is unchanged and no commercial jobs are added. Contact-Q consistency, independent quantum returned-state audits and general quantum/strong-II convergence remain open; research exclusions and bounded Sentaurus qualification remain. See 376 acceptance (`validation/quantum_fresh_acceptance_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 377: Species-specific DG contact Q throughout Newton

Newton now matches the existing Gummel/returned-current convention: electron Dirichlet contacts pin Qn only, hole contacts pin Qp only, and potential-only boundaries do not pin either carrier correction. Projection follows Q selection in residual/Jacobian/KCL and follows the complete damped refresh in the cache. Local audits do not mutate caches. Outside one include and four insertions Newton CPP is byte-exact; thresholds, DG, fixed-Q linearization, undamped success gate and globalization remain unchanged.

Actual parent cores reproduce 576 residual mismatch states and 48 KCL misclassifications across two profiles. Candidate checks pass 864 matrix scenarios plus 48 KCL cases, 17280 independent continuity rows, 31104 returned flux/Q comparisons and 194400 full fixed-Q Jacobian FD entries (12960 columns). This is basic DG/MB prescribed-state operator qualification, not dQ/dn or general device convergence. Two old manufactured fixtures are explicitly made contact-compatible without changing assertions, reference formulas or tolerances; 1152 KCL scenarios and 288 fresh-gate cases are rerun. All 1882 selected pytest nodes pass unchanged, including exact parent controls. The parent result archive name collision is preserved and recovered without numerical reruns. Production is unchanged; no new commercial jobs. Independent quantum Newton returned-state SG audits, general quantum/strong-II convergence and unhit search branches remain open. Research exclusions and bounded Sentaurus claims remain. See 377 acceptance (`validation/quantum_contact_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 378: Physical-DG Newton returned-state SG audit

Opt-in audit_newton now recomputes physical Q from the returned n/p, pins species-specific contacts and uses independent Gummel SG continuity assembly plus isolated Poisson assembly. Scope is quantum_Newton_SG_final_returned_state; earned convergence and other returned fields are preserved. Temporary Q cache swaps restore empty, complete and incomplete originals on exceptions. Failed reassembly clears stale equation rows. Basic MB/single-axis/homogeneous/all-mobile constant-mobility DG only; unqualified quantum variants remain explicitly unavailable.

Final dual-profile selected pytest: 2476 passed (1878 retained parent configuration nodes, 4 obsolete unavailable nodes retired, 598 added). New native prescribed-state matrix: 864 scenarios, 2592 audits, 7776 independent rows, cache and exception restoration checks. The initial new Python fixture disabled Newton for hybrid cases and retained merged endpoint contacts; 480 failures are preserved. Only new fixture setup was corrected, with unchanged formulas/assertions/tolerances and exact same built core/bindings; final reference_results pass. No deployment or new commercial runs. Fixed-Q FD qualification is inherited from 377 without rerun. General quantum/strong-II convergence and unhit search branches remain open; full Sentaurus alignment is not established. See 378 acceptance (`validation/quantum_returned_audit_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 379: Steady one-dimensional Newton KCL in every orientation

The existing guard now checks x/y/z single-axis devices with the corresponding nonuniform edge lengths. Original x indices/spacings and 1e-8 A/m2 or 1% thresholds are retained. Transient, frozen-carrier, short-chain and multidimensional exclusions remain. Reversing only the applicability/index/spacing edits restores byte-exact parent Newton CPP; all operators, DG/HFS, cache selection and other stopping/globalization logic are unchanged.

Actual parent and candidate cores each run 3456 direction scenarios (1152 inherited x controls plus 2304 new y/z configurations). The parent bypasses 1728 nonconservative y/z states; the candidate classifies all states correctly using independent SG currents, with 10368 assembled continuity-divergence checks and 22464 selection/exclusion probes per version. This is direct guard qualification, not a full public false-success replay. All 2476 selected pytest nodes and old test sources are retained and pass, including exact classical HFS/quantum controls. Only two Newton targets are rebuilt; FD is inherited without rerun. No production deployment or new commercial jobs. General quantum/strong-II convergence, internal-contact networks, multidimensional conservation and unhit search branches remain outside qualification. See 379 acceptance (`validation/axis_kcl_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 380: Internal carrier reservoirs and steady Newton KCL

An internal electron or hole Dirichlet contact can inject current. The single-axis guard now checks total conventional current separately between carrier reservoirs, retaining its original 1e-8 A/m2 or 1% thresholds per section. The unconstrained species at a partial contact retains its full continuity residual gate. Without internal carrier contacts, arithmetic is unchanged. Four reversible CPP edits leave all operators, Jacobians, DG/HFS/cache selection and other stopping/globalization logic byte-exact.

Actual parent and candidate cores each run 4320 new configurations. Independent SG currents identify 1152 parent false rejections and none in the candidate, with 17280 assembled divergence rows, 1152 free-species contact rows and 4320 cache checks per version. The candidate accepts 1440 and rejects 2880 prescribed states. Public solve additionally succeeds in 576 new configurations whose actual parent results all fail convergence despite independently verified returned-state equations. Public quantum fixtures have uniform density and fresh Q=0; nonzero prescribed fixed Q is covered only by native guard tests. This does not qualify general nonlinear quantum convergence.

All 3052 selected pytest nodes pass, retaining 2476 parent nodes and frozen controls. The inherited 3456-case axis matrix is rerun with identical candidate reports. Only two Newton extension objects are rebuilt; 26 objects are reused after 28 fresh dependency checks. No FD rerun, deployment or new commercial jobs. A stale descriptive pytest-count field is retained with an administrative erratum; execution lists and predeclared scope use the actual 1526 per profile. General contact networks, strong-II/quantum device convergence, multidimensional conservation, full main-suite and complete Sentaurus parity remain unqualified. See 380 acceptance (`validation/contact_kcl_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 381: Current native qualification and CTest registration

The quantum-contact fixture now checks all single-axis orientations against an independent contact-section reference. Historical whole-chain/axis-bypass expectations are preserved in archived sources and demonstrably fail against the same stage380 core in both constant profiles. Existing DG/SG/source, returned-field, cache and fixed-Q FD tolerances are retained. The symmetric fresh-quantum probe now checks every axis, adding 96 y/z probes across profiles.

Five current native targets are registered in the product CMake tests. Main CMake discovery confirms registration; a validation-only CMake harness imports hash-verified stage380 core objects and builds/runs the actual product test subdirectory. All 10 selected CTests pass, with 194400 fixed-Q FD entries rerun. This is not a clean main-core build or full CTest qualification. Production sources and bindings are unchanged; Python tests are inherited from380 without rerun. One CMake Python-wrapper startup failure is preserved and corrected by using binaries from the same installation directly. No numerical retries, deployment or new commercial jobs. See 381 acceptance (`validation/native_suite_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 382: Clean main CMake builds and all registered CTests

The unchanged stage381 controlled source now builds directly through the main CMake project in two previously nonexistent build directories, for SI and legacy-charge. All 22 core translation units are newly compiled; no historical objects are imported. Both float128 builds use enabled assertions and the existing native optimization settings, without PETSc. All 56 registered tests per profile pass (112 total), without selection, skips, failures or retries. The five guard reports match381 field by field and rerun 194400 fixed-Q FD entries. HFS warm-start raw states are archived without claiming a new independent Python audit. Four test_*.cpp sources and other probes remain outside registration; Python, long-double and complete repository qualification are not established this round. No solver/test changes, deployment, new commercial run or complete Sentaurus parity claim. See 382 acceptance (`validation/main_ctest_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 383: Register remaining named native regression sources

The four remaining tests/cpp/test_*.cpp sources now have default CTest targets: Fermi trial-domain and one-sided-domain contracts, fixed-Q quantum-II source/Jacobian checks, and returned-state quantum FV audit/cache checks. The existing CMake byte prefix and 56 test registrations are preserved; no numerical source, reference or tolerance changes. Both clean float128 main builds pass all 60 registered tests (120 total), with eight added target executions. Added source FD loops visit 86400 entries using their original scale gate, without dQ/dn. Returned audits compare three independent FV norm classes 7776 times; zero-budget public initializations are expected failures, not successful device solves. Existing guard reports match382 and previous fixed-Q/contact and II-driving matrices rerun successfully. A local newline preflight failure and three collector failures are preserved. CTest show-only clobbered primary LastTest logs; primary JUnit and exit codes survive. Parent logs were restored from sealed originals. The same verified binaries reran all 120 tests successfully and immediately snapshotted complete recovery output; duplicate executions are not extra coverage. No numerical failure occurred. Other probes, general device convergence and full Sentaurus parity remain unqualified; no deployment or new commercial runs. See 383 acceptance (`validation/native_registration_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 384: Native tensor-grid multi-contact port extraction

terminal_currents_native integrates exported Jn/Jp/Jleak on reservoir-to-free-volume edges in every axis, including internal/thick contacts and lateral faces. Disjoint binary named masks and complete finite native fluxes are required. Geometry uses Grid3D full endpoint control widths, explicitly distinct from the old physical half-face 2-D quadrature; reservoir-to-reservoir edges are excluded. This is conduction extraction, not a new convergence or energy acceptance gate.

All 389 selected dual-profile pytest nodes pass, including 186 new nodes and 56 actual native solves seeded with independently computed harmonic resistor solutions. Independent divergence/network checks and 20% current damage controls pass. Original helpers, C++ and bindings remain unchanged; existing SI commercial replay uses the old extractor. One generated-dependency setup failure and 56 initial new-fixture API failures are preserved; only the fixture setter name was corrected before rerunning the selected suite. No compilation, full CTest rerun, new commercial run, deployment or full Sentaurus parity claim. See 384 acceptance (`validation/tensor_terminal_currents_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 385: Reject invalid conservation ledger evidence

Explicit malformed energy/stored-charge totals can no longer be hidden by valid components. DC/time-domain ledgers reject complex arrays before conversion and handle integer-to-float overflow as unavailable evidence. Relative normalization no longer has a smallest-normal denominator floor; explicit SI absolute budgets and default tolerances remain unchanged. Missing totals still permit complete component-only ledgers.

The identical new 93-node contract suite reproduced 46 failures per profile in the sealed parent and passes in the candidate. All 575 selected dual-profile pytest nodes pass, retaining the previous 389 nodes and adding 186. Both public validation class ASTs, existing tests, solver and binding sources remain unchanged. This repairs validation evidence, not general device energy physics. No build, full CTest rerun, new commercial simulation, deployment or full Sentaurus parity claim. See 385 acceptance (`validation/conservation_contract_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 386: Charge-neutral intrinsic and low-doping Ohmic reservoirs

Simulator.set_contact now supplies both carrier Dirichlet values at intrinsic contacts and solves the Boltzmann charge-neutral/mass-action equilibrium at low doping. The larger quadratic root avoids cancellation, and asinh retains near-intrinsic potential offsets. Existing mobility-based carrier-region classification is applied per node for mixed-material electrodes. Other Simulator methods and native core/bindings remain unchanged. Fermi/BGN contact equilibrium is outside this qualification.

All 955 final selected dual-profile pytest nodes pass: 575 retained, 216 new, 164 additionally selected existing nodes. The new suite reproduces 96 failures per profile in the parent Simulator. There are 72 new actual public resistor solutions using the native default initializer, three orientations and uniform/graded grids; maximum analytic current error is 1.81691e-15. Gummel-first mode retains the existing low-DOS Newton fallback. First-run legacy failures in 13 existing configuration nodes also occur with the sealed parent; two analytic doping inputs now use compiled QE, leaving SI inputs and all targets/tolerances intact. Initial logs and the parent probe are preserved. No new commercial run, compilation, full CTest rerun, deployment or full Sentaurus parity claim. See 386 acceptance (`validation/ohmic_equilibrium_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 387: Replace contact mode and validate before writing boundaries

set_contact now removes a saved workfunction when selecting Ohmic mode, so subsequent run/update_contact and configuration replay do not restore a stale Schottky boundary. It rejects invalid scalar parameters, nonbinary/missized contact masks and nonfinite/nonpositive computed boundaries before native writes. Only this method changes; numerical formulas, native code and all existing tests remain unchanged. All 1075 selected dual-profile nodes pass (955 retained, 120 new); the parent reproduces 114 new contract failures. Twenty-four device sequences perform 72 new public solves with analytic resistor checks; maximum current error 3.77476e-15. No user-provided initial guess; later solves reuse accepted states, and Gummel-first keeps its existing low-DOS Newton fallback. No compilation, new commercial run or deployment. Fermi contacts and general convergence remain open. See 387 acceptance (`validation/contact_replacement_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 388: Normalized half-order Fermi integral

Replace the discontinuous and incorrectly normalized scalar function with the documented Bednarczyk (1978) approximation, including range-safe evaluation. Four scalar profile/precision configurations pass against independent DLMF integral quadrature with maximum relative error 0.0037878731; all four parent controls reproduce failures. Rebuild six affected float128 native core units, reuse sixteen audited objects, and pass sixteen selected CTest entries, including 144 prescribed-state Gummel Poisson charge-map checks. Long double is scalar-only. No Python extension build, Python rerun, deployment or commercial job. Intrinsic FD density remains the prior Boltzmann approximation; contact and transport/variable consistency are still open. See 388 acceptance (`validation/fermi_half_20261101/ACCEPTANCE.md`; historical archive, not bundled).

The final prescribed-state fixture explicitly disables Boltzmann stabilization on both solvers to audit physical charge. The prior fixture failed 18 damaged-input controls per profile because its stabilized RHS norm hid charge errors; full failures and a diagnostic probe are preserved. Default stabilized residual qualification remains open. A separate JSON report collection failure was repaired without recompilation or numerical reruns.


## 389: Isolate the physical unscaled Poisson diagnostic

The legacy residual_norm now assembles physical equations in a local copy with artificial Gummel stabilization disabled and the supplied potential refreshed. This removes stabilized-RHS dilution and stale-iterate contamination without replacing the live matrix or caches. The default Gummel scaled acceptance was already physical and is unchanged. Both profiles pass 32 selected CTest entries in total, including 768 analytic prescribed-state combinations and 40 invalid inputs; the parent hides 480 damaged-state diagnostics across the two profiles. These are diagnostics, not device solves or default false acceptance. Recompile only two Poisson objects and reuse twenty objects after header-code and provenance checks. No new extension, Python tests, commercial run or deployment. Unscaled neutrality/offset limitations and general FD contact/transport consistency remain open. See 389 acceptance (`validation/physical_raw_residual_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 390: Intrinsic FD neutrality

intrinsic_density now solves n=p at a shared Fermi level using the current normalized F_half approximation in log density, instead of returning the Boltzmann placeholder. The MB branch and other statistics functions remain unchanged. Four scalar profile/precision candidates pass 84 independent quadrature neutrality references per run (maximum relative error 0.0037684445), 87 MB bitwise controls, five range controls and 19 invalid inputs; four parent valid-state controls fail as expected. Rebuild six dependency-verified native units and reuse sixteen audited objects; forty selected float128 CTest entries pass across two profiles. Long double is scalar-only. No Python extension, Python rerun, deployment or commercial/experimental qualification. General degenerate recombination detailed balance, FD contacts and transport/variable consistency remain open; intrinsic n=p does not establish a general FD mass-action identity. See 390 acceptance (`validation/fd_intrinsic_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 391: Auger sink and physical transient audit

Gummel implicitly linearizes forward Auger recombination while lagging reverse generation. Its transient audit excludes iteration derivatives and uses net transport, actual storage and source scales. Final native qualification: 288 uniform classical return states (270 Gummel, 18 explicitly handed from a rejected Gummel seed to existing Newton), plus 48 prescribed-state audit controls. This does not qualify public automatic routing or standalone stiff-generation Gummel convergence. Rejected revisions and failed probes are retained; final selected CTest 42 pass. No Python extension, deployment, commercial or general FD qualification. See 391 acceptance (`validation/auger_generation_sink_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 392: Public classical Auger transient

DeviceSimulator now forwards the Auger switch and coefficients into its existing direct Newton transient path. Scope: Boltzmann, no FE, paired positive mobilities. FD/FE/blocked combinations fail before any trial. Both native profiles pass 108 public uniform trajectories, 8 guards and 46 selected CTest entries. Strong generation explicitly enables the existing adaptive controller; no manual Gummel handoff was added. This does not qualify arbitrary devices, spatial convergence, FD detailed balance or full Sentaurus alignment. No Python rebuild, deployment or new commercial run. See 392 acceptance (`validation/public_auger_transient_20261101/ACCEPTANCE.md`; historical archive, not bundled).


## 393: Python binding integration of stages 388-392

Two clean float128 CPython 3.13 extension builds compile all 26 objects with no object reuse. Effective unique-node dual-profile pytest evidence: 1873 pass, including 108 independent public Auger BE trajectories and 8 scope guards. This combines unaffected passing initial tests with five corrected/dependent files rerun, not a final full rerun. Initial failures are retained; only valid FE test damping and compiled-charge test references changed, without numerical gate relaxation or recompilation. Two diagnostic pytest-cache mutations and collection recovery are explicitly recorded. Prior pre388 extensions reproduce 98 new-test failures, including guard-message contracts. Four failed setup starts and a local newline preflight are preserved; initial failures compile no C++, although two generate Cython CPP. Existing build dependencies were privately isolated, with no global install or runtime-path change. No production numerical source changed in this stage. Candidate extensions are archived; no wheel, deployment, new commercial run or full Sentaurus parity. See 393 acceptance (`validation/python_core_integration_20261101/ACCEPTANCE.md`; historical archive, not bundled).
