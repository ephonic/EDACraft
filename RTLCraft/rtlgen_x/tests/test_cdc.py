import pytest

from rtlgen_x.dsl import Array, AsyncFIFO, DslLoweringReport, Else, If, Input, LoweredDslModule, Module, Output, ReadyValidAsyncBridge, Reg, Wire
from rtlgen_x.dsl.lib import AsyncResetRel, SyncCell
from rtlgen_x.sim import (
    Assignment,
    ClockDomain,
    ConstExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    Signal,
    SignalRef,
    SimModule,
    UnaryExpr,
)
from rtlgen_x.verify.cdc import analyze_cdc, emit_cdc_report_markdown


def _lowered(module: SimModule) -> LoweredDslModule:
    return LoweredDslModule(
        module=module,
        report=DslLoweringReport(
            source_module=module.name,
            flattened_module=module.name,
            signal_count=len(module.signals),
            assignment_count=len(module.assignments),
            outputs_post_state=module.outputs_post_state,
        ),
    )


class UnsafeSingleBitCrossing(Module):
    def __init__(self):
        super().__init__("unsafe_single_bit_crossing")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.flag_in = Input(1, "flag_in")
        self.flag_seen = Output(1, "flag_seen")
        self.flag_q = Reg(1, "flag_q")
        self.flag_seen_q = Reg(1, "flag_seen_q")

        @self.comb
        def _comb():
            self.flag_seen <<= self.flag_seen_q

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.flag_q <<= 0
            with Else():
                self.flag_q <<= self.flag_in

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.flag_seen_q <<= 0
            with Else():
                self.flag_seen_q <<= self.flag_q


class UnsafeToggleCrossing(Module):
    def __init__(self):
        super().__init__("unsafe_toggle_crossing")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.event_in = Input(1, "event_in")
        self.event_seen = Output(1, "event_seen")
        self.toggle_src = Reg(1, "toggle_src")
        self.toggle_seen = Reg(1, "toggle_seen")

        @self.comb
        def _comb():
            self.event_seen <<= self.toggle_seen

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.toggle_src <<= 0
            with Else():
                with If(self.event_in == 1):
                    self.toggle_src <<= ~self.toggle_src

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.toggle_seen <<= 0
            with Else():
                self.toggle_seen <<= self.toggle_src


class UnsafeBusCrossing(Module):
    def __init__(self):
        super().__init__("unsafe_bus_crossing")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.data_in = Input(8, "data_in")
        self.data_out = Output(8, "data_out")
        self.data_q = Reg(8, "data_q")
        self.data_seen = Reg(8, "data_seen")

        @self.comb
        def _comb():
            self.data_out <<= self.data_seen

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.data_q <<= 0
            with Else():
                self.data_q <<= self.data_in

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.data_seen <<= 0
            with Else():
                self.data_seen <<= self.data_q


class UnsafeArrayMailbox(Module):
    def __init__(self):
        super().__init__("unsafe_array_mailbox")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.rf = Array(8, 4, "rf")
        self.wptr = Reg(2, "wptr")
        self.rptr = Reg(2, "rptr")

        @self.comb
        def _comb():
            self.dout <<= self.rf[self.rptr]

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.wptr <<= 0
            with Else():
                with If(self.wr_en == 1):
                    self.rf[self.wptr] <<= self.din
                    self.wptr <<= self.wptr + 1

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.rptr <<= 0
            with Else():
                with If(self.rd_en == 1):
                    self.rptr <<= self.rptr + 1


class SafeSyncCellCrossing(Module):
    def __init__(self):
        super().__init__("safe_sync_cell_crossing")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.flag_in = Input(1, "flag_in")
        self.flag_seen = Output(1, "flag_seen")
        self.flag_q = Reg(1, "flag_q")
        self.sync = SyncCell(width=1, name="sync")

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.flag_q <<= 0
            with Else():
                self.flag_q <<= self.flag_in

        self.instantiate(
            self.sync,
            "u_sync",
            port_map={
                "clk": self.rd_clk,
                "rst": self.rd_rst,
                "data_in": self.flag_q,
                "data_out": self.flag_seen,
            },
        )


class SafeAsyncFifoCrossing(Module):
    def __init__(self):
        super().__init__("safe_async_fifo_crossing")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self.fifo = AsyncFIFO(width=8, depth=4, name="fifo")

        self.instantiate(
            self.fifo,
            "u_fifo",
            port_map={
                "wr_clk": self.wr_clk,
                "rd_clk": self.rd_clk,
                "wr_rst": self.wr_rst,
                "rd_rst": self.rd_rst,
                "wr_en": self.wr_en,
                "rd_en": self.rd_en,
                "din": self.din,
                "dout": self.dout,
                "full": self.full,
                "empty": self.empty,
            },
        )


class SafeReadyValidAsyncBridgeCrossing(Module):
    def __init__(self):
        super().__init__("safe_ready_valid_async_bridge_crossing")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.in_data = Input(8, "in_data")
        self.in_valid = Input(1, "in_valid")
        self.in_ready = Output(1, "in_ready")
        self.out_data = Output(8, "out_data")
        self.out_valid = Output(1, "out_valid")
        self.out_ready = Input(1, "out_ready")
        self.bridge = ReadyValidAsyncBridge(width=8, depth=4, name="bridge")

        self.instantiate(
            self.bridge,
            "u_bridge",
            port_map={
                "wr_clk": self.wr_clk,
                "rd_clk": self.rd_clk,
                "wr_rst": self.wr_rst,
                "rd_rst": self.rd_rst,
                "in_data": self.in_data,
                "in_valid": self.in_valid,
                "in_ready": self.in_ready,
                "out_data": self.out_data,
                "out_valid": self.out_valid,
                "out_ready": self.out_ready,
            },
        )


