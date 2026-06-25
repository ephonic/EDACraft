import importlib.util
import json
from pathlib import Path

import pytest

from rtlgen_x.dsl import (
    APBRegisterBank,
    AsyncFIFO,
    AXI4LiteRegisterBank,
    DslLoweringReport,
    Else,
    If,
    Input,
    LoweredDslModule,
    Module,
    Output,
    ReadyValidAsyncBridge,
    ReadyValidFIFO,
    ReadyValidRegister,
    ReqRsp,
    ReqRspQueue,
    Reg,
    SkidBuffer,
    SyncFIFO,
    WishboneRegisterBank,
    build_compiled_simulator_from_dsl,
)
from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    ClockDomain,
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
    AhbLiteTransfer,
    ApbTransfer,
    Axi4Transfer,
    AxiStreamTransfer,
    AxiLiteTransfer,
    CsrTransfer,
    InterruptEvent,
    PythonUvmCoverage,
    PythonUvmSequenceItem,
    PythonUvmSequenceLibrary,
    ReadyValidTransfer,
    ReqRspTransfer,
    WishboneTransfer,
    apb_reference_model,
    apb_sequence,
    axi4_sequence,
    axilite_protocol_sequence,
    axilite_reference_model,
    axi_memory_reference_model,
    axistream_sequence,
    csr_reference_model,
    csr_sequence,
    dump_python_uvm_triage,
    ahblite_reference_model,
    ahblite_sequence,
    check_reqrsp_trace,
    check_ready_valid_trace,
    interrupt_reference_model,
    interrupt_sequence,
    req_rsp_reference_model,
    req_rsp_sequence,
    ready_valid_reference_model,
    ready_valid_sequence,
    register_reference_model,
    wishbone_clocked_protocol_sequence,
    wishbone_clocked_reference_model,
    check_wishbone_trace,
    wishbone_protocol_sequence,
    wishbone_reference_model,
    run_python_uvm_test,
    wishbone_sequence,
)


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


def _accum_module() -> LoweredDslModule:
    return _lowered(_raw_accum_module())


def _raw_multi_clock_python_uvm_module() -> SimModule:
    return SimModule(
        name="python_uvm_multiclk",
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
    )


def _multi_clock_python_uvm_module() -> LoweredDslModule:
    return _lowered(_raw_multi_clock_python_uvm_module())


class DslPythonUvmAccum(Module):
    def __init__(self):
        super().__init__("dsl_python_uvm_accum")
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


def _raw_csr_storage_module() -> SimModule:
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


def _csr_storage_module() -> LoweredDslModule:
    return _lowered(_raw_csr_storage_module())


def _raw_interrupt_controller_module() -> SimModule:
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


def _interrupt_controller_module() -> LoweredDslModule:
    return _lowered(_raw_interrupt_controller_module())


def _raw_axi4_memory_module() -> SimModule:
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


def _axi4_memory_module() -> LoweredDslModule:
    return _lowered(_raw_axi4_memory_module())


def _raw_axilite_regfile_module() -> SimModule:
    word_addr_w = BinaryExpr(">>", SignalRef("awaddr"), ConstExpr(2, 32))
    word_addr_r = BinaryExpr(">>", SignalRef("araddr"), ConstExpr(2, 32))
    return SimModule(
        name="axilite_regfile",
        signals=(
            Signal("awaddr", width=32, kind="input"),
            Signal("awvalid", width=1, kind="input"),
            Signal("awprot", width=3, kind="input"),
            Signal("wdata", width=32, kind="input"),
            Signal("wstrb", width=4, kind="input"),
            Signal("wvalid", width=1, kind="input"),
            Signal("bready", width=1, kind="input"),
            Signal("araddr", width=32, kind="input"),
            Signal("arvalid", width=1, kind="input"),
            Signal("arprot", width=3, kind="input"),
            Signal("rready", width=1, kind="input"),
            Signal("bvalid_state", width=1, kind="state"),
            Signal("rvalid_state", width=1, kind="state"),
            Signal("rdata_state", width=32, kind="state"),
            Signal("bvalid", width=1, kind="output"),
            Signal("rvalid", width=1, kind="output"),
            Signal("rdata", width=32, kind="output"),
        ),
        assignments=(
            Assignment("bvalid", SignalRef("bvalid_state")),
            Assignment("rvalid", SignalRef("rvalid_state")),
            Assignment("rdata", SignalRef("rdata_state")),
            Assignment(
                "bvalid_state",
                BinaryExpr("&", SignalRef("awvalid"), SignalRef("wvalid")),
                phase="seq",
            ),
            Assignment(
                "rvalid_state",
                SignalRef("arvalid"),
                phase="seq",
            ),
            Assignment(
                "rdata_state",
                MuxExpr(
                    SignalRef("arvalid"),
                    MemoryReadExpr("regmem", word_addr_r),
                    SignalRef("rdata_state"),
                ),
                phase="seq",
            ),
        ),
        outputs=("bvalid", "rvalid", "rdata"),
        memories=(Memory("regmem", width=32, depth=256),),
        memory_writes=(
            MemoryWrite(
                "regmem",
                word_addr_w,
                SignalRef("wdata"),
                enable=BinaryExpr("&", SignalRef("awvalid"), SignalRef("wvalid")),
            ),
        ),
    )


def _axilite_regfile_module() -> LoweredDslModule:
    return _lowered(_raw_axilite_regfile_module())


