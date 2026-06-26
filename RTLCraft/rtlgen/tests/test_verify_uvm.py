import importlib.util
import os
import shutil
from pathlib import Path

import pytest

from rtlgen.dsl import DslLoweringReport, LoweredDslModule
from rtlgen.sim import (
    Assignment,
    BinaryExpr,
    ClockDomain,
    ConstExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    Signal,
    SignalRef,
    SimModule,
)
from rtlgen.dsl import APBRegisterBank, AXI4LiteRegisterBank, Array, AsyncFIFO, Else, If, Input, Module, Output, ReadyValidAsyncBridge, ReadyValidFIFO, ReadyValidRegister, Reg, SkidBuffer, SyncFIFO, WishboneRegisterBank
from rtlgen.verify import (
    ApbTransfer,
    AxiLiteTransfer,
    AxiStreamTransfer,
    describe_verification_interface,
    emit_python_reference_model,
    generate_uvm_collateral,
    generate_uvm_runtime_bundle,
    load_generated_reference_model,
    protocol_transfers_to_uvm_sequence_steps,
    probe_iverilog_uvm_collateral,
    smoke_test_generated_reference_model,
    UvmSequenceStep,
    WishboneTransfer,
    write_uvm_collateral,
    write_uvm_runtime_bundle,
)
from rtlgen.verify.uvm import _render_memory, _render_memory_write


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


def _raw_accum_module() -> SimModule:
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


def _accum_module() -> LoweredDslModule:
    return _lowered(_raw_accum_module())


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


def _axis_ready_dut_sv() -> str:
    return """
module uvm_axis_ready (
    input logic clk,
    input logic rst,
    input logic [15:0] tdata,
    input logic tvalid,
    input logic tlast,
    input logic [1:0] tkeep,
    output logic tready
);
  always_comb begin
    tready = tvalid;
  end
endmodule
""".strip() + "\n"


def _multi_clock_ref_module() -> LoweredDslModule:
    return _lowered(SimModule(
        name="uvm_multiclk_ref",
        signals=(
            Signal("wr_clk", width=1, kind="input"),
            Signal("rd_clk", width=1, kind="input"),
            Signal("wr_rst", width=1, kind="input"),
            Signal("rd_rst", width=1, kind="input"),
            Signal("wr_en", width=1, kind="input"),
            Signal("rd_en", width=1, kind="input"),
            Signal("wptr", width=4, kind="state"),
            Signal("rptr", width=4, kind="state"),
            Signal("out", width=4, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("wptr"), SignalRef("rptr"))),
            Assignment(
                "wptr",
                MuxExpr(
                    SignalRef("wr_en"),
                    BinaryExpr("+", SignalRef("wptr"), ConstExpr(1, 4)),
                    SignalRef("wptr"),
                ),
                phase="seq",
                clock_domain="wr_clk",
            ),
            Assignment(
                "rptr",
                MuxExpr(
                    SignalRef("rd_en"),
                    BinaryExpr("+", SignalRef("rptr"), ConstExpr(1, 4)),
                    SignalRef("rptr"),
                ),
                phase="seq",
                clock_domain="rd_clk",
            ),
        ),
        outputs=("out",),
        clock_domains=(
            ClockDomain("wr_clk", reset_signal="wr_rst"),
            ClockDomain("rd_clk", reset_signal="rd_rst"),
        ),
    ))


class DslAccum(Module):
    def __init__(self):
        super().__init__("dsl_uvm_accum")
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


class DslStorage(Module):
    def __init__(self):
        super().__init__("dsl_storage")
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


class DslMultiClockMailbox(Module):
    def __init__(self):
        super().__init__("dsl_multi_clock_mailbox")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.mem = Array(8, 4, "rf")
        self.wptr = Reg(2, "wptr")
        self.rptr = Reg(2, "rptr")
        self.clock_domain("write", self.wr_clk, self.wr_rst)
        self.clock_domain("read", self.rd_clk, self.rd_rst)

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
            with If(self.rd_rst == 1):
                self.rptr <<= 0
            with Else():
                with If(self.rd_en == 1):
                    self.rptr <<= self.rptr + 1


class DslAsyncLowStorage(Module):
    def __init__(self):
        super().__init__("dsl_async_low_storage")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.we = Input(1, "we")
        self.addr = Input(2, "addr")
        self.din = Input(8, "din")
        self.dout = Output(8, "dout")
        self.rf = Array(8, 4, "rf")

        @self.comb
        def _comb():
            self.dout <<= self.rf[self.addr]

        @self.seq(self.clk, ~self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.rf[0] <<= 0
            with Else():
                with If(self.we == 1):
                    self.rf[self.addr] <<= self.din


class DslReadyValidAsyncBridgeHarness(Module):
    def __init__(self):
        super().__init__("dsl_ready_valid_async_bridge_harness")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.in_data = Input(8, "in_data")
        self.in_valid = Input(1, "in_valid")
        self.out_ready = Input(1, "out_ready")
        self.in_ready = Output(1, "in_ready")
        self.out_data = Output(8, "out_data")
        self.out_valid = Output(1, "out_valid")
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


class DslAsyncFifoHarness(Module):
    def __init__(self):
        super().__init__("dsl_async_fifo_harness")
        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")
        self.din = Input(8, "din")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
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
                "din": self.din,
                "wr_en": self.wr_en,
                "rd_en": self.rd_en,
                "dout": self.dout,
                "full": self.full,
                "empty": self.empty,
            },
        )


class DslSyncFifoHarness(Module):
    def __init__(self):
        super().__init__("dsl_sync_fifo_harness")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.din = Input(8, "din")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.dout = Output(8, "dout")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self.count = Output(3, "count")
        self.rd_rdy = Output(1, "rd_rdy")
        self.fifo = SyncFIFO(width=8, depth=4, name="fifo")

        self.instantiate(
            self.fifo,
            "u_fifo",
            port_map={
                "clk": self.clk,
                "rst": self.rst,
                "din": self.din,
                "wr_en": self.wr_en,
                "rd_en": self.rd_en,
                "dout": self.dout,
                "full": self.full,
                "empty": self.empty,
                "count": self.count,
                "rd_rdy": self.rd_rdy,
            },
        )


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


def test_describe_verification_interface_rejects_raw_simmodule():
    with pytest.raises(TypeError, match="does not accept raw SimModule"):
        describe_verification_interface(_raw_accum_module())


