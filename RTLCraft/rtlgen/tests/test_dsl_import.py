import copy
import importlib.util
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

from rtlgen.dsl import (
    AHBLite,
    APB,
    APBRegisterBank,
    Array,
    AsyncFIFO,
    AXI4Stream,
    AXI4Lite,
    AXI4LiteRegisterBank,
    BlackBoxModule,
    ClockDomainSpec,
    collect_external_verilog_artifacts,
    ConnectivitySite,
    Const,
    Else,
    EmitProfile,
    If,
    Input,
    DslLoweringError,
    MemoryAccess,
    Memory,
    build_compiled_simulator_from_dsl,
    lower_dsl_module_to_sim,
    Module,
    ModuleConnectivityReport,
    ModuleInstancePath,
    Mux,
    Output,
    PackedStructType,
    PadLeft,
    Parameter,
    PortConnection,
    ReadyValid,
    ReadyValidAsyncBridge,
    ReadyValidFIFO,
    ReadyValidRegister,
    ReqRsp,
    ReqRspQueue,
    Reg,
    ResetDomainSpec,
    RoundShiftRight,
    RoundRobinArbiter,
    SRA,
    SkidBuffer,
    SignalDriver,
    Switch,
    SyncFIFO,
    StateWriter,
    Divider,
    Decoder,
    EnumType,
    PriorityEncoder,
    BarrelShifter,
    FSM,
    LFSR,
    MarkerSequenceReport,
    ReadabilityContractError,
    analyze_marker_sequence,
    analyze_emitted_readability,
    analyze_verilog_readability,
    assert_emitted_rtl_contract,
    assert_marker_sequence,
    assert_readable_verilog,
    emit_marker_sequence_report_markdown,
    emit_readability_report_markdown,
    VerilogEmitter,
    VerilogLinter,
    validate_authoring_intent,
    Wishbone,
    WishboneRegisterBank,
    Wire,
)
from rtlgen.dsl.lib import AsyncResetRel, Counter, GrayCounter, MultiCycleFSM, PipelineShift, PulseSynchronizer, SyncCell, EdgeDetector, PipelineInterlock, BypassNetwork, MultiCyclePath, MAC, SignedMultiplier, RegisterFile, DualPortRAM, LUT
from rtlgen.dsl.pipeline import ShiftReg, ValidPipe
from rtlgen.sim.python_runtime import PythonSimulator
from rtlgen.dsl.unsupported import DslSimulationRemovedError


class Accum(Module):
    def __init__(self):
        super().__init__("Accum")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.inp = Input(8, "inp")
        self.out = Output(8, "out")
        self.acc = Reg(8, "acc")

        @self.comb
        def _comb():
            self.out <<= self.acc

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.acc <<= 0
            with Else():
                self.acc <<= self.acc + self.inp


class BitUpdate(Module):
    def __init__(self):
        super().__init__("BitUpdate")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.flag = Input(1, "flag")
        self.out = Output(8, "out")
        self.state = Reg(8, "state")

        @self.comb
        def _comb():
            self.out <<= self.state

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.state <<= 0xA0
            with Else():
                self.state[2] <<= self.flag


class ExternalParameterizedLeaf(BlackBoxModule):
    def __init__(self):
        super().__init__(
            name="ExternalParameterizedLeaf",
            verilog_module_name="ext_param_leaf",
            inputs=[("din", 8)],
            outputs=[("dout", 8)],
            parameters=[("WIDTH", 8), ("LATENCY", 1)],
            external_verilog=True,
            verilog_sources=["rtl/ext_param_leaf.sv"],
            include_dirs=["rtl/include"],
            defines={"EXT_PARAM_LEAF": "1"},
        )


class UsesExternalParameterizedLeaf(Module):
    def __init__(self):
        super().__init__("UsesExternalParameterizedLeaf")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.leaf = ExternalParameterizedLeaf()
        self.leaf._param_bindings["WIDTH"] = 16
        self.leaf._param_bindings["LATENCY"] = 2

        @self.comb
        def _comb():
            self.leaf.din <<= self.din
            self.dout <<= self.leaf.dout


class MixedExternalRomLeaf(Module):
    def __init__(self, init_file: str = "roms/mixed_rom.hex"):
        super().__init__("MixedExternalRomLeaf")
        self.addr = Input(2, "addr")
        self.dout = Output(8, "dout")
        self.mem = self.add_memory(Memory(8, 4, "mem", init_file=init_file))

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.addr]


class MixedExternalRomTop(Module):
    def __init__(self):
        super().__init__("MixedExternalRomTop")
        self.addr = Input(2, "addr")
        self.din = Input(8, "din")
        self.out = Output(8, "out")
        self.ext = ExternalParameterizedLeaf()
        self.rom = MixedExternalRomLeaf()
        self.mid = Wire(8, "mid")

        @self.comb
        def _comb():
            self.ext.din <<= self.din
            self.rom.addr <<= self.addr
            self.mid <<= self.ext.dout
            self.out <<= self.mid + self.rom.dout


class NamedByString(Module):
    def __init__(self):
        super().__init__("named_by_string")
        self.inp = Input(8, "inp")
        self.out = Output(8, "out")

        @self.comb
        def _comb():
            self.out <<= self.inp


class ConcatWidened(Module):
    def __init__(self):
        super().__init__("concat_widened")
        self.inp = Input(128, "inp")
        self.out = Output(260, "out")

        @self.comb
        def _comb():
            self.out <<= PadLeft(self.inp, 260)


class NestedSliceBinOp(Module):
    def __init__(self):
        super().__init__("nested_slice_binop")
        self.inp = Input(128, "inp")
        self.out = Output(17, "out")

        @self.comb
        def _comb():
            midsum = PadLeft(self.inp[127:64], 65) + PadLeft(self.inp[63:0], 65)
            self.out <<= midsum[64:32][16:0]


class ReadableCombSeq(Module):
    def __init__(self):
        super().__init__("readable_comb_seq")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.sel = Input(1, "sel")
        self.a = Input(8, "a")
        self.b = Input(8, "b")
        self.out = Output(8, "out")
        self.state = Reg(8, "state")

        @self.comb
        def _comb():
            with If(self.sel == 1):
                self.out <<= self.a
            with Else():
                self.out <<= self.b

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.state <<= 0
            with Else():
                self.state <<= self.out


class ReadableRepeatedExpr(Module):
    def __init__(self):
        super().__init__("readable_repeated_expr")
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.out = Output(17, "out")

        @self.comb
        def _comb():
            pair = self.a + self.b
            expr = pair ^ pair
            for _ in range(9):
                expr = expr ^ pair
            self.out <<= expr


class SliceUpdate(Module):
    def __init__(self):
        super().__init__("SliceUpdate")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.nibble = Input(4, "nibble")
        self.out = Output(8, "out")
        self.state = Reg(8, "state")

        @self.comb
        def _comb():
            self.out <<= self.state

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.state <<= 0xA0
            with Else():
                self.state[3:0] <<= self.nibble


def _jpeg_reference_idct2(coeffs):
    from jpeg_decoder.dsl_modules import IDCT_FRAC, IDCT_TABLE

    transform = np.array(IDCT_TABLE, dtype=float).reshape(8, 8) / (1 << IDCT_FRAC)
    coeffs_fp = coeffs.astype(float)
    row_out = np.zeros((8, 8), dtype=float)
    for v in range(8):
        for col in range(8):
            row_sum = sum(coeffs_fp[v][u] * transform[u][col] for u in range(8))
            row_out[v][col] = np.floor(row_sum + 0.5)
    temp = np.zeros((8, 8), dtype=float)
    for row in range(8):
        for col in range(8):
            col_sum = sum(row_out[u][col] * transform[u][row] for u in range(8))
            temp[row][col] = np.floor(col_sum + 0.5)
    return np.clip(temp + 128, 0, 255).astype(np.uint8)


def _run_jpeg_idct_sim(sim, block, coeff_width):
    for value in block:
        sim.step({
            "clk": 0,
            "rst": 0,
            "in_data": value & ((1 << coeff_width) - 1),
            "in_valid": 1,
            "out_ready": 1,
        })

    outputs = []
    for _ in range(1200):
        observed = sim.step({
            "clk": 0,
            "rst": 0,
            "in_data": 0,
            "in_valid": 0,
            "out_ready": 1,
        })
        if observed.get("out_valid"):
            outputs.append(observed["out_data"])
        if len(outputs) >= 64:
            break
    return outputs


class DynamicPartSelectUpdate(Module):
    def __init__(self):
        super().__init__("DynamicPartSelectUpdate")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.we = Input(1, "we")
        self.lane = Input(2, "lane")
        self.nibble = Input(4, "nibble")
        self.out = Output(4, "out")
        self.state = Reg(16, "state")

        @self.comb
        def _comb():
            self.out <<= self.state[(self.lane + 1) * 4 - 1 : self.lane * 4]

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.state <<= 0
            with Else():
                with If(self.we == 1):
                    self.state[(self.lane + 1) * 4 - 1 : self.lane * 4] <<= self.nibble


class DynamicSliceUpdate(Module):
    def __init__(self):
        super().__init__("DynamicSliceUpdate")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.we = Input(1, "we")
        self.lo = Input(3, "lo")
        self.width_sel = Input(1, "width_sel")
        self.data = Input(4, "data")
        self.out = Output(8, "out")
        self.state = Reg(8, "state")

        @self.comb
        def _comb():
            self.out <<= self.state

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.state <<= 0
            with Else():
                with If(self.we == 1):
                    with If(self.width_sel == 0):
                        self.state[self.lo + 1 : self.lo] <<= self.data[1:0]
                    with Else():
                        self.state[self.lo + 3 : self.lo] <<= self.data


class PackedStructRoundTrip(Module):
    def __init__(self):
        super().__init__("PackedStructRoundTrip")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.load = Input(1, "load")
        self.opcode = Input(4, "opcode")
        self.tag = Input(4, "tag")
        self.out_opcode = Output(4, "out_opcode")
        self.out_tag = Output(4, "out_tag")
        self.out_raw = Output(8, "out_raw")

        self.packet_t = PackedStructType.define(
            "packet_t",
            (
                ("opcode", 4),
                ("tag", 4),
            ),
        )
        self.packet = Reg(name="packet", struct_type=self.packet_t)

        @self.comb
        def _comb():
            self.out_opcode <<= self.packet.opcode
            self.out_tag <<= self.packet.tag
            self.out_raw <<= self.packet

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.packet <<= self.packet_t.pack(opcode=0, tag=0)
            with Else():
                with If(self.load == 1):
                    self.packet.opcode <<= self.opcode
                    self.packet.tag <<= self.tag


class InitBlockState(Module):
    def __init__(self):
        super().__init__("InitBlockState")
        self.addr = Input(2, "addr")
        self.out = Output(8, "out")
        self.acc = Reg(8, "acc")
        self.rf = Array(8, 4, "rf")

        with self.init:
            self.acc <<= 0xA0
            self.acc[3:0] <<= 0x5
            self.rf[0] <<= 1
            self.rf[1] <<= 7
            self.rf[2] <<= 9

        @self.comb
        def _comb():
            self.out <<= self.acc + self.rf[self.addr]


class InitBlockDynamicSliceState(Module):
    def __init__(self):
        super().__init__("InitBlockDynamicSliceState")
        self.sel = Input(2, "sel")
        self.out = Output(4, "out")
        self.acc = Reg(8, "acc")
        self.idx = Reg(2, "idx")

        with self.init:
            self.acc <<= 0
            self.idx <<= 1
            self.acc[self.idx + 3 : self.idx] <<= 0xA

        @self.comb
        def _comb():
            self.out <<= self.acc[self.sel + 3 : self.sel]


class LatchPass(Module):
    def __init__(self):
        super().__init__("LatchPass")
        self.en = Input(1, "en")
        self.d = Input(8, "d")
        self.out = Output(8, "out")
        self.state = Reg(8, "state")

        with self.latch:
            with If(self.en == 1):
                self.state <<= self.d

        @self.comb
        def _comb():
            self.out <<= self.state


class TinyMem(Module):
    def __init__(self):
        super().__init__("TinyMem")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.we = Input(1, "we")
        self.addr = Input(2, "addr")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.mem = Memory(8, 4, "mem", init_zero=True)

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.addr]

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.we):
                self.mem[self.addr] <<= self.din


class InitDataMem(Module):
    def __init__(self):
        super().__init__("InitDataMem")
        self.addr = Input(2, "addr")
        self.dout = Output(8, "dout")
        self.mem = self.add_memory(Memory(8, 4, "mem", init_data=[-1, 3, 0x55, -128]))

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.addr]


class ReadFirstMem(Module):
    def __init__(self):
        super().__init__("ReadFirstMem")
        self.clk = Input(1, "clk")
        self.we = Input(1, "we")
        self.addr = Input(2, "addr")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.mem = self.add_memory(
            Memory(8, 4, "mem", init_data=[1, 2, 3, 4], read_during_write="read_first")
        )

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.addr]

        @self.seq(self.clk)
        def _seq():
            with If(self.we == 1):
                self.mem[self.addr] <<= self.din


class ByteEnableDeclaredMem(Module):
    def __init__(self):
        super().__init__("ByteEnableDeclaredMem")
        self.clk = Input(1, "clk")
        self.addr = Input(2, "addr")
        self.din = Input(32, "din")
        self.be = Input(4, "be")
        self.dout = Output(32, "dout")
        self.mem = self.add_memory(
            Memory(32, 4, "mem", byte_enable_granularity=8)
        )

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.addr]

        @self.seq(self.clk)
        def _seq():
            self.mem.write(self.addr, self.din, byte_enable=self.be)


class SyncReadDeclaredMem(Module):
    def __init__(self):
        super().__init__("SyncReadDeclaredMem")
        self.clk = Input(1, "clk")
        self.addr = Input(2, "addr")
        self.dout = Output(8, "dout")
        self.mem = self.add_memory(
            Memory(8, 4, "mem", init_data=[10, 20, 30, 40], read_style="sync", read_latency=1)
        )

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.addr]

        @self.seq(self.clk)
        def _seq():
            pass


class QueryLeaf(Module):
    def __init__(self):
        super().__init__("QueryLeaf")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.a = Input(8, "a")
        self.addr = Input(2, "addr")
        self.y = Output(8, "y")
        self.state = Reg(8, "state")
        self.mem = self.add_memory(Memory(8, 4, "mem", init_data=[1, 2, 3, 4]))

        @self.comb
        def _comb():
            self.y <<= self.state + self.mem[self.addr]

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.state <<= 0
            with Else():
                self.state <<= self.a
                self.mem[self.addr] <<= self.a


class QueryTop(Module):
    def __init__(self):
        super().__init__("QueryTop")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.a = Input(8, "a")
        self.addr = Input(2, "addr")
        self.y = Output(8, "y")
        self.mid = Wire(8, "mid")
        self.u_leaf = QueryLeaf()

        @self.comb
        def _comb():
            self.u_leaf.clk <<= self.clk
            self.u_leaf.rst <<= self.rst
            self.u_leaf.a <<= self.a
            self.u_leaf.addr <<= self.addr
            self.mid <<= self.u_leaf.y
            self.y <<= self.mid


class ExplicitLeaf(Module):
    def __init__(self):
        super().__init__("ExplicitLeaf")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")

        @self.comb
        def _comb():
            self.dout <<= self.din


class ExplicitTop(Module):
    def __init__(self):
        super().__init__("ExplicitTop")
        self.a = Input(8, "a")
        self.y = Output(8, "y")
        leaf = ExplicitLeaf()
        self.instantiate(leaf, "u_leaf", port_map={"din": self.a, "dout": self.y})


class PortExprLeaf(Module):
    def __init__(self):
        super().__init__("PortExprLeaf")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")

        @self.comb
        def _comb():
            self.dout <<= self.din


class PortExprTop(Module):
    def __init__(self):
        super().__init__("PortExprTop")
        self.a = Input(8, "a")
        self.b = Input(8, "b")
        self.y = Output(8, "y")
        leaf = PortExprLeaf()
        self.instantiate(
            leaf,
            "u_leaf",
            port_map={
                "din": (self.a + self.b)[7:0],
                "dout": self.y,
            },
        )


class InvalidPortLeaf(Module):
    def __init__(self):
        super().__init__("InvalidPortLeaf")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")

        @self.comb
        def _comb():
            self.dout <<= self.din


class InvalidPortTop(Module):
    def __init__(self):
        super().__init__("InvalidPortTop")
        self.a = Input(8, "a")
        self.y = Output(8, "y")
        leaf = InvalidPortLeaf()
        self.instantiate(
            leaf,
            "u_leaf",
            port_map={
                "din": self.a,
                "dout_typo": self.y,
            },
        )


class ReadyValidAsyncBridgeTop(Module):
    def __init__(self):
        super().__init__("ReadyValidAsyncBridgeTop")
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


class FlattenLeaf(Module):
    def __init__(self):
        super().__init__("FlattenLeaf")
        self.clk = Input(1, "clk")
        self.a = Input(8, "a")
        self.addr = Input(2, "addr")
        self.y = Output(8, "y")
        self.mem = self.add_memory(Memory(8, 4, "mem", init_data=[1, 2, 3, 4]))

        @self.comb
        def _comb():
            self.y <<= self.mem[self.addr]

        @self.seq(self.clk)
        def _seq():
            self.mem[self.addr] <<= self.a


class FlattenTop(Module):
    def __init__(self):
        super().__init__("FlattenTop")
        self.clk = Input(1, "clk")
        self.a = Input(8, "a")
        self.addr = Input(2, "addr")
        self.y = Output(8, "y")
        leaf = FlattenLeaf()
        self.instantiate(
            leaf,
            "u_leaf",
            port_map={"clk": self.clk, "a": self.a, "addr": self.addr, "y": self.y},
        )


class ImplicitArrayReadLeaf(Module):
    def __init__(self):
        super().__init__("ImplicitArrayReadLeaf")
        self.addr = Input(2, "addr")
        self.dout = Output(8, "dout")
        self.rf = Array(8, 4, "rf")

        @self.comb
        def _comb():
            self.dout <<= self.rf[self.addr]


class ImplicitArrayReadTop(Module):
    def __init__(self):
        super().__init__("ImplicitArrayReadTop")
        self.addr = Input(2, "addr")
        self.out = Output(8, "out")
        self.u = ImplicitArrayReadLeaf()

        @self.comb
        def _comb():
            self.u.addr <<= self.addr
            self.out <<= self.u.dout


class ImplicitMemoryReadLeaf(Module):
    def __init__(self):
        super().__init__("ImplicitMemoryReadLeaf")
        self.addr = Input(2, "addr")
        self.dout = Output(8, "dout")
        self.mem = self.add_memory(Memory(8, 4, "mem", init_data=[1, 2, 3, 4]))

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.addr]


class ImplicitMemoryReadTop(Module):
    def __init__(self):
        super().__init__("ImplicitMemoryReadTop")
        self.addr = Input(2, "addr")
        self.out = Output(8, "out")
        self.u = ImplicitMemoryReadLeaf()

        @self.comb
        def _comb():
            self.u.addr <<= self.addr
            self.out <<= self.u.dout


class SignedExprLeaf(Module):
    def __init__(self):
        super().__init__("SignedExprLeaf")
        self.a = Input(8, "a", signed=True)
        self.y = Output(8, "y", signed=True)

        @self.comb
        def _comb():
            self.y <<= self.a


class SignedExprTop(Module):
    def __init__(self):
        super().__init__("SignedExprTop")
        self.a = Input(8, "a", signed=True)
        self.out = Output(8, "out")
        self.u = SignedExprLeaf()

        @self.comb
        def _comb():
            self.u.a <<= self.a
            self.out <<= SRA(self.u.y, 2).as_uint()[7:0]


class ThreeStageLeaf(Module):
    def __init__(self, stage_add: int, name: str):
        super().__init__(name)
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")

        @self.comb
        def _comb():
            self.dout <<= self.din + stage_add


class ThreeStageChainTop(Module):
    def __init__(self):
        super().__init__("ThreeStageChainTop")
        self.a = Input(8, "a")
        self.out = Output(8, "out")
        self.s0_mid = Wire(8, "s0_mid")
        self.s1_mid = Wire(8, "s1_mid")
        self.u0 = ThreeStageLeaf(1, name="StageAdd")
        self.u1 = ThreeStageLeaf(2, name="StageAdd")
        self.u2 = ThreeStageLeaf(3, name="StageAdd")

        @self.comb
        def _comb():
            self.u0.din <<= self.a
            self.s0_mid <<= self.u0.dout
            self.u1.din <<= self.s0_mid
            self.s1_mid <<= self.u1.dout
            self.u2.din <<= self.s1_mid
            self.out <<= self.u2.dout


class ThreeStageReadyValidChainTop(Module):
    def __init__(self):
        super().__init__("ThreeStageReadyValidChainTop")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.in_data = Input(8, "in_data")
        self.in_valid = Input(1, "in_valid")
        self.in_ready = Output(1, "in_ready")
        self.out_data = Output(8, "out_data")
        self.out_valid = Output(1, "out_valid")
        self.out_ready = Input(1, "out_ready")
        self.link0_data = Wire(8, "link0_data")
        self.link0_valid = Wire(1, "link0_valid")
        self.link0_ready = Wire(1, "link0_ready")
        self.link1_data = Wire(8, "link1_data")
        self.link1_valid = Wire(1, "link1_valid")
        self.link1_ready = Wire(1, "link1_ready")
        self.u0 = ReadyValidRegister(width=8)
        self.u1 = ReadyValidRegister(width=8)
        self.u2 = ReadyValidRegister(width=8)

        @self.comb
        def _comb():
            self.u0.clk <<= self.clk
            self.u0.rst <<= self.rst
            self.u1.clk <<= self.clk
            self.u1.rst <<= self.rst
            self.u2.clk <<= self.clk
            self.u2.rst <<= self.rst

            self.u0.in_data <<= self.in_data
            self.u0.in_valid <<= self.in_valid
            self.in_ready <<= self.u0.in_ready
            self.link0_data <<= self.u0.out_data
            self.link0_valid <<= self.u0.out_valid
            self.u0.out_ready <<= self.link0_ready

            self.u1.in_data <<= self.link0_data
            self.u1.in_valid <<= self.link0_valid
            self.link0_ready <<= self.u1.in_ready
            self.link1_data <<= self.u1.out_data
            self.link1_valid <<= self.u1.out_valid
            self.u1.out_ready <<= self.link1_ready

            self.u2.in_data <<= self.link1_data
            self.u2.in_valid <<= self.link1_valid
            self.link1_ready <<= self.u2.in_ready
            self.out_data <<= self.u2.out_data
            self.out_valid <<= self.u2.out_valid
            self.u2.out_ready <<= self.out_ready


class FsmControlledDatapathLeaf(Module):
    def __init__(self):
        super().__init__("FsmControlledDatapathLeaf")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.load = Input(1, "load")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.done = Output(1, "done")
        self.busy = Output(1, "busy")
        self._data_reg = Reg(8, "data_reg")
        self._stage_reg = Reg(1, "stage_reg")
        self._done_reg = Reg(1, "done_reg")

        @self.comb
        def _comb():
            self.dout <<= self._data_reg
            self.done <<= self._done_reg
            self.busy <<= self._stage_reg

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self._data_reg <<= 0
                self._stage_reg <<= 0
                self._done_reg <<= 0
            with Else():
                self._done_reg <<= 0
                with If(self.load):
                    self._data_reg <<= (self.din << 1) + 1
                    self._stage_reg <<= 1
                with Else():
                    with If(self._stage_reg == 1):
                        self._data_reg <<= self._data_reg + 3
                        self._stage_reg <<= 0
                        self._done_reg <<= 1