class MultiWriterStateHazard(Module):
    def __init__(self):
        super().__init__("multi_writer_state_hazard")
        self.a_clk = Input(1, "a_clk")
        self.b_clk = Input(1, "b_clk")
        self.a_rst = Input(1, "a_rst")
        self.b_rst = Input(1, "b_rst")
        self.out = Output(8, "out")
        self.shared = Reg(8, "shared")

        @self.comb
        def _comb():
            self.out <<= self.shared

        @self.seq(self.a_clk, self.a_rst)
        def _a_seq():
            with If(self.a_rst == 1):
                self.shared <<= 0
            with Else():
                self.shared <<= self.shared + 1

        @self.seq(self.b_clk, self.b_rst)
        def _b_seq():
            with If(self.b_rst == 1):
                self.shared <<= 0
            with Else():
                self.shared <<= self.shared + 2


class SafeHandwrittenSyncCrossing(Module):
    def __init__(self):
        super().__init__("safe_handwritten_sync_crossing")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.flag_in = Input(1, "flag_in")
        self.flag_seen = Output(1, "flag_seen")
        self.flag_q = Reg(1, "flag_q")
        self.sync_ff1 = Reg(1, "sync_ff1")
        self.sync_ff2 = Reg(1, "sync_ff2")

        @self.comb
        def _comb():
            self.flag_seen <<= self.sync_ff2

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.flag_q <<= 0
            with Else():
                self.flag_q <<= self.flag_in

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.sync_ff1 <<= 0
                self.sync_ff2 <<= 0
            with Else():
                self.sync_ff1 <<= self.flag_q
                self.sync_ff2 <<= self.sync_ff1


class SafeHandwrittenSyncCrossingWithAlias(Module):
    def __init__(self):
        super().__init__("safe_handwritten_sync_crossing_with_alias")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.flag_in = Input(1, "flag_in")
        self.flag_seen = Output(1, "flag_seen")
        self.flag_q = Reg(1, "flag_q")
        self.sync_ff1 = Reg(1, "sync_ff1")
        self.sync_ff2 = Reg(1, "sync_ff2")
        self.sync_alias = Wire(1, "sync_alias")

        @self.comb
        def _comb():
            self.sync_alias <<= self.sync_ff2
            self.flag_seen <<= self.sync_alias

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.flag_q <<= 0
            with Else():
                self.flag_q <<= self.flag_in

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.sync_ff1 <<= 0
                self.sync_ff2 <<= 0
            with Else():
                self.sync_ff1 <<= self.flag_q
                self.sync_ff2 <<= self.sync_ff1


class SafeHandwrittenSyncCrossingWithTap(Module):
    def __init__(self):
        super().__init__("safe_handwritten_sync_crossing_with_tap")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.flag_in = Input(1, "flag_in")
        self.flag_seen = Output(1, "flag_seen")
        self.sync_dbg = Output(1, "sync_dbg")
        self.flag_q = Reg(1, "flag_q")
        self.sync_ff1 = Reg(1, "sync_ff1")
        self.sync_ff2 = Reg(1, "sync_ff2")
        self.sync_alias = Wire(1, "sync_alias")

        @self.comb
        def _comb():
            self.sync_alias <<= self.sync_ff2
            self.flag_seen <<= self.sync_alias
            self.sync_dbg <<= self.sync_ff2

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.flag_q <<= 0
            with Else():
                self.flag_q <<= self.flag_in

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.sync_ff1 <<= 0
                self.sync_ff2 <<= 0
            with Else():
                self.sync_ff1 <<= self.flag_q
                self.sync_ff2 <<= self.sync_ff1


class SafeHandwrittenPulseSynchronizer(Module):
    def __init__(self):
        super().__init__("safe_handwritten_pulse_synchronizer")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.event_in = Input(1, "event_in")
        self.event_seen = Output(1, "event_seen")
        self.toggle_src = Reg(1, "toggle_src")
        self.sync_ff0 = Reg(1, "sync_ff0")
        self.sync_ff1 = Reg(1, "sync_ff1")
        self.sync_ff2 = Reg(1, "sync_ff2")

        @self.comb
        def _comb():
            self.event_seen <<= self.sync_ff1 ^ self.sync_ff2

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.toggle_src <<= 0
            with Else():
                with If(self.event_in == 1):
                    self.toggle_src <<= ~self.toggle_src

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.sync_ff0 <<= 0
                self.sync_ff1 <<= 0
                self.sync_ff2 <<= 0
            with Else():
                self.sync_ff0 <<= self.toggle_src
                self.sync_ff1 <<= self.sync_ff0
                self.sync_ff2 <<= self.sync_ff1


class SafeHandwrittenPulseSynchronizerWithAlias(Module):
    def __init__(self):
        super().__init__("safe_handwritten_pulse_synchronizer_with_alias")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.event_in = Input(1, "event_in")
        self.event_seen = Output(1, "event_seen")
        self.event_dbg = Output(1, "event_dbg")
        self.toggle_src = Reg(1, "toggle_src")
        self.sync_ff0 = Reg(1, "sync_ff0")
        self.sync_ff1 = Reg(1, "sync_ff1")
        self.sync_ff2 = Reg(1, "sync_ff2")
        self.event_pulse = Wire(1, "event_pulse")

        @self.comb
        def _comb():
            self.event_pulse <<= self.sync_ff1 ^ self.sync_ff2
            self.event_seen <<= self.event_pulse
            self.event_dbg <<= self.sync_ff2

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.toggle_src <<= 0
            with Else():
                with If(self.event_in == 1):
                    self.toggle_src <<= ~self.toggle_src

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.sync_ff0 <<= 0
                self.sync_ff1 <<= 0
                self.sync_ff2 <<= 0
            with Else():
                self.sync_ff0 <<= self.toggle_src
                self.sync_ff1 <<= self.sync_ff0
                self.sync_ff2 <<= self.sync_ff1


