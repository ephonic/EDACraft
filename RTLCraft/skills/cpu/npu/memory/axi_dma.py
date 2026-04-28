"""
NeuralAccel AXI4 Master DMA Engine

Bridges between NPU internal SRAM (16-bit) and external AXI4 bus (64-bit).
Supports burst transfers with automatic 16-bit <-> 64-bit packing/unpacking.

Features:
  - AXI4 full protocol master (AR/R + AW/W/B channels)
  - Burst up to 16 beats (AXI awlen/arlen max = 15)
  - Per-beat pack/unpack buffer (4 x 16-bit via Array)
  - Single outstanding transaction
  - 64-bit aligned addresses assumed

DMA Control Interface:
  - dma_start   : pulse to start transfer
  - dma_dir     : 0 = LOAD (AXI read -> SRAM write), 1 = STORE (SRAM read -> AXI write)
  - dma_done    : asserted when transfer completes
  - dma_busy    : asserted while active

Configuration (loaded at dma_start):
  - cfg_ext_addr : 32-bit AXI byte address
  - cfg_len      : transfer length in 16-bit words
  - cfg_sram_addr: internal SRAM start address

AXI4 Parameters:
  - ID_WIDTH   = 4
  - ADDR_WIDTH = 32
  - DATA_WIDTH = 64
  - STRB_WIDTH = 8
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Array
from rtlgen.logic import If, Else, Mux


# DMA FSM states
DMA_IDLE = 0
DMA_AR_SEND = 1
DMA_R_RECV = 2
DMA_W_PREP = 3
DMA_AW_SEND = 4
DMA_W_SEND = 5
DMA_B_RECV = 6
DMA_DONE = 7


class AXI4DMA(Module):
    """AXI4 master DMA engine for NeuralAccel NPU."""

    def __init__(
        self,
        data_width: int = 16,
        axi_data_width: int = 64,
        addr_width: int = 32,
        sram_addr_width: int = 8,
        id_width: int = 4,
        name: str = "AXI4DMA",
    ):
        super().__init__(name)
        self.data_width = data_width
        self.axi_data_width = axi_data_width
        self.addr_width = addr_width
        self.sram_addr_width = sram_addr_width
        self.id_width = id_width
        self.words_per_beat = axi_data_width // data_width  # typically 4
        self.beat_cnt_width = 8  # AXI arlen/awlen is 8-bit (up to 256 beats)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # =====================================================================
        # DMA Control Interface
        # =====================================================================
        self.dma_start = Input(1, "dma_start")
        self.dma_dir = Input(1, "dma_dir")  # 0 = LOAD (read), 1 = STORE (write)
        self.dma_done = Output(1, "dma_done")
        self.dma_busy = Output(1, "dma_busy")

        self.cfg_ext_addr = Input(addr_width, "cfg_ext_addr")
        self.cfg_len = Input(16, "cfg_len")  # in 16-bit words
        self.cfg_sram_addr = Input(sram_addr_width, "cfg_sram_addr")

        # =====================================================================
        # Local SRAM Interface (to crossbar / internal memory)
        # =====================================================================
        self.local_req_valid = Output(1, "local_req_valid")
        self.local_req_addr = Output(sram_addr_width, "local_req_addr")
        self.local_req_wdata = Output(data_width, "local_req_wdata")
        self.local_req_we = Output(1, "local_req_we")
        self.local_resp_data = Input(data_width, "local_resp_data")
        self.local_resp_valid = Input(1, "local_resp_valid")

        # =====================================================================
        # AXI4 Read Address Channel (master -> slave)
        # =====================================================================
        self.arid = Output(id_width, "arid")
        self.araddr = Output(addr_width, "araddr")
        self.arlen = Output(8, "arlen")
        self.arsize = Output(3, "arsize")
        self.arburst = Output(2, "arburst")
        self.arvalid = Output(1, "arvalid")
        self.arready = Input(1, "arready")

        # =====================================================================
        # AXI4 Read Data Channel (slave -> master)
        # =====================================================================
        self.rid = Input(id_width, "rid")
        self.rdata = Input(axi_data_width, "rdata")
        self.rresp = Input(2, "rresp")
        self.rlast = Input(1, "rlast")
        self.rvalid = Input(1, "rvalid")
        self.rready = Output(1, "rready")

        # =====================================================================
        # AXI4 Write Address Channel (master -> slave)
        # =====================================================================
        self.awid = Output(id_width, "awid")
        self.awaddr = Output(addr_width, "awaddr")
        self.awlen = Output(8, "awlen")
        self.awsize = Output(3, "awsize")
        self.awburst = Output(2, "awburst")
        self.awvalid = Output(1, "awvalid")
        self.awready = Input(1, "awready")

        # =====================================================================
        # AXI4 Write Data Channel (master -> slave)
        # =====================================================================
        self.wdata = Output(axi_data_width, "wdata")
        self.wstrb = Output(axi_data_width // 8, "wstrb")
        self.wlast = Output(1, "wlast")
        self.wvalid = Output(1, "wvalid")
        self.wready = Input(1, "wready")

        # =====================================================================
        # AXI4 Write Response Channel (slave -> master)
        # =====================================================================
        self.bid = Input(id_width, "bid")
        self.bresp = Input(2, "bresp")
        self.bvalid = Input(1, "bvalid")
        self.bready = Output(1, "bready")

        # =====================================================================
        # Internal State
        # =====================================================================
        self.state = Reg(3, "state")

        # Latched config
        self.ext_addr_r = Reg(addr_width, "ext_addr_r")
        self.len_r = Reg(16, "len_r")
        self.sram_addr_r = Reg(sram_addr_width, "sram_addr_r")

        # Counters
        self.beat_cnt = Reg(self.beat_cnt_width, "beat_cnt")
        self.total_beats = Reg(self.beat_cnt_width, "total_beats")
        self.word_cnt = Reg(16, "word_cnt")

        # Pack/unpack buffer using rtlgen Array (supports dynamic indexing)
        self.buf = Array(data_width, self.words_per_beat, "buf", vtype=Reg)
        self.buf_idx = Reg(2, "buf_idx")  # read or write index within buffer
        self.buf_valid = Reg(1, "buf_valid")
        self.rlast_flag = Reg(1, "rlast_flag")
        self.beat_words_r = Reg(3, "beat_words_r")  # latched beat_words for current beat

        # =====================================================================
        # Combinational helpers
        # =====================================================================
        self.words_rem = Wire(16, "words_rem")
        self.beat_words = Wire(3, "beat_words")
        self.all_done = Wire(1, "all_done")

        @self.comb
        def _helpers():
            self.words_rem <<= self.len_r - self.word_cnt
            # Number of words in current beat: min(remaining, words_per_beat)
            rem_lt_wp = self.words_rem < self.words_per_beat
            self.beat_words <<= Mux(rem_lt_wp, self.words_rem[2:0], self.words_per_beat)
            self.all_done <<= self.word_cnt >= self.len_r

        # =====================================================================
        # FSM Sequential Logic
        # =====================================================================
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm_seq():
            with If(self.rst_n == 0):
                self.state <<= DMA_IDLE
                self.ext_addr_r <<= 0
                self.len_r <<= 0
                self.sram_addr_r <<= 0
                self.beat_cnt <<= 0
                self.total_beats <<= 0
                self.word_cnt <<= 0
                self.buf_idx <<= 0
                self.buf_valid <<= 0
                self.rlast_flag <<= 0
                for i in range(self.words_per_beat):
                    self.buf[i] <<= 0
            with Else():
                with If(self.state == DMA_IDLE):
                    with If(self.dma_start):
                        self.ext_addr_r <<= self.cfg_ext_addr
                        self.len_r <<= self.cfg_len
                        self.sram_addr_r <<= self.cfg_sram_addr
                        self.beat_cnt <<= 0
                        self.word_cnt <<= 0
                        self.buf_idx <<= 0
                        self.buf_valid <<= 0
                        self.rlast_flag <<= 0
                        # total_beats = ceil(len / words_per_beat)
                        self.total_beats <<= (self.cfg_len + (self.words_per_beat - 1)) >> 2
                        with If(self.dma_dir == 0):
                            self.state <<= DMA_AR_SEND
                        with Else():
                            self.state <<= DMA_W_PREP
                            # beat_words for first beat = min(cfg_len, words_per_beat)
                            # Use cfg_len directly because word_cnt hasn't cleared yet in comb eval
                            rem_lt_wp = self.cfg_len < self.words_per_beat
                            self.beat_words_r <<= Mux(rem_lt_wp, self.cfg_len[2:0], self.words_per_beat)

                # -----------------------------------------------------------------
                # READ: send AR
                # -----------------------------------------------------------------
                with If(self.state == DMA_AR_SEND):
                    with If(self.arvalid & self.arready):
                        self.state <<= DMA_R_RECV
                        self.beat_cnt <<= 0

                # -----------------------------------------------------------------
                # READ: receive R beats and drain to SRAM
                # -----------------------------------------------------------------
                with If(self.state == DMA_R_RECV):
                    # Case 1: accept new AXI read beat when buffer is free
                    with If(self.rvalid & self.rready & ~self.buf_valid):
                        for i in range(self.words_per_beat):
                            lo = i * self.data_width
                            hi = lo + self.data_width - 1
                            self.buf[i] <<= self.rdata[hi:lo]
                        self.buf_valid <<= 1
                        self.rlast_flag <<= self.rlast
                        self.beat_cnt <<= self.beat_cnt + 1
                        self.buf_idx <<= 0
                        self.beat_words_r <<= self.beat_words

                    # Case 2: drain one buffered word to SRAM per cycle
                    with If(self.buf_valid & self.local_req_valid):
                        self.buf_idx <<= self.buf_idx + 1
                        self.word_cnt <<= self.word_cnt + 1
                        self.sram_addr_r <<= self.sram_addr_r + 1
                        with If(self.buf_idx + 1 >= self.beat_words_r):
                            self.buf_valid <<= 0
                            with If(self.rlast_flag):
                                self.state <<= DMA_DONE

                # -----------------------------------------------------------------
                # WRITE: read words from SRAM into buffer
                # -----------------------------------------------------------------
                with If(self.state == DMA_W_PREP):
                    with If(self.local_req_valid & self.local_resp_valid):
                        self.buf[self.buf_idx] <<= self.local_resp_data
                        self.buf_idx <<= self.buf_idx + 1
                        self.word_cnt <<= self.word_cnt + 1
                        self.sram_addr_r <<= self.sram_addr_r + 1
                        with If(self.buf_idx + 1 >= self.beat_words_r):
                            self.buf_valid <<= 1
                            self.buf_idx <<= 0
                            self.state <<= DMA_AW_SEND

                # -----------------------------------------------------------------
                # WRITE: send AW
                # -----------------------------------------------------------------
                with If(self.state == DMA_AW_SEND):
                    with If(self.awvalid & self.awready):
                        self.state <<= DMA_W_SEND

                # -----------------------------------------------------------------
                # WRITE: send W beat
                # -----------------------------------------------------------------
                with If(self.state == DMA_W_SEND):
                    with If(self.wvalid & self.wready):
                        self.beat_cnt <<= self.beat_cnt + 1
                        with If(self.wlast):
                            self.state <<= DMA_B_RECV
                        with Else():
                            self.buf_valid <<= 0
                            self.state <<= DMA_W_PREP
                            self.beat_words_r <<= self.beat_words

                # -----------------------------------------------------------------
                # WRITE: receive B response
                # -----------------------------------------------------------------
                with If(self.state == DMA_B_RECV):
                    with If(self.bvalid & self.bready):
                        self.state <<= DMA_DONE

                # -----------------------------------------------------------------
                # DONE
                # -----------------------------------------------------------------
                with If(self.state == DMA_DONE):
                    self.state <<= DMA_IDLE

        # =====================================================================
        # AXI4 Output Combinational Logic
        # =====================================================================
        @self.comb
        def _axi_outputs():
            # Defaults: all idle
            self.arvalid <<= 0
            self.arid <<= 0
            self.araddr <<= 0
            self.arlen <<= 0
            self.arsize <<= 0
            self.arburst <<= 0
            self.rready <<= 0

            self.awvalid <<= 0
            self.awid <<= 0
            self.awaddr <<= 0
            self.awlen <<= 0
            self.awsize <<= 0
            self.awburst <<= 0
            self.wvalid <<= 0
            self.wdata <<= 0
            self.wstrb <<= 0
            self.wlast <<= 0
            self.bready <<= 0

            # Read Address
            with If(self.state == DMA_AR_SEND):
                self.arvalid <<= 1
                self.arid <<= 0
                self.araddr <<= self.ext_addr_r
                self.arlen <<= self.total_beats - 1
                self.arsize <<= 0b011  # 8 bytes (64 bits)
                self.arburst <<= 0b01  # INCR

            # Read Data: ready when buffer is empty
            with If(self.state == DMA_R_RECV):
                self.rready <<= ~self.buf_valid

            # Write Address
            with If(self.state == DMA_AW_SEND):
                self.awvalid <<= 1
                self.awid <<= 0
                self.awaddr <<= self.ext_addr_r
                self.awlen <<= self.total_beats - 1
                self.awsize <<= 0b011  # 8 bytes
                self.awburst <<= 0b01  # INCR

            # Write Data
            with If(self.state == DMA_W_SEND):
                self.wvalid <<= 1
                # Pack buffer words into 64-bit wdata using Mux chain
                wdata_val = 0
                for i in range(self.words_per_beat):
                    wdata_val = wdata_val | (self.buf[i] << (i * self.data_width))
                self.wdata <<= wdata_val
                # wlast on last beat (beat_cnt is #beats already sent)
                self.wlast <<= (self.beat_cnt + 1 >= self.total_beats)
                # wstrb: all bytes valid for full beats; partial on last if unaligned
                self.wstrb <<= 0xFF

            # Write Response
            with If(self.state == DMA_B_RECV):
                self.bready <<= 1

        # =====================================================================
        # Local SRAM Interface Combinational Logic
        # =====================================================================
        @self.comb
        def _local_outputs():
            # Default idle
            self.local_req_valid <<= 0
            self.local_req_addr <<= 0
            self.local_req_wdata <<= 0
            self.local_req_we <<= 0

            # LOAD: drain buffer to SRAM (write)
            with If(self.state == DMA_R_RECV):
                with If(self.buf_valid & (self.buf_idx < self.beat_words_r)):
                    self.local_req_valid <<= 1
                    self.local_req_addr <<= self.sram_addr_r
                    # Read from buf array using dynamic index
                    self.local_req_wdata <<= self.buf[self.buf_idx]
                    self.local_req_we <<= 1

            # STORE: read SRAM into buffer
            with If(self.state == DMA_W_PREP):
                with If(self.buf_idx < self.beat_words_r):
                    self.local_req_valid <<= 1
                    self.local_req_addr <<= self.sram_addr_r
                    self.local_req_we <<= 0

        # =====================================================================
        # Status Outputs
        # =====================================================================
        self.dma_done <<= (self.state == DMA_DONE)
        self.dma_busy <<= (self.state != DMA_IDLE)
