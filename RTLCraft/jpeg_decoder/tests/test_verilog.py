"""Generate JPEG RTL and run an iverilog compile smoke test.

The main functional closure for the JPEG path lives in the Python and compiled
simulator regressions. This script keeps `iverilog -g2012` as a lightweight
compatibility check for the emitted SystemVerilog subset.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pathlib import Path
import shutil
import subprocess

import pytest

from rtlgen.dsl import VerilogEmitter, EmitProfile

from jpeg_decoder.dsl_modules import JpegDecoder, JpegIdct8x8, JpegDequantZigzag, JpegEntropyDecoder


def emit_jpeg_verilog_bundle(build_dir):
    build_dir = Path(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    for module in [JpegEntropyDecoder, JpegDequantZigzag, JpegIdct8x8]:
        rtl = VerilogEmitter(profile=EmitProfile.review()).emit(module())
        (build_dir / f"{module.__name__}.v").write_text(rtl)

    # Emit the full design (top + child modules) for the decoder.
    rtl_design = VerilogEmitter(profile=EmitProfile.review()).emit_design(JpegDecoder())
    top_path = build_dir / "JpegDecoder.v"
    top_path.write_text(rtl_design)
    return top_path


def run_iverilog_compile_smoke(build_dir):
    top_path = emit_jpeg_verilog_bundle(build_dir)
    output_path = Path(build_dir) / "JpegDecoder.vvp"
    return subprocess.run(
        ["iverilog", "-g2012", "-o", str(output_path), str(top_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_jpeg_verilog_iverilog_compile_smoke(tmp_path):
    if shutil.which("iverilog") is None:
        pytest.skip("iverilog not installed")

    result = run_iverilog_compile_smoke(tmp_path / "verilog")

    assert result.returncode == 0, result.stderr


def main():
    build_dir = Path("jpeg_decoder/build/verilog")
    top_path = emit_jpeg_verilog_bundle(build_dir)
    print(f"Wrote {top_path} (design)")

    if shutil.which("iverilog") is None:
        print("iverilog not found; skipping compile smoke test")
        return

    result = run_iverilog_compile_smoke(build_dir)
    print("iverilog stdout:", result.stdout)
    print("iverilog stderr:", result.stderr)
    print("iverilog return code:", result.returncode)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
