import importlib.util
from pathlib import Path

from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    Signal,
    SignalRef,
    SimModule,
)
from rtlgen_x.dsl import Array, Else, If, Input, Module, Output, Reg
from rtlgen_x.verify import (
    describe_verification_interface,
    emit_python_reference_model,
    generate_uvm_collateral,
    write_uvm_collateral,
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
    assert [port.name for port in interface.inputs] == ["clk", "rst_n", "inp"]
    assert [port.name for port in interface.outputs] == ["out"]
    assert interface.outputs[0].width == 8


def test_emit_python_reference_model_contains_wrapper_class():
    source = emit_python_reference_model(_accum_module())

    assert 'Generated Python reference model for "uvm_accum"' in source
    assert "class UvmAccumReferenceModel:" in source
    assert "self._sim = PythonSimulator(build_uvm_accum_module())" in source
    assert "def predict(self, transaction: Mapping[str, int]) -> Dict[str, int]:" in source


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
    assert "uvm_accum_ref_model.py" in artifact_map
    assert "uvm_accum_dpi_bridge.py" in artifact_map
    assert "uvm_accum_dpi_bridge.c" in artifact_map
    assert "interface uvm_accum_if(input logic clk);" in artifact_map["uvm_accum_if.sv"]
    assert "logic rst_n;" in artifact_map["uvm_accum_if.sv"]
    assert "logic [7:0] inp;" in artifact_map["uvm_accum_if.sv"]
    assert "logic [7:0] out;" in artifact_map["uvm_accum_if.sv"]
    assert "logic clk;" not in artifact_map["uvm_accum_if.sv"]
    assert "class uvm_accum_driver extends uvm_driver #(uvm_accum_txn);" in artifact_map["uvm_accum_driver.sv"]
    assert "class uvm_accum_sequencer extends uvm_sequencer #(uvm_accum_txn);" in artifact_map["uvm_accum_sequencer.sv"]
    assert "class uvm_accum_agent extends uvm_agent;" in artifact_map["uvm_accum_agent.sv"]
    assert "seq.start(env.agent.sequencer);" in artifact_map["uvm_accum_test.sv"]
    assert "class uvm_accum_scoreboard extends uvm_component;" in artifact_map["uvm_accum_scoreboard.sv"]
    assert 'import "DPI-C" context function void rtlgen_x_predict(' in artifact_map["uvm_accum_scoreboard.sv"]
    assert "rtlgen_x_predict(" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "uvm_accum_ref_model.py" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "observed.rst_n, observed.inp, predicted_out" in artifact_map["uvm_accum_scoreboard.sv"]
    assert "expected.out = predicted_out;" in artifact_map["uvm_accum_scoreboard.sv"]
    assert '`include "uvm_accum_if.sv"' in artifact_map["uvm_accum_uvm_pkg.sv"]
    assert "def predict_flat(ref_model_path: str, *input_values: int):" in artifact_map["uvm_accum_dpi_bridge.py"]
    assert "void rtlgen_x_predict(" in artifact_map["uvm_accum_dpi_bridge.c"]
    assert "PyObject_CallObject" in artifact_map["uvm_accum_dpi_bridge.c"]

    written = write_uvm_collateral(collateral, tmp_path / "uvm_out")
    written_names = sorted(path.name for path in written)
    assert written_names == sorted(artifact_map)
    assert (tmp_path / "uvm_out" / "uvm_accum_ref_model.py").read_text(encoding="utf-8") == artifact_map[
        "uvm_accum_ref_model.py"
    ]


def test_verification_collateral_accepts_legacy_dsl_module():
    interface = describe_verification_interface(LegacyAccum())
    source = emit_python_reference_model(LegacyAccum())
    collateral = generate_uvm_collateral(LegacyAccum(), interface_name="legacy_uvm_if", clock_name="clk")

    assert interface.module_name == "legacy_uvm_accum"
    assert interface.reset_signal is None
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


def test_verification_collateral_accepts_legacy_storage_module():
    interface = describe_verification_interface(LegacyStorage())
    source = emit_python_reference_model(LegacyStorage())

    assert interface.module_name == "legacy_storage"
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
    assert interface.reset_signal is None
    assert [port.name for port in interface.inputs[:4]] == ["clk", "rst_n", "paddr", "pwdata"]
    assert [port.name for port in interface.outputs] == ["prdata", "pready", "pslverr"]
    assert "earphone_sram_if.sv" in artifact_map
    assert "earphone_sram256k_ref_model.py" in artifact_map
    assert "logic [31:0] paddr;" in artifact_map["earphone_sram_if.sv"]
    assert "logic [31:0] prdata;" in artifact_map["earphone_sram_if.sv"]
    assert "Memory('mem', width=32, depth=65536" in artifact_map["earphone_sram256k_ref_model.py"]
    assert "MemoryWrite('mem'" in artifact_map["earphone_sram256k_ref_model.py"]
