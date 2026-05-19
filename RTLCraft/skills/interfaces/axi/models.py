"""
skills.interfaces.axi.models — AXI Behavioral Models
"""
from __future__ import annotations


class AXI_DP_RAM_Simple_Model:
    """Simplified AXI dual-port RAM model."""

    def __init__(self, data_width: int = 32, addr_width: int = 8):
        self.data_width = data_width
        self.addr_width = addr_width
        depth = 2 ** addr_width
        self._mem = [0] * depth
        self.reset()

    def reset(self):
        self.a_awready = 0
        self.a_wready = 0
        self.a_bvalid = 0
        self.a_arready = 0
        self.a_rdata = 0
        self.a_rvalid = 0
        self.b_awready = 0
        self.b_wready = 0
        self.b_bvalid = 0
        self.b_arready = 0
        self.b_rdata = 0
        self.b_rvalid = 0
        self._a_bvalid = 0
        self._a_rvalid = 0
        self._b_bvalid = 0
        self._b_rvalid = 0

    def cycle_a(self, a_rst=0, a_awvalid=0, a_wvalid=0, a_awaddr=0, a_wdata=0,
                a_bready=0, a_arvalid=0, a_araddr=0, a_rready=0):
        if a_rst:
            self._a_bvalid = 0
            self._a_rvalid = 0
            return

        if a_bready and self._a_bvalid:
            self._a_bvalid = 0
        if a_rready and self._a_rvalid:
            self._a_rvalid = 0

        if a_awvalid and a_wvalid and not self._a_bvalid:
            self.a_awready = 1
            self.a_wready = 1
            self._a_bvalid = 1
            if a_awaddr < len(self._mem):
                self._mem[a_awaddr] = a_wdata
        else:
            self.a_awready = 0
            self.a_wready = 0

        if a_arvalid and (not self._a_rvalid or a_rready):
            self.a_arready = 1
            self._a_rvalid = 1
            if a_araddr < len(self._mem):
                self.a_rdata = self._mem[a_araddr]
        else:
            self.a_arready = 0

        self.a_bvalid = self._a_bvalid
        self.a_rvalid = self._a_rvalid

    def cycle_b(self, b_rst=0, b_awvalid=0, b_wvalid=0, b_awaddr=0, b_wdata=0,
                b_bready=0, b_arvalid=0, b_araddr=0, b_rready=0):
        if b_rst:
            self._b_bvalid = 0
            self._b_rvalid = 0
            return

        if b_bready and self._b_bvalid:
            self._b_bvalid = 0
        if b_rready and self._b_rvalid:
            self._b_rvalid = 0

        if b_awvalid and b_wvalid and not self._b_bvalid:
            self.b_awready = 1
            self.b_wready = 1
            self._b_bvalid = 1
            if b_awaddr < len(self._mem):
                self._mem[b_awaddr] = b_wdata
        else:
            self.b_awready = 0
            self.b_wready = 0

        if b_arvalid and (not self._b_rvalid or b_rready):
            self.b_arready = 1
            self._b_rvalid = 1
            if b_araddr < len(self._mem):
                self.b_rdata = self._mem[b_araddr]
        else:
            self.b_arready = 0

        self.b_bvalid = self._b_bvalid
        self.b_rvalid = self._b_rvalid
