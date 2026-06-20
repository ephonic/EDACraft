import importlib.util
import os
from pathlib import Path

from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    Signal,
    SignalRef,
    SimModule,
)
from rtlgen_x.dsl import Array, Else, If, Input, Module, Output, Reg
from rtlgen_x.verify import (
    describe_verification_interface,
    emit_python_reference_model,
    generate_uvm_collateral,
    generate_uvm_runtime_bundle,
    load_generated_reference_model,
    probe_iverilog_uvm_collateral,
    smoke_test_generated_reference_model,
    UvmSequenceStep,
    write_uvm_collateral,
    write_uvm_runtime_bundle,
)


def _accum_module() -> SimModule:
    return SimModule(
        name="uvm_accum",
        signals=(
            Signal("clk", width=1, kind="input"),
            Signal("rst_n", width=1, kind="input"),
            Signal("inp", width=8, kind="input"),
            Signal("acc", width=8, kind="state", init=3),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("acc"), SignalRef("inp"))),
            Assignment("acc", SignalRef("out"), phase="seq"),
        ),
        outputs=("out",),
        reset_signal="rst_n",
    )


def _accum_dut_sv() -> str:
    return """
module uvm_accum (
    input logic clk,
    input logic rst_n,
    input logic [7:0] inp,
    output logic [7:0] out
);
  logic [7:0] acc = 8'd3;

  always_ff @(posedge clk) begin
    if (rst_n) begin
      acc <= 8'd3;
    end else begin
      acc <= out;
    end
  end

  always_comb begin
    out = acc + inp;
  end
endmodule
""".strip() + "\n"


class LegacyAccum(Module):
    def __init__(self):
        super().__init__("legacy_uvm_accum")
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


class LegacyStorage(Module):
    def __init__(self):
        super().__init__("legacy_storage")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.we = Input(1, "we")
        self.addr = Input(2, "addr")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.rf = Array(8, 4, "rf")

        @self.comb
        def _comb():
            self.dout <<= self.rf[self.addr]

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.we):
                self.rf[self.addr] <<= self.din