class ParentFsmChildDatapathTop(Module):
    def __init__(self):
        super().__init__("ParentFsmChildDatapathTop")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.start = Input(1, "start")
        self.din = Input(8, "din")
        self.busy = Output(1, "busy")
        self.valid = Output(1, "valid")
        self.out = Output(8, "out")
        self.launch = Wire(1, "launch")
        self.child_done = Wire(1, "child_done")
        self.child_result = Wire(8, "child_result")
        self.u = FsmControlledDatapathLeaf()

        fsm = FSM("IDLE", name="ctrl")
        fsm.add_output("issue", default=0)
        fsm.add_output("waiting", default=0)
        fsm.add_output("capture", default=0)

        @fsm.state("IDLE")
        def idle(ctx):
            ctx.goto("ISSUE", when=self.start)

        @fsm.state("ISSUE")
        def issue(ctx):
            ctx.issue = 1
            ctx.goto("WAIT")

        @fsm.state("WAIT")
        def wait_state(ctx):
            ctx.waiting = 1
            ctx.goto("CAPTURE", when=self.child_done)

        @fsm.state("CAPTURE")
        def capture(ctx):
            ctx.capture = 1
            ctx.goto("IDLE")

        fsm.build(self.clk, self.rst, parent=self)

        @self.comb
        def _comb():
            self.launch <<= self.issue
            self.u.clk <<= self.clk
            self.u.rst <<= self.rst
            self.u.load <<= self.launch
            self.u.din <<= self.din + 1
            self.child_done <<= self.u.done
            self.child_result <<= self.u.dout
            self.busy <<= self.issue | self.waiting
            self.valid <<= self.capture
            self.out <<= self.child_result


class DualLutInitTop(Module):
    def __init__(self):
        super().__init__("DualLutInitTop")
        self.addr0 = Input(2, "addr0")
        self.addr1 = Input(2, "addr1")
        self.out0 = Output(8, "out0")
        self.out1 = Output(8, "out1")
        self.u0 = LUT(8, init_data=[1, 2, 3, 4], depth=4, name="MyLut")
        self.u1 = LUT(8, init_data=[11, 22, 33, 44], depth=4, name="MyLut")

        @self.comb
        def _comb():
            self.u0.addr <<= self.addr0
            self.u1.addr <<= self.addr1
            self.out0 <<= self.u0.dout
            self.out1 <<= self.u1.dout


class DeclaredDomainMailbox(Module):
    def __init__(self):
        super().__init__("DeclaredDomainMailbox")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst_n = Input(1, "rd_rst_n")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.mem = Memory(8, 4, "mailbox_mem", init_zero=True)
        self.wptr = Reg(2, "wptr")
        self.rptr = Reg(2, "rptr")

        self.wr_reset_dom = self.reset_domain("wr_reset", self.wr_rst)
        self.rd_reset_dom = self.reset_domain(
            "rd_reset",
            self.rd_rst_n,
            reset_async=True,
            reset_active_low=True,
        )
        self.wr_domain = self.clock_domain("write", self.wr_clk, self.wr_reset_dom)
        self.rd_domain = self.clock_domain("read", self.rd_clk, self.rd_reset_dom)

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.rptr]

        @self.seq_domain(self.wr_domain)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.wptr <<= 0
            with Else():
                with If(self.wr_en == 1):
                    self.mem[self.wptr] <<= self.din
                    self.wptr <<= self.wptr + 1

        @self.seq_domain(self.rd_domain)
        def _rd_seq():
            with If(self.rd_rst_n == 0):
                self.rptr <<= 0
            with Else():
                with If(self.rd_en == 1):
                    self.rptr <<= self.rptr + 1


class DeclaredDomainMailboxByName(Module):
    def __init__(self):
        super().__init__("DeclaredDomainMailboxByName")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst_n = Input(1, "rd_rst_n")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.mem = Memory(8, 4, "mailbox_mem", init_zero=True)
        self.wptr = Reg(2, "wptr")
        self.rptr = Reg(2, "rptr")

        self.reset_domain("wr_reset", self.wr_rst)
        self.reset_domain(
            "rd_reset",
            self.rd_rst_n,
            reset_async=True,
            reset_active_low=True,
        )
        self.clock_domain("write", self.wr_clk, self.declared_reset_domains[0])
        self.clock_domain("read", self.rd_clk, self.declared_reset_domains[1])

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.rptr]

        @self.seq_domain("write")
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.wptr <<= 0
            with Else():
                with If(self.wr_en == 1):
                    self.mem[self.wptr] <<= self.din
                    self.wptr <<= self.wptr + 1

        @self.seq_domain("read")
        def _rd_seq():
            with If(self.rd_rst_n == 0):
                self.rptr <<= 0
            with Else():
                with If(self.rd_en == 1):
                    self.rptr <<= self.rptr + 1


class DeclaredDomainMailboxByResetName(Module):
    def __init__(self):
        super().__init__("DeclaredDomainMailboxByResetName")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst_n = Input(1, "rd_rst_n")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.mailbox_mem = Array(8, 4, "mailbox_mem")
        self.wptr = Reg(2, "wptr")
        self.rptr = Reg(2, "rptr")

        self.reset_domain("wr_reset", self.wr_rst)
        self.reset_domain("rd_reset", self.rd_rst_n, reset_async=True, reset_active_low=True)
        self.clock_domain("write", self.wr_clk, "wr_reset")
        self.clock_domain("read", self.rd_clk, "rd_reset")

        @self.comb
        def _comb():
            self.dout <<= self.mailbox_mem[self.rptr]

        @self.seq_domain("write")
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.wptr <<= 0
            with Else():
                with If(self.wr_en == 1):
                    self.mailbox_mem[self.wptr] <<= self.din
                    self.wptr <<= self.wptr + 1

        @self.seq_domain("read")
        def _rd_seq():
            with If(self.rd_rst_n == 0):
                self.rptr <<= 0
            with Else():
                with If(self.rd_en == 1):
                    self.rptr <<= self.rptr + 1


class ArithmeticShiftLane(Module):
    def __init__(self):
        super().__init__("ArithmeticShiftLane")
        self.inp = Input(8, "inp")
        self.shamt = Input(3, "shamt")
        self.out = Output(8, "out")

        @self.comb
        def _comb():
            self.out <<= SRA(self.inp.as_sint(), self.shamt).as_uint()[7:0]


class ArithmeticShiftUnsignedLane(Module):
    def __init__(self):
        super().__init__("ArithmeticShiftUnsignedLane")
        self.inp = Input(8, "inp")
        self.shamt = Input(3, "shamt")
        self.out = Output(8, "out")

        @self.comb
        def _comb():
            self.out <<= SRA(self.inp, self.shamt).as_uint()[7:0]


class FixedPointRoundShiftLane(Module):
    def __init__(self):
        super().__init__("FixedPointRoundShiftLane")
        self.inp = Input(16, "inp")
        self.out = Output(17, "out")

        @self.comb
        def _comb():
            self.out <<= RoundShiftRight(self.inp.as_sint(), 3).as_uint()


class FixedPointRoundClipLane(Module):
    def __init__(self):
        super().__init__("FixedPointRoundClipLane")
        self.inp = Input(24, "inp", signed=True)
        self.rounded = Wire(24, "rounded", signed=True)
        self.shifted = Wire(25, "shifted", signed=True)
        self.clipped = Wire(25, "clipped", signed=True)
        self.out = Output(8, "out")

        @self.comb
        def _comb():
            self.rounded <<= RoundShiftRight(self.inp.as_sint(), 4)
            self.shifted <<= self.rounded.as_sint() + Const(128, 25).as_sint()
            self.clipped <<= Mux(
                self.shifted.as_sint() < Const(0, 25).as_sint(),
                Const(0, 25),
                Mux(
                    self.shifted.as_sint() > Const(255, 25).as_sint(),
                    Const(255, 25),
                    self.shifted,
                ),
            )
            self.out <<= self.clipped[7:0]


class TinyRegFile(Module):
    def __init__(self):
        super().__init__("TinyRegFile")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.we = Input(1, "we")
        self.waddr = Input(2, "waddr")
        self.wdata = Input(8, "wdata")
        self.raddr = Input(2, "raddr")
        self.rdata = Output(8, "rdata")
        self.rf = Array(8, 4, "rf")

        @self.comb
        def _comb():
            self.rdata <<= self.rf[self.raddr]

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.we):
                self.rf[self.waddr] <<= self.wdata


class MultiSeqActiveLow(Module):
    def __init__(self):
        super().__init__("MultiSeqActiveLow")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.we = Input(1, "we")
        self.addr = Input(2, "addr")
        self.din = Input(8, "din")
        self.out = Output(8, "out")
        self.acc = Reg(8, "acc")
        self.rf = Array(8, 4, "rf")

        @self.comb
        def _comb():
            self.out <<= self.acc + self.rf[self.addr]

        @self.seq(self.clk, ~self.rst_n)
        def _seq_acc():
            with If(~self.rst_n):
                self.acc <<= 0
            with Else():
                self.acc <<= self.acc + 1

        @self.seq(self.clk, ~self.rst_n)
        def _seq_rf():
            with If(~self.rst_n):
                self.rf[0] <<= 0
            with Else():
                with If(self.we):
                    self.rf[self.addr] <<= self.din


class DualClockMailbox(Module):
    def __init__(self):
        super().__init__("DualClockMailbox")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.mem = Memory(8, 4, "mailbox_mem", init_zero=True)
        self.wptr = Reg(2, "wptr")
        self.rptr = Reg(2, "rptr")

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.rptr]

        @self.seq(self.wr_clk, self.wr_rst)
        def _wr_seq():
            with If(self.wr_rst == 1):
                self.wptr <<= 0
            with Else():
                with If(self.wr_en == 1):
                    self.mem[self.wptr] <<= self.din
                    self.wptr <<= self.wptr + 1

        @self.seq(self.rd_clk, self.rd_rst)
        def _rd_seq():
            with If(self.rd_rst == 1):
                self.rptr <<= 0
            with Else():
                with If(self.rd_en == 1):
                    self.rptr <<= self.rptr + 1


class ConflictingClockResetBlocks(Module):
    def __init__(self):
        super().__init__("ConflictingClockResetBlocks")
        self.clk = Input(1, "clk")
        self.rst_a = Input(1, "rst_a")
        self.rst_b = Input(1, "rst_b")
        self.out = Output(8, "out")
        self.a = Reg(8, "a")
        self.b = Reg(8, "b")

        @self.comb
        def _comb():
            self.out <<= self.a + self.b

        @self.seq(self.clk, self.rst_a)
        def _seq_a():
            with If(self.rst_a == 1):
                self.a <<= 0
            with Else():
                self.a <<= self.a + 1

        @self.seq(self.clk, self.rst_b)
        def _seq_b():
            with If(self.rst_b == 1):
                self.b <<= 0
            with Else():
                self.b <<= self.b + 1


class SeqMulTruncate(Module):
    """Sequential block registers a truncated product (full width -> 16-bit reg)."""

    def __init__(self):
        super().__init__("SeqMulTruncate")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.out = Output(16, "out")
        self.y_reg = Reg(16, "y_reg")

        @self.comb
        def _comb():
            self.out <<= self.y_reg

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.y_reg <<= 0
            with Else():
                self.y_reg <<= self.a * self.b


class SeqMulSlice(Module):
    """Sequential block registers a sliced product (slice of product in seq)."""

    def __init__(self):
        super().__init__("SeqMulSlice")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.out = Output(16, "out")
        self.y_reg = Reg(16, "y_reg")

        @self.comb
        def _comb():
            self.out <<= self.y_reg

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.y_reg <<= 0
            with Else():
                self.y_reg <<= (self.a * self.b)[15:0]


class SeqMulProductReg(Module):
    """gpu_sm-style: 32-bit product register, low 16 bits extracted next cycle."""

    def __init__(self):
        super().__init__("SeqMulProductReg")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.out = Output(16, "out")
        self.acc = Reg(16, "acc")
        self.prod = Reg(32, "prod")

        @self.comb
        def _comb():
            self.out <<= self.acc

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.acc <<= 0
                self.prod <<= 0
            with Else():
                self.prod <<= self.a * self.b
                self.acc <<= self.prod[15:0]


class SeqBitUpdateUsesOldState(Module):
    """Sequential partial update should read the old state value on the RHS."""

    def __init__(self):
        super().__init__("SeqBitUpdateUsesOldState")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.flag = Input(1, "flag")
        self.out = Output(8, "out")
        self.state = Reg(8, "state")

        @self.comb
        def _comb():
            self.out <<= self.state

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.state <<= 0xA0
            with Else():
                self.state[2] <<= self.flag


