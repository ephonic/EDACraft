#!/usr/bin/env python3
"""
Lightweight DDR3 Memory Controller — RTLCraft Python DSL
==========================================================

Based on ref_rtl/core_ddr3_controller (ultraembedded/core_ddr3_controller).

Features:
  - DLL-off mode DDR3 controller for low-speed operation (< 125 MHz)
  - Simplified 32-bit memory port with byte-masked writes and burst reads
  - Up to 8 open rows for back-to-back burst access
  - Standardized DFI interface to PHY
  - Refresh management with periodic auto-refresh
  - Power-up initialization sequence (CKE, LOAD_MODE, ZQCL, PRECHARGE)

Modules:
  DDR3FIFO        : Simple synchronous FIFO (ID tracking, DFI write data)
  DDR3DFISeq      : DFI sequencer — command timing, write/read data shifting
  DDR3Core        : Core controller — initialization FSM, refresh, bank management
  DDR3Controller  : Top-level wrapper
"""

import sys
sys.path.insert(0, "/Users/yangfan/release/EDACraft-main/RTLCraft")

from rtlgen import (
    Module, Input, Output, Reg, Wire, Memory,
    VerilogEmitter, Simulator, LocalParam, Parameter,
)
from rtlgen.logic import If, Else, Switch, Const, Cat


# =====================================================================
# DDR3FIFO — Simple synchronous FIFO
# =====================================================================

class DDR3FIFO(Module):
    """Synchronous FIFO with parameterized width and depth."""

    def __init__(self, width: int = 8, depth: int = 4, name: str = "DDR3FIFO"):
        super().__init__(name)
        self._width = width
        self._depth = depth
        addr_w = max(depth.bit_length(), 1)
        count_w = addr_w + 1

        self.WIDTH = Parameter(width, "WIDTH")
        self.DEPTH = Parameter(depth, "DEPTH")

        self.clk_i = Input(1, "clk_i")
        self.rst_i = Input(1, "rst_i")
        self.data_in_i = Input(width, "data_in_i")
        self.push_i = Input(1, "push_i")
        self.pop_i = Input(1, "pop_i")

        self.data_out_o = Output(width, "data_out_o")
        self.accept_o = Output(1, "accept_o")
        self.valid_o = Output(1, "valid_o")

        # Memory array
        self.ram = Memory(width, depth, "ram")

        self.rd_ptr = Reg(addr_w, "rd_ptr")
        self.wr_ptr = Reg(addr_w, "wr_ptr")
        self.count = Reg(count_w, "count")

        @self.comb
        def _comb():
            self.accept_o <<= self.count != depth
            self.valid_o <<= self.count != 0
            self.data_out_o <<= self.ram[self.rd_ptr]

        @self.seq(self.clk_i, self.rst_i)
        def _seq():
            with If(self.rst_i == 1):
                self.count <<= 0
                self.rd_ptr <<= 0
                self.wr_ptr <<= 0
            with Else():
                with If(self.push_i & self.accept_o):
                    self.ram[self.wr_ptr] <<= self.data_in_i
                    self.wr_ptr <<= self.wr_ptr + 1

                with If(self.pop_i & self.valid_o):
                    self.rd_ptr <<= self.rd_ptr + 1

                with If((self.push_i & self.accept_o) & ~(self.pop_i & self.valid_o)):
                    self.count <<= self.count + 1
                with Else():
                    with If(~(self.push_i & self.accept_o) & (self.pop_i & self.valid_o)):
                        self.count <<= self.count - 1


# =====================================================================
# DDR3DFISeq — DFI Sequencer
# =====================================================================

