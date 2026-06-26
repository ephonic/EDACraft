"""
skills.interfaces.axis.models — AXI-Stream Behavioral Models

Golden-reference simulators for AXI-Stream components.
"""
from __future__ import annotations


class AXIS_Register_Model:
    """AXI-Stream skid buffer register model (REG_TYPE=2)."""

    def __init__(self, data_width: int = 8):
        self.data_width = data_width
        self.reset()

    def reset(self):
        self.s_axis_tready = 0
        self.m_axis_tdata = 0
        self.m_axis_tvalid = 0
        self._m_data_reg = 0
        self._m_valid_reg = 0
        self._temp_data_reg = 0
        self._temp_valid_reg = 0
        self._s_tready_reg = 0

    def cycle(self, rst=0, s_axis_tdata=0, s_axis_tvalid=0, m_axis_tready=0):
        if rst:
            self.reset()
            return

        s_tready_early = m_axis_tready or (not self._temp_valid_reg and (not self._m_valid_reg or not s_axis_tvalid))

        if self._s_tready_reg:
            if m_axis_tready or not self._m_valid_reg:
                self._m_valid_reg = s_axis_tvalid
                self._m_data_reg = s_axis_tdata
                self._temp_valid_reg = self._temp_valid_reg
            else:
                self._temp_valid_reg = s_axis_tvalid
                self._temp_data_reg = s_axis_tdata
        elif m_axis_tready:
            self._m_valid_reg = self._temp_valid_reg
            self._m_data_reg = self._temp_data_reg
            self._temp_valid_reg = 0

        self._s_tready_reg = s_tready_early
        self.s_axis_tready = self._s_tready_reg
        self.m_axis_tdata = self._m_data_reg
        self.m_axis_tvalid = self._m_valid_reg


class AXIS_Adapter_Model:
    """AXI-Stream width up-size adapter model."""

    def __init__(self, s_data_width: int = 8, m_data_width: int = 32):
        self.s_data_width = s_data_width
        self.m_data_width = m_data_width
        self.seg_count = m_data_width // s_data_width
        self.reset()

    def reset(self):
        self.s_axis_tready = 0
        self.m_axis_tdata = 0
        self.m_axis_tvalid = 0
        self.m_axis_tlast = 0
        self._seg_out = [0] * self.seg_count
        self._seg_cnt = 0
        self._s_data_reg = 0
        self._s_valid_reg = 0
        self._m_valid_reg = 0
        self._m_last_reg = 0

    def cycle(self, rst=0, s_axis_tdata=0, s_axis_tvalid=0, s_axis_tlast=0, m_axis_tready=0):
        if rst:
            self.reset()
            return

        self._m_valid_reg = self._m_valid_reg and not m_axis_tready
        self.s_axis_tready = not self._s_valid_reg

        if not self._m_valid_reg or m_axis_tready:
            if self._s_valid_reg:
                self._s_valid_reg = 0
                self._seg_out[self._seg_cnt] = self._s_data_reg
                if s_axis_tlast or self._seg_cnt == self.seg_count - 1:
                    self._seg_cnt = 0
                    self._m_valid_reg = 1
                    self._m_last_reg = s_axis_tlast
                else:
                    self._seg_cnt += 1
            elif s_axis_tvalid:
                self._seg_out[self._seg_cnt] = s_axis_tdata
                if s_axis_tlast or self._seg_cnt == self.seg_count - 1:
                    self._seg_cnt = 0
                    self._m_valid_reg = 1
                    self._m_last_reg = s_axis_tlast
                else:
                    self._seg_cnt += 1

        if s_axis_tvalid and self.s_axis_tready:
            self._s_data_reg = s_axis_tdata
            self._s_valid_reg = 1 if (self._m_valid_reg and not m_axis_tready) else 0

        self.m_axis_tdata = 0
        for i in range(self.seg_count):
            self.m_axis_tdata |= self._seg_out[i] << (i * self.s_data_width)
        self.m_axis_tvalid = self._m_valid_reg
        self.m_axis_tlast = self._m_last_reg
