"""
NeuralAccel Crossbar

Programmable data movement engine connecting 4 on-chip SRAM buffers.
Supports 4 transfer modes:
  0 BLOCK     : contiguous copy   dst[i] = src[i]
  1 STRIDE    : strided copy      dst[i] = src[i * stride]
  2 BROADCAST : broadcast         dst[i] = src[0]
  3 GATHER    : gather            dst[i] = src[idx[i]] (idx from config reg, simplified)

Single-transaction architecture with round-robin arbitration
if multiple requesters are present.  For simplicity, this version
processes one transaction at a time.

Timing: 2 cycles per word (1 read, 1 write).
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else, Mux, Select


MODE_BLOCK = 0b00
MODE_STRIDE = 0b01
MODE_BROADCAST = 0b10
MODE_GATHER = 0b11

# FSM states
CB_IDLE = 0
CB_READ = 1
CB_WRITE = 2
CB_DONE = 3


class Crossbar(Module):
    """4×4 data movement crossbar with programmable transfer modes."""

    def __init__(self, num_ports: int = 4, data_width: int = 16, addr_width: int = 8, name: str = "Crossbar"):
        super().__init__(name)
        self.num_ports = num_ports
        self.port_bits = max(num_ports.bit_length(), 1)
        self.data_width = data_width
        self.addr_width = addr_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Transaction configuration
        self.cfg_valid = Input(1, "cfg_valid")
        self.cfg_mode = Input(2, "cfg_mode")
        self.cfg_src = Input(self.port_bits, "cfg_src")
        self.cfg_dst = Input(self.port_bits, "cfg_dst")
        self.cfg_len = Input(8, "cfg_len")
        self.cfg_src_addr = Input(addr_width, "cfg_src_addr")
        self.cfg_dst_addr = Input(addr_width, "cfg_dst_addr")
        self.cfg_stride = Input(8, "cfg_stride")

        # Port interfaces to SRAM buffers
        # Each port: addr, wdata, we, rdata, valid
        self.port_addr = Vector(addr_width, num_ports, "port_addr", vtype=Output)
        self.port_wdata = Vector(data_width, num_ports, "port_wdata", vtype=Output)
        self.port_we = Vector(num_ports, num_ports, "port_we", vtype=Output)
        self.port_rdata = Vector(data_width, num_ports, "port_rdata", vtype=Input)
        self.port_valid = Vector(num_ports, num_ports, "port_valid", vtype=Output)

        # Status
        self.busy = Output(1, "busy")
        self.done = Output(1, "done")

        # =====================================================================
        # Transaction registers (latched when cfg_valid is asserted)
        # =====================================================================
        self.mode_reg = Reg(2, "mode_reg")
        self.src_reg = Reg(self.port_bits, "src_reg")
        self.dst_reg = Reg(self.port_bits, "dst_reg")
        self.len_reg = Reg(8, "len_reg")
        self.src_addr_reg = Reg(addr_width, "src_addr_reg")
        self.dst_addr_reg = Reg(addr_width, "dst_addr_reg")
        self.stride_reg = Reg(8, "stride_reg")

        # =====================================================================
        # FSM
        # =====================================================================
        self.state = Reg(2, "state")
        self.word_cnt = Reg(8, "word_cnt")
        self.read_data = Reg(data_width, "read_data")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with If(self.rst_n == 0):
                self.state <<= CB_IDLE
                self.word_cnt <<= 0
                self.read_data <<= 0
                self.mode_reg <<= 0
                self.src_reg <<= 0
                self.dst_reg <<= 0
                self.len_reg <<= 0
            with Else():
                with If(self.state == CB_IDLE):
                    with If(self.cfg_valid):
                        # Latch transaction config
                        self.mode_reg <<= self.cfg_mode
                        self.src_reg <<= self.cfg_src
                        self.dst_reg <<= self.cfg_dst
                        self.len_reg <<= self.cfg_len
                        self.src_addr_reg <<= self.cfg_src_addr
                        self.dst_addr_reg <<= self.cfg_dst_addr
                        self.stride_reg <<= self.cfg_stride
                        self.state <<= CB_READ
                        self.word_cnt <<= 0

                with If(self.state == CB_READ):
                    # Read from source port (dynamic select)
                    self.read_data <<= Select(self.port_rdata._signals, self.src_reg)
                    self.state <<= CB_WRITE

                with If(self.state == CB_WRITE):
                    # Advance addresses based on mode
                    self.word_cnt <<= self.word_cnt + 1
                    with If(self.mode_reg == MODE_BLOCK):
                        self.src_addr_reg <<= self.src_addr_reg + 1
                        self.dst_addr_reg <<= self.dst_addr_reg + 1
                    with If(self.mode_reg == MODE_STRIDE):
                        self.src_addr_reg <<= self.src_addr_reg + self.stride_reg
                        self.dst_addr_reg <<= self.dst_addr_reg + 1
                    with If(self.mode_reg == MODE_BROADCAST):
                        # src_addr stays at base, dst advances
                        self.dst_addr_reg <<= self.dst_addr_reg + 1
                    with If(self.mode_reg == MODE_GATHER):
                        # simplified: same as stride
                        self.src_addr_reg <<= self.src_addr_reg + self.stride_reg
                        self.dst_addr_reg <<= self.dst_addr_reg + 1

                    with If(self.word_cnt + 1 >= self.len_reg):
                        self.state <<= CB_DONE
                    with Else():
                        self.state <<= CB_READ

                with If(self.state == CB_DONE):
                    self.state <<= CB_IDLE

        # =====================================================================
        # Port connections (combinational)
        # =====================================================================
        @self.comb
        def _ports():
            # Default all ports idle
            for p in range(num_ports):
                self.port_valid[p] <<= 0
                self.port_addr[p] <<= 0
                self.port_wdata[p] <<= 0
                self.port_we[p] <<= 0

            # Source port: read request in READ state
            for p in range(num_ports):
                with If((self.state == CB_READ) & (self.src_reg == p)):
                    self.port_valid[p] <<= 1
                    self.port_addr[p] <<= self.src_addr_reg
                    self.port_we[p] <<= 0

            # Destination port: write request in WRITE state
            for p in range(num_ports):
                with If((self.state == CB_WRITE) & (self.dst_reg == p)):
                    self.port_valid[p] <<= 1
                    self.port_addr[p] <<= self.dst_addr_reg
                    self.port_wdata[p] <<= self.read_data
                    self.port_we[p] <<= 1

        # Status
        self.busy <<= (self.state != CB_IDLE)
        self.done <<= (self.state == CB_DONE)