class DDR3DFISeq(Module):
    """DFI sequencer: handles DDR3 command timing and data-path serialization.

    Translates high-level commands (ACTIVE, READ, WRITE, etc.) into DFI signals
    with proper tRCD/tRP/tRFC delays. Serializes 128-bit write data into 32-bit
    DFI words and assembles 32-bit read data into 128-bit words.
    """

    def __init__(
        self,
        ddr_mhz: int = 50,
        ddr_write_latency: int = 6,
        ddr_read_latency: int = 5,
        ddr_burst_len: int = 4,
        ddr_col_w: int = 9,
        ddr_bank_w: int = 3,
        ddr_row_w: int = 15,
        ddr_data_w: int = 32,
        ddr_dqm_w: int = 4,
        name: str = "DDR3DFISeq",
    ):
        super().__init__(name)
        self.ddr_mhz = ddr_mhz
        self.ddr_write_latency = ddr_write_latency
        self.ddr_read_latency = ddr_read_latency
        self.ddr_burst_len = ddr_burst_len
        self.ddr_col_w = ddr_col_w
        self.ddr_bank_w = ddr_bank_w
        self.ddr_row_w = ddr_row_w
        self.ddr_data_w = ddr_data_w
        self.ddr_dqm_w = ddr_dqm_w

        cycle_time_ns = 1000 // ddr_mhz if ddr_mhz > 0 else 20
        ddr_trcd_cycles = (15 + (cycle_time_ns - 1)) // cycle_time_ns
        ddr_trp_cycles = (15 + (cycle_time_ns - 1)) // cycle_time_ns
        ddr_trfc_cycles = (260 + (cycle_time_ns - 1)) // cycle_time_ns
        ddr_twtr_cycles = 5 + 1
        ddr_rw_nonseq_cycles = ddr_write_latency + ddr_burst_len + ddr_twtr_cycles
        ddr_rw_seq_cycles = ddr_rw_nonseq_cycles + 1 - ddr_burst_len

        t_phy_wrlat = ddr_write_latency - 1
        t_phy_rdlat = ddr_read_latency - 1
        delay_w = 6

        # Commands
        cmd_w = 4
        cmd_nop = 0b0111
        cmd_active = 0b0011
        cmd_read = 0b0101
        cmd_write = 0b0100
        cmd_precharge = 0b0010
        cmd_refresh = 0b0001
        cmd_load_mode = 0b0000
        cmd_zqcl = 0b0110

        # Ports
        self.clk_i = Input(1, "clk_i")
        self.rst_i = Input(1, "rst_i")
        self.address_i = Input(ddr_row_w, "address_i")
        self.bank_i = Input(ddr_bank_w, "bank_i")
        self.command_i = Input(cmd_w, "command_i")
        self.cke_i = Input(1, "cke_i")
        self.wrdata_i = Input(128, "wrdata_i")
        self.wrdata_mask_i = Input(16, "wrdata_mask_i")
        self.dfi_rddata_i = Input(ddr_data_w, "dfi_rddata_i")
        self.dfi_rddata_valid_i = Input(1, "dfi_rddata_valid_i")
        self.dfi_rddata_dnv_i = Input(2, "dfi_rddata_dnv_i")

        self.accept_o = Output(1, "accept_o")
        self.rddata_o = Output(128, "rddata_o")
        self.rddata_valid_o = Output(1, "rddata_valid_o")
        self.dfi_address_o = Output(ddr_row_w, "dfi_address_o")
        self.dfi_bank_o = Output(ddr_bank_w, "dfi_bank_o")
        self.dfi_cas_n_o = Output(1, "dfi_cas_n_o")
        self.dfi_cke_o = Output(1, "dfi_cke_o")
        self.dfi_cs_n_o = Output(1, "dfi_cs_n_o")
        self.dfi_odt_o = Output(1, "dfi_odt_o")
        self.dfi_ras_n_o = Output(1, "dfi_ras_n_o")
        self.dfi_reset_n_o = Output(1, "dfi_reset_n_o")
        self.dfi_we_n_o = Output(1, "dfi_we_n_o")
        self.dfi_wrdata_o = Output(ddr_data_w, "dfi_wrdata_o")
        self.dfi_wrdata_en_o = Output(1, "dfi_wrdata_en_o")
        self.dfi_wrdata_mask_o = Output(ddr_dqm_w, "dfi_wrdata_mask_o")
        self.dfi_rddata_en_o = Output(1, "dfi_rddata_en_o")

        # Internal signals
        wr_shift_w = t_phy_wrlat + ddr_burst_len
        rd_shift_w = t_phy_rdlat + ddr_burst_len
        cmd_accept_w = 9

        self.delay_q = Reg(delay_w, "delay_q")
        self.last_cmd_q = Reg(cmd_w, "last_cmd_q")
        self.wr_accept_q = Reg(cmd_accept_w, "wr_accept_q")
        self.wr_en_q = Reg(wr_shift_w, "wr_en_q")
        self.rd_en_q = Reg(rd_shift_w, "rd_en_q")
        self.command_q = Reg(cmd_w, "command_q")
        self.addr_q = Reg(ddr_row_w, "addr_q")
        self.bank_q = Reg(ddr_bank_w, "bank_q")
        self.cke_q = Reg(1, "cke_q")
        self.dfi_wrdata_q = Reg(ddr_data_w, "dfi_wrdata_q")
        self.dfi_wrdata_mask_q = Reg(ddr_dqm_w, "dfi_wrdata_mask_q")
        self.dfi_wr_idx_q = Reg(2, "dfi_wr_idx_q")
        self.dfi_wrdata_en_q = Reg(1, "dfi_wrdata_en_q")
        self.dfi_rddata_en_q = Reg(1, "dfi_rddata_en_q")
        self.dfi_rd_idx_q = Reg(2, "dfi_rd_idx_q")
        self.rd_data_q = Reg(128, "rd_data_q")
        self.rd_valid_q = Reg(1, "rd_valid_q")

        # Wires for FIFO connections and internal logic
        self.wrfifo_push = Wire(1, "wrfifo_push")
        self.wrfifo_pop = Wire(1, "wrfifo_pop")
        self.wrfifo_data_in = Wire(144, "wrfifo_data_in")
        self.wrfifo_data_out = Wire(144, "wrfifo_data_out")
        self.wrdata_w = Wire(128, "wrdata_w")
        self.wrdata_mask_w = Wire(16, "wrdata_mask_w")
        self.delay_r = Wire(delay_w, "delay_r")
        self.read_early_accept = Wire(1, "read_early_accept")
        self.write_early_accept = Wire(1, "write_early_accept")

        @self.comb
        def _fifo_logic():
            self.wrfifo_push <<= (self.command_i == cmd_write) & self.accept_o
            self.wrfifo_data_in <<= Cat(self.wrdata_mask_i, self.wrdata_i)
            self.wrfifo_pop <<= self.wr_en_q[0] & (self.dfi_wr_idx_q == 3)
            self.wrdata_w <<= self.wrfifo_data_out[127:0]
            self.wrdata_mask_w <<= self.wrfifo_data_out[143:128]

        self.instantiate(
            DDR3FIFO(width=144, depth=4, name="u_write_fifo"),
            name="u_write_fifo",
            params={"WIDTH": 144, "DEPTH": 4},
            port_map={
                "clk_i": self.clk_i,
                "rst_i": self.rst_i,
                "data_in_i": self.wrfifo_data_in,
                "push_i": self.wrfifo_push,
                "pop_i": self.wrfifo_pop,
                "data_out_o": self.wrfifo_data_out,
            },
        )

        @self.comb
        def _early_accept():
            self.read_early_accept <<= (self.last_cmd_q == cmd_read) & (self.command_i == cmd_read) & (self.delay_q == ddr_rw_seq_cycles)
            self.write_early_accept <<= (self.last_cmd_q == cmd_write) & (self.command_i == cmd_write) & (self.delay_q == ddr_rw_seq_cycles)

        @self.comb
        def _accept_logic():
            self.accept_o <<= (self.delay_q == 0) | self.read_early_accept | self.write_early_accept | (self.command_i == cmd_nop)

        @self.comb
        def _delay_comb():
            self.delay_r <<= self.delay_q
            with If(self.delay_q == 0):
                with If(self.command_i == cmd_active):
                    self.delay_r <<= ddr_trcd_cycles
                with Else():
                    with If((self.command_i == cmd_read) | (self.command_i == cmd_write)):
                        self.delay_r <<= ddr_rw_nonseq_cycles
                    with Else():
                        with If(self.command_i == cmd_precharge):
                            self.delay_r <<= ddr_trp_cycles
                        with Else():
                            with If(self.command_i == cmd_refresh):
                                self.delay_r <<= ddr_trfc_cycles
                            with Else():
                                self.delay_r <<= 0
            with Else():
                with If(self.delay_q != 0):
                    self.delay_r <<= self.delay_q - 1
                    with If(self.read_early_accept | self.write_early_accept):
                        self.delay_r <<= ddr_rw_nonseq_cycles

        # Sequential logic
        @self.seq(self.clk_i, self.rst_i)
        def _seq():
            with If(self.rst_i == 1):
                self.delay_q <<= 0
                self.last_cmd_q <<= cmd_nop
                self.wr_accept_q <<= 0
                self.wr_en_q <<= 0
                self.rd_en_q <<= 0
                self.command_q <<= cmd_nop
                self.addr_q <<= 0
                self.bank_q <<= 0
                self.cke_q <<= 0
                self.dfi_wrdata_q <<= 0
                self.dfi_wrdata_mask_q <<= 0
                self.dfi_wr_idx_q <<= 0
                self.dfi_wrdata_en_q <<= 0
                self.dfi_rddata_en_q <<= 0
                self.dfi_rd_idx_q <<= 0
                self.rd_data_q <<= 0
                self.rd_valid_q <<= 0
            with Else():
                # Delay counter
                self.delay_q <<= self.delay_r

                # Last command tracking
                with If(self.accept_o & (self.command_i != cmd_nop)):
                    self.last_cmd_q <<= self.command_i

                # Write accept shift register
                with If((self.command_i == cmd_write) & (self.delay_q == 0)):
                    self.wr_accept_q <<= Cat(Const(1, 1), self.wr_accept_q[cmd_accept_w - 1:1])
                with Else():
                    self.wr_accept_q <<= Cat(Const(0, 1), self.wr_accept_q[cmd_accept_w - 1:1])

                # Write enable shift register
                with If((self.command_i == cmd_write) & self.accept_o):
                    ones = Const((1 << ddr_burst_len) - 1, ddr_burst_len)
                    self.wr_en_q <<= Cat(ones, self.wr_en_q[t_phy_wrlat:1])
                with Else():
                    self.wr_en_q <<= Cat(Const(0, 1), self.wr_en_q[wr_shift_w - 1:1])

                # Read enable shift register
                with If((self.command_i == cmd_read) & self.accept_o):
                    ones = Const((1 << ddr_burst_len) - 1, ddr_burst_len)
                    self.rd_en_q <<= Cat(ones, self.rd_en_q[t_phy_rdlat:1])
                with Else():
                    self.rd_en_q <<= Cat(Const(0, 1), self.rd_en_q[rd_shift_w - 1:1])

                # Command / address / bank / cke flops
                with If(self.accept_o):
                    self.command_q <<= self.command_i
                    self.addr_q <<= self.address_i
                    self.bank_q <<= self.bank_i
                with Else():
                    self.command_q <<= cmd_nop
                    self.addr_q <<= 0
                    self.bank_q <<= 0
                self.cke_q <<= self.cke_i

                # Write data serialization
                with If(self.wr_en_q[0]):
                    with Switch(self.dfi_wr_idx_q) as sw:
                        with sw.case(0):
                            self.dfi_wrdata_q <<= self.wrdata_w[31:0]
                            self.dfi_wrdata_mask_q <<= self.wrdata_mask_w[3:0]
                        with sw.case(1):
                            self.dfi_wrdata_q <<= self.wrdata_w[63:32]
                            self.dfi_wrdata_mask_q <<= self.wrdata_mask_w[7:4]
                        with sw.case(2):
                            self.dfi_wrdata_q <<= self.wrdata_w[95:64]
                            self.dfi_wrdata_mask_q <<= self.wrdata_mask_w[11:8]
                        with sw.case(3):
                            self.dfi_wrdata_q <<= self.wrdata_w[127:96]
                            self.dfi_wrdata_mask_q <<= self.wrdata_mask_w[15:12]
                    self.dfi_wr_idx_q <<= self.dfi_wr_idx_q + 1
                with Else():
                    self.dfi_wrdata_q <<= 0
                    self.dfi_wrdata_mask_q <<= 0

                # Write/read data enable flops
                self.dfi_wrdata_en_q <<= self.wr_en_q[0]
                self.dfi_rddata_en_q <<= self.rd_en_q[0]

                # Read data deserialization
                with If(self.dfi_rddata_valid_i):
                    self.dfi_rd_idx_q <<= self.dfi_rd_idx_q + 1
                    self.rd_data_q <<= Cat(self.dfi_rddata_i, self.rd_data_q[127:32])

                with If(self.dfi_rddata_valid_i & (self.dfi_rd_idx_q == 3)):
                    self.rd_valid_q <<= 1
                with Else():
                    self.rd_valid_q <<= 0

        # DFI output assignments
        @self.comb
        def _dfi_out():
            self.dfi_address_o <<= self.addr_q
            self.dfi_bank_o <<= self.bank_q
            self.dfi_cs_n_o <<= self.command_q[3]
            self.dfi_ras_n_o <<= self.command_q[2]
            self.dfi_cas_n_o <<= self.command_q[1]
            self.dfi_we_n_o <<= self.command_q[0]
            self.dfi_cke_o <<= self.cke_q
            self.dfi_odt_o <<= 0
            self.dfi_reset_n_o <<= 1
            self.dfi_wrdata_o <<= self.dfi_wrdata_q
            self.dfi_wrdata_mask_o <<= self.dfi_wrdata_mask_q
            self.dfi_wrdata_en_o <<= self.dfi_wrdata_en_q
            self.dfi_rddata_en_o <<= self.dfi_rddata_en_q
            self.rddata_o <<= self.rd_data_q
            self.rddata_valid_o <<= self.rd_valid_q


