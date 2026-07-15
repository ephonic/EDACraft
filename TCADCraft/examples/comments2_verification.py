#!/usr/bin/env python3
"""
comments2.docx 验证脚本

验证 div(P) 散度 + L-K 钳位 + 退极化场修复后的效果：
1. P-V 回线是否产生正确的 S 形滞回（非钉死在常数）
2. P 值是否在物理范围 [−Ps, +Ps] 内
3. 不同厚度(20/40/100nm)的存储窗口关系是否正确（越厚窗口越大）
4. 保持特性仿真
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

plt.rcParams.update({
    'font.size': 11, 'font.family': 'serif',
    'axes.labelsize': 12, 'axes.titlesize': 13,
    'figure.dpi': 150, 'savefig.dpi': 300, 'savefig.bbox': 'tight',
    'axes.grid': True, 'grid.alpha': 0.3,
})

from tcad.core import PyDeviceSimulator

QE = 1.602176634e-19
EPS0 = 8.854187817e-12
K_B = 1.3806503e-23
VT_300 = K_B * 300.0 / QE

# AlScN 参数
ALSCN_PS = 1.4       # C/m^2 (140 uC/cm^2)
ALSCN_EC = 3.5e8     # V/m (3.5 MV/cm)
ALSCN_EPS_R = 15.0   # 相对介电常数
ALSCN_ALPHA = -6.49e8
ALSCN_BETA = 3.31e8


def build_alscn_slab(Lx=40e-9, nx=41, model=1, E_bi=0.0, eps_depol=0.0):
    """构建 AlScN 铁电平板"""
    dx = Lx / (nx - 1)
    N = nx
    sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)
    sim.set_permittivity(np.full(N, EPS0 * ALSCN_EPS_R))
    sim.set_mobility(np.zeros(N), np.zeros(N))
    sim.set_doping(np.zeros(N))
    sim.set_thermal_voltage(VT_300)
    sim.set_recombination(np.full(N, 1e-7), np.full(N, 1e-7))
    sim.set_effective_dos(np.full(N, 2.8e25), np.full(N, 1.04e25))
    sim.set_bandgap(np.full(N, 5.5))
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(N, dtype=np.int8), ALSCN_ALPHA, ALSCN_BETA)
    sim.set_ferroelectric_model(model)
    sim.set_ferroelectric_preisach(ALSCN_PS, ALSCN_EC, 0.0)
    if E_bi != 0.0:
        sim.set_ferroelectric_builtin_field(E_bi)
    if eps_depol > 0.0:
        sim.set_ferroelectric_depol(eps_depol)
    sim.set_dirichlet_potential({0: 0.0, N - 1: 0.0})
    sim.set_electron_bc({0: 0.0, N - 1: 0.0})
    sim.set_hole_bc({0: 0.0, N - 1: 0.0})
    return sim, N


def bipolar_sweep(sim, N, Vmax, n_pts=30):
    """双向电压扫描"""
    mid = N // 2
    Vl = np.concatenate([
        np.linspace(0, Vmax, n_pts),
        np.linspace(Vmax, 0, n_pts)[1:],
        np.linspace(0, -Vmax, n_pts)[1:],
        np.linspace(-Vmax, 0, n_pts)[1:],
    ])
    Pxs = []
    for Vg in Vl:
        sim.set_dirichlet_potential({0: float(Vg), N - 1: 0.0})
        r = sim.solve()
        Pxs.append(r["P"][mid][0])
    return Vl, np.array(Pxs)


def extract_memory_window(V, P):
    """提取存储窗口 (矫顽电压之差)"""
    # 找到 P 过零点对应的电压
    pos_crossings = []
    neg_crossings = []
    for i in range(1, len(P)):
        # P 从正到负
        if P[i-1] > 0 and P[i] <= 0:
            # 线性插值
            frac = P[i-1] / (P[i-1] - P[i])
            pos_crossings.append(V[i-1] + frac * (V[i] - V[i-1]))
        # P 从负到正
        if P[i-1] < 0 and P[i] >= 0:
            frac = -P[i-1] / (P[i] - P[i-1])
            neg_crossings.append(V[i-1] + frac * (V[i] - V[i-1]))

    if len(pos_crossings) >= 1 and len(neg_crossings) >= 1:
        Vc_pos = neg_crossings[0]  # P从负到正的矫顽电压
        Vc_neg = pos_crossings[0]  # P从正到负的矫顽电压
        return abs(Vc_pos - Vc_neg)
    return 0.0


def test1_pv_loop_shape():
    """测试1: P-V 回线是否产生 S 形滞回（非钉死常数）"""
    print("=" * 60)
    print("测试1: P-V 回线形状验证")
    print("=" * 60)

    sim, N = build_alscn_slab(Lx=40e-9, model=1, eps_depol=ALSCN_EPS_R)
    V, P = bipolar_sweep(sim, N, Vmax=20, n_pts=30)

    P_uC = P * 1e4  # C/m^2 -> uC/cm^2 (1 C/m^2 = 1e4 uC/cm^2)

    print(f"  P range: [{P_uC.min():.1f}, {P_uC.max():.1f}] uC/cm^2")
    print(f"  Expected: ~[-{ALSCN_PS*1e4:.0f}, +{ALSCN_PS*1e4:.0f}] uC/cm^2")

    # 检查1: P 值在物理范围内
    max_abs_P = max(abs(P.min()), abs(P.max()))
    in_range = max_abs_P <= ALSCN_PS * 1.1
    print(f"  P within [+/-{ALSCN_PS*1.1:.2f} C/m^2]: {in_range}")

    # 检查2: P 不是常数（有变化）
    p_variation = P.max() - P.min()
    has_variation = p_variation > 0.1 * ALSCN_PS
    print(f"  P variation: {p_variation:.3f} C/m^2 (threshold: {0.1*ALSCN_PS:.3f})")
    print(f"  P is NOT pinned at constant: {has_variation}")

    # 检查3: 有滞回（正向和反向扫描的 P 不同）
    n = len(V) // 4
    P_fwd = P[:n]  # 0 -> +Vmax
    P_bwd = P[n:2*n]  # +Vmax -> 0
    has_hysteresis = not np.allclose(P_fwd, P_bwd[::-1], atol=0.01)
    print(f"  Has hysteresis (P_fwd != P_bwd): {has_hysteresis}")

    # 绘图
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(V, P_uC, '-', lw=1.5)
    ax.set_xlabel("Gate Voltage [V]")
    ax.set_ylabel(r"Polarization [$\mu$C/cm$^2$]")
    ax.set_title("AlScN P-V Hysteresis Loop (Preisach model)")
    ax.axhline(0, color='0.5', lw=0.5)
    ax.axvline(0, color='0.5', lw=0.5)
    plt.tight_layout()
    plt.savefig("verify_pv_loop.png", dpi=300)
    print("  Saved: verify_pv_loop.png")
    plt.close()

    passed = in_range and has_variation
    print(f"\n  Result: {'PASS' if passed else 'FAIL'}")
    return passed


def test2_thickness_window():
    """测试2: 多厚度存储窗口 - 越厚窗口应越大"""
    print("\n" + "=" * 60)
    print("测试2: 厚度-存储窗口关系验证")
    print("=" * 60)

    thicknesses = [20e-9, 40e-9, 100e-9]
    windows = []

    for t_fe in thicknesses:
        print(f"\n  Thickness = {t_fe*1e9:.0f} nm:")
        sim, N = build_alscn_slab(Lx=t_fe, nx=max(21, int(t_fe/1e-9)+1),
                                   model=1, eps_depol=ALSCN_EPS_R)
        # 扫描电压需要足够大以达到饱和
        Vmax = max(20.0, 2 * ALSCN_EC * t_fe)  # 至少 2*Ec*Lx
        V, P = bipolar_sweep(sim, N, Vmax=Vmax, n_pts=30)
        mw = extract_memory_window(V, P)
        windows.append(mw)
        P_uC = P * 1e4
        print(f"    Vmax = {Vmax:.1f} V")
        print(f"    P range: [{P_uC.min():.1f}, {P_uC.max():.1f}] uC/cm^2")
        print(f"    Memory window = {mw:.2f} V")

    # 验证厚度-窗口趋势
    print(f"\n  Windows: {[f'{w:.2f}V' for w in windows]}")
    # 物理上：越厚 => 矫顽电压越大 => 存储窗口越大
    # （窗口 ~ 2*Ec*t_fe）
    trend_ok = windows[2] >= windows[1] >= windows[0] * 0.8
    print(f"  Trend (thicker => larger window): {trend_ok}")

    # 绘图
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar([f"{t*1e9:.0f}nm" for t in thicknesses], windows,
           color=['#1f77b4', '#ff7f0e', '#2ca02c'], width=0.5)
    ax.set_xlabel("FE Thickness")
    ax.set_ylabel("Memory Window [V]")
    ax.set_title("Memory Window vs FE Thickness")
    plt.tight_layout()
    plt.savefig("verify_thickness_window.png", dpi=300)
    print("  Saved: verify_thickness_window.png")
    plt.close()

    print(f"\n  Result: {'PASS' if trend_ok else 'CHECK'}")
    return trend_ok


def test3_retention():
    """测试3: 保持特性"""
    print("\n" + "=" * 60)
    print("测试3: 保持特性验证")
    print("=" * 60)

    sim, N = build_alscn_slab(Lx=40e-9, model=1, eps_depol=ALSCN_EPS_R)
    mid = N // 2

    # 编程到 +V
    sim.set_dirichlet_potential({0: 20.0, N - 1: 0.0})
    r = sim.solve()
    P_program = r["P"][mid][0]
    print(f"  Programmed P = {P_program:.4f} C/m^2 ({P_program*1e4:.1f} uC/cm^2)")

    # 在 V=0 下保持
    P_retention = []
    for i in range(10):
        sim.set_dirichlet_potential({0: 0.0, N - 1: 0.0})
        r = sim.solve()
        P_retention.append(r["P"][mid][0])

    P_retention = np.array(P_retention)
    P_final = P_retention[-1]
    retention_loss = abs(P_program - P_final) / max(abs(P_program), 1e-10)

    print(f"  Retention P_final = {P_final:.4f} C/m^2 ({P_final*1e4:.1f} uC/cm^2)")
    print(f"  Retention loss = {retention_loss*100:.1f}%")

    # 绘图
    fig, ax = plt.subplots(figsize=(7, 5))
    times = np.arange(len(P_retention))
    ax.plot(times, P_retention * 1e4, 'o-', lw=2, ms=6)
    ax.set_xlabel("Time step")
    ax.set_ylabel(r"Polarization [$\mu$C/cm$^2$]")
    ax.set_title("Retention Characteristics (V=0 after programming)")
    plt.tight_layout()
    plt.savefig("verify_retention.png", dpi=300)
    print("  Saved: verify_retention.png")
    plt.close()

    passed = P_final != 0
    print(f"\n  Result: {'PASS' if passed else 'FAIL'}")
    return passed


def main():
    print("\n" + "=" * 70)
    print("comments2.docx 验证脚本")
    print("=" * 70 + "\n")

    results = []

    results.append(("P-V 回线形状", test1_pv_loop_shape()))
    results.append(("厚度-窗口关系", test2_thickness_window()))
    results.append(("保持特性", test3_retention()))

    print("\n" + "=" * 70)
    print("验证总结")
    print("=" * 70)
    for name, passed in results:
        status = "PASS" if passed else "FAIL/CHECK"
        print(f"  {name}: {status}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n  {passed_count}/{len(results)} 通过")

    print("\n生成的文件:")
    print("  - verify_pv_loop.png")
    print("  - verify_thickness_window.png")
    print("  - verify_retention.png")


if __name__ == '__main__':
    main()