def _load_external_module(rel_path: str, class_name: str):
    path = Path(__file__).resolve().parents[2] / rel_path
    spec = importlib.util.spec_from_file_location(f"test_{path.stem}_{class_name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, class_name)()


def _step_python_and_compiled(python_sim: PythonSimulator, compiled, vector):
    inputs = {name: int(vector.get(name, 0)) for name in python_sim.input_names}
    expected = python_sim.step(inputs)
    actual = compiled.step({name: int(vector.get(name, 0)) for name in compiled.input_names})
    assert actual == expected


def _step_multiclock_python_and_compiled(
    python_sim: PythonSimulator,
    compiled,
    vector,
    active_domains,
):
    inputs = {name: int(vector.get(name, 0)) for name in python_sim.input_names}
    expected = python_sim.step_clocks(inputs, active_domains)
    actual = compiled.step_clocks(
        {name: int(vector.get(name, 0)) for name in compiled.input_names},
        active_domains,
    )
    assert actual == expected
    return expected


def _three_stage_ready_valid_vectors():
    return (
        {"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0},
        {"clk": 0, "rst": 0, "in_data": 0x11, "in_valid": 1, "out_ready": 0},
        {"clk": 0, "rst": 0, "in_data": 0x22, "in_valid": 1, "out_ready": 0},
        {"clk": 0, "rst": 0, "in_data": 0x33, "in_valid": 1, "out_ready": 0},
        {"clk": 0, "rst": 0, "in_data": 0x44, "in_valid": 1, "out_ready": 1},
        {"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1},
        {"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1},
        {"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1},
    )


def _parent_fsm_child_datapath_vectors():
    return (
        {"clk": 0, "rst": 1, "start": 0, "din": 0},
        {"clk": 0, "rst": 0, "start": 1, "din": 5},
        {"clk": 0, "rst": 0, "start": 0, "din": 5},
        {"clk": 0, "rst": 0, "start": 0, "din": 0},
        {"clk": 0, "rst": 0, "start": 0, "din": 0},
        {"clk": 0, "rst": 0, "start": 0, "din": 0},
    )


def test_dsl_emits_verilog():
    text = VerilogEmitter().emit(Accum())

    assert "module Accum" in text
    assert "input [7:0] inp" in text
    assert "output [7:0] out" in text


def test_dsl_emit_prefers_explicit_module_name():
    text = VerilogEmitter().emit(NamedByString())

    assert "module named_by_string" in text
    assert "module NamedByString" not in text


def test_dsl_emits_external_parameterized_blackbox_instance():
    text = VerilogEmitter().emit(UsesExternalParameterizedLeaf())

    assert "module UsesExternalParameterizedLeaf" in text
    assert "ext_param_leaf #(.WIDTH(16), .LATENCY(2)) leaf (" in text
    assert ".din(din)" in text
    assert ".dout(dout)" in text
    assert "leaf_dout" not in text


def test_emit_design_skips_external_verilog_blackbox_shell():
    text = VerilogEmitter().emit_design(UsesExternalParameterizedLeaf())

    assert "module UsesExternalParameterizedLeaf" in text
    assert "ext_param_leaf #(.WIDTH(16), .LATENCY(2)) leaf (" in text
    assert "module ext_param_leaf" not in text


def test_emit_design_keeps_distinct_lut_modules_when_init_data_differs():
    text = VerilogEmitter().emit_design(DualLutInitTop())

    assert "module MyLut (" in text
    assert "module MyLut_1 (" in text
    assert "lut[0] = 8'd1;" in text
    assert "lut[0] = 8'd11;" in text
    assert "MyLut u0 (" in text
    assert "MyLut_1 u1 (" in text


def test_emit_design_keeps_distinct_rom_modules_when_init_file_differs():
    class InitFileLeaf(Module):
        def __init__(self, init_file, name="InitFileLeaf"):
            super().__init__(name)
            self.addr = Input(2, "addr")
            self.dout = Output(8, "dout")
            self.mem = self.add_memory(Memory(8, 4, "mem", init_file=init_file))

            @self.comb
            def _comb():
                self.dout <<= self.mem[self.addr]

    class DualInitFileTop(Module):
        def __init__(self):
            super().__init__("DualInitFileTop")
            self.addr0 = Input(2, "addr0")
            self.addr1 = Input(2, "addr1")
            self.out0 = Output(8, "out0")
            self.out1 = Output(8, "out1")
            self.u0 = InitFileLeaf("rom0.hex", name="RomLeaf")
            self.u1 = InitFileLeaf("rom1.hex", name="RomLeaf")

            @self.comb
            def _comb():
                self.u0.addr <<= self.addr0
                self.u1.addr <<= self.addr1
                self.out0 <<= self.u0.dout
                self.out1 <<= self.u1.dout

    text = VerilogEmitter().emit_design(DualInitFileTop())

    assert 'module RomLeaf (' in text
    assert 'module RomLeaf_1 (' in text
    assert '$readmemh("rom0.hex", mem);' in text
    assert '$readmemh("rom1.hex", mem);' in text
    assert 'RomLeaf u0 (' in text
    assert 'RomLeaf_1 u1 (' in text


def test_emit_design_renames_reserved_internal_signal_identifiers():
    class ReservedNameLeaf(Module):
        def __init__(self):
            super().__init__("ReservedNameLeaf")
            self.inp = Input(8, "inp")
            self.out = Output(8, "out")
            self.final = Wire(8, "final")

            @self.comb
            def _comb():
                self.final <<= self.inp
                self.out <<= self.final

    text = VerilogEmitter(profile=EmitProfile.review()).emit(ReservedNameLeaf())

    assert "logic [7:0] final_sv;" in text
    assert "assign final_sv = inp;" in text
    assert "assign out = $signed(final_sv);" in text or "assign out = final_sv;" in text
    assert "logic [7:0] final;" not in text


def test_collect_external_verilog_artifacts_from_mixed_design():
    artifacts = collect_external_verilog_artifacts(UsesExternalParameterizedLeaf())

    assert artifacts["sources"] == ("rtl/ext_param_leaf.sv",)
    assert artifacts["include_dirs"] == ("rtl/include",)
    assert artifacts["defines"] == {"EXT_PARAM_LEAF": "1"}
    assert artifacts["init_files"] == ()


def test_collect_external_verilog_artifacts_include_rom_init_files_from_mixed_design():
    artifacts = collect_external_verilog_artifacts(MixedExternalRomTop())

    assert artifacts["sources"] == ("rtl/ext_param_leaf.sv",)
    assert artifacts["include_dirs"] == ("rtl/include",)
    assert artifacts["defines"] == {"EXT_PARAM_LEAF": "1"}
    assert artifacts["init_files"] == ("roms/mixed_rom.hex",)


def test_dsl_emits_extracted_concat_without_constructor_collision():
    text = VerilogEmitter().emit(ConcatWidened())

    assert "module concat_widened" in text
    assert "assign out =" in text


def test_dsl_nested_slice_binop_emits_iverilog_safe_verilog(tmp_path):
    text = VerilogEmitter().emit(NestedSliceBinOp())

    assert "module nested_slice_binop" in text
    assert "assign out =" in text
    assert ">>" in text
    assert "&" in text

    compiler = shutil.which("iverilog")
    if compiler is None:
        pytest.skip("iverilog not installed")

    rtl = tmp_path / "nested_slice_binop.v"
    rtl.write_text(text, encoding="utf-8")
    out = tmp_path / "nested_slice_binop.vvp"
    cp = subprocess.run(
        [compiler, "-g2012", "-o", str(out), str(rtl)],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, f"iverilog compile failed:\n{cp.stderr}"


def test_emit_profile_review_and_compact_change_readability_contract():
    review_text = VerilogEmitter(profile=EmitProfile.review()).emit(ReadableRepeatedExpr())
    compact_text = VerilogEmitter(profile=EmitProfile.compact()).emit(ReadableRepeatedExpr())

    assert "// Module: readable_repeated_expr" in review_text
    assert "// Module: readable_repeated_expr" not in compact_text
    assert "// Comb:" in review_text
    assert "// Comb:" not in compact_text
    assert "_out_ex" in review_text
    assert "_cse_" not in review_text
    assert "_cse_" in compact_text


def test_emit_profile_review_extracts_repeated_subexpressions_with_target_local_names():
    review_text = VerilogEmitter(profile=EmitProfile.review()).emit(ReadableRepeatedExpr())

    assert "assign _out_ex0 = a + b;" in review_text
    assert "assign _out_ex1 = _out_ex0 ^ _out_ex0" in review_text
    assert "assign out = _out_ex" in review_text
    assert "assign out = _out_ex1 ^ _out_ex2 ^ _out_ex3;" in review_text
    assert "assign _out_ex0 = a + b ^ a + b" not in review_text


def test_emit_profile_systemverilog_uses_sv_always_keywords():
    emitted = VerilogEmitter(profile=EmitProfile.systemverilog()).emit(ReadableCombSeq())

    assert "always_comb begin" in emitted
    assert "always_ff @(posedge clk)" in emitted


def test_emit_profile_review_includes_readable_sections_and_seq_timing_comments():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(DeclaredDomainMailbox())

    assert "// Storage declarations" in emitted
    assert "// Internal declarations" in emitted
    assert "// Combinational logic" in emitted
    assert "// Sequential logic" in emitted
    assert "// Seq timing: clk=wr_clk, reset=wr_rst (sync, active-high)" in emitted
    assert "// Seq timing: clk=rd_clk, reset=rd_rst_n (async, active-low)" in emitted


def test_emit_profile_review_readability_contract_avoids_duplicated_block_prefixes():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(DeclaredDomainMailbox())

    assert "// Comb: dout" in emitted
    assert "// Seq: wptr" in emitted
    assert "// Seq: rptr" in emitted
    assert "Comb: Comb:" not in emitted
    assert "Seq: Seq:" not in emitted


def test_emit_profile_review_places_port_expression_helpers_in_structural_section():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(PortExprTop())

    expected_markers = (
        "// Structural wiring and instances",
        "// Port connection helpers",
        "wire [7:0] u_leaf_din_expr;",
        "assign u_leaf_din_expr = ((a + b) & 8'd255);",
        "PortExprLeaf u_leaf (",
        ".din(u_leaf_din_expr)",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_analyze_emitted_readability_accepts_review_profile_output():
    report = analyze_emitted_readability(ReadableRepeatedExpr(), profile=EmitProfile.review())

    assert report.passed is True
    assert report.profile == "review"
    assert report.long_line_count == 0
    assert report.anonymous_helper_count == 0
    assert report.duplicated_block_prefix_count == 0


def test_analyze_verilog_readability_flags_machineish_helpers_and_long_mux_lines():
    text = "\n".join(
        (
            "module ugly;",
            "  wire [7:0] _cse_0;",
            "  assign out = a ? b : c ? d : e ? f : g ? h : i;",
            "endmodule",
        )
    )
    report = analyze_verilog_readability(text, profile="review", max_line_length=40, max_mux_ternaries_per_assign=2)

    assert report.passed is False
    assert report.long_line_count == 1
    assert report.anonymous_helper_count == 1
    assert report.deep_mux_assign_count == 1
    assert {finding.kind for finding in report.findings} == {
        "anonymous_helper",
        "deep_mux_assign",
        "long_line",
        "missing_module_header",
        "missing_port_table",
    }


def test_emit_readability_report_markdown_summarizes_findings():
    report = analyze_verilog_readability(
        "module ugly;\n  wire _cse_0;\nendmodule",
        profile="review",
        max_line_length=80,
    )
    markdown = emit_readability_report_markdown(report, title="Readable RTL")

    assert "# Readable RTL" in markdown
    assert "- profile: `review`" in markdown
    assert "- passed: `false`" in markdown
    assert "## Findings" in markdown
    assert "`anonymous_helper`" in markdown


def test_analyze_marker_sequence_reports_missing_and_out_of_order_markers():
    text = "\n".join(
        (
            "module sample;",
            "  // Internal declarations",
            "  // Combinational logic",
            "  // Storage declarations",
            "endmodule",
        )
    )

    report = analyze_marker_sequence(
        text,
        (
            "// Storage declarations",
            "// Internal declarations",
            "// Sequential logic",
        ),
        context="sample review RTL",
    )

    assert isinstance(report, MarkerSequenceReport)
    assert report.passed is False
    assert report.expected_marker_count == 3
    assert report.matched_marker_count == 1
    assert [finding.kind for finding in report.findings] == [
        "out_of_order_marker",
        "missing_marker",
    ]


def test_emit_marker_sequence_report_markdown_summarizes_findings():
    report = analyze_marker_sequence(
        "module sample;\n  // Internal declarations\nendmodule",
        ("// Storage declarations",),
        context="sample review RTL",
    )
    markdown = emit_marker_sequence_report_markdown(report, title="Readable Marker Contract")

    assert "# Readable Marker Contract" in markdown
    assert "- context: `sample review RTL`" in markdown
    assert "- passed: `false`" in markdown
    assert "## Findings" in markdown
    assert "`missing_marker` `// Storage declarations`" in markdown


def test_assert_readable_verilog_raises_readability_contract_error_with_markdown():
    with pytest.raises(ReadabilityContractError) as excinfo:
        assert_readable_verilog(
            "module ugly;\n  wire _cse_0;\nendmodule",
            profile="review",
        )

    assert "# RTL Readability Report" in str(excinfo.value)
    assert "`anonymous_helper`" in str(excinfo.value)


def test_assert_marker_sequence_raises_readability_contract_error_with_markdown():
    with pytest.raises(ReadabilityContractError) as excinfo:
        assert_marker_sequence(
            "module sample;\n  // Internal declarations\nendmodule",
            ("// Storage declarations",),
            context="sample review RTL",
        )

    assert "# RTL Marker Contract Report" in str(excinfo.value)
    assert "`missing_marker` `// Storage declarations`" in str(excinfo.value)


def test_assert_emitted_rtl_contract_enforces_readability_and_marker_gate():
    emitted = assert_emitted_rtl_contract(
        DeclaredDomainMailbox(),
        expected_markers=(
            "// Storage declarations",
            "// Internal declarations",
            "// Combinational logic",
            "// Sequential logic",
        ),
        profile=EmitProfile.review(),
    )

    assert "// Module: DeclaredDomainMailbox" in emitted


def test_emit_profile_review_declared_domain_mailbox_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(DeclaredDomainMailbox())

    expected_markers = (
        "// Storage declarations",
        "reg [7:0] mailbox_mem [0:3];",
        "// Internal declarations",
        "reg [1:0] wptr;",
        "reg [1:0] rptr;",
        "// Combinational logic",
        "// Comb: dout",
        "assign dout = mailbox_mem[rptr];",
        "// Sequential logic",
        "// Seq timing: clk=wr_clk, reset=wr_rst (sync, active-high)",
        "// Seq: wptr",
        "always @(posedge wr_clk) begin",
        "// Seq timing: clk=rd_clk, reset=rd_rst_n (async, active-low)",
        "// Seq: rptr",
        "always @(posedge rd_clk or negedge rd_rst_n) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_synccell_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(SyncCell())

    expected_markers = (
        "// Internal declarations",
        "reg sync_ff1;",
        "reg sync_ff2;",
        "// Combinational logic",
        "assign data_out = sync_ff2;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "// Seq: sync_ff1, sync_ff2",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_asyncresetrel_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(AsyncResetRel())

    expected_markers = (
        "// Internal declarations",
        "reg ar_ff1;",
        "reg ar_ff2;",
        "// Combinational logic",
        "assign rst_sync = ~ar_ff2;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst_async (async, active-high)",
        "// Seq: ar_ff1, ar_ff2",
        "always @(posedge clk or posedge rst_async) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_pulsesynchronizer_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(PulseSynchronizer())

    expected_markers = (
        "// Internal declarations",
        "reg toggle_src;",
        "reg sync_0;",
        "reg sync_1;",
        "reg sync_2;",
        "// Combinational logic",
        "assign pulse_out = sync_1 ^ sync_2;",
        "// Sequential logic",
        "// Seq timing: clk=clk_src, reset=rst (sync, active-high)",
        "// Seq: toggle_src",
        "always @(posedge clk_src) begin",
        "// Seq timing: clk=clk_dst, reset=rst (sync, active-high)",
        "// Seq: sync_0, sync_1, sync_2",
        "always @(posedge clk_dst) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_ready_valid_async_bridge_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(ReadyValidAsyncBridge())

    expected_markers = (
        "// Internal declarations",
        "logic rd_fire;",
        "logic [31:0] fifo_dout;",
        "logic fifo_full;",
        "logic fifo_empty;",
        "// Structural wiring and instances",
        "AsyncFIFO u_fifo (",
        ".wr_en(in_valid & in_ready)",
        ".rd_en(rd_fire)",
        ".dout(fifo_dout)",
        ".full(fifo_full)",
        ".empty(fifo_empty)",
        "// Combinational logic",
        "assign in_ready = ~fifo_full;",
        "assign out_valid = ~fifo_empty;",
        "assign out_data = fifo_dout;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_async_fifo_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(AsyncFIFO(width=8, depth=4))

    expected_markers = (
        "// Storage declarations",
        "reg [7:0] af_mem [0:3];",
        "// Internal declarations",
        "logic [2:0] wr_nxt;",
        "logic [2:0] wr_nxt_gray;",
        "logic [2:0] rd_nxt;",
        "reg [2:0] wr_ptr;",
        "reg [2:0] rd_ptr;",
        "// Combinational logic",
        "assign wr_nxt = wr_ptr + 1'd1;",
        "assign wr_nxt_gray = wr_nxt ^ wr_nxt >> 1'd1;",
        "assign full = wr_nxt_gray == {~rds_1[2:1], rds_1[0]};",
        "assign empty = rd_gray == wrs_1;",
        "assign dout = af_mem[rd_ptr[1:0]];",
        "// Sequential logic",
        "// Seq timing: clk=wr_clk, reset=wr_rst (sync, active-high)",
        "always @(posedge wr_clk) begin",
        "// Seq timing: clk=rd_clk, reset=rd_rst (sync, active-high)",
        "always @(posedge rd_clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_sync_fifo_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(SyncFIFO(width=8, depth=4))

    expected_markers = (
        "// Storage declarations",
        "// Internal declarations",
        "logic wr_inc;",
        "logic rd_inc;",
        "reg [1:0] wr_ptr;",
        "reg [1:0] rd_ptr;",
        "reg [2:0] count_reg;",
        "reg [7:0] storage [0:3];",
        "// Combinational logic",
        "always @(*) begin",
        "full = count_reg == 3'd4;",
        "empty = count_reg == 1'd0;",
        "count = count_reg;",
        "rd_rdy = ~empty;",
        "dout = storage[rd_ptr];",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_sync_fifo_lowers_and_buffers_single_clock_storage(tmp_path):
    lowered = lower_dsl_module_to_sim(SyncFIFO(width=8, depth=4))
    sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        SyncFIFO(width=8, depth=4),
        build_dir=tmp_path / "sync_fifo",
    )
    try:
        vectors = (
            (
                {"clk": 0, "rst": 1, "din": 0, "wr_en": 0, "rd_en": 0},
                {"dout": 0, "full": 0, "empty": 1, "count": 0, "rd_rdy": 0},
            ),
            (
                {"clk": 0, "rst": 0, "din": 0x11, "wr_en": 1, "rd_en": 0},
                {"dout": 0x11, "full": 0, "empty": 0, "count": 1, "rd_rdy": 1},
            ),
            (
                {"clk": 0, "rst": 0, "din": 0x22, "wr_en": 1, "rd_en": 0},
                {"dout": 0x11, "full": 0, "empty": 0, "count": 2, "rd_rdy": 1},
            ),
            (
                {"clk": 0, "rst": 0, "din": 0, "wr_en": 0, "rd_en": 1},
                {"dout": 0x22, "full": 0, "empty": 0, "count": 1, "rd_rdy": 1},
            ),
            (
                {"clk": 0, "rst": 0, "din": 0, "wr_en": 0, "rd_en": 1},
                {"dout": 0, "full": 0, "empty": 1, "count": 0, "rd_rdy": 0},
            ),
        )
        for inputs, expected in vectors:
            assert sim.step(inputs) == expected
            assert compiled.step(inputs) == expected
    finally:
        compiled.close()


def test_emit_profile_review_apb_register_bank_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(APBRegisterBank(depth=4))

    expected_markers = (
        "// Storage declarations",
        "reg [31:0] regmem [0:3];",
        "// Internal declarations",
        "reg [31:0] rdata_reg;",
        "// Combinational logic",
        "assign prdata = rdata_reg;",
        "assign pready = psel & penable;",
        "// Sequential logic",
        "// Seq timing: clk=pclk, reset=presetn (async, active-low)",
        "always @(posedge pclk or negedge presetn) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_wishbone_register_bank_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(WishboneRegisterBank(depth=4))

    expected_markers = (
        "// Storage declarations",
        "reg [31:0] wbmem [0:3];",
        "// Internal declarations",
        "logic access_fire;",
        "reg ack_state;",
        "// Combinational logic",
        "assign access_fire = cyc_i & stb_i;",
        "assign ack_o = ack_state;",
        "// Sequential logic",
        "// Seq timing: clk=clk_i, reset=rst_i (sync, active-high)",
        "always @(posedge clk_i) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_wishbone_register_bank_split_control_state_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(
        WishboneRegisterBank(depth=4, split_control_state=True)
    )

    expected_markers = (
        "logic capture_fire;",
        "assign capture_fire = accept_fire;",
        "always @(posedge clk_i) begin",
        "always @(posedge clk_i) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker, last_index + 1)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_ready_valid_register_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(ReadyValidRegister())

    expected_markers = (
        "// Internal declarations",
        "reg [31:0] data_reg;",
        "reg valid_reg;",
        "// Combinational logic",
        "assign in_ready = (valid_reg == 1'd0) | out_ready;",
        "assign out_valid = valid_reg;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_ready_valid_register_hold_payload_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(ReadyValidRegister(hold_payload=True))

    expected_markers = (
        "// Internal declarations",
        "reg [31:0] data_reg;",
        "reg valid_reg;",
        "// Combinational logic",
        "assign in_ready = (valid_reg == 1'd0) | out_ready;",
        "// Sequential logic",
        "if (in_valid == 1'd1) begin",
        "data_reg <= in_data;",
        "end else begin",
        "data_reg <= data_reg;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_ready_valid_fifo_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(ReadyValidFIFO(depth=4))

    expected_markers = (
        "// Storage declarations",
        "// Internal declarations",
        "logic push_fire;",
        "logic pop_fire;",
        "reg [31:0] storage [0:3];",
        "// Combinational logic",
        "always @(*) begin",
        "out_valid = count != 1'd0;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_reqrsp_queue_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(
        ReqRspQueue(depth=4, addr_width=12, write_enable=True, strobe_width=4)
    )

    expected_markers = (
        "// Storage declarations",
        "// Internal declarations",
        "logic push_fire;",
        "reg [31:0] req_storage [0:3];",
        "reg [11:0] addr_storage [0:3];",
        "// Combinational logic",
        "always @(*) begin",
        "down_req_valid = count != 1'd0;",
        "up_rsp = down_rsp;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_reqrsp_queue_bundled_sideband_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(
        ReqRspQueue(depth=4, addr_width=12, write_enable=True, strobe_width=4, bundle_sideband=True)
    )

    expected_markers = (
        "// Storage declarations",
        "// Internal declarations",
        "logic push_fire;",
        "reg [48:0] entry_storage [0:3];",
        "// Combinational logic",
        "down_req = entry_storage[rd_ptr][31:0];",
        "down_addr = entry_storage[rd_ptr][43:32];",
        "down_write = entry_storage[rd_ptr][44];",
        "down_strb = entry_storage[rd_ptr][48:45];",
        "// Sequential logic",
        "entry_storage[wr_ptr] <= {up_strb, up_write, up_addr, up_req};",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_axilite_register_bank_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(AXI4LiteRegisterBank(depth=4))

    expected_markers = (
        "// Storage declarations",
        "reg [31:0] regmem [0:3];",
        "// Internal declarations",
        "logic aw_capture;",
        "logic write_commit;",
        "reg [31:0] rdata_state;",
        "// Combinational logic",
        "assign awready = ~aw_seen & ~bvalid_state;",
        "assign write_commit = (aw_seen | aw_capture) & (w_seen | w_capture) & ~bvalid_state;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_axilite_register_bank_split_control_state_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(
        AXI4LiteRegisterBank(depth=4, split_control_state=True)
    )

    expected_markers = (
        "// Internal declarations",
        "logic capture_fire;",
        "assign capture_fire = aw_capture | w_capture | read_fire;",
        "// Sequential logic",
        "// Seq: ar_addr_latched, aw_addr_latched, aw_seen",
        "else if (capture_fire == 1'd1) begin",
        "// Seq: bvalid_state, rdata_state, rvalid_state",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_skid_buffer_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(SkidBuffer(16))

    expected_markers = (
        "// Internal declarations",
        "reg buf_valid;",
        "reg [15:0] buf_data;",
        "// Combinational logic",
        "always @(*) begin",
        "in_ready = (buf_valid == 1'd0) | out_ready;",
        "out_valid = buf_valid | in_valid;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_round_robin_arbiter_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(RoundRobinArbiter(4))

    expected_markers = (
        "// Internal declarations",
        "logic [7:0] double_reqs;",
        "reg [1:0] pointer;",
        "// Combinational logic",
        "// Comb: double_reqs, grant_idx, grant_vec (+6)",
        "double_reqs = {2{reqs}};",
        "grant_vec = 4'd0;",
        "grants = grant_vec;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_divider_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(Divider(16))

    expected_markers = (
        "// Internal declarations",
        "logic [32:0] shifted_rem;",
        "reg [31:0] rem_reg;",
        "reg [15:0] quo_reg;",
        "// Combinational logic",
        "// Comb: busy, done, quotient (+1)",
        "assign quotient = quo_reg;",
        "assign remainder = rem_reg;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "// Seq: count_reg, quo_reg, rem_reg (+2)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_shiftreg_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(ShiftReg(8, 4))

    expected_markers = (
        "// Storage declarations",
        "reg [7:0] regs [0:3];",
        "// Combinational logic",
        "// Comb: dout",
        "assign dout = regs[2'd3];",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst_n (async, active-low)",
        "always @(posedge clk or negedge rst_n) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_validpipe_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(ValidPipe(8))

    expected_markers = (
        "// Internal declarations",
        "reg [7:0] data_reg;",
        "reg valid_reg;",
        "// Combinational logic",
        "// Comb: dout, valid_out",
        "assign dout = data_reg;",
        "assign valid_out = valid_reg;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst_n (async, active-low)",
        "// Seq: data_reg, valid_reg",
        "always @(posedge clk or negedge rst_n) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_pipelineshift_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(PipelineShift(16, 3))

    expected_markers = (
        "// Internal declarations",
        "reg pv_0;",
        "reg [15:0] pd_0;",
        "// Combinational logic",
        "// Comb: in_ready",
        "assign in_ready = (pv_2 == 1'd0) | out_ready;",
        "// Comb: data_out, out_valid",
        "assign data_out = pd_2;",
        "assign out_valid = pv_2;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "// Seq: pd_0, pd_1, pd_2 (+3)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_counter_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(Counter(8))

    expected_markers = (
        "// Internal declarations",
        "reg [7:0] cnt;",
        "// Combinational logic",
        "// Comb: count, max_reached, zero",
        "assign count = cnt;",
        "assign zero = cnt == 1'd0;",
        "assign max_reached = cnt >= 8'd255;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "// Seq: cnt",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_multicyclefsm_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(MultiCycleFSM(8))

    expected_markers = (
        "// Internal declarations",
        "reg [1:0] state;",
        "reg [7:0] timer;",
        "// Combinational logic",
        "// Comb: busy, done",
        "assign busy = state != 1'd0;",
        "assign done = state == 2'd3;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "// Seq: state, timer",
        "always @(posedge clk) begin",
        "case (state)",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_graycounter_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(GrayCounter(8))

    expected_markers = (
        "// Internal declarations",
        "reg [7:0] gb_bin;",
        "// Combinational logic",
        "// Comb: binary, gray",
        "assign gray = gb_bin ^ gb_bin >> 1'd1;",
        "assign binary = gb_bin;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "// Seq: gb_bin",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_decoder_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(Decoder(3))

    expected_markers = (
        "// Combinational logic",
        "// Comb: out",
        "always @(*) begin",
        "case (in)",
        "3'd7: begin",
        "out = 8'd128;",
        "if (~en) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_priorityencoder_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(PriorityEncoder(8))

    expected_markers = (
        "// Module: PriorityEncoder",
        "logic [3:0] out_wire;",
        "// Comb: out, out_wire, valid",
        "out_wire = 4'd0;",
        "if (in[7] == 1'd1) begin",
        "out = out_wire;",
        "valid = in != 1'd0;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_barrelshifter_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(BarrelShifter(16))

    expected_markers = (
        "// Module: BarrelShifter",
        "logic [15:0] result;",
        "// Comb: data_out, result",
        "result = data_in;",
        "if (shift_amount[3] == 1'd1) begin",
        "result = result << 4'd8;",
        "data_out = result;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_lfsr_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(LFSR(8))

    expected_markers = (
        "// Internal declarations",
        "logic [7:0] next_val;",
        "logic fb;",
        "reg [7:0] lfsr_reg;",
        "// Comb: out",
        "assign out = lfsr_reg;",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "fb <= lfsr_reg[0];",
        "next_val[3'd7] = fb;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_edgedetector_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(EdgeDetector())

    expected_markers = (
        "// Internal declarations",
        "reg sig_d;",
        "// Comb: falling, rising",
        "assign rising = sig & ~sig_d;",
        "assign falling = ~sig & sig_d;",
        "// Seq: sig_d",
        "sig_d <= sig;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_pipelineinterlock_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(PipelineInterlock())

    expected_markers = (
        "// Module: PipelineInterlock",
        "reg pl_v;",
        "reg pl_stall;",
        "// Comb: ready_out, valid_out",
        "assign ready_out = ~pl_stall;",
        "assign valid_out = pl_v;",
        "// Seq: pl_stall, pl_v",
        "pl_stall <= hold;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_bypassnetwork_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(BypassNetwork(4, 16))

    expected_markers = (
        "// Module: BypassNetwork",
        "// Comb: fwd_data, fwd_valid",
        "fwd_data = 16'd0;",
        "fwd_valid = 1'd0;",
        "if (rd_valid_3 & (rd_addr_3 == rs_addr)) begin",
        "fwd_data = rd_data_3;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_multicyclepath_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(MultiCyclePath(16, 3))

    expected_markers = (
        "// Internal declarations",
        "reg [15:0] mcp_0;",
        "reg [15:0] mcp_2;",
        "// Comb: data_out",
        "assign data_out = mcp_2;",
        "// Seq: mcp_0, mcp_1, mcp_2",
        "mcp_0 <= data_in;",
        "if (en == 1'd1) begin",
        "mcp_2 <= mcp_1;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_mac_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(MAC(8))

    expected_markers = (
        "// Internal declarations",
        "reg [7:0] pipe_a;",
        "reg [15:0] prod;",
        "// Comb: acc_out, valid",
        "assign acc_out = acc;",
        "assign valid = 1'd1;",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "pipe_a <= $signed(a);",
        "prod <= $signed(pipe_a) * $signed(pipe_b);",
        "acc <= acc + prod;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_signedmultiplier_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(SignedMultiplier(8, 3))

    expected_markers = (
        "// Internal declarations",
        "reg mpv_0;",
        "reg [15:0] mpd_2;",
        "// Comb: in_ready",
        "assign in_ready = (mpv_2 == 1'd0) | out_ready;",
        "// Comb: out_valid, product",
        "assign product = mpd_2;",
        "assign out_valid = mpv_2;",
        "// Seq: mpd_0, mpd_1, mpd_2 (+3)",
        "if (mpv_1 & ((mpv_2 == 1'd0) | out_ready)) begin",
        "mpd_0 <= $signed(a) * $signed(b);",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_registerfile_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(RegisterFile(8, 4, 2, 1))

    expected_markers = (
        "// Internal declarations",
        "reg [7:0] rf_0;",
        "reg [7:0] rf_3;",
        "// Comb: rd_data_0, rd_data_1",
        "rd_data_0 = 8'd0;",
        "if (rd_addr_1 == 2'd3) begin",
        "rd_data_1 = rf_3;",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "if (wr_en_0) begin",
        "rf_3 <= wr_data_0;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_dualportram_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(DualPortRAM(8, 8))

    expected_markers = (
        "// Storage declarations",
        "reg [7:0] mem [0:7];",
        "// Comb: a_rdata, b_rdata",
        "assign a_rdata = mem[a_addr];",
        "assign b_rdata = mem[b_addr];",
        "// Seq timing: clk=clk, reset=none",
        "if (a_wen) begin",
        "mem[a_addr] <= a_wdata;",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_emit_profile_review_lut_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(LUT(8, depth=8))

    expected_markers = (
        "// Storage declarations",
        "reg [7:0] lut [0:7];",
        "initial begin",
        "lut[7] = 8'd0;",
        "// Comb: dout",
        "assign dout = lut[addr];",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index


def test_ready_valid_bundle_supports_flip_and_protocol_aware_port_map():
    sink = ReadyValid(32, name="sink")
    source = sink.flip()

    assert sink.payload_name == "data"
    assert sink.direction_of("valid") == "in"
    assert sink.direction_of("ready") == "out"
    assert source.direction_of("valid") == "out"
    assert source.direction_of("ready") == "in"
    assert source.port_map()["data"].width == 32

    port_map = source.connect_port_map(sink)
    assert set(port_map) == {"data", "valid", "ready"}
    assert port_map["data"] is source.data
    assert port_map["valid"] is source.valid
    assert port_map["ready"] is sink.ready
    assert source.payload_fields() == ("data",)
    assert source.forward_fields() == ("data", "valid")
    assert source.backward_fields() == ("ready",)


def test_axistream_inherits_ready_valid_channel_shape():
    axis = AXI4Stream(32, user_width=4, has_strb=True, name="axis")
    flipped = axis.flip()

    assert axis.payload_name == "tdata"
    assert axis.valid_name == "tvalid"
    assert axis.ready_name == "tready"
    assert axis.direction_of("tvalid") == "in"
    assert axis.direction_of("tready") == "out"
    assert flipped.direction_of("tvalid") == "out"
    assert flipped.direction_of("tready") == "in"
    assert "tlast" in axis.signal_map()
    assert "tkeep" in axis.signal_map()
    assert "tuser" in axis.signal_map()
    assert "tstrb" in axis.signal_map()
    assert axis.payload_fields() == ("tdata", "tlast", "tkeep", "tuser", "tstrb")


def test_reqrsp_bundle_exposes_request_response_semantics_and_port_map():
    responder = ReqRsp(32, 16, addr_width=12, write_enable=True, strobe_width=4, name="rr_s")
    requester = responder.flip()

    assert responder.direction_of("req") == "in"
    assert responder.direction_of("req_valid") == "in"
    assert responder.direction_of("req_ready") == "out"
    assert responder.direction_of("rsp") == "out"
    assert requester.direction_of("req") == "out"
    assert requester.direction_of("rsp") == "in"
    assert requester.request_fields() == ("addr", "req", "write", "strb", "req_valid", "req_ready")
    assert requester.response_fields() == ("rsp", "rsp_valid", "rsp_ready")

    mapping = requester.connect_port_map(responder)
    assert mapping["addr"] is requester.addr
    assert mapping["req"] is requester.req
    assert mapping["write"] is requester.write
    assert mapping["strb"] is requester.strb
    assert mapping["req_valid"] is requester.req_valid
    assert mapping["req_ready"] is responder.req_ready
    assert mapping["rsp"] is responder.rsp
    assert mapping["rsp_valid"] is responder.rsp_valid
    assert mapping["rsp_ready"] is requester.rsp_ready
    assert requester.request_payload_fields() == ("addr", "req", "write", "strb")
    assert requester.response_payload_fields() == ("rsp",)


def test_apb_bundle_exposes_master_slave_semantics_and_port_map():
    slave = APB(32, 32, name="apb_s")
    master = slave.flip()

    assert master.master_fields()[0:2] == ("pclk", "presetn")
    assert "prdata" in master.slave_fields()
    assert slave.direction_of("psel") == "in"
    assert master.direction_of("psel") == "out"
    mapping = master.transaction_port_map(slave)
    assert mapping["psel"] is master.psel
    assert mapping["prdata"] is slave.prdata
    assert mapping["pready"] is slave.pready


def test_axilite_bundle_exposes_channel_semantics_and_port_map():
    slave = AXI4Lite(32, 32, name="axil_s")
    master = slave.flip()

    assert master.write_address_fields() == ("awaddr", "awvalid", "awprot")
    assert master.read_response_fields()[-2:] == ("rvalid", "rready")
    assert slave.direction_of("awvalid") == "in"
    assert master.direction_of("awvalid") == "out"
    mapping = master.transaction_port_map(slave)
    assert mapping["awaddr"] is master.awaddr
    assert mapping["wdata"] is master.wdata
    assert mapping["bvalid"] is slave.bvalid
    assert mapping["rdata"] is slave.rdata


def test_wishbone_bundle_exposes_master_slave_semantics_and_port_map():
    slave = Wishbone(32, 32, name="wb_s")
    master = slave.flip()

    assert master.clock_reset_fields() == ("clk_i", "rst_i")
    assert master.master_fields()[0:2] == ("clk_i", "rst_i")
    assert master.slave_fields() == ("dat_o", "ack_o", "err_o", "rty_o")
    assert slave.direction_of("adr_i") == "in"
    assert master.direction_of("adr_i") == "out"
    mapping = master.transaction_port_map(slave)
    assert mapping["adr_i"] is master.adr_i
    assert mapping["dat_i"] is master.dat_i
    assert mapping["ack_o"] is slave.ack_o
    assert mapping["dat_o"] is slave.dat_o


def test_bundle_prefixed_peer_port_map_targets_peer_signal_names():
    sink = ReadyValid(16, name="sink")
    source = sink.flip().prefixed("src")
    peer = sink.prefixed("u_sink")

    mapping = source.instantiate_port_map(peer)

    assert set(mapping) == {"u_sink_data", "u_sink_valid", "u_sink_ready"}
    assert mapping["u_sink_data"] is source.data
    assert mapping["u_sink_valid"] is source.valid
    assert mapping["u_sink_ready"] is source.ready


def test_module_bundle_registration_exposes_prefixed_ports():
    class BundleWrapped(Module):
        def __init__(self):
            super().__init__("BundleWrapped")
            self.in_ch = ReadyValid(8, name="in_ch").prefixed("in_ch")
            self.out_ch = ReadyValid(8, name="out_ch").flip().prefixed("out_ch")

            @self.comb
            def _comb():
                self.out_ch.data <<= self.in_ch.data
                self.out_ch.valid <<= self.in_ch.valid
                self.in_ch.ready <<= self.out_ch.ready

    wrapped = BundleWrapped()
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(wrapped)

    assert "input [7:0] in_ch_data" in emitted
    assert "input in_ch_valid" in emitted
    assert "output in_ch_ready" in emitted
    assert "output [7:0] out_ch_data" in emitted
    assert "output out_ch_valid" in emitted
    assert "input out_ch_ready" in emitted
    assert "assign out_ch_data = in_ch_data;" in emitted
    assert "assign out_ch_valid = in_ch_valid;" in emitted
    assert "assign in_ch_ready = out_ch_ready;" in emitted


def test_instantiate_with_bundles_bulk_connects_prefixed_ready_valid_ports():
    class BundleLeaf(Module):
        def __init__(self):
            super().__init__("BundleLeaf")
            self.leaf_in = ReadyValid(8, name="leaf_in").prefixed("leaf_in")
            self.leaf_out = ReadyValid(8, name="leaf_out").flip().prefixed("leaf_out")

            @self.comb
            def _comb():
                self.leaf_out.data <<= self.leaf_in.data
                self.leaf_out.valid <<= self.leaf_in.valid
                self.leaf_in.ready <<= self.leaf_out.ready

    class BundleTop(Module):
        def __init__(self):
            super().__init__("BundleTop")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.up = ReadyValid(8, name="up").prefixed("up")
            self.down = ReadyValid(8, name="down").flip().prefixed("down")
            leaf = BundleLeaf()
            self.instantiate_with_bundles(
                leaf,
                "u_leaf",
                parent_bundles={"leaf_in": self.up, "leaf_out": self.down},
                extra_ports={"clk": self.clk, "rst": self.rst},
            )

    top = BundleTop()
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(top)

    assert ".leaf_in_data(up_data)" in emitted
    assert ".leaf_in_valid(up_valid)" in emitted
    assert ".leaf_in_ready(up_ready)" in emitted
    assert ".leaf_out_data(down_data)" in emitted
    assert ".leaf_out_valid(down_valid)" in emitted
    assert ".leaf_out_ready(down_ready)" in emitted
    assert ".clk(clk)" not in emitted
    assert ".rst(rst)" not in emitted


def test_instantiate_with_bundles_can_override_submodule_bundle_lookup():
    class BundleLeaf(Module):
        def __init__(self):
            super().__init__("BundleLeafAlt")
            self.sink = ReadyValid(8, name="sink").prefixed("sink")

    class BundleTop(Module):
        def __init__(self):
            super().__init__("BundleTopAlt")
            self.src = ReadyValid(8, name="src").flip().prefixed("src")
            leaf = BundleLeaf()
            self.instantiate_with_bundles(
                leaf,
                "u_leaf",
                parent_bundles={"path": self.src},
                sub_bundles={"path": leaf.sink},
            )

    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(BundleTop())

    assert ".sink_data(src_data)" in emitted
    assert ".sink_valid(src_valid)" in emitted
    assert ".sink_ready(src_ready)" in emitted


def test_instantiate_with_bundles_auto_discovers_same_named_parent_and_sub_bundles():
    class BundleLeaf(Module):
        def __init__(self):
            super().__init__("BundleLeafAuto")
            self.link = ReadyValid(8, name="link").prefixed("link")

    class BundleTop(Module):
        def __init__(self):
            super().__init__("BundleTopAuto")
            self.link = ReadyValid(8, name="link").flip().prefixed("link")
            leaf = BundleLeaf()
            self.instantiate_with_bundles(leaf, "u_leaf")

    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(BundleTop())

    assert ".link_data(link_data)" in emitted
    assert ".link_valid(link_valid)" in emitted
    assert ".link_ready(link_ready)" in emitted


def test_instantiate_with_bundles_supports_field_include_exclude():
    class BundleLeaf(Module):
        def __init__(self):
            super().__init__("BundleLeafFields")
            self.link = ReadyValid(
                8,
                name="link",
                has_last=True,
                has_keep=True,
                user_width=2,
            ).prefixed("link")

    class BundleTop(Module):
        def __init__(self):
            super().__init__("BundleTopFields")
            self.link = ReadyValid(
                8,
                name="link",
                has_last=True,
                has_keep=True,
                user_width=2,
            ).flip().prefixed("link")
            leaf = BundleLeaf()
            self.instantiate_with_bundles(
                leaf,
                "u_leaf",
                bundle_includes={"link": ("data", "valid", "ready", "last", "user")},
                bundle_excludes={"link": ("user",)},
            )

    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(BundleTop())

    assert ".link_data(link_data)" in emitted
    assert ".link_valid(link_valid)" in emitted
    assert ".link_ready(link_ready)" in emitted
    assert ".link_last(link_last)" in emitted
    assert ".link_keep(" not in emitted
    assert ".link_user(" not in emitted


def test_instantiate_with_bundles_rejects_unknown_bundle_filter_keys():
    class BundleLeaf(Module):
        def __init__(self):
            super().__init__("BundleLeafBadFilter")
            self.link = ReadyValid(8, name="link").prefixed("link")

    class BundleTop(Module):
        def __init__(self):
            super().__init__("BundleTopBadFilter")
            self.link = ReadyValid(8, name="link").flip().prefixed("link")
            leaf = BundleLeaf()
            with pytest.raises(ValueError, match="bundle include/exclude keys"):
                self.instantiate_with_bundles(
                    leaf,
                    "u_leaf",
                    bundle_includes={"missing": ("data",)},
                )

    BundleTop()


def test_ahblite_bundle_exposes_master_slave_semantics_and_port_map():
    slave = AHBLite(32, 32, name="ahb_s")
    master = slave.flip()

    assert master.clock_reset_fields() == ("hclk", "hresetn")
    assert master.master_fields()[0:2] == ("hclk", "hresetn")
    assert master.slave_fields() == ("hrdata", "hready", "hresp")
    assert slave.direction_of("haddr") == "in"
    assert master.direction_of("haddr") == "out"
    mapping = master.transaction_port_map(slave)
    assert mapping["haddr"] is master.haddr
    assert mapping["hwdata"] is master.hwdata
    assert mapping["hready"] is slave.hready
    assert mapping["hrdata"] is slave.hrdata


def test_skid_buffer_lowers_and_preserves_stalled_payload():
    lowered = lower_dsl_module_to_sim(SkidBuffer(16))
    sim = PythonSimulator(lowered.module)

    assert sim.step({"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x12, "in_valid": 1, "out_ready": 0}) == {
        "in_ready": 0,
        "out_data": 0x12,
        "out_valid": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 0}) == {
        "in_ready": 0,
        "out_data": 0x12,
        "out_valid": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 0}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
    }


def test_enum_type_emits_named_localparams_and_lowers_on_runtime():
    class EnumCounter(Module):
        def __init__(self):
            super().__init__("EnumCounter")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.out = Output(2, "out")
            self.phase_t = EnumType.define("phase_t", ("IDLE", "RUN", "DONE"))
            self.phase = Reg(name="phase", enum_type=self.phase_t, init_value=self.phase_t.IDLE)

            @self.comb
            def _comb():
                self.out <<= self.phase

            @self.seq(self.clk, self.rst)
            def _seq():
                with If(self.rst == 1):
                    self.phase <<= self.phase_t.IDLE
                with Else():
                    with Switch(self.phase) as sw:
                        with sw.case(self.phase_t.IDLE):
                            self.phase <<= self.phase_t.RUN
                        with sw.case(self.phase_t.RUN):
                            self.phase <<= self.phase_t.DONE
                        with sw.default():
                            self.phase <<= self.phase_t.IDLE

    module = EnumCounter()
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(module)

    assert "localparam [1:0] PHASE_T_IDLE = 2'd0;" in emitted
    assert "localparam [1:0] PHASE_T_RUN = 2'd1;" in emitted
    assert "reg [1:0] phase = PHASE_T_IDLE; // enum phase_t" in emitted
    assert "PHASE_T_IDLE: begin" in emitted
    assert "phase <= PHASE_T_RUN;" in emitted

    lowered = lower_dsl_module_to_sim(module)
    sim = PythonSimulator(lowered.module)
    assert sim.step({"clk": 0, "rst": 1}) == {"out": 0}
    assert sim.step({"clk": 0, "rst": 0}) == {"out": 1}
    assert sim.step({"clk": 0, "rst": 0}) == {"out": 2}
    assert sim.step({"clk": 0, "rst": 0}) == {"out": 0}


def test_packed_struct_emits_field_layout_comments_and_supports_field_access():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(PackedStructRoundTrip())

    assert "// struct packet_t: opcode[7:4], tag[3:0]" in emitted
    assert "reg [7:0] packet; // struct packet_t: opcode[7:4], tag[3:0]" in emitted
    assert "assign out_opcode = packet[7:4];" in emitted
    assert "assign out_tag = packet[3:0];" in emitted
    assert "packet <= {2{4'd0}};" in emitted


def test_packed_struct_field_access_lowers_and_runs_on_python_runtime():
    lowered = lower_dsl_module_to_sim(PackedStructRoundTrip())
    sim = PythonSimulator(lowered.module)

    assert sim.step({"clk": 0, "rst": 1, "load": 0, "opcode": 0, "tag": 0}) == {
        "out_opcode": 0,
        "out_tag": 0,
        "out_raw": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "load": 1, "opcode": 0xA, "tag": 0x5}) == {
        "out_opcode": 0xA,
        "out_tag": 0x5,
        "out_raw": 0xA5,
    }
    assert sim.step({"clk": 0, "rst": 0, "load": 0, "opcode": 0, "tag": 0}) == {
        "out_opcode": 0xA,
        "out_tag": 0x5,
        "out_raw": 0xA5,
    }


def test_packed_struct_field_access_matches_compiled_simulator(tmp_path):
    python_sim = PythonSimulator(lower_dsl_module_to_sim(PackedStructRoundTrip()).module)
    compiled = build_compiled_simulator_from_dsl(
        PackedStructRoundTrip(),
        build_dir=tmp_path / "packed_struct_roundtrip",
    )
    try:
        python_sim.reset()
        compiled.reset()
        for vector in (
            {"clk": 0, "rst": 1, "load": 0, "opcode": 0, "tag": 0},
            {"clk": 0, "rst": 0, "load": 1, "opcode": 0x3, "tag": 0xC},
            {"clk": 0, "rst": 0, "load": 1, "opcode": 0xF, "tag": 0x1},
            {"clk": 0, "rst": 0, "load": 0, "opcode": 0, "tag": 0},
        ):
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_fsm_emits_enum_state_markers_and_runs_on_lowered_runtime():
    class TrafficTop(Module):
        def __init__(self):
            super().__init__("TrafficTop")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.start = Input(1, "start")
            self.stop = Input(1, "stop")
            fsm = FSM("IDLE", name="traffic")
            fsm.add_output("red", default=1)
            fsm.add_output("green", default=0)

            @fsm.state("IDLE")
            def idle(ctx):
                ctx.red = 1
                ctx.green = 0
                ctx.goto("RUN", when=self.start)

            @fsm.state("RUN")
            def run(ctx):
                ctx.red = 0
                ctx.green = 1
                ctx.goto("IDLE", when=self.stop)

            fsm.build(self.clk, self.rst, parent=self)

    module = TrafficTop()
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(module)

    assert "localparam [0:0] TRAFFIC_STATE_T_IDLE = 1'd0;" in emitted
    assert "localparam [0:0] TRAFFIC_STATE_T_RUN = 1'd1;" in emitted
    assert "reg traffic_state_reg = TRAFFIC_STATE_T_IDLE; // enum traffic_state_t" in emitted
    assert "case (traffic_state_reg)" in emitted
    assert "TRAFFIC_STATE_T_IDLE: begin" in emitted
    assert "traffic_next_state = TRAFFIC_STATE_T_RUN;" in emitted

    lowered = lower_dsl_module_to_sim(module)
    sim = PythonSimulator(lowered.module)
    assert sim.step({"clk": 0, "rst": 1, "start": 0, "stop": 0}) == {"traffic_red": 1, "traffic_green": 0}
    assert sim.step({"clk": 0, "rst": 0, "start": 1, "stop": 0}) == {"traffic_red": 0, "traffic_green": 1}
    assert sim.step({"clk": 0, "rst": 0, "start": 0, "stop": 1}) == {"traffic_red": 1, "traffic_green": 0}


def test_enum_and_struct_metadata_are_deepcopy_safe():
    enum_type = EnumType.define("state_t", ("IDLE", "RUN"))
    struct_type = PackedStructType.define("packet_t", (("opcode", 4), ("tag", 4)))

    assert copy.deepcopy(enum_type) is enum_type
    assert copy.deepcopy(struct_type) is struct_type
    assert copy.deepcopy(ParentFsmChildDatapathTop()).name == "ParentFsmChildDatapathTop"


def test_ready_valid_fifo_lowers_and_handles_backpressure_and_bypass():
    lowered = lower_dsl_module_to_sim(ReadyValidFIFO(width=8, depth=2))
    sim = PythonSimulator(lowered.module)

    assert sim.step({"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
        "level": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x11, "in_valid": 1, "out_ready": 0}) == {
        "in_ready": 1,
        "out_data": 0x11,
        "out_valid": 1,
        "level": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x22, "in_valid": 1, "out_ready": 0}) == {
        "in_ready": 0,
        "out_data": 0x11,
        "out_valid": 1,
        "level": 2,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x33, "in_valid": 1, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0x22,
        "out_valid": 1,
        "level": 2,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0x33,
        "out_valid": 1,
        "level": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
        "level": 0,
    }


def test_ready_valid_register_lowers_and_inserts_one_stage_latency():
    lowered = lower_dsl_module_to_sim(ReadyValidRegister(width=8))
    sim = PythonSimulator(lowered.module)

    assert sim.step({"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x44, "in_valid": 1, "out_ready": 0}) == {
        "in_ready": 0,
        "out_data": 0x44,
        "out_valid": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x55, "in_valid": 1, "out_ready": 0}) == {
        "in_ready": 0,
        "out_data": 0x44,
        "out_valid": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x66, "in_valid": 1, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0x66,
        "out_valid": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
    }


def test_ready_valid_register_hold_payload_preserves_data_on_drain():
    lowered = lower_dsl_module_to_sim(ReadyValidRegister(width=8, hold_payload=True))
    sim = PythonSimulator(lowered.module)

    assert sim.step({"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x44, "in_valid": 1, "out_ready": 0}) == {
        "in_ready": 0,
        "out_data": 0x44,
        "out_valid": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0x44,
        "out_valid": 0,
    }


def test_ready_valid_async_bridge_lowers_and_supports_multiclock_python_and_compiled(tmp_path):
    lowered = lower_dsl_module_to_sim(ReadyValidAsyncBridgeTop())
    assert tuple(domain.name for domain in lowered.module.clock_domains) == ("wr_clk", "rd_clk")

    python_sim = PythonSimulator(lowered.module)
    with build_compiled_simulator_from_dsl(ReadyValidAsyncBridgeTop(), build_dir=tmp_path / "rv_async_bridge") as compiled:
        with pytest.raises(ValueError, match="step_clocks"):
            python_sim.step({"in_data": 0, "in_valid": 0, "out_ready": 0})
        with pytest.raises(ValueError, match="step_clocks"):
            compiled.step({"in_data": 0, "in_valid": 0, "out_ready": 0})

        _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"wr_rst": 1},
            ("wr_clk",),
        )
        _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"rd_rst": 1},
            ("rd_clk",),
        )

        _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"wr_rst": 0, "rd_rst": 0, "in_data": 0x11, "in_valid": 1},
            ("wr_clk",),
        )
        expected = _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"out_ready": 0},
            ("rd_clk",),
        )
        assert expected["out_valid"] == 0
        expected = _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"out_ready": 1},
            ("rd_clk",),
        )
        assert expected["out_valid"] == 1
        assert expected["out_data"] == 0x11
        expected = _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"out_ready": 1},
            ("rd_clk",),
        )
        assert expected["out_valid"] == 0


def test_reqrsp_queue_lowers_and_buffers_requests():
    lowered = lower_dsl_module_to_sim(
        ReqRspQueue(req_width=8, rsp_width=8, depth=2, addr_width=4, write_enable=True, strobe_width=2)
    )
    sim = PythonSimulator(lowered.module)

    assert sim.step(
        {
            "clk": 0,
            "rst": 1,
            "up_addr": 0,
            "up_req": 0,
            "up_write": 0,
            "up_strb": 0,
            "up_req_valid": 0,
            "up_rsp_ready": 1,
            "down_req_ready": 0,
            "down_rsp": 0,
            "down_rsp_valid": 0,
        }
    ) == {
        "up_req_ready": 1,
        "up_rsp": 0,
        "up_rsp_valid": 0,
        "down_addr": 0,
        "down_req": 0,
        "down_req_valid": 0,
        "down_rsp_ready": 1,
        "down_strb": 0,
        "down_write": 0,
        "level": 0,
    }
    assert sim.step(
        {
            "clk": 0,
            "rst": 0,
            "up_addr": 3,
            "up_req": 0x12,
            "up_write": 1,
            "up_strb": 0x3,
            "up_req_valid": 1,
            "up_rsp_ready": 1,
            "down_req_ready": 0,
            "down_rsp": 0x80,
            "down_rsp_valid": 1,
        }
    ) == {
        "up_req_ready": 1,
        "up_rsp": 0x80,
        "up_rsp_valid": 1,
        "down_addr": 3,
        "down_req": 0x12,
        "down_req_valid": 1,
        "down_rsp_ready": 1,
        "down_strb": 0x3,
        "down_write": 1,
        "level": 1,
    }
    assert sim.step(
        {
            "clk": 0,
            "rst": 0,
            "up_addr": 5,
            "up_req": 0x34,
            "up_write": 0,
            "up_strb": 0x1,
            "up_req_valid": 1,
            "up_rsp_ready": 1,
            "down_req_ready": 0,
            "down_rsp": 0,
            "down_rsp_valid": 0,
        }
    ) == {
        "up_req_ready": 0,
        "up_rsp": 0,
        "up_rsp_valid": 0,
        "down_addr": 3,
        "down_req": 0x12,
        "down_req_valid": 1,
        "down_rsp_ready": 1,
        "down_strb": 0x3,
        "down_write": 1,
        "level": 2,
    }
    assert sim.step(
        {
            "clk": 0,
            "rst": 0,
            "up_addr": 7,
            "up_req": 0x56,
            "up_write": 1,
            "up_strb": 0x2,
            "up_req_valid": 1,
            "up_rsp_ready": 1,
            "down_req_ready": 1,
            "down_rsp": 0,
            "down_rsp_valid": 0,
        }
    ) == {
        "up_req_ready": 1,
        "up_rsp": 0,
        "up_rsp_valid": 0,
        "down_addr": 5,
        "down_req": 0x34,
        "down_req_valid": 1,
        "down_rsp_ready": 1,
        "down_strb": 0x1,
        "down_write": 0,
        "level": 2,
    }


def test_reqrsp_queue_bundled_sideband_lowers_and_buffers_requests():
    lowered = lower_dsl_module_to_sim(
        ReqRspQueue(
            req_width=8,
            rsp_width=8,
            depth=2,
            addr_width=4,
            write_enable=True,
            strobe_width=2,
            bundle_sideband=True,
        )
    )
    sim = PythonSimulator(lowered.module)

    assert sim.step(
        {
            "clk": 0,
            "rst": 1,
            "up_addr": 0,
            "up_req": 0,
            "up_write": 0,
            "up_strb": 0,
            "up_req_valid": 0,
            "up_rsp_ready": 1,
            "down_req_ready": 0,
            "down_rsp": 0,
            "down_rsp_valid": 0,
        }
    ) == {
        "up_req_ready": 1,
        "up_rsp": 0,
        "up_rsp_valid": 0,
        "down_addr": 0,
        "down_req": 0,
        "down_req_valid": 0,
        "down_rsp_ready": 1,
        "down_strb": 0,
        "down_write": 0,
        "level": 0,
    }
    assert sim.step(
        {
            "clk": 0,
            "rst": 0,
            "up_addr": 3,
            "up_req": 0x12,
            "up_write": 1,
            "up_strb": 0x3,
            "up_req_valid": 1,
            "up_rsp_ready": 1,
            "down_req_ready": 0,
            "down_rsp": 0x80,
            "down_rsp_valid": 1,
        }
    ) == {
        "up_req_ready": 1,
        "up_rsp": 0x80,
        "up_rsp_valid": 1,
        "down_addr": 3,
        "down_req": 0x12,
        "down_req_valid": 1,
        "down_rsp_ready": 1,
        "down_strb": 0x3,
        "down_write": 1,
        "level": 1,
    }
    assert sim.step(
        {
            "clk": 0,
            "rst": 0,
            "up_addr": 5,
            "up_req": 0x34,
            "up_write": 0,
            "up_strb": 0x1,
            "up_req_valid": 1,
            "up_rsp_ready": 1,
            "down_req_ready": 0,
            "down_rsp": 0,
            "down_rsp_valid": 0,
        }
    ) == {
        "up_req_ready": 0,
        "up_rsp": 0,
        "up_rsp_valid": 0,
        "down_addr": 3,
        "down_req": 0x12,
        "down_req_valid": 1,
        "down_rsp_ready": 1,
        "down_strb": 0x3,
        "down_write": 1,
        "level": 2,
    }
    assert sim.step(
        {
            "clk": 0,
            "rst": 0,
            "up_addr": 7,
            "up_req": 0x56,
            "up_write": 1,
            "up_strb": 0x2,
            "up_req_valid": 1,
            "up_rsp_ready": 1,
            "down_req_ready": 1,
            "down_rsp": 0,
            "down_rsp_valid": 0,
        }
    ) == {
        "up_req_ready": 1,
        "up_rsp": 0,
        "up_rsp_valid": 0,
        "down_addr": 5,
        "down_req": 0x34,
        "down_req_valid": 1,
        "down_rsp_ready": 1,
        "down_strb": 0x1,
        "down_write": 0,
        "level": 2,
    }


def test_axilite_register_bank_lowers_and_applies_byte_enable_writes(tmp_path):
    lowered = lower_dsl_module_to_sim(AXI4LiteRegisterBank(depth=8))
    sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        AXI4LiteRegisterBank(depth=8),
        build_dir=tmp_path / "axilite_register_bank",
    )
    try:
        vectors = (
            (
                {
                    "clk": 0,
                    "rst": 1,
                    "awaddr": 0,
                    "awvalid": 0,
                    "awprot": 0,
                    "wdata": 0,
                    "wstrb": 0,
                    "wvalid": 0,
                    "bready": 0,
                    "araddr": 0,
                    "arvalid": 0,
                    "arprot": 0,
                    "rready": 0,
                },
                {"awready": 1, "wready": 1, "bresp": 0, "bvalid": 0, "arready": 1, "rdata": 0, "rresp": 0, "rvalid": 0},
            ),
            (
                {
                    "clk": 0,
                    "rst": 0,
                    "awaddr": 0x10,
                    "awvalid": 1,
                    "awprot": 0,
                    "wdata": 0x11223344,
                    "wstrb": 0x5,
                    "wvalid": 1,
                    "bready": 0,
                    "araddr": 0,
                    "arvalid": 0,
                    "arprot": 0,
                    "rready": 0,
                },
                {"awready": 1, "wready": 1, "bresp": 0, "bvalid": 0, "arready": 1, "rdata": 0, "rresp": 0, "rvalid": 0},
            ),
            (
                {
                    "clk": 0,
                    "rst": 0,
                    "awaddr": 0,
                    "awvalid": 0,
                    "awprot": 0,
                    "wdata": 0,
                    "wstrb": 0,
                    "wvalid": 0,
                    "bready": 1,
                    "araddr": 0,
                    "arvalid": 0,
                    "arprot": 0,
                    "rready": 0,
                },
                {"awready": 0, "wready": 0, "bresp": 0, "bvalid": 1, "arready": 1, "rdata": 0, "rresp": 0, "rvalid": 0},
            ),
            (
                {
                    "clk": 0,
                    "rst": 0,
                    "awaddr": 0,
                    "awvalid": 0,
                    "awprot": 0,
                    "wdata": 0,
                    "wstrb": 0,
                    "wvalid": 0,
                    "bready": 0,
                    "araddr": 0x10,
                    "arvalid": 1,
                    "arprot": 0,
                    "rready": 0,
                },
                {"awready": 0, "wready": 0, "bresp": 0, "bvalid": 1, "arready": 1, "rdata": 0, "rresp": 0, "rvalid": 0},
            ),
            (
                {
                    "clk": 0,
                    "rst": 0,
                    "awaddr": 0,
                    "awvalid": 0,
                    "awprot": 0,
                    "wdata": 0,
                    "wstrb": 0,
                    "wvalid": 0,
                    "bready": 0,
                    "araddr": 0,
                    "arvalid": 0,
                    "arprot": 0,
                    "rready": 1,
                },
                {"awready": 0, "wready": 0, "bresp": 0, "bvalid": 1, "arready": 0, "rvalid": 1, "rdata": 0x00220044, "rresp": 0},
            ),
        )
        for inputs, expected in vectors:
            assert sim.step(inputs) == expected
            assert compiled.step(inputs) == expected
    finally:
        compiled.close()


def test_axilite_register_bank_split_control_state_lowers_and_applies_byte_enable_writes(tmp_path):
    lowered = lower_dsl_module_to_sim(AXI4LiteRegisterBank(depth=8, split_control_state=True))
    sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        AXI4LiteRegisterBank(depth=8, split_control_state=True),
        build_dir=tmp_path / "axilite_register_bank_split_control_state",
    )
    try:
        vectors = (
            (
                {
                    "clk": 0,
                    "rst": 1,
                    "awaddr": 0,
                    "awvalid": 0,
                    "awprot": 0,
                    "wdata": 0,
                    "wstrb": 0,
                    "wvalid": 0,
                    "bready": 0,
                    "araddr": 0,
                    "arvalid": 0,
                    "arprot": 0,
                    "rready": 0,
                },
                {"awready": 1, "wready": 1, "bresp": 0, "bvalid": 0, "arready": 1, "rdata": 0, "rresp": 0, "rvalid": 0},
            ),
            (
                {
                    "clk": 0,
                    "rst": 0,
                    "awaddr": 0x10,
                    "awvalid": 1,
                    "awprot": 0,
                    "wdata": 0x11223344,
                    "wstrb": 0x5,
                    "wvalid": 1,
                    "bready": 0,
                    "araddr": 0,
                    "arvalid": 0,
                    "arprot": 0,
                    "rready": 0,
                },
                {"awready": 1, "wready": 1, "bresp": 0, "bvalid": 0, "arready": 1, "rdata": 0, "rresp": 0, "rvalid": 0},
            ),
            (
                {
                    "clk": 0,
                    "rst": 0,
                    "awaddr": 0,
                    "awvalid": 0,
                    "awprot": 0,
                    "wdata": 0,
                    "wstrb": 0,
                    "wvalid": 0,
                    "bready": 1,
                    "araddr": 0,
                    "arvalid": 0,
                    "arprot": 0,
                    "rready": 0,
                },
                {"awready": 0, "wready": 0, "bresp": 0, "bvalid": 1, "arready": 1, "rdata": 0, "rresp": 0, "rvalid": 0},
            ),
            (
                {
                    "clk": 0,
                    "rst": 0,
                    "awaddr": 0,
                    "awvalid": 0,
                    "awprot": 0,
                    "wdata": 0,
                    "wstrb": 0,
                    "wvalid": 0,
                    "bready": 0,
                    "araddr": 0x10,
                    "arvalid": 1,
                    "arprot": 0,
                    "rready": 0,
                },
                {"awready": 0, "wready": 0, "bresp": 0, "bvalid": 1, "arready": 1, "rdata": 0, "rresp": 0, "rvalid": 0},
            ),
            (
                {
                    "clk": 0,
                    "rst": 0,
                    "awaddr": 0,
                    "awvalid": 0,
                    "awprot": 0,
                    "wdata": 0,
                    "wstrb": 0,
                    "wvalid": 0,
                    "bready": 0,
                    "araddr": 0,
                    "arvalid": 0,
                    "arprot": 0,
                    "rready": 1,
                },
                {"awready": 0, "wready": 0, "bresp": 0, "bvalid": 1, "arready": 0, "rdata": 0x00220044, "rresp": 0, "rvalid": 1},
            ),
            (
                {
                    "clk": 0,
                    "rst": 0,
                    "awaddr": 0,
                    "awvalid": 0,
                    "awprot": 0,
                    "wdata": 0,
                    "wstrb": 0,
                    "wvalid": 0,
                    "bready": 0,
                    "araddr": 0,
                    "arvalid": 0,
                    "arprot": 0,
                    "rready": 0,
                },
                {"awready": 0, "wready": 0, "bresp": 0, "bvalid": 1, "arready": 0, "rdata": 0x00220044, "rresp": 0, "rvalid": 1},
            ),
        )
        for inputs, expected in vectors:
            observed_python = sim.step(inputs)
            observed_compiled = compiled.step(inputs)
            assert observed_python == expected
            assert observed_compiled == expected
    finally:
        compiled.close()

    emitted = VerilogEmitter(use_sv_always=True).emit(AXI4LiteRegisterBank(depth=8))
    assert "module AXI4LiteRegisterBank" in emitted
    assert "regmem" in emitted


def test_apb_register_bank_lowers_and_applies_byte_enable_writes(tmp_path):
    lowered = lower_dsl_module_to_sim(APBRegisterBank(depth=8))
    sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        APBRegisterBank(depth=8),
        build_dir=tmp_path / "apb_register_bank",
    )
    try:
        vectors = (
            (
                {
                    "pclk": 0,
                    "presetn": 0,
                    "psel": 0,
                    "penable": 0,
                    "pwrite": 0,
                    "paddr": 0,
                    "pwdata": 0,
                    "pprot": 0,
                    "pstrb": 0,
                },
                {"prdata": 0, "pready": 0, "pslverr": 0},
            ),
            (
                {
                    "pclk": 0,
                    "presetn": 1,
                    "psel": 0,
                    "penable": 0,
                    "pwrite": 0,
                    "paddr": 0,
                    "pwdata": 0,
                    "pprot": 0,
                    "pstrb": 0,
                },
                {"prdata": 0, "pready": 0, "pslverr": 0},
            ),
            (
                {
                    "pclk": 0,
                    "presetn": 1,
                    "psel": 1,
                    "penable": 0,
                    "pwrite": 1,
                    "paddr": 0x10,
                    "pwdata": 0xA5A55A5A,
                    "pprot": 0,
                    "pstrb": 0x5,
                },
                {"prdata": 0, "pready": 0, "pslverr": 0},
            ),
            (
                {
                    "pclk": 0,
                    "presetn": 1,
                    "psel": 1,
                    "penable": 1,
                    "pwrite": 1,
                    "paddr": 0x10,
                    "pwdata": 0xA5A55A5A,
                    "pprot": 0,
                    "pstrb": 0x5,
                },
                {"prdata": 0, "pready": 1, "pslverr": 0},
            ),
            (
                {
                    "pclk": 0,
                    "presetn": 1,
                    "psel": 1,
                    "penable": 0,
                    "pwrite": 0,
                    "paddr": 0x10,
                    "pwdata": 0,
                    "pprot": 0,
                    "pstrb": 0xF,
                },
                {"prdata": 0, "pready": 0, "pslverr": 0},
            ),
            (
                {
                    "pclk": 0,
                    "presetn": 1,
                    "psel": 1,
                    "penable": 1,
                    "pwrite": 0,
                    "paddr": 0x10,
                    "pwdata": 0,
                    "pprot": 0,
                    "pstrb": 0xF,
                },
                {"prdata": 0x00A5005A, "pready": 1, "pslverr": 0},
            ),
        )
        for inputs, expected in vectors:
            assert sim.step(inputs) == expected
            assert compiled.step(inputs) == expected
    finally:
        compiled.close()

    emitted = VerilogEmitter(use_sv_always=True).emit(APBRegisterBank(depth=8))
    assert "module APBRegisterBank" in emitted
    assert "regmem" in emitted


def test_wishbone_register_bank_lowers_and_applies_byte_enable_writes(tmp_path):
    lowered = lower_dsl_module_to_sim(WishboneRegisterBank(depth=8))
    sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        WishboneRegisterBank(depth=8),
        build_dir=tmp_path / "wishbone_register_bank",
    )
    try:
        vectors = (
            (
                {
                    "clk_i": 0,
                    "rst_i": 1,
                    "adr_i": 0,
                    "dat_i": 0,
                    "we_i": 0,
                    "sel_i": 0,
                    "stb_i": 0,
                    "cyc_i": 0,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 0, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0x10,
                    "dat_i": 0xA5A55A5A,
                    "we_i": 1,
                    "sel_i": 0x5,
                    "stb_i": 1,
                    "cyc_i": 1,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 0, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0x10,
                    "dat_i": 0xA5A55A5A,
                    "we_i": 1,
                    "sel_i": 0x5,
                    "stb_i": 1,
                    "cyc_i": 1,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 1, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0,
                    "dat_i": 0,
                    "we_i": 0,
                    "sel_i": 0,
                    "stb_i": 0,
                    "cyc_i": 0,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 0, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0x10,
                    "dat_i": 0,
                    "we_i": 0,
                    "sel_i": 0xF,
                    "stb_i": 1,
                    "cyc_i": 1,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 0, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0x10,
                    "dat_i": 0,
                    "we_i": 0,
                    "sel_i": 0xF,
                    "stb_i": 1,
                    "cyc_i": 1,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0x00A5005A, "ack_o": 1, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0,
                    "dat_i": 0,
                    "we_i": 0,
                    "sel_i": 0,
                    "stb_i": 0,
                    "cyc_i": 0,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 0, "err_o": 0, "rty_o": 0},
            ),
        )
        for inputs, expected in vectors:
            assert sim.step(inputs) == expected
            assert compiled.step(inputs) == expected
    finally:
        compiled.close()

    emitted = VerilogEmitter(use_sv_always=True).emit(WishboneRegisterBank(depth=8))
    assert "module WishboneRegisterBank" in emitted
    assert "wbmem" in emitted


def test_wishbone_register_bank_split_control_state_lowers_and_applies_byte_enable_writes(tmp_path):
    lowered = lower_dsl_module_to_sim(WishboneRegisterBank(depth=8, split_control_state=True))
    sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        WishboneRegisterBank(depth=8, split_control_state=True),
        build_dir=tmp_path / "wishbone_register_bank_split_control_state",
    )
    try:
        vectors = (
            (
                {
                    "clk_i": 0,
                    "rst_i": 1,
                    "adr_i": 0,
                    "dat_i": 0,
                    "we_i": 0,
                    "sel_i": 0,
                    "stb_i": 0,
                    "cyc_i": 0,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 0, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0x10,
                    "dat_i": 0xA5A55A5A,
                    "we_i": 1,
                    "sel_i": 0x5,
                    "stb_i": 1,
                    "cyc_i": 1,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 0, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0x10,
                    "dat_i": 0xA5A55A5A,
                    "we_i": 1,
                    "sel_i": 0x5,
                    "stb_i": 1,
                    "cyc_i": 1,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 1, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0,
                    "dat_i": 0,
                    "we_i": 0,
                    "sel_i": 0,
                    "stb_i": 0,
                    "cyc_i": 0,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 0, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0x10,
                    "dat_i": 0,
                    "we_i": 0,
                    "sel_i": 0xF,
                    "stb_i": 1,
                    "cyc_i": 1,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0, "ack_o": 0, "err_o": 0, "rty_o": 0},
            ),
            (
                {
                    "clk_i": 0,
                    "rst_i": 0,
                    "adr_i": 0x10,
                    "dat_i": 0,
                    "we_i": 0,
                    "sel_i": 0xF,
                    "stb_i": 1,
                    "cyc_i": 1,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                {"dat_o": 0x00A5005A, "ack_o": 1, "err_o": 0, "rty_o": 0},
            ),
        )
        for inputs, expected in vectors:
            assert sim.step(inputs) == expected
            assert compiled.step(inputs) == expected
    finally:
        compiled.close()

    emitted = VerilogEmitter(use_sv_always=True).emit(WishboneRegisterBank(depth=8, split_control_state=True))
    assert "module WishboneRegisterBank" in emitted
    assert "capture_fire" in emitted


def test_dsl_memory_init_data_emits_masked_literals():
    text = VerilogEmitter().emit(InitDataMem())

    assert "mem[0] = 8'hff;" in text
    assert "mem[1] = 8'd3;" in text
    assert "mem[2] = 8'd85;" in text
    assert "mem[3] = 8'h80;" in text


def test_dsl_init_data_reaches_lowered_runtime():
    lowered = lower_dsl_module_to_sim(InitDataMem())
    sim = PythonSimulator(lowered.module)

    assert lowered.module.memories[0].init == (0xFF, 0x03, 0x55, 0x80)
    assert sim.step({"addr": 0}) == {"dout": 0xFF}
    assert sim.step({"addr": 1}) == {"dout": 0x03}


def test_dsl_init_file_reaches_lowered_runtime(tmp_path):
    init_file = tmp_path / "mem.hex"
    init_file.write_text("0b\n16\n21\n2c\n")

    class InitFileMem(Module):
        def __init__(self):
            super().__init__("InitFileMem")
            self.addr = Input(2, "addr")
            self.dout = Output(8, "dout")
            self.mem = self.add_memory(Memory(8, 4, "mem", init_file=str(init_file)))

            @self.comb
            def _comb():
                self.dout <<= self.mem[self.addr]

    lowered = lower_dsl_module_to_sim(InitFileMem())
    sim = PythonSimulator(lowered.module)

    assert lowered.module.memories[0].init == (0x0B, 0x16, 0x21, 0x2C)
    assert sim.step({"addr": 0}) == {"dout": 0x0B}
    assert sim.step({"addr": 3}) == {"dout": 0x2C}


def test_dsl_runs_on_lowered_python_runtime():
    sim = PythonSimulator(lower_dsl_module_to_sim(Accum()).module)
    sim.reset()
    assert sim.step({"clk": 0, "rst": 1, "inp": 0}) == {"out": 0}
    assert sim.step({"clk": 0, "rst": 0, "inp": 5}) == {"out": 5}
    assert sim.step({"clk": 0, "rst": 0, "inp": 2}) == {"out": 7}


def test_dsl_ast_simulation_surfaces_keep_only_top_level_compat_wrapper():
    import rtlgen
    import rtlgen.dsl as dsl_mod

    assert not hasattr(dsl_mod, "Simulator")
    assert not hasattr(dsl_mod, "DSLSimValidator")
    assert rtlgen.Simulator is importlib.import_module("rtlgen.dsl.sim").Simulator

    sim = rtlgen.Simulator(Accum())
    sim.reset()
    sim.poke("rst", 1)
    sim.poke("inp", 0)
    assert sim.step() == {"out": 0}
    sim.poke("rst", 0)
    sim.poke("inp", 5)
    assert sim.step() == {"out": 5}
    assert sim.peek("out") == 5
    assert sim.peek("inp") == 5

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("rtlgen.dsl.sim_jit")

    sim_mod = importlib.import_module("rtlgen.dsl.sim")
    with pytest.raises(RuntimeError, match="SimValue is not available"):
        sim_mod.SimValue(0)

    dsl_sim_mod = importlib.import_module("rtlgen.dsl.dsl_sim")
    with pytest.raises(DslSimulationRemovedError):
        dsl_sim_mod.DSLSimValidator(modules=[("Accum", Accum)])


def test_dsl_lowers_to_sim_module():
    lowered = lower_dsl_module_to_sim(Accum())

    assert lowered.module.name == "Accum"
    assert lowered.module.outputs == ("out",)
    assert lowered.module.outputs_post_state is True
    assert lowered.report.assignment_count >= 2


def test_dsl_compiled_simulator_matches_lowered_python_step_semantics(tmp_path):
    python_sim = PythonSimulator(lower_dsl_module_to_sim(Accum()).module)
    compiled = build_compiled_simulator_from_dsl(Accum(), build_dir=tmp_path)
    try:
        python_sim.reset()
        compiled.reset()

        vectors = (
            {"clk": 0, "rst": 1, "inp": 0},
            {"clk": 0, "rst": 0, "inp": 5},
            {"clk": 0, "rst": 0, "inp": 2},
            {"clk": 0, "rst": 1, "inp": 9},
            {"clk": 0, "rst": 0, "inp": 4},
        )
        for vector in vectors:
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_dsl_compiled_simulator_supports_bit_assignment(tmp_path):
    python_sim = PythonSimulator(lower_dsl_module_to_sim(BitUpdate()).module)
    compiled = build_compiled_simulator_from_dsl(BitUpdate(), build_dir=tmp_path)
    try:
        python_sim.reset()
        compiled.reset()
        for vector in (
            {"clk": 0, "rst": 1, "flag": 0},
            {"clk": 0, "rst": 0, "flag": 1},
            {"clk": 0, "rst": 0, "flag": 0},
        ):
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_dsl_compiled_simulator_supports_slice_assignment(tmp_path):
    python_sim = PythonSimulator(lower_dsl_module_to_sim(SliceUpdate()).module)
    compiled = build_compiled_simulator_from_dsl(SliceUpdate(), build_dir=tmp_path)
    try:
        python_sim.reset()
        compiled.reset()
        for vector in (
            {"clk": 0, "rst": 1, "nibble": 0},
            {"clk": 0, "rst": 0, "nibble": 5},
            {"clk": 0, "rst": 0, "nibble": 9},
        ):
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_dsl_compiled_simulator_supports_dynamic_partselect(tmp_path):
    python_sim = PythonSimulator(lower_dsl_module_to_sim(DynamicPartSelectUpdate()).module)
    compiled = build_compiled_simulator_from_dsl(
        DynamicPartSelectUpdate(),
        build_dir=tmp_path / "dynamic_partselect",
    )
    try:
        python_sim.reset()
        compiled.reset()
        for vector in (
            {"clk": 0, "rst": 1, "we": 0, "lane": 0, "nibble": 0},
            {"clk": 0, "rst": 0, "we": 1, "lane": 0, "nibble": 0xA},
            {"clk": 0, "rst": 0, "we": 1, "lane": 1, "nibble": 0x5},
            {"clk": 0, "rst": 0, "we": 0, "lane": 0, "nibble": 0},
            {"clk": 0, "rst": 0, "we": 0, "lane": 1, "nibble": 0},
        ):
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_dsl_compiled_simulator_supports_dynamic_slice_assign(tmp_path):
    python_sim = PythonSimulator(lower_dsl_module_to_sim(DynamicSliceUpdate()).module)
    compiled = build_compiled_simulator_from_dsl(
        DynamicSliceUpdate(),
        build_dir=tmp_path / "dynamic_slice",
    )
    try:
        python_sim.reset()
        compiled.reset()
        for vector in (
            {"clk": 0, "rst": 1, "we": 0, "lo": 0, "width_sel": 0, "data": 0},
            {"clk": 0, "rst": 0, "we": 1, "lo": 1, "width_sel": 0, "data": 0b0011},
            {"clk": 0, "rst": 0, "we": 1, "lo": 4, "width_sel": 1, "data": 0b1010},
            {"clk": 0, "rst": 0, "we": 1, "lo": 0, "width_sel": 1, "data": 0b0101},
        ):
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_dsl_lowering_applies_initial_block_state_and_array_values(tmp_path):
    lowered = lower_dsl_module_to_sim(InitBlockState())
    sim = PythonSimulator(lowered.module)

    signal_map = lowered.module.signal_map()
    memory_map = lowered.module.memory_map()
    assert signal_map["acc"].init == 0xA5
    assert memory_map["rf"].init == (1, 7, 9, 0)

    compiled = build_compiled_simulator_from_dsl(
        InitBlockState(),
        build_dir=tmp_path / "initial_block",
    )
    try:
        expected = {
            0: {"out": 0xA5 + 1},
            1: {"out": 0xA5 + 7},
            2: {"out": 0xA5 + 9},
            3: {"out": 0xA5},
        }
        for addr, observed in expected.items():
            assert sim.step({"addr": addr}) == observed
            compiled.reset()
            assert compiled.step({"addr": addr}) == observed
    finally:
        compiled.close()


def test_dsl_initial_block_supports_dynamic_slice_expression(tmp_path):
    lowered = lower_dsl_module_to_sim(InitBlockDynamicSliceState())
    sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        InitBlockDynamicSliceState(),
        build_dir=tmp_path / "initial_dynamic_slice",
    )
    try:
        for sel in (0, 1, 2):
            expected = sim.step({"sel": sel})
            compiled.reset()
            assert compiled.step({"sel": sel}) == expected
    finally:
        compiled.close()


def test_dsl_latch_blocks_round_trip_to_lowered_simulator_and_verilog(tmp_path):
    module = LatchPass()
    assert len(module._latch_blocks) == 1
    assert len(module._comb_blocks) == 1

    lowered = lower_dsl_module_to_sim(module)
    assert any(assignment.phase == "latch" for assignment in lowered.module.assignments)

    sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        LatchPass(),
        build_dir=tmp_path / "latch_pass",
    )
    try:
        vectors = (
            ({"en": 0, "d": 0x12}, {"out": 0x00}),
            ({"en": 1, "d": 0x34}, {"out": 0x34}),
            ({"en": 0, "d": 0x56}, {"out": 0x34}),
            ({"en": 1, "d": 0x78}, {"out": 0x78}),
        )
        for inputs, expected in vectors:
            assert sim.step(inputs) == expected
            assert compiled.step(inputs) == expected
    finally:
        compiled.close()

    emitted = VerilogEmitter(use_sv_always=True).emit(LatchPass())
    assert "always_latch begin" in emitted


def test_dsl_lowering_preserves_slice_width_for_signed_arithmetic():
    class SignedShiftLane(Module):
        def __init__(self):
            super().__init__("SignedShiftLane")
            self.inp = Input(16, "inp")
            self.shamt = Input(4, "shamt")
            self.out = Output(16, "out")

            with self.comb:
                self.out <<= (self.inp[7:0].as_sint() >> self.shamt).as_uint()[7:0]

    lowered = lower_dsl_module_to_sim(SignedShiftLane())
    sim = PythonSimulator(lowered.module)

    observed = sim.step({"inp": 0x0088, "shamt": 1})
    assert observed == {"out": 0x00C4}


def test_dsl_sra_helper_round_trip_to_verilog_and_sim():
    lowered = lower_dsl_module_to_sim(ArithmeticShiftLane())
    sim = PythonSimulator(lowered.module)

    observed = sim.step({"inp": 0x88, "shamt": 2})
    assert observed == {"out": 0xE2}

    emitted = VerilogEmitter().emit(ArithmeticShiftLane())
    assert ">>>" in emitted


def test_dsl_sra_helper_casts_unsigned_lhs_to_signed_intent():
    lowered = lower_dsl_module_to_sim(ArithmeticShiftUnsignedLane())
    sim = PythonSimulator(lowered.module)

    observed = sim.step({"inp": 0x88, "shamt": 2})
    assert observed == {"out": 0xE2}

    emitted = VerilogEmitter().emit(ArithmeticShiftUnsignedLane())
    assert "$signed(inp)" in emitted
    assert ">>>" in emitted


def test_dsl_round_shift_right_helper_handles_negative_intermediates():
    lowered = lower_dsl_module_to_sim(FixedPointRoundShiftLane())
    sim = PythonSimulator(lowered.module)

    observed_neg = sim.step({"inp": ((1 << 16) - 13)})
    observed_neg_tie = sim.step({"inp": ((1 << 16) - 12)})
    observed_pos = sim.step({"inp": 13})
    observed_pos_tie = sim.step({"inp": 12})

    assert observed_neg == {"out": ((-2) & ((1 << 17) - 1))}
    assert observed_neg_tie == {"out": ((-1) & ((1 << 17) - 1))}
    assert observed_pos == {"out": 2}
    assert observed_pos_tie == {"out": 2}

    emitted = VerilogEmitter().emit(FixedPointRoundShiftLane())
    assert ">>>" in emitted
    assert "$signed" in emitted


def test_dsl_lint_flags_plain_signed_right_shift_for_clarity():
    class SignedShiftLintLane(Module):
        def __init__(self):
            super().__init__("SignedShiftLintLane")
            self.inp = Input(16, "inp")
            self.shamt = Input(4, "shamt")
            self.out = Output(16, "out")

            with self.comb:
                self.out <<= (self.inp[7:0].as_sint() >> self.shamt).as_uint()[7:0]

    violations = SignedShiftLintLane().lint(rules=["signed_shift"])

    assert any("SignedShift" in item for item in violations)
    assert any("severity=warning" in item for item in violations)
    assert any("source=" in item for item in violations)
    assert any("object=out" in item for item in violations)
    assert any("suggested_fix=" in item for item in violations)
    assert any("SRA" in item for item in violations)
    assert any(".py:" in item for item in violations)


def test_verilog_linter_flags_signed_shift_intent_and_accepts_sra():
    linter = VerilogLinter(rules=["signed_shift"])

    unsafe_unsigned = """
module SignedShiftVerilogLane (
    input [7:0] inp,
    output [7:0] out
);
    assign out = inp >>> 2'd2;
endmodule
"""
    violations = linter.lint(unsafe_unsigned).issues
    assert any(item.rule == "signed_shift" for item in violations)
    assert any("explicitly signed" in item.message.lower() for item in violations)

    unsafe_signed = """
module SignedShiftVerilogLane2 (
    input signed [7:0] inp,
    output [7:0] out
);
    assign out = inp >> 2'd2;
endmodule
"""
    violations_signed = linter.lint(unsafe_signed).issues
    assert any(item.rule == "signed_shift" for item in violations_signed)
    assert any("signed signal" in item.message.lower() or "signed left operand" in item.message.lower() for item in violations_signed)

    safe = """
module SraVerilogLane (
    input [7:0] inp,
    output [7:0] out
);
    assign out = $signed(inp) >>> 2'd2;
endmodule
"""
    violations_ok = linter.lint(safe).issues
    assert not violations_ok


def test_dsl_emitter_preserves_arithmetic_intent_for_signed_right_shift():
    class SignedShiftEmitLane(Module):
        def __init__(self):
            super().__init__("SignedShiftEmitLane")
            self.inp = Input(16, "inp")
            self.shamt = Input(4, "shamt")
            self.out = Output(16, "out")

            with self.comb:
                self.out <<= (self.inp[7:0].as_sint() >> self.shamt).as_uint()[7:0]

    emitted = VerilogEmitter().emit(SignedShiftEmitLane())

    assert ">>>" in emitted


def test_dsl_lint_flags_nested_signed_unsigned_mix():
    class SignedUnsignedMixLane(Module):
        def __init__(self):
            super().__init__("SignedUnsignedMixLane")
            self.a = Input(8, "a")
            self.b = Input(8, "b")
            self.out = Output(16, "out")

            @self.comb
            def _comb():
                self.out <<= (self.a.as_sint() * self.b).as_uint()

    violations = SignedUnsignedMixLane().lint(rules=["signed_mix"])

    assert any("SignedMix" in item for item in violations)
    assert any("'*'" in item for item in violations)


def test_dsl_lint_flags_signed_unsigned_multiply_with_specific_rule():
    class SignedUnsignedMultiplyLane(Module):
        def __init__(self):
            super().__init__("SignedUnsignedMultiplyLane")
            self.a = Input(8, "a")
            self.b = Input(8, "b")
            self.out = Output(16, "out")

            @self.comb
            def _comb():
                self.out <<= (self.a.as_sint() * self.b).as_uint()

    violations = SignedUnsignedMultiplyLane().lint(rules=["signed_multiply"])

    assert any("SignedMultiply" in item for item in violations)
    assert any("severity=warning" in item for item in violations)
    assert any("source=" in item for item in violations)
    assert any("object=out" in item for item in violations)
    assert any("suggested_fix=" in item for item in violations)
    assert any("multiply intent" in item for item in violations)
    assert any(".py:" in item for item in violations)


def test_dsl_lint_flags_signed_unsigned_compare_with_specific_rule():
    class SignedUnsignedCompareLane(Module):
        def __init__(self):
            super().__init__("SignedUnsignedCompareLane")
            self.a = Input(8, "a")
            self.b = Input(8, "b")
            self.out = Output(1, "out")

            @self.comb
            def _comb():
                self.out <<= self.a.as_sint() < self.b

    violations = SignedUnsignedCompareLane().lint(rules=["signed_compare"])

    assert any("SignedCompare" in item for item in violations)
    assert any("severity=warning" in item for item in violations)
    assert any("source=" in item for item in violations)
    assert any("object=out" in item for item in violations)
    assert any("suggested_fix=" in item for item in violations)
    assert any("comparison intent" in item for item in violations)
    assert any(".py:" in item for item in violations)


def test_verilog_linter_flags_signed_multiply_and_compare_intent():
    multiply_linter = VerilogLinter(rules=["signed_multiply"])
    compare_linter = VerilogLinter(rules=["signed_compare"])

    unsafe_multiply = """
module SignedMultiplyVerilogLane (
    input [7:0] a,
    input [7:0] b,
    output [15:0] out
);
    assign out = $signed(a) * b;
endmodule
"""
    multiply_violations = multiply_linter.lint(unsafe_multiply).issues
    assert any(item.rule == "signed_multiply" for item in multiply_violations)
    assert any("multiply intent explicit" in item.message.lower() for item in multiply_violations)

    safe_multiply = """
module SignedMultiplyVerilogLaneSafe (
    input [7:0] a,
    input [7:0] b,
    output [15:0] out
);
    assign out = $signed(a) * $signed(b);
endmodule
"""
    assert not multiply_linter.lint(safe_multiply).issues

    unsafe_compare = """
module SignedCompareVerilogLane (
    input [7:0] a,
    input [7:0] b,
    output out
);
    assign out = $signed(a) < b;
endmodule
"""
    compare_violations = compare_linter.lint(unsafe_compare).issues
    assert any(item.rule == "signed_compare" for item in compare_violations)
    assert any("intent explicit" in item.message.lower() for item in compare_violations)

    safe_compare = """
module SignedCompareVerilogLaneSafe (
    input [7:0] a,
    input [7:0] b,
    output out
);
    assign out = $signed(a) < $signed(b);
endmodule
"""
    assert not compare_linter.lint(safe_compare).issues


def test_dsl_round_shift_right_helper_matches_compiled_simulator(tmp_path):
    lowered = lower_dsl_module_to_sim(FixedPointRoundShiftLane())
    py_sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        FixedPointRoundShiftLane(),
        build_dir=tmp_path / "round_shift_right",
    )

    try:
        for raw_inp, expected in (
            (((1 << 16) - 13), ((-2) & ((1 << 17) - 1))),
            (((1 << 16) - 12), ((-1) & ((1 << 17) - 1))),
            (13, 2),
            (12, 2),
        ):
            inputs = {"inp": raw_inp}
            assert py_sim.step(inputs) == {"out": expected}
            assert compiled.step(inputs) == {"out": expected}
    finally:
        compiled.close()


def test_dsl_round_shift_level_shift_and_clip_matches_compiled_simulator(tmp_path):
    lowered = lower_dsl_module_to_sim(FixedPointRoundClipLane())
    py_sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        FixedPointRoundClipLane(),
        build_dir=tmp_path / "round_shift_clip",
    )

    try:
        for signed_inp, expected in (
            (-4096, 0),      # rounded=-256, +128 -> negative, clip low
            (-2048, 0),      # rounded=-128, +128 -> exact low edge
            (-1152, 56),     # rounded=-72, +128 -> in-range negative intermediate
            (0, 128),        # JPEG-style neutral level shift
            (2032, 255),     # rounded=127, +128 -> high edge
            (4096, 255),     # rounded=256, +128 -> clip high
        ):
            raw_inp = signed_inp & ((1 << 24) - 1)
            expected_outputs = {"out": expected}
            assert py_sim.step({"inp": raw_inp}) == expected_outputs
            assert compiled.step({"inp": raw_inp}) == expected_outputs
    finally:
        compiled.close()

    emitted = VerilogEmitter().emit(FixedPointRoundClipLane())
    assert ">>>" in emitted
    assert "$signed" in emitted


def test_jpeg_idct_signed_level_shift_matches_reference_and_compiled(tmp_path):
    from jpeg_decoder.dsl_modules import COEFF_WIDTH, JpegIdct8x8

    coeffs = np.zeros((8, 8), dtype=np.int16)
    coeffs[0, 0] = 128
    coeffs[0, 1] = 64
    coeffs[1, 0] = -32
    expected = _jpeg_reference_idct2(coeffs)
    block = coeffs.flatten().tolist()

    lowered = lower_dsl_module_to_sim(JpegIdct8x8())
    py_sim = PythonSimulator(lowered.module)
    py_sim.reset()
    py_outputs = _run_jpeg_idct_sim(py_sim, block, COEFF_WIDTH)
    py_pixels = np.array(py_outputs[:64], dtype=np.uint8).reshape(8, 8)

    compiled = build_compiled_simulator_from_dsl(
        JpegIdct8x8(),
        build_dir=tmp_path / "jpeg_idct_signed_level_shift",
    )
    try:
        compiled.reset()
        cpp_outputs = _run_jpeg_idct_sim(compiled, block, COEFF_WIDTH)
    finally:
        compiled.close()
    cpp_pixels = np.array(cpp_outputs[:64], dtype=np.uint8).reshape(8, 8)

    assert np.array_equal(py_pixels, expected)
    assert np.array_equal(cpp_pixels, expected)
    assert py_pixels[0, 7] == 128
    assert cpp_pixels[0, 7] == 128


def test_dsl_lowered_simd16_matches_behavior_model_for_signed_int_ops():
    pytest.importorskip("earphone.modules.simd16.layer_L1_behavior.src.behavior")
    from earphone.modules.simd16.layer_L1_behavior.src.behavior import (
        SIMD_OP_VADD,
        SIMD_OP_VCMP_EQ,
        SIMD_OP_VCMP_LT,
        SIMD_OP_VMUL,
        SIMD_OP_VSRA,
        SIMD_OP_VSUB,
        simd16_int16_functional,
    )

    module = _load_external_module(
        "earphone/modules/simd16/layer_L5_dsl/src/dsl.py",
        "EarphoneSIMD16",
    )
    sim = PythonSimulator(lower_dsl_module_to_sim(module).module)

    vectors = (
        (
            0x000100027FFF80000000FFFF1234ABCD * (1 << 128)
            | 0x11112222333344445555666677778888,
            0x0001000100010001FFFF000100020003 * (1 << 128)
            | 0x00010002000300040005000600070008,
            0x0001,
        ),
        (
            int("55aa" * 16, 16),
            int("0f0f" * 16, 16),
            0xFFFF,
        ),
    )
    ops = (
        SIMD_OP_VADD,
        SIMD_OP_VSUB,
        SIMD_OP_VMUL,
        SIMD_OP_VSRA,
        SIMD_OP_VCMP_EQ,
        SIMD_OP_VCMP_LT,
    )

    for op in ops:
        for a, b, pred in vectors:
            sim.reset()
            observed = sim.step(
                {
                    "clk": 0,
                    "rst_n": 1,
                    "vsrc0": a,
                    "vsrc1": b,
                    "vsrc2": 0,
                    "op": op,
                    "mode": 0,
                    "pred": pred,
                    "start": 1,
                }
            )
            expected = simd16_int16_functional(op, a, b, pred)
            assert observed["done"] == 1
            assert observed["vdst"] == expected


def test_dsl_lowers_memory_storage():
    lowered = lower_dsl_module_to_sim(TinyMem())

    assert tuple(memory.name for memory in lowered.module.memories) == ("mem",)
    assert len(lowered.module.memory_writes) == 1


def test_dsl_lowers_memory_init_data():
    lowered = lower_dsl_module_to_sim(InitDataMem())

    assert tuple(memory.name for memory in lowered.module.memories) == ("mem",)
    assert lowered.module.memories[0].init == (0xFF, 0x03, 0x55, 0x80)


def test_dsl_lowers_memory_read_during_write_policy():
    lowered = lower_dsl_module_to_sim(ReadFirstMem())

    assert tuple(memory.name for memory in lowered.module.memories) == ("mem",)
    assert lowered.module.memories[0].read_during_write == "read_first"
    assert lowered.module.memories[0].read_ports == 1
    assert lowered.module.memories[0].write_ports == 1
    assert lowered.module.memories[0].read_style == "async"
    assert lowered.module.memories[0].read_latency == 0

    python_sim = PythonSimulator(lowered.module)
    assert python_sim.step({"clk": 0, "we": 0, "addr": 2, "din": 0}) == {"dout": 3}
    assert python_sim.step({"clk": 1, "we": 1, "addr": 2, "din": 99}) == {"dout": 3}
    assert python_sim.step({"clk": 0, "we": 0, "addr": 2, "din": 0}) == {"dout": 99}


def test_dsl_lowering_preserves_memory_write_source_location():
    lowered = lower_dsl_module_to_sim(ReadFirstMem())

    assert len(lowered.module.memory_writes) == 1
    write = lowered.module.memory_writes[0]
    assert write.source_file is not None
    assert write.source_file.endswith("test_dsl_import.py")
    assert isinstance(write.source_line, int)
    assert write.source_line > 0


def test_dsl_connectivity_report_exposes_hierarchy_and_signal_memory_relationships():
    module = QueryLeaf()
    hierarchy = module.describe_hierarchy()
    report = module.analyze_connectivity()

    assert isinstance(report, ModuleConnectivityReport)
    assert all(isinstance(node, ModuleInstancePath) for node in hierarchy)
    assert hierarchy == (ModuleInstancePath(path="QueryLeaf", module_name="QueryLeaf", type_name="QueryLeaf", parent_path=None, child_instances=()),)

    assert all(isinstance(driver, SignalDriver) for driver in report.signal_drivers)
    y_drivers = report.drivers_of("y")
    assert any(driver.phase == "comb" for driver in y_drivers)

    assert all(isinstance(writer, StateWriter) for writer in report.state_writers)
    state_writers = report.writers_of("state")
    assert state_writers
    assert all(writer.clock == "clk" for writer in state_writers)
    assert any("a" in writer.source_signals for writer in state_writers)

    assert all(isinstance(access, MemoryAccess) for access in report.memory_accesses)
    mem_accesses = report.accesses_of("mem")
    assert any(access.access == "read" and access.target == "y" for access in mem_accesses)
    assert any(access.access == "write" and "addr" in access.addr_signals for access in mem_accesses)
    assert any(access.access == "write" and "a" in access.value_signals for access in mem_accesses)
    assert any(access.source_file and access.source_file.endswith("test_dsl_import.py") for access in mem_accesses)

    assert all(isinstance(conn, PortConnection) for conn in report.port_connections)
    assert report.port_connections == ()


def test_dsl_hierarchy_summary_tracks_nested_submodules():
    hierarchy = QueryTop().describe_hierarchy()

    assert any(node.path == "QueryTop" for node in hierarchy)
    assert any(node.path == "QueryTop.u_leaf" for node in hierarchy)


def test_dsl_connectivity_report_tracks_implicit_submodule_port_links():
    report = QueryTop().analyze_connectivity()

    assert any(conn.instance == "u_leaf" and conn.port == "a" and conn.direction == "input" for conn in report.port_connections)
    assert any(conn.instance == "u_leaf" and conn.port == "y" and conn.direction == "output" for conn in report.port_connections)


def test_dsl_connectivity_report_tracks_explicit_submodule_port_maps():
    report = ExplicitTop().analyze_connectivity()

    assert any(conn.instance == "u_leaf" and conn.port == "din" and conn.connected_signals == ("a",) for conn in report.port_connections)
    assert any(conn.instance == "u_leaf" and conn.port == "dout" and conn.connected_signals == ("y",) for conn in report.port_connections)


def test_dsl_lowering_supports_implicit_submodule_parent_interconnect():
    lowered = lower_dsl_module_to_sim(QueryTop())
    signal_names = {signal.name for signal in lowered.module.signals}
    assignment_targets = {assignment.target for assignment in lowered.module.assignments}

    assert "u_leaf_state" in signal_names
    assert "u_leaf_mem" in {memory.name for memory in lowered.module.memories}
    assert "u_leaf_y" in assignment_targets
    assert "mid" in assignment_targets
    assert "y" in assignment_targets


def test_dsl_verilog_emitter_preserves_implicit_submodule_parent_interconnect():
    text = VerilogEmitter().emit(QueryTop())

    assert "QueryLeaf u_leaf (" in text
    assert ".clk(clk)" in text
    assert ".rst(rst)" in text
    assert ".a(a)" in text
    assert ".addr(addr)" in text
    assert ".y(u_leaf_y)" in text
    assert "assign mid = u_leaf_y;" in text
    assert "assign y = mid;" in text


def test_dsl_lowering_supports_implicit_array_read_through_submodule():
    lowered = lower_dsl_module_to_sim(ImplicitArrayReadTop())
    signal_names = {signal.name for signal in lowered.module.signals}
    assignment_targets = {assignment.target for assignment in lowered.module.assignments}
    memories = {memory.name for memory in lowered.module.memories}

    assert "u_dout" in signal_names
    assert "u_addr" in signal_names
    assert "u_rf" in memories
    assert "u_dout" in assignment_targets
    assert "out" in assignment_targets


def test_dsl_verilog_emitter_supports_implicit_array_read_through_submodule():
    text = VerilogEmitter().emit(ImplicitArrayReadTop())

    assert "ImplicitArrayReadLeaf u (" in text
    assert ".addr(addr)" in text
    assert ".dout(u_dout)" in text
    assert "assign out = u_dout;" in text


def test_dsl_lowering_supports_implicit_memory_read_through_submodule():
    lowered = lower_dsl_module_to_sim(ImplicitMemoryReadTop())
    signal_names = {signal.name for signal in lowered.module.signals}
    assignment_targets = {assignment.target for assignment in lowered.module.assignments}
    memories = {memory.name for memory in lowered.module.memories}

    assert "u_dout" in signal_names
    assert "u_addr" in signal_names
    assert "u_mem" in memories
    assert "u_dout" in assignment_targets
    assert "out" in assignment_targets


def test_dsl_verilog_emitter_supports_implicit_memory_read_through_submodule():
    text = VerilogEmitter().emit(ImplicitMemoryReadTop())

    assert "ImplicitMemoryReadLeaf u (" in text
    assert ".addr(addr)" in text
    assert ".dout(u_dout)" in text
    assert "assign out = u_dout;" in text


def test_dsl_lowering_supports_child_output_in_parent_expression():
    lowered = lower_dsl_module_to_sim(SignedExprTop())
    signal_map = {signal.name: signal for signal in lowered.module.signals}
    assignments = {assignment.target: assignment for assignment in lowered.module.assignments}
    sim = PythonSimulator(lowered.module)

    assert signal_map["u_a"].signed is True
    assert signal_map["u_y"].signed is True
    assert "u_y" in assignments
    assert "SignalRef(name='u_y')" in repr(assignments["out"].expr)
    assert sim.step({"a": 0x88}) == {"out": 0xE2}


def test_dsl_verilog_emitter_supports_child_output_in_parent_expression():
    text = VerilogEmitter().emit(SignedExprTop())

    assert "SignedExprLeaf u (" in text
    assert ".a($signed(a))" in text
    assert ".y(u_y)" in text
    assert "$signed(u_y)" in text
    assert ">>>" in text


def test_dsl_lowering_supports_three_stage_hierarchical_chain():
    lowered = lower_dsl_module_to_sim(ThreeStageChainTop())
    assignment_targets = {assignment.target for assignment in lowered.module.assignments}
    sim = PythonSimulator(lowered.module)

    assert "u0_dout" in assignment_targets
    assert "u1_dout" in assignment_targets
    assert "u2_dout" in assignment_targets
    assert sim.step({"a": 9}) == {"out": 15}


def test_dsl_verilog_emitter_preserves_three_stage_hierarchical_chain():
    text = VerilogEmitter().emit_design(ThreeStageChainTop())

    assert text.count("module StageAdd") == 1
    assert "StageAdd u0 (" in text
    assert "StageAdd u1 (" in text
    assert "StageAdd u2 (" in text
    assert "assign s0_mid = u0_dout;" in text
    assert "assign s1_mid = u1_dout;" in text
    assert "assign out = u2_dout;" in text


def test_dsl_lowering_supports_three_stage_ready_valid_chain():
    lowered = lower_dsl_module_to_sim(ThreeStageReadyValidChainTop())
    sim = PythonSimulator(lowered.module)

    assert sim.step({"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x11, "in_valid": 1, "out_ready": 0}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x22, "in_valid": 1, "out_ready": 0}) == {
        "in_ready": 1,
        "out_data": 0,
        "out_valid": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x33, "in_valid": 1, "out_ready": 0}) == {
        "in_ready": 0,
        "out_data": 0x11,
        "out_valid": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0x44, "in_valid": 1, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0x22,
        "out_valid": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0x33,
        "out_valid": 1,
    }
    assert sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1}) == {
        "in_ready": 1,
        "out_data": 0x44,
        "out_valid": 1,
    }


def test_dsl_verilog_emitter_preserves_three_stage_ready_valid_chain():
    text = VerilogEmitter(profile=EmitProfile.review()).emit(ThreeStageReadyValidChainTop())

    assert text.count("ReadyValidRegister") == 3
    assert "logic [7:0] link0_data;" in text
    assert "logic link0_valid;" in text
    assert "logic link0_ready;" in text
    assert "logic [7:0] link1_data;" in text
    assert "logic link1_valid;" in text
    assert "logic link1_ready;" in text
    assert "assign in_ready = u0_in_ready;" in text
    assert ".out_ready(out_ready)" in text


def test_three_stage_ready_valid_chain_matches_compiled_simulator(tmp_path):
    python_sim = PythonSimulator(lower_dsl_module_to_sim(ThreeStageReadyValidChainTop()).module)
    compiled = build_compiled_simulator_from_dsl(
        ThreeStageReadyValidChainTop(),
        build_dir=tmp_path / "three_stage_ready_valid_chain",
    )
    try:
        python_sim.reset()
        compiled.reset()
        for vector in _three_stage_ready_valid_vectors():
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_dsl_lowering_supports_parent_fsm_child_datapath():
    lowered = lower_dsl_module_to_sim(ParentFsmChildDatapathTop())
    assignments = {assignment.target for assignment in lowered.module.assignments}
    sim = PythonSimulator(lowered.module)

    assert "ctrl_next_state" in assignments
    assert "ctrl_issue" in assignments
    assert "ctrl_waiting" in assignments
    assert "ctrl_capture" in assignments
    assert sim.step({"clk": 0, "rst": 1, "start": 0, "din": 0}) == {
        "busy": 0,
        "valid": 0,
        "out": 0,
        "ctrl_issue": 0,
        "ctrl_waiting": 0,
        "ctrl_capture": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "start": 1, "din": 5}) == {
        "busy": 1,
        "valid": 0,
        "out": 0,
        "ctrl_issue": 1,
        "ctrl_waiting": 0,
        "ctrl_capture": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "start": 0, "din": 5}) == {
        "busy": 1,
        "valid": 0,
        "out": 13,
        "ctrl_issue": 0,
        "ctrl_waiting": 1,
        "ctrl_capture": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "start": 0, "din": 0}) == {
        "busy": 1,
        "valid": 0,
        "out": 16,
        "ctrl_issue": 0,
        "ctrl_waiting": 1,
        "ctrl_capture": 0,
    }
    assert sim.step({"clk": 0, "rst": 0, "start": 0, "din": 0}) == {
        "busy": 0,
        "valid": 1,
        "out": 16,
        "ctrl_issue": 0,
        "ctrl_waiting": 0,
        "ctrl_capture": 1,
    }


def test_dsl_verilog_emitter_preserves_parent_fsm_child_datapath():
    text = VerilogEmitter().emit(ParentFsmChildDatapathTop())

    assert "localparam [1:0] CTRL_STATE_T_IDLE = 2'd0;" in text
    assert "localparam [1:0] CTRL_STATE_T_ISSUE = 2'd1;" in text
    assert "localparam [1:0] CTRL_STATE_T_WAIT = 2'd2;" in text
    assert "localparam [1:0] CTRL_STATE_T_CAPTURE = 2'd3;" in text
    assert "FsmControlledDatapathLeaf u (" in text
    assert "assign launch = ctrl_issue;" in text
    assert "assign busy = ctrl_issue | ctrl_waiting;" in text
    assert "assign out = child_result;" in text


def test_parent_fsm_child_datapath_matches_compiled_simulator(tmp_path):
    python_sim = PythonSimulator(lower_dsl_module_to_sim(ParentFsmChildDatapathTop()).module)
    compiled = build_compiled_simulator_from_dsl(
        ParentFsmChildDatapathTop(),
        build_dir=tmp_path / "parent_fsm_child_datapath",
    )
    try:
        python_sim.reset()
        compiled.reset()
        for vector in _parent_fsm_child_datapath_vectors():
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_dsl_flatten_preserves_nested_memory_source_location():
    lowered = lower_dsl_module_to_sim(FlattenTop())

    matching = [write for write in lowered.module.memory_writes if write.memory == "u_leaf_mem"]
    assert matching
    write = matching[0]
    assert write.source_file is not None
    assert write.source_file.endswith("test_dsl_import.py")
    assert isinstance(write.source_line, int)
    assert write.source_line > 0


def test_dsl_lowering_supports_sync_read_storage_contract():
    lowered = lower_dsl_module_to_sim(SyncReadDeclaredMem())
    memory = lowered.module.memories[0]

    assert memory.read_style == "async"
    assert memory.read_latency == 0
    assert any(signal.name.startswith("__sync_rd_mem_dout") for signal in lowered.module.signals)
    assert any(
        assignment.phase == "seq" and assignment.target.startswith("__sync_rd_mem_dout")
        for assignment in lowered.module.assignments
    )


def test_dsl_lowering_rejects_multiport_storage_metadata_with_source_location():
    class MultiPortLoweringMem(Module):
        def __init__(self):
            super().__init__("MultiPortLoweringMem")
            self.addr = Input(2, "addr")
            self.dout = Output(8, "dout")
            self.mem = self.add_memory(Memory(8, 4, "mem", read_ports=2))

            @self.comb
            def _comb():
                self.dout <<= self.mem[self.addr]

    with pytest.raises(DslLoweringError) as exc_info:
        lower_dsl_module_to_sim(MultiPortLoweringMem())
    message = str(exc_info.value)
    assert "UnsupportedStorageContract" in message
    assert "severity=error" in message
    assert "source=" in message
    assert "object=memory.mem" in message
    assert "suggested_fix=" in message
    assert "memory 'mem'" in message
    assert "read_ports=2" in message
    assert "read_ports=1, write_ports=1" in message
    assert ".py:" in message


def test_dsl_lowering_supports_byte_enable_storage_contract():
    lowered = lower_dsl_module_to_sim(ByteEnableDeclaredMem())
    memory = lowered.module.memories[0]
    write = lowered.module.memory_writes[0]

    assert memory.byte_enable_granularity == 8
    assert memory.byte_enable_width == 4
    assert write.byte_enable is not None


def test_dsl_memory_write_requires_declared_byte_enable_contract():
    class MissingByteEnableContract(Module):
        def __init__(self):
            super().__init__("MissingByteEnableContract")
            self.clk = Input(1, "clk")
            self.addr = Input(2, "addr")
            self.din = Input(32, "din")
            self.be = Input(4, "be")
            self.mem = self.add_memory(Memory(32, 4, "mem"))

            @self.seq(self.clk)
            def _seq():
                self.mem.write(self.addr, self.din, byte_enable=self.be)

    with pytest.raises(ValueError, match="does not declare byte_enable_granularity"):
        MissingByteEnableContract()


def test_dsl_verilog_emitter_supports_byte_enable_memory_writes():
    text = VerilogEmitter().emit(ByteEnableDeclaredMem())

    assert "if (be[0]) mem[addr][7:0] <=" in text
    assert "if (be[3]) mem[addr][31:24] <=" in text


def test_dsl_verilog_emitter_rejects_sync_read_memory_inference():
    with pytest.raises(DslLoweringError) as exc_info:
        VerilogEmitter().emit(SyncReadDeclaredMem())
    message = str(exc_info.value)
    assert "UnsupportedStorageContract" in message
    assert "severity=error" in message
    assert "source=" in message
    assert "object=memory.mem" in message
    assert "suggested_fix=" in message
    assert "module 'SyncReadDeclaredMem'" in message
    assert "memory 'mem'" in message
    assert "read_style='sync'" in message
    assert "read_latency=1" in message
    assert "read_style='async', read_latency=0" in message
    assert ".py:" in message


def test_dsl_verilog_emitter_rejects_multiport_memory_metadata():
    class MultiPortDeclaredMem(Module):
        def __init__(self):
            super().__init__("MultiPortDeclaredMem")
            self.addr = Input(2, "addr")
            self.dout = Output(8, "dout")
            self.mem = self.add_memory(Memory(8, 4, "mem", read_ports=2))

            @self.comb
            def _comb():
                self.dout <<= self.mem[self.addr]

    with pytest.raises(DslLoweringError) as exc_info:
        VerilogEmitter().emit(MultiPortDeclaredMem())
    message = str(exc_info.value)
    assert "UnsupportedStorageContract" in message
    assert "severity=error" in message
    assert "source=" in message
    assert "object=memory.mem" in message
    assert "suggested_fix=" in message
    assert "module 'MultiPortDeclaredMem'" in message
    assert "memory 'mem'" in message
    assert "read_ports=2" in message
    assert "read_ports=1, write_ports=1" in message
    assert ".py:" in message


def test_dsl_emit_design_preflights_child_storage_contracts():
    class SyncReadTop(Module):
        def __init__(self):
            super().__init__("SyncReadTop")
            self.clk = Input(1, "clk")
            self.addr = Input(2, "addr")
            self.dout = Output(8, "dout")
            self.mid = Wire(8, "mid")
            self.u_leaf = SyncReadDeclaredMem()

            @self.comb
            def _comb():
                self.u_leaf.clk <<= self.clk
                self.u_leaf.addr <<= self.addr
                self.mid <<= self.u_leaf.dout
                self.dout <<= self.mid

    with pytest.raises(DslLoweringError) as exc_info:
        VerilogEmitter().emit_design(SyncReadTop())
    message = str(exc_info.value)
    assert "module 'SyncReadDeclaredMem'" in message
    assert "memory 'mem'" in message


def test_dsl_compiled_simulator_supports_sync_read_storage_contract(tmp_path):
    compiled = build_compiled_simulator_from_dsl(
        SyncReadDeclaredMem(),
        build_dir=tmp_path / "sync_read_mem",
    )
    try:
        assert compiled.step({"addr": 0}) == {"dout": 10}
        assert compiled.step({"addr": 2}) == {"dout": 10}
        assert compiled.step({"addr": 3}) == {"dout": 30}
        assert compiled.step({"addr": 1}) == {"dout": 40}
    finally:
        compiled.close()


def test_dsl_compiled_simulator_supports_byte_enable_memory_writes(tmp_path):
    compiled = build_compiled_simulator_from_dsl(
        ByteEnableDeclaredMem(),
        build_dir=tmp_path / "byte_enable_mem",
    )
    try:
        assert compiled.step({"addr": 1, "din": 0x11223344, "be": 0xF}) == {"dout": 0x11223344}
        assert compiled.step({"addr": 1, "din": 0xAABBCCDD, "be": 0x3}) == {"dout": 0x1122CCDD}
        assert compiled.step({"addr": 1, "din": 0x55667788, "be": 0x8}) == {"dout": 0x5522CCDD}
    finally:
        compiled.close()


def test_dsl_declared_clock_and_reset_domains_round_trip():
    module = DeclaredDomainMailbox()

    assert isinstance(module.wr_domain, ClockDomainSpec)
    assert isinstance(module.rd_domain, ClockDomainSpec)
    assert isinstance(module.wr_reset_dom, ResetDomainSpec)
    assert isinstance(module.rd_reset_dom, ResetDomainSpec)
    assert tuple(domain.name for domain in module.declared_clock_domains) == ("write", "read")
    assert tuple(domain.name for domain in module.declared_reset_domains) == ("wr_reset", "rd_reset")
    assert module.rd_domain.reset_active_low is True
    assert module.rd_domain.reset_async is True

    lowered = lower_dsl_module_to_sim(module)
    assert tuple(domain.name for domain in lowered.module.clock_domains) == ("write", "read")
    assert tuple(domain.clock_signal for domain in lowered.module.clock_domains) == ("wr_clk", "rd_clk")
    assert tuple(domain.aliases for domain in lowered.module.clock_domains) == (("wr_clk",), ("rd_clk",))
    assert tuple(domain.reset_signal for domain in lowered.module.clock_domains) == ("wr_rst", "rd_rst_n")
    assert tuple(domain.reset_active_low for domain in lowered.module.clock_domains) == (False, True)
    assert tuple(domain.reset_async for domain in lowered.module.clock_domains) == (False, True)


def test_dsl_seq_domain_accepts_declared_domain_name():
    lowered = lower_dsl_module_to_sim(DeclaredDomainMailboxByName())

    assert tuple(domain.name for domain in lowered.module.clock_domains) == ("write", "read")
    seq_domains = {
        assignment.target: assignment.clock_domain
        for assignment in lowered.module.assignments
        if assignment.phase == "seq"
    }
    assert seq_domains["wptr"] == "write"
    assert seq_domains["rptr"] == "read"


def test_dsl_seq_domain_accepts_clock_alias_and_canonicalizes_to_declared_domain():
    class DeclaredDomainMailboxByAlias(Module):
        def __init__(self):
            super().__init__("DeclaredDomainMailboxByAlias")
            self.wr_clk = Input(1, "wr_clk")
            self.rd_clk = Input(1, "rd_clk")
            self.wr_rst = Input(1, "wr_rst")
            self.rd_rst_n = Input(1, "rd_rst_n")
            self.wptr = Reg(2, "wptr")
            self.rptr = Reg(2, "rptr")
            self.out = Output(2, "out")

            self.wr_reset_dom = self.reset_domain("wr_reset", self.wr_rst)
            self.rd_reset_dom = self.reset_domain(
                "rd_reset",
                self.rd_rst_n,
                reset_async=True,
                reset_active_low=True,
            )
            self.clock_domain("write", self.wr_clk, self.wr_reset_dom)
            self.clock_domain("read", self.rd_clk, self.rd_reset_dom)

            @self.seq_domain("wr_clk")
            def _wr_seq():
                with If(self.wr_rst == 1):
                    self.wptr <<= 0
                with Else():
                    self.wptr <<= self.wptr + 1

            @self.seq_domain("rd_clk")
            def _rd_seq():
                with If(self.rd_rst_n == 0):
                    self.rptr <<= 0
                with Else():
                    self.rptr <<= self.rptr + 1

            @self.comb
            def _comb():
                self.out <<= self.wptr

    lowered = lower_dsl_module_to_sim(DeclaredDomainMailboxByAlias())

    assert tuple(domain.name for domain in lowered.module.clock_domains) == ("write", "read")
    assert tuple(domain.clock_signal for domain in lowered.module.clock_domains) == ("wr_clk", "rd_clk")
    seq_domains = {
        assignment.target: assignment.clock_domain
        for assignment in lowered.module.assignments
        if assignment.phase == "seq"
    }
    assert seq_domains["wptr"] == "write"
    assert seq_domains["rptr"] == "read"


def test_dsl_named_clock_domains_are_steppable_by_name_and_clock_alias(tmp_path):
    lowered = lower_dsl_module_to_sim(DeclaredDomainMailboxByName())

    assert tuple(domain.name for domain in lowered.module.clock_domains) == ("write", "read")
    assert tuple(domain.aliases for domain in lowered.module.clock_domains) == (("wr_clk",), ("rd_clk",))

    python_sim = PythonSimulator(lowered.module)
    with build_compiled_simulator_from_dsl(
        DeclaredDomainMailboxByName(),
        build_dir=tmp_path / "declared_domain_mailbox_by_name",
    ) as compiled:
        reset_expected = _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"wr_rst": 1},
            ("write",),
        )
        assert reset_expected["dout"] == 0

        _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"rd_rst_n": 0},
            ("rd_clk",),
        )

        push_expected = _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"wr_rst": 0, "rd_rst_n": 1, "wr_en": 1, "din": 0x2A},
            ("wr_clk",),
        )
        assert push_expected["dout"] == 0x2A

        pop_expected = _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"wr_en": 0, "rd_en": 0},
            ("read",),
        )
        assert pop_expected["dout"] == 0x2A


def test_dsl_clock_domain_accepts_declared_reset_domain_name():
    lowered = lower_dsl_module_to_sim(DeclaredDomainMailboxByResetName())

    assert tuple(domain.name for domain in lowered.module.clock_domains) == ("write", "read")
    assert tuple(domain.clock_signal for domain in lowered.module.clock_domains) == ("wr_clk", "rd_clk")
    assert tuple(domain.reset_signal for domain in lowered.module.clock_domains) == ("wr_rst", "rd_rst_n")
    assert tuple(domain.reset_active_low for domain in lowered.module.clock_domains) == (False, True)
    assert tuple(domain.reset_async for domain in lowered.module.clock_domains) == (False, True)


def test_dsl_clock_domain_reuses_matching_declared_reset_domain_for_raw_reset_signal():
    class ReuseDeclaredResetDomain(Module):
        def __init__(self):
            super().__init__("ReuseDeclaredResetDomain")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.out = Output(1, "out")
            self.state = Reg(1, "state")
            self.func_reset = self.reset_domain("func_reset", self.rst)
            self.func_domain = self.clock_domain("func", self.clk, self.rst)

            @self.comb
            def _comb():
                self.out <<= self.state

            @self.seq_domain("func")
            def _seq():
                with If(self.rst == 1):
                    self.state <<= 0
                with Else():
                    self.state <<= 1

    module = ReuseDeclaredResetDomain()
    assert tuple(domain.name for domain in module.declared_reset_domains) == ("func_reset",)
    assert module.func_domain.reset is module.func_reset

    lowered = lower_dsl_module_to_sim(module)
    assert tuple(domain.name for domain in lowered.module.clock_domains) == ("func",)
    assert tuple(domain.clock_signal for domain in lowered.module.clock_domains) == ("clk",)
    assert tuple(domain.reset_signal for domain in lowered.module.clock_domains) == ("rst",)


def test_dsl_reset_domain_rejects_same_signal_with_conflicting_semantics():
    class ConflictingResetDomainSemantics(Module):
        def __init__(self):
            super().__init__("ConflictingResetDomainSemantics")
            self.rst = Input(1, "rst")
            self.reset_domain("sync_rst", self.rst)
            self.reset_domain("async_rst", self.rst, reset_async=True)

    with pytest.raises(
        ValueError,
        match="reset signal 'rst' is already declared by reset domain 'sync_rst'",
    ):
        ConflictingResetDomainSemantics()


def test_dsl_seq_domain_unknown_name_reports_known_domains():
    class MissingSeqDomain(Module):
        def __init__(self):
            super().__init__("MissingSeqDomain")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.clock_domain("func", self.clk, self.rst)

            @self.seq_domain("missing")
            def _seq():
                pass

    with pytest.raises(
        ValueError,
        match=r"Known clock domains: func\. Known clock aliases: clk",
    ):
        MissingSeqDomain()


def test_dsl_clock_domain_unknown_reset_name_reports_known_reset_domains():
    class MissingResetDomain(Module):
        def __init__(self):
            super().__init__("MissingResetDomain")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.reset_domain("func_reset", self.rst)
            self.clock_domain("func", self.clk, "missing_reset")

    with pytest.raises(ValueError, match="Known reset domains: func_reset"):
        MissingResetDomain()


def test_async_fifo_lowers_with_sane_empty_flag_semantics():
    lowered = lower_dsl_module_to_sim(AsyncFIFO(width=8, depth=4))
    sim = PythonSimulator(lowered.module)

    assert sim.step_clocks({"wr_rst": 1}, ("wr_clk",)) == {"dout": 0, "full": 0, "empty": 1}
    assert sim.step_clocks({"rd_rst": 1}, ("rd_clk",)) == {"dout": 0, "full": 0, "empty": 1}
    assert sim.step_clocks({"wr_rst": 0, "rd_rst": 0, "din": 0x11, "wr_en": 1}, ("wr_clk",)) == {
        "dout": 0x11,
        "full": 0,
        "empty": 1,
    }
    assert sim.step_clocks({"rd_en": 0}, ("rd_clk",)) == {"dout": 0x11, "full": 0, "empty": 1}
    assert sim.step_clocks({"rd_en": 1}, ("rd_clk",)) == {"dout": 0x11, "full": 0, "empty": 0}


def test_async_fifo_supports_multiclock_python_and_compiled(tmp_path):
    lowered = lower_dsl_module_to_sim(AsyncFIFO(width=8, depth=4))
    python_sim = PythonSimulator(lowered.module)
    with build_compiled_simulator_from_dsl(AsyncFIFO(width=8, depth=4), build_dir=tmp_path / "async_fifo") as compiled:
        _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"wr_rst": 1},
            ("wr_clk",),
        )
        _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"rd_rst": 1},
            ("rd_clk",),
        )
        push_expected = _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"wr_rst": 0, "rd_rst": 0, "din": 0x11, "wr_en": 1},
            ("wr_clk",),
        )
        assert push_expected == {"dout": 0x11, "full": 0, "empty": 1}
        hold_expected = _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"rd_en": 0},
            ("rd_clk",),
        )
        assert hold_expected == {"dout": 0x11, "full": 0, "empty": 1}
        pop_expected = _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"rd_en": 1},
            ("rd_clk",),
        )
        assert pop_expected == {"dout": 0x11, "full": 0, "empty": 0}


