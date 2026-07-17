#!/usr/bin/env python3
"""waveview.py — rfsim 波形查看器（增强版，Phase D）

用法:
    python tools/waveview.py <file> [signals...] [options]
    python tools/waveview.py build/out_pss.raw              # 自动识别格式
    python tools/waveview.py out.csv v(in) v(out)           # 指定信号
    python tools/waveview.py out.json --fft v(out)          # FFT 面板
    python tools/waveview.py out.raw --panel                # 多面板（每信号一个子图）
    python tools/waveview.py out.csv --logx                 # 对数 X 轴
    python tools/waveview.py out.csv --export out.png       # 导出 PNG（不弹窗）

支持格式（按扩展名 + 内容自动识别）:
    - CSV  : rfsim 原生（time,v1,v2,... 或 time,v(n),...）
    - Raw  : ngspice/ltx ASCII raw（Title/Variables/Values）
    - JSON : rfsim 结构化（{signals, points}）

功能:
    - 多信号叠加 / 多面板（--panel）
    - FFT 频谱面板（--fft SIG）
    - 对数坐标（--logx / --logy）
    - XY / Lissajous 模式（--xy SIG1 SIG2）
    - PNG 导出（--export）
    - 信号名筛选（位置参数）

依赖: matplotlib + numpy（pip install matplotlib numpy）
"""
import sys
import os
import json
import math

try:
    import numpy as np
    import matplotlib
    matplotlib.use('TkAgg')  # 交互式后端
    import matplotlib.pyplot as plt
except ImportError:
    print("错误: 需要 matplotlib + numpy。安装: pip install matplotlib numpy")
    sys.exit(1)


# ============ 格式 reader ============

def read_csv(path):
    """读 CSV（time,v1,... 或 time,v(n),...）。返回 (time_list, {sig: vals})"""
    import csv
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
    time_key = 'time' if 'time' in cols else list(cols.keys())[0]
    t = cols.pop(time_key)
    return t, cols


def read_raw(path):
    """读 ngspice ASCII raw。返回 (time_list, {sig: vals})"""
    with open(path, 'r') as f:
        lines = f.readlines()
    num_vars = 0
    num_points = 0
    var_names = []
    in_vars = False
    in_values = False
    points = []
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        low = ln.lower()
        if low.startswith('no. variables:'):
            num_vars = int(ln.split(':')[-1].strip())
        elif low.startswith('no. points:'):
            num_points = int(ln.split(':')[-1].strip())
        elif low == 'variables:':
            in_vars = True
            in_values = False
        elif low == 'values:':
            in_vars = False
            in_values = True
        elif in_vars:
            # "  0 time time" / "  1 v(in) voltage"
            parts = ln.split()
            if len(parts) >= 2:
                var_names.append(parts[1])
        elif in_values:
            # "  idx  value0" 然后后续每行一个值
            parts = ln.split()
            if parts and parts[0].isdigit():
                # 新点：parts[0]=idx, parts[1]=第一个变量（time）的值
                point = [float(parts[1])]
                # 收集后续 num_vars-1 个值（每行一个）
                j = i + 1
                while len(point) < num_vars and j < len(lines):
                    vj = lines[j].strip()
                    if vj:
                        try:
                            point.append(float(vj))
                        except ValueError:
                            break
                    j += 1
                points.append(point)
                i = j - 1
        i += 1
    if not var_names:
        var_names = ['time'] + [f'v{k}' for k in range(1, num_vars)]
    t = [p[0] for p in points] if points else []
    cols = {}
    for k in range(1, min(len(var_names), num_vars if num_vars else len(var_names))):
        name = var_names[k] if k < len(var_names) else f'sig{k}'
        cols[name] = [p[k] if k < len(p) else 0.0 for p in points]
    return t, cols


def read_json(path):
    """读 rfsim JSON。返回 (time_list, {sig: vals})"""
    with open(path, 'r') as f:
        data = json.load(f)
    signals = data.get('signals', [])
    points = data.get('points', [])
    # signals[0] 通常是 'time'，但 points 里 t 单独存
    t = [p.get('t', 0.0) for p in points]
    cols = {}
    # signals[1:] 是电压/电流；points[].v 对应
    val_signals = [s for s in signals if s != 'time']
    for idx, sname in enumerate(val_signals):
        cols[sname] = [p['v'][idx] if idx < len(p.get('v', [])) else 0.0 for p in points]
    return t, cols


def detect_and_read(path):
    """按扩展名 + 内容自动识别格式。返回 (time, cols, fmt_name)"""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.json':
            return (*read_json(path), 'json')
        if ext == '.raw':
            return (*read_raw(path), 'raw')
        if ext == '.csv':
            return (*read_csv(path), 'csv')
        # 无扩展名/未知：嗅探内容
        with open(path, 'r') as f:
            head = f.read(256)
        if head.strip().startswith('{') or '"signals"' in head:
            return (*read_json(path), 'json')
        if 'Title:' in head or 'Variables:' in head or 'No. Variables' in head:
            return (*read_raw(path), 'raw')
        return (*read_csv(path), 'csv')
    except FileNotFoundError:
        print(f"错误: {path} 不存在")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取 {path} 失败: {e}")
        sys.exit(1)


