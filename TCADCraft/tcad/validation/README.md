# TCAD 验证策略集

[????????????????](../../docs/validation/thermionic_thermal_refinement_20261018/README.md)
????? Sentaurus Kappa ????????????Sentaurus ????? Kappa ??? W/(K?cm)??? 1e-4 W/(K?cm)=0.01 W/(m?K)?? Python ???????? 40?80 ???/??????? 0.041%/0.026%?Python 256 ?? 450 K ??? 0.012%???? 6.589%??????????? 0.1 V ?????????????????????

[热发射界面与温度场同一步联立](../../docs/validation/thermionic_coupled_20261018/README.md)
新增带两侧界面密度迹的热发射电热瞬态入口，电子/空穴/陷阱/温度同一步联立，界面携能进入局部热平衡与开放端口能量账本。新增 33 项检查，专项回归 1270 项通过；独立 ODE 时间加密最细状态误差 0.111%。实际重跑 4 次含热方程的 Sentaurus，原生 12/24/48 格均完成推进与审计；最细电流最大差 0.122%，最高温升最大差 38.7%，仍未通过原定热学门槛。量子-热发射耦合、界面温度重构、商业能流验收、原生完整多物理集成与真实材料动态标定仍缺。

[非等温界面能量矩与局部量热账本](../../docs/validation/thermionic_energy_20261018/README.md)
新增等有效质量、Maxwell–Boltzmann 非等温热发射粒子/能量/熵通量，以及冻结储库的局部转移量热账本和稳态器件适配器。新增 40 项检查，专项回归 1237 项通过；72 组独立积分的最大归一化能量矩误差 8.32e-15，局部能量残差 4.13e-33 J。实际重跑 8 次 Sentaurus；修正界面取样后的等温粒子电流最大相对差 0.002%。本轮没有非等温商业携能验收，没有推进温度场或器件状态；完整器件能量闭合与真实材料动态标定仍未完成。

[异质结双侧迹与等温热发射商业对照](../../docs/validation/heterojunction_interfaces_20261018/README.md)
新增异质结双侧活度迹、有限界面传输电阻和等温 Poisson–电子–空穴自洽稳态求解，覆盖斜界面解析通量、带边/态密度跳变平衡与独立界面审计。专项回归 1197 项通过。实际重跑 Sentaurus 300/450 K、0.1 eV 阶跃 Thermionic 控制，12→24 格后电流最大差 0.565%，内部密度最大差 0.766%、电势最大差 0.0553 mV。商业验收限于等 DOS/等有效质量平面界面；非等温热发射携能、通用质量/谷简并界面模型、原生集成、FE 联合闭合与真实动态材料验收仍缺。

[多切面物理端口与二维斜接触商业对照](../../docs/validation/oblique_contacts_20261018/README.md)
新增多切面物理端口分组、总电流/位移电流/源功和携能积分及独立审计；拒绝漏面、重叠和非等势分组。实际重跑二维梯形斜接触 SDE/SDevice，300/450 K 两温度及商业两级网格，原生 4/8/12 格加密。最细网格电流最大差 0.488%、最大温升差 1.774%，内部探针温升最大差 2.529%；专项回归 1181 项通过。验收限于均匀 Boltzmann/Kelvin 斜接触模型；异质结、大场单调性、原生多物理场集成、FE 联合闭合和真实材料动态验收仍缺。

[斜切网格 HMM 输运、热与量子验证](../../docs/validation/mimetic_transport_20261018/README.md)
新增共享面 HMM 对数活度输运、一致导热与变分量子能。斜切线性漂移/热通量归一化误差从旧两点路径约 1.16 降至 3.2e-13 以下，光滑制造解与载流子扩散均通过网格收敛检查。专项回归 1164 项通过。新跑 Sentaurus 300/450 K 自热电阻，16 单元电流最大差 0.057%、温升最大差 0.161%。该路径限于均匀带边/参考态密度；大场单调性、通用非线性商业验证、原生集成、FE 联合闭合与真实材料动态标定仍缺。

[开放接触与双向热电耦合验证](../../docs/validation/electrothermal_contacts_20261018/README.md)
新增开放载流子接触、载流子携能与端口电流账本，密度/陷阱/共同载流子晶格温度同一步联合求解；迁移率、扩散和 SRH 发射率接受温度反馈。专项回归 1144 项通过。新跑 Sentaurus 300/450 K 两级网格热电电阻，16 单元电流最大差 0.061%、温升最大差 0.164%。此结果限于固定带隙、Boltzmann/Kelvin 均匀材料模型；通用斜切一致输运、原生多物理场集成、FE 能量联合闭合与真实材料动态标定仍未完成。

[非 LK 历史、多区域 cut-cell 与载流子联合能量](../../docs/validation/multiphysics_history_20261017/README.md)
新增 NLS、单 play Preisach 和 Sentaurus Preisach 单集合历史守恒迁移，完整保留转折点栈；实际重跑 Sentaurus 九段嵌套回线，网格中途迁移后的 504 点最大极化差 5.42e−16 C/m²。新增非凸多区域共同切分及共享面载流子/陷阱/图量子/晶格热求解和独立能量审计，受限模型最大能量残差 2.27e−32 J。末次专项回归 1118 项通过。电子温度固定，通用斜切一致输运、开放接触携能、原生完整多物理耦合与完整器件能量闭合仍缺。

[守恒历史、共享 cut-cell、共同能量和实验动态标定](../../docs/validation/conservative_physics_20261017/README.md)
新增带显式 Landau 能量预算的 LK 极化历史守恒迁移和绝对时钟续算；新增任意凸半空间共享面 cut-cell 与守恒混合 Poisson 求解器；公开材料半边共同能量审计，8 个二维/三维无电荷 FE 算例闭合。实际导入两种 6 nm HfO₂ 样品的动态原始数据，单时间常数及 Weibull 拟合均未通过原定留出门槛。末次主回归 906 项通过，能量专项 242 项通过。Preisach/NLS 历史迁移、通用载流子 cut-cell、载流子/陷阱/热/量子全能量和已验收真实动态材料仍待补齐。

[渐变网格与强响应三维 FE](../../docs/validation/graded_fe_mesh_20261017/README.md)
新增保持物理外边界及材料分界的渐变坐标，拒绝间距精度不足的极端网格。实际完成三档强响应三维 FE 重放，最细方案对既有严格 Sentaurus 16/32 参考的最坏误差为 7.77981%，未通过原定 5% 门槛；原生内核、材料参数与参考均保持原样。

[自然边界半单元与 LK 场一致性](../../docs/validation/natural_fe_boundary_20261017/README.md)
新增显式自然边界半单元声明，同步 LK 场、材料响应/雅可比和局部能量体积；制造解与独立多维方程验证通过，并修复稳态 C++ 异常未转换为 Python 异常的问题。复用严格 Sentaurus 16/32 参考，原生 32 网格最坏误差 14.07020%，仍未通过 5% 门槛；未将边界修正标为强响应三维对齐完成。

为物理效应开发提供系统化的验证框架，确保代码正确性和可靠性。

[强极化率三维 FE 与共同能量审计](../../docs/validation/strong_fe_surface_20261017/README.md)
新增 FE/氧化层共同能量审计，独立核算端口功、介电储能、Landau 储能、LK 耗散及后向欧拉修正；三个方向、两种 Landau 系数的原生非均匀堆栈通过受限能量闭合，局部 LK 与整体能量残差均低于 1e−11。另实际完成强极化率三维 Sentaurus 16/32 两档严格瞬态及各九时刻单元场导出；商业网格最坏分量差异 1.631%，原生保留网格对两档参考的最佳最坏差异 13.979%。末次八文件 439 项通过，包含已知未收敛参考的拒绝检查；强极化率三维和商业单元能量仍按原门限判定，不以全局小残差替代局部 LK 检查。FE 历史保守迁移、通用 cut-cell、完整器件能量和真实材料动态标定仍未全部完成。

此前
[四面体接触面电荷与三维 FE 对齐](../../docs/validation/tetrahedral_surface_20261017/README.md)
新增四面体单元侧接触面积分，按单元电势梯度、材料介电常数与局部极化重建 D，避免界面节点平均量污染端口电荷；覆盖面方向、材料突变、线性极化及无效网格检查。实际重跑两档三维 Sentaurus 瞬态并保留各九个时刻的单元场，适中极化率 FE 角块/氧化层混合控制通过原定商业 2%、原生 5% 门限；商业面电荷网格差异从旧节点积分的 3.413% 降为 0.840%，原生对两档参考的最佳最坏分量误差为 2.482%。末次相关五文件 197 项通过，含重新求解的原生 16 格控制。旧节点积分的失败记录及强极化率未通过用例保持原样。FE 历史保守迁移、通用 cut-cell 输运、完整器件能量闭合和真实材料动态标定仍缺；历史全量回归未重跑。

此前
[三维非均匀 FE 与商业收敛审计](../../docs/validation/nonuniform_fe_3d_20261017/README.md)
新增商业非线性日志审计，拒绝绝对残差提前停止、未收敛、截断及失败后续跑掩盖。实际新增 11 次三维 SDevice 尝试、9 次完成、2 次超时；保留全部失败和原始输出。建立 FE 角块/氧化层混合三维对照，独立检查 Ex/Ey/Ez 和 Px/Py/Pz、端口电荷/电流，保持原生 5%、商业网格 2% 门限。强极化率用例尚未通过，适中极化率控制仍有预定门限未通过。其中适中控制的场/三向极化/电流商业网格差异最大 0.898%，面电荷差异 3.413% 超过 2%。末次相关五文件 110 项通过；该计数包含对已知不合格参考的拒绝测试，不表示三维混合场验收全通过。原生内核与 113 位二进制保持不变，历史全量回归未重跑。FE 历史保守迁移、通用 cut-cell、完整能量闭合和真实材料动态留出验收仍缺。

此前
[配置继承与三维商业 FE 控制](../../docs/validation/configuration_inheritance_20261017/README.md)
按用户要求将配置继承、通用 cut-cell、三维商业 FE、能量闭合和真实材料动态标定提升为优先任务，详见本轮优先清单。已加入配置配方与物理坐标重映射，保留运行时接触/功函数、求解器、模型、显式节点/材料字段、电子初值及电压延续，并使事务回滚同时还原配置；自适应从原坐标加密且默认不推进物理时钟。末次相关七文件 512 项通过，三维商业模块 5 项通过；保留初次测试及轻量适配器兼容失败和修复。实际新增 8 次三维 SDevice 尝试、7 次完成、1 次超时，最终接受两档 128 位均匀场 FE 参考，非零观测最大相对差异 1.21e-13；零横向场通过原定绝对门限。这只关闭三维均匀场控制：FE 历史保守迁移、非零三向耦合、通用切割面输运、完整能量闭合和真实材料动态留出验收仍缺。