def test_dsl_declared_clock_domain_rejects_conflicting_seq_reset_semantics():
    class ConflictingDeclaredDomain(Module):
        def __init__(self):
            super().__init__("ConflictingDeclaredDomain")
            self.clk = Input(1, "clk")
            self.rst_n = Input(1, "rst_n")
            self.out = Output(8, "out")
            self.state = Reg(8, "state")
            self.func_domain = self.clock_domain(
                "func",
                self.clk,
                self.rst_n,
                reset_async=True,
                reset_active_low=True,
            )

            @self.comb
            def _comb():
                self.out <<= self.state

            @self.seq(self.clk, self.rst_n)
            def _seq():
                with If(self.rst_n == 0):
                    self.state <<= 0
                with Else():
                    self.state <<= self.state + 1

    with pytest.raises(DslLoweringError, match="disagree with declared clock domain"):
        lower_dsl_module_to_sim(ConflictingDeclaredDomain())


def test_dsl_compiled_simulator_supports_memory_and_array_storage(tmp_path):
    for module_type in (TinyMem, TinyRegFile):
        python_sim = PythonSimulator(lower_dsl_module_to_sim(module_type()).module)
        compiled = build_compiled_simulator_from_dsl(module_type(), build_dir=tmp_path / module_type.__name__)
        try:
            python_sim.reset()
            compiled.reset()
            for vector in (
                {"clk": 0, "rst": 0, "we": 0, "addr": 0, "din": 0, "waddr": 0, "wdata": 0, "raddr": 0},
                {"clk": 0, "rst": 0, "we": 1, "addr": 2, "din": 7, "waddr": 2, "wdata": 7, "raddr": 2},
                {"clk": 0, "rst": 0, "we": 0, "addr": 2, "din": 0, "waddr": 2, "wdata": 0, "raddr": 2},
            ):
                _step_python_and_compiled(python_sim, compiled, vector)
        finally:
            compiled.close()