def _raw_wishbone_regfile_module() -> SimModule:
    word_addr = BinaryExpr(">>", SignalRef("adr_i"), ConstExpr(2, 32))
    wb_access = BinaryExpr("&", SignalRef("cyc_i"), SignalRef("stb_i"))
    wb_write = BinaryExpr("&", wb_access, SignalRef("we_i"))
    wb_read = BinaryExpr("&", wb_access, UnaryExpr("~", SignalRef("we_i")))
    return SimModule(
        name="wishbone_regfile",
        signals=(
            Signal("adr_i", width=32, kind="input"),
            Signal("dat_i", width=32, kind="input"),
            Signal("we_i", width=1, kind="input"),
            Signal("sel_i", width=4, kind="input"),
            Signal("stb_i", width=1, kind="input"),
            Signal("cyc_i", width=1, kind="input"),
            Signal("cti_i", width=3, kind="input"),
            Signal("bte_i", width=2, kind="input"),
            Signal("dat_o", width=32, kind="output"),
            Signal("ack_o", width=1, kind="output"),
            Signal("err_o", width=1, kind="output"),
            Signal("rty_o", width=1, kind="output"),
        ),
        assignments=(
            Assignment(
                "dat_o",
                MuxExpr(
                    wb_read,
                    MemoryReadExpr("wbmem", word_addr),
                    ConstExpr(0, 32),
                ),
            ),
            Assignment("ack_o", wb_access),
            Assignment("err_o", ConstExpr(0, 1)),
            Assignment("rty_o", ConstExpr(0, 1)),
        ),
        outputs=("dat_o", "ack_o", "err_o", "rty_o"),
        memories=(Memory("wbmem", width=32, depth=256),),
        memory_writes=(
            MemoryWrite(
                "wbmem",
                word_addr,
                SignalRef("dat_i"),
                enable=wb_write,
            ),
        ),
    )


def _wishbone_regfile_module() -> LoweredDslModule:
    return _lowered(_raw_wishbone_regfile_module())


def _raw_ahblite_regfile_module() -> SimModule:
    word_addr = BinaryExpr(">>", SignalRef("haddr"), ConstExpr(2, 32))
    htrans_active = BinaryExpr("|", BinaryExpr("==", SignalRef("htrans"), ConstExpr(2, 2)), BinaryExpr("==", SignalRef("htrans"), ConstExpr(3, 2)))
    ahb_access = BinaryExpr("&", SignalRef("hsel"), htrans_active)
    ahb_write = BinaryExpr("&", ahb_access, SignalRef("hwrite"))
    ahb_read = BinaryExpr("&", ahb_access, UnaryExpr("~", SignalRef("hwrite")))
    return SimModule(
        name="ahblite_regfile",
        signals=(
            Signal("haddr", width=32, kind="input"),
            Signal("htrans", width=2, kind="input"),
            Signal("hwrite", width=1, kind="input"),
            Signal("hsize", width=3, kind="input"),
            Signal("hburst", width=3, kind="input"),
            Signal("hprot", width=4, kind="input"),
            Signal("hwdata", width=32, kind="input"),
            Signal("hsel", width=1, kind="input"),
            Signal("hrdata", width=32, kind="output"),
            Signal("hready", width=1, kind="output"),
            Signal("hresp", width=1, kind="output"),
        ),
        assignments=(
            Assignment(
                "hrdata",
                MuxExpr(
                    ahb_read,
                    MemoryReadExpr("ahbmem", word_addr),
                    ConstExpr(0, 32),
                ),
            ),
            Assignment("hready", ConstExpr(1, 1)),
            Assignment("hresp", ConstExpr(0, 1)),
        ),
        outputs=("hrdata", "hready", "hresp"),
        memories=(Memory("ahbmem", width=32, depth=256),),
        memory_writes=(
            MemoryWrite(
                "ahbmem",
                word_addr,
                SignalRef("hwdata"),
                enable=ahb_write,
            ),
        ),
    )


def _ahblite_regfile_module() -> LoweredDslModule:
    return _lowered(_raw_ahblite_regfile_module())


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


def test_python_uvm_rejects_raw_simmodule():
    with pytest.raises(TypeError, match="does not accept raw SimModule"):
        run_python_uvm_test(
            _raw_accum_module(),
            ({"inp": 5},),
            name="python_uvm_raw",
        )


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

    protocol_check = check_ready_valid_trace(
        (
            report.traces[0].__class__(
                cycle=0,
                inputs={"data": 1, "valid": 1},
                outputs={"ready": 0},
                expected={},
            ),
            report.traces[0].__class__(
                cycle=1,
                inputs={"data": 2, "valid": 1},
                outputs={"ready": 0},
                expected={},
            ),
        )
    )
    triage_path = dump_python_uvm_triage(
        report,
        tmp_path / "triage.json",
        protocol_checks=(protocol_check,),
    )
    payload = json.loads(triage_path.read_text(encoding="utf-8"))
    assert payload["name"] == "python_uvm_triage"
    assert payload["passed"] is False
    assert payload["coverage"]["labels_seen"]["negative"] == 1
    assert payload["failures"][0]["cycle"] == 1
    assert payload["traces"][0]["active_domains"] == []
    assert payload["protocol_checks"][0]["protocol"] == "ReadyValid"
    assert payload["protocol_checks"][0]["passed"] is False
    assert payload["protocol_checks"][0]["violations"][0]["rule"] == "ready_valid_payload_stable"


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
    with builder.build(_raw_accum_module(), tmp_path / "compiled_uvm") as simulator:
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


def test_python_uvm_accepts_dsl_module():
    report = run_python_uvm_test(
        DslPythonUvmAccum(),
        (
            {"clk": 0, "rst": 1, "inp": 0},
            {"clk": 0, "rst": 0, "inp": 5},
            {"clk": 0, "rst": 0, "inp": 2},
        ),
        name="python_uvm_dsl",
    )

    assert report.passed is True
    assert report.traces[1].outputs == {"out": 5}
    assert report.traces[2].outputs == {"out": 7}


