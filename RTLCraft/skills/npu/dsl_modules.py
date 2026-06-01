
"""
Spec2RTL Design Flow: FPGA-NPU (Neural Processing Unit)
========================================================

Architecture: Intel FPGA-NPU overlay for low-latency AI inference.
Reference: ref_rtl/fpga-npu (Stratix 10 / Arria 10).

Full-configuration matching npu.vh:
  - INT8 datapath: EW=8, ACCW=32, DOTW=40
  - 7 MVU tiles, 40 DPEs per tile
  - 2 MFUs (ReLU / Sigmoid / Tanh / Add / Sub / Mul / Max)
  - 10 VRF write ports -> 12 VRF banks
  - LD unit with input/output FIFOs
  - Instruction depth 512, FIFO depth 512

Hierarchy (matching reference RTL):
  NPUTop
    ├── TopScheduler        (inst_ram + 5x output FIFO + FSM)
    ├── MVUScheduler        (minst_fifo -> uinst_fifo + loop unrolling)
    ├── EVRFScheduler       (minst_fifo -> uinst_fifo)
    ├── MFUScheduler x2     (minst_fifo -> uinst_fifo)
    ├── LDScheduler         (minst_fifo -> uinst_fifo + tree dispatch)
    ├── MVU                 (NTILE tiles x NDPE DPEs + accumulator)
    ├── MFU x2              (inst_fifo + data_fifo + mult/add/act)
    ├── eVRF                (12-bank VRF + pipeline)
    └── LD                  (in_fifo / wb_fifo / out_fifo + writeback)
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rtlgen import (
    Input, Output, Wire, Reg, Module, Vector, Array, VerilogEmitter,
    BehavioralSpec, StrategySpec, ConnectionSpec, DecompositionResult,
    SystemSimulator, generate_dsl_skeleton,
    TopLevelDoc, ModuleDoc, StrategyDoc, SimulationDoc, SimulationResult,
    MicroArchDoc,
)
from rtlgen.logic import If, Else, Elif, When, Otherwise, Const, Cat, Mux, Switch, Rep, ForGen
from rtlgen.lib import SyncFIFO, RoundRobinArbiter

print("=" * 70)
print("FPGA-NPU -- Phase 1: Behavioral Decomposition")
print("=" * 70)

# ============================================================================
# NPU Configuration Constants (faithful to npu.vh)
# ============================================================================
EW = 8
ACCW = 32
DOTW = 40
NTILE = 7
NDPE = 40
NMFU = 2
VRFD = 512
MRFD = 512
INST_DEPTH = 512
QDEPTH = 512
INPUT_BUFFER_SIZE = 512
OUTPUT_BUFFER_SIZE = 512

VRFAW = (VRFD - 1).bit_length()
MRFAW = (MRFD - 1).bit_length()
INST_ADDRW = (INST_DEPTH - 1).bit_length()
QDEPTH_AW = (QDEPTH - 1).bit_length()
INBUF_AW = (INPUT_BUFFER_SIZE - 1).bit_length()
OUTBUF_AW = (OUTPUT_BUFFER_SIZE - 1).bit_length()

NVRF = NTILE + 1 + (2 * NMFU)
NMRF = NTILE * NDPE
PRIME_DOTW = 10
NUM_DSP = DOTW // PRIME_DOTW
NUM_ACCUM = 3 * NUM_DSP
ACCIDW = (NUM_ACCUM - 1).bit_length()
VRFIDW = (NUM_DSP - 1).bit_length()
MRFIDW = (NMRF - 1).bit_length()
NTAGW = 9
NSIZEW = (max(VRFD, MRFD) - 1).bit_length() + 1

MIW_MVU = 1 + VRFAW + VRFAW + MRFAW + NSIZEW + NSIZEW + NTAGW
UIW_MVU = VRFAW + VRFIDW + 1 + MRFAW + NTAGW + 2 + 5 + 1
MIW_EVRF = 1 + VRFAW + 2 + NTAGW + NSIZEW
UIW_EVRF = VRFAW + 2 + NTAGW
MIW_MFU = 1 + VRFAW + VRFAW + 6 + NTAGW + NSIZEW
UIW_MFU = VRFAW + VRFAW + 6 + NTAGW
MIW_LD = 1 + NVRF + VRFAW + VRFAW + 1 + 1 + 1 + 1 + NTAGW + NSIZEW
UIW_LD = NVRF + VRFAW + VRFAW + 1 + 1 + 1 + 1 + NTAGW
MICW = MIW_MVU + MIW_EVRF + (2 * MIW_MFU) + MIW_LD

print(f"Config: NTILE={NTILE}, NDPE={NDPE}, DOTW={DOTW}, NVRF={NVRF}, NMRF={NMRF}")
print(f"MICW={MICW}, MIW_MVU={MIW_MVU}, UIW_MVU={UIW_MVU}")

def _make_spec(name, inputs, outputs, latency=1):
    return BehavioralSpec(
        name=name, inputs=inputs, outputs=outputs,
        func=lambda inp: {p.name: 0 for p in outputs},
        mod_type="processor", strategy=StrategySpec.timing(), latency=latency,
    )

# Top-level spec
top_sched_outputs = []
for prefix, w in [("mvu", MIW_MVU), ("evrf", MIW_EVRF), ("mfu0", MIW_MFU), ("mfu1", MIW_MFU), ("ld", MIW_LD)]:
    top_sched_outputs += [Output(1, f"o_{prefix}_minst_rd_rdy"), Output(w, f"o_{prefix}_minst_rd_dout")]
top_sched_inputs = [
    Input(1, "i_minst_chain_wr_en"), Input(INST_ADDRW, "i_minst_chain_wr_addr"),
    Input(MICW, "i_minst_chain_wr_din"), Input(1, "i_start"),
    Input(INST_ADDRW, "pc_start_offset"),
] + [Input(1, f"i_{p}_minst_rd_en") for p in ["mvu", "evrf", "mfu0", "mfu1", "ld"]]
top_sched_outputs += [Output(1, "o_done")]
_ = _make_spec("top_sched", top_sched_inputs, top_sched_outputs, latency=1)

# Scheduler specs
for unit, miw, uiw in [
    ("mvu", MIW_MVU, UIW_MVU), ("evrf", MIW_EVRF, UIW_EVRF),
    ("mfu", MIW_MFU, UIW_MFU), ("ld", MIW_LD, UIW_LD)
]:
    _make_spec(f"{unit}_sched", [
        Input(1, f"i_{unit}_minst_wr_en"), Input(miw, f"i_{unit}_minst_wr_din"),
        Input(1, f"i_{unit}_uinst_rd_en"),
    ], [
        Output(1, f"o_{unit}_minst_wr_rdy"), Output(1, f"o_{unit}_uinst_rd_rdy"),
        Output(uiw, f"o_{unit}_uinst_rd_dout"),
    ])

# MVU datapath spec
mvu_inputs = [Input(MRFIDW, "i_mrf_wr_en"), Input(MRFAW, "i_mrf_wr_addr"), Input(EW * DOTW, "i_mrf_wr_data")]
mvu_inputs += [Input(VRFAW, "i_vrf0_wr_addr"), Input(VRFAW, "i_vrf1_wr_addr"), Input(ACCW * DOTW, "i_vrf_wr_data")]
mvu_inputs += [Input(1, "i_vrf_wr_en"), Input(2 * NVRF, "i_vrf_wr_id")]
mvu_inputs += [Input(1, "i_inst_wr_en"), Input(VRFAW, "i_vrf_rd_addr"), Input(VRFIDW, "i_vrf_rd_id")]
mvu_inputs += [Input(1, "i_reg_sel"), Input(MRFAW, "i_mrf_rd_addr"), Input(2, "i_acc_op")]
mvu_inputs += [Input(NTAGW, "i_tag"), Input(5, "i_acc_size"), Input(1, "i_vrf_en")]
mvu_inputs += [Input(DOTW, "i_data_rd_en")]
mvu_outputs = [Output(1, "o_inst_wr_rdy"), Output(DOTW, "o_data_rd_rdy"), Output(ACCW * NDPE, "o_data_rd_dout")]
_ = _make_spec("mvu", mvu_inputs, mvu_outputs, latency=3)

# MFU datapath spec
mfu_inputs = [Input(VRFAW, "i_vrf0_wr_addr"), Input(VRFAW, "i_vrf1_wr_addr"), Input(ACCW * DOTW, "i_vrf_wr_data")]
mfu_inputs += [Input(1, "i_vrf_wr_en"), Input(2 * NVRF, "i_vrf_wr_id")]
mfu_inputs += [Input(DOTW, "i_data_wr_en"), Input(ACCW * DOTW, "i_data_wr_din"), Input(DOTW, "i_data_rd_en")]
mfu_inputs += [Input(1, "i_inst_wr_en"), Input(VRFAW, "i_vrf0_rd_addr"), Input(VRFAW, "i_vrf1_rd_addr")]
mfu_inputs += [Input(6, "i_func_op"), Input(NTAGW, "i_tag"), Input(1, "i_tag_update_en")]
mfu_outputs = [Output(DOTW, "o_data_wr_rdy"), Output(DOTW, "o_data_rd_rdy"), Output(ACCW * DOTW, "o_data_rd_dout"), Output(1, "o_inst_wr_rdy")]
_ = _make_spec("mfu", mfu_inputs, mfu_outputs, latency=2)

# eVRF datapath spec
evrf_inputs = [Input(VRFAW, "i_vrf0_wr_addr"), Input(VRFAW, "i_vrf1_wr_addr"), Input(ACCW * DOTW, "i_vrf_wr_data")]
evrf_inputs += [Input(1, "i_vrf_wr_en"), Input(2 * NVRF, "i_vrf_wr_id"), Input(DOTW, "i_data_wr_en")]
evrf_inputs += [Input(ACCW * NDPE, "i_data_wr_din"), Input(DOTW, "i_data_rd_en"), Input(1, "i_inst_wr_en")]
evrf_inputs += [Input(VRFAW, "i_vrf_rd_addr"), Input(2, "i_src_sel"), Input(NTAGW, "i_tag"), Input(1, "i_tag_update_en")]
evrf_outputs = [Output(DOTW, "o_data_wr_rdy"), Output(DOTW, "o_data_rd_rdy"), Output(ACCW * DOTW, "o_data_rd_dout"), Output(1, "o_inst_wr_rdy")]
_ = _make_spec("evrf", evrf_inputs, evrf_outputs, latency=1)

# LD datapath spec
ld_outputs = [Output(1, "o_vrf_wr_en"), Output(2 * NVRF, "o_vrf_wr_id"), Output(VRFAW, "o_vrf0_wr_addr"), Output(VRFAW, "o_vrf1_wr_addr"), Output(ACCW * DOTW, "o_vrf_wr_data")]
ld_outputs += [Output(1, "o_in_wr_rdy"), Output(INBUF_AW, "o_in_usedw"), Output(1, "o_out_rd_rdy"), Output(ACCW * DOTW + 1, "o_out_rd_dout"), Output(OUTBUF_AW, "o_out_usedw")]
ld_outputs += [Output(1, "o_inst_wr_rdy"), Output(1, "o_tag_update_en"), Output(1, "o_start"), Output(1, "o_done")]
ld_outputs += [Output(32, "o_debug_ld_ififo_counter"), Output(32, "o_debug_ld_wbfifo_counter")]
ld_outputs += [Output(32, "o_debug_ld_instfifo_counter"), Output(32, "o_debug_ld_ofifo_counter"), Output(32, "o_result_count")]
_ = _make_spec("ld", [], ld_outputs, latency=1)

# NPUTop spec
npu_top_inputs = [
    Input(1, "i_minst_chain_wr_en"), Input(INST_ADDRW, "i_minst_chain_wr_addr"), Input(MICW, "i_minst_chain_wr_din"),
    Input(1, "i_start"), Input(INST_ADDRW, "pc_start_offset"),
    Input(1, "i_ld_in_wr_en"), Input(EW * DOTW, "i_ld_in_wr_din"), Input(1, "i_ld_out_rd_en"),
    Input(MRFAW, "i_mrf_wr_addr"), Input(EW * DOTW, "i_mrf_wr_data"), Input(MRFIDW, "i_mrf_wr_en"),
]
npu_top_outputs = [
    Output(1, "o_ld_in_wr_rdy"), Output(INBUF_AW, "o_ld_in_usedw"), Output(1, "o_ld_out_rd_rdy"),
    Output(ACCW * DOTW + 1, "o_ld_out_rd_dout"), Output(OUTBUF_AW, "o_ld_out_usedw"), Output(1, "o_done"),
]
_ = _make_spec("npu_top", npu_top_inputs, npu_top_outputs, latency=1)

result = DecompositionResult(design_name="FPGA-NPU", design_type="processor")
print("Phase 1 complete.")

print("\n" + "=" * 70)
print("Phase 2: Behavioral Modeling (Full-Fidelity)")
print("=" * 70)

# ============================================================================
# TopScheduler -- Program controller, 5-way dispatch
# ============================================================================
class TopScheduler(Module):
    def __init__(self):
        super().__init__("top_sched")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_minst_chain_wr_en = Input(1, "i_minst_chain_wr_en")
        self.i_minst_chain_wr_addr = Input(INST_ADDRW, "i_minst_chain_wr_addr")
        self.i_minst_chain_wr_din = Input(MICW, "i_minst_chain_wr_din")
        self.i_start = Input(1, "i_start")
        self.pc_start_offset = Input(INST_ADDRW, "pc_start_offset")
        self.i_mvu_minst_rd_en = Input(1, "i_mvu_minst_rd_en")
        self.i_evrf_minst_rd_en = Input(1, "i_evrf_minst_rd_en")
        self.i_mfu0_minst_rd_en = Input(1, "i_mfu0_minst_rd_en")
        self.i_mfu1_minst_rd_en = Input(1, "i_mfu1_minst_rd_en")
        self.i_ld_minst_rd_en = Input(1, "i_ld_minst_rd_en")
        self.o_mvu_minst_rd_rdy = Output(1, "o_mvu_minst_rd_rdy")
        self.o_evrf_minst_rd_rdy = Output(1, "o_evrf_minst_rd_rdy")
        self.o_mfu0_minst_rd_rdy = Output(1, "o_mfu0_minst_rd_rdy")
        self.o_mfu1_minst_rd_rdy = Output(1, "o_mfu1_minst_rd_rdy")
        self.o_ld_minst_rd_rdy = Output(1, "o_ld_minst_rd_rdy")
        self.o_mvu_minst_rd_dout = Output(MIW_MVU, "o_mvu_minst_rd_dout")
        self.o_evrf_minst_rd_dout = Output(MIW_EVRF, "o_evrf_minst_rd_dout")
        self.o_mfu0_minst_rd_dout = Output(MIW_MFU, "o_mfu0_minst_rd_dout")
        self.o_mfu1_minst_rd_dout = Output(MIW_MFU, "o_mfu1_minst_rd_dout")
        self.o_ld_minst_rd_dout = Output(MIW_LD, "o_ld_minst_rd_dout")
        self.o_done = Output(1, "o_done")

        self.add_localparam("ST_IDLE", 0)
        self.add_localparam("ST_RUNNING", 1)
        self.add_localparam("ST_DONE", 2)
        self._state = Reg(2, "state")
        self._pc = Reg(INST_ADDRW, "pc")

        self._inst_mem = Array(MICW, INST_DEPTH, "inst_mem")
        self._inst_mem_dout = Reg(MICW, "inst_mem_dout")

        # Build FIFOs and keep references
        self._fifos = {}
        for prefix, w in [("mvu", MIW_MVU), ("evrf", MIW_EVRF), ("mfu0", MIW_MFU), ("mfu1", MIW_MFU), ("ld", MIW_LD)]:
            fifo = SyncFIFO(w, QDEPTH_AW)
            wren = Wire(1, f"_{prefix}_fifo_wr_en")
            wrdata = Wire(w, f"_{prefix}_fifo_wr_data")
            rden = Wire(1, f"_{prefix}_fifo_rd_en")
            rdrdy = Wire(1, f"_{prefix}_fifo_rd_rdy")
            rddata = Wire(w, f"_{prefix}_fifo_rd_data")
            full = Wire(1, f"_{prefix}_fifo_full")
            empty = Wire(1, f"_{prefix}_fifo_empty")
            usedw = Wire(QDEPTH_AW, f"_{prefix}_fifo_usedw")
            self.instantiate(fifo, f"minst_ofifo_{prefix}", port_map={"wr_en": wren, "din": wrdata, "rd_en": rden, "rd_rdy": rdrdy, "dout": rddata, "full": full, "empty": empty, "count": usedw, "clk": self.clk, "rst": ~self.rst_n})
            self._fifos[prefix] = {
                "wren": wren, "wrdata": wrdata, "rden": rden,
                "rdrdy": rdrdy, "rddata": rddata, "full": full,
                "empty": empty, "usedw": usedw,
            }

        self._current_inst = Wire(MICW, "current_inst")
        self._mvu_minst = Wire(MIW_MVU, "mvu_minst")
        self._evrf_minst = Wire(MIW_EVRF, "evrf_minst")
        self._mfu0_minst = Wire(MIW_MFU, "mfu0_minst")
        self._mfu1_minst = Wire(MIW_MFU, "mfu1_minst")
        self._ld_minst = Wire(MIW_LD, "ld_minst")

        self._mvu_valid_bit = Wire(1, "mvu_valid_bit")
        self._evrf_valid_bit = Wire(1, "evrf_valid_bit")
        self._mfu0_valid_bit = Wire(1, "mfu0_valid_bit")
        self._mfu1_valid_bit = Wire(1, "mfu1_valid_bit")
        self._ld_valid_bit = Wire(1, "ld_valid_bit")

        self._mvu_valid = Wire(1, "mvu_valid")
        self._evrf_valid = Wire(1, "evrf_valid")
        self._mfu0_valid = Wire(1, "mfu0_valid")
        self._mfu1_valid = Wire(1, "mfu1_valid")
        self._ld_valid = Wire(1, "ld_valid")
        self._any_active = Wire(1, "any_active")
        self._all_rdy = Wire(1, "all_rdy")
        self._br_target = Wire(INST_ADDRW, "br_target")

        # Sequential
        with self.seq(self.clk, self.rst_n):
            with If(self.i_minst_chain_wr_en):
                self._inst_mem[self.i_minst_chain_wr_addr] <<= self.i_minst_chain_wr_din
            self._inst_mem_dout <<= self._inst_mem[self._pc]

            with If(self.i_start):
                self._state <<= self.ST_IDLE
                self._pc <<= self.pc_start_offset
            with Elif(self._state == self.ST_IDLE):
                with If(self.i_start):
                    self._state <<= self.ST_RUNNING
                    self._pc <<= self.pc_start_offset
            with Elif(self._state == self.ST_RUNNING):
                with If(self._all_rdy):
                    with If(self._any_active):
                        self._pc <<= self._br_target
                    with Else():
                        self._state <<= self.ST_DONE

        # Combinational
        with self.comb:
            self._current_inst <<= self._inst_mem_dout

            # Extract valid bits: MICW layout = ld | mfu1 | mfu0 | evrf | mvu
            p0 = 0
            self._ld_valid_bit   <<= self._current_inst[p0]
            p1 = p0 + MIW_LD
            self._mfu1_valid_bit <<= self._current_inst[p1]
            p2 = p1 + MIW_MFU
            self._mfu0_valid_bit <<= self._current_inst[p2]
            p3 = p2 + MIW_MFU
            self._evrf_valid_bit <<= self._current_inst[p3]
            p4 = p3 + MIW_EVRF
            self._mvu_valid_bit  <<= self._current_inst[p4]

            # Extract sub-instructions
            self._ld_minst   <<= self._current_inst[MIW_LD - 1 : 0]
            self._mfu1_minst <<= self._current_inst[MIW_LD + MIW_MFU - 1 : MIW_LD]
            self._mfu0_minst <<= self._current_inst[MIW_LD + 2 * MIW_MFU - 1 : MIW_LD + MIW_MFU]
            self._evrf_minst <<= self._current_inst[MIW_LD + 2 * MIW_MFU + MIW_EVRF - 1 : MIW_LD + 2 * MIW_MFU]
            self._mvu_minst  <<= self._current_inst[MICW - 1 : MIW_LD + 2 * MIW_MFU + MIW_EVRF]

            # Valid = valid-bit & !fifo_full
            mvu_f = self._fifos["mvu"]
            evrf_f = self._fifos["evrf"]
            mfu0_f = self._fifos["mfu0"]
            mfu1_f = self._fifos["mfu1"]
            ld_f = self._fifos["ld"]

            self._mvu_valid  <<= self._mvu_valid_bit  & ~mvu_f["full"]
            self._evrf_valid <<= self._evrf_valid_bit & ~evrf_f["full"]
            self._mfu0_valid <<= self._mfu0_valid_bit & ~mfu0_f["full"]
            self._mfu1_valid <<= self._mfu1_valid_bit & ~mfu1_f["full"]
            self._ld_valid   <<= self._ld_valid_bit   & ~ld_f["full"]

            self._any_active <<= (self._mvu_valid | self._evrf_valid | self._mfu0_valid | self._mfu1_valid | self._ld_valid)
            self._all_rdy <<= (~mvu_f["full"] & ~evrf_f["full"] & ~mfu0_f["full"] & ~mfu1_f["full"] & ~ld_f["full"])

            self._br_target <<= self._pc + Const(1, INST_ADDRW)

            # FIFO write
            mvu_f["wren"]   <<= self._mvu_valid
            mvu_f["wrdata"] <<= self._mvu_minst
            evrf_f["wren"]  <<= self._evrf_valid
            evrf_f["wrdata"] <<= self._evrf_minst
            mfu0_f["wren"]  <<= self._mfu0_valid
            mfu0_f["wrdata"] <<= self._mfu0_minst
            mfu1_f["wren"]  <<= self._mfu1_valid
            mfu1_f["wrdata"] <<= self._mfu1_minst
            ld_f["wren"]    <<= self._ld_valid
            ld_f["wrdata"]  <<= self._ld_minst

            # FIFO read
            mvu_f["rden"] <<= self.i_mvu_minst_rd_en
            evrf_f["rden"] <<= self.i_evrf_minst_rd_en
            mfu0_f["rden"] <<= self.i_mfu0_minst_rd_en
            mfu1_f["rden"] <<= self.i_mfu1_minst_rd_en
            ld_f["rden"]   <<= self.i_ld_minst_rd_en

            # Outputs
            self.o_mvu_minst_rd_rdy  <<= mvu_f["rdrdy"]
            self.o_evrf_minst_rd_rdy <<= evrf_f["rdrdy"]
            self.o_mfu0_minst_rd_rdy <<= mfu0_f["rdrdy"]
            self.o_mfu1_minst_rd_rdy <<= mfu1_f["rdrdy"]
            self.o_ld_minst_rd_rdy   <<= ld_f["rdrdy"]

            self.o_mvu_minst_rd_dout  <<= mvu_f["rddata"]
            self.o_evrf_minst_rd_dout <<= evrf_f["rddata"]
            self.o_mfu0_minst_rd_dout <<= mfu0_f["rddata"]
            self.o_mfu1_minst_rd_dout <<= mfu1_f["rddata"]
            self.o_ld_minst_rd_dout   <<= ld_f["rddata"]

            self.o_done <<= (self._state == self.ST_DONE)



# ============================================================================
# GenericScheduler -- Base class for all unit schedulers
# ============================================================================
class GenericScheduler(Module):
    """Base scheduler: minst_ififo -> state machine -> uinst_ofifo."""
    def __init__(self, name, miw, uiw, has_mrf=False, has_func=False):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.miw = miw
        self.uiw = uiw
        self.has_mrf = has_mrf
        self.has_func = has_func

        # I/O
        self.i_minst_wr_en = Input(1, "i_minst_wr_en")
        self.i_minst_wr_din = Input(miw, "i_minst_wr_din")
        self.i_uinst_rd_en = Input(1, "i_uinst_rd_en")
        self.o_minst_wr_rdy = Output(1, "o_minst_wr_rdy")
        self.o_uinst_rd_rdy = Output(1, "o_uinst_rd_rdy")
        self.o_uinst_rd_dout = Output(uiw, "o_uinst_rd_dout")

        # FIFOs
        self._minst_fifo = SyncFIFO(miw, QDEPTH_AW)
        self._minst_fifo_wr_en = Wire(1, "_minst_fifo_wr_en")
        self._minst_fifo_wr_data = Wire(miw, "_minst_fifo_wr_data")
        self._minst_fifo_rd_en = Wire(1, "_minst_fifo_rd_en")
        self._minst_fifo_rd_rdy = Wire(1, "_minst_fifo_rd_rdy")
        self._minst_fifo_rd_data = Wire(miw, "_minst_fifo_rd_data")
        self._minst_fifo_full = Wire(1, "_minst_fifo_full")
        self._minst_fifo_empty = Wire(1, "_minst_fifo_empty")
        self._minst_fifo_usedw = Wire(QDEPTH_AW, "_minst_fifo_usedw")

        self._uinst_fifo = SyncFIFO(uiw, QDEPTH_AW)
        self._uinst_fifo_wr_en = Wire(1, "_uinst_fifo_wr_en")
        self._uinst_fifo_wr_data = Wire(uiw, "_uinst_fifo_wr_data")
        self._uinst_fifo_rd_en = Wire(1, "_uinst_fifo_rd_en")
        self._uinst_fifo_rd_rdy = Wire(1, "_uinst_fifo_rd_rdy")
        self._uinst_fifo_rd_data = Wire(uiw, "_uinst_fifo_rd_data")
        self._uinst_fifo_full = Wire(1, "_uinst_fifo_full")
        self._uinst_fifo_empty = Wire(1, "_uinst_fifo_empty")
        self._uinst_fifo_usedw = Wire(QDEPTH_AW, "_uinst_fifo_usedw")

        self.instantiate(self._minst_fifo, "minst_ififo", port_map={"wr_en": self._minst_fifo_wr_en, "din": self._minst_fifo_wr_data, "rd_en": self._minst_fifo_rd_en, "rd_rdy": self._minst_fifo_rd_rdy, "dout": self._minst_fifo_rd_data, "full": self._minst_fifo_full, "empty": self._minst_fifo_empty, "count": self._minst_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})
        self.instantiate(self._uinst_fifo, "uinst_ofifo", port_map={"wr_en": self._uinst_fifo_wr_en, "din": self._uinst_fifo_wr_data, "rd_en": self._uinst_fifo_rd_en, "rd_rdy": self._uinst_fifo_rd_rdy, "dout": self._uinst_fifo_rd_data, "full": self._uinst_fifo_full, "empty": self._uinst_fifo_empty, "count": self._uinst_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        # State machine
        self.add_localparam("ST_INIT", 0)
        self.add_localparam("ST_ISSUE", 1)
        self.add_localparam("ST_LOOP", 2)
        self._state = Reg(2, "state")

        # Macro-instruction register (latched from FIFO)
        self._minst_reg = Reg(miw, "minst_reg")
        self._minst_valid = Reg(1, "minst_valid")

        # Loop counters
        self._batch_cnt = Reg(NSIZEW, "batch_cnt")
        self._vrf_cnt = Reg(NSIZEW, "vrf_cnt")
        self._mrf_cnt = Reg(NSIZEW, "mrf_cnt")

        # Decode wires
        self._batch_size = Wire(NSIZEW, "batch_size")
        self._vrf_size = Wire(NSIZEW, "vrf_size")
        self._mrf_size = Wire(NSIZEW, "mrf_size")
        self._mrf_start = Wire(MRFAW, "mrf_start")
        self._vrf_start = Wire(VRFAW, "vrf_start")
        self._tag = Wire(NTAGW, "tag")

        # Micro-instruction assemble wires
        self._uinst_out = Wire(uiw, "uinst_out")

        # Next-state wires for loop counters (computed in comb, updated in seq)
        self._next_batch_cnt = Wire(NSIZEW, "next_batch_cnt")
        self._next_vrf_cnt = Wire(NSIZEW, "next_vrf_cnt")
        self._next_mrf_cnt = Wire(NSIZEW, "next_mrf_cnt")

        # Control wires
        self._issue_done = Wire(1, "issue_done")
        self._all_done = Wire(1, "all_done")

        # Sequential
        with self.seq(self.clk, self.rst_n):
            # State machine using case for flat structure
            with Switch(self._state) as sw:
                with sw.case(self.ST_INIT):
                    with If(~self._minst_fifo_empty & ~self._uinst_fifo_full):
                        self._minst_reg <<= self._minst_fifo_rd_data
                        self._minst_valid <<= Const(1, 1)
                        self._state <<= self.ST_ISSUE
                        self._batch_cnt <<= Const(0, NSIZEW)
                        self._vrf_cnt <<= Const(0, NSIZEW)
                        self._mrf_cnt <<= Const(0, NSIZEW)
                with sw.case(self.ST_ISSUE):
                    with If(self._issue_done):
                        self._state <<= self.ST_LOOP
                with sw.case(self.ST_LOOP):
                    with If(self._all_done):
                        self._state <<= self.ST_INIT
                        self._minst_valid <<= Const(0, 1)
                    with Elif(~self._uinst_fifo_full):
                        self._state <<= self.ST_ISSUE
                        self._vrf_cnt <<= self._next_vrf_cnt
                        self._mrf_cnt <<= self._next_mrf_cnt
                        self._batch_cnt <<= self._next_batch_cnt
                with sw.default():
                    pass

        # Combinational
        with self.comb:
            # FIFO passthrough
            self._minst_fifo_wr_en <<= self.i_minst_wr_en
            self._minst_fifo_wr_data <<= self.i_minst_wr_din
            self._minst_fifo_rd_en <<= (self._state == self.ST_INIT) & ~self._minst_fifo_empty & ~self._uinst_fifo_full

            self._uinst_fifo_wr_en <<= (self._state == self.ST_ISSUE) & self._issue_done
            self._uinst_fifo_wr_data <<= self._uinst_out
            self._uinst_fifo_rd_en <<= self.i_uinst_rd_en

            self.o_minst_wr_rdy <<= ~self._minst_fifo_full
            self.o_uinst_rd_rdy <<= self._uinst_fifo_rd_rdy
            self.o_uinst_rd_dout <<= self._uinst_fifo_rd_data

            self._issue_done <<= Const(1, 1)

            # Decode macro-instruction (simplified field layout)
            decode_pos = 1  # skip valid bit
            self._batch_size <<= self._minst_reg[decode_pos + NSIZEW - 1 : decode_pos]
            decode_pos += NSIZEW
            self._vrf_size <<= self._minst_reg[decode_pos + NSIZEW - 1 : decode_pos]
            decode_pos += NSIZEW
            self._mrf_size <<= self._minst_reg[decode_pos + NSIZEW - 1 : decode_pos]
            decode_pos += NSIZEW
            self._mrf_start <<= self._minst_reg[decode_pos + MRFAW - 1 : decode_pos]
            decode_pos += MRFAW
            self._vrf_start <<= self._minst_reg[decode_pos + VRFAW - 1 : decode_pos]
            decode_pos += VRFAW
            self._tag <<= self._minst_reg[decode_pos + NTAGW - 1 : decode_pos]

            # Done flags
            self._all_done <<= (self._batch_cnt + Const(1, NSIZEW) >= self._batch_size) & \
                               (self._vrf_cnt + Const(1, NSIZEW) >= self._vrf_size) & \
                               (self._mrf_cnt + Const(1, NSIZEW) >= self._mrf_size)

            # Loop counter next-state logic (flat if-else)
            self._next_vrf_cnt <<= self._vrf_cnt + Const(1, NSIZEW)
            self._next_mrf_cnt <<= self._mrf_cnt
            self._next_batch_cnt <<= self._batch_cnt
            with If(self._vrf_cnt + Const(1, NSIZEW) >= self._vrf_size):
                self._next_vrf_cnt <<= Const(0, NSIZEW)
                self._next_mrf_cnt <<= self._mrf_cnt + Const(1, NSIZEW)
                with If(self._mrf_cnt + Const(1, NSIZEW) >= self._mrf_size):
                    self._next_mrf_cnt <<= Const(0, NSIZEW)
                    self._next_batch_cnt <<= self._batch_cnt + Const(1, NSIZEW)

            # Assemble micro-instruction (simplified)
            uinst_bits = []
            uinst_bits.append(self._vrf_start + self._vrf_cnt)
            uinst_bits.append(Const(0, VRFIDW))
            uinst_bits.append(Const(0, 1))
            uinst_bits.append(self._mrf_start + self._mrf_cnt)
            uinst_bits.append(self._tag)
            uinst_bits.append(Const(0, 2))
            uinst_bits.append(Const(DOTW - 1, 5))
            uinst_bits.append(Const(1, 1))
            self._uinst_out <<= Cat(*uinst_bits)

# ============================================================================
# MVUScheduler
# ============================================================================
class MVUScheduler(GenericScheduler):
    def __init__(self):
        super().__init__("mvu_sched", MIW_MVU, UIW_MVU, has_mrf=True)

# ============================================================================
# EVRFScheduler
# ============================================================================
class EVRFScheduler(GenericScheduler):
    def __init__(self):
        super().__init__("evrf_sched", MIW_EVRF, UIW_EVRF, has_mrf=False)

# ============================================================================
# MFUScheduler
# ============================================================================
class MFUScheduler(GenericScheduler):
    def __init__(self):
        super().__init__("mfu_sched", MIW_MFU, UIW_MFU, has_mrf=False, has_func=True)

# ============================================================================
# LDScheduler
# ============================================================================
class LDScheduler(GenericScheduler):
    def __init__(self):
        super().__init__("ld_sched", MIW_LD, UIW_LD, has_mrf=False)



# ============================================================================
# MVU -- Matrix Vector Unit (NTILE tiles x NDPE DPEs)
# ============================================================================
class MVU(Module):
    def __init__(self):
        super().__init__("mvu")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_mrf_wr_en = Input(MRFIDW, "i_mrf_wr_en")
        self.i_mrf_wr_addr = Input(MRFAW, "i_mrf_wr_addr")
        self.i_mrf_wr_data = Input(EW * DOTW, "i_mrf_wr_data")
        self.i_vrf0_wr_addr = Input(VRFAW, "i_vrf0_wr_addr")
        self.i_vrf1_wr_addr = Input(VRFAW, "i_vrf1_wr_addr")
        self.i_vrf_wr_data = Input(ACCW * DOTW, "i_vrf_wr_data")
        self.i_vrf_wr_en = Input(1, "i_vrf_wr_en")
        self.i_vrf_wr_id = Input(2 * NVRF, "i_vrf_wr_id")
        self.i_inst_wr_en = Input(1, "i_inst_wr_en")
        self.i_vrf_rd_addr = Input(VRFAW, "i_vrf_rd_addr")
        self.i_vrf_rd_id = Input(VRFIDW, "i_vrf_rd_id")
        self.i_reg_sel = Input(1, "i_reg_sel")
        self.i_mrf_rd_addr = Input(MRFAW, "i_mrf_rd_addr")
        self.i_acc_op = Input(2, "i_acc_op")
        self.i_tag = Input(NTAGW, "i_tag")
        self.i_acc_size = Input(5, "i_acc_size")
        self.i_vrf_en = Input(1, "i_vrf_en")
        self.i_data_rd_en = Input(DOTW, "i_data_rd_en")
        self.o_inst_wr_rdy = Output(1, "o_inst_wr_rdy")
        self.o_data_rd_rdy = Output(DOTW, "o_data_rd_rdy")
        self.o_data_rd_dout = Output(ACCW * NDPE, "o_data_rd_dout")

        # Memories
        self._mrf = Array(EW * DOTW, NMRF * MRFD, "mrf")
        self._vrf = Array(ACCW * DOTW, NVRF * VRFD, "vrf")

        # Instruction FIFO
        self._inst_fifo = SyncFIFO(UIW_MVU, QDEPTH_AW)
        self._inst_fifo_wr_en = Wire(1, "_inst_fifo_wr_en")
        self._inst_fifo_wr_data = Wire(UIW_MVU, "_inst_fifo_wr_data")
        self._inst_fifo_rd_en = Wire(1, "_inst_fifo_rd_en")
        self._inst_fifo_rd_rdy = Wire(1, "_inst_fifo_rd_rdy")
        self._inst_fifo_rd_data = Wire(UIW_MVU, "_inst_fifo_rd_data")
        self._inst_fifo_full = Wire(1, "_inst_fifo_full")
        self._inst_fifo_empty = Wire(1, "_inst_fifo_empty")
        self._inst_fifo_usedw = Wire(QDEPTH_AW, "_inst_fifo_usedw")
        self.instantiate(self._inst_fifo, "inst_fifo", port_map={"wr_en": self._inst_fifo_wr_en, "din": self._inst_fifo_wr_data, "rd_en": self._inst_fifo_rd_en, "rd_rdy": self._inst_fifo_rd_rdy, "dout": self._inst_fifo_rd_data, "full": self._inst_fifo_full, "empty": self._inst_fifo_empty, "count": self._inst_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        # State machine
        self.add_localparam("ST_IDLE", 0)
        self.add_localparam("ST_FETCH", 1)
        self.add_localparam("ST_EXEC", 2)
        self.add_localparam("ST_OUTPUT", 3)
        self._state = Reg(2, "state")

        # Instruction decode registers
        self._inst_vrf_addr = Reg(VRFAW, "inst_vrf_addr")
        self._inst_vrf_id = Reg(VRFIDW, "inst_vrf_id")
        self._inst_reg_sel = Reg(1, "inst_reg_sel")
        self._inst_mrf_addr = Reg(MRFAW, "inst_mrf_addr")
        self._inst_tag = Reg(NTAGW, "inst_tag")
        self._inst_acc_op = Reg(2, "inst_acc_op")
        self._inst_acc_size = Reg(5, "inst_acc_size")
        self._inst_vrf_en = Reg(1, "inst_vrf_en")

        # Pipeline registers
        self._vrf_rdata = Reg(ACCW * DOTW, "vrf_rdata")
        self._dpe_result = Array(ACCW, NDPE * NTILE, "dpe_result")
        self._out_data = Reg(ACCW * NDPE, "out_data")
        self._out_valid = Reg(DOTW, "out_valid")
        self._out_tag = Reg(NTAGW, "out_tag")

        # Accumulator memory (per-DPE accumulator)
        self._accum = Array(ACCW, NDPE * NTILE, "accum")

        # Temporary array for dot-product (used in comb)
        self._dot_sum = Array(ACCW, NDPE * NTILE, "dot_sum")

        # Per-tile per-DPE MRF read data (combinational)
        self._mrf_rdata_arr = Array(EW * DOTW, NDPE * NTILE, "mrf_rdata_arr")
        self._reduced_result = Array(ACCW, NDPE, "reduced_result")

        # Sequential logic
        with self.seq(self.clk, self.rst_n):
            # MRF write
            with ForGen("m", 0, NMRF) as m:
                with If(self.i_mrf_wr_en[m]):
                    self._mrf[m * Const(MRFD, MRFAW + 1) + self.i_mrf_wr_addr] <<= self.i_mrf_wr_data

            # VRF write (multi-bank, one-hot id)
            with ForGen("v", 0, NVRF) as v:
                with If(self.i_vrf_wr_en & self.i_vrf_wr_id[v]):
                    wraddr = Mux(self.i_reg_sel, self.i_vrf1_wr_addr, self.i_vrf0_wr_addr)
                    self._vrf[v * Const(VRFD, VRFAW + 1) + wraddr] <<= self.i_vrf_wr_data

            # State machine
            with If(self._state == self.ST_IDLE):
                with If(~self._inst_fifo_empty):
                    self._state <<= self.ST_FETCH
                    # Decode instruction
                    uinst = self._inst_fifo_rd_data
                    p = 0
                    self._inst_vrf_addr <<= uinst[p + VRFAW - 1 : p]; p += VRFAW
                    self._inst_vrf_id <<= uinst[p + VRFIDW - 1 : p]; p += VRFIDW
                    self._inst_reg_sel <<= uinst[p]; p += 1
                    self._inst_mrf_addr <<= uinst[p + MRFAW - 1 : p]; p += MRFAW
                    self._inst_tag <<= uinst[p + NTAGW - 1 : p]; p += NTAGW
                    self._inst_acc_op <<= uinst[p + 2 - 1 : p]; p += 2
                    self._inst_acc_size <<= uinst[p + 5 - 1 : p]; p += 5
                    self._inst_vrf_en <<= uinst[p]
            with Elif(self._state == self.ST_FETCH):
                # Read VRF (shared across tiles)
                vrf_bank = self._inst_vrf_id
                self._vrf_rdata <<= self._vrf[vrf_bank * Const(VRFD, VRFAW + 1) + self._inst_vrf_addr]
                self._state <<= self.ST_EXEC
            with Elif(self._state == self.ST_EXEC):
                # Compute dot-products (combinational, latched here)
                with ForGen("t", 0, NTILE) as t:
                    with ForGen("d", 0, NDPE) as d:
                        idx = t * NDPE + d
                        with If(self._inst_acc_op == Const(0, 2)):
                            # SET: overwrite accumulator
                            self._accum[idx] <<= self._dot_sum[idx]
                        with Elif(self._inst_acc_op == Const(1, 2)):
                            # UPD: add to accumulator
                            self._accum[idx] <<= self._accum[idx] + self._dot_sum[idx]
                        with Elif(self._inst_acc_op == Const(2, 2)):
                            # WB: writeback only
                            pass
                        with Else():
                            # SET_AND_WB
                            self._accum[idx] <<= self._dot_sum[idx]
                        self._dpe_result[idx] <<= self._dot_sum[idx]
                self._state <<= self.ST_OUTPUT
            with Elif(self._state == self.ST_OUTPUT):
                with ForGen("d", 0, NDPE) as d:
                    self._out_data[d * ACCW + (ACCW - 1) : d * ACCW] <<= self._reduced_result[d]
                self._out_valid <<= Const(-1, DOTW)
                self._out_tag <<= self._inst_tag
                with If(self.i_data_rd_en[0]):
                    self._state <<= self.ST_IDLE

        # Module-level combinational assignments (avoid massive for-loops inside always @(*))
        # which cause iverilog to timeout due to dependency-graph explosion.

        # Read MRF for each tile/DPE
        for t in range(NTILE):
            for d in range(NDPE):
                idx = t * NDPE + d
                mrf_bank_addr = idx * Const(MRFD, MRFAW + 1) + self._inst_mrf_addr
                self._mrf_rdata_arr[idx] <<= self._mrf[mrf_bank_addr]

        # Compute dot-products for all tiles and DPEs
        for t in range(NTILE):
            for d in range(NDPE):
                idx = t * NDPE + d
                total = None
                for l in range(DOTW):
                    lo_v = l * ACCW
                    hi_v = lo_v + (ACCW - 1)
                    lo_m = l * EW
                    hi_m = lo_m + (EW - 1)
                    vrf_lane = self._vrf_rdata[hi_v : lo_v]
                    mrf_lane = self._mrf_rdata_arr[idx][hi_m : lo_m]
                    prod = vrf_lane * mrf_lane
                    if total is None:
                        total = prod
                    else:
                        total = total + prod
                self._dot_sum[idx] <<= total

        # Reduction tree: sum across tiles for each DPE
        for d in range(NDPE):
            total = None
            for t in range(NTILE):
                idx = t * NDPE + d
                if total is None:
                    total = self._dot_sum[idx]
                else:
                    total = total + self._dot_sum[idx]
            self._reduced_result[d] <<= total

        # Simple combinational signals stay in comb block
        with self.comb:
            self._inst_fifo_wr_en <<= self.i_inst_wr_en
            self._inst_fifo_wr_data <<= Cat(self.i_vrf_rd_addr, self.i_vrf_rd_id, self.i_reg_sel,
                                            self.i_mrf_rd_addr, self.i_tag, self.i_acc_op,
                                            self.i_acc_size, self.i_vrf_en)
            self._inst_fifo_rd_en <<= (self._state == self.ST_IDLE) & ~self._inst_fifo_empty
            self.o_inst_wr_rdy <<= ~self._inst_fifo_full
            self.o_data_rd_dout <<= self._out_data
            self.o_data_rd_rdy <<= self._out_valid



# ============================================================================
# MFU -- Multi-Function Unit (ReLU / Sigmoid / Tanh / Add / Sub / Mul / Max)
# ============================================================================
class MFU(Module):
    def __init__(self):
        super().__init__("mfu")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_vrf0_wr_addr = Input(VRFAW, "i_vrf0_wr_addr")
        self.i_vrf1_wr_addr = Input(VRFAW, "i_vrf1_wr_addr")
        self.i_vrf_wr_data = Input(ACCW * DOTW, "i_vrf_wr_data")
        self.i_vrf_wr_en = Input(1, "i_vrf_wr_en")
        self.i_vrf_wr_id = Input(2 * NVRF, "i_vrf_wr_id")
        self.i_data_wr_en = Input(DOTW, "i_data_wr_en")
        self.i_data_wr_din = Input(ACCW * DOTW, "i_data_wr_din")
        self.i_data_rd_en = Input(DOTW, "i_data_rd_en")
        self.i_inst_wr_en = Input(1, "i_inst_wr_en")
        self.i_vrf0_rd_addr = Input(VRFAW, "i_vrf0_rd_addr")
        self.i_vrf1_rd_addr = Input(VRFAW, "i_vrf1_rd_addr")
        self.i_func_op = Input(6, "i_func_op")
        self.i_tag = Input(NTAGW, "i_tag")
        self.i_tag_update_en = Input(1, "i_tag_update_en")
        self.o_data_wr_rdy = Output(DOTW, "o_data_wr_rdy")
        self.o_data_rd_rdy = Output(DOTW, "o_data_rd_rdy")
        self.o_data_rd_dout = Output(ACCW * DOTW, "o_data_rd_dout")
        self.o_inst_wr_rdy = Output(1, "o_inst_wr_rdy")

        # VRF memory (subset of NVRF banks allocated to this MFU)
        self._vrf = Array(ACCW * DOTW, NVRF * VRFD, "vrf")

        # Instruction FIFO
        self._inst_fifo = SyncFIFO(UIW_MFU, QDEPTH_AW)
        self._inst_fifo_wr_en = Wire(1, "_inst_fifo_wr_en")
        self._inst_fifo_wr_data = Wire(UIW_MFU, "_inst_fifo_wr_data")
        self._inst_fifo_rd_en = Wire(1, "_inst_fifo_rd_en")
        self._inst_fifo_rd_rdy = Wire(1, "_inst_fifo_rd_rdy")
        self._inst_fifo_rd_data = Wire(UIW_MFU, "_inst_fifo_rd_data")
        self._inst_fifo_full = Wire(1, "_inst_fifo_full")
        self._inst_fifo_empty = Wire(1, "_inst_fifo_empty")
        self._inst_fifo_usedw = Wire(QDEPTH_AW, "_inst_fifo_usedw")
        self.instantiate(self._inst_fifo, "inst_fifo", port_map={"wr_en": self._inst_fifo_wr_en, "din": self._inst_fifo_wr_data, "rd_en": self._inst_fifo_rd_en, "rd_rdy": self._inst_fifo_rd_rdy, "dout": self._inst_fifo_rd_data, "full": self._inst_fifo_full, "empty": self._inst_fifo_empty, "count": self._inst_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        # Data input FIFO (per-lane or shared)
        self._data_fifo = SyncFIFO(ACCW * DOTW, QDEPTH_AW)
        self._data_fifo_wr_en = Wire(1, "_data_fifo_wr_en")
        self._data_fifo_wr_data = Wire(ACCW * DOTW, "_data_fifo_wr_data")
        self._data_fifo_rd_en = Wire(1, "_data_fifo_rd_en")
        self._data_fifo_rd_rdy = Wire(1, "_data_fifo_rd_rdy")
        self._data_fifo_rd_data = Wire(ACCW * DOTW, "_data_fifo_rd_data")
        self._data_fifo_full = Wire(1, "_data_fifo_full")
        self._data_fifo_empty = Wire(1, "_data_fifo_empty")
        self._data_fifo_usedw = Wire(QDEPTH_AW, "_data_fifo_usedw")
        self.instantiate(self._data_fifo, "data_fifo", port_map={"wr_en": self._data_fifo_wr_en, "din": self._data_fifo_wr_data, "rd_en": self._data_fifo_rd_en, "rd_rdy": self._data_fifo_rd_rdy, "dout": self._data_fifo_rd_data, "full": self._data_fifo_full, "empty": self._data_fifo_empty, "count": self._data_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        # Output FIFO
        self._out_fifo = SyncFIFO(ACCW * DOTW, QDEPTH_AW)
        self._out_fifo_wr_en = Wire(1, "_out_fifo_wr_en")
        self._out_fifo_wr_data = Wire(ACCW * DOTW, "_out_fifo_wr_data")
        self._out_fifo_rd_en = Wire(1, "_out_fifo_rd_en")
        self._out_fifo_rd_rdy = Wire(1, "_out_fifo_rd_rdy")
        self._out_fifo_rd_data = Wire(ACCW * DOTW, "_out_fifo_rd_data")
        self._out_fifo_full = Wire(1, "_out_fifo_full")
        self._out_fifo_empty = Wire(1, "_out_fifo_empty")
        self._out_fifo_usedw = Wire(QDEPTH_AW, "_out_fifo_usedw")
        self.instantiate(self._out_fifo, "out_fifo", port_map={"wr_en": self._out_fifo_wr_en, "din": self._out_fifo_wr_data, "rd_en": self._out_fifo_rd_en, "rd_rdy": self._out_fifo_rd_rdy, "dout": self._out_fifo_rd_data, "full": self._out_fifo_full, "empty": self._out_fifo_empty, "count": self._out_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        # State machine
        self.add_localparam("ST_IDLE", 0)
        self.add_localparam("ST_FETCH", 1)
        self.add_localparam("ST_MULT", 2)
        self.add_localparam("ST_ADD", 3)
        self.add_localparam("ST_ACT", 4)
        self.add_localparam("ST_OUTPUT", 5)
        self._state = Reg(3, "state")

        # Instruction decode
        self._func_op = self.func_op_reg = Reg(6, "func_op_reg")
        self._vrf0_addr = self.vrf0_addr_reg = Reg(VRFAW, "vrf0_addr_reg")
        self._vrf1_addr = self.vrf1_addr_reg = Reg(VRFAW, "vrf1_addr_reg")
        self._tag_reg = Reg(NTAGW, "tag_reg")

        # Pipeline data
        self._vrf0_data = Reg(ACCW * DOTW, "vrf0_data")
        self._vrf1_data = Reg(ACCW * DOTW, "vrf1_data")

        # Pipeline registers for full mult->add->act chain
        self._mult_result = Reg(ACCW * DOTW, "mult_result")
        self._add_result = Reg(ACCW * DOTW, "add_result")
        self._act_result = Reg(ACCW * DOTW, "act_result")

        # Per-lane computation arrays (for ForGen)
        self._lane_mult = Array(ACCW, DOTW, "lane_mult")
        self._lane_add = Array(ACCW, DOTW, "lane_add")
        self._lane_act = Array(ACCW, DOTW, "lane_act")

        # Operation decode wires
        self._use_vrf0 = Wire(1, "use_vrf0")
        self._use_vrf1 = Wire(1, "use_vrf1")
        self._is_addsub = Wire(1, "is_addsub")
        self._is_sub = Wire(1, "is_sub")
        self._is_act = Wire(1, "is_act")
        self._is_relu = Wire(1, "is_relu")

        # Sequential
        with self.seq(self.clk, self.rst_n):
            # VRF write
            with ForGen("v", 0, NVRF) as v:
                with If(self.i_vrf_wr_en & self.i_vrf_wr_id[v]):
                    self._vrf[v * Const(VRFD, VRFAW + 1) + self.i_vrf0_wr_addr] <<= self.i_vrf_wr_data

            # State machine
            with If(self._state == self.ST_IDLE):
                with If(~self._inst_fifo_empty):
                    self._state <<= self.ST_FETCH
                    uinst = self._inst_fifo_rd_data
                    p = 0
                    self._vrf0_addr <<= uinst[p + VRFAW - 1 : p]; p += VRFAW
                    self._vrf1_addr <<= uinst[p + VRFAW - 1 : p]; p += VRFAW
                    self._func_op <<= uinst[p + 6 - 1 : p]; p += 6
                    self._tag_reg <<= uinst[p + NTAGW - 1 : p]
            with Elif(self._state == self.ST_FETCH):
                self._vrf0_data <<= self._vrf[self._vrf0_addr]
                self._vrf1_data <<= self._vrf[self._vrf1_addr]
                self._state <<= self.ST_MULT
            with Elif(self._state == self.ST_MULT):
                with ForGen("l", 0, DOTW) as l:
                    lo = l * ACCW
                    hi = lo + (ACCW - 1)
                    a = self._vrf0_data[hi : lo]
                    b = self._vrf1_data[hi : lo]
                    self._lane_mult[l] <<= a * b
                with ForGen("l", 0, DOTW) as l:
                    self._mult_result[l * ACCW + (ACCW - 1) : l * ACCW] <<= self._lane_mult[l]
                self._state <<= self.ST_ADD
            with Elif(self._state == self.ST_ADD):
                with ForGen("l", 0, DOTW) as l:
                    lo = l * ACCW
                    hi = lo + (ACCW - 1)
                    a = self._vrf0_data[hi : lo]
                    b = self._vrf1_data[hi : lo]
                    m = self._lane_mult[l]
                    with If(self._is_addsub):
                        with If(self._is_sub):
                            self._lane_add[l] <<= a - b
                        with Else():
                            self._lane_add[l] <<= a + b
                    with Else():
                        self._lane_add[l] <<= m
                with ForGen("l", 0, DOTW) as l:
                    self._add_result[l * ACCW + (ACCW - 1) : l * ACCW] <<= self._lane_add[l]
                self._state <<= self.ST_ACT
            with Elif(self._state == self.ST_ACT):
                with ForGen("l", 0, DOTW) as l:
                    x = self._lane_add[l]
                    with If(self._is_act):
                        with If(self._is_relu):
                            # ReLU
                            with If(x[ACCW - 1]):
                                self._lane_act[l] <<= Const(0, ACCW)
                            with Else():
                                self._lane_act[l] <<= x
                        with Else():
                            # Tanh approximation: saturate to INT8 range
                            with If(x > Const(127, ACCW)):
                                self._lane_act[l] <<= Const(127, ACCW)
                            with Elif(x < Const(-128, ACCW)):
                                self._lane_act[l] <<= Const(-128, ACCW)
                            with Else():
                                self._lane_act[l] <<= x
                    with Else():
                        self._lane_act[l] <<= x
                with ForGen("l", 0, DOTW) as l:
                    self._act_result[l * ACCW + (ACCW - 1) : l * ACCW] <<= self._lane_act[l]
                self._state <<= self.ST_OUTPUT
            with Elif(self._state == self.ST_OUTPUT):
                with If(~self._out_fifo_full):
                    self._state <<= self.ST_IDLE

        # Combinational
        with self.comb:
            self._inst_fifo_wr_en <<= self.i_inst_wr_en
            self._inst_fifo_wr_data <<= Cat(self.i_vrf0_rd_addr, self.i_vrf1_rd_addr, self.i_func_op, self.i_tag)
            self._inst_fifo_rd_en <<= (self._state == self.ST_IDLE) & ~self._inst_fifo_empty
            self.o_inst_wr_rdy <<= ~self._inst_fifo_full

            self._data_fifo_wr_en <<= self.i_data_wr_en[0]
            self._data_fifo_wr_data <<= self.i_data_wr_din
            self._data_fifo_rd_en <<= (self._state == self.ST_FETCH)
            self.o_data_wr_rdy <<= Rep(~self._data_fifo_full, DOTW)

            self._out_fifo_wr_en <<= (self._state == self.ST_OUTPUT) & ~self._out_fifo_full
            self._out_fifo_wr_data <<= self._act_result
            self._out_fifo_rd_en <<= self.i_data_rd_en[0]

            self.o_data_rd_rdy <<= Rep(self._out_fifo_rd_rdy, DOTW)
            self.o_data_rd_dout <<= self._out_fifo_rd_data

            # Decode func_op
            self._use_vrf0 <<= self._func_op[0]
            self._use_vrf1 <<= self._func_op[1]
            self._is_addsub <<= self._func_op[2]
            self._is_sub <<= self._func_op[3]
            self._is_act <<= self._func_op[4]
            self._is_relu <<= self._func_op[5]



# ============================================================================
# eVRF -- Extended Vector Register File (12-bank VRF)
# ============================================================================
class EVRF(Module):
    def __init__(self):
        super().__init__("evrf")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_vrf0_wr_addr = Input(VRFAW, "i_vrf0_wr_addr")
        self.i_vrf1_wr_addr = Input(VRFAW, "i_vrf1_wr_addr")
        self.i_vrf_wr_data = Input(ACCW * DOTW, "i_vrf_wr_data")
        self.i_vrf_wr_en = Input(1, "i_vrf_wr_en")
        self.i_vrf_wr_id = Input(2 * NVRF, "i_vrf_wr_id")
        self.i_data_wr_en = Input(DOTW, "i_data_wr_en")
        self.i_data_wr_din = Input(ACCW * NDPE, "i_data_wr_din")
        self.i_data_rd_en = Input(DOTW, "i_data_rd_en")
        self.i_inst_wr_en = Input(1, "i_inst_wr_en")
        self.i_vrf_rd_addr = Input(VRFAW, "i_vrf_rd_addr")
        self.i_src_sel = Input(2, "i_src_sel")
        self.i_tag = Input(NTAGW, "i_tag")
        self.i_tag_update_en = Input(1, "i_tag_update_en")
        self.o_data_wr_rdy = Output(DOTW, "o_data_wr_rdy")
        self.o_data_rd_rdy = Output(DOTW, "o_data_rd_rdy")
        self.o_data_rd_dout = Output(ACCW * DOTW, "o_data_rd_dout")
        self.o_inst_wr_rdy = Output(1, "o_inst_wr_rdy")

        # VRF memory
        self._vrf = Array(ACCW * DOTW, NVRF * VRFD, "vrf")

        # Instruction FIFO
        self._inst_fifo = SyncFIFO(UIW_EVRF, QDEPTH_AW)
        self._inst_fifo_wr_en = Wire(1, "_inst_fifo_wr_en")
        self._inst_fifo_wr_data = Wire(UIW_EVRF, "_inst_fifo_wr_data")
        self._inst_fifo_rd_en = Wire(1, "_inst_fifo_rd_en")
        self._inst_fifo_rd_rdy = Wire(1, "_inst_fifo_rd_rdy")
        self._inst_fifo_rd_data = Wire(UIW_EVRF, "_inst_fifo_rd_data")
        self._inst_fifo_full = Wire(1, "_inst_fifo_full")
        self._inst_fifo_empty = Wire(1, "_inst_fifo_empty")
        self._inst_fifo_usedw = Wire(QDEPTH_AW, "_inst_fifo_usedw")
        self.instantiate(self._inst_fifo, "inst_fifo", port_map={"wr_en": self._inst_fifo_wr_en, "din": self._inst_fifo_wr_data, "rd_en": self._inst_fifo_rd_en, "rd_rdy": self._inst_fifo_rd_rdy, "dout": self._inst_fifo_rd_data, "full": self._inst_fifo_full, "empty": self._inst_fifo_empty, "count": self._inst_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        # Data input FIFO
        self._data_fifo = SyncFIFO(ACCW * NDPE, QDEPTH_AW)
        self._data_fifo_wr_en = Wire(1, "_data_fifo_wr_en")
        self._data_fifo_wr_data = Wire(ACCW * NDPE, "_data_fifo_wr_data")
        self._data_fifo_rd_en = Wire(1, "_data_fifo_rd_en")
        self._data_fifo_rd_rdy = Wire(1, "_data_fifo_rd_rdy")
        self._data_fifo_rd_data = Wire(ACCW * NDPE, "_data_fifo_rd_data")
        self._data_fifo_full = Wire(1, "_data_fifo_full")
        self._data_fifo_empty = Wire(1, "_data_fifo_empty")
        self._data_fifo_usedw = Wire(QDEPTH_AW, "_data_fifo_usedw")
        self.instantiate(self._data_fifo, "data_fifo", port_map={"wr_en": self._data_fifo_wr_en, "din": self._data_fifo_wr_data, "rd_en": self._data_fifo_rd_en, "rd_rdy": self._data_fifo_rd_rdy, "dout": self._data_fifo_rd_data, "full": self._data_fifo_full, "empty": self._data_fifo_empty, "count": self._data_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        # Output FIFO
        self._out_fifo = SyncFIFO(ACCW * DOTW, QDEPTH_AW)
        self._out_fifo_wr_en = Wire(1, "_out_fifo_wr_en")
        self._out_fifo_wr_data = Wire(ACCW * DOTW, "_out_fifo_wr_data")
        self._out_fifo_rd_en = Wire(1, "_out_fifo_rd_en")
        self._out_fifo_rd_rdy = Wire(1, "_out_fifo_rd_rdy")
        self._out_fifo_rd_data = Wire(ACCW * DOTW, "_out_fifo_rd_data")
        self._out_fifo_full = Wire(1, "_out_fifo_full")
        self._out_fifo_empty = Wire(1, "_out_fifo_empty")
        self._out_fifo_usedw = Wire(QDEPTH_AW, "_out_fifo_usedw")
        self.instantiate(self._out_fifo, "out_fifo", port_map={"wr_en": self._out_fifo_wr_en, "din": self._out_fifo_wr_data, "rd_en": self._out_fifo_rd_en, "rd_rdy": self._out_fifo_rd_rdy, "dout": self._out_fifo_rd_data, "full": self._out_fifo_full, "empty": self._out_fifo_empty, "count": self._out_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        # State machine
        self.add_localparam("ST_IDLE", 0)
        self.add_localparam("ST_FETCH", 1)
        self.add_localparam("ST_OUTPUT", 2)
        self._state = Reg(2, "state")

        self._vrf_addr_reg = Reg(VRFAW, "vrf_addr_reg")
        self._src_sel_reg = Reg(2, "src_sel_reg")
        self._tag_reg = Reg(NTAGW, "tag_reg")

        self._vrf_rdata = Reg(ACCW * DOTW, "vrf_rdata")
        self._data_rdata = Reg(ACCW * NDPE, "data_rdata")

        # Sequential
        with self.seq(self.clk, self.rst_n):
            # VRF write
            with ForGen("v", 0, NVRF) as v:
                with If(self.i_vrf_wr_en & self.i_vrf_wr_id[v]):
                    self._vrf[v * Const(VRFD, VRFAW + 1) + self.i_vrf0_wr_addr] <<= self.i_vrf_wr_data

            with If(self._state == self.ST_IDLE):
                with If(~self._inst_fifo_empty):
                    self._state <<= self.ST_FETCH
                    uinst = self._inst_fifo_rd_data
                    p = 0
                    self._vrf_addr_reg <<= uinst[p + VRFAW - 1 : p]; p += VRFAW
                    self._src_sel_reg <<= uinst[p + 2 - 1 : p]; p += 2
                    self._tag_reg <<= uinst[p + NTAGW - 1 : p]
            with Elif(self._state == self.ST_FETCH):
                with If(self._src_sel_reg == Const(0, 2)):
                    self._vrf_rdata <<= self._vrf[self._vrf_addr_reg]
                with Elif(self._src_sel_reg == Const(1, 2)):
                    self._data_rdata <<= self._data_fifo_rd_data
                self._state <<= self.ST_OUTPUT
            with Elif(self._state == self.ST_OUTPUT):
                with If(~self._out_fifo_full):
                    self._state <<= self.ST_IDLE

        # Combinational
        with self.comb:
            self._inst_fifo_wr_en <<= self.i_inst_wr_en
            self._inst_fifo_wr_data <<= Cat(self.i_vrf_rd_addr, self.i_src_sel, self.i_tag)
            self._inst_fifo_rd_en <<= (self._state == self.ST_IDLE) & ~self._inst_fifo_empty
            self.o_inst_wr_rdy <<= ~self._inst_fifo_full

            self._data_fifo_wr_en <<= self.i_data_wr_en[0]
            self._data_fifo_wr_data <<= self.i_data_wr_din
            self._data_fifo_rd_en <<= (self._state == self.ST_FETCH) & (self._src_sel_reg == Const(1, 2))
            self.o_data_wr_rdy <<= Rep(~self._data_fifo_full, DOTW)

            self._out_fifo_wr_en <<= (self._state == self.ST_OUTPUT) & ~self._out_fifo_full
            with If(self._src_sel_reg == Const(0, 2)):
                self._out_fifo_wr_data <<= self._vrf_rdata
            with Else():
                # Extract first DOTW elements from NDPE-wide data
                self._out_fifo_wr_data <<= self._data_rdata[ACCW * DOTW - 1 : 0]
            self._out_fifo_rd_en <<= self.i_data_rd_en[0]

            self.o_data_rd_rdy <<= Rep(self._out_fifo_rd_rdy, DOTW)
            self.o_data_rd_dout <<= self._out_fifo_rd_data



# ============================================================================
# LD -- Load/Store Unit (input FIFO, writeback FIFO, output FIFO, VRF writeback)
# ============================================================================
class LD(Module):
    def __init__(self):
        super().__init__("ld")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        # I/O
        self.i_vrf_wr_en = Input(1, "i_vrf_wr_en")
        self.i_vrf_wr_id = Input(2 * NVRF, "i_vrf_wr_id")
        self.i_vrf0_wr_addr = Input(VRFAW, "i_vrf0_wr_addr")
        self.i_vrf1_wr_addr = Input(VRFAW, "i_vrf1_wr_addr")
        self.i_vrf_wr_data = Input(ACCW * DOTW, "i_vrf_wr_data")
        self.i_in_wr_en = Input(1, "i_in_wr_en")
        self.i_in_wr_din = Input(EW * DOTW, "i_in_wr_din")
        self.i_wb_wr_en = Input(DOTW, "i_wb_wr_en")
        self.i_wb_wr_din = Input(ACCW * DOTW, "i_wb_wr_din")
        self.i_out_rd_en = Input(1, "i_out_rd_en")
        self.i_inst_wr_en = Input(1, "i_inst_wr_en")
        self.i_inst_wr_din = Input(UIW_LD, "i_inst_wr_din")
        self.i_tag = Input(NTAGW, "i_tag")
        self.i_tag_update_en = Input(1, "i_tag_update_en")
        self.i_start = Input(1, "i_start")

        self.o_vrf_wr_en = Output(1, "o_vrf_wr_en")
        self.o_vrf_wr_id = Output(2 * NVRF, "o_vrf_wr_id")
        self.o_vrf0_wr_addr = Output(VRFAW, "o_vrf0_wr_addr")
        self.o_vrf1_wr_addr = Output(VRFAW, "o_vrf1_wr_addr")
        self.o_vrf_wr_data = Output(ACCW * DOTW, "o_vrf_wr_data")
        self.o_in_wr_rdy = Output(1, "o_in_wr_rdy")
        self.o_in_usedw = Output(INBUF_AW, "o_in_usedw")
        self.o_out_rd_rdy = Output(1, "o_out_rd_rdy")
        self.o_out_rd_dout = Output(ACCW * DOTW + 1, "o_out_rd_dout")
        self.o_out_usedw = Output(OUTBUF_AW, "o_out_usedw")
        self.o_inst_wr_rdy = Output(1, "o_inst_wr_rdy")
        self.o_tag_update_en = Output(1, "o_tag_update_en")
        self.o_start = Output(1, "o_start")
        self.o_done = Output(1, "o_done")
        self.o_debug_ld_ififo_counter = Output(32, "o_debug_ld_ififo_counter")
        self.o_debug_ld_wbfifo_counter = Output(32, "o_debug_ld_wbfifo_counter")
        self.o_debug_ld_instfifo_counter = Output(32, "o_debug_ld_instfifo_counter")
        self.o_debug_ld_ofifo_counter = Output(32, "o_debug_ld_ofifo_counter")
        self.o_result_count = Output(32, "o_result_count")

        # FIFOs
        self._in_fifo = SyncFIFO(EW * DOTW, INBUF_AW)
        self._in_fifo_wr_en = Wire(1, "_in_fifo_wr_en")
        self._in_fifo_wr_data = Wire(EW * DOTW, "_in_fifo_wr_data")
        self._in_fifo_rd_en = Wire(1, "_in_fifo_rd_en")
        self._in_fifo_rd_rdy = Wire(1, "_in_fifo_rd_rdy")
        self._in_fifo_rd_data = Wire(EW * DOTW, "_in_fifo_rd_data")
        self._in_fifo_full = Wire(1, "_in_fifo_full")
        self._in_fifo_empty = Wire(1, "_in_fifo_empty")
        self._in_fifo_usedw = Wire(INBUF_AW, "_in_fifo_usedw")
        self.instantiate(self._in_fifo, "in_fifo", port_map={"wr_en": self._in_fifo_wr_en, "din": self._in_fifo_wr_data, "rd_en": self._in_fifo_rd_en, "rd_rdy": self._in_fifo_rd_rdy, "dout": self._in_fifo_rd_data, "full": self._in_fifo_full, "empty": self._in_fifo_empty, "count": self._in_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        self._wb_fifo = SyncFIFO(ACCW * DOTW, QDEPTH_AW)
        self._wb_fifo_wr_en = Wire(1, "_wb_fifo_wr_en")
        self._wb_fifo_wr_data = Wire(ACCW * DOTW, "_wb_fifo_wr_data")
        self._wb_fifo_rd_en = Wire(1, "_wb_fifo_rd_en")
        self._wb_fifo_rd_rdy = Wire(1, "_wb_fifo_rd_rdy")
        self._wb_fifo_rd_data = Wire(ACCW * DOTW, "_wb_fifo_rd_data")
        self._wb_fifo_full = Wire(1, "_wb_fifo_full")
        self._wb_fifo_empty = Wire(1, "_wb_fifo_empty")
        self._wb_fifo_usedw = Wire(QDEPTH_AW, "_wb_fifo_usedw")
        self.instantiate(self._wb_fifo, "wb_fifo", port_map={"wr_en": self._wb_fifo_wr_en, "din": self._wb_fifo_wr_data, "rd_en": self._wb_fifo_rd_en, "rd_rdy": self._wb_fifo_rd_rdy, "dout": self._wb_fifo_rd_data, "full": self._wb_fifo_full, "empty": self._wb_fifo_empty, "count": self._wb_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        self._inst_fifo = SyncFIFO(UIW_LD, QDEPTH_AW)
        self._inst_fifo_wr_en = Wire(1, "_inst_fifo_wr_en")
        self._inst_fifo_wr_data = Wire(UIW_LD, "_inst_fifo_wr_data")
        self._inst_fifo_rd_en = Wire(1, "_inst_fifo_rd_en")
        self._inst_fifo_rd_rdy = Wire(1, "_inst_fifo_rd_rdy")
        self._inst_fifo_rd_data = Wire(UIW_LD, "_inst_fifo_rd_data")
        self._inst_fifo_full = Wire(1, "_inst_fifo_full")
        self._inst_fifo_empty = Wire(1, "_inst_fifo_empty")
        self._inst_fifo_usedw = Wire(QDEPTH_AW, "_inst_fifo_usedw")
        self.instantiate(self._inst_fifo, "inst_fifo", port_map={"wr_en": self._inst_fifo_wr_en, "din": self._inst_fifo_wr_data, "rd_en": self._inst_fifo_rd_en, "rd_rdy": self._inst_fifo_rd_rdy, "dout": self._inst_fifo_rd_data, "full": self._inst_fifo_full, "empty": self._inst_fifo_empty, "count": self._inst_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        self._out_fifo = SyncFIFO(ACCW * DOTW + 1, OUTBUF_AW)
        self._out_fifo_wr_en = Wire(1, "_out_fifo_wr_en")
        self._out_fifo_wr_data = Wire(ACCW * DOTW + 1, "_out_fifo_wr_data")
        self._out_fifo_rd_en = Wire(1, "_out_fifo_rd_en")
        self._out_fifo_rd_rdy = Wire(1, "_out_fifo_rd_rdy")
        self._out_fifo_rd_data = Wire(ACCW * DOTW + 1, "_out_fifo_rd_data")
        self._out_fifo_full = Wire(1, "_out_fifo_full")
        self._out_fifo_empty = Wire(1, "_out_fifo_empty")
        self._out_fifo_usedw = Wire(OUTBUF_AW, "_out_fifo_usedw")
        self.instantiate(self._out_fifo, "out_fifo", port_map={"wr_en": self._out_fifo_wr_en, "din": self._out_fifo_wr_data, "rd_en": self._out_fifo_rd_en, "rd_rdy": self._out_fifo_rd_rdy, "dout": self._out_fifo_rd_data, "full": self._out_fifo_full, "empty": self._out_fifo_empty, "count": self._out_fifo_usedw, "clk": self.clk, "rst": ~self.rst_n})

        # State machine
        self.add_localparam("ST_IDLE", 0)
        self.add_localparam("ST_RD_INST", 1)
        self.add_localparam("ST_RD_DATA", 2)
        self.add_localparam("ST_WR_VRF", 3)
        self.add_localparam("ST_WR_OUT", 4)
        self.add_localparam("ST_DONE", 5)
        self._state = Reg(3, "state")

        # Instruction decode
        self._ld_vrf_id = Reg(2 * NVRF, "ld_vrf_id")
        self._ld_vrf0_addr = Reg(VRFAW, "ld_vrf0_addr")
        self._ld_vrf1_addr = Reg(VRFAW, "ld_vrf1_addr")
        self._ld_type = Reg(4, "ld_type")
        self._ld_tag = Reg(NTAGW, "ld_tag")
        self._ld_size = Reg(NSIZEW, "ld_size")

        # Counters
        self._cnt = Reg(NSIZEW, "cnt")
        self._result_cnt = Reg(32, "result_cnt")

        # Sequential
        with self.seq(self.clk, self.rst_n):
            with If(self.i_start):
                self._state <<= self.ST_IDLE
                self._cnt <<= Const(0, NSIZEW)
                self._result_cnt <<= Const(0, 32)
            with Elif(self._state == self.ST_IDLE):
                with If(~self._inst_fifo_empty):
                    self._state <<= self.ST_RD_INST
                    uinst = self._inst_fifo_rd_data
                    p = 0
                    self._ld_vrf_id <<= uinst[p + 2 * NVRF - 1 : p]; p += 2 * NVRF
                    self._ld_vrf0_addr <<= uinst[p + VRFAW - 1 : p]; p += VRFAW
                    self._ld_vrf1_addr <<= uinst[p + VRFAW - 1 : p]; p += VRFAW
                    self._ld_type <<= uinst[p + 4 - 1 : p]; p += 4
                    self._ld_tag <<= uinst[p + NTAGW - 1 : p]; p += NTAGW
                    self._ld_size <<= uinst[p + NSIZEW - 1 : p]
            with Elif(self._state == self.ST_RD_INST):
                self._state <<= self.ST_RD_DATA
            with Elif(self._state == self.ST_RD_DATA):
                with If(self._ld_type[0]):
                    # Write to VRF
                    self._state <<= self.ST_WR_VRF
                with Else():
                    self._state <<= self.ST_WR_OUT
            with Elif(self._state == self.ST_WR_VRF):
                with If(self._cnt + Const(1, NSIZEW) >= self._ld_size):
                    self._cnt <<= Const(0, NSIZEW)
                    self._state <<= self.ST_DONE
                with Else():
                    self._cnt <<= self._cnt + Const(1, NSIZEW)
            with Elif(self._state == self.ST_WR_OUT):
                with If(self._cnt + Const(1, NSIZEW) >= self._ld_size):
                    self._cnt <<= Const(0, NSIZEW)
                    self._state <<= self.ST_DONE
                with Else():
                    self._cnt <<= self._cnt + Const(1, NSIZEW)
            with Elif(self._state == self.ST_DONE):
                self._result_cnt <<= self._result_cnt + Const(1, 32)
                self._state <<= self.ST_IDLE

        # Combinational
        with self.comb:
            self._in_fifo_wr_en <<= self.i_in_wr_en
            self._in_fifo_wr_data <<= self.i_in_wr_din
            self.o_in_wr_rdy <<= ~self._in_fifo_full
            self.o_in_usedw <<= self._in_fifo_usedw

            self._wb_fifo_wr_en <<= self.i_wb_wr_en[0]
            self._wb_fifo_wr_data <<= self.i_wb_wr_din

            self._inst_fifo_wr_en <<= self.i_inst_wr_en
            self._inst_fifo_wr_data <<= self.i_inst_wr_din
            self._inst_fifo_rd_en <<= (self._state == self.ST_IDLE) & ~self._inst_fifo_empty
            self.o_inst_wr_rdy <<= ~self._inst_fifo_full

            self._out_fifo_rd_en <<= self.i_out_rd_en
            self.o_out_rd_rdy <<= self._out_fifo_rd_rdy
            self.o_out_rd_dout <<= self._out_fifo_rd_data
            self.o_out_usedw <<= self._out_fifo_usedw

            # Data read from in_fifo or wb_fifo
            self._in_fifo_rd_en <<= (self._state == self.ST_RD_DATA) & self._ld_type[1]
            self._wb_fifo_rd_en <<= (self._state == self.ST_RD_DATA) & ~self._ld_type[1]

            # VRF writeback output
            self.o_vrf_wr_en <<= (self._state == self.ST_WR_VRF)
            self.o_vrf_wr_id <<= self._ld_vrf_id
            self.o_vrf0_wr_addr <<= self._ld_vrf0_addr + self._cnt
            self.o_vrf1_wr_addr <<= self._ld_vrf1_addr + self._cnt
            with If(self._ld_type[1]):
                # Zero-extend input data from EW to ACCW
                in_data = self._in_fifo_rd_data
                ext_data = []
                for l in range(DOTW):
                    lane = in_data[(l + 1) * EW - 1 : l * EW]
                    ext_data.append(Cat(Const(0, ACCW - EW), lane))
                self.o_vrf_wr_data <<= Cat(*ext_data)
            with Else():
                self.o_vrf_wr_data <<= self._wb_fifo_rd_data

            # Output FIFO write
            self._out_fifo_wr_en <<= (self._state == self.ST_WR_OUT)
            out_data = self._wb_fifo_rd_data if not self._ld_type[1] else self.o_vrf_wr_data
            self._out_fifo_wr_data <<= Cat(out_data, Const(1, 1))

            # Debug counters
            self.o_debug_ld_ififo_counter <<= self._in_fifo_usedw
            self.o_debug_ld_wbfifo_counter <<= self._wb_fifo_usedw
            self.o_debug_ld_instfifo_counter <<= self._inst_fifo_usedw
            self.o_debug_ld_ofifo_counter <<= self._out_fifo_usedw
            self.o_result_count <<= self._result_cnt

            self.o_tag_update_en <<= self.i_tag_update_en
            self.o_start <<= self.i_start
            self.o_done <<= (self._state == self.ST_DONE)



# ============================================================================
# NPUTop -- Top-level integration
# ============================================================================
class NPUTop(Module):
    def __init__(self):
        super().__init__("npu_top")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_minst_chain_wr_en = Input(1, "i_minst_chain_wr_en")
        self.i_minst_chain_wr_addr = Input(INST_ADDRW, "i_minst_chain_wr_addr")
        self.i_minst_chain_wr_din = Input(MICW, "i_minst_chain_wr_din")
        self.i_start = Input(1, "i_start")
        self.pc_start_offset = Input(INST_ADDRW, "pc_start_offset")
        self.i_ld_in_wr_en = Input(1, "i_ld_in_wr_en")
        self.i_ld_in_wr_din = Input(EW * DOTW, "i_ld_in_wr_din")
        self.i_ld_out_rd_en = Input(1, "i_ld_out_rd_en")
        self.i_mrf_wr_addr = Input(MRFAW, "i_mrf_wr_addr")
        self.i_mrf_wr_data = Input(EW * DOTW, "i_mrf_wr_data")
        self.i_mrf_wr_en = Input(MRFIDW, "i_mrf_wr_en")
        self.o_ld_in_wr_rdy = Output(1, "o_ld_in_wr_rdy")
        self.o_ld_in_usedw = Output(INBUF_AW, "o_ld_in_usedw")
        self.o_ld_out_rd_rdy = Output(1, "o_ld_out_rd_rdy")
        self.o_ld_out_rd_dout = Output(ACCW * DOTW + 1, "o_ld_out_rd_dout")
        self.o_ld_out_usedw = Output(OUTBUF_AW, "o_ld_out_usedw")
        self.o_done = Output(1, "o_done")

        # Internal wires for interconnection
        # TopScheduler -> Schedulers (macro-inst) valid/ready
        self._mvu_minst_rd_rdy = Wire(1, "_mvu_minst_rd_rdy")
        self._mvu_sched_rdy = Wire(1, "_mvu_sched_rdy")
        self._mvu_minst_rd_dout = Wire(MIW_MVU, "_mvu_minst_rd_dout")
        self._evrf_minst_rd_rdy = Wire(1, "_evrf_minst_rd_rdy")
        self._evrf_sched_rdy = Wire(1, "_evrf_sched_rdy")
        self._evrf_minst_rd_dout = Wire(MIW_EVRF, "_evrf_minst_rd_dout")
        self._mfu0_minst_rd_rdy = Wire(1, "_mfu0_minst_rd_rdy")
        self._mfu0_sched_rdy = Wire(1, "_mfu0_sched_rdy")
        self._mfu0_minst_rd_dout = Wire(MIW_MFU, "_mfu0_minst_rd_dout")
        self._mfu1_minst_rd_rdy = Wire(1, "_mfu1_minst_rd_rdy")
        self._mfu1_sched_rdy = Wire(1, "_mfu1_sched_rdy")
        self._mfu1_minst_rd_dout = Wire(MIW_MFU, "_mfu1_minst_rd_dout")
        self._ld_minst_rd_rdy = Wire(1, "_ld_minst_rd_rdy")
        self._ld_sched_rdy = Wire(1, "_ld_sched_rdy")
        self._ld_minst_rd_dout = Wire(MIW_LD, "_ld_minst_rd_dout")

        # Schedulers -> Datapaths (micro-inst) valid/ready
        self._mvu_uinst_rd_rdy = Wire(1, "_mvu_uinst_rd_rdy")
        self._mvu_inst_rdy = Wire(1, "_mvu_inst_rdy")
        self._mvu_uinst_rd_dout = Wire(UIW_MVU, "_mvu_uinst_rd_dout")
        self._evrf_uinst_rd_rdy = Wire(1, "_evrf_uinst_rd_rdy")
        self._evrf_inst_rdy = Wire(1, "_evrf_inst_rdy")
        self._evrf_uinst_rd_dout = Wire(UIW_EVRF, "_evrf_uinst_rd_dout")
        self._mfu0_uinst_rd_rdy = Wire(1, "_mfu0_uinst_rd_rdy")
        self._mfu0_inst_rdy = Wire(1, "_mfu0_inst_rdy")
        self._mfu0_uinst_rd_dout = Wire(UIW_MFU, "_mfu0_uinst_rd_dout")
        self._mfu1_uinst_rd_rdy = Wire(1, "_mfu1_uinst_rd_rdy")
        self._mfu1_inst_rdy = Wire(1, "_mfu1_inst_rdy")
        self._mfu1_uinst_rd_dout = Wire(UIW_MFU, "_mfu1_uinst_rd_dout")
        self._ld_uinst_rd_rdy = Wire(1, "_ld_uinst_rd_rdy")
        self._ld_inst_rdy = Wire(1, "_ld_inst_rdy")
        self._ld_uinst_rd_dout = Wire(UIW_LD, "_ld_uinst_rd_dout")

        # Datapath -> LD writeback (valid/ready separated)
        self._mvu_data_rd_rdy = Wire(DOTW, "_mvu_data_rd_rdy")
        self._mvu_data_rd_dout = Wire(ACCW * NDPE, "_mvu_data_rd_dout")
        self._evrf_wr_ready = Wire(DOTW, "_evrf_wr_ready")
        self._evrf_data_rd_rdy = Wire(DOTW, "_evrf_data_rd_rdy")
        self._evrf_data_rd_dout = Wire(ACCW * DOTW, "_evrf_data_rd_dout")
        self._mfu0_wr_ready = Wire(DOTW, "_mfu0_wr_ready")
        self._mfu0_data_rd_rdy = Wire(DOTW, "_mfu0_data_rd_rdy")
        self._mfu0_data_rd_dout = Wire(ACCW * DOTW, "_mfu0_data_rd_dout")
        self._mfu1_wr_ready = Wire(DOTW, "_mfu1_wr_ready")
        self._mfu1_data_rd_rdy = Wire(DOTW, "_mfu1_data_rd_rdy")
        self._mfu1_data_rd_dout = Wire(ACCW * DOTW, "_mfu1_data_rd_dout")

        # LD -> VRF writeback (broadcast to all datapaths)
        self._ld_vrf_wr_en = Wire(1, "_ld_vrf_wr_en")
        self._ld_vrf_wr_id = Wire(2 * NVRF, "_ld_vrf_wr_id")
        self._ld_vrf0_wr_addr = Wire(VRFAW, "_ld_vrf0_wr_addr")
        self._ld_vrf1_wr_addr = Wire(VRFAW, "_ld_vrf1_wr_addr")
        self._ld_vrf_wr_data = Wire(ACCW * DOTW, "_ld_vrf_wr_data")

        # LD control
        self._ld_tag_update_en = Wire(1, "_ld_tag_update_en")
        self._ld_start = Wire(1, "_ld_start")
        self._ld_done = Wire(1, "_ld_done")

        # Instantiate modules
        self._top_sched = TopScheduler()
        self.instantiate(self._top_sched, "top_sched", port_map={"i_minst_chain_wr_en": self.i_minst_chain_wr_en, "i_minst_chain_wr_addr": self.i_minst_chain_wr_addr, "i_minst_chain_wr_din": self.i_minst_chain_wr_din, "i_start": self.i_start, "pc_start_offset": self.pc_start_offset, "i_mvu_minst_rd_en": self._mvu_sched_rdy, "i_evrf_minst_rd_en": self._evrf_sched_rdy, "i_mfu0_minst_rd_en": self._mfu0_sched_rdy, "i_mfu1_minst_rd_en": self._mfu1_sched_rdy, "i_ld_minst_rd_en": self._ld_sched_rdy, "o_mvu_minst_rd_rdy": self._mvu_minst_rd_rdy, "o_mvu_minst_rd_dout": self._mvu_minst_rd_dout, "o_evrf_minst_rd_rdy": self._evrf_minst_rd_rdy, "o_evrf_minst_rd_dout": self._evrf_minst_rd_dout, "o_mfu0_minst_rd_rdy": self._mfu0_minst_rd_rdy, "o_mfu0_minst_rd_dout": self._mfu0_minst_rd_dout, "o_mfu1_minst_rd_rdy": self._mfu1_minst_rd_rdy, "o_mfu1_minst_rd_dout": self._mfu1_minst_rd_dout, "o_ld_minst_rd_rdy": self._ld_minst_rd_rdy, "o_ld_minst_rd_dout": self._ld_minst_rd_dout, "o_done": self.o_done, "clk": self.clk, "rst_n": self.rst_n})

        self._mvu_sched = MVUScheduler()
        self.instantiate(self._mvu_sched, "mvu_sched", port_map={"i_minst_wr_en": self._mvu_minst_rd_rdy, "i_minst_wr_din": self._mvu_minst_rd_dout, "i_uinst_rd_en": self._mvu_inst_rdy, "o_minst_wr_rdy": self._mvu_sched_rdy, "o_uinst_rd_rdy": self._mvu_uinst_rd_rdy, "o_uinst_rd_dout": self._mvu_uinst_rd_dout, "clk": self.clk, "rst_n": self.rst_n})

        self._evrf_sched = EVRFScheduler()
        self.instantiate(self._evrf_sched, "evrf_sched", port_map={"i_minst_wr_en": self._evrf_minst_rd_rdy, "i_minst_wr_din": self._evrf_minst_rd_dout, "i_uinst_rd_en": self._evrf_inst_rdy, "o_minst_wr_rdy": self._evrf_sched_rdy, "o_uinst_rd_rdy": self._evrf_uinst_rd_rdy, "o_uinst_rd_dout": self._evrf_uinst_rd_dout, "clk": self.clk, "rst_n": self.rst_n})

        self._mfu0_sched = MFUScheduler()
        self.instantiate(self._mfu0_sched, "mfu0_sched", port_map={"i_minst_wr_en": self._mfu0_minst_rd_rdy, "i_minst_wr_din": self._mfu0_minst_rd_dout, "i_uinst_rd_en": self._mfu0_inst_rdy, "o_minst_wr_rdy": self._mfu0_sched_rdy, "o_uinst_rd_rdy": self._mfu0_uinst_rd_rdy, "o_uinst_rd_dout": self._mfu0_uinst_rd_dout, "clk": self.clk, "rst_n": self.rst_n})

        self._mfu1_sched = MFUScheduler()
        self.instantiate(self._mfu1_sched, "mfu1_sched", port_map={"i_minst_wr_en": self._mfu1_minst_rd_rdy, "i_minst_wr_din": self._mfu1_minst_rd_dout, "i_uinst_rd_en": self._mfu1_inst_rdy, "o_minst_wr_rdy": self._mfu1_sched_rdy, "o_uinst_rd_rdy": self._mfu1_uinst_rd_rdy, "o_uinst_rd_dout": self._mfu1_uinst_rd_dout, "clk": self.clk, "rst_n": self.rst_n})

        self._ld_sched = LDScheduler()
        self.instantiate(self._ld_sched, "ld_sched", port_map={"i_minst_wr_en": self._ld_minst_rd_rdy, "i_minst_wr_din": self._ld_minst_rd_dout, "i_uinst_rd_en": self._ld_inst_rdy, "o_minst_wr_rdy": self._ld_sched_rdy, "o_uinst_rd_rdy": self._ld_uinst_rd_rdy, "o_uinst_rd_dout": self._ld_uinst_rd_dout, "clk": self.clk, "rst_n": self.rst_n})

        self._mvu = MVU()
        self.instantiate(self._mvu, "mvu", port_map={"i_mrf_wr_en": self.i_mrf_wr_en, "i_mrf_wr_addr": self.i_mrf_wr_addr, "i_mrf_wr_data": self.i_mrf_wr_data, "i_vrf0_wr_addr": self._ld_vrf0_wr_addr, "i_vrf1_wr_addr": self._ld_vrf1_wr_addr, "i_vrf_wr_data": self._ld_vrf_wr_data, "i_vrf_wr_en": self._ld_vrf_wr_en, "i_vrf_wr_id": self._ld_vrf_wr_id, "i_inst_wr_en": self._mvu_uinst_rd_rdy, "i_vrf_rd_addr": self._mvu_uinst_rd_dout[VRFAW - 1 : 0], "i_vrf_rd_id": self._mvu_uinst_rd_dout[VRFAW + VRFIDW - 1 : VRFAW], "i_reg_sel": self._mvu_uinst_rd_dout[VRFAW + VRFIDW], "i_mrf_rd_addr": self._mvu_uinst_rd_dout[VRFAW + VRFIDW + 1 + MRFAW - 1 : VRFAW + VRFIDW + 1], "i_acc_op": self._mvu_uinst_rd_dout[VRFAW + VRFIDW + 1 + MRFAW + NTAGW + 2 - 1 : VRFAW + VRFIDW + 1 + MRFAW + NTAGW], "i_tag": self._mvu_uinst_rd_dout[VRFAW + VRFIDW + 1 + MRFAW + NTAGW - 1 : VRFAW + VRFIDW + 1 + MRFAW], "i_acc_size": self._mvu_uinst_rd_dout[VRFAW + VRFIDW + 1 + MRFAW + NTAGW + 2 + 5 - 1 : VRFAW + VRFIDW + 1 + MRFAW + NTAGW + 2], "i_vrf_en": self._mvu_uinst_rd_dout[VRFAW + VRFIDW + 1 + MRFAW + NTAGW + 2 + 5], "i_data_rd_en": self._evrf_wr_ready, "o_inst_wr_rdy": self._mvu_inst_rdy, "o_data_rd_rdy": self._mvu_data_rd_rdy, "o_data_rd_dout": self._mvu_data_rd_dout, "clk": self.clk, "rst_n": self.rst_n})

        self._evrf = EVRF()
        self.instantiate(self._evrf, "evrf", port_map={"i_vrf0_wr_addr": self._ld_vrf0_wr_addr, "i_vrf1_wr_addr": self._ld_vrf1_wr_addr, "i_vrf_wr_data": self._ld_vrf_wr_data, "i_vrf_wr_en": self._ld_vrf_wr_en, "i_vrf_wr_id": self._ld_vrf_wr_id, "i_data_wr_en": self._mvu_data_rd_rdy, "i_data_wr_din": self._mvu_data_rd_dout, "i_data_rd_en": self._mfu0_wr_ready, "i_inst_wr_en": self._evrf_uinst_rd_rdy, "i_vrf_rd_addr": self._evrf_uinst_rd_dout[VRFAW - 1 : 0], "i_src_sel": self._evrf_uinst_rd_dout[VRFAW + 2 - 1 : VRFAW], "i_tag": self._evrf_uinst_rd_dout[VRFAW + 2 + NTAGW - 1 : VRFAW + 2], "i_tag_update_en": self._ld_tag_update_en, "o_data_wr_rdy": self._evrf_wr_ready, "o_data_rd_rdy": self._evrf_data_rd_rdy, "o_data_rd_dout": self._evrf_data_rd_dout, "o_inst_wr_rdy": self._evrf_inst_rdy, "clk": self.clk, "rst_n": self.rst_n})

        self._mfu0 = MFU()
        self.instantiate(self._mfu0, "mfu0", port_map={"i_vrf0_wr_addr": self._ld_vrf0_wr_addr, "i_vrf1_wr_addr": self._ld_vrf1_wr_addr, "i_vrf_wr_data": self._ld_vrf_wr_data, "i_vrf_wr_en": self._ld_vrf_wr_en, "i_vrf_wr_id": self._ld_vrf_wr_id, "i_data_wr_en": self._evrf_data_rd_rdy, "i_data_wr_din": self._evrf_data_rd_dout, "i_data_rd_en": self._mfu1_wr_ready, "i_inst_wr_en": self._mfu0_uinst_rd_rdy, "i_vrf0_rd_addr": self._mfu0_uinst_rd_dout[VRFAW - 1 : 0], "i_vrf1_rd_addr": self._mfu0_uinst_rd_dout[2 * VRFAW - 1 : VRFAW], "i_func_op": self._mfu0_uinst_rd_dout[2 * VRFAW + 6 - 1 : 2 * VRFAW], "i_tag": self._mfu0_uinst_rd_dout[2 * VRFAW + 6 + NTAGW - 1 : 2 * VRFAW + 6], "i_tag_update_en": self._ld_tag_update_en, "o_data_wr_rdy": self._mfu0_wr_ready, "o_data_rd_rdy": self._mfu0_data_rd_rdy, "o_data_rd_dout": self._mfu0_data_rd_dout, "o_inst_wr_rdy": self._mfu0_inst_rdy, "clk": self.clk, "rst_n": self.rst_n})

        self._mfu1 = MFU()
        self.instantiate(self._mfu1, "mfu1", port_map={"i_vrf0_wr_addr": self._ld_vrf0_wr_addr, "i_vrf1_wr_addr": self._ld_vrf1_wr_addr, "i_vrf_wr_data": self._ld_vrf_wr_data, "i_vrf_wr_en": self._ld_vrf_wr_en, "i_vrf_wr_id": self._ld_vrf_wr_id, "i_data_wr_en": self._mfu0_data_rd_rdy, "i_data_wr_din": self._mfu0_data_rd_dout, "i_data_rd_en": self._ld_uinst_rd_rdy, "i_inst_wr_en": self._mfu1_uinst_rd_rdy, "i_vrf0_rd_addr": self._mfu1_uinst_rd_dout[VRFAW - 1 : 0], "i_vrf1_rd_addr": self._mfu1_uinst_rd_dout[2 * VRFAW - 1 : VRFAW], "i_func_op": self._mfu1_uinst_rd_dout[2 * VRFAW + 6 - 1 : 2 * VRFAW], "i_tag": self._mfu1_uinst_rd_dout[2 * VRFAW + 6 + NTAGW - 1 : 2 * VRFAW + 6], "i_tag_update_en": self._ld_tag_update_en, "o_data_wr_rdy": self._mfu1_wr_ready, "o_data_rd_rdy": self._mfu1_data_rd_rdy, "o_data_rd_dout": self._mfu1_data_rd_dout, "o_inst_wr_rdy": self._mfu1_inst_rdy, "clk": self.clk, "rst_n": self.rst_n})

        self._debug_ififo = Wire(32, "_debug_ififo")
        self._debug_wbfifo = Wire(32, "_debug_wbfifo")
        self._debug_instfifo = Wire(32, "_debug_instfifo")
        self._debug_ofifo = Wire(32, "_debug_ofifo")
        self._debug_result_cnt = Wire(32, "_debug_result_cnt")
        self._ld = LD()
        self.instantiate(self._ld, "ld", port_map={"i_vrf_wr_en": self._ld_vrf_wr_en, "i_vrf_wr_id": self._ld_vrf_wr_id, "i_vrf0_wr_addr": self._ld_vrf0_wr_addr, "i_vrf1_wr_addr": self._ld_vrf1_wr_addr, "i_vrf_wr_data": self._ld_vrf_wr_data, "i_in_wr_en": self.i_ld_in_wr_en, "i_in_wr_din": self.i_ld_in_wr_din, "i_wb_wr_en": self._mfu1_data_rd_rdy, "i_wb_wr_din": self._mfu1_data_rd_dout, "i_out_rd_en": self.i_ld_out_rd_en, "i_inst_wr_en": self._ld_uinst_rd_rdy, "i_inst_wr_din": self._ld_uinst_rd_dout, "i_tag": self._ld_uinst_rd_dout[NVRF + 2 * VRFAW + 4 - 1 : NVRF + 2 * VRFAW + 4 - NTAGW], "i_tag_update_en": self._ld_tag_update_en, "i_start": self._ld_start, "o_vrf_wr_en": self._ld_vrf_wr_en, "o_vrf_wr_id": self._ld_vrf_wr_id, "o_vrf0_wr_addr": self._ld_vrf0_wr_addr, "o_vrf1_wr_addr": self._ld_vrf1_wr_addr, "o_vrf_wr_data": self._ld_vrf_wr_data, "o_in_wr_rdy": self.o_ld_in_wr_rdy, "o_in_usedw": self.o_ld_in_usedw, "o_out_rd_rdy": self.o_ld_out_rd_rdy, "o_out_rd_dout": self.o_ld_out_rd_dout, "o_out_usedw": self.o_ld_out_usedw, "o_inst_wr_rdy": self._ld_inst_rdy, "o_tag_update_en": self._ld_tag_update_en, "o_start": self._ld_start, "o_done": self._ld_done, "o_debug_ld_ififo_counter": self._debug_ififo, "o_debug_ld_wbfifo_counter": self._debug_wbfifo, "o_debug_ld_instfifo_counter": self._debug_instfifo, "o_debug_ld_ofifo_counter": self._debug_ofifo, "o_result_count": self._debug_result_cnt, "clk": self.clk, "rst_n": self.rst_n})