此前
[一维二维局部自适应与闭环验证](../../docs/validation/adaptive_dimensions_20261017/README.md)
补齐一维/二维局部标记与公开 base_shape 配置，覆盖三维外侧边，统一正式网格构造，修复提前停止的历史列长度。5×1×1/5×3×1 的空标记现能只平分指定区间；两轮零失败，首轮 536 项、后轮 196 项，按最终集合八文件 557 个不同检查覆盖通过，新增 177 项。三轴线/三平面/三维共 12 种组合验证原生加密与重求解；复用既有两档实际 Sentaurus 薄层参考，24 次粗细原生电容重放最大电荷差异 0.000138%，未新增商业运行。仅为张量轴区间加密与启发式指标；内部夹杂自动发现、通用 cut-cell/部分电极、三维商业 FE、完整能量及真实材料动态标定仍缺。

此前
[非均匀输运与端口面积修复](../../docs/validation/nonuniform_transport_20261017/README.md)
补齐非均匀输运后处理：SG/机理拆分/KCL 使用实际边长，二维端口采用端点半面积，完整顶底电极不再因角点误判，原生 quad 通量优先并统一加入泄漏电流，BTBT 使用控制体积积分。旧探针电流偏差 80%、侧面高估 50%、顶面越界和 BTBT 高估 33.3% 已消除。合并八文件 309 个不同检查通过，新增 61 项；1 项跳过、一项旧慢用例排除，保留初次收集、探针、测试失败及中断。八组非均匀重放对既有两档 Sentaurus 最终稳态 Si 导电分支最大差异 0.000959%，没有新增商业运行；不是混合几何瞬态或真实材料标定验收。切割面输运、亚网格部分电极、带电瞬态障碍、三维商业 FE、完整能量和真实材料动态验证仍缺。

此前
[非均匀网格坐标、体积与传递修复](../../docs/validation/nonuniform_mesh_20261017/README.md)
修复高层 Simulator 丢失非均匀坐标、控制体积与网格传递使用均匀坐标的问题，统一实际步长用于加密局部/全局指标，并修复单节点方向空均值。旧探针中间电势偏差 80 mV、最小体积高估 400%、插值偏差 0.4，重放后分别为零、2.22e-16、1.11e-16。首轮 653 通过/3 个新增测试漏参失败/1 个原有警告；修正并补齐全局指标后相关两文件 107 项通过，合并 12 文件 668 个不同检查通过，新增 88 项。复用既有两档实际 Sentaurus 薄层参考，六组非均匀重放电荷差异最大 0.000138%，未新增商业运行。仅覆盖端点节点式张量网格；旧输运后处理的平均步长、完整 cut-cell/部分电极、三维商业 FE、完整器件能量及真实材料动态标定仍缺。

此前
[圆锥与凹棱柱多交段及商业对照](../../docs/validation/primitive_cut_edges_20261017/README.md)
补齐 z 轴 Cone 与简单凹多边形 Prism 的全部介电交段，修复隐藏圆锥/凹棱柱边系数低估 8%/16% 的问题。实际新增三次 Sentaurus 凹多边形静电运行：64/128 商业网格差异 1.564% 超过 1% 门槛，保留拒绝；128/256 差异最大 0.554% 通过。原生 16/32/64 格仍拒绝，128 格最坏差异 1.638%，通过预先固定的 3% 预算。12 文件 514 个不同检查通过，新增 134 项；原生内核不变。仅为边线系数与二维五点扰动/通量对照；通用切割面输运、部分电极、FE cut-cell、带电瞬态台阶、三维商业 FE、完整器件能量及真实材料动态标定仍未完成。

此前
[曲面解析交段与二维夹杂对照](../../docs/validation/curved_cut_edges_20261017/README.md)
补齐 Sphere 与轴向 Cylinder 的解析弦段/端盖区间，支持与 Box 混合的多次界面穿越和覆盖。原探针均低估 8%，相同重放误差降至 2.22e-16。新增两组实际 Sentaurus 圆形介质夹杂静电运行；按运行前固定的 3% 扰动/电容增量预算，16 格 4.030% 保持拒绝，32/64/128 格分别 2.374%/1.907%/0.693%，通过两档商业参考。相关七文件 335 项通过，其中新增 95 项；原生内核不变。只覆盖介电边线积分，不穿越任何网格边的夹杂仍不可见；通用切割面输运、部分电极、FE cut-cell、带电瞬态台阶、三维商业 FE、完整器件能量与真实材料动态标定仍未完成。

此前
[Box 多界面边积分与隐藏薄层](../../docs/validation/box_cut_edges_20261017/README.md)
补齐 Box 区域多界面介电边积分，覆盖没有网格节点的隐藏薄层和重叠区域，修复关闭 cut-cell 后残留系数及同材料边反向系数。旧探针首边误差 5.92%；两次实际 Sentaurus 静电运行中，原生端口电荷最大差异 0.000138%，通过运行前固定的 0.001% 预算；三档节点与独立解析电容及原生瞬态储能一致。468 项既有检查通过，新增 76 项修正测试漏参后通过，分两次覆盖 544 个不同检查；保留首次收集失败、漏参失败及一个未收敛点警告，原生内核不变。其他形状仍为采样近似；切割面输运、部分电极、FE cut-cell、带电瞬态台阶、三维商业 FE、完整器件能量和真实材料动态标定仍缺，comments 尚未全部关闭。

此前
[多维 FE 内存修复与二维双阱脉冲反转](../../docs/validation/compact_fe_20261017/README.md)
将多维材料侧 LK 导数从 `3N²` 压缩为坐标线存储，保持相同方程。80 网格独立进程峰值 RSS 从 4,201,320 KiB 降至 195,524 KiB，减少 95.35%，相同商业接受时刻下七类导出观测数组逐项相同。新增 48 项 quad 导数、有限差分及存储检查。实际补充两次 Sentaurus 二维双阱正负脉冲运行，商业网格及表面 D/电流一致性通过原定 2% 门槛；原生 20 网格横向极化误差约 8.28%，保持拒绝。原生 40 网格通过两组商业参考，最大分量差异 2.964%；这是人工高场、局部三次 LK 的采样波形对照，不能代替真实材料、完整空间场或准静态回线验收。完整回归 60 文件、3074 项通过、1 个原有预期警告（1168.91 s），源文件、原生内核及商业原始记录执行前后校验，历史证据保持封存。三维商业 FE、移动载流子与二维 FE 商业联立、梯度能/畴壁、通用 cut-cell/部分电极、带电瞬态台阶、完整器件能量及真实材料动态标定仍缺，comments 尚未全部关闭。

此前
[二维矢量 FE 商业对照与大网格修复](../../docs/validation/multidim_fe_commercial_20261017/README.md)
增加非均匀 FE/普通介质二维矢量 GLK 的实际 Sentaurus 对照。
原生 12 至 56 格未通过原定 5% 分量预算；80 格通过两组商业网格，
最坏 Py 差异 2.860%、电流差异 2.219%。较大无载流子材料侧算例保留线稀疏结构，
采用 quad GMRES，20 格单次对照由 143.94 s 降至 2.17 s，导出观测量相同。
修复迭代舍入导致绝缘体 n/p 固定下限不相等、端口电流不可用的问题。
64 格商业表面 D/电流一致性及 Solver II 原始电流仍拒绝，未混合为合格参考。
既有 3015 项回归通过（815.54 s，1 个预期警告），新增 11 项通过（253.01 s），
合计 59 文件、3026 项通过；339 个冻结输入、53 个原生构建输入、1123 个商业原始文件
及八份历史证据身份核验通过。
三维商业 FE、完整空间/器件能量、cut-cell 及真实材料动态验收仍未关闭。

此前
[台阶商业对照、稳态混合几何、多维 FE 与材料静态标定](../../docs/validation/stepped_multidim_20261017/README.md)
将普通稳态载流子控制体积与瞬态统一，并线性化 Gummel 的 SRH 复合项。
显式分数电荷体积的旧稳态配置保留历史界面节点约定，未作为通用 cut-cell 验证。
实际新增两组 Sentaurus 台阶 Si/HfO₂ 稳态对照；16／24 格横向场不通过固定 5% 预算，
32 格通过两组商业网格，最坏场差异 4.663%、电流差异 1.165%。
显式二维／三维局部三次 LK 已通过独立完整非线性方程组、固定电荷 Gauss 与回滚检查。
新增有来源、特定工艺的 AlScN Pr／Ec 静态标定，动态黏滞系数及实验不确定性仍未识别。
完整冻结回归 57 文件、3015 项通过，815.46 s；另行兼容扩展 72 项通过。
319 个冻结输入、53 个原生构建输入、1035 个商业原始文件及七份历史证据身份核验通过。
多维 FE 商业对照、通用 cut-cell、
完整器件能量及真实材料动态／器件验收仍缺，`physical_validated=False`。

此前
[带移动空间电荷的二维初始化修复与商业对照](../../docs/validation/mobile_space_charge_2d_20261017/README.md)
为经典 PB 增加显式布尔载流子材料掩码，绝缘体保留固定 Poisson 电荷而移动密度严格为零。
六组旧探针电势偏差约 7.601 mV、首区间总电流不可用；修复后六组独立 PB／SG／BE／Gauss／KCL 均通过。
实际新增 4 次 Sentaurus Si／HfO₂ 二维移动空间电荷运行。原生 16 格横向场不通过原有 3% 预算，
24 格对最细商业网格的正／负参考最大差异约 2.09%，通过相同预算；原始商业 Charge 仍拒绝。
新增 49 项，独立针对性 160 项通过；完整回归 53 文件、2885 项通过、1 个预期警告，825.62 s。
316 个输入、53 个原生构建输入、1007 个商业原始文件及六份历史清单／产物身份核验通过，新增商业文件 68 个。
台阶障碍商业对照、稳态裁剪几何、cut-cell、多维 FE、完整能量及真实材料验收仍缺。

此前
[局部固定电荷二维商业对照](../../docs/validation/charged_mixed_2d_20261017/README.md)
补齐无移动载流子的二维混合 SiO₂／HfO₂ 局部固定电荷参考，实际新增 8 次 Sentaurus 瞬态。
粗网格拒绝；四组加密正／负参考通过原有 2% 剂量、Gauss 和波形预算。
原生 32 格对最细商业网格的电势／双向电场／绝对端口电荷最大差异约 0.7851%，
位移电流峰值归一差异小于 3.5e-12；原始商业 Charge 仍因约 100% Gauss 失配而拒绝。
该阶段新增 34 项，针对性 152 项通过，原生求解器不变；当时缺少的平直二维移动空间电荷参考由本轮受限补齐，台阶障碍仍缺。
完整回归 52 文件、2836 项通过、1 个预期警告，453.49 s；311 个输入、53 个原生构建输入、
939 个商业原始文件及历史产物执行前后身份核验通过，新增商业文件 200 个。