def test_python_uvm_requires_active_domains_for_multi_clock_modules():
    with pytest.raises(ValueError) as excinfo:
        run_python_uvm_test(
            _multi_clock_python_uvm_module(),
            ({"wr_en": 0, "rd_en": 0},),
            name="python_uvm_multiclk",
        )
    assert "must provide explicit active_domains" in str(excinfo.value)
    assert "PythonUvmSequenceItem" in str(excinfo.value)


def test_python_uvm_supports_explicit_multi_clock_sequences():
    report = run_python_uvm_test(
        _multi_clock_python_uvm_module(),
        (
            PythonUvmSequenceItem(
                inputs={"wr_rst": 1, "rd_rst": 1},
                active_domains=("wr_clk", "rd_clk"),
                label="reset",
            ),
            PythonUvmSequenceItem(
                inputs={"wr_en": 1},
                active_domains=("wr_clk",),
                label="write0",
            ),
            PythonUvmSequenceItem(
                inputs={"wr_en": 1},
                active_domains=("wr_clk",),
                label="write1",
            ),
            PythonUvmSequenceItem(
                inputs={"rd_en": 1},
                active_domains=("rd_clk",),
                label="read0",
            ),
            PythonUvmSequenceItem(
                inputs={"rd_en": 1},
                active_domains=("rd_clk",),
                label="read1",
            ),
        ),
        name="python_uvm_multiclk_python",
        batch_cycles=2,
    )

    assert report.passed is True
    assert report.total_cycles == 5
    assert report.used_batch_mode is False
    assert report.coverage["labels_seen"]["reset"] == 1
    assert report.traces[0].outputs == {"out": 0}
    assert report.traces[2].outputs == {"out": 1}
    assert report.traces[4].outputs == {"out": 3}
    assert report.traces[3].active_domains == ("rd_clk",)


def test_python_uvm_supports_structured_multi_clock_sequence_items():
    report = run_python_uvm_test(
        _multi_clock_python_uvm_module(),
        (
            {
                "inputs": {"wr_rst": 1, "rd_rst": 1},
                "active_domains": ("wr_clk", "rd_clk"),
                "label": "reset",
            },
            {
                "inputs": {"wr_en": 1},
                "active_domains": ("wr_clk",),
                "label": "write0",
            },
            {
                "inputs": {"rd_en": 1},
                "active_domains": ("rd_clk",),
                "label": "read0",
            },
        ),
        name="python_uvm_multiclk_structured",
    )

    assert report.passed is True
    assert report.total_cycles == 3
    assert report.traces[0].active_domains == ("wr_clk", "rd_clk")
    assert report.traces[2].active_domains == ("rd_clk",)


def test_python_uvm_supports_mapping_active_domains_for_structured_steps():
    report = run_python_uvm_test(
        _multi_clock_python_uvm_module(),
        (
            {
                "inputs": {"wr_rst": 1, "rd_rst": 1},
                "active_domains": {"wr_clk": True, "rd_clk": True},
                "label": "reset",
            },
            {
                "inputs": {"wr_en": 1},
                "active_domains": {"wr_clk": True, "rd_clk": False},
                "label": "write0",
            },
            {
                "inputs": {"rd_en": 1},
                "active_domains": {"wr_clk": False, "rd_clk": True},
                "label": "read0",
            },
        ),
        name="python_uvm_multiclk_mapping_payload",
    )

    assert report.passed is True
    assert report.traces[0].active_domains == ("wr_clk", "rd_clk")
    assert report.traces[1].active_domains == ("wr_clk",)
    assert report.traces[2].active_domains == ("rd_clk",)


def test_python_uvm_rejects_unknown_active_domains_early():
    with pytest.raises(ValueError) as excinfo:
        run_python_uvm_test(
            _multi_clock_python_uvm_module(),
            (
                {
                    "inputs": {"wr_en": 1},
                    "active_domains": ("bogus_clk",),
                    "label": "bad_step",
                },
            ),
            name="python_uvm_multiclk_unknown_domain",
        )

    assert "reference unknown active_domains: bogus_clk" in str(excinfo.value)
    assert "Known clock domains: wr_clk, rd_clk" in str(excinfo.value)


def test_python_uvm_rejects_unknown_active_domains_with_declared_domain_aliases():
    class DeclaredDomainPythonUvmMailbox(Module):
        def __init__(self):
            super().__init__("DeclaredDomainPythonUvmMailbox")
            self.wr_clk = Input(1, "wr_clk")
            self.rd_clk = Input(1, "rd_clk")
            self.wr_rst = Input(1, "wr_rst")
            self.rd_rst = Input(1, "rd_rst")
            self.wr_en = Input(1, "wr_en")
            self.rd_en = Input(1, "rd_en")
            self.din = Input(8, "din")
            self.dout = Output(8, "dout")
            self.data_q = Reg(8, "data_q")
            self.read_q = Reg(8, "read_q")

            self.clock_domain("write", self.wr_clk, self.wr_rst)
            self.clock_domain("read", self.rd_clk, self.rd_rst)

            @self.comb
            def _comb():
                self.dout <<= self.read_q

            @self.seq_domain("write")
            def _wr_seq():
                with If(self.wr_rst == 1):
                    self.data_q <<= 0
                with Else():
                    with If(self.wr_en == 1):
                        self.data_q <<= self.din

            @self.seq_domain("read")
            def _rd_seq():
                with If(self.rd_rst == 1):
                    self.read_q <<= 0
                with Else():
                    with If(self.rd_en == 1):
                        self.read_q <<= self.data_q

    with pytest.raises(ValueError) as excinfo:
        run_python_uvm_test(
            DeclaredDomainPythonUvmMailbox(),
            (
                {
                    "inputs": {"wr_en": 1},
                    "active_domains": ("bogus_clk",),
                    "label": "bad_step",
                },
            ),
            name="python_uvm_multiclk_unknown_declared_domain",
        )

    assert "reference unknown active_domains: bogus_clk" in str(excinfo.value)
    assert "Known clock domains: write, read" in str(excinfo.value)
    assert "Known clock aliases: wr_clk, rd_clk" in str(excinfo.value)
    assert "Known clock aliases: wr_clk, rd_clk" in str(excinfo.value)


