# 经典高场饱和电流与Newton KCL一致性

当经典HFS开启时，Newton连续性方程使用饱和迁移率。稳态x轴KCL检查也必须按相同迁移率计算SG电流；使用未饱和电流会将已满足方程的稳态解判为不守恒，导致Newton在精度极限处反复拒绝。

本修复在现有x轴KCL计算中补齐ElectricField和GradQuasiFermi两种驱动力的电子/空穴饱和迁移率，使用原有DOS和密度下限、速度和指数。保持原绝对电流散度1e-8 A/m²或相对散度1%的门限，保持Newton残差、步边界、搜索和Gummel行为。量子模型及其他既有作用域不扩展。

`tests/cpp/test_hfs_kcl_consistency.cpp`以48份已独立审计的构造MB稳态解为相同暖启动种子，覆盖17/33节点、两种pn方向、正负0.05V、constant/Arora及HFS关闭/ElectricField/GradQuasiFermi。修复前32份被原生错误拒绝，修复后48份全部通过原1e-19要求；HFS关闭的16份全部字段及迭代历史与修复前相同。四项独立Poisson一致性回归通过。

这些是暖启动回归，不能代表冷启动、真实材料标定或商业完整器件对标。固定材料量纲搜索方案尚有正0.2V/Arora/GQF冷启动失败，未进入产品。源数据和完整前后日志见316证据 (`validation/hfs_kcl_consistency_20261030/ACCEPTANCE.md`; historical archive, not bundled)；本轮不更新远端候选或生产二进制。

CTest入口为`hfs_kcl_consistency`，使用`tests/data/hfs_kcl_seeds.dat`。本地已直接用Cygwin GCC15.2编译测试所用完整核心；没有运行CMake配置、Python扩展或Linux ABI验收。
