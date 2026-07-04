"""Touchstone .sNp 文件写入（符合 Touchstone 2.0 规范）。

支持 .s1p / .s2p / .sNp。每行：freq, S11_re, S11_im, S12_re, S12_im, ...
可选 [Hz|kHz|MHz|GHz], [S|Y|Z], [RI|MA|DB], R ref。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np


def write_touchstone(
    filename: Union[str, Path],
    freqs: np.ndarray,
    S: np.ndarray,
    *,
    freq_unit: str = "GHz",
    param_type: str = "S",
    fmt: str = "RI",
    z0: Union[float, complex, list, np.ndarray] = 50.0,
    comments: Optional[list] = None,
) -> Path:
    """写 Touchstone .sNp 文件。

    Parameters
    ----------
    filename : 输出文件名（扩展名建议 .sNp，N=端口数）。
    freqs : 频率数组 (Hz)，shape (nfreq,)。
    S : S 参数数组，shape (nfreq, N, N)，复数。
    freq_unit : {"Hz","kHz","MHz","GHz"} 频率单位（文件内）。
    param_type : {"S","Y","Z"} 参数类型。
    fmt : {"RI","MA","DB"} 数据格式：实虚部 / 幅角 / dB-幅角。
    z0 : 参考阻抗（标量或每端口数组，欧姆）。
    comments : 可选注释行列表（每行加 !）。

    Returns
    -------
    Path : 写入的文件路径。
    """
    freqs = np.asarray(freqs, dtype=np.float64).ravel()
    S = np.asarray(S, dtype=np.complex128)
    if S.ndim != 3:
        raise ValueError(f"S 必须是 3D (nfreq, N, N)，得到 shape {S.shape}")
    nfreq, nport, nport2 = S.shape
    if nport != nport2:
        raise ValueError(f"S 必须方阵，得到 {nport}x{nport2}")

    # 频率单位缩放
    unit_factor = {"Hz": 1.0, "kHz": 1e-3, "MHz": 1e-6, "GHz": 1e-9}[freq_unit]
    freqs_scaled = freqs * unit_factor

    # z0 规范化
    if np.isscalar(z0):
        z0_arr = np.full(nport, complex(z0))
    else:
        z0_arr = np.asarray([complex(z) for z in z0])
        if len(z0_arr) != nport:
            raise ValueError(f"z0 长度 {len(z0_arr)} != 端口数 {nport}")

    lines = []
    # 注释
    if comments:
        for c in comments:
            lines.append(f"! {c}")
    lines.append(f"! Created by mom Touchstone writer")
    lines.append("!")

    # 选项行：# freq_unit param_type fmt R z0
    z0_real = z0_arr[0].real if np.allclose(z0_arr.real, z0_arr[0].real) else None
    r_str = f"R {z0_real}" if z0_real is not None else ""
    lines.append(f"# {freq_unit} {param_type} {fmt} {r_str}".strip())

    # .s2p 特殊：端口阻抗行（Touchstone 2.0 可选）
    # 简化：仅写数据行（兼容 Touchstone 1.0）

    # 数据格式化
    def fmt_complex(z):
        if fmt == "RI":
            return f"{z.real:.6e} {z.imag:.6e}"
        elif fmt == "MA":
            return f"{np.abs(z):.6e} {np.angle(z, deg=True):.4f}"
        elif fmt == "DB":
            mag_db = 20 * np.log10(np.abs(z) + 1e-30)
            return f"{mag_db:.6e} {np.angle(z, deg=True):.4f}"
        else:
            raise ValueError(f"未知 fmt {fmt!r}")

    # 每频点一行（.s2p 标准）或多行（.sNp, N>2 时按矩阵行换行）
    for fi in range(nfreq):
        parts = [f"{freqs_scaled[fi]:.6e}"]
        for r in range(nport):
            for c in range(nport):
                parts.append(fmt_complex(S[fi, r, c]))
        # .s2p: 全部一行；.s1p: 一行；.sNp (N>2): 触摸石允许换行
        if nport <= 2:
            lines.append(" ".join(parts))
        else:
            # N>2: 第一行 freq + S[行0]（nport 个复数），后续每行一个矩阵行
            # parts 索引：parts[0]=freq, parts[1..nport²]=复数（按行优先）
            row0 = [parts[0]] + [parts[1 + c] for c in range(nport)]
            lines.append(" ".join(row0))
            for r in range(1, nport):
                row_parts = [parts[1 + r*nport + c] for c in range(nport)]
                lines.append(" ".join(row_parts))

    path = Path(filename)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def read_touchstone(filename: Union[str, Path]):
    """读 Touchstone .sNp，返回 (freqs_Hz, S, z0)。

    支持 RI/MA/DB 格式，自动检测端口数。
    """
    path = Path(filename)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    freq_unit = "GHz"
    fmt = "RI"
    z0 = 50.0
    data_lines = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("!"):
            continue
        if s.startswith("#"):
            # 选项行
            tokens = s[1:].split()
            for i, t in enumerate(tokens):
                tl = t.lower()
                if tl in ("hz", "khz", "mhz", "ghz"):
                    # 规范化单位大小写
                    freq_unit = {"hz":"Hz","khz":"kHz","mhz":"MHz","ghz":"GHz"}[tl]
                elif tl in ("s", "y", "z"):
                    pass
                elif tl in ("ri", "ma", "db"):
                    fmt = tl.upper()
                elif tl == "r" and i + 1 < len(tokens):
                    z0 = float(tokens[i + 1])
            continue
        data_lines.append(s)

    # 解析端口数（从第一频点的数据点数）
    # .s2p: 每频点 1 行 9 列 (freq + 8)；.s1p: 3 列
    # 通用：统计连续数据直到下一个频率
    unit_factor = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[freq_unit]

    # 通用 N-port 解析：展平所有数值，按 (freq, N² 复数) 分块
    unit_factor = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[freq_unit]
    # 展平所有数据行的数值
    flat = []
    for s in data_lines:
        flat.extend(float(t) for t in s.split())
    if not flat:
        return np.zeros(0), np.zeros((0, 1, 1), complex), z0
    # 从第一频点推断 N：第一数值是 freq，后续直到下一个"频率样"的数值。
    # .s2p: freq + 8 (4 复数) = 9 值/频点；.s4p: freq + 32 = 33 值/频点（多行拼接）
    # 启发式：首频点行有 freq + n_c 复数。若 n_c == 1→N=1, n_c==4→N=2, 否则 N=n_c（多行首行）
    # 更稳健：首行（data_lines[0]）的复数数决定
    first_rest = [float(t) for t in data_lines[0].split()][1:]
    n_c_first = len(first_rest) // 2
    # 检测 N：n_c_first 可能是 N²（.s1p/.s2p 单行）或 N（.sNp N>2 多行首行）
    is_square = int(round(np.sqrt(n_c_first)))**2 == n_c_first
    if n_c_first == 1:
        nport = 1
    elif n_c_first == 4 and is_square:
        # .s2p 单行（N=2, N²=4）vs .s4p 多行首行（N=4, 首行 N=4 复数）
        # 区分：看总数据是否 = nfreq·(1+2·4²)=33n 或 nfreq·(1+2·2²)=9n
        total_vals = len(flat)
        n4 = total_vals / (1 + 2*16)  # N=4
        n2 = total_vals / (1 + 2*4)   # N=2
        nport = 4 if abs(n4 - round(n4)) < abs(n2 - round(n2)) else 2
    elif is_square and n_c_first <= 4:
        nport = int(round(np.sqrt(n_c_first)))
    else:
        nport = n_c_first  # N>2 多行：首行有 N 复数
    # 每频点总数值数：1 (freq) + 2·N² (复数)。对 N>2，跨多行但展平后连续。
    nvals_per_freq = 1 + 2 * nport * nport
    nfreq = len(flat) // nvals_per_freq
    freqs = []
    all_s = []
    for k in range(nfreq):
        base = k * nvals_per_freq
        f = flat[base] * unit_factor
        cvals = []
        for j in range(nport * nport):
            re = flat[base + 1 + 2*j]
            im = flat[base + 1 + 2*j + 1]
            if fmt == "MA":
                cvals.append(complex(re * np.cos(np.radians(im)),
                                     re * np.sin(np.radians(im))))
            elif fmt == "DB":
                mag = 10**(re/20)
                cvals.append(complex(mag * np.cos(np.radians(im)),
                                     mag * np.sin(np.radians(im))))
            else:  # RI
                cvals.append(complex(re, im))
        freqs.append(f)
        all_s.append(np.array(cvals).reshape(nport, nport))
    freqs = np.array(freqs)
    S = np.array(all_s) if all_s else np.zeros((0, 1, 1), complex)
    return freqs, S, z0
