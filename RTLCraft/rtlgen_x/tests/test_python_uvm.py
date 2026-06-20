import importlib.util
import json
from pathlib import Path

from rtlgen_x.dsl import Else, If, Input, Module, Output, Reg, build_compiled_simulator_from_legacy
from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    ConstExpr,
    CppBackendScaffold,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    Signal,
    SignalRef,
    SimModule,
    UnaryExpr,
)
from rtlgen_x.verify import (
    ApbTransfer,
    Axi4Transfer,
    AxiStreamTransfer,
    CsrTransfer,
    InterruptEvent,
    PythonUvmCoverage,
    PythonUvmSequenceItem,
    PythonUvmSequenceLibrary,
    WishboneTransfer,
    apb_sequence,
    axi4_sequence,
    axi_memory_reference_model,
    axistream_sequence,
    csr_reference_model,
    csr_sequence,
    dump_python_uvm_triage,
    interrupt_reference_model,
    interrupt_sequence,
    register_reference_model,
    run_python_uvm_test,
    wishbone_sequence,
)


def _accum_module() -> SimModule:
    return SimModule(
        name="python_uvm_accum",
        signals=(
            Signal("inp", width=8, kind="input"),
            Signal("acc", width=8, kind="state", init=3),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("acc"), SignalRef("inp"))),
            Assignment("acc", SignalRef("out"), phase="seq"),
        ),
        outputs=("out",),
    )


class LegacyPythonUvmAccum(Module):
    def __init__(self):
        super().__init__("legacy_python_uvm_accum")
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