def test_dsl_compiled_simulator_supports_multiple_seq_blocks_and_active_low_expr(tmp_path):
    python_sim = PythonSimulator(lower_dsl_module_to_sim(MultiSeqActiveLow()).module)
    compiled = build_compiled_simulator_from_dsl(MultiSeqActiveLow(), build_dir=tmp_path / "multiseq")
    try:
        python_sim.reset()
        compiled.reset()
        for vector in (
            {"clk": 0, "rst_n": 0, "we": 0, "addr": 0, "din": 0},
            {"clk": 0, "rst_n": 1, "we": 1, "addr": 1, "din": 9},
            {"clk": 0, "rst_n": 1, "we": 0, "addr": 1, "din": 0},
        ):
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_dsl_lowering_supports_multi_clock_modules(tmp_path):
    lowered = lower_dsl_module_to_sim(DualClockMailbox())

    assert tuple(domain.name for domain in lowered.module.clock_domains) == ("wr_clk", "rd_clk")
    assert tuple(domain.reset_signal for domain in lowered.module.clock_domains) == ("wr_rst", "rd_rst")
    seq_domains = {assignment.target: assignment.clock_domain for assignment in lowered.module.assignments if assignment.phase == "seq"}
    assert seq_domains["wptr"] == "wr_clk"
    assert seq_domains["rptr"] == "rd_clk"
    assert {write.clock_domain for write in lowered.module.memory_writes} == {"wr_clk"}

    python_sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(DualClockMailbox(), build_dir=tmp_path / "dual_clock_mailbox")
    try:
        with pytest.raises(ValueError, match="step_clocks"):
            python_sim.step({"wr_rst": 1, "rd_rst": 1})
        with pytest.raises(ValueError, match="step_clocks"):
            compiled.step({"wr_rst": 1, "rd_rst": 1})

        _step_multiclock_python_and_compiled(python_sim, compiled, {"wr_rst": 1}, ("wr_clk",))
        _step_multiclock_python_and_compiled(python_sim, compiled, {"rd_rst": 1}, ("rd_clk",))
        _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"wr_rst": 0, "din": 11, "wr_en": 1},
            ("wr_clk",),
        )
        _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"din": 22, "wr_en": 1},
            ("wr_clk",),
        )
        assert _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"rd_rst": 0, "rd_en": 0},
            ("rd_clk",),
        ) == {"dout": 11}
        assert _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"rd_en": 1},
            ("rd_clk",),
        ) == {"dout": 22}
        assert _step_multiclock_python_and_compiled(
            python_sim,
            compiled,
            {"rd_en": 0},
            ("rd_clk",),
        ) == {"dout": 22}
    finally:
        compiled.close()


