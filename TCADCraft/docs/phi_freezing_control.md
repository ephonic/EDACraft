# Gummel 电势冻结开关

C++ `DeviceSimulator::set_phi_freezing_enabled(bool)` 控制 Gummel 的周期均值接受及电势冻结回退，默认开启。关闭后，每轮仍正常求解 Poisson 和载流子连续性方程；混合 Gummel/Newton 路由仍可检测周期并交给 Newton。Newton 的 `set_newton_freeze_phi` 是独立设置。

```cpp
sim.set_use_newton(false);
sim.set_phi_freezing_enabled(false);
const auto result = sim.solve();
```

设置保存在模拟器中，在每次重建 Gummel 求解器时传入；后一次设置覆盖前一次。`result.phi_frozen` 报告实际是否采用冻结／周期均值路径。开启开关仅允许该路径，不要求每次求解都冻结。

关闭开关不改变残差门限，也不保证收敛。调用方应检查 `converged`、非线性历史和方程残差。本项修复通过本地 C++ 检查；没有新增 Python 绑定方法。改动需重新构建核心及依赖它的扩展，不能直接复用旧二进制。

回归入口为 `tests/cpp/test_phi_freezing_control.cpp`，覆盖默认开启、显式开启／关闭和两种开关切换顺序。详细证据见 `docs/validation/phi_freezing_control_20261030/ACCEPTANCE.md`；完整 0.2 V 冷启动矩阵仍存在 Newton 停滞，未授予完整资格。
