from rtlgen_x.dsl import Else, If, Input, Module, Output, Reg
from rtlgen_x.sim.cosim import run_legacy_rtl_cosim


class LegacyCosimAccum(Module):
    def __init__(self):
        super().__init__("legacy_cosim_accum")
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


class LegacyCosimValidPipe(Module):
    def __init__(self):
        super().__init__("legacy_cosim_valid_pipe")
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


def test_legacy_rtl_cosim_matches_compiled_simulator(tmp_path):
    report = run_legacy_rtl_cosim(
        LegacyCosimAccum(),
        (
            {"inp": 5},
            {"inp": 2},
            {"inp": 1},
        ),
        build_dir=tmp_path / "cosim",
    )

    assert report.skipped_reason is None
    assert report.legacy_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.mismatches == ()
    assert report.compiled_trace[-1]["out"] == 8
    assert report.rtl_trace[-1]["out"] == 8


def test_legacy_rtl_cosim_returns_skip_when_tool_missing(monkeypatch):
    import rtlgen_x.sim.cosim as cosim_mod

    def missing_compile(*args, **kwargs):
        raise FileNotFoundError("iverilog")

    monkeypatch.setattr(cosim_mod.rtl_cosim, "_compile_and_run", missing_compile)

    report = run_legacy_rtl_cosim(
        LegacyCosimAccum(),
        ({"inp": 1},),
    )

    assert report.skipped_reason == "iverilog"
    assert report.legacy_matches_rtl is False
    assert report.compiled_matches_rtl is False


def test_legacy_rtl_cosim_supports_valid_gated_streaming_outputs(tmp_path):
    report = run_legacy_rtl_cosim(
        LegacyCosimValidPipe(),
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
    assert report.legacy_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.mismatches == ()
    assert [step["out"] for step in report.rtl_trace] == [4, 8]
    assert [step["out"] for step in report.compiled_trace] == [4, 8]