def _load_external_module(rel_path: str, class_name: str):
    path = Path(__file__).resolve().parents[2] / rel_path
    spec = importlib.util.spec_from_file_location(f"verify_{path.stem}_{class_name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, class_name)()


def test_describe_verification_interface_preserves_signal_order():
    interface = describe_verification_interface(_accum_module())

    assert interface.module_name == "uvm_accum"
    assert interface.reset_signal == "rst_n"
    assert interface.reset_active_low is False
    assert [port.name for port in interface.inputs] == ["clk", "rst_n", "inp"]
    assert [port.name for port in interface.outputs] == ["out"]
    assert interface.outputs[0].width == 8


def test_emit_python_reference_model_contains_wrapper_class():
    source = emit_python_reference_model(_accum_module())

    assert 'Generated Python reference model for "uvm_accum"' in source
    assert "class UvmAccumReferenceModel:" in source
    assert "rtlgen_x_ref_runtime.py" in source
    assert "self._sim = PythonSimulator(build_uvm_accum_module())" in source
    assert "def predict(self, transaction: Mapping[str, int]) -> Dict[str, int]:" in source
    assert "def predict_batch(self, transactions):" in source
    assert "self._sim.run_batch(rows)" in source


def test_generate_uvm_collateral_emits_expected_artifacts(tmp_path):
    collateral = generate_uvm_collateral(
        _accum_module(),
        interface_name="uvm_accum_if",
        clock_name="clk",
    )

    artifact_map = collateral.artifact_map()

    assert collateral.package_name == "uvm_accum_uvm_pkg"
    assert collateral.reference_model_class == "UvmAccumReferenceModel"
    assert "uvm_accum_if.sv" in artifact_map
    assert "uvm_accum_txn.sv" in artifact_map
    assert "uvm_accum_sequencer.sv" in artifact_map
    assert "uvm_accum_smoke_seq.sv" in artifact_map
    assert "uvm_accum_driver.sv" in artifact_map
    assert "uvm_accum_monitor.sv" in artifact_map
    assert "uvm_accum_agent.sv" in artifact_map
    assert "uvm_accum_scoreboard.sv" in artifact_map
    assert "uvm_accum_env.sv" in artifact_map
    assert "uvm_accum_test.sv" in artifact_map
    assert "uvm_accum_uvm_pkg.sv" in artifact_map
    assert "rtlgen_x_ref_runtime.py" in artifact_map
    assert "uvm_accum_ref_model.py" in artifact_map
    assert "uvm_accum_dpi_bridge.py" in artifact_map
    assert "uvm_accum_dpi_bridge.c" in artifact_map
    assert "interface uvm_accum_if(input logic clk);" in artifact_map["uvm_accum_if.sv"]
    assert "logic rst_n;" in artifact_map["uvm_accum_if.sv"]
    assert "logic [7:0] inp;" in artifact_map["uvm_accum_if.sv"]
    assert "logic [7:0] out;" in artifact_map["uvm_accum_if.sv"]
    assert "logic clk;" not in artifact_map["uvm_accum_if.sv"]
    assert "class uvm_accum_driver extends uvm_driver #(uvm_accum_txn);" in artifact_map["uvm_accum_driver.sv"]
    assert "@(negedge vif.clk);" in artifact_map["uvm_accum_driver.sv"]
    assert "class uvm_accum_sequencer extends uvm_sequencer #(uvm_accum_txn);" in artifact_map["uvm_accum_sequencer.sv"]
    assert "class uvm_accum_agent extends uvm_agent;" in artifact_map["uvm_accum_agent.sv"]
    assert "#1step;" in artifact_map["uvm_accum_monitor.sv"]
    assert "seq.start(env.agent.sequencer);" in artifact_map["uvm_accum_test.sv"]
    assert "req.randomize() with { rst_n == 1'b1; }" in artifact_map["uvm_accum_smoke_seq.sv"]
    assert "req.randomize() with { rst_n == 1'b0; }" in artifact_map["uvm_accum_smoke_seq.sv"]
    assert "class uvm_accum_scoreboard extends uvm_component;" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "rtlgen_x_predict(" in artifact_map["uvm_accum_scoreboard.sv"]
    assert 'rtlgen_x_predict("uvm_accum_ref_model.py", observed.rst_n, observed.inp, predicted_out);' in artifact_map[
        "uvm_accum_scoreboard.sv"
    ]
    assert "uvm_accum_ref_model.py" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "observed.rst_n, observed.inp, predicted_out" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "expected.out = predicted_out;" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "function void report_phase(uvm_phase phase);" in artifact_map["uvm_accum_scoreboard.sv"]
    assert '`uvm_info("UVM_ACCUM_SCOREBOARD", "scoreboard passed", UVM_LOW)' in artifact_map["uvm_accum_scoreboard.sv"]
    assert '`include "uvm_accum_if.sv"' in artifact_map["uvm_accum_uvm_pkg.sv"]
    assert 'import "DPI-C" context function void rtlgen_x_predict(' in artifact_map["uvm_accum_uvm_pkg.sv"]
    assert "def predict_flat(ref_model_path: str, *input_values: int):" in artifact_map["uvm_accum_dpi_bridge.py"]
    assert "void rtlgen_x_predict(" in artifact_map["uvm_accum_dpi_bridge.c"]
    assert "PyObject_CallObject" in artifact_map["uvm_accum_dpi_bridge.c"]
    assert "class PythonSimulator:" in artifact_map["rtlgen_x_ref_runtime.py"]

    written = write_uvm_collateral(collateral, tmp_path / "uvm_out")
    written_names = sorted(path.name for path in written)
    assert written_names == sorted(artifact_map)
    assert (tmp_path / "uvm_out" / "uvm_accum_ref_model.py").read_text(encoding="utf-8") == artifact_map[
        "uvm_accum_ref_model.py"
    ]
    assert (tmp_path / "uvm_out" / "rtlgen_x_ref_runtime.py").read_text(encoding="utf-8") == artifact_map[
        "rtlgen_x_ref_runtime.py"
    ]


def test_generate_uvm_collateral_accepts_directed_sequence():
    collateral = generate_uvm_collateral(
        _accum_module(),
        interface_name="uvm_accum_if",
        clock_name="clk",
        directed_sequence=(
            UvmSequenceStep(inputs={"rst_n": 0, "inp": 0}, label="reset0"),
            {"rst_n": 1, "inp": 5},
            {"rst_n": 1, "inp": 2},
        ),
    )

    seq_source = collateral.artifact_map()["uvm_accum_smoke_seq.sv"]

    assert 'create("reset0")' in seq_source
    assert "req.rst_n = 1'b0;" in seq_source
    assert "req.inp = 8'h5;" in seq_source
    assert "req.inp = 8'h2;" in seq_source
    assert "req.randomize()" not in seq_source


def test_generate_uvm_runtime_bundle_emits_runnable_artifacts(tmp_path):
    bundle = generate_uvm_runtime_bundle(
        _accum_module(),
        interface_name="uvm_accum_if",
        clock_name="clk",
        dut_module_name="uvm_accum",
        dut_source=_accum_dut_sv(),
    )

    artifact_map = bundle.artifact_map()

    assert bundle.top_module_name == "uvm_accum_top"
    assert bundle.test_name == "uvm_accum_test"
    assert "uvm_accum_dut.sv" in artifact_map
    assert "uvm_accum_top.sv" in artifact_map
    assert "filelist.f" in artifact_map
    assert "run_vcs.sh" in artifact_map
    assert "rtlgen_x_ref_runtime.py" in artifact_map
    assert "module uvm_accum" in artifact_map["uvm_accum_dut.sv"]
    assert "import uvm_pkg::*;" in artifact_map["uvm_accum_top.sv"]
    assert 'uvm_config_db#(virtual uvm_accum_if)::set(null, "*", "vif", vif);' in artifact_map["uvm_accum_top.sv"]
    assert 'run_test("uvm_accum_test");' in artifact_map["uvm_accum_top.sv"]
    assert "uvm_accum_uvm_pkg.sv" in artifact_map["filelist.f"]
    assert "uvm_accum_dut.sv" in artifact_map["filelist.f"]
    assert "uvm_accum_top.sv" in artifact_map["filelist.f"]
    assert "python3-config --embed --ldflags" in artifact_map["run_vcs.sh"]
    assert "-ntb_opts uvm-1.2" in artifact_map["run_vcs.sh"]
    assert "gcc -shared -fPIC " in artifact_map["run_vcs.sh"]
    assert "./simv -sv_lib libuvm_accum_dpi_bridge +UVM_TESTNAME=uvm_accum_test" in artifact_map["run_vcs.sh"]

    written = write_uvm_runtime_bundle(bundle, tmp_path / "uvm_runtime", include_runtime_package=True)
    written_names = sorted(path.name for path in written)
    assert "run_vcs.sh" in written_names
    assert "rtlgen_x_ref_runtime.py" in written_names
    assert os.access(tmp_path / "uvm_runtime" / "run_vcs.sh", os.X_OK)
    assert (tmp_path / "uvm_runtime" / "rtlgen_x_ref_runtime.py").exists()
    assert (tmp_path / "uvm_runtime" / "rtlgen_x" / "sim" / "__init__.py").exists()


def test_generate_uvm_runtime_bundle_accepts_legacy_dsl_module():
    bundle = generate_uvm_runtime_bundle(LegacyAccum(), clock_name="clk")
    artifact_map = bundle.artifact_map()

    assert bundle.dut_module_name == "legacy_uvm_accum"
    assert "legacy_uvm_accum_dut.sv" in artifact_map
    assert "legacy_uvm_accum_top.sv" in artifact_map
    assert "module legacy_uvm_accum" in artifact_map["legacy_uvm_accum_dut.sv"]
    assert "req.randomize() with { rst == 1'b1; }" in artifact_map["legacy_uvm_accum_smoke_seq.sv"]
    assert "req.randomize() with { rst == 1'b0; }" in artifact_map["legacy_uvm_accum_smoke_seq.sv"]


def test_generate_uvm_runtime_bundle_accepts_legacy_latch_module(tmp_path):
    from rtlgen_x.tests.test_dsl_legacy_import import LatchPass

    bundle = generate_uvm_runtime_bundle(LatchPass(), clock_name="clk")
    artifact_map = bundle.artifact_map()

    assert bundle.module_name == "LatchPass"
    assert bundle.dut_module_name == "LatchPass"
    assert "latchpass_dut.sv" in artifact_map
    assert "latchpass_top.sv" in artifact_map
    assert "module LatchPass" in artifact_map["latchpass_dut.sv"]
    assert "always_latch begin" in artifact_map["latchpass_dut.sv"]
    assert "logic clk;" in artifact_map["latchpass_top.sv"]
    assert ".en(vif.en)" in artifact_map["latchpass_top.sv"]
    assert ".d(vif.d)" in artifact_map["latchpass_top.sv"]
    assert 'rtlgen_x_predict("latchpass_ref_model.py"' in artifact_map["latchpass_scoreboard.sv"]

    write_uvm_runtime_bundle(bundle, tmp_path / "latch_pass_runtime", include_runtime_package=False)
    report = smoke_test_generated_reference_model(
        tmp_path / "latch_pass_runtime" / "latchpass_ref_model.py",
        inputs={"en": 1, "d": 0x34},
    )
    assert report.predicted == {"out": 0x34}


def test_generate_uvm_runtime_bundle_accepts_real_sram256k_module(tmp_path):
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )

    bundle = generate_uvm_runtime_bundle(module, clock_name="clk")
    artifact_map = bundle.artifact_map()

    assert bundle.module_name == "earphone_sram256k"
    assert bundle.dut_module_name == "EarphoneSRAM256K"
    assert "earphone_sram256k_dut.sv" in artifact_map
    assert "earphone_sram256k_top.sv" in artifact_map
    assert "rtlgen_x_ref_runtime.py" in artifact_map
    assert "module EarphoneSRAM256K" in artifact_map["earphone_sram256k_dut.sv"]
    assert "req.randomize() with { rst_n == 1'b0; }" in artifact_map["earphone_sram256k_smoke_seq.sv"]
    assert "req.randomize() with { rst_n == 1'b1; }" in artifact_map["earphone_sram256k_smoke_seq.sv"]
    assert "logic [31:0] paddr;" in artifact_map["earphone_sram256k_if.sv"]
    assert "logic [31:0] pwdata;" in artifact_map["earphone_sram256k_if.sv"]
    assert "logic [31:0] prdata;" in artifact_map["earphone_sram256k_if.sv"]
    assert 'rtlgen_x_predict("earphone_sram256k_ref_model.py"' in artifact_map["earphone_sram256k_scoreboard.sv"]

    write_uvm_runtime_bundle(bundle, tmp_path / "earphone_sram_runtime", include_runtime_package=False)
    report = smoke_test_generated_reference_model(
        tmp_path / "earphone_sram_runtime" / "earphone_sram256k_ref_model.py",
        inputs={
            "clk": 0,
            "rst_n": 1,
            "paddr": 0,
            "pwdata": 0,
            "pwrite": 0,
            "psel": 0,
            "penable": 0,
            "pstrb": 0,
        },
    )
    assert report.predicted == {"prdata": 0, "pready": 0, "pslverr": 0}