def test_emit_python_reference_model_contains_wrapper_class():
    source = emit_python_reference_model(_accum_module())

    assert 'Generated Python reference model for "uvm_accum"' in source
    assert "class UvmAccumReferenceModel:" in source
    assert "rtlgen_ref_runtime.py" in source
    assert "self._sim = PythonSimulator(build_uvm_accum_module())" in source
    assert "def predict(self, transaction: Mapping[str, int]) -> Dict[str, int]:" in source
    assert "def predict_clocks(self, transaction: Mapping[str, int], active_domains) -> Dict[str, int]:" in source
    assert "def predict_batch(self, transactions):" in source
    assert "self._sim.run_batch(rows)" in source


def test_emit_python_reference_model_supports_multi_clock_modules():
    source = emit_python_reference_model(_multi_clock_ref_module())

    assert 'Generated Python reference model for "uvm_multiclk_ref"' in source
    assert "ClockDomain(name='wr_clk', reset_signal='wr_rst')" in source
    assert "ClockDomain(name='rd_clk', reset_signal='rd_rst')" in source
    assert "clock_domain='wr_clk'" in source
    assert "clock_domain='rd_clk'" in source
    assert "def predict_clocks(self, transaction: Mapping[str, int], active_domains) -> Dict[str, int]:" in source


def test_python_uvm_accepts_declared_clock_domain_aliases():
    from rtlgen.verify import PythonUvmSequenceItem, run_python_uvm_test

    report = run_python_uvm_test(
        DslMultiClockMailbox(),
        (
            PythonUvmSequenceItem(
                inputs={"wr_rst": 1, "rd_rst": 1},
                active_domains=("write", "read"),
                label="reset",
            ),
            PythonUvmSequenceItem(
                inputs={"wr_en": 1, "din": 9},
                active_domains=("write",),
                label="write0",
            ),
            PythonUvmSequenceItem(
                inputs={"rd_en": 1},
                active_domains=("read",),
                label="read0",
            ),
        ),
        name="python_uvm_declared_domain_aliases",
    )

    assert report.passed is True
    assert report.traces[0].active_domains == ("write", "read")


def test_emit_python_reference_model_preserves_declared_clock_domain_metadata():
    source = emit_python_reference_model(DslMultiClockMailbox())

    assert "ClockDomain(name='write', clock_signal='wr_clk', reset_signal='wr_rst', aliases=('wr_clk',))" in source
    assert "ClockDomain(name='read', clock_signal='rd_clk', reset_signal='rd_rst', aliases=('rd_clk',))" in source
    assert "clock_domain='write'" in source
    assert "clock_domain='read'" in source


def test_generate_uvm_collateral_uses_domain_aliases_for_steps_and_clock_signals_for_ports():
    collateral = generate_uvm_collateral(
        DslMultiClockMailbox(),
        interface_name="mc_if",
        directed_sequence=(
            UvmSequenceStep(inputs={"wr_rst": 1, "rd_rst": 1}, active_domains=("write", "read"), label="reset"),
            UvmSequenceStep(inputs={"wr_en": 1, "din": 7}, active_domains=("write",), label="write0"),
        ),
    )
    artifact_map = collateral.artifact_map()
    seq_src = artifact_map["dsl_multi_clock_mailbox_smoke_seq.sv"]
    drv_src = artifact_map["dsl_multi_clock_mailbox_driver.sv"]
    if_src = artifact_map["mc_if.sv"]

    assert "req.rtlgen_active_write = 1'b1;" in seq_src
    assert "req.rtlgen_active_read = 1'b1;" in seq_src
    assert "vif.wr_clk = req.rtlgen_active_write;" in drv_src
    assert "vif.rd_clk = req.rtlgen_active_read;" in drv_src
    assert "logic wr_clk;" in if_src
    assert "logic rd_clk;" in if_src


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
    assert "rtlgen_ref_runtime.py" in artifact_map
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
    assert "rtlgen_predict(" in artifact_map["uvm_accum_scoreboard.sv"]
    assert 'rtlgen_predict("uvm_accum_ref_model.py", observed.rst_n, observed.inp, predicted_out);' in artifact_map[
        "uvm_accum_scoreboard.sv"
    ]
    assert "uvm_accum_ref_model.py" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "observed.rst_n, observed.inp, predicted_out" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "expected.out = predicted_out;" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "function void report_phase(uvm_phase phase);" in artifact_map["uvm_accum_scoreboard.sv"]
    assert '`uvm_info("UVM_ACCUM_SCOREBOARD", "scoreboard passed", UVM_LOW)' in artifact_map["uvm_accum_scoreboard.sv"]
    assert '`include "uvm_accum_if.sv"' in artifact_map["uvm_accum_uvm_pkg.sv"]
    assert 'import "DPI-C" context function void rtlgen_predict(' in artifact_map["uvm_accum_uvm_pkg.sv"]
    assert "def predict_flat(ref_model_path: str, *input_values: int):" in artifact_map["uvm_accum_dpi_bridge.py"]
    assert "void rtlgen_predict(" in artifact_map["uvm_accum_dpi_bridge.c"]
    assert "PyObject_CallObject" in artifact_map["uvm_accum_dpi_bridge.c"]
    assert "class PythonSimulator:" in artifact_map["rtlgen_ref_runtime.py"]

    written = write_uvm_collateral(collateral, tmp_path / "uvm_out")
    written_names = sorted(path.name for path in written)
    assert written_names == sorted(artifact_map)
    assert (tmp_path / "uvm_out" / "uvm_accum_ref_model.py").read_text(encoding="utf-8") == artifact_map[
        "uvm_accum_ref_model.py"
    ]
    assert (tmp_path / "uvm_out" / "rtlgen_ref_runtime.py").read_text(encoding="utf-8") == artifact_map[
        "rtlgen_ref_runtime.py"
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
    assert "rtlgen_ref_runtime.py" in artifact_map
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
    assert "rtlgen_ref_runtime.py" in written_names
    assert os.access(tmp_path / "uvm_runtime" / "run_vcs.sh", os.X_OK)
    assert (tmp_path / "uvm_runtime" / "rtlgen_ref_runtime.py").exists()
    assert (tmp_path / "uvm_runtime" / "rtlgen" / "sim" / "__init__.py").exists()


def test_generate_uvm_runtime_bundle_accepts_dsl_module():
    bundle = generate_uvm_runtime_bundle(DslAccum(), clock_name="clk")
    artifact_map = bundle.artifact_map()

    assert bundle.dut_module_name == "dsl_uvm_accum"
    assert "dsl_uvm_accum_dut.sv" in artifact_map
    assert "dsl_uvm_accum_top.sv" in artifact_map
    assert "module dsl_uvm_accum" in artifact_map["dsl_uvm_accum_dut.sv"]
    assert "req.randomize() with { rst == 1'b1; }" in artifact_map["dsl_uvm_accum_smoke_seq.sv"]
    assert "req.randomize() with { rst == 1'b0; }" in artifact_map["dsl_uvm_accum_smoke_seq.sv"]


def test_generate_uvm_runtime_bundle_preserves_sync_reset_semantics_for_dsl_dut():
    bundle = generate_uvm_runtime_bundle(
        DslMultiClockMailbox(),
        interface_name="dsl_multi_clock_mailbox_if",
        clock_name="wr_clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"wr_rst": 1, "rd_rst": 1},
                label="reset",
                active_domains=("write", "read"),
            ),
        ),
    )

    dut_source = bundle.artifact_map()["dsl_multi_clock_mailbox_dut.sv"]

    assert "always_ff @(posedge wr_clk)" in dut_source
    assert "always_ff @(posedge rd_clk)" in dut_source
    assert "or negedge wr_rst" not in dut_source
    assert "or negedge rd_rst" not in dut_source