def test_dsl_lowering_rejects_conflicting_reset_semantics_on_shared_clock():
    with pytest.raises(DslLoweringError, match="disagree on reset semantics"):
        lower_dsl_module_to_sim(ConflictingClockResetBlocks())


def test_real_sram256k_module_lowers_into_executable_model():
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )

    lowered = lower_dsl_module_to_sim(module)

    assert lowered.module.name == "earphone_sram256k"
    assert len(lowered.module.memories) == 1
    assert lowered.module.memories[0].name == "mem"
    assert len(lowered.module.memory_writes) == 1
    assert lowered.module.outputs == ("prdata", "pready", "pslverr")


def test_real_rv32_module_lowers_into_executable_model():
    module = _load_external_module(
        "earphone/modules/rv32/layer_L5_dsl/src/dsl.py",
        "EarphoneRV32",
    )

    lowered = lower_dsl_module_to_sim(module)

    assert lowered.module.name == "earphone_rv32"
    assert len(lowered.module.memories) == 1
    assert lowered.module.memories[0].name == "rf"
    assert len(lowered.module.memory_writes) == 2
    assert "retire_result" in lowered.module.outputs


def test_real_sram256k_module_compiled_simulator_matches_dsl(tmp_path):
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )
    python_sim = PythonSimulator(lower_dsl_module_to_sim(module).module)
    compiled = build_compiled_simulator_from_dsl(module, build_dir=tmp_path / "sram256k")
    try:
        # Guard against regressing back to per-element unrolled 64K SRAM codegen.
        assert compiled.source_path.stat().st_size < 20_000

        vectors = (
            {
                "clk": 0,
                "rst_n": 0,
                "paddr": 0,
                "pwdata": 0,
                "pwrite": 0,
                "psel": 0,
                "penable": 0,
                "pstrb": 0,
            },
            {
                "clk": 0,
                "rst_n": 1,
                "paddr": 8,
                "pwdata": 0x11223344,
                "pwrite": 1,
                "psel": 1,
                "penable": 1,
                "pstrb": 0b1111,
            },
            {
                "clk": 0,
                "rst_n": 1,
                "paddr": 8,
                "pwdata": 0,
                "pwrite": 0,
                "psel": 1,
                "penable": 1,
                "pstrb": 0,
            },
            {
                "clk": 0,
                "rst_n": 1,
                "paddr": 8,
                "pwdata": 0,
                "pwrite": 0,
                "psel": 1,
                "penable": 1,
                "pstrb": 0,
            },
        )
        for vector in vectors:
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_real_sram256k_module_can_be_lowered_twice_without_mutating_authoring_state():
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )

    first = lower_dsl_module_to_sim(module)
    second = lower_dsl_module_to_sim(module)

    assert first.module.name == "earphone_sram256k"
    assert second.module.name == "earphone_sram256k"
    assert len(second.module.memory_writes) == 1