def _load_external_module(rel_path: str, class_name: str):
    path = Path(__file__).resolve().parents[2] / rel_path
    spec = importlib.util.spec_from_file_location(f"python_uvm_{path.stem}_{class_name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, class_name)()


def _stimulus_only(sequence):
    return tuple(
        PythonUvmSequenceItem(
            inputs=dict(item.inputs),
            label=item.label,
        )
        for item in sequence
    )


def _csr_storage_module() -> SimModule:
    return SimModule(
        name="csr_storage",
        signals=(
            Signal("csr_addr", width=8, kind="input"),
            Signal("csr_valid", width=1, kind="input"),
            Signal("csr_write", width=1, kind="input"),
            Signal("csr_wdata", width=32, kind="input"),
            Signal("rdata", width=32, kind="output"),
        ),
        assignments=(
            Assignment(
                "rdata",
                MuxExpr(
                    SignalRef("csr_valid"),
                    MuxExpr(
                        SignalRef("csr_write"),
                        ConstExpr(0, 32),
                        MemoryReadExpr("csr_mem", SignalRef("csr_addr")),
                    ),
                    ConstExpr(0, 32),
                ),
            ),
        ),
        outputs=("rdata",),
        memories=(Memory("csr_mem", width=32, depth=256),),
        memory_writes=(
            MemoryWrite(
                "csr_mem",
                SignalRef("csr_addr"),
                SignalRef("csr_wdata"),
                enable=BinaryExpr("&", SignalRef("csr_valid"), SignalRef("csr_write")),
            ),
        ),
    )


def _interrupt_controller_module() -> SimModule:
    return SimModule(
        name="irq_controller",
        signals=(
            Signal("irq_set", width=1, kind="input"),
            Signal("irq_clear", width=1, kind="input"),
            Signal("irq_mask", width=8, kind="input"),
            Signal("pending", width=8, kind="state"),
            Signal("irq_pending", width=8, kind="output"),
        ),
        assignments=(
            Assignment("irq_pending", SignalRef("pending")),
            Assignment(
                "pending",
                MuxExpr(
                    SignalRef("irq_clear"),
                    BinaryExpr("&", SignalRef("pending"), UnaryExpr("~", SignalRef("irq_mask"))),
                    MuxExpr(
                        SignalRef("irq_set"),
                        BinaryExpr("|", SignalRef("pending"), SignalRef("irq_mask")),
                        SignalRef("pending"),
                    ),
                ),
                phase="seq",
            ),
        ),
        outputs=("irq_pending",),
        outputs_post_state=True,
    )


def _axi4_memory_module() -> SimModule:
    word_addr = BinaryExpr(">>", SignalRef("awaddr"), ConstExpr(2, 32))
    read_addr = BinaryExpr(">>", SignalRef("araddr"), ConstExpr(2, 32))
    read_active = BinaryExpr("!=", SignalRef("rd_rem"), ConstExpr(0, 8))
    last_read = BinaryExpr("==", SignalRef("rd_rem"), ConstExpr(1, 8))
    return SimModule(
        name="axi_mem_model",
        signals=(
            Signal("awaddr", width=32, kind="input"),
            Signal("awvalid", width=1, kind="input"),
            Signal("awlen", width=8, kind="input"),
            Signal("awsize", width=3, kind="input"),
            Signal("awburst", width=2, kind="input"),
            Signal("awid", width=4, kind="input"),
            Signal("wdata", width=32, kind="input"),
            Signal("wvalid", width=1, kind="input"),
            Signal("wlast", width=1, kind="input"),
            Signal("araddr", width=32, kind="input"),
            Signal("arvalid", width=1, kind="input"),
            Signal("arlen", width=8, kind="input"),
            Signal("arsize", width=3, kind="input"),
            Signal("arburst", width=2, kind="input"),
            Signal("arid", width=4, kind="input"),
            Signal("wr_addr", width=8, kind="state"),
            Signal("rd_addr", width=8, kind="state"),
            Signal("rd_rem", width=8, kind="state"),
            Signal("bvalid_state", width=1, kind="state"),
            Signal("bvalid", width=1, kind="output"),
            Signal("rdata", width=32, kind="output"),
            Signal("rvalid", width=1, kind="output"),
            Signal("rlast", width=1, kind="output"),
        ),
        assignments=(
            Assignment("bvalid", SignalRef("bvalid_state")),
            Assignment(
                "rdata",
                MuxExpr(
                    read_active,
                    MemoryReadExpr("mem", SignalRef("rd_addr")),
                    ConstExpr(0, 32),
                ),
            ),
            Assignment("rvalid", read_active),
            Assignment("rlast", last_read),
            Assignment(
                "wr_addr",
                MuxExpr(
                    SignalRef("awvalid"),
                    MuxExpr(
                        SignalRef("wvalid"),
                        BinaryExpr("+", word_addr, ConstExpr(1, 32)),
                        word_addr,
                    ),
                    MuxExpr(
                        SignalRef("wvalid"),
                        BinaryExpr("+", SignalRef("wr_addr"), ConstExpr(1, 8)),
                        SignalRef("wr_addr"),
                    ),
                ),
                phase="seq",
            ),
            Assignment(
                "bvalid_state",
                BinaryExpr("&", SignalRef("wvalid"), SignalRef("wlast")),
                phase="seq",
            ),
            Assignment(
                "rd_addr",
                MuxExpr(
                    SignalRef("arvalid"),
                    read_addr,
                    MuxExpr(
                        read_active,
                        BinaryExpr("+", SignalRef("rd_addr"), ConstExpr(1, 8)),
                        SignalRef("rd_addr"),
                    ),
                ),
                phase="seq",
            ),
            Assignment(
                "rd_rem",
                MuxExpr(
                    SignalRef("arvalid"),
                    BinaryExpr("+", SignalRef("arlen"), ConstExpr(1, 8)),
                    MuxExpr(
                        read_active,
                        BinaryExpr("-", SignalRef("rd_rem"), ConstExpr(1, 8)),
                        SignalRef("rd_rem"),
                    ),
                ),
                phase="seq",
            ),
        ),
        outputs=("bvalid", "rdata", "rvalid", "rlast"),
        memories=(Memory("mem", width=32, depth=256),),
        memory_writes=(
            MemoryWrite(
                "mem",
                MuxExpr(SignalRef("awvalid"), word_addr, SignalRef("wr_addr")),
                SignalRef("wdata"),
                enable=SignalRef("wvalid"),
            ),
        ),
    )


def test_python_uvm_uses_reference_model_by_default():
    report = run_python_uvm_test(
        _accum_module(),
        (
            {"inp": 5},
            {"inp": 2},
            {"inp": 1},
        ),
        name="python_uvm_ref_model",
    )

    assert report.name == "python_uvm_ref_model"
    assert report.passed is True
    assert report.total_cycles == 3
    assert report.failures == ()
    assert report.traces[0].outputs == {"out": 8}
    assert report.traces[1].expected == {"out": 10}
    assert report.coverage["cycle_count"] == 3
    assert report.coverage["input_bins"]["inp"][5] == 1
    assert report.used_batch_mode is False


def test_python_uvm_accepts_explicit_expected_values():
    report = run_python_uvm_test(
        _accum_module(),
        (
            PythonUvmSequenceItem(inputs={"inp": 5}, expected={"out": 8}),
            PythonUvmSequenceItem(inputs={"inp": 2}, expected={"out": 9}),
        ),
        name="python_uvm_explicit_expected",
    )

    assert report.passed is False
    assert len(report.failures) == 1
    failure = report.failures[0]
    assert failure.cycle == 1
    assert failure.signal == "out"
    assert failure.expected == 9
    assert failure.actual == 10


def test_python_uvm_sequence_library_and_triage_dump(tmp_path):
    sequence = PythonUvmSequenceLibrary(
        sequences=(
            (
                PythonUvmSequenceItem(inputs={"inp": 5}, label="warmup"),
                PythonUvmSequenceItem(inputs={"inp": 2}, expected={"out": 9}, label="negative"),
            ),
            (
                {"inp": 1},
            ),
        )
    )
    coverage = PythonUvmCoverage()
    report = run_python_uvm_test(
        _accum_module(),
        sequence,
        coverage=coverage,
        name="python_uvm_triage",
    )

    assert report.passed is False
    assert report.total_cycles == 3
    assert report.coverage["labels_seen"]["warmup"] == 1
    assert report.coverage["labels_seen"]["negative"] == 1
    assert report.coverage["output_bins"]["out"][8] == 1

    triage_path = dump_python_uvm_triage(report, tmp_path / "triage.json")
    payload = json.loads(triage_path.read_text(encoding="utf-8"))
    assert payload["name"] == "python_uvm_triage"
    assert payload["passed"] is False
    assert payload["coverage"]["labels_seen"]["negative"] == 1
    assert payload["failures"][0]["cycle"] == 1


def test_python_uvm_uses_batch_mode_with_reference_model():
    report = run_python_uvm_test(
        _accum_module(),
        ({"inp": 1}, {"inp": 2}, {"inp": 3}, {"inp": 4}),
        name="python_uvm_batch_ref",
        batch_cycles=2,
    )

    assert report.passed is True
    assert report.total_cycles == 4
    assert report.used_batch_mode is True
    assert report.traces[-1].outputs == {"out": 13}


def test_python_uvm_accepts_online_expected_function():
    acc_state = {"acc": 3}

    def expected_fn(cycle, inputs):
        out = (acc_state["acc"] + inputs["inp"]) & 0xFF
        acc_state["acc"] = out
        return {"out": out}

    report = run_python_uvm_test(
        _accum_module(),
        ({"inp": 1}, {"inp": 2}, {"inp": 3}, {"inp": 4}),
        expected_fn=expected_fn,
        name="python_uvm_online_expected",
    )

    assert report.passed is True
    assert report.total_cycles == 4


def test_python_uvm_runs_on_compiled_simulator(tmp_path):
    builder = CppBackendScaffold()
    with builder.build(_accum_module(), tmp_path / "compiled_uvm") as simulator:
        report = run_python_uvm_test(
            _accum_module(),
            ({"inp": 5}, {"inp": 2}, {"inp": 1}),
            simulator=simulator,
            name="python_uvm_compiled",
            batch_cycles=2,
        )

    assert report.passed is True
    assert report.total_cycles == 3
    assert report.traces[-1].outputs == {"out": 11}
    assert report.used_batch_mode is True


def test_python_uvm_accepts_legacy_dsl_module():
    report = run_python_uvm_test(
        LegacyPythonUvmAccum(),
        (
            {"clk": 0, "rst": 1, "inp": 0},
            {"clk": 0, "rst": 0, "inp": 5},
            {"clk": 0, "rst": 0, "inp": 2},
        ),
        name="python_uvm_legacy",
    )

    assert report.passed is True
    assert report.traces[1].outputs == {"out": 5}
    assert report.traces[2].outputs == {"out": 7}


def test_python_uvm_runs_real_sram256k_module_on_compiled_simulator(tmp_path):
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )

    with build_compiled_simulator_from_legacy(module, build_dir=tmp_path / "real_sram_uvm") as simulator:
        report = run_python_uvm_test(
            module,
            (
                {"clk": 0, "rst_n": 0, "paddr": 0, "pwdata": 0, "pwrite": 0, "psel": 0, "penable": 0, "pstrb": 0},
                {"clk": 0, "rst_n": 1, "paddr": 8, "pwdata": 0x11223344, "pwrite": 1, "psel": 1, "penable": 1, "pstrb": 0b1111},
                {"clk": 0, "rst_n": 1, "paddr": 8, "pwdata": 0, "pwrite": 0, "psel": 1, "penable": 1, "pstrb": 0},
                {"clk": 0, "rst_n": 1, "paddr": 8, "pwdata": 0, "pwrite": 0, "psel": 1, "penable": 1, "pstrb": 0},
            ),
            simulator=simulator,
            name="python_uvm_real_sram",
            batch_cycles=2,
        )

    assert report.passed is True
    assert report.used_batch_mode is True
    assert report.traces[2].outputs["prdata"] == 0x11223344
    assert report.traces[3].expected["prdata"] == 0x11223344