class UnsafeAsyncResetRelease(Module):
    def __init__(self):
        super().__init__("unsafe_async_reset_release")
        self.core_clk = Input(1, "core_clk")
        self.rst_async = Input(1, "rst_async")
        self.data_in = Input(1, "data_in")
        self.data_q = Reg(1, "data_q")
        self.data_out = Output(1, "data_out")

        @self.comb
        def _comb():
            self.data_out <<= self.data_q

        @self.seq(self.core_clk, self.rst_async, reset_async=True)
        def _core_seq():
            with If(self.rst_async == 1):
                self.data_q <<= 0
            with Else():
                self.data_q <<= self.data_in


class SafePrimitiveAsyncResetRelease(Module):
    def __init__(self):
        super().__init__("safe_primitive_async_reset_release")
        self.core_clk = Input(1, "core_clk")
        self.rst_async = Input(1, "rst_async")
        self.data_in = Input(1, "data_in")
        self.rst_sync = Wire(1, "rst_sync")
        self.data_q = Reg(1, "data_q")
        self.data_out = Output(1, "data_out")
        self.reset_rel = AsyncResetRel(name="reset_rel")

        @self.comb
        def _comb():
            self.data_out <<= self.data_q

        self.instantiate(
            self.reset_rel,
            "u_reset_rel",
            port_map={
                "clk": self.core_clk,
                "rst_async": self.rst_async,
                "rst_sync": self.rst_sync,
            },
        )

        @self.seq(self.core_clk, self.rst_sync, reset_async=True)
        def _core_seq():
            with If(self.rst_sync == 1):
                self.data_q <<= 0
            with Else():
                self.data_q <<= self.data_in


class SafeHandwrittenAsyncResetRelease(Module):
    def __init__(self):
        super().__init__("safe_handwritten_async_reset_release")
        self.core_clk = Input(1, "core_clk")
        self.rst_async = Input(1, "rst_async")
        self.data_in = Input(1, "data_in")
        self.rst_ff1 = Reg(1, "rst_ff1")
        self.rst_ff2 = Reg(1, "rst_ff2")
        self.rst_sync = Wire(1, "rst_sync")
        self.data_q = Reg(1, "data_q")
        self.data_out = Output(1, "data_out")

        @self.comb
        def _comb():
            self.rst_sync <<= ~self.rst_ff2
            self.data_out <<= self.data_q

        @self.seq(self.core_clk, self.rst_async, reset_async=True)
        def _reset_release_seq():
            with If(self.rst_async == 1):
                self.rst_ff1 <<= 1
                self.rst_ff2 <<= 1
            with Else():
                self.rst_ff1 <<= 0
                self.rst_ff2 <<= self.rst_ff1

        @self.seq(self.core_clk, self.rst_sync, reset_async=True)
        def _core_seq():
            with If(self.rst_sync == 1):
                self.data_q <<= 0
            with Else():
                self.data_q <<= self.data_in


class SafeHandwrittenAsyncResetReleaseWithAlias(Module):
    def __init__(self):
        super().__init__("safe_handwritten_async_reset_release_with_alias")
        self.core_clk = Input(1, "core_clk")
        self.rst_async = Input(1, "rst_async")
        self.data_in = Input(1, "data_in")
        self.rst_ff1 = Reg(1, "rst_ff1")
        self.rst_ff2 = Reg(1, "rst_ff2")
        self.rst_sync_int = Wire(1, "rst_sync_int")
        self.rst_sync = Wire(1, "rst_sync")
        self.data_q = Reg(1, "data_q")
        self.data_out = Output(1, "data_out")
        self.reset_dbg = Output(1, "reset_dbg")

        @self.comb
        def _comb():
            self.rst_sync_int <<= ~self.rst_ff2
            self.rst_sync <<= self.rst_sync_int
            self.reset_dbg <<= self.rst_sync_int
            self.data_out <<= self.data_q

        @self.seq(self.core_clk, self.rst_async, reset_async=True)
        def _reset_release_seq():
            with If(self.rst_async == 1):
                self.rst_ff1 <<= 1
                self.rst_ff2 <<= 1
            with Else():
                self.rst_ff1 <<= 0
                self.rst_ff2 <<= self.rst_ff1

        @self.seq(self.core_clk, self.rst_sync, reset_async=True)
        def _core_seq():
            with If(self.rst_sync == 1):
                self.data_q <<= 0
            with Else():
                self.data_q <<= self.data_in


