"""UVM-style verification for the JPEG decoder.

1. Local Python-UVM smoke: drive a byte stream and observe handshake / output.
2. Generated SV/UVM collateral plus iverilog packaging probe.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from rtlgen_x.verify import (
    PythonUvmSequenceItem,
    describe_verification_interface,
    generate_uvm_collateral,
    generate_uvm_runtime_bundle,
    probe_iverilog_uvm_collateral,
    run_python_uvm_test,
    write_uvm_collateral,
    write_uvm_runtime_bundle,
)

from jpeg_decoder.dsl_modules import JpegDecoder, ZIGZAG_ORDER


BUILD = "jpeg_decoder/build/uvm"


def _build_gradient_bytes():
    """Return the byte stream for a single gradient test block."""
    coeffs = np.zeros((8, 8), dtype=np.int16)
    coeffs[0, 0] = 128
    coeffs[0, 1] = 64
    coeffs[1, 0] = -32

    zz = np.zeros(64, dtype=np.int16)
    for i, ri in enumerate(ZIGZAG_ORDER):
        zz[i] = coeffs.flat[ri]

    tokens = []
    i = 0
    while i < 64:
        if zz[i] == 0:
            run = 0
            j = i
            while j < 64 and zz[j] == 0 and run < 14:
                run += 1
                j += 1
            if j >= 64:
                tokens.append(0xF000)
                break
            tokens.append((run << 12) | (zz[j] & 0xFFF))
            i = j + 1
        else:
            tokens.append(zz[i] & 0xFFF)
            i += 1

    bytes_stream = []
    for t in tokens:
        bytes_stream.append(t & 0xFF)
        bytes_stream.append((t >> 8) & 0xFF)
    return bytes_stream


def _module():
    return JpegDecoder()


def test_describe_verification_interface():
    vi = describe_verification_interface(_module())
    input_names = {p.name for p in vi.inputs}
    output_names = {p.name for p in vi.outputs}
    assert "s_axis_tdata" in input_names
    assert "s_axis_tvalid" in input_names
    assert "m_axis_tdata" in output_names
    assert "m_axis_tvalid" in output_names
    print("Verification interface OK")


def test_python_uvm_smoke():
    """Drive the gradient block through the Python-UVM plumbing."""
    bytes_stream = _build_gradient_bytes()
    sequence = [PythonUvmSequenceItem(
        inputs={"clk": 0, "rst": 1, "s_axis_tdata": 0, "s_axis_tvalid": 0, "m_axis_tready": 1},
        label="reset",
    )]
    for idx, b in enumerate(bytes_stream):
        sequence.append(PythonUvmSequenceItem(
            inputs={
                "clk": 0, "rst": 0,
                "s_axis_tdata": b,
                "s_axis_tvalid": 1,
                "m_axis_tready": 1,
            },
            label=f"byte{idx}",
        ))
    # Drain bubbles.
    for i in range(300):
        sequence.append(PythonUvmSequenceItem(
            inputs={
                "clk": 0, "rst": 0,
                "s_axis_tdata": 0,
                "s_axis_tvalid": 0,
                "m_axis_tready": 1,
            },
            label=f"drain{i}",
        ))
    report = run_python_uvm_test(_module(), sequence, name="jpeg_decoder_uvm_smoke")
    assert report.total_cycles > 0
    print(f"Python-UVM smoke passed: {report.total_cycles} cycles")


def test_generate_uvm_collateral():
    collateral = generate_uvm_collateral(_module(), clock_name="clk")
    write_uvm_collateral(collateral, f"{BUILD}/collateral")
    am = collateral.artifact_map() if callable(getattr(collateral, "artifact_map")) else collateral.artifact_map
    assert am
    print("UVM collateral generated")


def test_uvm_runtime_bundle_written():
    bundle = generate_uvm_runtime_bundle(_module(), clock_name="clk")
    write_uvm_runtime_bundle(bundle, f"{BUILD}/runtime", include_runtime_package=False)
    files = os.listdir(f"{BUILD}/runtime")
    assert any("dut" in f.lower() and f.endswith(".sv") for f in files)
    print("UVM runtime bundle written")


def test_iverilog_uvm_packaging_probe():
    collateral = generate_uvm_collateral(_module(), clock_name="clk")
    probe = probe_iverilog_uvm_collateral(collateral, output_dir=f"{BUILD}/iverilog_probe")
    if probe.skipped_reason:
        print(f"iverilog probe skipped: {probe.skipped_reason}")
        return
    assert probe.interface_compile_ok or probe.package_compile_ok
    print(f"iverilog probe OK: interface_compile_ok={probe.interface_compile_ok}, "
          f"package_compile_ok={probe.package_compile_ok}")


if __name__ == "__main__":
    test_describe_verification_interface()
    test_python_uvm_smoke()
    test_generate_uvm_collateral()
    test_uvm_runtime_bundle_written()
    test_iverilog_uvm_packaging_probe()