def test_python_uvm_supports_apb_protocol_sequences():
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )
    sequence = apb_sequence(
        (
            ApbTransfer(addr=8, write=True, wdata=0x11223344, label="write"),
            ApbTransfer(addr=8, write=False, expected_rdata=0x11223344, label="read"),
        ),
        extra_inputs={"clk": 0, "rst_n": 1},
    )
    report = run_python_uvm_test(
        module,
        sequence,
        reference_model=register_reference_model(storage={}, read_output_name="prdata"),
        name="python_uvm_apb_protocol",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["write"] == 2
    assert report.traces[-1].expected["prdata"] == 0x11223344
    assert report.used_batch_mode is False


def test_python_uvm_uses_batch_mode_with_register_reference_model():
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )
    sequence = apb_sequence(
        (
            ApbTransfer(addr=8, write=True, wdata=0x11223344, label="write"),
            ApbTransfer(addr=8, write=False, expected_rdata=0x11223344, label="read"),
        ),
        extra_inputs={"clk": 0, "rst_n": 1},
    )
    report = run_python_uvm_test(
        module,
        sequence,
        reference_model=register_reference_model(storage={}, read_output_name="prdata"),
        name="python_uvm_apb_protocol_batch",
        batch_cycles=2,
    )

    assert report.passed is True
    assert report.used_batch_mode is True
    assert report.traces[-1].expected["prdata"] == 0x11223344