def test_generate_uvm_runtime_bundle_accepts_real_fft256_module(tmp_path):
    module = _load_external_module(
        "earphone/modules/fft256/layer_L5_dsl/src/dsl.py",
        "EarphoneFFT256",
    )

    bundle = generate_uvm_runtime_bundle(module, clock_name="clk")
    artifact_map = bundle.artifact_map()

    assert bundle.module_name == "earphone_fft256"
    assert bundle.dut_module_name == "EarphoneFFT256"
    assert "earphone_fft256_dut.sv" in artifact_map
    assert "earphone_fft256_ref_model.py" in artifact_map
    assert "module EarphoneFFT256" in artifact_map["earphone_fft256_dut.sv"]

    write_uvm_runtime_bundle(bundle, tmp_path / "earphone_fft_runtime", include_runtime_package=False)
    report = smoke_test_generated_reference_model(
        tmp_path / "earphone_fft_runtime" / "earphone_fft256_ref_model.py",
        inputs={"clk": 0, "rst": 1, "di_en": 0, "di_re": 0, "di_im": 0},
    )
    assert report.predicted == {"do_en": 0, "do_re": 0, "do_im": 0}


def test_generate_uvm_runtime_bundle_accepts_real_simd16_module(tmp_path):
    module = _load_external_module(
        "earphone/modules/simd16/layer_L5_dsl/src/dsl.py",
        "EarphoneSIMD16",
    )

    bundle = generate_uvm_runtime_bundle(module, clock_name="clk")
    artifact_map = bundle.artifact_map()

    assert bundle.module_name == "earphone_simd16"
    assert "earphone_simd16_dut.sv" in artifact_map
    assert "logic [255:0] vsrc0;" in artifact_map["earphone_simd16_if.sv"]
    assert "logic [255:0] vdst;" in artifact_map["earphone_simd16_if.sv"]

    write_uvm_runtime_bundle(bundle, tmp_path / "earphone_simd_runtime", include_runtime_package=False)
    report = smoke_test_generated_reference_model(
        tmp_path / "earphone_simd_runtime" / "earphone_simd16_ref_model.py",
        inputs={
            "clk": 0,
            "rst_n": 0,
            "vsrc0": 0,
            "vsrc1": 0,
            "vsrc2": 0,
            "op": 0,
            "mode": 0,
            "pred": 0,
            "start": 0,
        },
    )
    assert report.predicted == {"vdst": 0, "done": 0}