def test_python_uvm_supports_explicit_multi_clock_sequences_on_compiled_simulator(tmp_path):
    builder = CppBackendScaffold()
    with builder.build(_raw_multi_clock_python_uvm_module(), tmp_path / "compiled_uvm_multiclk") as simulator:
        report = run_python_uvm_test(
            _multi_clock_python_uvm_module(),
            (
                PythonUvmSequenceItem(
                    inputs={"wr_rst": 1, "rd_rst": 1},
                    active_domains=("wr_clk", "rd_clk"),
                ),
                PythonUvmSequenceItem(
                    inputs={"wr_en": 1},
                    active_domains=("wr_clk",),
                ),
                PythonUvmSequenceItem(
                    inputs={"wr_en": 1},
                    active_domains=("wr_clk",),
                ),
                PythonUvmSequenceItem(
                    inputs={"rd_en": 1},
                    active_domains=("rd_clk",),
                ),
                PythonUvmSequenceItem(
                    inputs={"rd_en": 1},
                    active_domains=("rd_clk",),
                ),
            ),
            simulator=simulator,
            name="python_uvm_multiclk_compiled",
            batch_cycles=2,
        )

    assert report.passed is True
    assert report.total_cycles == 5
    assert report.used_batch_mode is False
    assert report.traces[-1].outputs == {"out": 3}
    assert report.traces[1].active_domains == ("wr_clk",)


def test_python_uvm_ready_valid_async_bridge_supports_explicit_multiclock_expected_traces():
    report = run_python_uvm_test(
        DslReadyValidAsyncBridgeHarness(),
        (
            PythonUvmSequenceItem(
                inputs={"wr_rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0},
                expected={"in_ready": 1, "out_data": 0, "out_valid": 0},
                active_domains=("wr_clk",),
                label="wr_reset",
            ),
            PythonUvmSequenceItem(
                inputs={"rd_rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0},
                expected={"in_ready": 1, "out_data": 0, "out_valid": 0},
                active_domains=("rd_clk",),
                label="rd_reset",
            ),
            PythonUvmSequenceItem(
                inputs={"wr_rst": 0, "rd_rst": 0, "in_data": 0x11, "in_valid": 1, "out_ready": 0},
                expected={"in_ready": 1, "out_data": 0x11, "out_valid": 0},
                active_domains=("wr_clk",),
                label="push0",
            ),
            PythonUvmSequenceItem(
                inputs={"in_data": 0, "in_valid": 0, "out_ready": 0},
                expected={"in_ready": 1, "out_data": 0x11, "out_valid": 0},
                active_domains=("rd_clk",),
                label="observe_empty",
            ),
            PythonUvmSequenceItem(
                inputs={"in_data": 0, "in_valid": 0, "out_ready": 1},
                expected={"in_ready": 1, "out_data": 0x11, "out_valid": 1},
                active_domains=("rd_clk",),
                label="pop0",
            ),
            PythonUvmSequenceItem(
                inputs={"in_data": 0, "in_valid": 0, "out_ready": 1},
                expected={"in_ready": 1, "out_data": 0, "out_valid": 0},
                active_domains=("rd_clk",),
                label="drain",
            ),
        ),
        name="python_uvm_ready_valid_async_bridge",
    )

    assert report.passed is True
    assert report.used_batch_mode is False
    assert report.coverage["labels_seen"]["pop0"] == 1
    assert report.traces[2].outputs["out_data"] == 0x11
    assert report.traces[4].outputs["out_valid"] == 1


def test_python_uvm_async_fifo_supports_explicit_multiclock_expected_traces():
    report = run_python_uvm_test(
        DslAsyncFifoHarness(),
        (
            PythonUvmSequenceItem(
                inputs={"wr_rst": 1, "rd_rst": 0, "din": 0, "wr_en": 0, "rd_en": 0},
                expected={"dout": 0, "full": 0, "empty": 1},
                active_domains=("wr_clk",),
                label="wr_reset",
            ),
            PythonUvmSequenceItem(
                inputs={"wr_rst": 0, "rd_rst": 1, "din": 0, "wr_en": 0, "rd_en": 0},
                expected={"dout": 0, "full": 0, "empty": 1},
                active_domains=("rd_clk",),
                label="rd_reset",
            ),
            PythonUvmSequenceItem(
                inputs={"wr_rst": 0, "rd_rst": 0, "din": 0x11, "wr_en": 1, "rd_en": 0},
                expected={"dout": 0x11, "full": 0, "empty": 1},
                active_domains=("wr_clk",),
                label="push0",
            ),
            PythonUvmSequenceItem(
                inputs={"din": 0, "wr_en": 0, "rd_en": 0},
                expected={"dout": 0x11, "full": 0, "empty": 1},
                active_domains=("rd_clk",),
                label="observe0",
            ),
            PythonUvmSequenceItem(
                inputs={"din": 0, "wr_en": 0, "rd_en": 1},
                expected={"dout": 0x11, "full": 0, "empty": 0},
                active_domains=("rd_clk",),
                label="pop0",
            ),
        ),
        name="python_uvm_async_fifo",
    )

    assert report.passed is True
    assert report.used_batch_mode is False
    assert report.coverage["labels_seen"]["push0"] == 1
    assert report.traces[2].outputs == {"dout": 0x11, "full": 0, "empty": 1}
    assert report.traces[4].outputs == {"dout": 0x11, "full": 0, "empty": 0}


def test_python_uvm_sync_fifo_buffers_single_clock_storage():
    report = run_python_uvm_test(
        DslSyncFifoHarness(),
        (
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 1, "din": 0, "wr_en": 0, "rd_en": 0},
                expected={"dout": 0, "full": 0, "empty": 1, "count": 0, "rd_rdy": 0},
                label="reset",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "din": 0x11, "wr_en": 1, "rd_en": 0},
                expected={"dout": 0x11, "full": 0, "empty": 0, "count": 1, "rd_rdy": 1},
                label="push0",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "din": 0x22, "wr_en": 1, "rd_en": 0},
                expected={"dout": 0x11, "full": 0, "empty": 0, "count": 2, "rd_rdy": 1},
                label="push1",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "din": 0, "wr_en": 0, "rd_en": 1},
                expected={"dout": 0x22, "full": 0, "empty": 0, "count": 1, "rd_rdy": 1},
                label="pop0",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "din": 0, "wr_en": 0, "rd_en": 1},
                expected={"dout": 0, "full": 0, "empty": 1, "count": 0, "rd_rdy": 0},
                label="pop1",
            ),
        ),
        name="python_uvm_sync_fifo",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["push1"] == 1
    assert report.traces[2].outputs["count"] == 2
    assert report.traces[3].outputs["dout"] == 0x22