此前
[混合网格总端口电流修复](../../docs/validation/mixed_terminal_currents_20261017/README.md)
开放满足完整电极／储库条件的二维／三维混合总电流，逐区间检查空阻断节点两端净电荷与源项。
24 组独立 Gauss／KCL 全部通过；18 组非法源项／阻断初始净电荷探针不再误导出总电流。
新增 70 项，针对性 308 项通过，含另行纳入的 108 项原有介电能量检查。
完整回归 51 文件、2802 项通过，443.39 s；源码、内核、739 个商业原始文件及历史产物身份核验通过。
实际新增 2 次 Sentaurus 二维 Si／SiO₂ 并联通道瞬态；三轴及两种密度表示共 12 次／252 时刻重放均通过，
十项观测最大差异约 0.0009591%，低于运行前声明的 0.2% 预算。
该商业控制包围净电荷为零；非零空间电荷／台阶障碍、多维 FE、cut-cell 和完整器件能量仍待验证。

此前
[瞬态混合控制体积修复](../../docs/validation/transient_mixed_volumes_20261017/README.md)
统一 BE 载流子存储、源项和端口通量的完整节点几何，修复
[上一轮门禁](../../docs/validation/mobile_charge_scope_20261017/README.md)仅拒绝账本的实际输运问题。
新增 48 项二维／三维、旋转、非均匀网格、线性／对数密度、Poisson／SG／BE 和生成／SRH 独立方程检查。
最大密度标度误差从 0.128 降至 2.365e-11，电荷审计由 8/48 变为 48/48 通过；针对性 167 项通过。
完整回归 49 文件、2624 项通过，438.41 s；源码、内核、711 个商业原始文件及历史产物身份核验通过。
既有实际 Sentaurus FE／Si 的 4 次／84 时刻重放均通过，最大波形差异仍约 0.01004%，修改前后状态一致。
该轮无新增商业运行；非零空间电荷多维商业对照、稳态裁剪几何、cut-cell、完整能量及商业原始 Charge 语义仍未验收。

[含载流子／混合界面的 LK 默认入口](../../docs/validation/lk_transport_default_20261017/README.md)
满足范围的一维双载流子和 FE 绝缘体／半导体中点界面，无模式开关即可采用联立材料侧求解，
保留生成／SRH、显式覆盖和不支持模型的原方程。新增 140 项，含独立完整方程、高层入口和自适应粗步／半步。
针对性 337 项、补充高层 6 项及自适应 6 项通过；完整回归 47 文件、2524 项通过，418.36 s。
重放两组既有实际 Sentaurus FE／Si 数据：旧默认 4 次中途失败、4 次完成但拒绝，
新默认 8 次／168 时刻全部通过，最大波形差异约 0.01004%。本轮无新增商业运行。
多维、cut-cell、非单调粗步、显式旧路径、真实材料和原始商业 Charge 账本问题仍缺。

此前
[一维 FE 绝缘体／半导体界面修复](../../docs/validation/lk_interface_material_20261017/README.md)
支持显式材料侧 LK 中点界面，在三个方向保留完整载流子体积、源项与存储，并拒绝会被丢弃的绝缘体输入。
新增受限的混合堆栈总电流导出和独立 KCL／Gauss 检查，新增 44 项通过。
实际新增两次 Sentaurus HfO₂／Si 非零 FE 运行，8 次／168 时刻重放最大差异约 0.01004%。
原始商业 Charge 仍不通过物理 Gauss 审查。最终 46 文件回归 **2384 passed，371.00 s**，封存身份见报告。
该阶段尚缺的含载流子默认入口已有上述受限扩展；多维、cut-cell、真实材料和完整器件认证仍缺。

此前
[一维含载流子 LK 材料侧修复](../../docs/validation/lk_carrier_material_20261016/README.md)
新增显式输运路径，联立 Poisson／SG／后向欧拉、生成／SRH 和非局部极化响应，新增 83 项物理与诊断检查。
三轴复现的材料侧 LK 归一残差从旧中心场路径的约 0.60 降至约 2e-16。
4 次新增实际 Sentaurus 均完成，但 Silicon 中 P 全为零，依官方模型范围拒绝作为非零 FE 参考。
它们仅作为零 FE 输运控制，8 次重放最大差异约 0.00096%；原有 13 组商业参考的判定保留。
最终 45 文件回归 **2340 passed，330.53 s**，针对性 107 项通过。
该阶段尚缺的半导体／绝缘体交界及非零 FE 商业联立已有上述受限扩展；回归范围见各报告。

[未设置模式时的 LK 默认入口修复](../../docs/validation/lk_auto_integration_20261016/README.md)
使符合条件、实际步长单调的一维无载流子介质链，在不调用任何模式开关时也采用联立材料侧求解。
三档原生网格修复前均报告收敛，但极化跨度达 1.47～1.96 C/m²；当前均匀目标跨度为零。
显式覆盖及不符合条件的模型保留原有方程；不改变配置 dt 或忽略载流子／源项。
新增 68 项检查，针对性 336 项通过；原生 quad 核心重新编译。
最终 36 文件回归 **1950 passed，288.58 s**。
13 组未修改的实际 Sentaurus 参考完成 36 次／7700 点重放，保留全部通过与拒绝判定。
显式分裂、非单调粗步、自由载流子、多维 FE 及完整物理认证仍缺。

[一维耦合 LK 默认路径修复](../../docs/validation/lk_default_material_20261016/README.md)
使符合条件的无载流子介质链自动采用材料侧模式，不再需要额外开启空间修复开关。
三档原生网格先前虽报告收敛，极化跨度达 1.79～2.22 C/m²；当前均匀目标中跨度为零。
显式 True 仍强制检查适用范围，显式 False 保留旧离散；自动条件每次运行重新判断。
13 组既有实际 Sentaurus 参考完成 36 次／7700 点默认路径重放，保留原通过／拒绝判定。
新增 58 项检查，针对性 346 项通过；原生 quad 核心重新编译。
最终 35 文件回归 **1882 passed，282.32 s**，含另行纳入的 58 项原有电气误差控制检查。
分裂、自由载流子、多维 FE 和完整物理认证仍未完成。

[绝对电极电荷审计](../../docs/validation/sentaurus_fixed_charge_ports_20261016/README.md)
提供公开的物理表面通量积分和高斯定律门禁，独立输入实际包围电荷及完整边界覆盖声明。
新增 13 次实际 Sentaurus 运行全部完成，定位到 0.195%～1.56% 的体电荷剂量离散偏差。
四组新增细网格场通量参考同时通过剂量、闭合和波形预算，最大波形差异低于 0.060%。
原始 Charge 记账差异仍未解决并继续拒绝，不能把新通量电荷冒充为原始输出。
新增 87 项检查；原生核心与二进制保持不变，完整物理认证仍未完成。
最终 33 文件回归 **1766 passed，332.73 s**，新增针对性检查 **87 passed**。

[固定体电荷 LK 修复](../../docs/validation/lk_fixed_charge_20261016/README.md)
将显式一维材料侧模式扩展到不移动的内部电荷，逐边 D 满足高斯定律，两端浓度必须为零。
新增 51 项独立完整方程、解析极限、quad 精度、端口、回滚、自适应及输入检查。
8 次实际 Sentaurus 均完成，首轮 4 次配置诊断保留，正式使用修正后的 4 次。
细商业网格下 P 轨迹差异不超过 0.007561%，电流不超过 5.968e-7，局部电场不超过 0.1183%。
商业原始 Charge 的体电荷闭合仍未解决，四组完整电荷参考均拒绝。
最终 32 文件回归 **1679 passed，331.95 s**，最终构建针对性检查 117 项通过。
默认中心场、自由载流子、多维 FE 及完整物理认证仍未完成。

`BirthDeathChain.tail_below` 直接补偿累加错误事件，保留小于单位舍入误差的已计算
尾质量；稳态只接受唯一闭合通信类，非唯一混合及不可导出的正质量明确拒绝。
概率状态、类型和整数索引校验在初始化及观察/更新前执行。
[概率审计](../../docs/validation/electron_probability_20261016/README.md)用独立有理数
方程覆盖 64 种零跃迁拓扑，相关 309 项检查通过；仍无任意极小尾概率的传播误差保证
或实验速率标定，不能把该数值验证当成目标器件 BER 证据。

生灭链 `advance(dt)` 对整次请求提交状态，局部分块/矩阵平方失败不保留部分推进，
返回分布与已接受状态隔离。速率组装采用有界尺度，无量纲时长保留二进制指数，
避免可求解过程被中间溢出误拒绝；正归一化速率或整体参数下溢明确报错。
[推进范围审计](../../docs/validation/electron_propagation_20261016/README.md)记录
367 项相关检查及独立 Decimal/生成矩阵参考，不认证任意极小尾概率的传播精度。

局部级数与平方路径初始级数去掉总质量阈值/固定项数截断，保留浮点递推产生的
全部正 Poisson 权重，修复尚未到达远端状态就返回零概率的问题。
[远端尾概率审计](../../docs/validation/electron_tail_series_20261016/README.md)记录
新增 58 项、合计 425 项相关检查，含 800 位 Decimal 正项和及实际译码 BER。
这仍不覆盖所有次正规尾和、舍入与归一化误差，也不认证真实可靠性参数。

内部概率向量、Poisson 权重及矩阵加入二进制缩放，在局部分块和矩阵平方之间
保持指数余量，整次请求完成后再导出公开 float64 分布，修复最小正质量在逐项
乘积中全部下溢及弱跃迁在平方前消失的问题。
[次正规传播审计](../../docs/validation/electron_subnormal_20261016/README.md)记录新增
132 项、合计 557 项相关检查及独立 Decimal 参考。缩放不增加尾数精度，完整
传播误差预算与真实可靠性参数仍未完成。

Schottky 接触饱和电流改用对数范围检查，极高有限温度下不可表示的电流明确拒绝，
隧穿开关要求显式布尔值。[接触边界审计](../../docs/validation/schottky_numeric_20261016/README.md)
记录 567 项相关回归；有效势垒降低仍是校准代理，直接/非局域隧穿和真实材料参数
未认证。

带串联电阻的接触电流改为按单调电压方程求根，保持正反电流符号，二分至相邻
浮点端点或电压匹配；零偏压精确返回零，修复小正向电流因固定 100 次二分而变负。
[串联电阻审计](../../docs/validation/schottky_series_20261016/README.md)记录 108 项
新增独立 Decimal 检查、20 文件 915 项回归及明确的表示范围限制。

无串联电阻时合并势垒和外加能量计算完整热发射电流，去除指数 700 裁剪及饱和
电流的人为下限；Richardson 各因子分别取对数，避免中间乘积先溢出或下溢。
单独 Is 不可表示时，完整电流仍可能可表示，现可正确返回；真正舍入为零的
非零电流明确拒绝。[完整指数审计](../../docs/validation/schottky_exponential_20261016/README.md)
记录新增 82 项 800 位 Decimal 检查、21 文件 997 项相关回归。