# =====================================================================
# DDR3Core — Core DDR3 Controller
# =====================================================================

class DDR3Core(Module):
    """Core DDR3 controller state machine.

    Handles:
      - Power-up initialization sequence (CKE, LOAD_MODE, ZQCL, PRECHARGE)
      - Refresh timer and periodic auto-refresh
      - Row/bank open/close tracking
      - Command generation (ACTIVE, READ, WRITE, PRECHARGE, REFRESH)
    """

    def __init__(
        self,
        ddr_mhz: int = 25,
        ddr_write_latency: int = 6,
        ddr_read_latency: int = 5,
        ddr_col_w: int = 10,
        ddr_bank_w: int = 3,
        ddr_row_w: int = 15,
        ddr_brc_mode: int = 0,
        name: str = "DDR3Core",
    ):
        super().__init__(name)
        self.ddr_mhz = ddr_mhz
        self.ddr_write_latency = ddr_write_latency
        self.ddr_read_latency = ddr_read_latency
        self.ddr_col_w = ddr_col_w
        self.ddr_bank_w = ddr_bank_w
        self.ddr_row_w = ddr_row_w
        self.ddr_brc_mode = ddr_brc_mode

        ddr_banks = 1 << ddr_bank_w
        ddr_start_delay = 600000 // (1000 // ddr_mhz) if ddr_mhz > 0 else 15000
        ddr_refresh_cycles = (64000 * ddr_mhz) // 8192
        ddr_burst_len = 8

        cmd_w = 4
        cmd_nop = 0b0111
        cmd_active = 0b0011
        cmd_read = 0b0101
        cmd_write = 0b0100
        cmd_precharge = 0b0010
        cmd_refresh = 0b0001
        cmd_load_mode = 0b0000
        cmd_zqcl = 0b0110

        # Mode registers (DLL disabled, CL=6, AL=0, CWL=6)
        mr0_reg = 0x0120
        mr1_reg = 0x0001
        mr2_reg = 0x0008
        mr3_reg = 0x0000

        state_w = 4
        self.STATE_INIT = LocalParam(0, "STATE_INIT")
        self.STATE_DELAY = LocalParam(1, "STATE_DELAY")
        self.STATE_IDLE = LocalParam(2, "STATE_IDLE")
        self.STATE_ACTIVATE = LocalParam(3, "STATE_ACTIVATE")
        self.STATE_READ = LocalParam(4, "STATE_READ")
        self.STATE_WRITE = LocalParam(5, "STATE_WRITE")
        self.STATE_PRECHARGE = LocalParam(6, "STATE_PRECHARGE")
        self.STATE_REFRESH = LocalParam(7, "STATE_REFRESH")

        auto_precharge = 10
        all_banks = 10
        refresh_cnt_w = 20

        # Ports
        self.clk_i = Input(1, "clk_i")
        self.rst_i = Input(1, "rst_i")
        self.cfg_enable_i = Input(1, "cfg_enable_i")
        self.cfg_stb_i = Input(1, "cfg_stb_i")
        self.cfg_data_i = Input(32, "cfg_data_i")
        self.inport_wr_i = Input(16, "inport_wr_i")
        self.inport_rd_i = Input(1, "inport_rd_i")
        self.inport_addr_i = Input(32, "inport_addr_i")
        self.inport_write_data_i = Input(128, "inport_write_data_i")
        self.inport_req_id_i = Input(16, "inport_req_id_i")
        self.dfi_rddata_i = Input(32, "dfi_rddata_i")
        self.dfi_rddata_valid_i = Input(1, "dfi_rddata_valid_i")
        self.dfi_rddata_dnv_i = Input(2, "dfi_rddata_dnv_i")

        self.cfg_stall_o = Output(1, "cfg_stall_o")
        self.inport_accept_o = Output(1, "inport_accept_o")
        self.inport_ack_o = Output(1, "inport_ack_o")
        self.inport_error_o = Output(1, "inport_error_o")
        self.inport_resp_id_o = Output(16, "inport_resp_id_o")
        self.inport_read_data_o = Output(128, "inport_read_data_o")
        self.dfi_address_o = Output(ddr_row_w, "dfi_address_o")
        self.dfi_bank_o = Output(ddr_bank_w, "dfi_bank_o")
        self.dfi_cas_n_o = Output(1, "dfi_cas_n_o")
        self.dfi_cke_o = Output(1, "dfi_cke_o")
        self.dfi_cs_n_o = Output(1, "dfi_cs_n_o")
        self.dfi_odt_o = Output(1, "dfi_odt_o")
        self.dfi_ras_n_o = Output(1, "dfi_ras_n_o")
        self.dfi_reset_n_o = Output(1, "dfi_reset_n_o")
        self.dfi_we_n_o = Output(1, "dfi_we_n_o")
        self.dfi_wrdata_o = Output(32, "dfi_wrdata_o")
        self.dfi_wrdata_en_o = Output(1, "dfi_wrdata_en_o")
        self.dfi_wrdata_mask_o = Output(4, "dfi_wrdata_mask_o")
        self.dfi_rddata_en_o = Output(1, "dfi_rddata_en_o")

        # Internal registers
        self.refresh_q = Reg(1, "refresh_q")
        self.row_open_q = Reg(ddr_banks, "row_open_q")
        self.state_q = Reg(state_w, "state_q")
        self.target_state_q = Reg(state_w, "target_state_q")
        self.refresh_timer_q = Reg(refresh_cnt_w, "refresh_timer_q")
        self.write_ack_q = Reg(1, "write_ack_q")

        # Active row array
        self.active_row = []
        for i in range(ddr_banks):
            self.active_row.append(self.reg(ddr_row_w, f"active_row_q_{i}"))

        # Internal wires
        self.next_state_r = Wire(state_w, "next_state_r")
        self.target_state_r = Wire(state_w, "target_state_r")
        self.command_r = Wire(cmd_w, "command_r")
        self.addr_r = Wire(ddr_row_w, "addr_r")
        self.cke_r = Wire(1, "cke_r")
        self.bank_r = Wire(ddr_bank_w, "bank_r")

        self.ram_addr_w = Wire(32, "ram_addr_w")
        self.ram_wr_w = Wire(16, "ram_wr_w")
        self.ram_rd_w = Wire(1, "ram_rd_w")
        self.ram_write_data_w = Wire(128, "ram_write_data_w")
        self.ram_read_data_w = Wire(128, "ram_read_data_w")
        self.ram_ack_w = Wire(1, "ram_ack_w")
        self.ram_accept_w = Wire(1, "ram_accept_w")
        self.ram_req_w = Wire(1, "ram_req_w")
        self.cmd_accept_w = Wire(1, "cmd_accept_w")

        self.addr_col_w = Wire(ddr_row_w, "addr_col_w")
        self.addr_row_w = Wire(ddr_row_w, "addr_row_w")
        self.addr_bank_w = Wire(ddr_bank_w, "addr_bank_w")
        self.row_open_hit = Wire(1, "row_open_hit")
        self.row_miss = Wire(1, "row_miss")

        self.id_fifo_space_w = Wire(1, "id_fifo_space_w")

        self.instantiate(
            DDR3FIFO(width=16, depth=8, name="u_id_fifo"),
            name="u_id_fifo",
            params={"WIDTH": 16, "DEPTH": 8},
            port_map={
                "clk_i": self.clk_i,
                "rst_i": self.rst_i,
                "data_in_i": self.inport_req_id_i,
                "push_i": self.ram_req_w & self.ram_accept_w,
                "pop_i": self.ram_ack_w,
                "accept_o": self.id_fifo_space_w,
                "data_out_o": self.inport_resp_id_o,
            },
        )

        # Address decode
        @self.comb
        def _addr_decode():
            self.ram_addr_w <<= self.inport_addr_i
            self.ram_wr_w <<= self.inport_wr_i
            self.ram_rd_w <<= self.inport_rd_i
            self.ram_write_data_w <<= self.inport_write_data_i

            # Column address: {zeros, addr[col_w:2], 1'b0}
            col_val = Cat(Const(0, 1), self.inport_addr_i[self.ddr_col_w:2])
            pad_w = self.ddr_row_w - self.ddr_col_w - 1
            if pad_w > 0:
                self.addr_col_w <<= Cat(Const(0, pad_w), col_val)
            else:
                self.addr_col_w <<= col_val

            # Row / bank address decode
            if self.ddr_brc_mode:
                # BRC mode
                self.addr_row_w <<= self.inport_addr_i[self.ddr_row_w + self.ddr_col_w:self.ddr_col_w + 1]
                self.addr_bank_w <<= self.inport_addr_i[self.ddr_row_w + self.ddr_col_w + 3:self.ddr_row_w + self.ddr_col_w + 1]
            else:
                # RBC mode
                self.addr_row_w <<= self.inport_addr_i[self.ddr_row_w + self.ddr_col_w + 3:self.ddr_col_w + 3 + 1]
                self.addr_bank_w <<= self.inport_addr_i[self.ddr_col_w + 1 + 3 - 1:self.ddr_col_w + 1]

        @self.comb
        def _row_check():
            self.row_open_hit <<= 0
            self.row_miss <<= 0
            with Switch(self.addr_bank_w) as sw:
                for b in range(ddr_banks):
                    with sw.case(b):
                        self.row_open_hit <<= self.row_open_q[b] & (self.addr_row_w == self.active_row[b])
                        self.row_miss <<= self.row_open_q[b] & (self.addr_row_w != self.active_row[b])

        # RAM request
        @self.comb
        def _ram_req():
            self.ram_req_w <<= ((self.ram_wr_w != 0) | self.ram_rd_w) & self.id_fifo_space_w

        # State machine — next state logic
        @self.comb
        def _next_state():
            self.next_state_r <<= self.state_q
            self.target_state_r <<= self.target_state_q

            with Switch(self.state_q) as sw:
                with sw.case(self.STATE_INIT):
                    with If(self.refresh_q):
                        self.next_state_r <<= self.STATE_IDLE

                with sw.case(self.STATE_IDLE):
                    with If(~self.cfg_enable_i):
                        self.next_state_r <<= self.STATE_IDLE
                    with Else():
                        with If(self.refresh_q):
                            with If(self.row_open_q != 0):
                                self.next_state_r <<= self.STATE_PRECHARGE
                                self.target_state_r <<= self.STATE_REFRESH
                            with Else():
                                self.next_state_r <<= self.STATE_REFRESH
                                self.target_state_r <<= self.STATE_REFRESH
                        with Else():
                            with If(self.ram_req_w):
                                with If(self.row_open_hit):
                                    with If(~self.ram_rd_w):
                                        self.next_state_r <<= self.STATE_WRITE
                                    with Else():
                                        self.next_state_r <<= self.STATE_READ
                                with Else():
                                    with If(self.row_miss):
                                        self.next_state_r <<= self.STATE_PRECHARGE
                                        with If(~self.ram_rd_w):
                                            self.target_state_r <<= self.STATE_WRITE
                                        with Else():
                                            self.target_state_r <<= self.STATE_READ
                                    with Else():
                                        self.next_state_r <<= self.STATE_ACTIVATE
                                        with If(~self.ram_rd_w):
                                            self.target_state_r <<= self.STATE_WRITE
                                        with Else():
                                            self.target_state_r <<= self.STATE_READ

                with sw.case(self.STATE_ACTIVATE):
                    self.next_state_r <<= self.target_state_q

                with sw.case(self.STATE_READ):
                    self.next_state_r <<= self.STATE_IDLE

                with sw.case(self.STATE_WRITE):
                    self.next_state_r <<= self.STATE_IDLE

                with sw.case(self.STATE_PRECHARGE):
                    with If(self.target_state_q == self.STATE_REFRESH):
                        self.next_state_r <<= self.STATE_REFRESH
                    with Else():
                        self.next_state_r <<= self.STATE_ACTIVATE

                with sw.case(self.STATE_REFRESH):
                    self.next_state_r <<= self.STATE_IDLE

        # Command generation
        @self.comb
        def _command_gen():
            self.command_r <<= cmd_nop
            self.addr_r <<= 0
            self.bank_r <<= 0
            self.cke_r <<= 1

            with Switch(self.state_q) as sw:
                with sw.case(self.STATE_INIT):
                    with If(self.refresh_timer_q > 2500):
                        self.cke_r <<= 0
                    with If(self.refresh_timer_q == 2400):
                        self.command_r <<= cmd_load_mode
                        self.bank_r <<= 2
                        self.addr_r <<= mr2_reg
                    with If(self.refresh_timer_q == 2300):
                        self.command_r <<= cmd_load_mode
                        self.bank_r <<= 3
                        self.addr_r <<= mr3_reg
                    with If(self.refresh_timer_q == 2200):
                        self.command_r <<= cmd_load_mode
                        self.bank_r <<= 1
                        self.addr_r <<= mr1_reg
                    with If(self.refresh_timer_q == 2100):
                        self.command_r <<= cmd_load_mode
                        self.bank_r <<= 0
                        self.addr_r <<= mr0_reg
                    with If(self.refresh_timer_q == 2000):
                        self.command_r <<= cmd_zqcl
                        self.addr_r <<= self.addr_r | (1 << all_banks)
                    with If(self.refresh_timer_q == 10):
                        self.command_r <<= cmd_precharge
                        self.addr_r <<= self.addr_r | (1 << all_banks)

                with sw.case(self.STATE_IDLE):
                    with If(~self.cfg_enable_i & self.cfg_stb_i):
                        self.command_r <<= self.cfg_data_i[cmd_w - 1:0]
                        self.addr_r <<= self.cfg_data_i[cmd_w + self.ddr_row_w - 1:cmd_w]
                        self.bank_r <<= self.cfg_data_i[cmd_w + self.ddr_row_w + self.ddr_bank_w - 1:cmd_w + self.ddr_row_w]
                        self.cke_r <<= self.cfg_data_i[cmd_w + self.ddr_row_w + self.ddr_bank_w]

                with sw.case(self.STATE_ACTIVATE):
                    self.command_r <<= cmd_active
                    self.addr_r <<= self.addr_row_w
                    self.bank_r <<= self.addr_bank_w

                with sw.case(self.STATE_PRECHARGE):
                    with If(self.target_state_q == self.STATE_REFRESH):
                        self.command_r <<= cmd_precharge
                        self.addr_r <<= self.addr_r | (1 << all_banks)
                    with Else():
                        self.command_r <<= cmd_precharge
                        self.bank_r <<= self.addr_bank_w

                with sw.case(self.STATE_REFRESH):
                    self.command_r <<= cmd_refresh
                    self.addr_r <<= 0
                    self.bank_r <<= 0

                with sw.case(self.STATE_READ):
                    self.command_r <<= cmd_read
                    self.addr_r <<= Cat(Const(0, 3), self.addr_col_w[self.ddr_row_w - 1:3])
                    self.bank_r <<= self.addr_bank_w
                    self.addr_r[auto_precharge] <<= 0

                with sw.case(self.STATE_WRITE):
                    self.command_r <<= cmd_write
                    self.addr_r <<= Cat(Const(0, 3), self.addr_col_w[self.ddr_row_w - 1:3])
                    self.bank_r <<= self.addr_bank_w
                    self.addr_r[auto_precharge] <<= 0

        # ACK and accept logic
        @self.comb
        def _ack_logic():
            self.inport_ack_o <<= self.ram_ack_w
            self.inport_read_data_o <<= self.ram_read_data_w
            self.inport_error_o <<= 0
            self.inport_accept_o <<= self.ram_accept_w
            self.ram_ack_w <<= self.dfi_rddata_valid_i | self.write_ack_q
            self.ram_accept_w <<= ((self.state_q == self.STATE_READ) | (self.state_q == self.STATE_WRITE)) & self.cmd_accept_w
            self.cfg_stall_o <<= ~((self.state_q == self.STATE_IDLE) & self.cmd_accept_w)

        # Sequential logic
        @self.seq(self.clk_i, self.rst_i)
        def _seq():
            with If(self.rst_i == 1):
                self.refresh_q <<= 0
                self.row_open_q <<= 0
                self.state_q <<= self.STATE_INIT
                self.target_state_q <<= self.STATE_IDLE
                self.refresh_timer_q <<= ddr_start_delay
                self.write_ack_q <<= 0
                for i in range(ddr_banks):
                    self.active_row[i] <<= 0
            with Else():
                # Refresh timer
                with If(self.refresh_timer_q == 0):
                    self.refresh_timer_q <<= ddr_refresh_cycles
                with Else():
                    self.refresh_timer_q <<= self.refresh_timer_q - 1

                # Refresh flag
                with If(self.refresh_timer_q == 0):
                    self.refresh_q <<= 1
                with Else():
                    with If(self.state_q == self.STATE_REFRESH):
                        self.refresh_q <<= 0

                # State update
                with If(self.cmd_accept_w):
                    self.state_q <<= self.next_state_r
                    self.target_state_q <<= self.target_state_r

                # Write ack
                self.write_ack_q <<= (self.state_q == self.STATE_WRITE) & self.ram_accept_w

                # Bank management
                with Switch(self.state_q) as sw:
                    with sw.case(self.STATE_ACTIVATE):
                        with Switch(self.addr_bank_w) as swb:
                            for b in range(ddr_banks):
                                with swb.case(b):
                                    self.active_row[b] <<= self.addr_row_w
                        self.row_open_q[self.addr_bank_w] <<= 1

                    with sw.case(self.STATE_PRECHARGE):
                        with If(self.target_state_q == self.STATE_REFRESH):
                            self.row_open_q <<= 0
                        with Else():
                            self.row_open_q[self.addr_bank_w] <<= 0

                with If(~self.cfg_enable_i):
                    self.row_open_q <<= 0

        self.instantiate(
            DDR3DFISeq(
                ddr_mhz=ddr_mhz,
                ddr_write_latency=ddr_write_latency,
                ddr_read_latency=ddr_read_latency,
                ddr_burst_len=ddr_burst_len,
                ddr_col_w=ddr_col_w,
                ddr_bank_w=ddr_bank_w,
                ddr_row_w=ddr_row_w,
                ddr_data_w=32,
                ddr_dqm_w=4,
                name="u_seq",
            ),
            name="u_seq",
            port_map={
                "clk_i": self.clk_i,
                "rst_i": self.rst_i,
                "address_i": self.addr_r,
                "bank_i": self.bank_r,
                "command_i": self.command_r,
                "cke_i": self.cke_r,
                "wrdata_i": self.ram_write_data_w,
                "wrdata_mask_i": ~self.ram_wr_w,
                "dfi_rddata_i": self.dfi_rddata_i,
                "dfi_rddata_valid_i": self.dfi_rddata_valid_i,
                "dfi_rddata_dnv_i": self.dfi_rddata_dnv_i,
                "dfi_address_o": self.dfi_address_o,
                "dfi_bank_o": self.dfi_bank_o,
                "dfi_cas_n_o": self.dfi_cas_n_o,
                "dfi_cke_o": self.dfi_cke_o,
                "dfi_cs_n_o": self.dfi_cs_n_o,
                "dfi_odt_o": self.dfi_odt_o,
                "dfi_ras_n_o": self.dfi_ras_n_o,
                "dfi_reset_n_o": self.dfi_reset_n_o,
                "dfi_we_n_o": self.dfi_we_n_o,
                "dfi_wrdata_o": self.dfi_wrdata_o,
                "dfi_wrdata_en_o": self.dfi_wrdata_en_o,
                "dfi_wrdata_mask_o": self.dfi_wrdata_mask_o,
                "dfi_rddata_en_o": self.dfi_rddata_en_o,
                "rddata_o": self.ram_read_data_w,
                "accept_o": self.cmd_accept_w,
            },
        )