def test_python_uvm_runs_real_sram256k_module_on_compiled_simulator(tmp_path):
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )

    with build_compiled_simulator_from_dsl(module, build_dir=tmp_path / "real_sram_uvm") as simulator:
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


def test_python_uvm_supports_apb_protocol_reference_model_alias():
    module = _load_external_module(
        "earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
        "EarphoneSRAM256K",
    )
    report = run_python_uvm_test(
        module,
        apb_sequence(
            (
                ApbTransfer(addr=8, write=True, wdata=0x11223344, label="write"),
                ApbTransfer(addr=8, write=False, expected_rdata=0x11223344, label="read"),
            ),
            extra_inputs={"clk": 0, "rst_n": 1},
        ),
        reference_model=apb_reference_model(storage={}, read_output_name="prdata"),
        name="python_uvm_apb_protocol_alias",
    )

    assert report.passed is True
    assert report.traces[-1].expected["prdata"] == 0x11223344


def test_python_uvm_apb_register_bank_runs_with_protocol_vip():
    report = run_python_uvm_test(
        APBRegisterBank(depth=8),
        apb_sequence(
            (
                ApbTransfer(
                    addr=0x10,
                    write=True,
                    wdata=0xA5A55A5A,
                    strb=0x5,
                    label="apb_wr",
                ),
                ApbTransfer(
                    addr=0x10,
                    write=False,
                    expected_rdata=0x00A5005A,
                    label="apb_rd",
                ),
            ),
            extra_inputs={"pclk": 0, "presetn": 1, "pprot": 0},
        ),
        reference_model=apb_reference_model(storage={}, read_output_name="prdata"),
        name="python_uvm_apb_register_bank",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["apb_wr"] == 2
    assert report.coverage["labels_seen"]["apb_rd"] == 2
    assert report.traces[1].outputs["pready"] == 1
    assert report.traces[-1].expected["prdata"] == 0x00A5005A


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
        _lowered(module),
        sequence,
        name="python_uvm_wishbone",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["wb_write"] == 1
    assert report.traces[0].outputs["wb_ack"] == 1


def test_python_uvm_supports_wishbone_protocol_reference_model():
    report = run_python_uvm_test(
        _wishbone_regfile_module(),
        wishbone_protocol_sequence(
            (
                WishboneTransfer(addr=0x10, write=True, wdata=0xA5A55A5A, label="wb_wr"),
                WishboneTransfer(addr=0x10, write=False, expected_rdata=0xA5A55A5A, label="wb_rd"),
            )
        ),
        reference_model=wishbone_reference_model(storage={}, read_output_name="dat_o"),
        name="python_uvm_wishbone_protocol_ref",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["wb_wr"] == 1
    assert report.traces[0].expected["ack_o"] == 1
    assert report.traces[-1].expected["dat_o"] == 0xA5A55A5A


def test_python_uvm_wishbone_register_bank_runs_with_clocked_protocol_vip():
    report = run_python_uvm_test(
        WishboneRegisterBank(depth=8),
        _stimulus_only(
            wishbone_clocked_protocol_sequence(
                (
                    WishboneTransfer(
                        addr=0x10,
                        write=True,
                        wdata=0xA5A55A5A,
                        sel=0x5,
                        label="wb_wr",
                    ),
                    WishboneTransfer(
                        addr=0x10,
                        write=False,
                        expected_rdata=0x00A5005A,
                        label="wb_rd",
                    ),
                ),
                extra_inputs={"clk_i": 0, "rst_i": 0},
            )
        ),
        reference_model=wishbone_clocked_reference_model(storage={}, read_output_name="dat_o"),
        name="python_uvm_wishbone_clocked_register_bank",
    )
    protocol_check = check_wishbone_trace(report)

    assert report.passed is True
    assert protocol_check.passed is True
    assert report.coverage["labels_seen"]["wb_wr"] == 2
    assert report.coverage["labels_seen"]["wb_rd"] == 2
    assert report.traces[1].expected["ack_o"] == 1
    assert report.traces[4].expected["dat_o"] == 0x00A5005A


def test_python_uvm_wishbone_register_bank_split_control_state_runs_with_clocked_protocol_vip():
    report = run_python_uvm_test(
        WishboneRegisterBank(depth=8, split_control_state=True),
        _stimulus_only(
            wishbone_clocked_protocol_sequence(
                (
                    WishboneTransfer(
                        addr=0x10,
                        write=True,
                        wdata=0xA5A55A5A,
                        sel=0x5,
                        label="wb_wr",
                    ),
                    WishboneTransfer(
                        addr=0x10,
                        write=False,
                        expected_rdata=0x00A5005A,
                        label="wb_rd",
                    ),
                ),
                extra_inputs={"clk_i": 0, "rst_i": 0},
            )
        ),
        reference_model=wishbone_clocked_reference_model(storage={}, read_output_name="dat_o"),
        name="python_uvm_wishbone_clocked_register_bank_split_control_state",
    )
    protocol_check = check_wishbone_trace(report)

    assert report.passed is True
    assert protocol_check.passed is True
    assert report.coverage["labels_seen"]["wb_wr"] == 2
    assert report.coverage["labels_seen"]["wb_rd"] == 2
    assert report.traces[1].expected["ack_o"] == 1
    assert report.traces[4].expected["dat_o"] == 0x00A5005A


def test_python_uvm_supports_ahblite_protocol_reference_model():
    report = run_python_uvm_test(
        _ahblite_regfile_module(),
        ahblite_sequence(
            (
                AhbLiteTransfer(addr=0x10, write=True, wdata=0xFACE1234, label="ahb_wr"),
                AhbLiteTransfer(addr=0x10, write=False, expected_rdata=0xFACE1234, label="ahb_rd"),
            )
        ),
        reference_model=ahblite_reference_model(storage={}, read_output_name="hrdata"),
        name="python_uvm_ahblite_protocol_ref",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["ahb_wr"] == 1
    assert report.traces[0].expected["hready"] == 1
    assert report.traces[-1].expected["hrdata"] == 0xFACE1234


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
    report = run_python_uvm_test(_lowered(module), sequence, name="python_uvm_axis")

    assert report.passed is True
    assert report.coverage["labels_seen"]["beat0"] == 1
    assert report.traces[-1].expected["tready"] == 1


def test_python_uvm_supports_ready_valid_sequences():
    module = SimModule(
        name="ready_valid_sink",
        signals=(
            Signal("data", width=16, kind="input"),
            Signal("valid", width=1, kind="input"),
            Signal("ready", width=1, kind="output"),
        ),
        assignments=(
            Assignment("ready", SignalRef("valid")),
        ),
        outputs=("ready",),
    )
    sequence = ready_valid_sequence(
        (
            ReadyValidTransfer(data=0x1234, expected_ready=1, label="beat0"),
            ReadyValidTransfer(data=0x5678, expected_ready=1, label="beat1"),
        )
    )
    report = run_python_uvm_test(
        _lowered(module),
        sequence,
        reference_model=ready_valid_reference_model(),
        name="python_uvm_ready_valid",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["beat0"] == 1
    assert report.traces[-1].expected["ready"] == 1


def test_python_uvm_supports_reqrsp_sequences():
    module = SimModule(
        name="reqrsp_endpoint",
        signals=(
            Signal("addr", width=12, kind="input"),
            Signal("req", width=16, kind="input"),
            Signal("write", width=1, kind="input"),
            Signal("strb", width=4, kind="input"),
            Signal("req_valid", width=1, kind="input"),
            Signal("req_ready", width=1, kind="output"),
            Signal("rsp", width=16, kind="output"),
            Signal("rsp_valid", width=1, kind="output"),
            Signal("rsp_ready", width=1, kind="input"),
        ),
        assignments=(
            Assignment("req_ready", ConstExpr(1, 1)),
            Assignment("rsp", BinaryExpr("+", SignalRef("req"), ConstExpr(1, 16))),
            Assignment("rsp_valid", SignalRef("req_valid")),
        ),
        outputs=("req_ready", "rsp", "rsp_valid"),
    )
    sequence = req_rsp_sequence(
        (
            ReqRspTransfer(req=0x10, addr=0x24, write=1, strb=0xF, expected_req_ready=1, expected_rsp=0x11, label="tx0"),
            ReqRspTransfer(req=0x20, addr=0x28, write=0, strb=0x3, expected_req_ready=1, expected_rsp=0x21, label="tx1"),
        ),
    )
    report = run_python_uvm_test(
        _lowered(module),
        sequence,
        reference_model=req_rsp_reference_model(response_map={0x10: 0x11, 0x20: 0x21}, req_name="req"),
        name="python_uvm_reqrsp",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["tx0"] == 1
    assert report.traces[-1].expected["rsp"] == 0x21


def test_python_uvm_reqrsp_queue_buffers_request_path():
    report = run_python_uvm_test(
        ReqRspQueue(req_width=8, rsp_width=8, depth=2, addr_width=4, write_enable=True, strobe_width=2),
        (
            PythonUvmSequenceItem(
                inputs={
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
                },
                expected={
                    "up_req_ready": 1,
                    "down_req_valid": 0,
                    "up_rsp_valid": 0,
                    "level": 0,
                },
                label="reset",
            ),
            PythonUvmSequenceItem(
                inputs={
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
                },
                expected={
                    "up_req_ready": 1,
                    "down_req_valid": 1,
                    "down_req": 0x12,
                    "down_addr": 3,
                    "down_write": 1,
                    "down_strb": 0x3,
                    "up_rsp": 0x80,
                    "up_rsp_valid": 1,
                    "level": 1,
                },
                label="push0",
            ),
            PythonUvmSequenceItem(
                inputs={
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
                },
                expected={
                    "up_req_ready": 0,
                    "down_req_valid": 1,
                    "down_req": 0x12,
                    "down_addr": 3,
                    "down_write": 1,
                    "down_strb": 0x3,
                    "up_rsp_valid": 0,
                    "level": 2,
                },
                label="push1",
            ),
            PythonUvmSequenceItem(
                inputs={
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
                },
                expected={
                    "up_req_ready": 1,
                    "down_req_valid": 1,
                    "down_req": 0x34,
                    "down_addr": 5,
                    "down_write": 0,
                    "down_strb": 0x1,
                    "up_rsp_valid": 0,
                    "level": 2,
                },
                label="pop_push",
            ),
        ),
        name="python_uvm_reqrsp_queue",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["pop_push"] == 1


def test_python_uvm_reqrsp_queue_bundled_sideband_buffers_request_path():
    report = run_python_uvm_test(
        ReqRspQueue(
            req_width=8,
            rsp_width=8,
            depth=2,
            addr_width=4,
            write_enable=True,
            strobe_width=2,
            bundle_sideband=True,
        ),
        (
            PythonUvmSequenceItem(
                inputs={
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
                },
                expected={
                    "up_req_ready": 1,
                    "down_req_valid": 0,
                    "up_rsp_valid": 0,
                    "level": 0,
                },
                label="reset",
            ),
            PythonUvmSequenceItem(
                inputs={
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
                },
                expected={
                    "up_req_ready": 1,
                    "down_req_valid": 1,
                    "down_req": 0x12,
                    "down_addr": 3,
                    "down_write": 1,
                    "down_strb": 0x3,
                    "up_rsp": 0x80,
                    "up_rsp_valid": 1,
                    "level": 1,
                },
                label="push0",
            ),
            PythonUvmSequenceItem(
                inputs={
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
                },
                expected={
                    "up_req_ready": 0,
                    "down_req_valid": 1,
                    "down_req": 0x12,
                    "down_addr": 3,
                    "down_write": 1,
                    "down_strb": 0x3,
                    "up_rsp_valid": 0,
                    "level": 2,
                },
                label="push1",
            ),
            PythonUvmSequenceItem(
                inputs={
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
                },
                expected={
                    "up_req_ready": 1,
                    "down_req_valid": 1,
                    "down_req": 0x34,
                    "down_addr": 5,
                    "down_write": 0,
                    "down_strb": 0x1,
                    "up_rsp_valid": 0,
                    "level": 2,
                },
                label="pop_push",
            ),
        ),
        name="python_uvm_reqrsp_queue_bundled",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["pop_push"] == 1


def test_python_uvm_reqrsp_trace_checker_accepts_protocol_clean_trace():
    module = SimModule(
        name="reqrsp_checker_endpoint",
        signals=(
            Signal("addr", width=8, kind="input"),
            Signal("req", width=8, kind="input"),
            Signal("write", width=1, kind="input"),
            Signal("strb", width=2, kind="input"),
            Signal("req_valid", width=1, kind="input"),
            Signal("req_ready", width=1, kind="output"),
            Signal("rsp", width=8, kind="output"),
            Signal("rsp_valid", width=1, kind="output"),
            Signal("rsp_ready", width=1, kind="input"),
        ),
        assignments=(
            Assignment("req_ready", ConstExpr(1, 1)),
            Assignment("rsp", BinaryExpr("+", SignalRef("req"), ConstExpr(1, 8))),
            Assignment("rsp_valid", SignalRef("req_valid")),
        ),
        outputs=("req_ready", "rsp", "rsp_valid"),
    )
    report = run_python_uvm_test(
        _lowered(module),
        req_rsp_sequence(
            (
                ReqRspTransfer(
                    req=0x10,
                    addr=0x4,
                    write=1,
                    strb=0x3,
                    expected_req_ready=1,
                    expected_rsp=0x11,
                    label="tx0",
                ),
                ReqRspTransfer(
                    req=0x20,
                    addr=0x8,
                    write=0,
                    strb=0x1,
                    expected_req_ready=1,
                    expected_rsp=0x21,
                    label="tx1",
                ),
            )
        ),
        reference_model=req_rsp_reference_model(
            response_map={0x10: 0x11, 0x20: 0x21},
            req_name="req",
        ),
        name="python_uvm_reqrsp_checker",
    )
    check = check_reqrsp_trace(report)

    assert report.passed is True
    assert check.passed is True


def test_python_uvm_skid_buffer_preserves_ready_valid_protocol_under_backpressure():
    report = run_python_uvm_test(
        SkidBuffer(16),
        (
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0},
                expected={"in_ready": 1, "out_valid": 0, "out_data": 0},
                label="reset",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0x12, "in_valid": 1, "out_ready": 0},
                expected={"in_ready": 0, "out_valid": 1, "out_data": 0x12},
                label="capture",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 0},
                expected={"in_ready": 0, "out_valid": 1, "out_data": 0x12},
                label="stall",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1},
                expected={"in_ready": 1, "out_valid": 0, "out_data": 0},
                label="drain",
            ),
        ),
        name="python_uvm_skid_buffer",
    )
    protocol_check = check_ready_valid_trace(
        report.traces[1:],
        data_name="out_data",
        valid_name="out_valid",
        ready_name="out_ready",
    )

    assert report.passed is True
    assert protocol_check.passed is True
    assert report.coverage["labels_seen"]["stall"] == 1


def test_python_uvm_ready_valid_fifo_preserves_order_under_backpressure():
    report = run_python_uvm_test(
        ReadyValidFIFO(width=8, depth=2),
        (
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0},
                expected={"in_ready": 1, "out_valid": 0, "out_data": 0, "level": 0},
                label="reset",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0x11, "in_valid": 1, "out_ready": 0},
                expected={"in_ready": 1, "out_valid": 1, "out_data": 0x11, "level": 1},
                label="push0",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0x22, "in_valid": 1, "out_ready": 0},
                expected={"in_ready": 0, "out_valid": 1, "out_data": 0x11, "level": 2},
                label="push1",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0x33, "in_valid": 1, "out_ready": 1},
                expected={"in_ready": 1, "out_valid": 1, "out_data": 0x22, "level": 2},
                label="pop_push",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1},
                expected={"in_ready": 1, "out_valid": 1, "out_data": 0x33, "level": 1},
                label="pop1",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1},
                expected={"in_ready": 1, "out_valid": 0, "out_data": 0, "level": 0},
                label="pop2",
            ),
        ),
        name="python_uvm_ready_valid_fifo",
    )
    protocol_check = check_ready_valid_trace(
        report.traces[1:],
        data_name="out_data",
        valid_name="out_valid",
        ready_name="out_ready",
    )

    assert report.passed is True
    assert protocol_check.passed is True
    assert report.coverage["labels_seen"]["pop_push"] == 1


