"""端到端示例：ε=1 微带线 MoM 扫频 → Touchstone .s2p 输出。

展示完整管线：
  1. 配置微带线几何（长度、宽度、介质）。
  2. 扫频（0.5–10 GHz）逐点 MoM 求解。
  3. Schur 2-端口提取 S 参数。
  4. 写入 Touchstone .s2p（RI 格式）。
  5. 读回验证（round-trip）。
"""
import numpy as np

import mom


def main():
    # ε=1 微带线（自由空间等效，验证物理正确）
    ms = mom.Microstrip(
        length=20e-3,      # 20 mm
        width=3e-3,        # 3 mm
        height=1.6e-3,     # 1.6 mm
        eps_eff=1.0,       # 有效介电常数
        nx=40,             # x 方向分段
        gauss=4,           # Gauss 积分阶
        z0_ref=50.0,       # 端口参考阻抗
    )

    # 扫频
    freqs = np.linspace(0.5e9, 10e9, 20)
    print(f"微带线: L={ms.length*1e3}mm W={ms.width*1e3}mm h={ms.height*1e3}mm")
    print(f"扫频: {freqs[0]/1e9:.1f}–{freqs[-1]/1e9:.1f} GHz, {len(freqs)} 点")
    print()

    # 写 Touchstone
    path = ms.to_touchstone(
        "demo_microstrip.s2p", freqs,
        freq_unit="GHz", fmt="RI",
        comments=["eps=1 microstrip MoM demo", "Schur 2-port S-param extraction"],
    )
    print(f"Touchstone 写入: {path}")

    # 读回验证
    fr, S, z0 = mom.read_touchstone(path)
    print(f"读回: {len(fr)} 频点, z0={z0}Ω, S shape={S.shape}")

    # 互易性 & 能量守恒
    recip = np.max(np.abs(S[:, 0, 1] - S[:, 1, 0]))
    conserve = np.abs(S[:, 0, 0])**2 + np.abs(S[:, 1, 0])**2
    print(f"\n验证:")
    print(f"  互易性 |S12-S21| max = {recip:.2e}（应≈0）")
    print(f"  能量守恒 |S11|²+|S21|² 范围 = {conserve.min():.3f}–{conserve.max():.3f}")
    print(f"    （<1 因 ε=1 微带辐射损耗，物理正确）")

    # 关键频点
    print(f"\n关键频点:")
    print(f"  {'f(GHz)':>7} {'|S11|':>7} {'|S21|':>7} {'守恒':>6}")
    for idx in [0, len(fr)//2, -1]:
        f = fr[idx] if idx >= 0 else fr[-1]
        s11 = abs(S[idx, 0, 0]); s21 = abs(S[idx, 1, 0])
        print(f"  {f/1e9:7.2f} {s11:7.3f} {s21:7.3f} {s11**2+s21**2:6.3f}")


if __name__ == "__main__":
    main()
