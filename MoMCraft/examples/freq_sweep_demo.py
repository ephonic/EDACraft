"""阶段 0 示例：扫频配置 + C++/NumPy 零拷贝通路演示。

运行：python examples/freq_sweep_demo.py
（需先 pip install -e . 编译 _mom 扩展）
"""
import numpy as np

import mom


def main():
    print(f"mom version: {mom.__version__}")

    # 1) 零拷贝通路冒烟测试
    a = np.arange(1, 6, dtype=np.float64)
    print("输入数组:", a)
    mom.square_inplace(a)
    print("平方后  :", a)

    # 2) 线性扫频
    lin = mom.FreqSweep.linear(1e6, 10e9, 11)
    fl = lin.frequencies()
    print(f"\n线性扫频 {fl.size} 点: {fl[0]/1e9:.3f} -> {fl[-1]/1e9:.3f} GHz")
    print("  前3点 (GHz):", np.round(fl[:3] / 1e9, 4))

    # 3) 对数扫频
    log = mom.FreqSweep.logarithmic(1e6, 10e9, 5)
    fg = log.frequencies()
    print(f"\n对数扫频 {fg.size} 点:")
    for v in fg:
        print(f"  {v/1e9:.4f} GHz")


if __name__ == "__main__":
    main()