def test_python_uvm_ready_valid_register_holds_data_under_backpressure():
    report = run_python_uvm_test(
        ReadyValidRegister(width=8),
        (
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0},
                expected={"in_ready": 1, "out_valid": 0, "out_data": 0},
                label="reset",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0x44, "in_valid": 1, "out_ready": 0},
                expected={"in_ready": 0, "out_valid": 1, "out_data": 0x44},
                label="capture",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0x55, "in_valid": 1, "out_ready": 0},
                expected={"in_ready": 0, "out_valid": 1, "out_data": 0x44},
                label="stall",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0x66, "in_valid": 1, "out_ready": 1},
                expected={"in_ready": 1, "out_valid": 1, "out_data": 0x66},
                label="replace",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1},
                expected={"in_ready": 1, "out_valid": 0, "out_data": 0},
                label="drain",
            ),
        ),
        name="python_uvm_ready_valid_register",
    )
    protocol_check = check_ready_valid_trace(
        report.traces[1:],
        data_name="out_data",
        valid_name="out_valid",
        ready_name="out_ready",
    )

    assert report.passed is True
    assert protocol_check.passed is True
    assert report.coverage["labels_seen"]["stall"] == 1


def test_python_uvm_ready_valid_register_hold_payload_preserves_data_on_drain():
    report = run_python_uvm_test(
        ReadyValidRegister(width=8, hold_payload=True),
        (
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 1, "in_data": 0, "in_valid": 0, "out_ready": 0},
                expected={"in_ready": 1, "out_valid": 0, "out_data": 0},
                label="reset",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0x44, "in_valid": 1, "out_ready": 0},
                expected={"in_ready": 0, "out_valid": 1, "out_data": 0x44},
                label="capture",
            ),
            PythonUvmSequenceItem(
                inputs={"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1},
                expected={"in_ready": 1, "out_valid": 0, "out_data": 0x44},
                label="drain_hold",
            ),
        ),
        name="python_uvm_ready_valid_register_hold_payload",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["drain_hold"] == 1


