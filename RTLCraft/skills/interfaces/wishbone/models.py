"""
skills.interfaces.wishbone.models — Wishbone Behavioral Models

Golden-reference simulators for Wishbone bus components.
"""
from __future__ import annotations


class WB_Reg_Model:
    """Wishbone register slice behavioral model."""

    def __init__(self, data_width: int = 32, addr_width: int = 32):
        self.data_width = data_width
        self.addr_width = addr_width
        self.reset()

    def reset(self):
        self.wbm_dat_o = 0
        self.wbm_ack_o = 0
        self.wbm_err_o = 0
        self.wbm_rty_o = 0
        self.wbs_adr_o = 0
        self.wbs_dat_o = 0
        self.wbs_we_o = 0
        self.wbs_stb_o = 0
        self.wbs_cyc_o = 0
        self._wbs_cyc_o_reg = 0
        self._wbs_stb_o_reg = 0

    def cycle(self, rst=0, **inputs):
        if rst:
            self.reset()
            return

        wbm_ack_o_prev = self.wbm_ack_o
        wbm_err_o_prev = self.wbm_err_o
        wbm_rty_o_prev = self.wbm_rty_o

        if self._wbs_cyc_o_reg and self._wbs_stb_o_reg:
            if inputs.get("wbs_ack_i") or inputs.get("wbs_err_i") or inputs.get("wbs_rty_i"):
                self.wbm_dat_o = inputs.get("wbs_dat_i", 0)
                self.wbm_ack_o = inputs.get("wbs_ack_i", 0)
                self.wbm_err_o = inputs.get("wbs_err_i", 0)
                self.wbm_rty_o = inputs.get("wbs_rty_i", 0)
                self._wbs_stb_o_reg = 0
        else:
            self.wbm_dat_o = 0
            self.wbm_ack_o = 0
            self.wbm_err_o = 0
            self.wbm_rty_o = 0
            self.wbs_adr_o = inputs.get("wbm_adr_i", 0)
            self.wbs_dat_o = inputs.get("wbm_dat_i", 0)
            self._wbs_cyc_o_reg = inputs.get("wbm_cyc_i", 0)
            self.wbs_we_o = inputs.get("wbm_we_i", 0) and not (wbm_ack_o_prev or wbm_err_o_prev or wbm_rty_o_prev)
            self.wbs_stb_o = inputs.get("wbm_stb_i", 0) and not (wbm_ack_o_prev or wbm_err_o_prev or wbm_rty_o_prev)
            self.wbs_cyc_o = self._wbs_cyc_o_reg


class WB_MUX_2_Model:
    """Wishbone 2-to-1 MUX behavioral model."""

    def __init__(self, data_width: int = 32, addr_width: int = 32):
        self.data_width = data_width
        self.addr_width = addr_width

    def cycle(self, **inputs):
        wbm_adr_i = inputs.get("wbm_adr_i", 0)
        wbm_cyc_i = inputs.get("wbm_cyc_i", 0)
        wbm_stb_i = inputs.get("wbm_stb_i", 0)
        wbm_dat_i = inputs.get("wbm_dat_i", 0)
        wbm_we_i = inputs.get("wbm_we_i", 0)
        wbm_sel_i = inputs.get("wbm_sel_i", 0)

        wbs0_addr = inputs.get("wbs0_addr", 0)
        wbs0_addr_msk = inputs.get("wbs0_addr_msk", 0)
        wbs1_addr = inputs.get("wbs1_addr", 0)
        wbs1_addr_msk = inputs.get("wbs1_addr_msk", 0)

        wbs0_dat_i = inputs.get("wbs0_dat_i", 0)
        wbs0_ack_i = inputs.get("wbs0_ack_i", 0)
        wbs0_err_i = inputs.get("wbs0_err_i", 0)
        wbs0_rty_i = inputs.get("wbs0_rty_i", 0)

        wbs1_dat_i = inputs.get("wbs1_dat_i", 0)
        wbs1_ack_i = inputs.get("wbs1_ack_i", 0)
        wbs1_err_i = inputs.get("wbs1_err_i", 0)
        wbs1_rty_i = inputs.get("wbs1_rty_i", 0)

        wbs0_match = 1 if ((wbm_adr_i ^ wbs0_addr) & wbs0_addr_msk) == 0 else 0
        wbs1_match = 1 if ((wbm_adr_i ^ wbs1_addr) & wbs1_addr_msk) == 0 else 0
        wbs0_sel = wbs0_match
        wbs1_sel = wbs1_match and not wbs0_match
        master_cycle = wbm_cyc_i and wbm_stb_i
        select_error = (not (wbs0_sel or wbs1_sel)) and master_cycle

        wbm_dat_o = wbs0_dat_i if wbs0_sel else (wbs1_dat_i if wbs1_sel else 0)

        return {
            "wbm_dat_o": wbm_dat_o,
            "wbm_ack_o": wbs0_ack_i or wbs1_ack_i,
            "wbm_err_o": wbs0_err_i or wbs1_err_i or select_error,
            "wbm_rty_o": wbs0_rty_i or wbs1_rty_i,
            "wbs0_adr_o": wbm_adr_i,
            "wbs0_dat_o": wbm_dat_i,
            "wbs0_we_o": wbm_we_i and wbs0_sel,
            "wbs0_sel_o": wbm_sel_i,
            "wbs0_stb_o": wbm_stb_i and wbs0_sel,
            "wbs0_cyc_o": wbm_cyc_i and wbs0_sel,
            "wbs1_adr_o": wbm_adr_i,
            "wbs1_dat_o": wbm_dat_i,
            "wbs1_we_o": wbm_we_i and wbs1_sel,
            "wbs1_sel_o": wbm_sel_i,
            "wbs1_stb_o": wbm_stb_i and wbs1_sel,
            "wbs1_cyc_o": wbm_cyc_i and wbs1_sel,
        }
