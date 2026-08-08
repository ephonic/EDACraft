# TCADCraft 0.2.0 发布说明

发布日期：2026-08-08

TCADCraft 0.2.0 是首个以 Sentaurus W-2024.09 标定门禁为核心的发布版本。
本版本重点闭环量子修正、Newton/Gummel 耦合稳定性、接触与隧穿、可靠性，
以及雪崩击穿和自热仿真。

## 发布门禁

- HfO2 铁电主回线：通过。
- Si 陷阱 stress/recovery：通过。
- GaN Schottky + 非局域隧穿：通过。
- 8 nm 双栅 MOS 密度梯度量子修正：通过。
- 电热雪崩击穿：通过；热失控外电压误差 3.72%，峰值温度误差
  0.193%，端电流 KCL 相对散度 6.10e-9。
- 核心数值回归快照：79 passed，1 skipped。
- 干净环境构建/安装快速门禁：42 passed（24.65 s）。

## 重要行为变化

Newton-primary 模式不再继承跳过的 Gummel 预热结果；Newton 收敛后也不再
执行会破坏载流子一致性的 Poisson-only 重解。Auger 及其解析 Jacobian 已进入
全耦合 Newton，非收敛安全钳位、KCL 判据、延续步长和热终止点细化也已加固。

## 已知边界

本版本可用于已通过门禁的参考器件与相邻参数空间，但不能把 Sentaurus synthetic
golden 当作材料实验真值。3/5/8/10 nm 量子厚度族仍为 partial_not_passed；IGZO、
WSe2 仍需实验/文献/第一性原理约束材料参数。电热击穿当前以 0.07 标定缩放等效
缺失的原生高场速度饱和模型，加入该模型后必须重新标定。

## 构建与验证

```bash
TCAD_USE_PETSC=0 TCAD_USE_LAPACK=0 python setup.py build_ext --inplace
python scripts/release_check.py --calibration-root ../..
python -m pytest -q
```

本版本仅发布 `EDACraft/TCADCraft/` 中的代码，不附带 tar.gz 或 wheel。默认构建
采用内部直接求解器，不依赖系统 LAPACK/BLAS，从而避免与 SciPy 自带线性代数库
发生符号冲突。经过平台级验证后，源码构建可显式设置
`TCAD_USE_LAPACK=1` 启用系统 LAPACK 加速。

支持 GCC/Clang 的 Linux 和 macOS 源码构建；原生 Windows/MSVC 不支持，Windows
用户应使用 WSL2。