def test_generate_uvm_runtime_bundle_requires_dut_source_for_non_legacy_module():
    try:
        generate_uvm_runtime_bundle(_accum_module(), interface_name="uvm_accum_if", clock_name="clk")
    except ValueError as exc:
        assert "dut_source is required" in str(exc)
    else:
        raise AssertionError("expected a dut_source requirement for raw SimModule runtime bundles")


def test_generated_reference_model_can_be_loaded_and_smoke_tested(tmp_path):
    collateral = generate_uvm_collateral(
        _accum_module(),
        interface_name="uvm_accum_if",
        clock_name="clk",
    )
    write_uvm_collateral(collateral, tmp_path / "uvm_out")
    ref_model_path = tmp_path / "uvm_out" / "uvm_accum_ref_model.py"

    model = load_generated_reference_model(ref_model_path)
    model.reset()
    first = model.predict({"clk": 0, "rst_n": 0, "inp": 5})
    model.reset()
    second = model.predict_batch(({"clk": 0, "rst_n": 0, "inp": 5},))
    report = smoke_test_generated_reference_model(
        ref_model_path,
        inputs={"clk": 0, "rst_n": 0, "inp": 5},
    )

    assert type(model).__name__ == "UvmAccumReferenceModel"
    assert first == {"out": 8}
    assert second == ({"out": 8},)
    assert report.class_name == "UvmAccumReferenceModel"
    assert report.predicted == {"out": 8}
    assert report.batched_predicted == ({"out": 8},)