def test_generate_uvm_runtime_bundle_preserves_async_low_reset_semantics_for_dsl_dut():
    bundle = generate_uvm_runtime_bundle(DslAsyncLowStorage(), clock_name="clk")

    dut_source = bundle.artifact_map()["dsl_async_low_storage_dut.sv"]

    assert "always_ff @(posedge clk or negedge rst_n)" in dut_source


def test_generate_uvm_runtime_bundle_accepts_dsl_latch_module(tmp_path):
    from rtlgen.tests.test_dsl_import import LatchPass

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
    assert 'rtlgen_predict("latchpass_ref_model.py"' in artifact_map["latchpass_scoreboard.sv"]

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
    assert "rtlgen_ref_runtime.py" in artifact_map
    assert "module EarphoneSRAM256K" in artifact_map["earphone_sram256k_dut.sv"]
    assert "req.randomize() with { rst_n == 1'b0; }" in artifact_map["earphone_sram256k_smoke_seq.sv"]
    assert "req.randomize() with { rst_n == 1'b1; }" in artifact_map["earphone_sram256k_smoke_seq.sv"]
    assert "logic [31:0] paddr;" in artifact_map["earphone_sram256k_if.sv"]
    assert "logic [31:0] pwdata;" in artifact_map["earphone_sram256k_if.sv"]
    assert "logic [31:0] prdata;" in artifact_map["earphone_sram256k_if.sv"]
    assert 'rtlgen_predict("earphone_sram256k_ref_model.py"' in artifact_map["earphone_sram256k_scoreboard.sv"]

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


def test_uvm_collateral_rejects_multi_clock_modules():
    module = DslMultiClockMailbox()

    with pytest.raises(ValueError) as excinfo:
        generate_uvm_collateral(module, clock_name="wr_clk")
    assert "requires directed_sequence with explicit active_domains" in str(excinfo.value)
    assert "Known clock domains: write, read" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        generate_uvm_runtime_bundle(module, clock_name="wr_clk")
    assert "requires directed_sequence with explicit active_domains" in str(excinfo.value)
    assert "Known clock domains: write, read" in str(excinfo.value)


def test_multiclock_uvm_collateral_requires_explicit_active_domains():
    module = DslMultiClockMailbox()

    with pytest.raises(ValueError) as excinfo:
        generate_uvm_collateral(
            module,
            clock_name="wr_clk",
            directed_sequence=(
                {"wr_rst": 1, "rd_rst": 1},
            ),
        )
    assert "must be UvmSequenceStep instances or structured step mappings with explicit active_domains" in str(excinfo.value)
    assert "Use UvmSequenceStep(..., active_domains=" in str(excinfo.value)


def test_multiclock_uvm_collateral_reports_known_clock_aliases_for_unknown_active_domains():
    with pytest.raises(ValueError) as excinfo:
        generate_uvm_collateral(
            DslMultiClockMailbox(),
            clock_name="wr_clk",
            directed_sequence=(
                UvmSequenceStep(
                    inputs={"wr_rst": 1, "rd_rst": 1},
                    active_domains=("bogus_clk",),
                    label="bad_step",
                ),
            ),
        )

    assert "unknown active_domains: bogus_clk" in str(excinfo.value)
    assert "Known clock domains: write, read" in str(excinfo.value)
    assert "Known clock aliases: wr_clk, rd_clk" in str(excinfo.value)


def test_generate_multiclock_uvm_collateral_emits_event_driven_artifacts():
    collateral = generate_uvm_collateral(
        DslMultiClockMailbox(),
        clock_name="wr_clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"wr_rst": 1, "rd_rst": 1},
                label="reset",
                active_domains=("write", "read"),
            ),
            UvmSequenceStep(
                inputs={"wr_en": 1, "din": 0x11},
                label="write0",
                active_domains=("write",),
            ),
            UvmSequenceStep(
                inputs={"rd_en": 1},
                label="read0",
                active_domains=("read",),
            ),
        ),
    )

    artifact_map = collateral.artifact_map()
    seq_source = artifact_map["dsl_multi_clock_mailbox_smoke_seq.sv"]
    if_source = artifact_map["dsl_multi_clock_mailbox_if.sv"]
    driver_source = artifact_map["dsl_multi_clock_mailbox_driver.sv"]
    monitor_source = artifact_map["dsl_multi_clock_mailbox_monitor.sv"]
    scoreboard_source = artifact_map["dsl_multi_clock_mailbox_scoreboard.sv"]
    dpi_py_source = artifact_map["dsl_multi_clock_mailbox_dpi_bridge.py"]

    assert "interface dsl_multi_clock_mailbox_if;" in if_source
    assert "logic wr_clk;" in if_source
    assert "logic rd_clk;" in if_source
    assert "logic rtlgen_active_write;" in if_source
    assert "logic rtlgen_active_read;" in if_source
    assert "event rtlgen_step_done;" in if_source

    assert 'create("reset")' in seq_source
    assert "req.rtlgen_active_write = 1'b1;" in seq_source
    assert "req.rtlgen_active_read = 1'b1;" in seq_source
    assert "req.rtlgen_active_read = 1'b0;" in seq_source

    assert "vif.wr_clk = req.rtlgen_active_write;" in driver_source
    assert "vif.rd_clk = req.rtlgen_active_read;" in driver_source
    assert "-> vif.rtlgen_step_done;" in driver_source

    assert "@(vif.rtlgen_step_done);" in monitor_source
    assert "txn.rtlgen_active_write = vif.rtlgen_active_write;" in monitor_source

    assert "observed.rtlgen_active_write" in scoreboard_source
    assert "observed.rtlgen_active_read" in scoreboard_source

    assert "ACTIVE_DOMAIN_FLAGS = ('rtlgen_active_write', 'rtlgen_active_read')" in dpi_py_source
    assert "outputs = model.predict_clocks(transaction, tuple(active_domains))" in dpi_py_source