def test_python_uvm_supports_axilite_protocol_sequences():
    sequence = axilite_protocol_sequence(
        (
            AxiLiteTransfer(addr=0x10, write=True, wdata=0x11223344, label="axil_wr"),
            AxiLiteTransfer(addr=0x10, write=False, expected_rdata=0x11223344, label="axil_rd"),
        )
    )

    assert len(sequence) == 4
    assert sequence[0].inputs["awvalid"] == 1
    assert sequence[0].inputs["wvalid"] == 1
    assert sequence[1].expected == {"bvalid": 1}
    assert sequence[2].inputs["arvalid"] == 1
    assert sequence[3].expected == {"rvalid": 1, "rdata": 0x11223344}


def test_python_uvm_axilite_register_bank_runs_with_protocol_vip():
    report = run_python_uvm_test(
        AXI4LiteRegisterBank(depth=8),
        axilite_protocol_sequence(
            (
                AxiLiteTransfer(
                    addr=0x10,
                    write=True,
                    wdata=0x11223344,
                    wstrb=0x5,
                    label="axil_wr",
                ),
                AxiLiteTransfer(
                    addr=0x10,
                    write=False,
                    expected_rdata=0x00220044,
                    label="axil_rd",
                ),
            ),
            extra_inputs={"clk": 0, "rst": 0},
        ),
        reference_model=axilite_reference_model(storage={}, read_output_name="rdata"),
        name="python_uvm_axilite_register_bank",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["axil_wr"] == 2
    assert report.coverage["labels_seen"]["axil_rd"] == 2
    assert report.traces[1].expected["bvalid"] == 1
    assert report.traces[3].expected["rdata"] == 0x00220044


def test_python_uvm_axilite_register_bank_split_control_state_runs_with_protocol_vip():
    report = run_python_uvm_test(
        AXI4LiteRegisterBank(depth=8, split_control_state=True),
        axilite_protocol_sequence(
            (
                AxiLiteTransfer(
                    addr=0x10,
                    write=True,
                    wdata=0x11223344,
                    wstrb=0x5,
                    label="axil_wr",
                ),
                AxiLiteTransfer(
                    addr=0x10,
                    write=False,
                    expected_rdata=0x00220044,
                    label="axil_rd",
                ),
            ),
            extra_inputs={"clk": 0, "rst": 0},
        ),
        reference_model=axilite_reference_model(storage={}, read_output_name="rdata"),
        name="python_uvm_axilite_register_bank_split_control_state",
    )

    assert report.passed is True
    assert report.coverage["labels_seen"]["axil_wr"] == 2
    assert report.coverage["labels_seen"]["axil_rd"] == 2
    assert report.traces[1].expected["bvalid"] == 1
    assert report.traces[3].expected["rdata"] == 0x00220044


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

    with builder.build(_raw_axi4_memory_module(), tmp_path / "compiled_axi4_uvm") as simulator:
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