串联电阻求根现直接使用 `log(Is)`，取消 Is 必须可表示的中间限制；同时保留
`nVT*I/Is` 的可表示电压贡献，次正规端口偏压按对数电压比较，避免残差舍入
平台。零与最小正数之间用真实半最小电流判断，包括高场输运分母；两个方向
均检查最大浮点电流能否包含根。[对数求根审计](../../docs/validation/schottky_log_series_20261016/README.md)
给出新增 125 项 1400 位 Decimal 参考、22 文件 1122 项相关回归及明确范围。
有效势垒降低与平滑窗口仍
为校准代理，完整舍入认证和真实材料标定未完成。

平滑 Schottky 能量窗口改用对数 sigmoid 权重和 log-sum-exp 组合，不再裁剪
窗口自变量到 ±700；无串联电阻时两支电流无需先导出即可得到可表示总电流。
窗口 `components()` 单独计算隧穿增量，避免总电流与热发射分量舍入为同值后
相减丢失增量；无电阻的小势垒变化直接使用有效势垒能差。
[窗口审计](../../docs/validation/schottky_window_20261016/README.md)给出新增 66 项
独立 Decimal 检查、23 文件 1188 项相关回归。

带电阻窗口现按两支电压方程之差直接求电流增量，避免相减独立根；结电压改用
二极管反关系，反向接近饱和时单独求结电压，避免减去接近的饱和电流。增量
体电压包含高场输运的两个分母。增强支根不可导出时仍可计算可表示的加权增量，
当时仍要求热发射基准根可导出。[串联窗口审计](../../docs/validation/schottky_series_window_20261016/README.md)
给出新增 80 项独立 180 位 Decimal 对照，24 文件 1268 项相关回归通过。
完整误差/舍入认证及真实隧穿路径
积分仍未完成。

非窗口及能量截止分支的 `components()` 也改为直接计算增量：无电阻用有效势垒
能差与 `expm1`，有电阻复用电压差方程，不再相减两个已舍入电流。截止分支与
总电流共享实际有效势垒，截止关闭或参数分辨率内没有势垒变化时增量严格为零。
非零增量导出下溢会明确报错，不能与真实零增量混淆。
[增量审计](../../docs/validation/schottky_increment_20261016/README.md)提供独立完整
分支反解、次正规导出和温度/理想因子检查：新增 169 项，25 文件 1437 项通过。
完整舍入认证及真实材料标定仍缺。

公共 Richardson 常数改用精确二进制整数比相乘、一次导出，恢复中间乘积溢出
但最终常数可表示的组合；确实溢出或非零下溢时明确拒绝。完整电流仍独立合并
所有因子，不要求常数单独导出。[Richardson 审计](../../docs/validation/schottky_richardson_20261016/README.md)
新增 90 项精确乘积、边界及物理电流对照，26 文件 1527 项相关回归通过。

串联窗口的次正规/下溢基准根现按连续对数幅值求解，保留实际结电压后组合
可表示的总电流；分量仍各自验证导出范围。正常高场根保留直接电流与输运
余量，避免对数往返放大舍入。[基准范围审计](../../docs/validation/schottky_window_base_range_20261016/README.md)
记录新增 52 项独立 800 位 Decimal 根、失败修正过程及剩余误差边界；
27 文件 1579 项相关回归通过。

接近高场输运上限时，注入增量现从完整电压方程独立求物理余量，避免已导出
电流相减的误差被小余量放大；该余量用于结电压、增益及两个高场分母。
[高场余量审计](../../docs/validation/schottky_highfield_gap_20261016/README.md)包含独立
完整电流反解、路径切换与严格上限导出检查：新增 109 项，28 文件 1688 项通过。
全域误差认证及真实材料标定仍缺。

WSe₂ 双窗口组合取消逐项暗加的 1e-300 下限，显式谷底仍保留；零耦合严格为
零，几何平均与耦合系数合并缩放后导出。限流按有界比值计算，拒绝非法输入，
保留既有禁用阈值。[WSe₂ 组合审计](../../docs/validation/wse2_current_composition_20261016/README.md)
覆盖独立分量、次正规总量、耦合溢出/下溢及总量接口。新增 90 项，相关回归
1784 项通过，包含六项既有 WSe₂ 代理检查；真实窗口标定仍缺。

WSe₂ 单窗口移除温度指数裁剪与漏压暗加下限，完整温度有理式避免倒数及能量
比值先溢出；温度、漏压与峰值合并后导出电流。单独非零因子超界明确拒绝，
零漏压的正幂取显式电流下限。[单窗口缩放审计](../../docs/validation/wse2_window_scaling_20261016/README.md)
新增 90 项独立 Decimal/范围检查，31 文件 1874 项通过，12 组实际旧版失真复核。
其栅权重尾部已由下列审计继续修复；该轮无新增 Sentaurus 运行。

WSe₂ 栅窗口的 Gaussian、sigmoid 尾部、skew 与 notch 保持对数权重至完整电流
导出；独立计算 `1-tail` 补量，避免尾部舍入为 1 后丢失可被大 lobe 放大的贡献。
坐标相减与 skew 符号用完整有理式，公开权重非零下溢明确拒绝。
[栅窗口审计](../../docs/validation/wse2_gate_window_20261016/README.md)新增 93 项独立
Decimal/范围检查，32 文件 1967 项通过，12 组实际旧版失真复核。该轮遗留的内部
对数超界由下列审计继续处理；该轮无新增 Sentaurus 运行。

WSe₂ 内部 float64 对数超界时使用标准库 Decimal 回退，保留大坐标及完整缩放，
最终按输出范围和显式下限验收，避免误拒绝 plateau、零驱动或可补偿电流。
[扩展范围审计](../../docs/validation/wse2_wide_window_20261016/README.md)新增 41 项
1900 位 mpmath/范围检查，修订 3 项既有拒绝检查，33 文件 2008 项通过，15 组
实际旧版问题复核。其有限巨大对数相消问题已由下列审计继续处理，扩展路径较慢。
本轮无新增 Sentaurus 运行，mpmath 仅加入开发依赖，生产使用标准库。

WSe₂ 大幅正负有限对数相消时重新计算完整公式，在导出电流或取显式下限前
触发；Decimal 回退的精度、舍入与异常陷阱隔离于调用方上下文。
[有限对数相消审计](../../docs/validation/wse2_log_cancellation_20261016/README.md)新增
31 项检查，覆盖 16 组实际失真、解析两倍峰值及 8 组上下文隔离；34 文件
2039 项通过，本轮无新增 Sentaurus 运行。
其中等幅度及峰值尺度相关的漏检由下列审计继续修复。

WSe₂ 相消按温度、漏压与栅权重的调制和检测，避免峰值尺度掩盖；有限对数
工作精度随幅度增长，notch 深度与 Gaussian 先组合后截断。
[自适应精度审计](../../docs/validation/wse2_adaptive_precision_20261016/README.md)新增
39 项检查及四组同机 API 前后耗时，覆盖 9 组实际失真和相邻公式/范围检查；
35 文件 2078 项通过，本轮无新增 Sentaurus 运行。
检测域外相消、全域误差、真实工作负载性能和材料标定仍缺。

WSe₂ 公开因子及完整电流在 float64 最大值与次正规边界重新计算，线性漏压比值
直接组合整数比，修复漏判溢出、非零下溢及中点舍入。
[导出边界审计](../../docs/validation/wse2_float_export_20261016/README.md)新增 80 项
检查，记录九组实际旧版错误，36 文件 **2158 passed，178.93 s**；高精度参考通过十进制
文本做一次 float 转换，避免参考自身的次正规二次舍入。本轮无新增 Sentaurus
运行；全域正确舍入、完整误差及真实材料标定仍未认证。

陷阱占据率用 `-expm1(-rate*dt)` 计算小时间步的衰减损失，避免指数接近 1 时的
相消丢失可表示占据增量。[陷阱更新审计](../../docs/validation/trap_expm1_20261016/README.md)
记录 Decimal 对照及 780 项相关回归；公开 float64 的不可表示边界和真实材料/寿命
参数标定仍未完成。

`tcad.core.native_precision()` 报告实际加载扩展的后端、有效尾数位和指数范围，
不读取运行时环境变量；Python 数组仍导出 float64。默认 quad 与实验性 long double
分别使用独立的对象/动态库缓存。[双后端审计](../../docs/validation/precision_backend_20261015/README.md)
保留此前 80 位负偏压 MOS 的失败；[守恒通量修复](../../docs/validation/continuity_chain_20261016/README.md)
采用单储库稳态一维 SG 通量累计和密度递推，保留实际源汇、核对组装残差，不支持的
配置回到通用求解器。最终 80 位专项 273 项及九个显式对数密度商业探测通过。
这不认证完整 80 位数值等价或缺失的界面注入/直接隧穿模型。

原生 `core.solve_equilibrium(max_iter=100, tolerance=1e-10)` 现在返回经典零费米
Poisson–Boltzmann 初值和实际 residual_history、update_history_V、damping_history。
只在未线性化方程残差和电势更新均满足条件时提交初值；失败/非法设置保留上次初值。
明确的 max_iter/status 避免旧实现首轮误报成功；无浓度下限或指数裁剪，不支持的
统计与储库关系会拒绝。这是电势初始化，不能代替耦合输运、量子或隧穿注入求解。
[模型、单位和独立/商业检查](../../docs/validation/equilibrium_initialization_20261015/README.md)。

`sentaurus_fn_to_native` 将显式 Sentaurus FowlerModel 的五个参数转换为高层
`Simulator.set_leakage` 的 kwargs，必须声明势垒和 Si→gate 相对原生轴的方向：

```python
from tcad.validation import sentaurus_fn_to_native
config = sentaurus_fn_to_native(
    dict(Aw=1.23e-6, Bw=2.37e8, Ae=1.87e-7, Be=1.88e8, Gm=1.),
    barrier_eV=3.15, semiconductor_to_gate_sign=1,
)
sim.set_leakage(**config, leak_mask_override=oxide_node_mask)
```

A 不变；V/cm→V/m 后 `B_native * barrier_eV**1.5 = 100*B_sentaurus`。
当 Si→gate 沿正轴时正场用 erase、负场用 write，方向为 -1 则交换。
桥接禁用 PF、场下限和电导率上限；拒绝缺字段、非法值、不可表示转换及 Gm≠1。
它仅对齐局部 FN 定律，不包含载流子界面注入、直接隧穿或非局域势垒积分。
新增真实 MOS 参考采用共同储库边界；直接隧穿对比预期失败，physical_validated
保持 False。[参数、14 条商业参考及界面修复证据](../../docs/validation/thin_oxide_fn_20261015/README.md)。