def test_register_reference_model_supports_full_cycle_apb_checking():
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )
    sequence = (
        {"clk": 0, "rst_n": 0, "paddr": 0, "pwdata": 0, "pwrite": 0, "psel": 0, "penable": 0, "pstrb": 0},
        *apb_sequence(
            (
                ApbTransfer(addr=8, write=True, wdata=0x11223344, label="write"),
                ApbTransfer(addr=8, write=False, label="read"),
            ),
            extra_inputs={"clk": 0, "rst_n": 1},
        ),
    )
    report = run_python_uvm_test(
        module,
        sequence,
        reference_model=register_reference_model(storage={}, read_output_name="prdata"),
        name="python_uvm_apb_full_cycle_ref",
        batch_cycles=2,
    )

    assert report.passed is True
    assert report.used_batch_mode is True
    assert report.traces[-1].expected["prdata"] == 0x11223344


def test_python_uvm_supports_wishbone_protocol_sequences():
    module = SimModule(
        name="wishbone_regfile",
        signals=(
            Signal("wb_adr", width=4, kind="input"),
            Signal("wb_dat_w", width=32, kind="input"),
            Signal("wb_we", width=1, kind="input"),
            Signal("wb_cyc", width=1, kind="input"),
            Signal("wb_stb", width=1, kind="input"),
            Signal("wb_sel", width=4, kind="input"),
            Signal("wb_dat_r", width=32, kind="output"),
            Signal("wb_ack", width=1, kind="output"),
        ),
        assignments=(
            Assignment("wb_dat_r", SignalRef("wb_dat_w")),
            Assignment("wb_ack", BinaryExpr("&", SignalRef("wb_cyc"), SignalRef("wb_stb"))),
        ),
        outputs=("wb_dat_r", "wb_ack"),
    )
    sequence = wishbone_sequence(
        (
            WishboneTransfer(addr=1, write=True, wdata=0x55AA55AA, label="wb_write"),
            WishboneTransfer(addr=1, write=False, expected_rdata=0, label="wb_read"),
        )
    )
    report = run_python_uvm_test(
        module,
        sequence,
        name="python_uvm_wishbone",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["wb_write"] == 1
    assert report.traces[0].outputs["wb_ack"] == 1


def test_python_uvm_supports_axistream_sequences():
    module = SimModule(
        name="axis_sink",
        signals=(
            Signal("tdata", width=16, kind="input"),
            Signal("tvalid", width=1, kind="input"),
            Signal("tlast", width=1, kind="input"),
            Signal("tkeep", width=2, kind="input"),
            Signal("tready", width=1, kind="output"),
        ),
        assignments=(
            Assignment("tready", SignalRef("tvalid")),
        ),
        outputs=("tready",),
    )
    sequence = axistream_sequence(
        (
            AxiStreamTransfer(data=0x1234, keep=0x3, expected_ready=1, label="beat0"),
            AxiStreamTransfer(data=0x5678, keep=0x3, last=1, expected_ready=1, label="beat1"),
        )
    )
    report = run_python_uvm_test(module, sequence, name="python_uvm_axis")

    assert report.passed is True
    assert report.coverage["labels_seen"]["beat0"] == 1
    assert report.traces[-1].expected["tready"] == 1


def test_python_uvm_supports_axi4_burst_sequences_with_memory_reference_model():
    module = _axi4_memory_module()
    sequence = _stimulus_only(
        axi4_sequence(
            (
                Axi4Transfer(addr=0x10, write=True, beats=(0x11111111, 0x22222222), burst_len=2, label="wr"),
                Axi4Transfer(addr=0x10, write=False, burst_len=2, label="rd"),
            )
        )
    )
    ref_model = axi_memory_reference_model(storage={}, read_data_name="rdata")

    report = run_python_uvm_test(
        module,
        (
            *sequence,
            PythonUvmSequenceItem(inputs={}),
        ),
        reference_model=ref_model,
        name="python_uvm_axi4_burst",
    )

    read_beats = [trace for trace in report.traces if trace.expected.get("rvalid") == 1]
    assert report.passed is True
    assert report.coverage["labels_seen"]["wr"] >= 2
    assert read_beats[-1].expected["rlast"] == 1
    assert read_beats[-1].expected["rdata"] == 0x22222222


def test_python_uvm_supports_csr_sequences():
    module = _csr_storage_module()
    ref_model = csr_reference_model(storage={})
    report = run_python_uvm_test(
        module,
        csr_sequence(
            (
                CsrTransfer(addr=8, write=True, wdata=0x55AA55AA, label="csr_wr"),
                CsrTransfer(addr=8, write=False, label="csr_rd"),
            )
        ),
        reference_model=ref_model,
        name="python_uvm_csr",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["csr_wr"] == 1
    assert report.traces[-1].expected["rdata"] == 0x55AA55AA


def test_python_uvm_supports_interrupt_sequences():
    module = _interrupt_controller_module()
    ref_model = interrupt_reference_model()
    report = run_python_uvm_test(
        module,
        interrupt_sequence(
            (
                InterruptEvent(irq_mask=0x3, cycles=2, label="irq0"),
            ),
            clear_between=True,
        ),
        reference_model=ref_model,
        name="python_uvm_irq",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["irq0"] == 2
    assert report.traces[1].expected["irq_pending"] == 0x3


def test_python_uvm_protocol_reference_models_run_on_compiled_simulator(tmp_path):
    builder = CppBackendScaffold()
    sequence = _stimulus_only(
        axi4_sequence(
            (
                Axi4Transfer(addr=0x20, write=True, beats=(0x33333333, 0x44444444), burst_len=2, label="wr"),
                Axi4Transfer(addr=0x20, write=False, burst_len=2, label="rd"),
            )
        )
    )
    ref_model = axi_memory_reference_model(storage={}, read_data_name="rdata")

    with builder.build(_axi4_memory_module(), tmp_path / "compiled_axi4_uvm") as simulator:
        report = run_python_uvm_test(
            _axi4_memory_module(),
            (
                *sequence,
                PythonUvmSequenceItem(inputs={}),
            ),
            simulator=simulator,
            reference_model=ref_model,
            name="python_uvm_axi4_compiled",
            batch_cycles=3,
        )

    read_beats = [trace for trace in report.traces if trace.expected.get("rvalid") == 1]
    assert report.passed is True
    assert report.used_batch_mode is True
    assert read_beats[-1].expected["rdata"] == 0x44444444