def test_real_rv32_module_compiled_simulator_matches_lowered_python(tmp_path):
    module = _load_external_module(
        "earphone/modules/rv32/layer_L5_dsl/src/dsl.py",
        "EarphoneRV32",
    )
    python_sim = PythonSimulator(lower_dsl_module_to_sim(module).module)
    compiled = build_compiled_simulator_from_dsl(module, build_dir=tmp_path / "rv32")
    try:
        def addi(rd: int, rs1: int, imm: int) -> int:
            imm12 = imm & 0xFFF
            return (imm12 << 20) | (rs1 << 15) | (0b000 << 12) | (rd << 7) | 0b0010011

        def srai(rd: int, rs1: int, shamt: int) -> int:
            funct7 = 0b0100000
            return (
                (funct7 << 25)
                | ((shamt & 0x1F) << 20)
                | (rs1 << 15)
                | (0b101 << 12)
                | (rd << 7)
                | 0b0010011
            )

        base = {
            "clk": 0,
            "imem_gnt": 1,
            "dmem_rdata": 0,
            "dmem_gnt": 1,
            "dmem_valid": 1,
        }
        vectors = (
            {**base, "rst_n": 0, "imem_rdata": 0},
            {**base, "rst_n": 1, "imem_rdata": addi(1, 0, -1)},
            {**base, "rst_n": 1, "imem_rdata": srai(2, 1, 1)},
            {**base, "rst_n": 1, "imem_rdata": addi(3, 0, 5)},
            {**base, "rst_n": 1, "imem_rdata": 0},
            {**base, "rst_n": 1, "imem_rdata": 0},
            {**base, "rst_n": 1, "imem_rdata": 0},
        )
        for vector in vectors:
            _step_python_and_compiled(python_sim, compiled, vector)
    finally:
        compiled.close()


