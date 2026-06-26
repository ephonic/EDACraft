"""dsl_modules — DSL Reference Implementations

Extracted from design_interfaces.py.
"""
from __future__ import annotations

from rtlgen import (
    Input, Output, Wire, Reg, Module, Vector, Array, VerilogEmitter,
    ArchDefinition, ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec, HandshakeSpec, QueueSpec,
    ArchSimulator, ArchSkeletonGenerator,
    BehavioralSpec, StrategySpec, DecompositionResult,
    Memory, Parameter, LocalParam,
)
from rtlgen.logic import If, Else, Elif, When, Otherwise, Const, Cat, Mux, Switch, Rep, ForGen
from rtlgen.lib import SyncFIFO
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template



class AXIS_REGISTER(Module):
    """AXI-Stream skid buffer register — bubble-free 1-stage pipeline.

    Reference: ref_rtl/interfaces/axis/rtl/axis_register.v (REG_TYPE=2)
    - Output register + temp register for skid buffering
    - No bubble cycles: can accept input even when output not ready
    - Fixed configuration: data_width only (no tkeep/tid/tdest/tuser)
    """

    def __init__(self, data_width=8):
        super().__init__("axis_register")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI-Stream input
        self.s_axis_tdata = Input(data_width, "s_axis_tdata")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")

        # AXI-Stream output
        self.m_axis_tdata = Output(data_width, "m_axis_tdata")
        self.m_axis_tvalid = Output(1, "m_axis_tvalid")
        self.m_axis_tready = Input(1, "m_axis_tready")

        # Output registers
        self._s_axis_tready_reg = Reg(1, "s_axis_tready_reg", init_value=0)
        self._m_axis_tdata_reg = Reg(data_width, "m_axis_tdata_reg", init_value=0)
        self._m_axis_tvalid_reg = Reg(1, "m_axis_tvalid_reg", init_value=0)

        # Temp (skid) registers
        self._temp_m_axis_tdata_reg = Reg(data_width, "temp_m_axis_tdata_reg", init_value=0)
        self._temp_m_axis_tvalid_reg = Reg(1, "temp_m_axis_tvalid_reg", init_value=0)

        # Next-state wires (combinational)
        self._m_axis_tvalid_next = Wire(1, "m_axis_tvalid_next")
        self._temp_m_axis_tvalid_next = Wire(1, "temp_m_axis_tvalid_next")
        self._store_input_to_output = Wire(1, "store_input_to_output")
        self._store_input_to_temp = Wire(1, "store_input_to_temp")
        self._store_temp_to_output = Wire(1, "store_temp_to_output")
        self._s_axis_tready_early = Wire(1, "s_axis_tready_early")

        with self.comb:
            self.s_axis_tready <<= self._s_axis_tready_reg
            self.m_axis_tdata <<= self._m_axis_tdata_reg
            self.m_axis_tvalid <<= self._m_axis_tvalid_reg

            # Ready early: output ready OR temp empty AND (output empty OR no input)
            self._s_axis_tready_early <<= (
                self.m_axis_tready
                | (~self._temp_m_axis_tvalid_reg
                   & (~self._m_axis_tvalid_reg | ~self.s_axis_tvalid))
            )

            # Default next states
            self._m_axis_tvalid_next <<= self._m_axis_tvalid_reg
            self._temp_m_axis_tvalid_next <<= self._temp_m_axis_tvalid_reg
            self._store_input_to_output <<= 0
            self._store_input_to_temp <<= 0
            self._store_temp_to_output <<= 0

            with If(self._s_axis_tready_reg == 1):
                # Input is ready
                with If((self.m_axis_tready == 1) | (self._m_axis_tvalid_reg == 0)):
                    # Output ready or invalid: transfer to output
                    self._m_axis_tvalid_next <<= self.s_axis_tvalid
                    self._store_input_to_output <<= 1
                with Else():
                    # Output not ready: store in temp
                    self._temp_m_axis_tvalid_next <<= self.s_axis_tvalid
                    self._store_input_to_temp <<= 1
            with Else():
                with If(self.m_axis_tready == 1):
                    # Input not ready but output ready: drain temp
                    self._m_axis_tvalid_next <<= self._temp_m_axis_tvalid_reg
                    self._temp_m_axis_tvalid_next <<= 0
                    self._store_temp_to_output <<= 1

        with self.seq(self.clk):
            self._s_axis_tready_reg <<= self._s_axis_tready_early
            self._m_axis_tvalid_reg <<= self._m_axis_tvalid_next
            self._temp_m_axis_tvalid_reg <<= self._temp_m_axis_tvalid_next

            with If(self._store_input_to_output == 1):
                self._m_axis_tdata_reg <<= self.s_axis_tdata
            with Else():
                with If(self._store_temp_to_output == 1):
                    self._m_axis_tdata_reg <<= self._temp_m_axis_tdata_reg

            with If(self._store_input_to_temp == 1):
                self._temp_m_axis_tdata_reg <<= self.s_axis_tdata

            with If(self.rst == 1):
                self._s_axis_tready_reg <<= 0
                self._m_axis_tvalid_reg <<= 0
                self._temp_m_axis_tvalid_reg <<= 0

        tpl = ModuleDocTemplate(
            source="AXIS_REGISTER — ref_rtl/interfaces/axis/rtl/axis_register.v",
            description=f"{data_width}-bit AXI-Stream skid buffer register. "
                        "Bubble-free pipeline stage.",
            author="rtlgen agent", version="1.0",
            timing="Registered: 1-cycle latency, no bubble cycles",
        )
        fill_doc_template(tpl, self)


