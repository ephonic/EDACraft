"""L5 DSL implementation for the Earphone top-level SoC."""

from __future__ import annotations

from typing import Any, Dict

from rtlgen import Cat, Mux
from rtlgen.core import Const, Input, Module, Output, Wire
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template

from earphone.modules.apb_bridge.layer_L5_dsl.src.dsl import EarphoneAPBBridge
from earphone.modules.fft256.layer_L5_dsl.src.dsl import EarphoneFFT256
from earphone.modules.i2c.layer_L5_dsl.src.dsl import EarphoneI2C
from earphone.modules.qspi.layer_L5_dsl.src.dsl import EarphoneQSPI
from earphone.modules.rv32.layer_L5_dsl.src.dsl import EarphoneRV32
from earphone.modules.simd16.layer_L5_dsl.src.dsl import EarphoneSIMD16
from earphone.modules.sram256k.layer_L5_dsl.src.dsl import EarphoneSRAM256K


class EarphoneTop(Module):
    """Top-level SoC integrating CPU, accelerators, memory, and peripherals."""

    def __init__(self):
        super().__init__("earphone_top")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # External QSPI flash pins.
        self.qspi_sck = Output(1, "qspi_sck")
        self.qspi_cs_n = Output(1, "qspi_cs_n")
        self.qspi_io_o = Output(4, "qspi_io_o")
        self.qspi_io_i = Input(4, "qspi_io_i")
        self.qspi_io_oe = Output(4, "qspi_io_oe")

        # I2C pins.
        self.scl_i = Input(1, "scl_i")
        self.scl_o = Output(1, "scl_o")
        self.scl_oe = Output(1, "scl_oe")
        self.sda_i = Input(1, "sda_i")
        self.sda_o = Output(1, "sda_o")
        self.sda_oe = Output(1, "sda_oe")

        # Simple instruction/data memory bus exposed at the SoC boundary.
        self.imem_addr = Output(32, "imem_addr")
        self.imem_rdata = Input(32, "imem_rdata")
        self.imem_req = Output(1, "imem_req")
        self.imem_gnt = Input(1, "imem_gnt")

        self.dmem_addr = Output(32, "dmem_addr")
        self.dmem_wdata = Output(32, "dmem_wdata")
        self.dmem_rdata = Input(32, "dmem_rdata")
        self.dmem_we = Output(4, "dmem_we")
        self.dmem_req = Output(1, "dmem_req")
        self.dmem_gnt = Input(1, "dmem_gnt")
        self.dmem_valid = Input(1, "dmem_valid")

        # External APB4 master port for test/debug access to peripherals.
        self.apb_paddr = Input(32, "apb_paddr")
        self.apb_penable = Input(1, "apb_penable")
        self.apb_pwrite = Input(1, "apb_pwrite")
        self.apb_psel = Input(1, "apb_psel")
        self.apb_pstrb = Input(4, "apb_pstrb")
        self.apb_pwdata = Input(32, "apb_pwdata")
        self.apb_prdata = Output(32, "apb_prdata")
        self.apb_pready = Output(1, "apb_pready")
        self.apb_pslverr = Output(1, "apb_pslverr")

        self._instantiate_cpu()
        self._instantiate_accelerators()
        self._instantiate_peripherals()

        tpl = ModuleDocTemplate(
            source="earphone/top/layer_L5_dsl/src/dsl.py",
            description="Smart Earphone SoC top-level integration with APB test port.",
            author="RTLCraft Agent",
            version="0.2",
            timing="Refer to top-level and submodule layer contracts.",
        )
        fill_doc_template(tpl, self)

    def _instantiate_cpu(self) -> None:
        cpu = EarphoneRV32()
        self.instantiate(cpu, "cpu", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "imem_addr": self.imem_addr,
            "imem_rdata": self.imem_rdata,
            "imem_req": self.imem_req,
            "imem_gnt": self.imem_gnt,
            "dmem_addr": self.dmem_addr,
            "dmem_wdata": self.dmem_wdata,
            "dmem_rdata": self.dmem_rdata,
            "dmem_we": self.dmem_we,
            "dmem_req": self.dmem_req,
            "dmem_gnt": self.dmem_gnt,
            "dmem_valid": self.dmem_valid,
            "retire_valid": Wire(1, "cpu_retire_valid"),
            "retire_rd": Wire(5, "cpu_retire_rd"),
            "retire_result": Wire(32, "cpu_retire_result"),
        })

    def _instantiate_accelerators(self) -> None:
        simd = EarphoneSIMD16()
        simd_vsrc0 = Wire(256, "simd_vsrc0")
        simd_vsrc1 = Wire(256, "simd_vsrc1")
        simd_vsrc2 = Wire(256, "simd_vsrc2")
        simd_op = Wire(5, "simd_op")
        simd_mode = Wire(1, "simd_mode")
        simd_pred = Wire(16, "simd_pred")
        simd_start = Wire(1, "simd_start")
        self.instantiate(simd, "simd16", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "vsrc0": simd_vsrc0,
            "vsrc1": simd_vsrc1,
            "vsrc2": simd_vsrc2,
            "vdst": Wire(256, "simd_vdst"),
            "op": simd_op,
            "mode": simd_mode,
            "pred": simd_pred,
            "start": simd_start,
            "done": Wire(1, "simd_done"),
        })

        fft = EarphoneFFT256()
        self.instantiate(fft, "fft256", port_map={
            "clk": self.clk,
            "rst": ~self.rst_n,
            "di_en": Wire(1, "fft_di_en"),
            "di_re": Wire(16, "fft_di_re"),
            "di_im": Wire(16, "fft_di_im"),
            "do_en": Wire(1, "fft_do_en"),
            "do_re": Wire(16, "fft_do_re"),
            "do_im": Wire(16, "fft_do_im"),
        })

    def _instantiate_peripherals(self) -> None:
        qspi = EarphoneQSPI()
        qspi_req = Wire(1, "qspi_req")
        qspi_addr = Wire(32, "qspi_addr")
        qspi_rdata = Wire(32, "qspi_rdata")
        qspi_ready = Wire(1, "qspi_ready")
        self.instantiate(qspi, "qspi", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "req": qspi_req,
            "addr": qspi_addr,
            "rdata": qspi_rdata,
            "ready": qspi_ready,
            "qspi_sck": self.qspi_sck,
            "qspi_cs_n": self.qspi_cs_n,
            "qspi_io_o": self.qspi_io_o,
            "qspi_io_i": self.qspi_io_i,
            "qspi_io_oe": self.qspi_io_oe,
        })

        s_paddr = Wire(32, "s_paddr")
        s_penable = Wire(1, "s_penable")
        s_pwdata = Wire(32, "s_pwdata")
        s_pwrite = Wire(1, "s_pwrite")
        s_psel = Wire(8, "s_psel")
        s_pstrb = Wire(4, "s_pstrb")

        sram_prdata = Wire(32, "sram_prdata")
        sram_pready = Wire(1, "sram_pready")
        sram_pslverr = Wire(1, "sram_pslverr")
        i2c_prdata = Wire(32, "i2c_prdata")
        i2c_pready = Wire(1, "i2c_pready")

        sram = EarphoneSRAM256K()
        self.instantiate(sram, "sram", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "paddr": s_paddr,
            "pwdata": s_pwdata,
            "prdata": sram_prdata,
            "pwrite": s_pwrite,
            "psel": s_psel[1],
            "penable": s_penable,
            "pready": sram_pready,
            "pslverr": sram_pslverr,
            "pstrb": s_pstrb,
        })

        i2c = EarphoneI2C()
        self.instantiate(i2c, "i2c", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "paddr": s_paddr[11:0],
            "pwdata": s_pwdata,
            "prdata": i2c_prdata,
            "pwrite": s_pwrite,
            "psel": s_psel[4],
            "penable": s_penable,
            "pready": i2c_pready,
            "scl_i": self.scl_i,
            "scl_o": self.scl_o,
            "scl_oe": self.scl_oe,
            "sda_i": self.sda_i,
            "sda_o": self.sda_o,
            "sda_oe": self.sda_oe,
        })

        s_prdata = Mux(s_psel[1], sram_prdata, Mux(s_psel[4], i2c_prdata, Const(0, 32)))
        s_pready = Cat(Const(0, 1), sram_pready, Const(0, 2), i2c_pready, Const(0, 3))
        s_pslverr = Cat(Const(0, 1), sram_pslverr, Const(0, 6))

        bridge = EarphoneAPBBridge()
        apb_prdata_w = Wire(32, "apb_prdata_w")
        apb_pready_w = Wire(1, "apb_pready_w")
        apb_pslverr_w = Wire(1, "apb_pslverr_w")
        self.instantiate(bridge, "apb_bridge", port_map={
            "clk": self.clk,
            "rst_n": self.rst_n,
            "m_paddr": self.apb_paddr,
            "m_pwdata": self.apb_pwdata,
            "m_prdata": apb_prdata_w,
            "m_pwrite": self.apb_pwrite,
            "m_psel": self.apb_psel,
            "m_penable": self.apb_penable,
            "m_pready": apb_pready_w,
            "m_pslverr": apb_pslverr_w,
            "m_pstrb": self.apb_pstrb,
            "s_paddr": s_paddr,
            "s_pwdata": s_pwdata,
            "s_prdata": s_prdata,
            "s_pwrite": s_pwrite,
            "s_psel": s_psel,
            "s_penable": s_penable,
            "s_pready": s_pready,
            "s_pslverr": s_pslverr,
            "s_pstrb": s_pstrb,
        })

        with self.comb:
            self.apb_prdata <<= apb_prdata_w
            self.apb_pready <<= apb_pready_w
            self.apb_pslverr <<= apb_pslverr_w


def build_top() -> EarphoneTop:
    """Instantiate the top-level DSL contract."""
    return EarphoneTop()


def describe() -> Dict[str, Any]:
    """Return L5 DSL metadata for top-level document generation and tests."""
    return {
        "name": "EarphoneTop",
        "layer": "L5_dsl",
        "status": "implemented",
        "dsl_object_name": "earphone_top",
        "verilog_module_name": "EarphoneTop",
        "verilog_file_name": "earphone_top.v",
        "source": "earphone.top.layer_L5_dsl.src.dsl.EarphoneTop",
        "external_ports": [
            "clk",
            "rst_n",
            "imem_addr",
            "dmem_addr",
            "apb_paddr",
            "qspi_cs_n",
            "scl_o",
            "sda_o",
        ],
    }


__all__ = ["EarphoneTop", "build_top", "describe"]