class SafeThreeStageAsyncResetRelease(Module):
    def __init__(self):
        super().__init__("safe_three_stage_async_reset_release")
        self.core_clk = Input(1, "core_clk")
        self.rst_async = Input(1, "rst_async")
        self.data_in = Input(1, "data_in")
        self.rst_ff1 = Reg(1, "rst_ff1")
        self.rst_ff2 = Reg(1, "rst_ff2")
        self.rst_ff3 = Reg(1, "rst_ff3")
        self.rst_sync = Wire(1, "rst_sync")
        self.data_q = Reg(1, "data_q")
        self.data_out = Output(1, "data_out")

        @self.comb
        def _comb():
            self.rst_sync <<= ~self.rst_ff3
            self.data_out <<= self.data_q

        @self.seq(self.core_clk, self.rst_async, reset_async=True)
        def _reset_release_seq():
            with If(self.rst_async == 1):
                self.rst_ff1 <<= 1
                self.rst_ff2 <<= 1
                self.rst_ff3 <<= 1
            with Else():
                self.rst_ff1 <<= 0
                self.rst_ff2 <<= self.rst_ff1
                self.rst_ff3 <<= self.rst_ff2

        @self.seq(self.core_clk, self.rst_sync, reset_async=True)
        def _core_seq():
            with If(self.rst_sync == 1):
                self.data_q <<= 0
            with Else():
                self.data_q <<= self.data_in


class SafeHandwrittenAsyncResetReleaseActiveLow(Module):
    def __init__(self):
        super().__init__("safe_handwritten_async_reset_release_active_low")
        self.core_clk = Input(1, "core_clk")
        self.rst_async_n = Input(1, "rst_async_n")
        self.data_in = Input(1, "data_in")
        self.rst_ff1 = Reg(1, "rst_ff1")
        self.rst_ff2 = Reg(1, "rst_ff2")
        self.rst_sync_n = Wire(1, "rst_sync_n")
        self.rst_sync_alias = Wire(1, "rst_sync_alias")
        self.data_q = Reg(1, "data_q")
        self.data_out = Output(1, "data_out")
        self.reset_dbg = Output(1, "reset_dbg")

        @self.comb
        def _comb():
            self.rst_sync_n <<= self.rst_ff2
            self.rst_sync_alias <<= self.rst_sync_n
            self.reset_dbg <<= self.rst_sync_alias
            self.data_out <<= self.data_q

        @self.seq(
            self.core_clk,
            self.rst_async_n,
            reset_async=True,
            reset_active_low=True,
        )
        def _reset_release_seq():
            with If(self.rst_async_n == 0):
                self.rst_ff1 <<= 0
                self.rst_ff2 <<= 0
            with Else():
                self.rst_ff1 <<= 1
                self.rst_ff2 <<= self.rst_ff1

        @self.seq(
            self.core_clk,
            self.rst_sync_alias,
            reset_async=True,
            reset_active_low=True,
        )
        def _core_seq():
            with If(self.rst_sync_alias == 0):
                self.data_q <<= 0
            with Else():
                self.data_q <<= self.data_in


class UnsafeCrossDomainReuseOfSynchronizedReset(Module):
    def __init__(self):
        super().__init__("unsafe_cross_domain_reuse_of_synchronized_reset")
        self.core_clk = Input(1, "core_clk")
        self.aux_clk = Input(1, "aux_clk")
        self.rst_async = Input(1, "rst_async")
        self.data_in = Input(1, "data_in")
        self.rst_ff1 = Reg(1, "rst_ff1")
        self.rst_ff2 = Reg(1, "rst_ff2")
        self.rst_sync = Wire(1, "rst_sync")
        self.core_q = Reg(1, "core_q")
        self.aux_q = Reg(1, "aux_q")
        self.core_out = Output(1, "core_out")
        self.aux_out = Output(1, "aux_out")

        @self.comb
        def _comb():
            self.rst_sync <<= ~self.rst_ff2
            self.core_out <<= self.core_q
            self.aux_out <<= self.aux_q

        @self.seq(self.core_clk, self.rst_async, reset_async=True)
        def _reset_release_seq():
            with If(self.rst_async == 1):
                self.rst_ff1 <<= 1
                self.rst_ff2 <<= 1
            with Else():
                self.rst_ff1 <<= 0
                self.rst_ff2 <<= self.rst_ff1

        @self.seq(self.core_clk, self.rst_sync, reset_async=True)
        def _core_seq():
            with If(self.rst_sync == 1):
                self.core_q <<= 0
            with Else():
                self.core_q <<= self.data_in

        @self.seq(self.aux_clk, self.rst_sync, reset_async=True)
        def _aux_seq():
            with If(self.rst_sync == 1):
                self.aux_q <<= 0
            with Else():
                self.aux_q <<= self.data_in


def test_analyze_cdc_reports_single_bit_crossing():
    report = analyze_cdc(UnsafeSingleBitCrossing())

    assert report.has_issues is True
    assert any(f.category == "single_bit_crossing" for f in report.findings)
    finding = next(f for f in report.findings if f.category == "single_bit_crossing")
    assert finding.src is not None
    assert finding.src.signal_name == "flag_q"
    assert "SyncCell" in " ".join(finding.suggestions)


def test_analyze_cdc_reports_toggle_crossing_as_pulse_crossing():
    report = analyze_cdc(UnsafeToggleCrossing())

    assert any(f.category == "pulse_crossing" for f in report.findings)
    finding = next(f for f in report.findings if f.category == "pulse_crossing")
    assert finding.src is not None
    assert finding.src.signal_name == "toggle_src"
    assert "PulseSynchronizer" in " ".join(finding.suggestions)


def test_analyze_cdc_reports_multi_bit_crossing():
    report = analyze_cdc(UnsafeBusCrossing())

    assert any(f.category == "multi_bit_crossing" for f in report.findings)
    finding = next(f for f in report.findings if f.category == "multi_bit_crossing")
    assert finding.severity == "error"
    assert "AsyncFIFO" in " ".join(finding.suggestions)