def test_generate_multiclock_uvm_collateral_accepts_structured_directed_steps():
    collateral = generate_uvm_collateral(
        DslMultiClockMailbox(),
        clock_name="wr_clk",
        directed_sequence=(
            {
                "inputs": {"wr_rst": 1, "rd_rst": 1},
                "label": "reset",
                "active_domains": ("wr_clk", "rd_clk"),
            },
            {
                "inputs": {"wr_en": 1, "din": 0x11},
                "label": "write0",
                "active_domains": ("wr_clk",),
            },
            {
                "inputs": {"rd_en": 1},
                "label": "read0",
                "active_domains": ("rd_clk",),
            },
        ),
    )

    seq_source = collateral.artifact_map()["dsl_multi_clock_mailbox_smoke_seq.sv"]

    assert "create(\"reset\")" in seq_source
    assert "req.rtlgen_active_write = 1'b1;" in seq_source
    assert "req.rtlgen_active_read = 1'b1;" in seq_source
    assert "create(\"write0\")" in seq_source
    assert "create(\"read0\")" in seq_source


def test_generate_multiclock_uvm_collateral_accepts_mapping_active_domains():
    collateral = generate_uvm_collateral(
        DslMultiClockMailbox(),
        clock_name="wr_clk",
        directed_sequence=(
            {
                "inputs": {"wr_rst": 1, "rd_rst": 1},
                "label": "reset",
                "active_domains": {"write": True, "read": True},
            },
            {
                "inputs": {"wr_en": 1, "din": 0x11},
                "label": "write0",
                "active_domains": {"write": True, "read": False},
            },
            {
                "inputs": {"rd_en": 1},
                "label": "read0",
                "active_domains": {"write": False, "read": True},
            },
        ),
    )

    seq_source = collateral.artifact_map()["dsl_multi_clock_mailbox_smoke_seq.sv"]

    assert "create(\"reset\")" in seq_source
    assert "req.rtlgen_active_write = 1'b1;" in seq_source
    assert "req.rtlgen_active_read = 1'b1;" in seq_source
    assert "create(\"write0\")" in seq_source
    assert "req.rtlgen_active_read = 1'b0;" in seq_source
    assert "create(\"read0\")" in seq_source


def test_generate_multiclock_uvm_runtime_bundle_emits_event_driven_top():
    bundle = generate_uvm_runtime_bundle(
        DslMultiClockMailbox(),
        clock_name="wr_clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"wr_rst": 1, "rd_rst": 1},
                active_domains=("write", "read"),
            ),
        ),
    )

    artifact_map = bundle.artifact_map()
    top_source = artifact_map["dsl_multi_clock_mailbox_top.sv"]
    dpi_c_source = artifact_map["dsl_multi_clock_mailbox_dpi_bridge.c"]

    assert "dsl_multi_clock_mailbox_if vif();" in top_source
    assert "always #5 clk = ~clk;" not in top_source
    assert ".wr_clk(vif.wr_clk)" in top_source
    assert ".rd_clk(vif.rd_clk)" in top_source
    assert 'uvm_config_db#(virtual dsl_multi_clock_mailbox_if)::set(null, "*", "vif", vif);' in top_source

    assert "const char* ref_model_path" in dpi_c_source
    assert "rtlgen_active_write" in dpi_c_source
    assert "rtlgen_active_read" in dpi_c_source


def test_generate_ready_valid_async_bridge_uvm_collateral_emits_multiclock_artifacts():
    collateral = generate_uvm_collateral(
        DslReadyValidAsyncBridgeHarness(),
        clock_name="wr_clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"wr_rst": 1, "rd_rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0},
                active_domains=("wr_clk", "rd_clk"),
                label="reset",
            ),
            UvmSequenceStep(
                inputs={"wr_rst": 0, "rd_rst": 0, "in_data": 0x11, "in_valid": 1, "out_ready": 0},
                active_domains=("wr_clk",),
                label="push0",
            ),
            UvmSequenceStep(
                inputs={"in_data": 0, "in_valid": 0, "out_ready": 1},
                active_domains=("rd_clk",),
                label="pop0",
            ),
        ),
    )

    artifact_map = collateral.artifact_map()
    seq_source = artifact_map["dsl_ready_valid_async_bridge_harness_smoke_seq.sv"]
    if_source = artifact_map["dsl_ready_valid_async_bridge_harness_if.sv"]
    driver_source = artifact_map["dsl_ready_valid_async_bridge_harness_driver.sv"]
    scoreboard_source = artifact_map["dsl_ready_valid_async_bridge_harness_scoreboard.sv"]

    assert "logic wr_clk;" in if_source
    assert "logic rd_clk;" in if_source
    assert "logic rtlgen_active_wr_clk;" in if_source
    assert "logic rtlgen_active_rd_clk;" in if_source
    assert "req.rtlgen_active_wr_clk = 1'b1;" in seq_source
    assert "req.rtlgen_active_rd_clk = 1'b1;" in seq_source
    assert "vif.wr_clk = req.rtlgen_active_wr_clk;" in driver_source
    assert "vif.rd_clk = req.rtlgen_active_rd_clk;" in driver_source
    assert "observed.rtlgen_active_wr_clk" in scoreboard_source
    assert "observed.rtlgen_active_rd_clk" in scoreboard_source