原生稳态可用 `sim.set_nonlinear_history_enabled(True)` 开启详细外迭代诊断，返回
`nonlinear_history` 分阶段列表。Gummel 的 relative_phi/n/p_update 是更新量，
poisson_relative_l2 是独立重组方程残差；final_poisson_residual 单列最终校正后的值。
Newton 分别导出原始三块范数、relative_block_max、scaled_merit_rms 和 equilibrated_linf。
默认关闭详细记录；同偏压重试、Gummel→Newton 阶段各自保留，零预算不伪造零残差。
开启/关闭已在三轴八类实际路径逐项核对解和收敛判定完全一致。

不默认把这些不同量拼成 iteration_residuals。调用者明确选一个阶段、一个字段后，
用 runner 适配 MonotoneConvergenceTest；其通过仅表示该序列满足单调约束，不能证明
收敛。[稳态接口与证据](../../docs/validation/nonlinear_history_20261015/README.md)。

同一开关现也记录原生瞬态尝试；求解后调用 `sim.get_transient_attempt_history()`。
每个 proposal group 保留实际区间、重试序号、接受判定和停止原因；粗步参考、第一/第二
半步或固定步长分别记录实际 Newton 范数。记录独立于物理回滚，只有 retained=True
的尝试贡献接受时间。未开启的误差分量与不可用估计返回 None，零迭代预算返回空数组。
三轴固定步长、经典自适应、LK 和 NLS 路径的全部物理快照开/关逐项一致。
记录仍不包含线性/线搜索内部过程、Gummel polish 全过程或 Python 延续累计调用。
[瞬态接口与证据](../../docs/validation/transient_attempt_history_20261015/README.md)。

`SensitivityTest` 和 `ParameterImportanceTest` 不再使用最大电势代理，也不再缺字段补零、
吞掉失败样本后返回成功。调用者必须声明 `field`、`response_scale` 和 `protocol`；缺配置
返回 unsupported 失败且不运行默认模型。field 是已经显式提取的有限实数标量，如某时刻
端口电荷或指定规则提取的 Vth，不能直接传一整条轨迹或让门禁猜测约简方式。

```python
from tcad.validation import SensitivityTest, ParameterImportanceTest

check = SensitivityTest(
    "rho", (.1, .3), num_points=5,
    field="P_end", response_scale=.01,  # C/m²，独立声明的响应尺度
    baseline={"alpha": 2e8, "beta": 3e12},
    protocol="40 nm 均匀 LK，零初始 P，同一脉冲，4 ns 读取 P [C/m²]",
    runner=extract_final_polarization,  # runner(sim) 返回下述测量记录
    tolerance=.2, min_response=1e-5,
)
result = check.run(build_fresh_lk_simulator)
# 测量记录示例：{"P_end": actual_P, "parameters": {"rho": actual_rho,
# "alpha": actual_alpha, "beta": actual_beta}, "time_s": 4e-9, "valid": True}
```

builder 接收全部变化/固定参数，必须每次新建实例；runner 默认 run()，可适配 solve()。
每次结果也必须独立，parameters 要记录与全部请求控制精确匹配的有限实数标量。提供的
valid/converged 必须为 True 布尔值；若提供 time_s，全部样本必须是同一非负标量时刻。
禁止用 times_s 搭配未约简轨迹。参数记录是调用方证据，门禁不能证明底层确实应用了参数，
所以 parameter_application_verified、physical_validated 和 reference_authenticity_validated
始终为 False。几何、预处理历史、观测单位、提取方法及其他固定条件由 protocol 声明。

SensitivityTest 至少需要三个均匀参数采样点；检查相邻差与二阶差除以 response_scale 的
绝对值是否各不超过 tolerance。两个检查开关独立生效，至少开启一个。尺度必须为与指标
相同单位的正标量，不使用输出均值、输出偏置或固定单位下限。全部常数响应为 inconclusive
失败；`min_response` 是相对于 response_scale 的非负响应检测下限，默认 0。实际响应范围
须严格超过该下限。通过只设置 numerical_sweep_validated，不证明连续性或导数精度；
稀疏网格可以漏过跳变，真实相变也可能触发失败，需另行分析和细化采样。

ParameterImportanceTest 必须提供包含全部待扫参数、且位于各自范围内的 baseline，可再
含其他固定控制。先独立运行基线，再逐参数做完整 one-at-a-time（OAT）扫描，其他参数
始终固定为基线值。任一样本失败立即中止，不输出有效的部分排名。分数为
`RMS((metric(sample)-metric(baseline))/response_scale)`，能处理负值、零基线与输出常数
偏置；一致换算指标单位及参数范围不改变分数。单个不敏感参数可为零分，全部响应未超过
检测下限则 inconclusive 失败。通过设置 ranking_validated，仅说明完整范围内的 OAT
筛选；不是 Sobol 指数、全局灵敏度、交互效应、统计显著性或因果识别。

框架两个 add_* 入口均支持上述显式配置。三轴原生制造解、五条新商业阻尼扫描与完整
证据见[灵敏度与重要性证据修复](../../docs/validation/sensitivity_evidence_20261015/README.md)。

`SymmetryTest` 需要明确 `protocol` 和 `relations`，缺条件返回 unsupported 失败，不运行
默认模型。relations 形如 `{"phi": ("phi", -1), "n": ("p", 1), "p": ("n", 1)}`，
表示将另一侧字段按声明的正负号变换后与本侧比较。映射必须自反，符号必须为整数 ±1。
不再默认所有器件在电压反转下电子/空穴互换；该条件需要材料、掺杂、接触和初态等支持。
通过仅设置 numerical_symmetry_validated，不能认证物理对称性、模型等价或参考真实性。

```python
from tcad.validation import SymmetryTest

check = SymmetryTest(
    "geometric", protocol="已声明坐标、材料和边界关于 x 中面镜像",
    relations={"phi": ("phi", 1), "Ex": ("Ex", -1)},
    axis=2,  # runner 返回 (nz, ny, nx) 数组，x 为最后一轴
    runner=extract_actual_spatial_fields,
    tolerance=1e-8, atol={"phi": 1e-12, "Ex": 1e-6},
)
result = check.run(build_fresh_simulator)
```

几何模式只运行一个实际模型，默认 run()，或由 runner(sim) 适配 solve() 及明确布局。
axis 必须提供，不能反射 times_s 所对应的首个时间轴；逐字段检查全部点位和奇数中心点。
可用 permutation 沿该轴替代索引倒序，要求长度精确一致、非平凡、双射且自反；坐标、
实际几何对称和矢量各分量奇偶性仍由调用者负责，接口不替调用者证明物理假设。
零维或反射轴只有一个点不能建立非平凡空间反射。多维数组不再直接返回零误差。

电压模式须 `runners={"positive": fn, "negative": fn}`，两侧使用独立实例和独立结果；
至少声明 phi→-phi，两侧实际控制元数据 bias_V 必须有限、同形状、精确反号且非全零。
仅在调用者明确声明 n↔p 时比较载流子互换；所选 n/p 还必须非负。不再猜测 set_bias。

铁电模式同样使用两个独立 runner，至少声明 P→-P；结果包含匹配的 voltage_V、times_s
和 P。波形必须有限、精确反号、非全零，至少两个采样点，时间从零严格增加且完全匹配。
初态必须在同一映射下比较；不能在同一实例连续扫描或把滞回时间序列倒序作为反向实验。
配对的 phi/P 响应若任一侧全零，结果为 inconclusive 失败。

所有模式共用 ReferenceComparisonTest 的逐字段预算 `atol + tolerance*peak(abs(reference))`，
拒绝缺字段、形状广播、非有限值、提供的失败状态及不一致时钟；无隐含 1e-10 单位下限。
容差为正的无量纲相对预算，atol 必须完整列出映射字段或全省略（各为零）。框架
add_symmetry_test 支持全部对应参数。4 次新商业运行及原生独立验证见
[对称性证据修复](../../docs/validation/symmetry_evidence_20261015/README.md)。

`BoundednessTest` 的启用条件现在必须有实际字段和明确界限。缺字段、非有限值、提供的
失败状态、点位形状不符均失败；不再推断 0–5 V、默认 Ps=1.4，或把无残差视为跳过成功。

```python
from tcad.validation.boundedness import BoundednessTest, PhysicalBoundsTest, MonotoneConvergenceTest

bounds = BoundednessTest(
    check_monotone_convergence=False,   # 场界限单独检查；残差需显式选择阶段/指标
    potential_bounds_V=(-1., 1.),
    polarization_limit_C_m2=.03,        # 调用者为当前方程/工况声明，非通用 Ps
    polarization_component_axis=-1,    # 原生 P.shape=(N,3)，核对向量模长
    tolerance=1e-8,
    atol={"phi": 1e-12},
    runner=lambda sim: sim.solve(),
)
result = bounds.run(build_fresh_simulator)
```

电势界限为有序的有限 (lower, upper) V 标量对，允许负偏压；极化上限为非负标量或与
标量 P/向量模长同形状的逐点数组，单位 C/m²。未指定 component_axis 时，P 被声明为有符号
标量场；指定时该轴必须长为 3。不得用数组广播拼接不同网格；所有启用的逐点字段在向量
约简后同形状。LK 的名义自发极化不构成任意外场下的通用硬上限。

兼容性变化：`tolerance` 现为无量纲的逐端点相对松弛；原先混用不同单位的绝对误差改用
`atol`，可指定已启用字段 n/p [m⁻³]、phi [V]、P [C/m²]，默认均为零。载流子非负条件
的零下限不使用相对松弛，只有显式 n/p 绝对预算才允许小负值。不能以大正密度掩盖另一
节点的极小负密度。所有检查关闭属于无效配置。

`check_monotone_convergence=True` 会执行实际 `iteration_residuals` 检查，需至少两个有限、
非负的一维值。`MonotoneConvergenceTest` 使用相同检查；相邻关系为
`r[i] <= r[i-1]*(1+tolerance) + residual_atol`，通过缩放计算避免极大/极小数误报。
默认调用 run()，可用 runner(sim) 显式提取历史；不会猜测 return_iterations 参数，也不会
从最终 residual 或迭代次数伪造历史。常数/零历史可以满足非增条件，但永远不设置
`convergence_validated` 或 `physical_validated`。原生分阶段历史须显式开启并选择字段，
未经适配时要求 iteration_residuals 仍会失败；若只检查场界限，应显式关闭单调性。

`PhysicalBoundsTest` 需真实同形状 n/p/Ex/Ey/Ez，执行 min/max_carrier_density 及完整向量场
模长检查。默认下限 1 m⁻³ 现在实际生效；绝缘体/零密度案例须显式选 min_carrier_density=0。
runner 同样支持 solve()。这些是声明的工况界限，不能证明材料有效域、最大值原理或击穿。
三个框架 add_* 入口均支持对应新参数，完整证据见
[有界性与残差修复](../../docs/validation/bounds_evidence_20261015/README.md)。

