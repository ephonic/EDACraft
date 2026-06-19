import importlib.util
from pathlib import Path

from rtlgen import Simulator as RtlgenSimulator
from rtlgen_x.dsl import (
    Array,
    DSLSimValidator,
    Else,
    If,
    Input,
    Memory,
    build_compiled_simulator_from_legacy,
    lower_legacy_module_to_sim,
    Module,
    Output,
    Reg,
    Simulator,
    VerilogEmitter,
)


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


def _load_external_module(rel_path: str, class_name: str):
    path = Path(__file__).resolve().parents[2] / rel_path
    spec = importlib.util.spec_from_file_location(f"test_{path.stem}_{class_name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, class_name)()


def _step_legacy_and_compiled(legacy: Simulator, compiled, vector):
    for key, value in vector.items():
        if hasattr(legacy.module, key):
            legacy.set(key, value)
    legacy.step()
    expected = {name: legacy.get_int(name) for name in compiled.output_names}
    compiled_inputs = {name: int(vector.get(name, 0)) for name in compiled.input_names}
    actual = compiled.step(compiled_inputs)
    assert actual == expected


def test_legacy_dsl_emits_verilog():
    text = VerilogEmitter().emit(Accum())

    assert "module Accum" in text
    assert "input [7:0] inp" in text
    assert "output [7:0] out" in text


def test_legacy_dsl_simulates():
    sim = Simulator(Accum())
    sim.set("rst", 1)
    sim.step()
    sim.set("rst", 0)
    sim.set("inp", 5)
    sim.step()
    assert sim.get_int("out") == 5
    sim.set("inp", 2)
    sim.step()
    assert sim.get_int("out") == 7


def test_legacy_dsl_validator_runs(tmp_path):
    validator = DSLSimValidator(modules=[("Accum", Accum)], output_dir=str(tmp_path))
    report = validator.validate_all()

    assert report.total_modules == 1
    assert report.passed_modules == 1


def test_legacy_dsl_lowers_to_sim_module():
    lowered = lower_legacy_module_to_sim(Accum())

    assert lowered.module.name == "Accum"
    assert lowered.module.outputs == ("out",)
    assert lowered.module.outputs_post_state is True
    assert lowered.report.assignment_count >= 2


def test_legacy_dsl_compiled_simulator_matches_legacy_step_semantics(tmp_path):
    legacy = Simulator(Accum())
    compiled = build_compiled_simulator_from_legacy(Accum(), build_dir=tmp_path)
    try:
        legacy.set("rst", 1)
        legacy.step()
        compiled.step({"clk": 0, "rst": 1, "inp": 0})

        vectors = (
            {"clk": 0, "rst": 0, "inp": 5},
            {"clk": 0, "rst": 0, "inp": 2},
            {"clk": 0, "rst": 1, "inp": 9},
            {"clk": 0, "rst": 0, "inp": 4},
        )
        for vector in vectors:
            legacy.set("rst", vector["rst"])
            legacy.set("inp", vector["inp"])
            legacy.step()
            assert compiled.step(vector) == {"out": legacy.get_int("out")}
    finally:
        compiled.close()


def test_legacy_dsl_compiled_simulator_supports_bit_assignment(tmp_path):
    legacy = Simulator(BitUpdate())
    compiled = build_compiled_simulator_from_legacy(BitUpdate(), build_dir=tmp_path)
    try:
        for vector in (
            {"clk": 0, "rst": 1, "flag": 0},
            {"clk": 0, "rst": 0, "flag": 1},
            {"clk": 0, "rst": 0, "flag": 0},
        ):
            legacy.set("rst", vector["rst"])
            legacy.set("flag", vector["flag"])
            legacy.step()
            assert compiled.step(vector) == {"out": legacy.get_int("out")}
    finally:
        compiled.close()


def test_legacy_dsl_compiled_simulator_supports_slice_assignment(tmp_path):
    legacy = Simulator(SliceUpdate())
    compiled = build_compiled_simulator_from_legacy(SliceUpdate(), build_dir=tmp_path)
    try:
        for vector in (
            {"clk": 0, "rst": 1, "nibble": 0},
            {"clk": 0, "rst": 0, "nibble": 5},
            {"clk": 0, "rst": 0, "nibble": 9},
        ):
            legacy.set("rst", vector["rst"])
            legacy.set("nibble", vector["nibble"])
            legacy.step()
            assert compiled.step(vector) == {"out": legacy.get_int("out")}
    finally:
        compiled.close()


def test_legacy_dsl_lowers_memory_storage():
    lowered = lower_legacy_module_to_sim(TinyMem())

    assert tuple(memory.name for memory in lowered.module.memories) == ("mem",)
    assert len(lowered.module.memory_writes) == 1


def test_legacy_dsl_compiled_simulator_supports_memory_and_array_storage(tmp_path):
    for module_type in (TinyMem, TinyRegFile):
        legacy = Simulator(module_type())
        compiled = build_compiled_simulator_from_legacy(module_type(), build_dir=tmp_path / module_type.__name__)
        try:
            for vector in (
                {"clk": 0, "rst": 0, "we": 0, "addr": 0, "din": 0, "waddr": 0, "wdata": 0, "raddr": 0},
                {"clk": 0, "rst": 0, "we": 1, "addr": 2, "din": 7, "waddr": 2, "wdata": 7, "raddr": 2},
                {"clk": 0, "rst": 0, "we": 0, "addr": 2, "din": 0, "waddr": 2, "wdata": 0, "raddr": 2},
            ):
                for key, value in vector.items():
                    if hasattr(legacy.module, key):
                        legacy.set(key, value)
                legacy.step()
                compiled_inputs = {
                    name: value
                    for name, value in vector.items()
                    if name in compiled.input_names
                }
                assert compiled.step(compiled_inputs) == {
                    compiled.output_names[0]: legacy.get_int(compiled.output_names[0])
                }
        finally:
            compiled.close()


def test_legacy_dsl_compiled_simulator_supports_multiple_seq_blocks_and_active_low_expr(tmp_path):
    legacy = Simulator(MultiSeqActiveLow())
    compiled = build_compiled_simulator_from_legacy(MultiSeqActiveLow(), build_dir=tmp_path / "multiseq")
    try:
        for vector in (
            {"clk": 0, "rst_n": 0, "we": 0, "addr": 0, "din": 0},
            {"clk": 0, "rst_n": 1, "we": 1, "addr": 1, "din": 9},
            {"clk": 0, "rst_n": 1, "we": 0, "addr": 1, "din": 0},
        ):
            for key, value in vector.items():
                legacy.set(key, value)
            legacy.step()
            assert compiled.step(vector) == {"out": legacy.get_int("out")}
    finally:
        compiled.close()


def test_real_sram256k_module_lowers_into_executable_model():
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )

    lowered = lower_legacy_module_to_sim(module)

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

    lowered = lower_legacy_module_to_sim(module)

    assert lowered.module.name == "earphone_rv32"
    assert len(lowered.module.memories) == 1
    assert lowered.module.memories[0].name == "rf"
    assert len(lowered.module.memory_writes) == 2
    assert "retire_result" in lowered.module.outputs


def test_real_sram256k_module_compiled_simulator_matches_legacy(tmp_path):
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )
    legacy = RtlgenSimulator(module)
    compiled = build_compiled_simulator_from_legacy(module, build_dir=tmp_path / "sram256k")
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
            _step_legacy_and_compiled(legacy, compiled, vector)
    finally:
        compiled.close()


def test_real_rv32_module_compiled_simulator_matches_legacy(tmp_path):
    module = _load_external_module(
        "earphone/modules/rv32/layer_L5_dsl/src/dsl.py",
        "EarphoneRV32",
    )
    legacy = RtlgenSimulator(module)
    compiled = build_compiled_simulator_from_legacy(module, build_dir=tmp_path / "rv32")
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
            _step_legacy_and_compiled(legacy, compiled, vector)
    finally:
        compiled.close()