def test_generate_async_fifo_uvm_collateral_emits_multiclock_artifacts():
    collateral = generate_uvm_collateral(
        DslAsyncFifoHarness(),
        clock_name="wr_clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"wr_rst": 1, "rd_rst": 1, "din": 0, "wr_en": 0, "rd_en": 0},
                active_domains=("wr_clk", "rd_clk"),
                label="reset",
            ),
            UvmSequenceStep(
                inputs={"wr_rst": 0, "rd_rst": 0, "din": 0x11, "wr_en": 1, "rd_en": 0},
                active_domains=("wr_clk",),
                label="push0",
            ),
            UvmSequenceStep(
                inputs={"din": 0, "wr_en": 0, "rd_en": 1},
                active_domains=("rd_clk",),
                label="pop0",
            ),
        ),
    )

    artifact_map = collateral.artifact_map()
    seq_source = artifact_map["dsl_async_fifo_harness_smoke_seq.sv"]
    if_source = artifact_map["dsl_async_fifo_harness_if.sv"]
    driver_source = artifact_map["dsl_async_fifo_harness_driver.sv"]
    scoreboard_source = artifact_map["dsl_async_fifo_harness_scoreboard.sv"]

    assert "logic wr_clk;" in if_source
    assert "logic rd_clk;" in if_source
    assert "logic rtlgen_active_wr_clk;" in if_source
    assert "logic rtlgen_active_rd_clk;" in if_source
    assert "req.rtlgen_active_wr_clk = 1'b1;" in seq_source
    assert "req.rtlgen_active_rd_clk = 1'b1;" in seq_source
    assert "vif.wr_clk = req.rtlgen_active_wr_clk;" in driver_source
    assert "vif.rd_clk = req.rtlgen_active_rd_clk;" in driver_source
    assert "observed.rtlgen_active_wr_clk" in scoreboard_source
    assert "observed.rtlgen_active_rd_clk" in scoreboard_source


def test_generate_async_fifo_uvm_runtime_bundle_emits_event_driven_top():
    bundle = generate_uvm_runtime_bundle(
        DslAsyncFifoHarness(),
        clock_name="wr_clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"wr_rst": 1, "rd_rst": 1, "din": 0, "wr_en": 0, "rd_en": 0},
                active_domains=("wr_clk", "rd_clk"),
                label="reset",
            ),
        ),
    )

    artifact_map = bundle.artifact_map()
    top_source = artifact_map["dsl_async_fifo_harness_top.sv"]
    dpi_c_source = artifact_map["dsl_async_fifo_harness_dpi_bridge.c"]

    assert "dsl_async_fifo_harness_if vif();" in top_source
    assert ".wr_clk(vif.wr_clk)" in top_source
    assert ".rd_clk(vif.rd_clk)" in top_source
    assert "rtlgen_active_wr_clk" in dpi_c_source
    assert "rtlgen_active_rd_clk" in dpi_c_source


def test_generate_sync_fifo_uvm_collateral_emits_single_clock_artifacts():
    collateral = generate_uvm_collateral(
        DslSyncFifoHarness(),
        clock_name="clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"rst": 1, "din": 0, "wr_en": 0, "rd_en": 0},
                label="reset",
            ),
            UvmSequenceStep(
                inputs={"rst": 0, "din": 0x11, "wr_en": 1, "rd_en": 0},
                label="push0",
            ),
        ),
    )

    artifact_map = collateral.artifact_map()
    seq_source = artifact_map["dsl_sync_fifo_harness_smoke_seq.sv"]
    if_source = artifact_map["dsl_sync_fifo_harness_if.sv"]
    scoreboard_source = artifact_map["dsl_sync_fifo_harness_scoreboard.sv"]

    assert "interface dsl_sync_fifo_harness_if(input logic clk);" in if_source
    assert "logic [7:0] din;" in if_source
    assert "logic [7:0] dout;" in if_source
    assert 'create("push0")' in seq_source
    assert "req.din = 8'h11;" in seq_source
    assert "req.wr_en = 1'b1;" in seq_source
    assert 'rtlgen_predict("dsl_sync_fifo_harness_ref_model.py"' in scoreboard_source


def test_generate_sync_fifo_uvm_runtime_bundle_emits_single_clock_top():
    bundle = generate_uvm_runtime_bundle(
        DslSyncFifoHarness(),
        clock_name="clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"rst": 1, "din": 0, "wr_en": 0, "rd_en": 0},
                label="reset",
            ),
        ),
    )

    artifact_map = bundle.artifact_map()
    top_source = artifact_map["dsl_sync_fifo_harness_top.sv"]
    dut_source = artifact_map["dsl_sync_fifo_harness_dut.sv"]

    assert "dsl_sync_fifo_harness_if vif(clk);" in top_source
    assert "always #5 clk = ~clk;" in top_source
    assert ".clk(clk)" in top_source
    assert "module dsl_sync_fifo_harness" in dut_source


def test_generate_skid_buffer_uvm_collateral_emits_single_clock_artifacts():
    collateral = generate_uvm_collateral(
        SkidBuffer(8),
        clock_name="clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 1},
                label="reset",
            ),
            UvmSequenceStep(
                inputs={"rst": 0, "in_data": 0x12, "in_valid": 1, "out_ready": 0},
                label="stall0",
            ),
        ),
    )

    artifact_map = collateral.artifact_map()
    seq_source = artifact_map["skidbuffer_smoke_seq.sv"]
    if_source = artifact_map["skidbuffer_if.sv"]
    scoreboard_source = artifact_map["skidbuffer_scoreboard.sv"]

    assert "interface skidbuffer_if(input logic clk);" in if_source
    assert "logic [7:0] in_data;" in if_source
    assert "logic [7:0] out_data;" in if_source
    assert 'create("stall0")' in seq_source
    assert "req.in_data = 8'h12;" in seq_source
    assert "req.in_valid = 1'b1;" in seq_source
    assert "req.out_ready = 1'b0;" in seq_source
    assert 'rtlgen_predict("skidbuffer_ref_model.py"' in scoreboard_source


def test_generate_skid_buffer_uvm_runtime_bundle_emits_single_clock_top():
    bundle = generate_uvm_runtime_bundle(
        SkidBuffer(8),
        clock_name="clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 1},
                label="reset",
            ),
        ),
    )

    artifact_map = bundle.artifact_map()
    top_source = artifact_map["skidbuffer_top.sv"]
    dut_source = artifact_map["skidbuffer_dut.sv"]

    assert "skidbuffer_if vif(clk);" in top_source
    assert "always #5 clk = ~clk;" in top_source
    assert ".clk(clk)" in top_source
    assert "module SkidBuffer" in dut_source