def test_probe_iverilog_uvm_collateral_reports_current_tool_support(tmp_path):
    collateral = generate_uvm_collateral(
        _accum_module(),
        interface_name="uvm_accum_if",
        clock_name="clk",
    )
    report = probe_iverilog_uvm_collateral(collateral, output_dir=tmp_path / "iverilog_probe")

    assert report.skipped_reason in {None, "iverilog"}
    if report.skipped_reason == "iverilog":
        return
    assert report.interface_compile_ok is True
    assert report.interface_returncode == 0
    assert report.package_source.name == "uvm_accum_uvm_pkg.sv"
    if report.package_compile_ok:
        assert report.uvm_support_available is True
    else:
        assert report.package_returncode != 0
        assert report.package_stderr


def test_verification_collateral_accepts_legacy_dsl_module():
    interface = describe_verification_interface(LegacyAccum())
    source = emit_python_reference_model(LegacyAccum())
    collateral = generate_uvm_collateral(LegacyAccum(), interface_name="legacy_uvm_if", clock_name="clk")

    assert interface.module_name == "legacy_uvm_accum"
    assert interface.reset_signal == "rst"
    assert interface.reset_active_low is False
    assert [port.name for port in interface.inputs] == ["clk", "rst", "inp"]
    assert "outputs_post_state=True" in source
    assert collateral.reference_model_class == "LegacyUvmAccumReferenceModel"
    assert "legacy_uvm_if.sv" in collateral.artifact_map()


