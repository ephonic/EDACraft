"""
skills.interfaces.pcie.models — PCIe Behavioral Models
"""
from __future__ import annotations


class Pulse_Merge_Model:
    """Pulse merge counter behavioral model."""

    def __init__(self, input_width: int = 2, count_width: int = 4):
        self.input_width = input_width
        self.count_width = count_width
        self.reset()

    def reset(self):
        self.count_out = 0
        self.pulse_out = 0
        self._count_reg = 0

    def cycle(self, rst=0, pulse_in=0):
        if rst:
            self.reset()
            return

        # Population count
        pulse_sum = bin(pulse_in & ((1 << self.input_width) - 1)).count('1')

        # Decrement
        count_base = self._count_reg - 1 if self._count_reg > 0 else 0
        self._count_reg = min(count_base + pulse_sum, (1 << self.count_width) - 1)

        self.count_out = self._count_reg
        self.pulse_out = 1 if self._count_reg > 0 else 0


class PCIe_PTile_FC_Model:
    """PCIe P-Tile flow control counter model."""

    def __init__(self, width: int = 16, index: int = 0):
        self.width = width
        self.index = index
        self.reset()

    def reset(self):
        self.fc_av = 0
        self._fc_cap = 0
        self._fc_limit = 0

    def cycle(self, rst=0, tx_cdts_limit=0, tx_cdts_limit_tdm_idx=0, fc_dec=0):
        if rst:
            self.reset()
            return

        if tx_cdts_limit_tdm_idx == self.index:
            if self._fc_cap == 0:
                self._fc_cap = tx_cdts_limit
            fc_inc = tx_cdts_limit - self._fc_limit
            self._fc_limit = tx_cdts_limit
        else:
            fc_inc = 0

        add_result = self.fc_av + fc_inc
        if add_result >= fc_dec:
            sub_result = add_result - fc_dec
            self.fc_av = sub_result if sub_result <= self._fc_cap else self._fc_cap
        else:
            self.fc_av = 0
