"""Microstrip —— 微带线 MoM 求解器的高层封装（阶段 1）。

把 MicrostripConfig + 扫频封装成易用对象，输出 NumPy 数组形式的 S 参数。
按 plan0627.md：扫频逐点精确求解，不做插值/降阶。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ._mom import (
    MicrostripConfig,
    solve_microstrip_sweep,
)


@dataclass
class Microstrip:
    """微带线参数与求解。

    Parameters
    ----------
    length : float
        走线长度 L (m)。
    width : float
        走线宽度 W (m)。
    height : float
        介质厚度 h（导体到接地平面，m）。
    eps_eff : float
        有效介电常数（阶段 1 近似；阶段 2 由多层格林函数吸收）。
    nx : int
        x 方向分段数（越大越精确，越慢）。
    gauss : int
        每段高斯积分点数（建议 4）。
    z0_ref : float
        端口参考阻抗（欧姆）。
    has_ground : bool
        是否有接地平面（镜像格林函数）。
    """

    length: float = 20.0e-3
    width: float = 3.0e-3
    height: float = 1.6e-3
    eps_eff: float = 1.0
    nx: int = 40
    gauss: int = 4
    z0_ref: float = 50.0
    has_ground: bool = True

    def _cfg(self) -> MicrostripConfig:
        c = MicrostripConfig()
        c.length = self.length
        c.width = self.width
        c.height = self.height
        c.eps_eff = self.eps_eff
        c.nx = self.nx
        c.gauss = self.gauss
        c.z0_ref = self.z0_ref
        c.has_ground = self.has_ground
        return c

    def solve_sweep(self, freqs: np.ndarray) -> np.ndarray:
        """逐点扫频求解，返回 (nfreq, 2, 2) complex128 S 参数。"""
        freqs = np.ascontiguousarray(freqs, dtype=np.float64)
        return solve_microstrip_sweep(freqs, self._cfg())

    def solve(self, freq: float) -> np.ndarray:
        """单频点求解，返回 (2, 2) complex128 S 参数。"""
        return self.solve_sweep(np.array([freq], dtype=np.float64))[0]

    def to_touchstone(
        self,
        filename,
        freqs: np.ndarray,
        *,
        freq_unit: str = "GHz",
        fmt: str = "RI",
        comments=None,
    ):
        """扫频并写 Touchstone .s2p 文件。

        Parameters
        ----------
        filename : 输出路径（建议 .s2p）。
        freqs : 频率数组 (Hz)。
        freq_unit : 文件内频率单位。
        fmt : {"RI","MA","DB"}。
        comments : 可选注释列表。
        """
        from pathlib import Path
        from .touchstone import write_touchstone

        S = self.solve_sweep(freqs)
        if comments is None:
            comments = []
        comments = list(comments) + [
            f"Microstrip: L={self.length*1e3:.2f}mm W={self.width*1e3:.2f}mm "
            f"h={self.height*1e3:.2f}mm eps_eff={self.eps_eff:.3f}",
            f"nx={self.nx} gauss={self.gauss} z0_ref={self.z0_ref}ohm",
        ]
        return write_touchstone(
            filename, freqs, S,
            freq_unit=freq_unit, param_type="S", fmt=fmt,
            z0=self.z0_ref, comments=comments,
        )