def test_emit_python_reference_model_renders_memory_support():
    module = SimModule(
        name="uvm_mem",
        signals=(
            Signal("we", width=1, kind="input"),
            Signal("addr", width=2, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("dout", width=8, kind="output"),
        ),
        assignments=(Assignment("dout", MemoryReadExpr("mem", SignalRef("addr"))),),
        outputs=("dout",),
        memories=(Memory("mem", width=8, depth=4, init=(1, 2, 3, 4)),),
        memory_writes=(MemoryWrite("mem", SignalRef("addr"), SignalRef("din"), enable=SignalRef("we")),),
        outputs_post_state=True,
    )

    source = emit_python_reference_model(module)
    assert "MemoryReadExpr('mem', SignalRef('addr'))" in source
    assert "MemoryWrite('mem', SignalRef('addr'), SignalRef('din'), enable=SignalRef('we'))" in source


def test_generated_reference_model_supports_latch_phase(tmp_path):
    module = SimModule(
        name="uvm_latch",
        signals=(
            Signal("en", width=1, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("state", width=8, kind="state", init=0),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment(
                "state",
                MuxExpr(SignalRef("en"), SignalRef("din"), SignalRef("state")),
                phase="latch",
            ),
            Assignment("out", SignalRef("state")),
        ),
        outputs=("out",),
        outputs_post_state=True,
    )

    collateral = generate_uvm_collateral(
        module,
        interface_name="uvm_latch_if",
        clock_name="en",
    )
    write_uvm_collateral(collateral, tmp_path / "uvm_latch_out")
    ref_model_path = tmp_path / "uvm_latch_out" / "uvm_latch_ref_model.py"

    model = load_generated_reference_model(ref_model_path)
    model.reset()
    assert model.predict({"en": 0, "din": 0x12}) == {"out": 0x00}
    assert model.predict({"en": 1, "din": 0x34}) == {"out": 0x34}
    assert model.predict({"en": 0, "din": 0x56}) == {"out": 0x34}


def test_verification_collateral_accepts_legacy_storage_module():
    interface = describe_verification_interface(LegacyStorage())
    source = emit_python_reference_model(LegacyStorage())

    assert interface.module_name == "legacy_storage"
    assert interface.reset_signal == "rst"
    assert interface.reset_active_low is False
    assert [port.name for port in interface.outputs] == ["dout"]
    assert "MemoryWrite('rf'" in source


def test_verification_collateral_accepts_real_sram256k_module():
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )

    interface = describe_verification_interface(module)
    collateral = generate_uvm_collateral(
        module,
        interface_name="earphone_sram_if",
        clock_name="clk",
    )
    artifact_map = collateral.artifact_map()

    assert interface.module_name == "earphone_sram256k"
    assert interface.reset_signal == "rst_n"
    assert interface.reset_active_low is True
    assert [port.name for port in interface.inputs[:4]] == ["clk", "rst_n", "paddr", "pwdata"]
    assert [port.name for port in interface.outputs] == ["prdata", "pready", "pslverr"]
    assert "earphone_sram_if.sv" in artifact_map
    assert "earphone_sram256k_ref_model.py" in artifact_map
    assert "logic [31:0] paddr;" in artifact_map["earphone_sram_if.sv"]
    assert "logic [31:0] prdata;" in artifact_map["earphone_sram_if.sv"]
    assert "Memory('mem', width=32, depth=65536" in artifact_map["earphone_sram256k_ref_model.py"]
    assert "MemoryWrite('mem'" in artifact_map["earphone_sram256k_ref_model.py"]