# ============ 绘图 ============

def plot_time_domain(t, cols, selected, args):
    """时域多信号叠加或分面板"""
    n = len(selected)
    if args.panel and n > 1:
        # 每信号一个子图
        fig, axes = plt.subplots(n, 1, figsize=(10, 2.5 * n), sharex=True)
        if n == 1:
            axes = [axes]
        for ax, sig in zip(axes, selected):
            ax.plot(t, cols[sig], linewidth=1.2, label=sig)
            ax.set_ylabel(sig)
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color='k', linewidth=0.5)
            if args.logy:
                ax.set_yscale('symlog')
        axes[-1].set_xlabel('Time (s)')
        if args.logx:
            axes[-1].set_xscale('log')
        fig.suptitle(f'{args.path} — {n} signals, {len(t)} points (multi-panel)')
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        for sig in selected:
            ax.plot(t, cols[sig], linewidth=1.2, label=sig)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Voltage (V) / Current (A)')
        ax.set_title(f'{args.path} — {n} signals, {len(t)} points')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='k', linewidth=0.5)
        if args.logx:
            ax.set_xscale('log')
        if args.logy:
            ax.set_yscale('symlog')
    return fig


def plot_fft(t, cols, sig, args):
    """单信号 FFT 频谱"""
    if sig not in cols:
        print(f"错误: 信号 {sig} 不存在。可用: {list(cols.keys())}")
        sys.exit(1)
    y = np.array(cols[sig])
    n = len(y)
    if n < 2:
        print("错误: 点数太少，无法做 FFT")
        sys.exit(1)
    # 采样率
    dt = (t[-1] - t[0]) / (n - 1) if n > 1 else 1.0
    fs = 1.0 / dt if dt > 0 else 1.0
    # 去直流 + 窗
    yw = y - np.mean(y)
    win = np.hanning(n)
    Y = np.fft.rfft(yw * win)
    freqs = np.fft.rfftfreq(n, d=dt)
    mag = 2.0 * np.abs(Y) / max(np.sum(win), 1e-30)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(freqs, mag, linewidth=1.2)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel(f'|{sig}| magnitude')
    ax.set_title(f'FFT of {sig} — fs={fs:.3g} Hz, N={n}')
    ax.grid(True, alpha=0.3)
    if args.logx:
        ax.set_xscale('log')
    if args.logy:
        ax.set_yscale('log')
    return fig


def plot_xy(cols, sig_x, sig_y):
    """XY / Lissajous 模式"""
    if sig_x not in cols or sig_y not in cols:
        print(f"错误: 信号不存在。可用: {list(cols.keys())}")
        sys.exit(1)
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(cols[sig_x], cols[sig_y], linewidth=1.2)
    ax.set_xlabel(sig_x)
    ax.set_ylabel(sig_y)
    ax.set_title(f'XY: {sig_y} vs {sig_x}')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='k', linewidth=0.5)
    ax.axvline(x=0, color='k', linewidth=0.5)
    return fig


# ============ CLI ============

def main():
    import argparse
    p = argparse.ArgumentParser(description='rfsim 波形查看器（多格式 + FFT + XY）')
    p.add_argument('path', help='波形文件（.csv/.raw/.json，自动识别）')
    p.add_argument('signals', nargs='*', help='要显示的信号名（默认全部）')
    p.add_argument('--fft', metavar='SIG', help='对 SIG 做 FFT 频谱面板')
    p.add_argument('--xy', nargs=2, metavar=('SIG_X', 'SIG_Y'), help='XY / Lissajous 模式')
    p.add_argument('--panel', action='store_true', help='多面板（每信号一个子图）')
    p.add_argument('--logx', action='store_true', help='对数 X 轴')
    p.add_argument('--logy', action='store_true', help='对数 Y 轴')
    p.add_argument('--export', metavar='PNG', help='导出 PNG（不弹窗）')
    p.add_argument('--list', action='store_true', help='列出所有信号后退出')
    args = p.parse_args()

    t, cols, fmt = detect_and_read(args.path)
    print(f"格式: {fmt} | 信号数: {len(cols)} | 点数: {len(t)}")
    print(f"时间范围: {t[0]:.6g} ~ {t[-1]:.6g} s" if t else "时间范围: (空)")

    all_sigs = list(cols.keys())
    if args.list:
        print("可用信号:", ', '.join(all_sigs))
        return

    selected = args.signals if args.signals else all_sigs
    # 过滤不存在的信号
    missing = [s for s in selected if s not in cols]
    if missing:
        print(f"警告: 信号不存在，已忽略: {missing}")
        selected = [s for s in selected if s in cols]
    if not selected:
        print(f"错误: 无可显示信号。可用: {all_sigs}")
        sys.exit(1)

    fig = None
    if args.xy:
        fig = plot_xy(cols, args.xy[0], args.xy[1])
    elif args.fft:
        fig = plot_fft(t, cols, args.fft, args)
    else:
        fig = plot_time_domain(t, cols, selected, args)

    plt.tight_layout()
    if args.export:
        fig.savefig(args.export, dpi=150)
        print(f"已导出: {args.export}")
    else:
        print("关闭窗口退出...")
        plt.show()


if __name__ == '__main__':
    main()