def test_generate_ready_valid_register_uvm_collateral_emits_single_clock_artifacts():
    collateral = generate_uvm_collateral(
        ReadyValidRegister(width=8),
        clock_name="clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 1},
                label="reset",
            ),
            UvmSequenceStep(
                inputs={"rst": 0, "in_data": 0x34, "in_valid": 1, "out_ready": 1},
                label="push0",
            ),
        ),
    )

    artifact_map = collateral.artifact_map()
    seq_source = artifact_map["readyvalidregister_smoke_seq.sv"]
    if_source = artifact_map["readyvalidregister_if.sv"]
    scoreboard_source = artifact_map["readyvalidregister_scoreboard.sv"]

    assert "interface readyvalidregister_if(input logic clk);" in if_source
    assert "logic [7:0] in_data;" in if_source
    assert "logic [7:0] out_data;" in if_source
    assert 'create("push0")' in seq_source
    assert "req.in_data = 8'h34;" in seq_source
    assert "req.in_valid = 1'b1;" in seq_source
    assert "req.out_ready = 1'b1;" in seq_source
    assert 'rtlgen_predict("readyvalidregister_ref_model.py"' in scoreboard_source


def test_generate_ready_valid_register_uvm_runtime_bundle_emits_single_clock_top():
    bundle = generate_uvm_runtime_bundle(
        ReadyValidRegister(width=8),
        clock_name="clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 1},
                label="reset",
            ),
        ),
    )

    artifact_map = bundle.artifact_map()
    top_source = artifact_map["readyvalidregister_top.sv"]
    dut_source = artifact_map["readyvalidregister_dut.sv"]

    assert "readyvalidregister_if vif(clk);" in top_source
    assert "always #5 clk = ~clk;" in top_source
    assert ".clk(clk)" in top_source
    assert "module ReadyValidRegister" in dut_source


def test_generate_ready_valid_fifo_uvm_collateral_emits_single_clock_artifacts():
    collateral = generate_uvm_collateral(
        ReadyValidFIFO(width=8, depth=2),
        clock_name="clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 1},
                label="reset",
            ),
            UvmSequenceStep(
                inputs={"rst": 0, "in_data": 0x56, "in_valid": 1, "out_ready": 0},
                label="fill0",
            ),
        ),
    )

    artifact_map = collateral.artifact_map()
    seq_source = artifact_map["readyvalidfifo_smoke_seq.sv"]
    if_source = artifact_map["readyvalidfifo_if.sv"]
    scoreboard_source = artifact_map["readyvalidfifo_scoreboard.sv"]

    assert "interface readyvalidfifo_if(input logic clk);" in if_source
    assert "logic [7:0] in_data;" in if_source
    assert "logic [1:0] level;" in if_source
    assert 'create("fill0")' in seq_source
    assert "req.in_data = 8'h56;" in seq_source
    assert "req.in_valid = 1'b1;" in seq_source
    assert "req.out_ready = 1'b0;" in seq_source
    assert 'rtlgen_predict("readyvalidfifo_ref_model.py"' in scoreboard_source


def test_generate_ready_valid_fifo_uvm_runtime_bundle_emits_single_clock_top():
    bundle = generate_uvm_runtime_bundle(
        ReadyValidFIFO(width=8, depth=2),
        clock_name="clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 1},
                label="reset",
            ),
        ),
    )

    artifact_map = bundle.artifact_map()
    top_source = artifact_map["readyvalidfifo_top.sv"]
    dut_source = artifact_map["readyvalidfifo_dut.sv"]

    assert "readyvalidfifo_if vif(clk);" in top_source
    assert "always #5 clk = ~clk;" in top_source
    assert ".clk(clk)" in top_source
    assert "module ReadyValidFIFO" in dut_source


def test_generate_uvm_runtime_bundle_rejects_raw_simmodule():
    with pytest.raises(TypeError, match="does not accept raw SimModule"):
        generate_uvm_runtime_bundle(_raw_accum_module(), interface_name="uvm_accum_if", clock_name="clk")


def test_generate_uvm_runtime_bundle_requires_authored_dsl_module_when_dut_source_missing():
    with pytest.raises(TypeError, match="requires the original DSL Module"):
        generate_uvm_runtime_bundle(_accum_module(), interface_name="uvm_accum_if", clock_name="clk")


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
    assert report.active_domains == ()


def test_generated_reference_model_can_run_explicit_multi_clock_predictions(tmp_path):
    source = emit_python_reference_model(_multi_clock_ref_module())
    runtime = Path(__file__).resolve().parents[1] / "verify" / "ref_runtime.py"
    out_dir = tmp_path / "uvm_multiclk_ref"
    out_dir.mkdir()
    ref_model_path = out_dir / "uvm_multiclk_ref_ref_model.py"
    runtime_path = out_dir / "rtlgen_ref_runtime.py"
    ref_model_path.write_text(source, encoding="utf-8")
    runtime_path.write_text(runtime.read_text(encoding="utf-8"), encoding="utf-8")

    model = load_generated_reference_model(ref_model_path)
    model.reset()
    assert model.predict_clocks(
        {"wr_rst": 1, "rd_rst": 1},
        ("wr_clk", "rd_clk"),
    ) == {"out": 0}
    assert model.predict_clocks({"wr_en": 1}, ("wr_clk",)) == {"out": 0}
    assert model.predict_clocks({"rd_en": 1}, ("rd_clk",)) == {"out": 1}

    report = smoke_test_generated_reference_model(
        ref_model_path,
        inputs={"wr_en": 1},
        active_domains=("wr_clk",),
    )
    assert report.predicted == {"out": 0}
    assert report.batched_predicted is None
    assert report.active_domains == ("wr_clk",)


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


def test_verification_collateral_accepts_dsl_module():
    interface = describe_verification_interface(DslAccum())
    source = emit_python_reference_model(DslAccum())
    collateral = generate_uvm_collateral(DslAccum(), interface_name="dsl_uvm_if", clock_name="clk")

    assert interface.module_name == "dsl_uvm_accum"
    assert interface.reset_signal == "rst"
    assert interface.reset_active_low is False
    assert [port.name for port in interface.inputs] == ["clk", "rst", "inp"]
    assert "outputs_post_state=True" in source
    assert collateral.reference_model_class == "DslUvmAccumReferenceModel"
    assert "dsl_uvm_if.sv" in collateral.artifact_map()


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
        memory_writes=(
            MemoryWrite(
                "mem",
                SignalRef("addr"),
                SignalRef("din"),
                enable=SignalRef("we"),
                source_file="uvm_mem.py",
                source_line=19,
            ),
        ),
        outputs_post_state=True,
    )

    source = emit_python_reference_model(_lowered(module))
    assert "MemoryReadExpr('mem', SignalRef('addr'))" in source
    assert "MemoryWrite('mem', SignalRef('addr'), SignalRef('din'), enable=SignalRef('we')" in source
    assert "source_file='uvm_mem.py'" in source
    assert "source_line=19" in source


