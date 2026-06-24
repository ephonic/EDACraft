from rtlgen_x.verify import (
    PythonUvmSequenceItem,
    TraceSample,
    check_ahblite_trace,
    check_apb_trace,
    check_axistream_trace,
    check_axilite_trace,
    check_reqrsp_trace,
    check_ready_valid_trace,
    check_wishbone_trace,
    emit_protocol_check_report_markdown,
    run_python_uvm_test,
)
from rtlgen_x.tests.test_python_uvm import (
    _accum_module,
    _axilite_regfile_module,
    _wishbone_regfile_module,
)


def test_ready_valid_checker_flags_payload_change_during_stall():
    report = run_python_uvm_test(
        _accum_module(),
        (
            PythonUvmSequenceItem(inputs={"inp": 0}, expected={"out": 3}, label="warmup"),
        ),
        name="checker_smoke",
    )

    bad_trace = (
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
    check = check_ready_valid_trace(bad_trace)

    assert check.passed is False
    assert any(violation.rule == "ready_valid_payload_stable" for violation in check.violations)


def test_apb_checker_accepts_well_formed_setup_access_trace():
    trace = (
        TraceSample(
            cycle=0,
            inputs={
                "psel": 1,
                "penable": 0,
                "pwrite": 1,
                "paddr": 0x10,
                "pwdata": 0x1234,
                "pstrb": 0xF,
                "pprot": 0,
            },
            outputs={"pready": 0},
            expected={},
        ),
        TraceSample(
            cycle=1,
            inputs={
                "psel": 1,
                "penable": 1,
                "pwrite": 1,
                "paddr": 0x10,
                "pwdata": 0x1234,
                "pstrb": 0xF,
                "pprot": 0,
            },
            outputs={"pready": 1},
            expected={},
        ),
    )
    check = check_apb_trace(trace)

    assert check.passed is True


def test_wishbone_checker_accepts_reference_model_trace():
    report = run_python_uvm_test(
        _wishbone_regfile_module(),
        (
            PythonUvmSequenceItem(
                inputs={
                    "adr_i": 0x10,
                    "dat_i": 0xA5A55A5A,
                    "we_i": 1,
                    "sel_i": 0xF,
                    "stb_i": 1,
                    "cyc_i": 1,
                    "cti_i": 0,
                    "bte_i": 0,
                },
                expected={"ack_o": 1, "err_o": 0, "rty_o": 0, "dat_o": 0},
            ),
        ),
        name="wishbone_checker_trace",
    )
    check = check_wishbone_trace(report)

    assert check.passed is True


def test_axistream_checker_flags_payload_change_during_stall():
    bad_trace = (
        TraceSample(
            cycle=0,
            inputs={"tdata": 0x12, "tvalid": 1, "tlast": 0, "tkeep": 0x3},
            outputs={"tready": 0},
            expected={},
        ),
        TraceSample(
            cycle=1,
            inputs={"tdata": 0x34, "tvalid": 1, "tlast": 0, "tkeep": 0x3},
            outputs={"tready": 0},
            expected={},
        ),
    )
    check = check_axistream_trace(bad_trace)

    assert check.passed is False
    assert any(violation.rule == "ready_valid_payload_stable" for violation in check.violations)


def test_reqrsp_checker_flags_request_payload_change_during_stall():
    bad_trace = (
        TraceSample(
            cycle=0,
            inputs={
                "req": 0x12,
                "addr": 0x24,
                "write": 1,
                "strb": 0xF,
                "req_valid": 1,
                "rsp_ready": 1,
            },
            outputs={"req_ready": 0, "rsp": 0, "rsp_valid": 0},
            expected={},
        ),
        TraceSample(
            cycle=1,
            inputs={
                "req": 0x34,
                "addr": 0x24,
                "write": 1,
                "strb": 0xF,
                "req_valid": 1,
                "rsp_ready": 1,
            },
            outputs={"req_ready": 0, "rsp": 0, "rsp_valid": 0},
            expected={},
        ),
    )
    check = check_reqrsp_trace(bad_trace)

    assert check.passed is False
    assert any(violation.rule == "req_payload_stable" for violation in check.violations)


def test_reqrsp_checker_flags_response_payload_change_during_stall():
    bad_trace = (
        TraceSample(
            cycle=0,
            inputs={
                "req": 0,
                "addr": 0,
                "write": 0,
                "strb": 0,
                "req_valid": 0,
                "rsp_ready": 0,
            },
            outputs={"req_ready": 1, "rsp": 0x55, "rsp_valid": 1},
            expected={},
        ),
        TraceSample(
            cycle=1,
            inputs={
                "req": 0,
                "addr": 0,
                "write": 0,
                "strb": 0,
                "req_valid": 0,
                "rsp_ready": 0,
            },
            outputs={"req_ready": 1, "rsp": 0x77, "rsp_valid": 1},
            expected={},
        ),
    )
    check = check_reqrsp_trace(bad_trace)

    assert check.passed is False
    assert any(violation.rule == "rsp_payload_stable" for violation in check.violations)


def test_ahblite_checker_flags_control_change_while_waiting():
    bad_trace = (
        TraceSample(
            cycle=0,
            inputs={
                "hsel": 1,
                "htrans": 2,
                "haddr": 0x100,
                "hwrite": 1,
                "hsize": 2,
                "hburst": 0,
                "hprot": 0,
                "hwdata": 0x55,
            },
            outputs={"hready": 0, "hresp": 0, "hrdata": 0},
            expected={},
        ),
        TraceSample(
            cycle=1,
            inputs={
                "hsel": 1,
                "htrans": 2,
                "haddr": 0x104,
                "hwrite": 1,
                "hsize": 2,
                "hburst": 0,
                "hprot": 0,
                "hwdata": 0x55,
            },
            outputs={"hready": 0, "hresp": 0, "hrdata": 0},
            expected={},
        ),
    )
    check = check_ahblite_trace(bad_trace)

    assert check.passed is False
    assert any(violation.rule == "transfer_control_stable" for violation in check.violations)


def test_axilite_checker_flags_write_address_change_while_stalled():
    bad_trace = (
        run_python_uvm_test(
            _axilite_regfile_module(),
            (
                PythonUvmSequenceItem(
                    inputs={"awaddr": 0x10, "awvalid": 1, "awprot": 0, "wdata": 0, "wstrb": 0, "wvalid": 0, "bready": 0, "araddr": 0, "arvalid": 0, "arprot": 0, "rready": 0},
                    expected={"bvalid": 0, "rvalid": 0, "rdata": 0},
                ),
            ),
            name="axil_checker_seed",
        ).traces[0].__class__(
            cycle=0,
            inputs={"awaddr": 0x10, "awvalid": 1, "awprot": 0},
            outputs={"awready": 0},
            expected={},
        ),
        run_python_uvm_test(
            _axilite_regfile_module(),
            (
                PythonUvmSequenceItem(
                    inputs={"awaddr": 0x14, "awvalid": 1, "awprot": 0, "wdata": 0, "wstrb": 0, "wvalid": 0, "bready": 0, "araddr": 0, "arvalid": 0, "arprot": 0, "rready": 0},
                    expected={"bvalid": 0, "rvalid": 0, "rdata": 0},
                ),
            ),
            name="axil_checker_seed2",
        ).traces[0].__class__(
            cycle=1,
            inputs={"awaddr": 0x14, "awvalid": 1, "awprot": 0},
            outputs={"awready": 0},
            expected={},
        ),
    )
    check = check_axilite_trace(bad_trace)
    markdown = emit_protocol_check_report_markdown(check)

    assert check.passed is False
    assert any(violation.rule == "aw_payload_stable" for violation in check.violations)
    assert "AXI4Lite Protocol Check" in markdown
