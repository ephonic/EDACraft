"""Generate Verilog for the JPEG decoder and run a quick iverilog smoke test."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pathlib import Path

from rtlgen_x.dsl import VerilogEmitter, EmitProfile

from jpeg_decoder.dsl_modules import JpegDecoder, JpegIdct8x8, JpegDequantZigzag, JpegEntropyDecoder


def main():
    build_dir = Path("jpeg_decoder/build/verilog")
    build_dir.mkdir(parents=True, exist_ok=True)

    for module in [JpegEntropyDecoder, JpegDequantZigzag, JpegIdct8x8]:
        rtl = VerilogEmitter(profile=EmitProfile.review()).emit(module())
        (build_dir / f"{module.__name__}.v").write_text(rtl)
        print(f"Wrote {build_dir / module.__name__}.v")

    # Emit the full design (top + child modules) for the decoder.
    rtl_design = VerilogEmitter(profile=EmitProfile.review()).emit_design(JpegDecoder())
    (build_dir / "JpegDecoder.v").write_text(rtl_design)
    print(f"Wrote {build_dir / 'JpegDecoder.v'} (design)")

    # Try iverilog compile on the design.
    try:
        import subprocess
        result = subprocess.run(
            ["iverilog", "-g2012", "-o", str(build_dir / "JpegDecoder.vvp"), str(build_dir / "JpegDecoder.v")],
            capture_output=True, text=True, timeout=30
        )
        print("iverilog stdout:", result.stdout)
        print("iverilog stderr:", result.stderr)
        print("iverilog return code:", result.returncode)
    except FileNotFoundError:
        print("iverilog not found; skipping compile smoke test")


if __name__ == "__main__":
    main()
