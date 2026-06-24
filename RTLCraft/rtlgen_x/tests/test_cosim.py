import pytest

from rtlgen_x.dsl import Else, If, Input, Memory, Module, Output, Reg
from rtlgen_x.sim.cosim import (
    CosimUnknownValueError,
    run_dsl_multiclock_rtl_cosim,
    run_dsl_rtl_cosim,
)


class DslCosimAccum(Module):
    def __init__(self):
        super().__init__("dsl_cosim_accum")
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


class DslCosimValidPipe(Module):
    def __init__(self):
        super().__init__("dsl_cosim_valid_pipe")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.in_valid = Input(1, "in_valid")
        self.inp = Input(8, "inp")
        self.out_valid = Output(1, "out_valid")
        self.out = Output(8, "out")
        self.v0 = Reg(1, "v0")
        self.v1 = Reg(1, "v1")
        self.d0 = Reg(8, "d0")
        self.d1 = Reg(8, "d1")

        @self.comb
        def _comb():
            self.out_valid <<= self.v1
            self.out <<= self.d1

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.v0 <<= 0
                self.v1 <<= 0
                self.d0 <<= 0
                self.d1 <<= 0
            with Else():
                self.v0 <<= self.in_valid
                self.v1 <<= self.v0
                with If(self.in_valid == 1):
                    self.d0 <<= self.inp + 1
                with If(self.v0 == 1):
                    self.d1 <<= self.d0


class DslCosimResetBranchValue(Module):
    def __init__(self):
        super().__init__("dsl_cosim_reset_branch_value")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.inp = Input(8, "inp")
        self.out = Output(8, "out")
        self.state = Reg(8, "state")

        @self.comb
        def _comb():
            self.out <<= self.state

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.state <<= 7
            with Else():
                self.state <<= self.inp


class DslCosimByteEnableMem(Module):
    def __init__(self):
        super().__init__("dsl_cosim_byte_enable_mem")
        self.clk = Input(1, "clk")
        self.addr = Input(2, "addr")
        self.din = Input(32, "din")
        self.be = Input(4, "be")
        self.dout = Output(32, "dout")
        self.mem = self.add_memory(Memory(32, 4, "mem", byte_enable_granularity=8))

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.addr]

        @self.seq(self.clk)
        def _seq():
            self.mem.write(self.addr, self.din, byte_enable=self.be)


class DslCosimDualClockMailbox(Module):
    def __init__(self):
        super().__init__("dsl_cosim_dual_clock_mailbox")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.mem = Memory(8, 4, "mem", init_zero=True)
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


class DslCosimDualClockArrayMailbox(Module):
    def __init__(self):
        super().__init__("dsl_cosim_dual_clock_array_mailbox")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        from rtlgen_x.dsl import Array

        self.mem = Array(8, 4, "rf")
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


def test_dsl_rtl_cosim_matches_compiled_simulator(tmp_path):
    report = run_dsl_rtl_cosim(
        DslCosimAccum(),
        (
            {"inp": 5},
            {"inp": 2},
            {"inp": 1},
        ),
        build_dir=tmp_path / "cosim",
    )

    assert report.skipped_reason is None
    assert report.dsl_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.mismatches == ()
    assert report.compiled_trace[-1]["out"] == 8
    assert report.rtl_trace[-1]["out"] == 8


def test_dsl_rtl_cosim_returns_skip_when_tool_missing(monkeypatch):
    import rtlgen_x.sim.cosim as cosim_mod

    def missing_compile(*args, **kwargs):
        raise FileNotFoundError("iverilog")

    monkeypatch.setattr(cosim_mod.rtl_cosim, "_compile_and_run", missing_compile)

    report = run_dsl_rtl_cosim(
        DslCosimAccum(),
        ({"inp": 1},),
    )

    assert report.skipped_reason == "iverilog"
    assert report.dsl_matches_rtl is False
    assert report.compiled_matches_rtl is False


def test_dsl_rtl_cosim_supports_valid_gated_streaming_outputs(tmp_path):
    report = run_dsl_rtl_cosim(
        DslCosimValidPipe(),
        (
            {"in_valid": 1, "inp": 3},
            {"in_valid": 1, "inp": 7},
            {"in_valid": 0, "inp": 0},
        ),
        build_dir=tmp_path / "cosim_valid",
        valid_signal="out_valid",
        flush_cycles=3,
        flush_inputs={"in_valid": 0, "inp": 0},
    )

    assert report.skipped_reason is None
    assert report.dsl_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.mismatches == ()
    assert [step["out"] for step in report.rtl_trace] == [4, 8]
    assert [step["out"] for step in report.compiled_trace] == [4, 8]


def test_dsl_rtl_cosim_preserves_reset_branch_value_not_just_init(tmp_path):
    report = run_dsl_rtl_cosim(
        DslCosimResetBranchValue(),
        (
            {"rst": 1, "inp": 2},
            {"rst": 0, "inp": 9},
            {"rst": 0, "inp": 5},
        ),
        build_dir=tmp_path / "cosim_reset_branch_value",
    )

    assert report.skipped_reason is None
    assert report.dsl_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.mismatches == ()
    assert [step["out"] for step in report.rtl_trace] == [7, 9, 5]
    assert [step["out"] for step in report.compiled_trace] == [7, 9, 5]


