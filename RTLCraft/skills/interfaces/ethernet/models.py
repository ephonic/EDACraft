"""
skills.interfaces.ethernet.models — Ethernet Behavioral Models
"""
from __future__ import annotations


class PTP_TS_Extract_Model:
    """PTP timestamp extraction model."""

    def __init__(self, ts_width: int = 96, ts_offset: int = 1):
        self.ts_width = ts_width
        self.ts_offset = ts_offset
        self.reset()

    def reset(self):
        self.m_axis_ts = 0
        self.m_axis_ts_valid = 0
        self._frame_reg = 0

    def cycle(self, rst=0, s_axis_tvalid=0, s_axis_tlast=0, s_axis_tuser=0):
        if rst:
            self.reset()
            return

        ts_mask = (1 << self.ts_width) - 1
        self.m_axis_ts = (s_axis_tuser >> self.ts_offset) & ts_mask
        self.m_axis_ts_valid = s_axis_tvalid and not self._frame_reg

        if s_axis_tvalid:
            self._frame_reg = not s_axis_tlast