def test_real_simd16_module_compiled_simulator_matches_python_model(tmp_path):
    pytest.importorskip("earphone.modules.simd16.layer_L1_behavior.src.behavior")
    from earphone.modules.simd16.layer_L1_behavior.src.behavior import (
        SIMD_OP_VADD,
        SIMD_OP_VCMP_LT,
        SIMD_OP_VMUL,
        SIMD_OP_VSRA,
    )

    module = _load_external_module(
        "earphone/modules/simd16/layer_L5_dsl/src/dsl.py",
        "EarphoneSIMD16",
    )
    lowered = lower_dsl_module_to_sim(module).module
    python_sim = PythonSimulator(lowered)
    compiled = build_compiled_simulator_from_dsl(module, build_dir=tmp_path / "simd16")
    try:
        vectors = (
            {
                "clk": 0,
                "rst_n": 1,
                "vsrc0": int("80007fff0001ffff" * 2, 16),
                "vsrc1": int("0001000200030004" * 2, 16),
                "vsrc2": 0,
                "op": SIMD_OP_VADD,
                "mode": 0,
                "pred": 0xFFFF,
                "start": 1,
            },
            {
                "clk": 0,
                "rst_n": 1,
                "vsrc0": int("ff00ff0080007fff" * 2, 16),
                "vsrc1": int("0003000300010001" * 2, 16),
                "vsrc2": 0,
                "op": SIMD_OP_VSRA,
                "mode": 0,
                "pred": 0xFFFF,
                "start": 1,
            },
            {
                "clk": 0,
                "rst_n": 1,
                "vsrc0": int("8000000100020003" * 2, 16),
                "vsrc1": int("0001000200030004" * 2, 16),
                "vsrc2": 0,
                "op": SIMD_OP_VCMP_LT,
                "mode": 0,
                "pred": 0xFFFF,
                "start": 1,
            },
            {
                "clk": 0,
                "rst_n": 1,
                "vsrc0": int("0002000300040005" * 2, 16),
                "vsrc1": int("0003000400050006" * 2, 16),
                "vsrc2": 0,
                "op": SIMD_OP_VMUL,
                "mode": 0,
                "pred": 0xFFFF,
                "start": 1,
            },
        )

        for vector in vectors:
            python_sim.reset()
            compiled.reset()
            assert compiled.step(vector) == python_sim.step(vector)
    finally:
        compiled.close()


def _run_seq_multiply_dut(module_cls, build_subdir, tmp_path):
    """Lower a sequential-multiply DUT and exercise it on both runtimes.

    Returns the (python, compiled) output tuples after the directed run so the
    caller can assert they match and stay non-zero (the historical bug produced
    all-zero multiplier results).
    """
    lowered = lower_dsl_module_to_sim(module_cls())
    python_sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        module_cls(), build_dir=tmp_path / build_subdir
    )
    vectors = (
        {"clk": 0, "rst": 1, "a": 0, "b": 0},
        {"clk": 0, "rst": 0, "a": 3, "b": 5},
        {"clk": 0, "rst": 0, "a": 7, "b": 6},
        {"clk": 0, "rst": 0, "a": 257, "b": 257},
    )
    py_outputs = []
    cpp_outputs = []
    try:
        python_sim.reset()
        compiled.reset()
        for vector in vectors:
            py_outputs.append(python_sim.step(vector))
            cpp_outputs.append(compiled.step(vector))
    finally:
        compiled.close()
    return py_outputs, cpp_outputs


def test_dsl_sequential_multiply_truncates_nonzero(tmp_path):
    py_outputs, cpp_outputs = _run_seq_multiply_dut(
        SeqMulTruncate, "seq_mul_truncate", tmp_path
    )
    assert py_outputs == cpp_outputs
    # 3 * 5 = 15, 7 * 6 = 42 (non-zero, historically regressed to zero)
    assert py_outputs[1] == {"out": 15}
    assert py_outputs[2] == {"out": 42}
    # 257 * 257 = 66049, truncated to 16 bits = 513
    assert py_outputs[3] == {"out": 513}


def test_dsl_sequential_multiply_slice_nonzero(tmp_path):
    py_outputs, cpp_outputs = _run_seq_multiply_dut(
        SeqMulSlice, "seq_mul_slice", tmp_path
    )
    assert py_outputs == cpp_outputs
    assert py_outputs[1] == {"out": 15}
    assert py_outputs[2] == {"out": 42}
    assert py_outputs[3] == {"out": 513}


def test_dsl_sequential_multiply_full_product_register(tmp_path):
    """gpu_sm-style: 32-bit product register, low 16 bits read one cycle later."""
    py_outputs, cpp_outputs = _run_seq_multiply_dut(
        SeqMulProductReg, "seq_mul_product_reg", tmp_path
    )
    assert py_outputs == cpp_outputs
    # prod = a*b captured into 32-bit reg; acc reads previous prod's low 16 bits.
    # cycle1 (a=3,b=5): acc = 0 (previous prod), prod = 15
    assert py_outputs[1] == {"out": 0}
    # cycle2 (a=7,b=6): acc = 15 (previous prod), prod = 42
    assert py_outputs[2] == {"out": 15}
    # cycle3 (a=257,b=257): acc = 42, prod = 66049
    assert py_outputs[3] == {"out": 42}


def test_dsl_seq_partial_update_reads_old_state_value(tmp_path):
    lowered = lower_dsl_module_to_sim(SeqBitUpdateUsesOldState())
    python_sim = PythonSimulator(lowered.module)
    compiled = build_compiled_simulator_from_dsl(
        SeqBitUpdateUsesOldState(),
        build_dir=tmp_path / "seq_bit_update_old_state",
    )
    try:
        assert python_sim.step(
            {"clk": 0, "rst": 1, "flag": 0}
        ) == compiled.step(
            {"clk": 0, "rst": 1, "flag": 0}
        ) == {"out": 0xA0}
        assert python_sim.step(
            {"clk": 0, "rst": 0, "flag": 1}
        ) == compiled.step(
            {"clk": 0, "rst": 0, "flag": 1}
        ) == {"out": 0xA4}
        assert python_sim.step(
            {"clk": 0, "rst": 0, "flag": 0}
        ) == compiled.step(
            {"clk": 0, "rst": 0, "flag": 0}
        ) == {"out": 0xA0}
    finally:
        compiled.close()


class SeqOutputDirectAssign(Module):
    """Anti-pattern: assigns an Output directly inside a seq block."""

    def __init__(self):
        super().__init__("SeqOutputDirectAssign")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.a = Input(8, "a")
        self.out = Output(8, "out")

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.out <<= 0
            with Else():
                self.out <<= self.a


class CombWritesReg(Module):
    def __init__(self):
        super().__init__("CombWritesReg")
        self.a = Input(8, "a")
        self.out = Output(8, "out")
        self.state = Reg(8, "state")

        @self.comb
        def _comb():
            self.state <<= self.a
            self.out <<= self.state


class ChildInternalState(Module):
    def __init__(self):
        super().__init__("ChildInternalState")
        self.inp = Input(8, "inp")
        self.out = Output(8, "out")
        self.hidden = Reg(8, "hidden")

        @self.comb
        def _comb():
            self.out <<= self.hidden


class ParentHierRead(Module):
    def __init__(self):
        super().__init__("ParentHierRead")
        self.out = Output(8, "out")
        self.child = ChildInternalState()

        @self.comb
        def _comb():
            self.out <<= self.child.hidden


def test_dsl_seq_output_assign_error_names_port_and_pattern():
    """Finding #2: the lowering error for an Output in a seq block must name
    the port and recommend the shadow-register pattern."""
    with pytest.raises(DslLoweringError) as exc_info:
        lower_dsl_module_to_sim(SeqOutputDirectAssign())
    message = str(exc_info.value)
    assert "SeqOutputAssign" in message
    assert "Output 'out'" in message
    assert "Reg" in message
    assert "comb" in message


def test_validate_authoring_intent_rejects_comb_reg_assign():
    with pytest.raises(DslLoweringError, match="intent contract"):
        validate_authoring_intent(CombWritesReg())


def test_validate_authoring_intent_rejects_hierarchical_read():
    with pytest.raises(DslLoweringError, match="HierarchicalRead"):
        validate_authoring_intent(ParentHierRead())


def test_validate_authoring_intent_rejects_unknown_submodule_port_binding():
    with pytest.raises(DslLoweringError) as exc_info:
        validate_authoring_intent(InvalidPortTop())
    message = str(exc_info.value)
    assert "UnknownSubmodulePort" in message
    assert "severity=error" in message
    assert "source=" in message
    assert "object=InvalidPortTop.u_leaf.dout_typo" in message
    assert "suggested_fix=" in message
    assert "InvalidPortTop.u_leaf" in message
    assert "dout_typo" in message
    assert "din, dout" in message
    assert ".py:" in message


def test_dsl_flatten_rejects_unknown_submodule_port_binding():
    with pytest.raises(DslLoweringError, match="UnknownSubmodulePort"):
        lower_dsl_module_to_sim(InvalidPortTop())


def test_verilog_emit_rejects_unknown_submodule_port_binding():
    with pytest.raises(DslLoweringError, match="UnknownSubmodulePort"):
        VerilogEmitter().emit(InvalidPortTop())


def test_validate_authoring_intent_rejects_untracked_local_wire():
    class LocalWireScratch(Module):
        def __init__(self):
            super().__init__("LocalWireScratch")
            self.a = Input(8, "a")
            self.out = Output(8, "out")
            scratch = Wire(8, "scratch")

            @self.comb
            def _comb():
                scratch.__ilshift__(self.a)
                self.out <<= scratch

    with pytest.raises(DslLoweringError) as exc_info:
        validate_authoring_intent(LocalWireScratch())
    message = str(exc_info.value)
    assert "UntrackedSignal" in message
    assert "severity=error" in message
    assert "source=" in message
    assert "object=LocalWireScratch.scratch" in message
    assert "suggested_fix=" in message
    assert "self.scratch" in message
    assert ".py:" in message


def test_validate_authoring_intent_rejects_untracked_local_memory():
    class LocalMemoryScratch(Module):
        def __init__(self):
            super().__init__("LocalMemoryScratch")
            self.addr = Input(2, "addr")
            self.out = Output(8, "out")
            scratch = Memory(8, 4, "scratch", init_zero=True)

            @self.comb
            def _comb():
                self.out <<= scratch[self.addr]

    with pytest.raises(DslLoweringError) as exc_info:
        validate_authoring_intent(LocalMemoryScratch())
    message = str(exc_info.value)
    assert "UntrackedMemory" in message
    assert "severity=error" in message
    assert "source=" in message
    assert "object=LocalMemoryScratch.scratch" in message
    assert "suggested_fix=" in message
    assert "self.scratch" in message
    assert ".py:" in message


def test_validate_authoring_intent_rejects_untracked_local_array():
    class LocalArrayScratch(Module):
        def __init__(self):
            super().__init__("LocalArrayScratch")
            self.addr = Input(2, "addr")
            self.out = Output(8, "out")
            scratch = Array(8, 4, "scratch")

            @self.comb
            def _comb():
                self.out <<= scratch[self.addr]

    with pytest.raises(DslLoweringError) as exc_info:
        validate_authoring_intent(LocalArrayScratch())
    message = str(exc_info.value)
    assert "UntrackedArray" in message
    assert "severity=error" in message
    assert "source=" in message
    assert "object=LocalArrayScratch.scratch" in message
    assert "suggested_fix=" in message
    assert "self.scratch" in message
    assert ".py:" in message


def test_validate_authoring_intent_source_maps_untracked_memory_write():
    class LocalMemoryWriteScratch(Module):
        def __init__(self):
            super().__init__("LocalMemoryWriteScratch")
            self.clk = Input(1, "clk")
            self.addr = Input(2, "addr")
            self.data = Input(8, "data")
            scratch = Memory(8, 4, "scratch", init_zero=True)

            @self.seq(self.clk)
            def _seq():
                scratch[self.addr] <<= self.data

    with pytest.raises(DslLoweringError) as exc_info:
        validate_authoring_intent(LocalMemoryWriteScratch())
    message = str(exc_info.value)
    assert "UntrackedMemory" in message
    assert "object=LocalMemoryWriteScratch.scratch" in message
    assert "source=" in message
    assert "test_dsl_import.py:" in message
    assert "adapter.py:" not in message
    assert "self.scratch" in message


def test_validate_authoring_intent_source_maps_untracked_array_write():
    class LocalArrayWriteScratch(Module):
        def __init__(self):
            super().__init__("LocalArrayWriteScratch")
            self.clk = Input(1, "clk")
            self.addr = Input(2, "addr")
            self.data = Input(8, "data")
            scratch = Array(8, 4, "scratch")

            @self.seq(self.clk)
            def _seq():
                scratch[self.addr] <<= self.data

    with pytest.raises(DslLoweringError) as exc_info:
        validate_authoring_intent(LocalArrayWriteScratch())
    message = str(exc_info.value)
    assert "UntrackedArray" in message
    assert "object=LocalArrayWriteScratch.scratch" in message
    assert "source=" in message
    assert "test_dsl_import.py:" in message
    assert "adapter.py:" not in message
    assert "self.scratch" in message


def test_verilog_emit_rejects_authoring_intent_violation():
    with pytest.raises(DslLoweringError, match="CombRegAssign"):
        VerilogEmitter().emit(CombWritesReg())


def test_dsl_seq_wire_assign_error_names_kind():
    """A wire target in a seq block should report its kind, not a bare name."""
    class SeqWireAssign(Module):
        def __init__(self):
            super().__init__("SeqWireAssign")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.a = Input(8, "a")
            self.out = Output(8, "out")
            self.w = Wire(8, "w")

            @self.comb
            def _comb():
                self.out <<= self.w

            @self.seq(self.clk, self.rst)
            def _seq():
                with If(self.rst == 1):
                    self.w <<= 0
                with Else():
                    self.w <<= self.a

    with pytest.raises(DslLoweringError) as exc_info:
        lower_dsl_module_to_sim(SeqWireAssign())
    message = str(exc_info.value)
    assert "wire 'w'" in message


def test_signal_truthiness_is_rejected_with_actionable_message():
    sig = Input(1, "sig")

    with pytest.raises(TypeError, match="does not support Python truthiness"):
        bool(sig)


def test_expr_truthiness_is_rejected_with_actionable_message():
    expr = Input(1, "a") & Input(1, "b")

    with pytest.raises(TypeError, match="does not support Python truthiness"):
        bool(expr)


def test_array_and_proxy_truthiness_are_rejected():
    arr = Array(8, 4, "rf")

    with pytest.raises(TypeError, match="Array does not support Python truthiness"):
        bool(arr)

    with pytest.raises(TypeError, match="ArrayProxy does not support Python truthiness"):
        bool(arr[0])


def test_memproxy_truthiness_is_rejected():
    mem = Memory(8, 4, "mem")

    with pytest.raises(TypeError, match="MemProxy does not support Python truthiness"):
        bool(mem[0])


def test_vector_truthiness_is_rejected():
    from rtlgen.dsl.core import Vector

    vector = Vector(8, 2, "v")
    with pytest.raises(TypeError, match="Vector does not support Python truthiness"):
        bool(vector)


def test_parameter_truthiness_is_rejected():
    width = Parameter(8, "WIDTH")

    with pytest.raises(TypeError, match="Parameter does not support Python truthiness"):
        bool(width)
