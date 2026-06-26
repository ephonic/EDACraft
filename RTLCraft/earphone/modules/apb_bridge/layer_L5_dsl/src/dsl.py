"""L5 DSL module for the EarphoneAPBBridge.

RTL-ready rtlgen description of the AHB-to-APB address decoder.
"""

from __future__ import annotations

from rtlgen.core import Module, Input, Output, Const
from rtlgen import Mux
from rtlgen.codegen import VerilogEmitter, ModuleDocTemplate, fill_doc_template


class EarphoneAPBBridge(Module):
    """Simple APB4 address decoder for 8 slave slots.

    Each slot occupies a 1 MB region starting at base 0x4000_0000.
    Slot 0: QSPI, 1: SRAM, 2: SPI, 3: UART, 4: I2C, 5: I2S, 6: BTLE, 7: SIMD16
    """

    def __init__(self):
        super().__init__("earphone_apb_bridge")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Master APB
        self.m_paddr = Input(32, "m_paddr")
        self.m_pwdata = Input(32, "m_pwdata")
        self.m_prdata = Output(32, "m_prdata")
        self.m_pwrite = Input(1, "m_pwrite")
        self.m_psel = Input(1, "m_psel")
        self.m_penable = Input(1, "m_penable")
        self.m_pready = Output(1, "m_pready")
        self.m_pslverr = Output(1, "m_pslverr")
        self.m_pstrb = Input(4, "m_pstrb")

        # Slave APBs (8 slots)
        self.s_paddr = Output(32, "s_paddr")
        self.s_pwdata = Output(32, "s_pwdata")
        self.s_prdata = Input(32, "s_prdata")
        self.s_pwrite = Output(1, "s_pwrite")
        self.s_psel = Output(8, "s_psel")
        self.s_penable = Output(1, "s_penable")
        self.s_pready = Input(8, "s_pready")
        self.s_pslverr = Input(8, "s_pslverr")
        self.s_pstrb = Output(4, "s_pstrb")

        with self.comb:
            region = self.m_paddr[29:22]  # 1 MB regions
            sel_onehot = Const(0, 8)
            for i in range(8):
                sel_onehot |= Mux(region == Const(i, 8), Const(1 << i, 8), Const(0, 8))

            self.s_paddr <<= self.m_paddr
            self.s_pwdata <<= self.m_pwdata
            self.s_pwrite <<= self.m_pwrite
            self.s_psel <<= sel_onehot
            self.s_penable <<= self.m_penable
            self.s_pstrb <<= self.m_pstrb

            # Mux slave responses back to master
            self.m_prdata <<= self.s_prdata
            self.m_pready <<= (self.s_pready & sel_onehot) != 0
            self.m_pslverr <<= (self.s_pslverr & sel_onehot) != 0

        tpl = ModuleDocTemplate(
            source="earphone/modules/apb_bridge/layer_L5_dsl/src/dsl.py",
            description="APB4 address decoder for smart earphone peripherals.",
            author="RTLCraft Agent", version="0.1",
            timing="Combinational decode; slave determines pready.",
        )
        fill_doc_template(tpl, self)


__all__ = ["EarphoneAPBBridge"]
