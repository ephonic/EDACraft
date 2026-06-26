#!/usr/bin/env python3
"""waveview.py — rfsim 波形查看器

用法:
    python tools/waveview.py <csv_file> [node1 node2 ...]
    python tools/waveview.py build/amp_pss.csv          # 显示所有节点
    python tools/waveview.py build/amp_pss.csv v1 v3    # 只显示 v1, v3

支持 CSV 格式（rfsim 导出的 _pss.csv / _tran.csv）:
    time,v1,v2,v3,...
    0.0,0.7,0.85,1.5,...
"""
import sys
import csv

try:
    import matplotlib
    matplotlib.use('TkAgg')  # 交互式后端
    import matplotlib.pyplot as plt
except ImportError:
    print("错误: 需要 matplotlib。安装: pip install matplotlib")
    sys.exit(1)


def load_csv(path):
    """加载 CSV 波形文件，返回 (time, signals) 字典"""
    with open(path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        header = [h.strip() for h in header]
        cols = {h: [] for h in header}
        for row in reader:
            for i, val in enumerate(row):
                if i < len(header):
                    try:
                        cols[header[i]].append(float(val))
                    except ValueError:
                        cols[header[i]].append(0.0)
    return cols


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    csv_path = sys.argv[1]
    selected = sys.argv[2:] if len(sys.argv) > 2 else None

    try:
        data = load_csv(csv_path)
    except FileNotFoundError:
        print(f"错误: {csv_path} 不存在")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取 {csv_path} 失败: {e}")
        sys.exit(1)

    time_key = 'time' if 'time' in data else list(data.keys())[0]
    t = data[time_key]

    # 选择要显示的信号
    signals = [k for k in data.keys() if k != time_key]
    if selected:
        signals = [s for s in signals if s in selected]
        if not signals:
            print(f"错误: 未找到指定信号。可用: {', '.join(data.keys())}")
            sys.exit(1)

    # 绘图
    fig, ax = plt.subplots(figsize=(10, 6))
    for sig in signals:
        ax.plot(t, data[sig], label=sig, linewidth=1.2)

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Voltage (V)')
    ax.set_title(f'{csv_path} — {len(signals)} signals, {len(t)} points')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='k', linewidth=0.5)

    # 自动调整 x 轴
    if t:
        t_max = max(t)
        ax.set_xlim(t[0], t_max)

    plt.tight_layout()
    print(f"显示 {len(signals)} 个信号, {len(t)} 个时间点")
    print(f"时间范围: {t[0]:.6g} ~ {t[-1]:.6g} s")
    print("关闭窗口退出...")
    plt.show()


if __name__ == '__main__':
    main()