def test_analyze_cdc_reports_memory_crossing():
    report = analyze_cdc(UnsafeArrayMailbox())

    assert any(f.category == "memory_crossing" for f in report.findings)
    finding = next(f for f in report.findings if f.category == "memory_crossing")
    assert finding.src is not None
    assert finding.src.signal_name == "rf"


def test_analyze_cdc_ignores_safe_sync_cell_crossing():
    report = analyze_cdc(SafeSyncCellCrossing())

    assert report.findings == ()


def test_analyze_cdc_ignores_safe_handwritten_sync_crossing():
    report = analyze_cdc(SafeHandwrittenSyncCrossing())

    assert not any(f.category == "single_bit_crossing" for f in report.findings)


def test_analyze_cdc_ignores_safe_handwritten_sync_crossing_with_comb_alias():
    report = analyze_cdc(SafeHandwrittenSyncCrossingWithAlias())

    assert not any(f.category == "single_bit_crossing" for f in report.findings)


def test_analyze_cdc_ignores_safe_handwritten_sync_crossing_with_tap():
    report = analyze_cdc(SafeHandwrittenSyncCrossingWithTap())

    assert not any(f.category == "single_bit_crossing" for f in report.findings)


def test_analyze_cdc_ignores_safe_handwritten_pulse_synchronizer():
    report = analyze_cdc(SafeHandwrittenPulseSynchronizer())

    assert not any(f.category == "pulse_crossing" for f in report.findings)
    assert report.findings == ()


def test_analyze_cdc_ignores_safe_handwritten_pulse_synchronizer_with_alias():
    report = analyze_cdc(SafeHandwrittenPulseSynchronizerWithAlias())

    assert not any(f.category == "pulse_crossing" for f in report.findings)


def test_analyze_cdc_ignores_safe_async_fifo_crossing():
    report = analyze_cdc(SafeAsyncFifoCrossing())

    assert report.findings == ()


def test_analyze_cdc_ignores_safe_ready_valid_async_bridge_crossing():
    report = analyze_cdc(SafeReadyValidAsyncBridgeCrossing())

    assert report.findings == ()


def test_analyze_cdc_reports_reset_release_crossing_for_raw_async_reset():
    report = analyze_cdc(UnsafeAsyncResetRelease())

    assert any(f.category == "reset_release_crossing" for f in report.findings)
    finding = next(f for f in report.findings if f.category == "reset_release_crossing")
    assert finding.severity == "warning"
    assert finding.src is not None
    assert finding.src.signal_name == "rst_async"
    assert finding.evidence["destination_domain"] == "core_clk"
    assert "data_q" in finding.evidence["affected_targets"]
    assert any(site[0] == "data_q" for site in finding.evidence["affected_target_sites"])
    assert "Affected sequential targets: data_q." in finding.message
    assert finding.evidence["recommended_sync_primitive"] == "AsyncResetRel"
    assert finding.evidence["recommended_sync_instance"] == "u_core_clk_reset_rel"
    assert finding.evidence["recommended_synchronized_reset"] == "core_clk_rst_sync"
    assert any("u_core_clk_reset_rel" in step for step in finding.evidence["remediation_steps"])
    assert any("core_clk_rst_sync" in suggestion for suggestion in finding.suggestions)


def test_analyze_cdc_ignores_safe_primitive_async_reset_release():
    report = analyze_cdc(SafePrimitiveAsyncResetRelease())

    assert not any(f.category == "reset_release_crossing" for f in report.findings)


def test_analyze_cdc_reports_apb_register_bank_raw_async_reset_release():
    from rtlgen_x.dsl import APBRegisterBank

    report = analyze_cdc(APBRegisterBank(depth=8))
    reset_findings = [f for f in report.findings if f.category == "reset_release_crossing"]
    assert len(reset_findings) == 1
    assert reset_findings[0].src is not None
    assert reset_findings[0].src.signal_name == "presetn"
    assert reset_findings[0].dst is not None
    assert reset_findings[0].dst.clock_domain == "pclk"


def test_analyze_cdc_ignores_axilite_register_bank_reset_release():
    from rtlgen_x.dsl import AXI4LiteRegisterBank

    report = analyze_cdc(AXI4LiteRegisterBank(depth=8))

    assert not any(f.category == "reset_release_crossing" for f in report.findings)
    assert report.findings == ()


def test_analyze_cdc_ignores_wishbone_register_bank_reset_release():
    from rtlgen_x.dsl import WishboneRegisterBank

    report = analyze_cdc(WishboneRegisterBank(depth=8))

    assert not any(f.category == "reset_release_crossing" for f in report.findings)
    assert report.findings == ()


def test_analyze_cdc_ignores_safe_handwritten_async_reset_release():
    report = analyze_cdc(SafeHandwrittenAsyncResetRelease())

    assert not any(f.category == "reset_release_crossing" for f in report.findings)


def test_analyze_cdc_ignores_safe_handwritten_async_reset_release_with_alias():
    report = analyze_cdc(SafeHandwrittenAsyncResetReleaseWithAlias())

    assert not any(f.category == "reset_release_crossing" for f in report.findings)


def test_analyze_cdc_ignores_safe_three_stage_handwritten_async_reset_release():
    report = analyze_cdc(SafeThreeStageAsyncResetRelease())

    assert not any(f.category == "reset_release_crossing" for f in report.findings)


def test_analyze_cdc_ignores_safe_handwritten_active_low_async_reset_release():
    report = analyze_cdc(SafeHandwrittenAsyncResetReleaseActiveLow())

    assert not any(f.category == "reset_release_crossing" for f in report.findings)


