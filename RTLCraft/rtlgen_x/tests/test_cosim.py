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