def test_dsl_rtl_cosim_supports_byte_enable_memory_writes(tmp_path):
    report = run_dsl_rtl_cosim(
        DslCosimByteEnableMem(),
        (
            {"addr": 1, "din": 0x11223344, "be": 0xF},
            {"addr": 1, "din": 0xAABBCCDD, "be": 0x3},
            {"addr": 1, "din": 0x55667788, "be": 0x8},
        ),
        build_dir=tmp_path / "cosim_byte_enable",
    )

    assert report.skipped_reason is None
    assert report.dsl_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.mismatches == ()
    assert [step["dout"] for step in report.rtl_trace] == [0x11223344, 0x1122CCDD, 0x5522CCDD]


def test_dsl_rtl_cosim_rejects_multi_clock_modules():
    with pytest.raises(ValueError, match="run_dsl_multiclock_rtl_cosim"):
        run_dsl_rtl_cosim(
            DslCosimDualClockMailbox(),
            ({"wr_en": 0, "rd_en": 0},),
        )


def test_dsl_multiclock_rtl_cosim_matches_compiled_and_emitted_rtl(tmp_path):
    report = run_dsl_multiclock_rtl_cosim(
        DslCosimDualClockMailbox(),
        (
            ({"wr_rst": 1, "rd_rst": 1}, ("wr_clk", "rd_clk")),
            ({"wr_rst": 0, "rd_rst": 0, "wr_en": 1, "din": 11}, ("wr_clk",)),
            ({"wr_en": 1, "din": 22}, ("wr_clk",)),
            ({"rd_en": 0}, ("rd_clk",)),
            ({"rd_en": 1}, ("rd_clk",)),
            ({"rd_en": 0}, ("rd_clk",)),
        ),
        build_dir=tmp_path / "multiclk_cosim",
    )

    assert report.skipped_reason is None
    assert report.mode == "multi_clock"
    assert report.dsl_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.mismatches == ()
    assert [step["dout"] for step in report.rtl_trace] == [0, 11, 11, 11, 22, 22]
    assert [step["dout"] for step in report.compiled_trace] == [0, 11, 11, 11, 22, 22]


def test_dsl_multiclock_rtl_cosim_accepts_structured_step_mappings(tmp_path):
    report = run_dsl_multiclock_rtl_cosim(
        DslCosimDualClockMailbox(),
        (
            {
                "inputs": {"wr_rst": 1, "rd_rst": 1},
                "active_domains": {"wr_clk": True, "rd_clk": True},
            },
            {
                "inputs": {"wr_rst": 0, "rd_rst": 0, "wr_en": 1, "din": 11},
                "active_domains": {"wr_clk": True, "rd_clk": False},
            },
            {
                "inputs": {"rd_en": 1},
                "active_domains": {"wr_clk": False, "rd_clk": True},
            },
        ),
        build_dir=tmp_path / "multiclk_cosim_structured",
    )

    assert report.skipped_reason is None
    assert report.dsl_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.mismatches == ()
    assert [step["dout"] for step in report.rtl_trace] == [0, 11, 0]


def test_dsl_multiclock_rtl_cosim_rejects_bad_structured_inputs():
    with pytest.raises(TypeError, match="structured multi-clock cosim vectors must provide an 'inputs' mapping"):
        run_dsl_multiclock_rtl_cosim(
            DslCosimDualClockMailbox(),
            (
                {
                    "inputs": 1,
                    "active_domains": ("wr_clk",),
                },
            ),
        )


def test_dsl_multiclock_rtl_cosim_returns_skip_when_tool_missing(monkeypatch):
    import rtlgen_x.sim.cosim as cosim_mod

    def missing_compile(*args, **kwargs):
        raise FileNotFoundError("iverilog")

    monkeypatch.setattr(cosim_mod.rtl_cosim, "_compile_and_run", missing_compile)

    report = run_dsl_multiclock_rtl_cosim(
        DslCosimDualClockMailbox(),
        (
            ({"wr_rst": 1, "rd_rst": 1}, ("wr_clk", "rd_clk")),
        ),
    )

    assert report.skipped_reason == "iverilog"
    assert report.dsl_matches_rtl is False
    assert report.compiled_matches_rtl is False


def test_dsl_multiclock_rtl_cosim_rejects_direct_clock_drives():
    with pytest.raises(ValueError, match="must not drive managed clock signals directly"):
        run_dsl_multiclock_rtl_cosim(
            DslCosimDualClockMailbox(),
            (
                ({"wr_clk": 1, "wr_rst": 1, "rd_rst": 1}, ("wr_clk", "rd_clk")),
            ),
        )


def test_dsl_multiclock_rtl_cosim_reports_unknown_array_state_clearly(tmp_path):
    with pytest.raises(CosimUnknownValueError, match="emitted RTL trace observed unknown value"):
        run_dsl_multiclock_rtl_cosim(
            DslCosimDualClockArrayMailbox(),
            (
                ({"wr_rst": 1, "rd_rst": 1}, ("wr_clk", "rd_clk")),
                ({"wr_rst": 0, "rd_rst": 0, "wr_en": 1, "din": 11}, ("wr_clk",)),
            ),
            build_dir=tmp_path / "multiclk_array_unknown",
        )