`LimitingCaseTest` 不再猜测设置接口或生成占位电流/阈值。四个已有条件测试须提供
`runners={"limit": runner, "reference": runner}` 及明确 `reference_source`；每次运行
使用新 simulator，结果包含实际字段与条件元数据。默认字段和条件如下：

| 条件 | 必须比较的字段 | 每侧必须记录的条件 |
| --- | --- | --- |
| no_ferroelectric | phi/n/p/P | ferroelectric_enabled 分别 True/False，ferroelectric_active_nodes=0，P 全零 |
| no_traps | phi/n/p | traps_enabled 分别 True/False，trap_density_m2_eV=0，oxide_trap_charge_C_m3 为同形状零电荷数组 |
| high_temperature | n/p | quantum_enabled 分别 True/False，两侧 temperature_K 相同且等于请求值 |
| thin_oxide | tunneling_current_A（标量，A） | 两侧 oxide_thickness_m、bias_V 与每档请求一致 |

前三类 runner 签名为 `runner(sim)`；薄氧化层为 `runner(sim, thickness_m)`，比较真实
电流与独立参考，拒绝常量/全零参考。`limit_params` 仅接受高温的 temperature_K
（默认 1000 K），或薄氧化层的 thicknesses_m（默认 5/2/1/0.5 nm）、bias_V（默认 1 V）。
rtol 由 tolerance 给定，atol 按字段明确提供；不硬编码 10% 或 1 µA 门槛。
无明确 runner 时返回 unsupported 失败。通过只表示声明条件下数值一致；参考来源
与开关元数据由调用者负责，接口不能认证它们。NLS/Preisach→LK 仍为未定义且直接失败。

底层 Poisson 陷阱占据率、Newton 残差及导数现使用配置的 VT，不再固定 300 K；
100/300/1000 K 的独立源项、非线性根及有限差分导数见
[极限证据与陷阱温度修复](../../docs/validation/limit_evidence_20261015/README.md)。
这使用全局热电压，并未实现空间温度变化的完整陷阱/电热模型。
通用 dense 求解另修复三对角结构误判、固定值行消元和尺度敏感主元替换；
独立矩阵、极端单位缩放及零 Thomas 主元回退也记录在同一报告。

网格验收现在必须显式提供 `reference(n, measured_result)`，返回同一采样位置的参考字段；
缺少参考或 builder 不支持 `nx/ny` 时失败。`runner(sim)` 可适配原生 `solve()`，
`spacing(n)` 声明实际网格间距；默认固定单位区域、`h=1/(n-1)`。
比较使用未加权节点 RMS 参考误差，每档误差须严格下降且每个相邻收敛阶均在范围内。
零误差无法辨识收敛阶，返回未通过并标记 inconclusive，不把浮点噪声当成二阶证据。
`TimeConvergenceTest` 要求至少三个严格减小的 dt，runner 返回相同终止时刻的快照
（`time_s=t_final`）；通过仅表示端点稳定。参数扫描通过仅表示扫描区间内的数值稳定性。
三类测试均要求新 simulator 和独立结果，不提供物理真实性或全程误差上界。
原生 Poisson 正弦源项、错误参考幅值和负向测试见
[收敛证据修复](../../docs/validation/convergence_evidence_20261015/README.md)。

字段比较现在拒绝缺字段、非有限实数、形状广播、失败状态和不匹配时钟；不会用零
替代缺失证据。`CrossValidationTest` / `ModelComparisonTest` 要求真实控制接口或
显式 `runners`，不能在缺少设置时比较两次默认求解。新增 `ReferenceComparisonTest`
及框架入口，以完整测量字段、明确来源和独立预算比较参考轨迹，缺失/损坏均失败；
已回放两组商业 P/Q/I 并验证独立损坏拒绝。见
[验证误报修复](../../docs/validation/validation_evidence_20261015/README.md)。

新增 `native_lk_to_sentaurus(alpha, beta, fe_gamma)` / `sentaurus_lk_to_native(parameters)`，
显式处理局部三次 LK 的 SI/厘米单位和 Landau 导数系数；原生 `fe_gamma` 对应商业
`rho`，而非商业六次项 `gamma`。缺失参数、非零梯度/六次项与非法数值均拒绝。
双阱反转/另一组凸自由能参数共 6 次真实 Sentaurus BE 瞬态，逐商业接受时间点对齐
极化、电极电荷和切换电流，并以独立连续 RK4 检查三档时间收敛；
数据与重放见 [Sentaurus LK 动态对齐](../../docs/validation/sentaurus_lk_dynamic_20261015/README.md)。
这是共享模型的数值验证，不是 NLS 等价关系或 AlScN/MoS₂ 材料标定。

[商业空间参考门禁](../../docs/validation/sentaurus_stack_spatial_audit_20261016/README.md)
新增 `audit_uniform_ferroelectric_reference()`：单点波形通过仍须检查明确提供的
FE 空间样本。4 个旧 TDR 状态及 6 次新 Sentaurus 运行揭示细网格和长读出
非均匀 P；旧 0.5 nm 长读出虽通过波形预算，现被空间门禁拒绝为均匀目标参考。
新 10 μm 宽的 1 nm 两档网格波形差异小于 1.315e-11，但改变了横向尺寸和
离散，不能替代原 100 nm 器件的拒绝结果。新增 47 项检查；单帧门禁不认证
完整轨迹、真实畴结构或材料标定，原生 quad 二进制保持不变。
主回归 31 文件 **1628 passed，328.72 s**；兼容性下溢守卫修正后，47 项相关
检查再次全部通过。

此前 [原生 LK 材料侧电场](../../docs/validation/lk_material_field_20261016/README.md)
在显式启用的 `set_transient_lk_material_field(True)` 模式下，修复无自由电荷
一维介质链的交替极化：每个节点独立求解，不强制均匀 P；原生 quad 核心重新编译。
复用 9 次已封存的实际 Sentaurus 数据，24 次原生重放共 7448 点，正式五组参考
四组在四档网格上通过，六项最大归一差异 1.32e-11。细商业网格和长读出超预算
差异继续拒绝。新增 66 项检查，覆盖非均匀材料／极化、三方向、90 位独立参考、
quad 微扰、端口、回滚和自适应；完整回归见报告。默认中心差分、含载流子和
多维 FE 仍未修复，完整物理认证仍为 false。
最终 30 个相关文件回归 **1581 passed，329.44 s**。

此前 [FE／氧化层串联堆栈](../../docs/validation/sentaurus_fe_oxide_stack_20261016/README.md)
新增 `tcad.physics.ferroelectric_stack.SeriesFerroelectricStack`，显式计算均匀 FE
与线性氧化层的电压分配、退极化反馈和指定端点的 BE 动态；不会替代原生空间求解器。
9 次新商业运行完成，5 组正式对照 **4 通过、1 拒绝**；细商业网格和长读出差异保留。
原生四档空间网格出现正负交替 P，新增 `audit_uniform_history()` 在声明的均匀目标下
拒绝该结果，空间离散本身仍待修复。新增 56 项检查，物理／空间认证均保持 false。
24 个相关文件回归 **1328 passed，319.24 s**；测试通过包含正确拒绝失败证据。

此前 [20 nm 高场协议对照](../../docs/validation/sentaurus_alscn_protocol_20261016/README.md)
共启动 7 次 Sentaurus 瞬态（5 次正式对照及短脉冲探索完成，严格自适应复算
另有 1 次超时并保留记录），使用 AlScN
材料库三次系数，逐同一 BE 网格比较 15 个候选幅值的复位/编程/零偏读出。
三档时间步、x/y 及自适应时钟共 32671 个样本，P/Q/I 最大峰值归一差异
2.48e-10；独立连续参考下自适应采样误差 0.426%，固定 25 ps 为 10.97%。
候选只形成两个极化簇；未验证完整 FeFET 或真实 15 电平。构建器现将未标定
擦除电压设为 None，候选数与已验证态数区分；新增显式连续协议生成器。
细步对照发现并修复 LK 汇总审计遗漏既有增量导出余量的问题，保留原始残差
及余量，并验证可分辨篡改仍拒绝。独立连续参考和源功步长变化单独记录。
新增 35 项检查，23 个相关文件回归 **1272 passed，318.94 s**。

此前 [自适应商业对齐](../../docs/validation/sentaurus_lk_adaptive_20261015/README.md)
补充 8 次 Sentaurus 运行，在 x/y、10/20/40 nm 下逐点复算原生接受半步，
含拒步回滚后的原始 P/Q/I 对照；三档局部预算使连续参考下最大 P 误差从 1.173% 降至
0.128%，但不提供全程误差上界。双向转换另拒绝扩展精度非零系数在 float64 接口下溢为零。

纯经典耦合瞬态可显式调用 `set_transient_electrical_error_control(True)`，
以电势绝对预算和双载流子绝对/相对预算联合验收粗 BE 步与两半步的差值。
该入口不要求铁电模型；FE/LK 控制与冻结方程须关闭。接受时仅返回两个物理半步，
超限则整组回滚、缩步重试；`audit_transient_electrical_error_control` 独立重算
稳定增量并检查配对时钟。三轴独立 Poisson/SG/BE、扩散精确解、连续波形和逐步账本
验证见[纯经典局部时间误差控制](../../docs/validation/classical_error_control_20261015/README.md)。
这仍不是全程误差上界或材料/多物理模型验收。

分裂 NLS 可独立调用 `set_transient_nls_error_control(True, rtol=1e-3, atol=1e-8)`，
联合约束 P/φ/n/p，使用粗步/两半步估计并整组回滚。P 绝对预算单位为 C/m²，
另可设置电势/双载流子预算和重试下限；其他控制器须关闭。
`audit_transient_nls_error_control` 共用经典控制器的严格时钟/分组检查，扩展到有符号 P
的形状、独立预算及稳定增量。三轴分层场反馈、活动载流子和连续 Merz/退极化 ODE
验证见 [NLS 局部误差控制](../../docs/validation/nls_error_control_20261015/README.md)。
该结果限定分裂 NLS 模型；未完成 NLS 联立、Preisach 自适应或完整能量闭合。

## 验证策略概览

```
        ┌─────────────────┐
        │  物理一致性验证  │  ← 对称性、守恒律、极限行为
        ├─────────────────┤
        │  数值方法验证    │  ← 收敛性、稳定性、精度
        ├─────────────────┤
        │  数学正确性验证  │  ← 单元测试、类型检查
        └─────────────────┘
```

## 目录结构