class AXIS_ADAPTER(Module):
    """AXI-Stream width adapter: 8-bit input → 32-bit output (up-size).

    Reference: ref_rtl/interfaces/axis/rtl/axis_adapter.v (upsize branch)
    - Collects 4 input bytes into one output word
    - Supports tlast propagation
    - Skid buffer for input when output not ready
    """

    def __init__(self, s_data_width=8, m_data_width=32):
        super().__init__("axis_adapter")
        self.S_DATA_WIDTH = Parameter(s_data_width, "S_DATA_WIDTH")
        self.M_DATA_WIDTH = Parameter(m_data_width, "M_DATA_WIDTH")
        seg_count = m_data_width // s_data_width
        self.SEG_COUNT = Parameter(seg_count, "SEG_COUNT")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI-Stream input (narrow)
        self.s_axis_tdata = Input(s_data_width, "s_axis_tdata")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")
        self.s_axis_tlast = Input(1, "s_axis_tlast")

        # AXI-Stream output (wide)
        self.m_axis_tdata = Output(m_data_width, "m_axis_tdata")
        self.m_axis_tvalid = Output(1, "m_axis_tvalid")
        self.m_axis_tready = Input(1, "m_axis_tready")
        self.m_axis_tlast = Output(1, "m_axis_tlast")

        self._build_with_seg_regs(s_data_width, m_data_width, seg_count)

        tpl = ModuleDocTemplate(
            source="AXIS_ADAPTER — ref_rtl/interfaces/axis/rtl/axis_adapter.v",
            description=f"AXI-Stream width adapter: {s_data_width}-bit → {m_data_width}-bit up-size. "
                        "Collects input segments with skid buffer and tlast propagation.",
            author="rtlgen agent", version="1.0",
            timing="Registered: variable latency, skid-buffered input",
        )
        fill_doc_template(tpl, self)

    def _build_with_seg_regs(self, s_data_width, m_data_width, seg_count):
        """Rebuild logic using per-segment registers (no dynamic slices)."""
        seg_bits = max(seg_count.bit_length(), 1)

        # Per-segment output registers
        self._seg_out = [Reg(s_data_width, f"seg_out_{i}", init_value=0)
                         for i in range(seg_count)]

        # Input skid buffer
        self._s_data_reg = Reg(s_data_width, "s_data_reg", init_value=0)
        self._s_valid_reg = Reg(1, "s_valid_reg", init_value=0)
        self._s_last_reg = Reg(1, "s_last_reg", init_value=0)

        self._seg_cnt = Reg(seg_bits, "seg_cnt", init_value=0)
        self._m_valid_reg = Reg(1, "m_valid_reg", init_value=0)
        self._m_last_reg = Reg(1, "m_last_reg", init_value=0)

        # Next-state wires (computed combinationally, sampled at clk)
        self._slot_avail = Wire(1, "slot_avail")
        self._have_data = Wire(1, "have_data")
        self._data_in = Wire(s_data_width, "data_in")
        self._last_in = Wire(1, "last_in")
        self._seg_cnt_next = Wire(seg_bits, "seg_cnt_next")
        self._m_valid_next = Wire(1, "m_valid_next")
        self._m_last_next = Wire(1, "m_last_next")
        self._s_valid_next = Wire(1, "s_valid_next")
        self._store_to_seg = Wire(1, "store_to_seg")

        with self.comb:
            self.s_axis_tready <<= self._slot_avail & ~self._s_valid_reg
            self.m_axis_tvalid <<= self._m_valid_reg
            self.m_axis_tlast <<= self._m_last_reg
            self.m_axis_tdata <<= Cat(*[self._seg_out[i] for i in range(seg_count - 1, -1, -1)])

            # Slot available when output empty or being consumed
            self._slot_avail <<= ~self._m_valid_reg | self.m_axis_tready

            # Data source: skid buffer first, then direct input
            self._have_data <<= self._s_valid_reg | self.s_axis_tvalid
            self._data_in <<= Mux(self._s_valid_reg, self._s_data_reg, self.s_axis_tdata)
            self._last_in <<= Mux(self._s_valid_reg, self._s_last_reg, self.s_axis_tlast)

            # Default next states (hold)
            self._seg_cnt_next <<= self._seg_cnt
            self._m_valid_next <<= self._m_valid_reg
            self._m_last_next <<= self._m_last_reg
            self._s_valid_next <<= self._s_valid_reg
            self._store_to_seg <<= 0

            with If(self._slot_avail):
                with If(self._have_data):
                    self._store_to_seg <<= 1
                    with If(self._last_in | (self._seg_cnt == seg_count - 1)):
                        self._seg_cnt_next <<= 0
                        self._m_valid_next <<= 1
                        self._m_last_next <<= self._last_in
                    with Else():
                        self._seg_cnt_next <<= self._seg_cnt + 1
                    # If consuming from skid buffer, clear it
                    with If(self._s_valid_reg):
                        self._s_valid_next <<= 0

            # If input arrives but slot is busy, buffer it
            with If(self.s_axis_tvalid & ~self.s_axis_tready):
                self._s_valid_next <<= 1

        with self.seq(self.clk):
            self._m_valid_reg <<= self._m_valid_next
            self._m_last_reg <<= self._m_last_next
            self._seg_cnt <<= self._seg_cnt_next
            self._s_valid_reg <<= self._s_valid_next

            with If(self._store_to_seg):
                for i in range(seg_count):
                    with If(self._seg_cnt == i):
                        self._seg_out[i] <<= self._data_in

            with If((self.s_axis_tvalid == 1) & (self.s_axis_tready == 1)):
                self._s_data_reg <<= self.s_axis_tdata
                self._s_last_reg <<= self.s_axis_tlast

            with If(self.rst == 1):
                self._seg_cnt <<= 0
                self._s_valid_reg <<= 0
                self._m_valid_reg <<= 0
                self._m_last_reg <<= 0
                for i in range(seg_count):
                    self._seg_out[i] <<= 0