# =====================================================================
# DDR3Controller — Top-level wrapper
# =====================================================================

class DDR3Controller(Module):
    """Top-level DDR3 controller with AXI-like port.

    Provides a simplified 32-bit memory interface:
      - Address, write data, write mask, read enable inputs
      - Read data, ack, accept outputs
    """

    def __init__(
        self,
        ddr_mhz: int = 25,
        ddr_write_latency: int = 6,
        ddr_read_latency: int = 5,
        ddr_col_w: int = 10,
        ddr_bank_w: int = 3,
        ddr_row_w: int = 15,
        name: str = "DDR3Controller",
    ):
        super().__init__(name)

        self.clk_i = Input(1, "clk_i")
        self.rst_i = Input(1, "rst_i")

        # Simplified memory port
        self.mem_addr_i = Input(32, "mem_addr_i")
        self.mem_wr_i = Input(16, "mem_wr_i")
        self.mem_rd_i = Input(1, "mem_rd_i")
        self.mem_wdata_i = Input(128, "mem_wdata_i")
        self.mem_req_id_i = Input(16, "mem_req_id_i")

        self.mem_accept_o = Output(1, "mem_accept_o")
        self.mem_ack_o = Output(1, "mem_ack_o")
        self.mem_rdata_o = Output(128, "mem_rdata_o")
        self.mem_resp_id_o = Output(16, "mem_resp_id_o")

        # DFI PHY interface
        self.dfi_rddata_i = Input(32, "dfi_rddata_i")
        self.dfi_rddata_valid_i = Input(1, "dfi_rddata_valid_i")
        self.dfi_rddata_dnv_i = Input(2, "dfi_rddata_dnv_i")

        self.dfi_address_o = Output(ddr_row_w, "dfi_address_o")
        self.dfi_bank_o = Output(ddr_bank_w, "dfi_bank_o")
        self.dfi_cas_n_o = Output(1, "dfi_cas_n_o")
        self.dfi_cke_o = Output(1, "dfi_cke_o")
        self.dfi_cs_n_o = Output(1, "dfi_cs_n_o")
        self.dfi_odt_o = Output(1, "dfi_odt_o")
        self.dfi_ras_n_o = Output(1, "dfi_ras_n_o")
        self.dfi_reset_n_o = Output(1, "dfi_reset_n_o")
        self.dfi_we_n_o = Output(1, "dfi_we_n_o")
        self.dfi_wrdata_o = Output(32, "dfi_wrdata_o")
        self.dfi_wrdata_en_o = Output(1, "dfi_wrdata_en_o")
        self.dfi_wrdata_mask_o = Output(4, "dfi_wrdata_mask_o")
        self.dfi_rddata_en_o = Output(1, "dfi_rddata_en_o")

        self.instantiate(
            DDR3Core(
                ddr_mhz=ddr_mhz,
                ddr_write_latency=ddr_write_latency,
                ddr_read_latency=ddr_read_latency,
                ddr_col_w=ddr_col_w,
                ddr_bank_w=ddr_bank_w,
                ddr_row_w=ddr_row_w,
                name="u_core",
            ),
            name="u_core",
            port_map={
                "clk_i": self.clk_i,
                "rst_i": self.rst_i,
                "cfg_enable_i": 1,
                "cfg_stb_i": 0,
                "cfg_data_i": Const(0, 32),
                "inport_wr_i": self.mem_wr_i,
                "inport_rd_i": self.mem_rd_i,
                "inport_addr_i": self.mem_addr_i,
                "inport_write_data_i": self.mem_wdata_i,
                "inport_req_id_i": self.mem_req_id_i,
                "dfi_rddata_i": self.dfi_rddata_i,
                "dfi_rddata_valid_i": self.dfi_rddata_valid_i,
                "dfi_rddata_dnv_i": self.dfi_rddata_dnv_i,
                "inport_accept_o": self.mem_accept_o,
                "inport_ack_o": self.mem_ack_o,
                "inport_read_data_o": self.mem_rdata_o,
                "inport_resp_id_o": self.mem_resp_id_o,
                "dfi_address_o": self.dfi_address_o,
                "dfi_bank_o": self.dfi_bank_o,
                "dfi_cas_n_o": self.dfi_cas_n_o,
                "dfi_cke_o": self.dfi_cke_o,
                "dfi_cs_n_o": self.dfi_cs_n_o,
                "dfi_odt_o": self.dfi_odt_o,
                "dfi_ras_n_o": self.dfi_ras_n_o,
                "dfi_reset_n_o": self.dfi_reset_n_o,
                "dfi_we_n_o": self.dfi_we_n_o,
                "dfi_wrdata_o": self.dfi_wrdata_o,
                "dfi_wrdata_en_o": self.dfi_wrdata_en_o,
                "dfi_wrdata_mask_o": self.dfi_wrdata_mask_o,
                "dfi_rddata_en_o": self.dfi_rddata_en_o,
            },
        )