def test_analyze_cdc_reports_cross_domain_reuse_of_domain_local_reset_release():
    report = analyze_cdc(UnsafeCrossDomainReuseOfSynchronizedReset())

    reset_findings = [f for f in report.findings if f.category == "reset_release_crossing"]
    assert reset_findings
    assert any(f.dst is not None and f.dst.clock_domain == "aux_clk" for f in reset_findings)


def test_analyze_cdc_reports_multi_writer_state_hazard():
    report = analyze_cdc(MultiWriterStateHazard())

    assert any(f.category == "multi_writer_state" for f in report.findings)
    finding = next(f for f in report.findings if f.category == "multi_writer_state")
    assert finding.severity == "error"
    assert "multiple clock domains" in finding.message


def test_emit_cdc_report_markdown_includes_findings():
    report = analyze_cdc(UnsafeSingleBitCrossing())
    text = emit_cdc_report_markdown(report, title="CDC Smoke")

    assert "# CDC Smoke" in text
    assert "single_bit_crossing" in text
    assert "flag_q" in text
    assert "kind=state" in text
    assert "errors" in text
    assert "warnings" in text


def test_emit_cdc_report_markdown_expands_reset_release_remediation_steps():
    report = analyze_cdc(UnsafeAsyncResetRelease())
    text = emit_cdc_report_markdown(report, title="Reset CDC")

    assert "# Reset CDC" in text
    assert "recommended_sync_primitive:" in text
    assert "recommended_sync_instance:" in text
    assert "u_core_clk_reset_rel" in text
    assert "core_clk_rst_sync" in text
    assert "remediation_steps:" in text


def test_emit_cdc_report_markdown_includes_source_site_details():
    report = analyze_cdc(_lowered(SimModule(
        name="simmodule_single_bit_crossing",
        signals=(
            Signal("wr_clk", width=1, kind="input"),
            Signal("rd_clk", width=1, kind="input"),
            Signal("wr_rst", width=1, kind="input"),
            Signal("rd_rst", width=1, kind="input"),
            Signal("flag_in", width=1, kind="input"),
            Signal("flag_q", width=1, kind="state"),
            Signal("flag_seen_q", width=1, kind="state"),
            Signal("flag_seen", width=1, kind="output"),
        ),
        assignments=(
            Assignment(
                "flag_seen",
                SignalRef("flag_seen_q"),
                phase="comb",
                source_file="unsafe_sim.py",
                source_line=30,
            ),
            Assignment(
                "flag_q",
                SignalRef("flag_in"),
                phase="seq",
                clock_domain="wr_clk",
                source_file="unsafe_sim.py",
                source_line=11,
            ),
            Assignment(
                "flag_seen_q",
                SignalRef("flag_q"),
                phase="seq",
                clock_domain="rd_clk",
                source_file="unsafe_sim.py",
                source_line=21,
            ),
        ),
        outputs=("flag_seen",),
        clock_domains=(
            ClockDomain("wr_clk", reset_signal="wr_rst"),
            ClockDomain("rd_clk", reset_signal="rd_rst"),
        ),
    )))
    text = emit_cdc_report_markdown(report)

    assert "source sites:" in text
    assert "source `flag_q` -> unsafe_sim.py:11" in text
    assert "destination `flag_seen_q` -> unsafe_sim.py:21" in text


def test_analyze_cdc_reports_simmodule_single_bit_crossing_with_locations():
    module = SimModule(
        name="simmodule_single_bit_crossing",
        signals=(
            Signal("wr_clk", width=1, kind="input"),
            Signal("rd_clk", width=1, kind="input"),
            Signal("wr_rst", width=1, kind="input"),
            Signal("rd_rst", width=1, kind="input"),
            Signal("flag_in", width=1, kind="input"),
            Signal("flag_q", width=1, kind="state"),
            Signal("flag_seen_q", width=1, kind="state"),
            Signal("flag_seen", width=1, kind="output"),
        ),
        assignments=(
            Assignment(
                "flag_seen",
                SignalRef("flag_seen_q"),
                phase="comb",
                source_file="unsafe_sim.py",
                source_line=30,
            ),
            Assignment(
                "flag_q",
                SignalRef("flag_in"),
                phase="seq",
                clock_domain="wr_clk",
                source_file="unsafe_sim.py",
                source_line=11,
            ),
            Assignment(
                "flag_seen_q",
                SignalRef("flag_q"),
                phase="seq",
                clock_domain="rd_clk",
                source_file="unsafe_sim.py",
                source_line=21,
            ),
        ),
        outputs=("flag_seen",),
        clock_domains=(
            ClockDomain("wr_clk", reset_signal="wr_rst"),
            ClockDomain("rd_clk", reset_signal="rd_rst"),
        ),
    )

    report = analyze_cdc(_lowered(module))

    assert any(f.category == "single_bit_crossing" for f in report.findings)
    finding = next(f for f in report.findings if f.category == "single_bit_crossing")
    assert finding.src is not None
    assert finding.dst is not None
    assert finding.src.signal_name == "flag_q"
    assert finding.src.source_file == "unsafe_sim.py"
    assert finding.src.source_line == 11
    assert finding.dst.signal_name == "flag_seen_q"
    assert finding.dst.source_file == "unsafe_sim.py"
    assert finding.dst.source_line == 21


