"""FreqSweep —— 扫频配置（线性 / 对数，逐点精确求解）。

按 plan0627.md §3：扫频只做逐点精确求解，不做插值/降阶（AWE 等留作后续
工具链）。本类是 C++ FrequencySweep 的轻量 Python 包装，提供更友好的
构造接口（默认参数、单位友好）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import numpy as np

from ._mom import FrequencySweep as _FrequencySweep
from ._mom import SweepScale

_SCALE_MAP = {
    "lin": SweepScale.Linear,
    "linear": SweepScale.Linear,
    "log": SweepScale.Log,
    "logarithmic": SweepScale.Log,
}


@dataclass
class FreqSweep:
    """扫频描述。

    Parameters
    ----------
    start : float
        起始频率（Hz）。
    stop : float
        终止频率（Hz）。
    count : int
        频点数（含两端）。count==1 时仅返回 {start}。
    scale : {"lin", "log"}
        频率刻度。对数刻度要求 start>0。
    """

    start: float = 1.0e6
    stop: float = 1.0e9
    count: int = 201
    scale: Union[str, SweepScale] = "lin"

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("count 必须 > 0")
        if self.stop < self.start:
            raise ValueError("stop 必须 >= start")
        if isinstance(self.scale, str):
            key = self.scale.lower()
            if key not in _SCALE_MAP:
                raise ValueError(f"未知刻度 {self.scale!r}，应为 'lin' 或 'log'")
            if key in ("log", "logarithmic") and self.start <= 0:
                raise ValueError("对数扫频要求 start > 0")
            self._scale_enum = _SCALE_MAP[key]
        else:
            self._scale_enum = self.scale

    def frequencies(self) -> np.ndarray:
        """返回本次扫频的全部频点（Hz），NumPy float64 数组。"""
        sw = _FrequencySweep(self.start, self.stop, self.count, self._scale_enum)
        return sw.frequencies()

    # 便捷构造
    @classmethod
    def linear(cls, start: float, stop: float, count: int) -> "FreqSweep":
        return cls(start, stop, count, "lin")

    @classmethod
    def logarithmic(cls, start: float, stop: float, count: int) -> "FreqSweep":
        return cls(start, stop, count, "log")