```
tcad/validation/
├── __init__.py              # 模块初始化
├── base.py                  # 基础类和工具函数
├── convergence.py           # 收敛性验证
├── conservation.py          # 守恒律验证
├── symmetry.py              # 对称性验证
├── limiting_cases.py        # 极限情况验证
├── boundedness.py           # 有界性和单调性验证
├── cross_validation.py      # 交叉验证
├── sensitivity.py           # 敏感性分析
├── report.py                # 验证报告生成
├── framework.py             # 验证框架主类
└── examples/
    └── example_usage.py     # 使用示例
```

## 验证策略详解

### 1. 收敛性验证 (`convergence.py`)

**网格收敛性测试** - 最重要的验证方法，不需要任何实验数据
- 验证数值解随网格加密收敛
- 计算收敛阶（二阶方法应为2.0）
- 检查误差单调递减

**时间步长收敛性测试**
- 验证瞬态模拟的时间步长收敛性
- 检查相邻时间步长结果的差异

**参数收敛性测试**
- 验证结果随参数变化的平滑性

### 2. 守恒律验证 (`conservation.py`)

**电荷守恒**
- 稳态：∇·J = 0（电流连续性）
- 瞬态：∂ρ/∂t + ∇·J = 0

`ConservationTest` 的稳态门禁检查所有接触的有符号电流之和。
结果须提供 `terminal_currents_A`（接触名到 A 的映射，正号表示流入器件），
或配置 `current_extractor(simulator, result)`。至少一个 `valid/converged`
布尔标记须为真，提供的任何失败标记均拒绝验收。缺少电流不再用 `n-p`
替代：掺杂或储存净电荷与电流守恒相容。该门禁检查整体 KCL，不代替
局部连续性残差或 Poisson 方程残差。

一维原生求解器可复用已有端口提取路径，并显式给出横截面积：

```python
from tcad.postprocess import terminal_currents_1d
from tcad.validation import ConservationTest

check = ConservationTest(
    check_energy=False,
    current_atol_A=1e-15,
    current_extractor=lambda sim, result: terminal_currents_1d(
        sim, result, cross_section_m2=1e-14),
)
verdict = check.run(device_builder)
```

`contact_current_1d` 返回 A/m²，乘以完整横截面积得到 A；新辅助函数仅接受
`ny=nz=1` 且两端有不重叠接触的网格。二维应使用对应截面积分，三维须完整
积分接触面积，不能把单条 cutline 当作端口电流。

`TransientConservationTest` 接受快照列表或包含 `snapshots` 的结果。
每个快照需要 `time_s`、有效性标记、`terminal_currents_A`，以及
`stored_charge_C` 或 `charge_density_C_per_m3` 和 `cell_volumes_m3`。
其判据为 `ΔQ = ∫ΣI_into dt`，允许正常充放电；时间严格递增且至少两点。
可选择 `integration="trapezoid"`（默认）或 `"backward_euler"`。
相对容差之外，`charge_atol_C` 指定以 C 计的绝对噪声预算。
快照的电流必须是输运账本内电荷的边界电流；位移电流与同一储存电荷不能
重复计入。调用者须提供包含所需自由电荷、陷阱电荷等的完整账本。
原生瞬态包含真实 `time_s/dt_s`、初态和失败状态。默认联立求解 Poisson 与
两种载流子的 BE 连续性方程；零时刻先按初始电荷求解电势，不推进载流子或 FE 历史。
自洽模式要求 Dirichlet 电势参考；经典模式可显式使用 `set_freeze_phi(True)`
进行固定电势输运实验。对一维或二维/三维完整接触平面、
载流子边界一致且每节点为双活动载流子或成对空阻断节点的情形，自动输出
`stored_charge_C` 与 `terminal_currents_A`：账本覆盖自由节点控制体积的
移动电荷，接触节点归属于外部电荷库。应使用 `integration="backward_euler"`。
账本排除接触电荷库之间的面通量；非单位 charge-volume fraction、部分接触平面、
没有自由节点或存在冻结载流子的情况不提供闭合账本。掺杂不会自动冻结多数载流子。
所有瞬态载流子方程使用完整节点体积，阻断面仅取消通量，保留存储／源项体积；
该几何与 LK 场策略独立。空阻断节点要求两种迁移率严格为零，密度相等、非负有限且
不超过数值下限、零生成并禁用 SRH，且至少有一个活动自由节点。
FE 已支持分裂极化更新与电学 Newton 反馈，拒绝同时请求固定电势；陷阱、量子、
热、BTBT 等尚未实现的瞬态模型组合明确报错。上述账本仅验证移动电荷连续性；
全耦合 FE、外部电路及完整陷阱/储能账本仍需实现。
自洽快照另提供 `D_x/D_y/D_z` 面通量和接受区间的 `Jdisp_x/Jdisp_y/Jdisp_z`，
其中 `D=εE+P` 使用与 Poisson 一致的面极化闭合。完整等电势外表面接触、
单位电荷体积分数与两侧一致面介电系数下，提供 `electrode_names`、
`electrode_charges_C` 和 `electrode_voltages_V`。匹配的活动载流子接触、空阻断混合网格或
纯介质可输出 `electrode_conduction_currents_A`、`electrode_displacement_currents_A`
与 `electrode_total_currents_A`；相应 `*_available` 标记明确可用范围。
活动行须有限非负生成与有限正寿命；空阻断行在接受区间两端都须零净电荷、零生成并禁用 SRH。
电极电荷/电流为流入自由控制体积的正方向；总电流应满足 Ampère 端口平衡，
不能将其替换移动电荷账本中的 `terminal_currents_A`。初态及失败步没有电流区间。
位移电流按 `ε_face*ΔE_face+ΔP_face` 计算，先求节点电势/极化增量再做面闭合，
避免较大的静态 D 掩盖小极化变化。另提供 `Jdielectric_x/y/z`、`Jpolarization_x/y/z`
及对应 `electrode_dielectric_currents_A`、`electrode_polarization_currents_A`。
`electrode_charge_increments_C` 保留接受区间的小电荷变化；在大静态电荷背景下，
不能用两个已转换到 float64 的 `electrode_charges_C` 相减替代它。
`tcad.postprocess.integrate_transient_terminal_history(history)` 按实际 BE 区间积分
电荷和带符号源做功，拒绝无效历史与时间/步长不一致；它不包含跨调用电压跳变的
冲激电荷，也不代表储能/耗散闭合或实验材料标定。
`current_kind` 可选择 `total`、`conduction`、`displacement`、`dielectric` 或
`polarization`；分量积分仍不能证明独立的热力学能量平衡。
外部 SI 时序的 `integrate_terminal_trace` 对分段线性电压、电流进行积分。
极端量级的乘法、过零分段和电荷求和按需使用精确有理数，直到最终导出再舍入；
避免中间溢出、下溢及极短时间权重的量化破坏可表示结果。无法表示的最终非零量
（包括平均源功率）明确拒绝。解析参考见
[端口积分量级审计](../../docs/validation/terminal_linear_range_20261014/README.md)。
`run_transient_pund` 新增一次连续原生预极化/P/U/N/D 驱动，要求有限上升/下降沿，
按“上升沿＋平台”窗口积分总 BE 端口电流。独立的
`extract_transient_pund_charge` 只接受准确落在已接受端点上的窗口，检查各电极
配对波形及窗口时长，拒绝失败历史、重叠窗口和电流范围不可用的数据。
接触必须完整覆盖单个边界面，返回具名接触到原生几何电极的映射；既有
`run_pund_sequence` 仍返回 FE 状态诊断。解析电容、NLS、欧姆导电与新增
Sentaurus 介电对照见 [原生 PUND 审计](../../docs/validation/transient_pund_20261014/README.md)。
P−U/N−D 配对积分不保证真实状态相关漏电抵消，`leakage_cancellation_validated`
保持 false。完整器件能量与真实材料校准仍须独立验收。
`audit_transient_pund_components` 逐接受区间、逐电极检查总电流=导电+位移、
位移=介电+极化，并分别积分配对窗口；`run_transient_pund(..., audit_components=True)`
可直接调用。`component_balance_validated` 仅表明导出电流的分解在容差内一致，
不代表热力学守恒或实验漏电扣除。移除导电及介电背景的量直接由对应原生分量
积分，避免从大总电荷相减丢失小极化信号。没有 FE 的载流子松弛也可产生非零
P−U/N−D，独立 Poisson/SG/BE 对照见
[PUND 分量审计](../../docs/validation/pund_components_20261015/README.md)。

瞬态历史还可通过 `audit_transient_energy_ledger` 组合原生介电储能、LK 局部账本和端口源做功，
并显式列出缺失的热、陷阱、量子、载流子耗散及 FE 梯度分量；该接口不会把分量一致性提升为完整器件能量闭合。
详见 [瞬态分量能量账本审计](../../docs/validation/energy_ledger_20261015/README.md)。
后续[失败处理与增量尺度修复](../../docs/validation/energy_ledger_guards_20261015/README.md)
统一缺少端口时的状态、接受时钟和储能增量检查；已声明可用的损坏源做功始终拒绝，
储能一致性残差与能量闭合残差分开，不能用大静态储能掩盖可分辨的小增量缺陷。
`set_transient_contact_waveforms(times_s, {name: voltages_V})` 现在支持一次连续
运行中的分段线性接触电压；时钟从零开始、覆盖请求终点，拐点自动截断时间步。
输入是实际施加的电压，保留接触内建电势；运行结束或异常后恢复配置的 DC 接触。
FE 在每步先按端点电压和上一接受态投影电势，再推进一次实际 dt 的分裂动力学。
固定电势与波形不能同时使用；不支持理想瞬时电压跳变。
原生积分采用端点电压乘本步 BE 电流；连续线性电容充放电的源做功有随 dt
收敛的端点积分误差，不能将这项误差称为耗散。独立解析与新 Sentaurus 脉冲参考
见 [连续电压波形审计](../../docs/validation/transient_voltage_waveforms_20261014/README.md)。
可显式选择 `voltage_quadrature="linear"`，用线性电压与本步恒定 BE 电流积分，
并在电压内部过零处分别累计吸收与回馈。这在已离散的线性电容中消除端点源做功误差，
不把非线性 FE/载流子电流变成精确时间积分。原生快照现在在限定范围下提供
`dielectric_energy_J` 和接受区间的 `dielectric_energy_increment_J`：
无 FE、无载流子输运、无光生、无掺杂、载流子净电荷为零、完整等电势接触平面，
并要求单位电荷分数及共享面 ε。储能由 FV/图边的 `0.5*ε*A/dx*(Δphi)^2` 独立计算，
仅覆盖至少一端为自由节点的边；不是端口源做功改名。
`audit_transient_dielectric_energy(history)` 检查每接受区间的线性电压源做功与
原生储能增量，增量按 quad 电势变化计算，不能用两个 float64 绝对储能相减替代。
通过时 `energy_balance_validated=True` 仅指这项无损、无自由电荷的线性模型。
耗散为该模型的显式零假设；`physical_validated=False`，不代表 FE/载流子/陷阱/热
能量账本闭合。FE 或超出范围、初态/失败增量、非有限和未表示的储能明确拒绝。
详见 [介电储能与积分审计](../../docs/validation/transient_dielectric_energy_20261014/README.md)。