def test_analyze_cdc_reports_simmodule_memory_crossing():
    module = SimModule(
        name="simmodule_memory_crossing",
        signals=(
            Signal("wr_clk", width=1, kind="input"),
            Signal("rd_clk", width=1, kind="input"),
            Signal("wr_rst", width=1, kind="input"),
            Signal("rd_rst", width=1, kind="input"),
            Signal("wr_en", width=1, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("rd_ptr", width=2, kind="state"),
            Signal("rd_data", width=8, kind="state"),
            Signal("dout", width=8, kind="output"),
        ),
        assignments=(
            Assignment(
                "dout",
                SignalRef("rd_data"),
                phase="comb",
                source_file="unsafe_mem.py",
                source_line=33,
            ),
            Assignment(
                "rd_data",
                MemoryReadExpr("rf", SignalRef("rd_ptr")),
                phase="seq",
                clock_domain="rd_clk",
                source_file="unsafe_mem.py",
                source_line=22,
            ),
        ),
        outputs=("dout",),
        memories=(
            Memory("rf", width=8, depth=4),
        ),
        memory_writes=(
            MemoryWrite(
                "rf",
                ConstExpr(0, 2),
                SignalRef("din"),
                enable=SignalRef("wr_en"),
                clock_domain="wr_clk",
                source_file="unsafe_mem.py",
                source_line=18,
            ),
        ),
        clock_domains=(
            ClockDomain("wr_clk", reset_signal="wr_rst"),
            ClockDomain("rd_clk", reset_signal="rd_rst"),
        ),
    )

    report = analyze_cdc(_lowered(module))

    assert any(f.category == "memory_crossing" for f in report.findings)
    finding = next(f for f in report.findings if f.category == "memory_crossing")
    assert finding.src is not None
    assert finding.dst is not None
    assert finding.src.signal_name == "rf"
    assert finding.src.source_file == "unsafe_mem.py"
    assert finding.src.source_line == 18
    assert finding.dst.signal_name == "rd_data"


def test_analyze_cdc_reports_simmodule_reset_release_crossing():
    module = SimModule(
        name="simmodule_unsafe_reset_release",
        signals=(
            Signal("core_clk", width=1, kind="input"),
            Signal("rst_async", width=1, kind="input"),
            Signal("data_in", width=1, kind="input"),
            Signal("data_q", width=1, kind="state"),
            Signal("data_out", width=1, kind="output"),
        ),
        assignments=(
            Assignment(
                "data_q",
                MuxExpr(SignalRef("rst_async"), ConstExpr(0, 1), SignalRef("data_in")),
                phase="seq",
                clock_domain="core_clk",
                source_file="unsafe_reset_sim.py",
                source_line=12,
            ),
            Assignment(
                "data_out",
                SignalRef("data_q"),
                phase="comb",
                source_file="unsafe_reset_sim.py",
                source_line=20,
            ),
        ),
        outputs=("data_out",),
        clock_domains=(
            ClockDomain("core_clk", reset_signal="rst_async", reset_async=True),
        ),
    )

    report = analyze_cdc(_lowered(module))

    assert any(f.category == "reset_release_crossing" for f in report.findings)
    finding = next(f for f in report.findings if f.category == "reset_release_crossing")
    assert finding.evidence["destination_domain"] == "core_clk"
    assert "data_q" in finding.evidence["affected_targets"]
    assert any(site[0] == "data_q" for site in finding.evidence["affected_target_sites"])


def test_analyze_cdc_ignores_simmodule_safe_handwritten_async_reset_release():
    module = SimModule(
        name="simmodule_safe_reset_release",
        signals=(
            Signal("core_clk", width=1, kind="input"),
            Signal("rst_async", width=1, kind="input"),
            Signal("data_in", width=1, kind="input"),
            Signal("rst_ff1", width=1, kind="state"),
            Signal("rst_ff2", width=1, kind="state"),
            Signal("rst_sync", width=1, kind="wire"),
            Signal("data_q", width=1, kind="state"),
            Signal("data_out", width=1, kind="output"),
        ),
        assignments=(
            Assignment(
                "rst_sync",
                UnaryExpr("~", SignalRef("rst_ff2")),
                phase="comb",
                source_file="safe_reset_sim.py",
                source_line=8,
            ),
            Assignment(
                "rst_ff1",
                MuxExpr(SignalRef("rst_async"), ConstExpr(1, 1), ConstExpr(0, 1)),
                phase="seq",
                clock_domain="core_clk",
                source_file="safe_reset_sim.py",
                source_line=12,
            ),
            Assignment(
                "rst_ff2",
                MuxExpr(SignalRef("rst_async"), ConstExpr(1, 1), SignalRef("rst_ff1")),
                phase="seq",
                clock_domain="core_clk",
                source_file="safe_reset_sim.py",
                source_line=13,
            ),
            Assignment(
                "data_q",
                MuxExpr(SignalRef("rst_sync"), ConstExpr(0, 1), SignalRef("data_in")),
                phase="seq",
                clock_domain="core_clk",
                source_file="safe_reset_sim.py",
                source_line=20,
            ),
            Assignment(
                "data_out",
                SignalRef("data_q"),
                phase="comb",
                source_file="safe_reset_sim.py",
                source_line=24,
            ),
        ),
        outputs=("data_out",),
        clock_domains=(
            ClockDomain("core_clk", reset_signal="rst_sync", reset_async=True),
        ),
    )

    report = analyze_cdc(_lowered(module))

    assert not any(f.category == "reset_release_crossing" for f in report.findings)


def test_analyze_cdc_ignores_simmodule_safe_three_stage_async_reset_release():
    module = SimModule(
        name="simmodule_safe_three_stage_reset_release",
        signals=(
            Signal("core_clk", width=1, kind="input"),
            Signal("rst_async", width=1, kind="input"),
            Signal("data_in", width=1, kind="input"),
            Signal("rst_ff1", width=1, kind="state"),
            Signal("rst_ff2", width=1, kind="state"),
            Signal("rst_ff3", width=1, kind="state"),
            Signal("rst_sync", width=1, kind="wire"),
            Signal("data_q", width=1, kind="state"),
            Signal("data_out", width=1, kind="output"),
        ),
        assignments=(
            Assignment(
                "rst_sync",
                UnaryExpr("~", SignalRef("rst_ff3")),
                phase="comb",
                source_file="safe_reset3_sim.py",
                source_line=8,
            ),
            Assignment(
                "rst_ff1",
                MuxExpr(SignalRef("rst_async"), ConstExpr(1, 1), ConstExpr(0, 1)),
                phase="seq",
                clock_domain="core_clk",
                source_file="safe_reset3_sim.py",
                source_line=12,
            ),
            Assignment(
                "rst_ff2",
                MuxExpr(SignalRef("rst_async"), ConstExpr(1, 1), SignalRef("rst_ff1")),
                phase="seq",
                clock_domain="core_clk",
                source_file="safe_reset3_sim.py",
                source_line=13,
            ),
            Assignment(
                "rst_ff3",
                MuxExpr(SignalRef("rst_async"), ConstExpr(1, 1), SignalRef("rst_ff2")),
                phase="seq",
                clock_domain="core_clk",
                source_file="safe_reset3_sim.py",
                source_line=14,
            ),
            Assignment(
                "data_q",
                MuxExpr(SignalRef("rst_sync"), ConstExpr(0, 1), SignalRef("data_in")),
                phase="seq",
                clock_domain="core_clk",
                source_file="safe_reset3_sim.py",
                source_line=20,
            ),
            Assignment(
                "data_out",
                SignalRef("data_q"),
                phase="comb",
                source_file="safe_reset3_sim.py",
                source_line=24,
            ),
        ),
        outputs=("data_out",),
        clock_domains=(
            ClockDomain("core_clk", reset_signal="rst_sync", reset_async=True),
        ),
    )

    report = analyze_cdc(_lowered(module))

    assert not any(f.category == "reset_release_crossing" for f in report.findings)


def test_analyze_cdc_reports_simmodule_cross_domain_reuse_of_domain_local_reset_release():
    module = SimModule(
        name="simmodule_cross_domain_reset_reuse",
        signals=(
            Signal("core_clk", width=1, kind="input"),
            Signal("aux_clk", width=1, kind="input"),
            Signal("rst_async", width=1, kind="input"),
            Signal("data_in", width=1, kind="input"),
            Signal("rst_ff1", width=1, kind="state"),
            Signal("rst_ff2", width=1, kind="state"),
            Signal("rst_sync", width=1, kind="wire"),
            Signal("core_q", width=1, kind="state"),
            Signal("aux_q", width=1, kind="state"),
            Signal("core_out", width=1, kind="output"),
            Signal("aux_out", width=1, kind="output"),
        ),
        assignments=(
            Assignment(
                "rst_sync",
                UnaryExpr("~", SignalRef("rst_ff2")),
                phase="comb",
                source_file="cross_domain_reset_reuse.py",
                source_line=8,
            ),
            Assignment(
                "rst_ff1",
                MuxExpr(SignalRef("rst_async"), ConstExpr(1, 1), ConstExpr(0, 1)),
                phase="seq",
                clock_domain="core_clk",
                source_file="cross_domain_reset_reuse.py",
                source_line=12,
            ),
            Assignment(
                "rst_ff2",
                MuxExpr(SignalRef("rst_async"), ConstExpr(1, 1), SignalRef("rst_ff1")),
                phase="seq",
                clock_domain="core_clk",
                source_file="cross_domain_reset_reuse.py",
                source_line=13,
            ),
            Assignment(
                "core_q",
                MuxExpr(SignalRef("rst_sync"), ConstExpr(0, 1), SignalRef("data_in")),
                phase="seq",
                clock_domain="core_clk",
                source_file="cross_domain_reset_reuse.py",
                source_line=20,
            ),
            Assignment(
                "aux_q",
                MuxExpr(SignalRef("rst_sync"), ConstExpr(0, 1), SignalRef("data_in")),
                phase="seq",
                clock_domain="aux_clk",
                source_file="cross_domain_reset_reuse.py",
                source_line=24,
            ),
            Assignment(
                "core_out",
                SignalRef("core_q"),
                phase="comb",
                source_file="cross_domain_reset_reuse.py",
                source_line=28,
            ),
            Assignment(
                "aux_out",
                SignalRef("aux_q"),
                phase="comb",
                source_file="cross_domain_reset_reuse.py",
                source_line=29,
            ),
        ),
        outputs=("core_out", "aux_out"),
        clock_domains=(
            ClockDomain("core_clk", reset_signal="rst_sync", reset_async=True),
            ClockDomain("aux_clk", reset_signal="rst_sync", reset_async=True),
        ),
    )

    report = analyze_cdc(_lowered(module))

    reset_findings = [f for f in report.findings if f.category == "reset_release_crossing"]
    assert reset_findings
    assert any(f.dst is not None and f.dst.clock_domain == "aux_clk" for f in reset_findings)


def test_analyze_cdc_rejects_raw_simmodule():
    module = SimModule(
        name="raw_cdc_probe",
        signals=(Signal("a", width=1, kind="input"), Signal("b", width=1, kind="output")),
        assignments=(Assignment("b", SignalRef("a"), phase="comb"),),
        outputs=("b",),
    )

    with pytest.raises(TypeError, match="does not accept raw SimModule"):
        analyze_cdc(module)
