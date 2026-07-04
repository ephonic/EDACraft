"""任意导体（RWG 网格）示例：mom.Structure API。

本例用 mom.Structure 在矩形带导体上提取 2 端口 S 参数，并写 Touchstone .s2p。
Structure 基于：三角网格 + RWG 基函数 + 并矢格林函数 + Schur N 端口降阶，
支持任意平面 / 三维导体（含过孔、垂直电流）。

运行：python examples/run_structure_demo.py
（需先 pip install -e . 编译 _mom 扩展）
"""
import numpy as np

import mom


def main():
    # 1) 定义几何与介质
    conductor = mom.RectangleConductor(
        x0=0.0, x1=0.02,         # 20 mm 长
        y0=-0.0015, y1=0.0015,   # 3 mm 宽
        z=0.0016,
    )
    medium = mom.Stackup(eps_r=4.3, h=1.6e-3)

    # 2) 构造 Structure（RWG 网格）
    s = mom.Structure(
        conductor=conductor,
        medium=medium,
        nx=8, ny=2,
        z0_ref=50.0,
    )
    print(f"导体: L={conductor.length*1e3:.2f}mm W={conductor.width*1e3:.2f}mm")
    print(f"介质: eps_r={medium.eps_r} h={medium.h*1e3:.2f}mm")
    print(f"RWG 基函数数: {s.nb}")

    # 3) 定义端口（在首尾两端的 RWG 基函数上）
    s.add_port("in", 0)      # 端口 1
    s.add_port("out", -1)    # -1 = 最后一个基函数（端口 2）

    # 4) 单频求解
    S = s.solve(1e9)
    print(f"\n1 GHz S 参数:")
    print(f"  |S11|={abs(S[0,0]):.4f}  |S21|={abs(S[1,0]):.4f}")
    print(f"  互易性 |S12-S21|={abs(S[0,1]-S[1,0]):.2e}")

    # 5) 扫频 + Touchstone 输出
    freqs = np.linspace(1e9, 10e9, 10)
    path = s.to_touchstone("demo_structure.s2p", freqs, fmt="RI")
    print(f"\nTouchstone 写入: {path}")

    # 6) 读回验证
    fr, S2, z0 = mom.read_touchstone(path)
    print(f"读回: {len(fr)} 频点, z0={z0}Ω, S shape={S2.shape}")


if __name__ == "__main__":
    main()
