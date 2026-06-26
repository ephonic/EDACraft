from pathlib import Path
import subprocess

import pytest

from rtlgen.dsl import BlackBoxModule, Else, If, Input, Memory, Module, Output, Reg
from rtlgen.sim.cosim import (
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
        from rtlgen.dsl import Array

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


class DslCosimExternalLeaf(BlackBoxModule):
    def __init__(
        self,
        *,
        verilog_source: str = "rtl/cosim_ext_leaf.sv",
        include_dir: str = "rtl/include",
    ):
        super().__init__(
            name="DslCosimExternalLeaf",
            verilog_module_name="cosim_ext_leaf",
            inputs=[("din", 8)],
            outputs=[("dout", 8)],
            external_verilog=True,
            verilog_sources=[verilog_source],
            include_dirs=[include_dir],
            defines={"COSIM_EXT": "1"},
        )


class DslCosimMixedExternalRomTop(Module):
    def __init__(
        self,
        *,
        verilog_source: str = "rtl/cosim_ext_leaf.sv",
        include_dir: str = "rtl/include",
        init_file: str = "roms/cosim.hex",
    ):
        super().__init__("DslCosimMixedExternalRomTop")
        self.addr = Input(2, "addr")
        self.din = Input(8, "din")
        self.out = Output(8, "out")
        self.ext = DslCosimExternalLeaf(verilog_source=verilog_source, include_dir=include_dir)
        self.mem = self.add_memory(Memory(8, 4, "mem", init_file=init_file))

        @self.comb
        def _comb():
            self.ext.din <<= self.din
            self.out <<= self.ext.dout + self.mem[self.addr]


def _materialize_mixed_cosim_artifacts(tmp_path: Path) -> DslCosimMixedExternalRomTop:
    include_dir = tmp_path / "rtl" / "include"
    include_dir.mkdir(parents=True, exist_ok=True)
    (include_dir / "cosim_defs.svh").write_text("`define COSIM_INC 1\n", encoding="utf-8")

    verilog_source = tmp_path / "rtl" / "cosim_ext_leaf.sv"
    verilog_source.parent.mkdir(parents=True, exist_ok=True)
    verilog_source.write_text(
        '`include "cosim_defs.svh"\n'
        "module cosim_ext_leaf(input logic [7:0] din, output logic [7:0] dout);\n"
        "  assign dout = din;\n"
        "endmodule\n",
        encoding="utf-8",
    )

    init_file = tmp_path / "roms" / "cosim.hex"
    init_file.parent.mkdir(parents=True, exist_ok=True)
    init_file.write_text("", encoding="utf-8")

    return DslCosimMixedExternalRomTop(
        verilog_source=str(verilog_source),
        include_dir=str(include_dir),
        init_file=str(init_file),
    )


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
    import rtlgen.sim.cosim as cosim_mod

    monkeypatch.setattr(cosim_mod, "_compile_and_run_with_iverilog", lambda **kwargs: (_ for _ in ()).throw(FileNotFoundError("iverilog")))

    report = run_dsl_rtl_cosim(
        DslCosimAccum(),
        ({"inp": 1},),
        rtl_backend="iverilog",
    )

    assert report.skipped_reason == "iverilog"
    assert report.dsl_matches_rtl is False
    assert report.compiled_matches_rtl is False


def test_collect_external_artifact_bundle_stages_external_and_init_files(tmp_path):
    import rtlgen.sim.cosim as cosim_mod
    from rtlgen.dsl import VerilogEmitter

    module = _materialize_mixed_cosim_artifacts(tmp_path)
    dut_src = VerilogEmitter().emit_design(module)
    bundle = cosim_mod._collect_external_artifact_bundle(module, dut_src)

    source_names = tuple(path for path, _ in bundle.sources)
    support_names = tuple(path for path, _ in bundle.support_files)

    assert source_names[0] == "dut.sv"
    assert "external_sources/0_cosim_ext_leaf.sv" in source_names
    assert bundle.include_dirs == ("include_dirs/0_include",)
    assert bundle.defines == {"COSIM_EXT": "1"}
    assert bundle.init_files == ("init_files/rom_0_cosim.hex",)
    assert "init_files/rom_0_cosim.hex" in support_names
    assert "include_dirs/0_include/cosim_defs.svh" in support_names
    assert '$readmemh("init_files/rom_0_cosim.hex",' in bundle.sources[0][1]


def test_compile_and_run_with_iverilog_stages_compile_flags_and_support_files(tmp_path, monkeypatch):
    import rtlgen.sim.cosim as cosim_mod
    from rtlgen.dsl import VerilogEmitter

    module = _materialize_mixed_cosim_artifacts(tmp_path)
    bundle = cosim_mod._collect_external_artifact_bundle(module, VerilogEmitter().emit_design(module))
    calls = []

    class _Completed:
        def __init__(self, returncode=0, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(cmd, cwd=None, capture_output=True, text=True, env=None):
        calls.append((tuple(cmd), Path(cwd)))
        if cmd[0] == "iverilog":
            assert "+incdir+include_dirs/0_include" in cmd
            assert "+define+COSIM_EXT=1" in cmd
            assert str(Path(cwd) / "external_sources/0_cosim_ext_leaf.sv") in cmd
            assert (Path(cwd) / "init_files/rom_0_cosim.hex").read_text(encoding="utf-8") == ""
            return _Completed(stdout="")
        return _Completed(stdout="CYCLE 0 out=3\nCOSIM_DONE\n")

    monkeypatch.setattr(cosim_mod.subprocess, "run", fake_run)

    stdout = cosim_mod._compile_and_run_with_iverilog(
        tb_sv="module tb_top; initial begin $display(\"COSIM_DONE\"); $finish; end endmodule\n",
        dut_src=bundle.sources[0][1],
        artifacts=bundle,
    )

    assert "COSIM_DONE" in stdout
    assert len(calls) == 2


def test_dsl_rtl_cosim_explicit_vcs_skips_when_missing(monkeypatch):
    import rtlgen.sim.cosim as cosim_mod

    monkeypatch.setattr(cosim_mod, "_find_local_vcs", lambda: None)

    report = run_dsl_rtl_cosim(
        DslCosimAccum(),
        ({"inp": 1},),
        rtl_backend="vcs",
    )

    assert report.rtl_backend == "vcs"
    assert report.skipped_reason == "vcs"


def test_dsl_rtl_cosim_auto_backend_reports_iverilog_when_verilator_missing(monkeypatch):
    import rtlgen.sim.cosim as cosim_mod

    monkeypatch.setattr(cosim_mod, "_find_local_verilator", lambda: None)
    monkeypatch.setattr(cosim_mod, "_find_local_vcs", lambda: None)
    monkeypatch.setattr(cosim_mod.rtl_cosim, "_compile_and_run", lambda *args, **kwargs: "CYCLE 0 out=1\nCOSIM_DONE\n")
    monkeypatch.setattr(cosim_mod.rtl_cosim, "_parse_sv_output", lambda stdout: ({"out": 1},))

    report = run_dsl_rtl_cosim(
        DslCosimAccum(),
        ({"inp": 1},),
        rtl_backend="auto",
    )

    assert report.rtl_backend == "iverilog"


def test_dsl_rtl_cosim_auto_backend_prefers_vcs_over_iverilog_when_verilator_missing(monkeypatch):
    import rtlgen.sim.cosim as cosim_mod

    monkeypatch.setattr(cosim_mod, "_find_local_verilator", lambda: None)
    monkeypatch.setattr(cosim_mod, "_find_local_vcs", lambda: "/tools/bin/vcs")
    monkeypatch.setattr(cosim_mod, "_run_reference_trace", lambda *args, **kwargs: ({"out": 1},))
    monkeypatch.setattr(cosim_mod, "_run_compiled_trace", lambda *args, **kwargs: ({"out": 1},))
    monkeypatch.setattr(
        cosim_mod,
        "_run_vcs_trace",
        lambda *args, **kwargs: (
            ({"out": 1},),
            cosim_mod._ExternalSimRunResult(
                stdout="CYCLE 0 out=1\nCOSIM_DONE\n",
                cache_enabled=True,
                cache_hit=False,
                cache_key="fake_vcs_key",
                cache_dir="/tmp/fake_vcs_cache",
            ),
        ),
    )

    report = run_dsl_rtl_cosim(
        DslCosimAccum(),
        ({"inp": 1},),
        rtl_backend="auto",
    )

    assert report.rtl_backend == "vcs"


def test_dsl_rtl_cosim_cached_external_sim_reuses_compiled_artifact(tmp_path, monkeypatch):
    import rtlgen.sim.cosim as cosim_mod

    compile_calls = []
    run_calls = []
    artifacts = cosim_mod._ExternalArtifactBundle(
        sources=(("dut.sv", "module dut; endmodule\n"),),
        support_files=(),
        include_dirs=(),
        defines={},
        init_files=(),
    )

    def fake_compile(root_path, **kwargs):
        compile_calls.append(root_path)
        obj_dir = root_path / "obj_dir"
        obj_dir.mkdir(parents=True, exist_ok=True)
        exe = obj_dir / "Vtb_top"
        exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        exe.chmod(0o755)

    def fake_cached_external_sim(**kwargs):
        root_path, _tempdir = cosim_mod._prepare_external_sim_root(
            kwargs["backend"],
            kwargs["compile_key"],
            kwargs["build_dir"],
        )
        for filename, contents in kwargs["source_files"].items():
            (root_path / filename).write_text(contents, encoding="utf-8")
        (root_path / kwargs["vector_filename"]).write_text(kwargs["vectors_text"], encoding="utf-8")
        stamp_path = root_path / ".compile_stamp"
        if not stamp_path.exists():
            kwargs["compile_runner"](root_path)
            stamp_path.write_text(kwargs["compile_key"], encoding="utf-8")
        run_calls.append(root_path)
        return cosim_mod._ExternalSimRunResult(
            stdout="CYCLE 0 out=1\nCOSIM_DONE\n",
            cache_enabled=kwargs["build_dir"] is not None,
            cache_hit=stamp_path.exists(),
            cache_key=kwargs["compile_key"],
            cache_dir=str(root_path),
        )

    monkeypatch.setattr(cosim_mod, "_run_verilator_compile", fake_compile)
    monkeypatch.setattr(cosim_mod, "_compile_and_run_cached_external_sim", fake_cached_external_sim)

    kwargs = dict(
        verilator="/tools/bin/verilator",
        tb_sv="module tb_top; endmodule\n",
        dut_src="module dut; endmodule\n",
        artifacts=artifacts,
        top_module="tb_top",
        vectors_text="0 1\n",
        build_dir=tmp_path / "cache_root",
    )
    first = cosim_mod._compile_and_run_with_verilator(**kwargs)
    second = cosim_mod._compile_and_run_with_verilator(**kwargs)

    assert first.stdout == "CYCLE 0 out=1\nCOSIM_DONE\n"
    assert second.stdout == first.stdout
    assert first.cache_enabled is True
    assert first.cache_hit is True
    assert second.cache_hit is True
    assert first.cache_key == second.cache_key
    assert len(compile_calls) == 1
    assert len(run_calls) == 2


def test_prepare_external_sim_root_normalizes_relative_build_dir(tmp_path, monkeypatch):
    import rtlgen.sim.cosim as cosim_mod

    monkeypatch.chdir(tmp_path)
    root_path, tempdir = cosim_mod._prepare_external_sim_root(
        "verilator",
        "abc123",
        Path("build") / "relative_cache",
    )
    try:
        assert tempdir is None
        assert root_path.is_absolute()
        assert root_path == (tmp_path / "build" / "relative_cache" / "abc123").resolve()
    finally:
        if tempdir is not None:
            tempdir.cleanup()


def test_dsl_rtl_cosim_report_exposes_cache_metadata(tmp_path):
    build_root = tmp_path / "cosim_cache_meta"

    first = run_dsl_rtl_cosim(
        DslCosimAccum(),
        (
            {"inp": 5},
            {"inp": 2},
        ),
        rtl_backend="verilator",
        build_dir=build_root,
    )
    second = run_dsl_rtl_cosim(
        DslCosimAccum(),
        (
            {"inp": 5},
            {"inp": 2},
        ),
        rtl_backend="verilator",
        build_dir=build_root,
    )

    assert first.skipped_reason is None
    assert first.cache_enabled is True
    assert first.cache_hit is False
    assert first.cache_key is not None
    assert first.cache_dir is not None
    assert second.cache_enabled is True
    assert second.cache_hit is True
    assert second.cache_key == first.cache_key
    assert second.cache_dir == first.cache_dir


def test_dsl_rtl_cosim_explicit_verilator_executes_when_available(tmp_path):
    report = run_dsl_rtl_cosim(
        DslCosimAccum(),
        (
            {"inp": 5},
            {"inp": 2},
            {"inp": 1},
        ),
        rtl_backend="verilator",
        build_dir=tmp_path / "cosim_verilator",
    )

    assert report.skipped_reason is None
    assert report.rtl_backend == "verilator"
    assert report.dsl_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.compiled_trace[-1]["out"] == 8
    assert report.rtl_trace[-1]["out"] == 8


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
    import rtlgen.sim.cosim as cosim_mod

    monkeypatch.setattr(cosim_mod, "_compile_and_run_with_iverilog", lambda **kwargs: (_ for _ in ()).throw(FileNotFoundError("iverilog")))

    report = run_dsl_multiclock_rtl_cosim(
        DslCosimDualClockMailbox(),
        (
            ({"wr_rst": 1, "rd_rst": 1}, ("wr_clk", "rd_clk")),
        ),
        rtl_backend="iverilog",
    )

    assert report.skipped_reason == "iverilog"
    assert report.dsl_matches_rtl is False
    assert report.compiled_matches_rtl is False


def test_dsl_multiclock_rtl_cosim_explicit_verilator_skips_when_missing(monkeypatch):
    import rtlgen.sim.cosim as cosim_mod

    monkeypatch.setattr(cosim_mod, "_find_local_verilator", lambda: None)

    report = run_dsl_multiclock_rtl_cosim(
        DslCosimDualClockMailbox(),
        (
            ({"wr_rst": 1, "rd_rst": 1}, ("wr_clk", "rd_clk")),
        ),
        rtl_backend="verilator",
    )

    assert report.rtl_backend == "verilator"
    assert report.skipped_reason == "verilator"


def test_dsl_multiclock_rtl_cosim_explicit_vcs_skips_when_missing(monkeypatch):
    import rtlgen.sim.cosim as cosim_mod

    monkeypatch.setattr(cosim_mod, "_find_local_vcs", lambda: None)

    report = run_dsl_multiclock_rtl_cosim(
        DslCosimDualClockMailbox(),
        (
            ({"wr_rst": 1, "rd_rst": 1}, ("wr_clk", "rd_clk")),
        ),
        rtl_backend="vcs",
    )

    assert report.rtl_backend == "vcs"
    assert report.skipped_reason == "vcs"


def test_dsl_multiclock_rtl_cosim_rejects_direct_clock_drives():
    with pytest.raises(ValueError, match="must not drive managed clock signals directly"):
        run_dsl_multiclock_rtl_cosim(
            DslCosimDualClockMailbox(),
            (
                ({"wr_clk": 1, "wr_rst": 1, "rd_rst": 1}, ("wr_clk", "rd_clk")),
            ),
        )


def test_dsl_multiclock_rtl_cosim_reports_unknown_array_state_clearly(monkeypatch):
    import rtlgen.sim.cosim as cosim_mod

    monkeypatch.setattr(cosim_mod, "_run_multiclock_reference_trace", lambda *args, **kwargs: ({"_cycle": 0, "dout": 0},))
    monkeypatch.setattr(cosim_mod, "_run_multiclock_compiled_trace", lambda *args, **kwargs: ({"_cycle": 0, "dout": 0},))
    monkeypatch.setattr(
        cosim_mod,
        "_run_multiclock_rtl_trace",
        lambda *args, **kwargs: (
            ({"_cycle": 0, "dout__raw": "x"},),
            cosim_mod._ExternalSimRunResult(
                stdout="CYCLE 0 dout=x\nCOSIM_DONE\n",
                cache_enabled=False,
                cache_hit=False,
                cache_key=None,
                cache_dir=None,
            ),
        ),
    )

    with pytest.raises(CosimUnknownValueError, match="emitted RTL trace observed unknown value"):
        run_dsl_multiclock_rtl_cosim(
            DslCosimDualClockArrayMailbox(),
            (
                ({"wr_rst": 1, "rd_rst": 1}, ("wr_clk", "rd_clk")),
                ({"wr_rst": 0, "rd_rst": 0, "wr_en": 1, "din": 11}, ("wr_clk",)),
            ),
        )