def test_emit_python_reference_model_renders_byte_enable_memory_support():
    rendered_memory = _render_memory(
        Memory(
            "mem",
            width=32,
            depth=4,
            init=(1, 2, 3, 4),
            byte_enable_granularity=8,
        )
    )
    rendered_write = _render_memory_write(
        MemoryWrite(
            "mem",
            SignalRef("addr"),
            SignalRef("din"),
            enable=SignalRef("we"),
            byte_enable=SignalRef("be"),
        )
    )

    assert "byte_enable_granularity=8" in rendered_memory
    assert "byte_enable=SignalRef('be')" in rendered_write


def test_emit_python_reference_model_renders_read_first_memory_policy():
    module = SimModule(
        name="uvm_mem_read_first",
        signals=(
            Signal("we", width=1, kind="input"),
            Signal("addr", width=2, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("dout", width=8, kind="output"),
        ),
        assignments=(Assignment("dout", MemoryReadExpr("mem", SignalRef("addr"))),),
        outputs=("dout",),
        memories=(Memory("mem", width=8, depth=4, init=(1, 2, 3, 4), read_during_write="read_first"),),
        memory_writes=(MemoryWrite("mem", SignalRef("addr"), SignalRef("din"), enable=SignalRef("we")),),
        outputs_post_state=True,
    )

    source = emit_python_reference_model(_lowered(module))
    assert "read_during_write='read_first'" in source


def test_render_memory_includes_storage_contract_metadata():
    rendered = _render_memory(
        Memory(
            "mem",
            width=8,
            depth=4,
            init=(1, 2, 3, 4),
            read_ports=2,
            write_ports=1,
            read_style="sync",
            read_latency=1,
        )
    )

    assert "read_ports=2" in rendered
    assert "read_style='sync'" in rendered
    assert "read_latency=1" in rendered


def test_render_memory_includes_byte_enable_storage_metadata():
    rendered = _render_memory(
        Memory(
            "mem",
            width=32,
            depth=4,
            byte_enable_granularity=8,
        )
    )

    assert "byte_enable_granularity=8" in rendered


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
        _lowered(module),
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


def test_verification_collateral_accepts_dsl_storage_module():
    interface = describe_verification_interface(DslStorage())
    source = emit_python_reference_model(DslStorage())

    assert interface.module_name == "dsl_storage"
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


def test_verification_collateral_accepts_apb_register_bank():
    interface = describe_verification_interface(APBRegisterBank(depth=8))
    collateral = generate_uvm_collateral(
        APBRegisterBank(depth=8),
        interface_name="apbregisterbank_if",
        clock_name="pclk",
    )
    artifact_map = collateral.artifact_map()

    assert interface.module_name == "APBRegisterBank"
    assert interface.reset_signal == "presetn"
    assert interface.reset_active_low is True
    assert [port.name for port in interface.inputs[:5]] == ["pclk", "presetn", "psel", "penable", "pwrite"]
    assert [port.name for port in interface.outputs] == ["prdata", "pready", "pslverr"]
    assert "apbregisterbank_if.sv" in artifact_map
    assert "apbregisterbank_ref_model.py" in artifact_map
    assert "logic presetn;" in artifact_map["apbregisterbank_if.sv"]
    assert "logic [31:0] paddr;" in artifact_map["apbregisterbank_if.sv"]
    assert "logic [31:0] prdata;" in artifact_map["apbregisterbank_if.sv"]
    assert "byte_enable_granularity=8" in artifact_map["apbregisterbank_ref_model.py"]
    assert "MemoryWrite('regmem'" in artifact_map["apbregisterbank_ref_model.py"]


def test_generate_uvm_runtime_bundle_accepts_apb_register_bank():
    bundle = generate_uvm_runtime_bundle(APBRegisterBank(depth=8), clock_name="pclk")
    artifact_map = bundle.artifact_map()

    assert bundle.module_name == "APBRegisterBank"
    assert bundle.dut_module_name == "APBRegisterBank"
    assert "apbregisterbank_dut.sv" in artifact_map
    assert "apbregisterbank_top.sv" in artifact_map
    assert "module APBRegisterBank" in artifact_map["apbregisterbank_dut.sv"]
    assert "req.randomize() with { presetn == 1'b0; }" in artifact_map["apbregisterbank_smoke_seq.sv"]
    assert "req.randomize() with { presetn == 1'b1; }" in artifact_map["apbregisterbank_smoke_seq.sv"]


def test_generate_uvm_runtime_bundle_accepts_protocol_transfer_bridge_for_apb():
    directed_sequence = protocol_transfers_to_uvm_sequence_steps(
        "apb",
        (ApbTransfer(addr=0x10, write=False, expected_rdata=0x1234, label="apb_rd"),),
    )
    bundle = generate_uvm_runtime_bundle(
        APBRegisterBank(depth=8),
        clock_name="pclk",
        directed_sequence=directed_sequence,
    )
    artifact_map = bundle.artifact_map()

    assert "apbregisterbank_smoke_seq.sv" in artifact_map
    assert "req.paddr = 32'h10;" in artifact_map["apbregisterbank_smoke_seq.sv"]
    assert "req.psel = 1'b1;" in artifact_map["apbregisterbank_smoke_seq.sv"]
    assert "req.penable = 1'b0;" in artifact_map["apbregisterbank_smoke_seq.sv"]


def test_generate_uvm_runtime_bundle_accepts_protocol_transfer_bridge_for_axilite():
    directed_sequence = protocol_transfers_to_uvm_sequence_steps(
        "axilite",
        (AxiLiteTransfer(addr=0x10, write=False, expected_rdata=0x1234, label="axil_rd"),),
    )
    bundle = generate_uvm_runtime_bundle(
        AXI4LiteRegisterBank(depth=8),
        clock_name="clk",
        directed_sequence=directed_sequence,
    )
    artifact_map = bundle.artifact_map()

    assert "axi4literegisterbank_smoke_seq.sv" in artifact_map
    assert "req.araddr = 32'h10;" in artifact_map["axi4literegisterbank_smoke_seq.sv"]
    assert "req.arvalid = 1'b1;" in artifact_map["axi4literegisterbank_smoke_seq.sv"]
    assert "req.rready = 1'b1;" in artifact_map["axi4literegisterbank_smoke_seq.sv"]
    assert "req.awvalid = 1'b0;" in artifact_map["axi4literegisterbank_smoke_seq.sv"]


def test_generate_uvm_runtime_bundle_accepts_protocol_transfer_bridge_for_wishbone_clocked():
    directed_sequence = protocol_transfers_to_uvm_sequence_steps(
        "wishbone_clocked",
        (WishboneTransfer(addr=0x10, write=False, expected_rdata=0x1234, label="wb_rd"),),
    )
    bundle = generate_uvm_runtime_bundle(
        WishboneRegisterBank(depth=8),
        clock_name="clk_i",
        directed_sequence=directed_sequence,
    )
    artifact_map = bundle.artifact_map()

    assert "wishboneregisterbank_smoke_seq.sv" in artifact_map
    assert "req.adr_i = 32'h10;" in artifact_map["wishboneregisterbank_smoke_seq.sv"]
    assert "req.cyc_i = 1'b1;" in artifact_map["wishboneregisterbank_smoke_seq.sv"]
    assert "req.stb_i = 1'b1;" in artifact_map["wishboneregisterbank_smoke_seq.sv"]
    assert 'create("wb_rd_gap")' in artifact_map["wishboneregisterbank_smoke_seq.sv"]


def test_generate_uvm_runtime_bundle_accepts_protocol_transfer_bridge_for_axistream_with_explicit_dut_source():
    module = _lowered(
        SimModule(
            name="uvm_axis_ready",
            signals=(
                Signal("clk", width=1, kind="input"),
                Signal("rst", width=1, kind="input"),
                Signal("tdata", width=16, kind="input"),
                Signal("tvalid", width=1, kind="input"),
                Signal("tlast", width=1, kind="input"),
                Signal("tkeep", width=2, kind="input"),
                Signal("tready", width=1, kind="output"),
            ),
            assignments=(Assignment("tready", SignalRef("tvalid")),),
            outputs=("tready",),
        )
    )
    directed_sequence = protocol_transfers_to_uvm_sequence_steps(
        "axis",
        (AxiStreamTransfer(data=0xABCD, last=1, keep=0x3, expected_ready=1, label="axis0"),),
    )
    bundle = generate_uvm_runtime_bundle(
        module,
        clock_name="clk",
        dut_module_name="uvm_axis_ready",
        dut_source=_axis_ready_dut_sv(),
        directed_sequence=directed_sequence,
    )
    artifact_map = bundle.artifact_map()

    assert "uvm_axis_ready_smoke_seq.sv" in artifact_map
    assert "req.tdata = 16'habcd;" in artifact_map["uvm_axis_ready_smoke_seq.sv"].lower()
    assert "req.tvalid = 1'b1;" in artifact_map["uvm_axis_ready_smoke_seq.sv"]
    assert "req.tlast = 1'b1;" in artifact_map["uvm_axis_ready_smoke_seq.sv"]
    assert "req.tkeep = 2'h3;" in artifact_map["uvm_axis_ready_smoke_seq.sv"]


def test_generated_reference_model_loads_runtime_via_env_override(tmp_path):
    """Finding #3: a reference model separated from its runtime sibling must
    still load when RTLGEN_REF_RUNTIME_PATH points at the runtime file."""
    bundle = generate_uvm_runtime_bundle(
        _accum_module(),
        clock_name="clk",
        dut_module_name="uvm_accum",
        dut_source=_accum_dut_sv(),
    )
    bundle_dir = tmp_path / "bundle"
    write_uvm_runtime_bundle(bundle, bundle_dir, include_runtime_package=False)

    runtime_src = bundle_dir / "rtlgen_ref_runtime.py"
    assert runtime_src.exists()

    # Move the reference model into its own directory without the runtime sibling.
    isolated_dir = tmp_path / "isolated_model"
    isolated_dir.mkdir()
    ref_model_src = bundle_dir / "uvm_accum_ref_model.py"
    isolated_ref_model = isolated_dir / "uvm_accum_ref_model.py"
    shutil.copy(ref_model_src, isolated_ref_model)

    # Without the override, the generated loader cannot find the runtime sibling.
    saved = os.environ.pop("RTLGEN_REF_RUNTIME_PATH", None)
    try:
        with pytest.raises((ImportError, FileNotFoundError)):
            load_generated_reference_model(isolated_ref_model)
    finally:
        if saved is not None:
            os.environ["RTLGEN_REF_RUNTIME_PATH"] = saved

    # With the runtime_path override, the model loads and predicts correctly.
    model = load_generated_reference_model(
        isolated_ref_model, runtime_path=runtime_src
    )
    model.reset()
    predicted = model.predict({"clk": 0, "rst_n": 0, "inp": 5})
    assert predicted == {"out": 8}


def test_emit_python_reference_model_emits_env_runtime_lookup():
    """The generated loader source must honor RTLGEN_REF_RUNTIME_PATH."""
    source = emit_python_reference_model(_accum_module())
    assert "RTLGEN_REF_RUNTIME_PATH" in source
    assert "Path(__file__).with_name" in source


def test_iverilog_probe_report_surfaces_width_mismatch_warnings():
    """Finding #5: warning lines in stderr must be surfaced as a property so
    width-mismatch diagnostics are not silently buried in a clean compile."""
    from rtlgen.verify import IverilogCollateralProbeReport

    report = IverilogCollateralProbeReport(
        collateral_dir=Path("/tmp/probe"),
        interface_source=Path("/tmp/probe/dut_if.sv"),
        package_source=Path("/tmp/probe/pkg.sv"),
        interface_compile_ok=True,
        package_compile_ok=True,
        interface_returncode=0,
        package_returncode=0,
        interface_stdout="",
        interface_stderr="dut_if.sv:5: warning: Port 0 (out_warp) of dut expects 1 bits, got 2.\n",
        package_stdout="",
        package_stderr="pkg.sv:12: some other note\n",
        skipped_reason=None,
    )
    assert report.has_warnings is True
    assert report.clean is False
    assert len(report.warnings) == 1
    assert "out_warp" in report.warnings[0]


def test_iverilog_probe_report_clean_when_no_warnings():
    """A successful compile with no warning lines is clean."""
    from rtlgen.verify import IverilogCollateralProbeReport

    report = IverilogCollateralProbeReport(
        collateral_dir=Path("/tmp/probe"),
        interface_source=Path("/tmp/probe/dut_if.sv"),
        package_source=Path("/tmp/probe/pkg.sv"),
        interface_compile_ok=True,
        package_compile_ok=True,
        interface_returncode=0,
        package_returncode=0,
        interface_stdout="",
        interface_stderr="",
        package_stdout="",
        package_stderr="",
        skipped_reason=None,
    )
    assert report.has_warnings is False
    assert report.warnings == ()
    assert report.clean is True
