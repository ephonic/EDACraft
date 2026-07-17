"""Structure: 任意导体结构的 MoM S 参数提取（3D RWG 网格）。

高层接口，基于 TriMesh + RWG 基函数 + 并矢格林函数 + Schur N-端口。

用法：
    s = mom.Structure(
        conductor=mom.RectangleConductor(0, 0.02, -0.0015, 0.0015, 0.0016),
        medium=mom.Stackup(eps_r=4.3, h=1.6e-3),
        nx=8, ny=2,
    )
    s.add_port("in", 0)
    s.add_port("out", -1)   # -1 = 最后一个基函数
    S = s.solve(1e9)         # → (2,2) S 参数
    s.to_touchstone('out.s2p', np.linspace(1e9, 10e9, 10))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union
import numpy as np

from . import _mom


@dataclass
class RectangleConductor:
    """矩形带导体（平面微带线）。"""
    x0: float = 0.0
    x1: float = 0.02
    y0: float = -0.0015
    y1: float = 0.0015
    z: float = 0.0016

    @property
    def length(self) -> float:
        return self.x1 - self.x0

    @property
    def width(self) -> float:
        return self.y1 - self.y0


@dataclass
class Stackup:
    """单层介质 + PEC 接地（屏蔽微带）。"""
    eps_r: float = 4.3
    tand: float = 0.0
    h: float = 0.0016


class Structure:
    """任意导体结构的 MoM S 参数提取（RWG 网格）。

    Parameters
    ----------
    conductor : RectangleConductor 或自定义（含 x0/x1/y0/y1/z 属性）
    medium : Stackup
    nx, ny : 网格分段
    z0_ref : 端口参考阻抗
    """

    def __init__(
        self,
        conductor: RectangleConductor,
        medium: Stackup,
        nx: int = 8,
        ny: int = 1,
        z0_ref: float = 50.0,
    ):
        self.conductor = conductor
        self.medium = medium
        self.nx = nx
        self.ny = ny
        self.z0_ref = z0_ref
        self._ports: dict[str, int] = {}

        # 查询基函数数
        info = _mom.trimesh_rectangle_strip(
            conductor.x0, conductor.x1,
            conductor.y0, conductor.y1,
            conductor.z, nx, ny,
        )
        self._nb = info["n_rwg"]

    @property
    def nb(self) -> int:
        """RWG 基函数数"""
        return self._nb

    def add_port(self, name: str, basis_index: int) -> None:
        """添加端口（指定 RWG 基函数索引，-1 = 最后一个）。

        Parameters
        ----------
        name : 端口名称
        basis_index : RWG 基函数索引（0-based），-1 = 最后一个
        """
        if basis_index < 0:
            basis_index = self._nb + basis_index
        if not (0 <= basis_index < self._nb):
            raise ValueError(f"端口索引 {basis_index} 超出范围 [0, {self._nb})")
        self._ports[name] = basis_index

    def solve(self, freq: float, **kwargs) -> np.ndarray:
        """单频求解 → S 参数矩阵。

        Parameters
        ----------
        freq : 频率 (Hz)
        kwargs : gauss_order, n_intervals, gauss_order_qwe

        Returns
        -------
        S : (nport, nport) complex128
        """
        if len(self._ports) < 1:
            raise RuntimeError("至少需要 1 个端口")

        ports = list(self._ports.values())
        S = _mom.solve_rwg_sparam(
            freq, self.medium.eps_r, self.medium.tand, self.medium.h,
            self.conductor.x0, self.conductor.x1,
            self.conductor.y0, self.conductor.y1,
            self.nx, self.ny,
            kwargs.get("gauss_order", 5),
            kwargs.get("n_intervals", 40),
            kwargs.get("gauss_order_qwe", 5),
            ports, self.z0_ref,
        )
        return np.asarray(S)

    def sweep(self, freqs: np.ndarray, **kwargs) -> np.ndarray:
        """扫频 → S 参数序列。

        Returns
        -------
        S : (nfreq, nport, nport) complex128
        """
        S_all = np.zeros((len(freqs), len(self._ports), len(self._ports)), complex)
        for i, f in enumerate(freqs):
            S_all[i] = self.solve(f, **kwargs)
        return S_all

    def to_touchstone(
        self,
        filename: Union[str, Path],
        freqs: np.ndarray,
        freq_unit: str = "GHz",
        fmt: str = "RI",
        comments=None,
        **kwargs,
    ) -> Path:
        """扫频 + Touchstone 输出。

        Parameters
        ----------
        filename : 输出路径
        freqs : 频率数组 (Hz)
        freq_unit, fmt, comments : Touchstone 选项
        kwargs : 传给 solve 的参数
        """
        from .touchstone import write_touchstone

        S = self.sweep(freqs, **kwargs)
        nport = S.shape[1]
        ext = f".s{nport}p"
        if comments is None:
            comments = []
        comments = list(comments) + [
            f"RWG Structure: L={self.conductor.length*1e3:.2f}mm "
            f"W={self.conductor.width*1e3:.2f}mm",
            f"eps_r={self.medium.eps_r} h={self.medium.h*1e3:.2f}mm",
            f"nx={self.nx} ny={self.ny} z0_ref={self.z0_ref}ohm",
            f"Ports: {list(self._ports.keys())}",
        ]
        return write_touchstone(
            filename, freqs, S,
            freq_unit=freq_unit, fmt=fmt, z0=self.z0_ref, comments=comments,
        )