class AXIS_BROADCAST(Module):
    """AXI-Stream broadcaster: 1 input → M_COUNT outputs.

    Reference: ref_rtl/interfaces/axis/rtl/axis_broadcast.v
    - Replicates input data to all outputs
    - Uses skid buffer logic for back-pressure handling
    - All outputs share the same data, individual valid/ready
    """

    def __init__(self, m_count=4, data_width=8):
        super().__init__("axis_broadcast")
        self.M_COUNT = Parameter(m_count, "M_COUNT")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI-Stream input
        self.s_axis_tdata = Input(data_width, "s_axis_tdata")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")

        # AXI-Stream outputs (packed)
        self.m_axis_tdata = Output(m_count * data_width, "m_axis_tdata")
        self.m_axis_tvalid = Output(m_count, "m_axis_tvalid")
        self.m_axis_tready = Input(m_count, "m_axis_tready")

        # Registers
        self._s_axis_tready_reg = Reg(1, "s_axis_tready_reg", init_value=0)
        self._m_axis_tdata_reg = Reg(data_width, "m_axis_tdata_reg", init_value=0)
        self._m_axis_tvalid_reg = Reg(m_count, "m_axis_tvalid_reg", init_value=0)

        self._temp_m_axis_tdata_reg = Reg(data_width, "temp_m_axis_tdata_reg", init_value=0)
        self._temp_m_axis_tvalid_reg = Reg(1, "temp_m_axis_tvalid_reg", init_value=0)

        # Next-state wires
        self._m_axis_tvalid_next = Wire(m_count, "m_axis_tvalid_next")
        self._temp_m_axis_tvalid_next = Wire(1, "temp_m_axis_tvalid_next")
        self._store_input_to_output = Wire(1, "store_input_to_output")
        self._store_input_to_temp = Wire(1, "store_input_to_temp")
        self._store_temp_to_output = Wire(1, "store_temp_to_output")
        self._s_axis_tready_early = Wire(1, "s_axis_tready_early")

        # Output ready check: all ready where valid is asserted
        self._all_ready = Wire(1, "all_ready")
        self._valid_any = Wire(1, "valid_any")

        with self.comb:
            self.s_axis_tready <<= self._s_axis_tready_reg
            # Broadcast data to all outputs
            data_bits = []
            for i in range(m_count):
                data_bits.append(self._m_axis_tdata_reg)
            self.m_axis_tdata <<= Cat(*data_bits)
            self.m_axis_tvalid <<= self._m_axis_tvalid_reg

            # all_ready = ((m_ready & m_valid) == m_valid)
            self._all_ready <<= ((self.m_axis_tready & self._m_axis_tvalid_reg) == self._m_axis_tvalid_reg)
            # OR-reduce of valid_reg
            valid_or = self._m_axis_tvalid_reg[0]
            for i in range(1, m_count):
                valid_or = valid_or | self._m_axis_tvalid_reg[i]
            self._valid_any <<= valid_or
            self._s_axis_tready_early <<= self._all_ready | (~self._temp_m_axis_tvalid_reg & (~self._valid_any | ~self.s_axis_tvalid))

            self._m_axis_tvalid_next <<= self._m_axis_tvalid_reg & ~self.m_axis_tready
            self._temp_m_axis_tvalid_next <<= self._temp_m_axis_tvalid_reg
            self._store_input_to_output <<= 0
            self._store_input_to_temp <<= 0
            self._store_temp_to_output <<= 0

            with If(self._s_axis_tready_reg == 1):
                with If(self._all_ready | ~self._valid_any):
                    self._m_axis_tvalid_next <<= Rep(self.s_axis_tvalid, m_count)
                    self._store_input_to_output <<= 1
                with Else():
                    self._temp_m_axis_tvalid_next <<= self.s_axis_tvalid
                    self._store_input_to_temp <<= 1
            with Else():
                with If(self._all_ready):
                    self._m_axis_tvalid_next <<= Rep(self._temp_m_axis_tvalid_reg, m_count)
                    self._temp_m_axis_tvalid_next <<= 0
                    self._store_temp_to_output <<= 1

        with self.seq(self.clk):
            self._s_axis_tready_reg <<= self._s_axis_tready_early
            self._m_axis_tvalid_reg <<= self._m_axis_tvalid_next
            self._temp_m_axis_tvalid_reg <<= self._temp_m_axis_tvalid_next

            with If(self._store_input_to_output == 1):
                self._m_axis_tdata_reg <<= self.s_axis_tdata
            with Else():
                with If(self._store_temp_to_output == 1):
                    self._m_axis_tdata_reg <<= self._temp_m_axis_tdata_reg

            with If(self._store_input_to_temp == 1):
                self._temp_m_axis_tdata_reg <<= self.s_axis_tdata

            with If(self.rst == 1):
                self._s_axis_tready_reg <<= 0
                self._m_axis_tvalid_reg <<= Const(0, m_count)
                self._temp_m_axis_tvalid_reg <<= 0

        tpl = ModuleDocTemplate(
            source="AXIS_BROADCAST — ref_rtl/interfaces/axis/rtl/axis_broadcast.v",
            description=f"AXI-Stream broadcaster: 1→{m_count}, {data_width}-bit. "
                        "Skid buffer back-pressure handling.",
            author="rtlgen agent", version="1.0",
            timing="Registered: 1-cycle latency, all outputs synchronized",
        )
        fill_doc_template(tpl, self)