LK 原生历史还提供实际驱动场、稳定 ΔP、Landau 自由能变化、γ 耗散和有符号 BE 修正。
`audit_transient_lk_energy(history)` 独立重算各项并检查逐节点/区间动力学恒等式。
通过只标记 `lk_kinetics_validated=True`，`energy_balance_validated=False`；
分步电势反馈后的最终电场不可替代更新时电场，BE 修正也不作为物理热量。
积分使用物理边界半宽的 FE 几何节点体积，区别于移动自由节点体积。
弱电场单调三次方程的虚假极化下限亦已修复。
详见 [LK 动力学能量审计](../../docs/validation/transient_lk_energy_20261014/README.md)。

`set_transient_lk_coupled(True)` 新增单调局部 LK 根消元的 Poisson/双载流子 BE Newton，
解析 `dP/dE` 进入面极化散度 Jacobian；每个试探场都由同一个已接受 P 推进一次实际 dt。
原生 `lk_coupled` 标记模式，耦合步的动力学驱动场必须与最终电场一致。
独立联立方程、标量载流子参考、多维矩阵极限和有限差分 Jacobian 通过。
非单调/多根步长明确拒绝；默认分步模式保留，仍需时间收敛及完整能量/材料验收。
详见 [LK 隐式耦合审计](../../docs/validation/transient_lk_coupled_20261014/README.md)。
可选 `set_transient_lk_substepping(True, safety=0.5)` 对负 α 限制实际步长至
`safety*gamma/abs(alpha)`，逐步联立求解并返回每个物理时间区间。
独立 RK4 验证弱反向场下的亚稳态保持、强反向场切换及时间步收敛，
还覆盖活动载流子、波形节点、失败回滚和浮点末步时间戳。
它提供唯一根的时间续接；不是误差自适应，也不验收非单调粗步多根或完整能量闭合。
详见 [LK 时间细分审计](../../docs/validation/transient_lk_substepping_20261014/README.md)。
`set_transient_lk_error_control(True, rtol=1e-3, atol=1e-6)` 增加可选局部极化
步加倍估计：粗步只作参考，通过后接受两次物理半步；超限/求解失败回滚整个
候选区间，再按重试预算和最小步长处理。atol 单位为 C/m²。
`audit_transient_lk_error_control(history)` 通过粗步 P 与稳定差值独立重算估计，
验收配对时间及元数据；通过也不声明全程误差上界、φ/载流子精度或完整能量闭合。
详见 [LK 局部误差控制审计](../../docs/validation/transient_lk_error_control_20261014/README.md)。
`set_transient_lk_electrical_error_control(True, phi_atol=1e-6,
carrier_rtol=1e-3, carrier_atol=1e10)` 为上述控制器增加 φ/n/p 预算，
φ 使用绝对 V 容差，载流子使用 m^-3 绝对容差加相对容差。
四种场共同决定接受/回滚，导出粗参考与原生稳定增量供
`audit_transient_lk_electrical_error_control` 独立重算。
三轴电中性扩散精确解揭示 P 估计近零时的载流子漏检，并验证收紧容差的轨迹趋势；
活动载流子另以独立 SG/Poisson/LK 方程逐粗步、半步检查。
适用范围限于显式耦合 LK 局部估计，全程误差上界、纯经典控制、完整能量及真实材料
标定仍未完成。详见 [联合电学误差控制](../../docs/validation/transient_electrical_error_20261015/README.md)。
LK 候选半步还需通过 float64 估计导出检查，原生及导出范数同时满足验收阈值；
不可导出的增量回滚并返回未提交失败，次正规数审计计入明确的向量舍入余量。
详见 [LK 估计导出与来源审计](../../docs/validation/transient_lk_estimate_export_20261014/README.md)。

连续电压波形先检查活动拐点及实际截断终点，非法未来电压在物理推进前拒绝。
绝对端点插值消除大 DC 与反向偏移产生的伪电压；失败后重试保留已准备的 FE 状态。
详见 [波形预检查与相消审计](../../docs/validation/transient_waveform_preflight_20261014/README.md)。
报告记录实际快照起止时间，验证仅覆盖该时间段，不承诺达到请求的 `t_final`。

**能量守恒**
- 输入能量 = 存储能量 + 耗散能量

以 J 计提供 `energy_initial`、`energy_final`，可选 `energy_supplied` 和
`energy_dissipated`；检查 `初始 + 外部供能 = 最终 + 耗散`。缺少可选项表示
零，提供 NaN 等无效可选项则失败。稳态结果没有能量账本时，应关闭能量
检查或补齐实际账本，不应以占位零值取得通过。

**熵产生**
- 热力学第二定律：熵产生 ≥ 0

### 3. 对称性验证 (`symmetry.py`)

**电压反转对称性**
- V和-V应该给出镜像结果

**几何对称性**
- 对称结构应该给出对称结果

**铁电极化对称性**
- 无内建场时P-V曲线应该对称

### 4. 极限情况验证 (`limiting_cases.py`)

验证在极限情况下模型是否退化为已知模型：
- `no_ferroelectric`: 无铁电层退化为MOSFET
- `high_temperature`: 高温极限退化为经典模型
- `thin_oxide`: 超薄氧化层极限
- `nls_to_lk` / `preisach_to_lk`：保留旧入口，但无已定义方程极限/参数映射，返回
  `passed=False, unsupported=True`；参考轨迹一致性应使用显式参考比较，不能据此声明本构等价。
- `no_traps`: 无陷阱退化为理想器件

### 5. 有界性和单调性验证 (`boundedness.py`)

**物理边界条件**
- 载流子浓度为正
- 电势在合理范围内
- 铁电极化不超过Ps

**单调收敛**
- Newton迭代残差单调递减

### 6. 交叉验证 (`cross_validation.py`)

不同数值方法的交叉验证：
- 有限差分 vs 有限元
- 显式 vs 隐式时间积分
- 不同线性求解器

### 7. 敏感性分析 (`sensitivity.py`)

**参数敏感性**
- 结果应该随参数平滑变化
- 不应该出现突然的跳变（除相变外）

**参数重要性**
- 识别关键参数

## 使用方法

### 基本使用

```python
from tcad.validation import ValidationFramework

# 定义设备构建函数
def device_builder(nx=40, ny=40, **kwargs):
    from tcad.simulator import Simulator
    from tcad.geometry import Device
    
    device = Device.mosfet(Lg=50e-9, tox=2e-9, tsi=10e-9, W=100e-9)
    sim = Simulator(device, nx=nx, ny=ny)
    
    # 设置物理参数
    if 'Ps' in kwargs:
        sim.set_ferroelectric(model='NLS', Ps=kwargs['Ps'])
    
    return sim

# 创建验证框架
framework = ValidationFramework(device_builder, name="NLS铁电模型验证")

# 添加测试
framework.add_grid_convergence_test(mesh_sizes=[20, 40, 80])
framework.add_conservation_test()
framework.add_boundedness_test()

# 运行测试
results = framework.run_all()

# 打印报告
framework.print_report()

# 保存报告
framework.save_report('validation_report.txt')
```

### 使用预定义测试套件

```python
from tcad.validation import create_validation_framework

# 创建标准验证框架
framework = create_validation_framework(
    device_builder,
    name="标准验证",
    test_suite='standard'  # 'basic', 'standard', 'comprehensive'
)

# 运行测试
framework.run_all()
framework.print_report()
```

### 自定义验证测试

```python
from tcad.validation.base import BaseValidationTest, ValidationResult

class CustomPhysicsTest(BaseValidationTest):
    def __init__(self):
        super().__init__("Custom Physics Test")
    
    def run(self, device_builder):
        try:
            sim = device_builder()
            result = sim.run()
            
            # 自定义验证逻辑
            phi = getattr(result, 'phi', np.zeros(1))
            condition_satisfied = True  # 你的验证条件
            
            return ValidationResult(
                self.name,
                condition_satisfied,
                "验证通过" if condition_satisfied else "验证失败"
            )
        except Exception as e:
            return ValidationResult(self.name, False, f"测试失败: {str(e)}")

# 使用自定义测试
framework = ValidationFramework(device_builder)
framework.add_test(CustomPhysicsTest())
framework.run_all()
```

## 验证流程建议

### 新物理效应开发流程

1. **数学正确性验证**
   - 单元测试
   - 类型检查
   - 矩阵对称性

2. **数值方法验证**
   - 网格收敛性测试（最重要！）
   - 时间步长收敛性测试
   - 参数收敛性测试

3. **物理一致性验证**
   - 守恒律验证
   - 对称性验证
   - 极限情况验证

4. **有界性和单调性验证**
   - 物理边界条件
   - 单调收敛

5. **交叉验证**
   - 不同数值方法对比
   - 不同模型对比

6. **敏感性分析**
   - 参数敏感性
   - 参数重要性

### 验证检查清单

- [ ] 网格收敛性测试通过
- [ ] 时间步长收敛性测试通过（瞬态问题）
- [ ] 电荷守恒满足
- [ ] 能量守恒满足（如适用）
- [ ] 对称性验证通过
- [ ] 极限情况退化为已知模型
- [ ] 载流子浓度为正
- [ ] 电势在合理范围内
- [ ] 收敛过程单调
- [ ] 交叉验证通过

## 示例

查看 `examples/example_usage.py` 获取完整示例：

```bash
python -m tcad.validation.examples.example_usage
```

## 报告格式

验证报告包含：
- 测试结果汇总（通过/失败数量）
- 详细测试结果（每个测试的状态、消息、详细信息）
- 失败测试列表
- 建议

## 最佳实践

1. **优先使用网格收敛性测试** - 这是最可靠的验证方法
2. **始终验证守恒律** - 这是物理定律的基石
3. **检查极限情况** - 新模型应该退化为已知模型
4. **验证对称性** - 物理系统通常具有对称性
5. **检查有界性** - 物理解应该在合理范围内
6. **使用交叉验证** - 不同方法应该给出一致结果

## 故障排除

### 测试失败

1. 检查失败测试的详细信息
2. 修复代码中的问题
3. 重新运行验证测试

### 收敛性问题

1. 检查网格质量
2. 调整时间步长
3. 检查物理参数是否合理

### 守恒律违反

1. 检查边界条件
2. 检查数值格式
3. 增加网格密度

## 参考资料

- 收敛性分析：Numerical Recipes in C
- 守恒律验证：Finite Volume Methods for Hyperbolic Problems
- 对称性验证：Group Theory and Physics

## 许可证

MIT License
