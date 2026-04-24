#!/usr/bin/env python3
"""
End-to-end synthesis demo for the 8b10b Decoder (registered version).

Flow:
    RTL IR (decoder_8b10b.py) → BLIF (with .latch) → ABC (strash + resyn2 + map)
    → gf65.lib technology mapping → mapped Verilog

The sequential registers are preserved as latches in the mapped netlist
because gf65.lib does not contain usable DFF/Latch cells (1 seq cell skipped).
"""

import os
import sys
import tempfile

sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import BLIFEmitter, ABCSynthesizer, WireLoadModel
from examples.decoder_8b10b import Decoder8b10b


def main():
    dut = Decoder8b10b()

    with tempfile.TemporaryDirectory() as tmpdir:
        blif_path = os.path.join(tmpdir, "decoder_8b10b.blif")
        lib_path = "/Users/yangfan/rtlgen/gf65.lib"
        mapped_v = os.path.join(tmpdir, "decoder_8b10b_mapped.v")

        # 1. Generate BLIF
        print("=" * 60)
        print("Step 1: Generate BLIF from RTL IR")
        print("=" * 60)
        blif = BLIFEmitter().emit(dut)
        with open(blif_path, "w") as f:
            f.write(blif)
        print(f"BLIF written to: {blif_path}")
        print(f"BLIF size: {len(blif)} chars, {blif.count(chr(10))} lines")
        latch_count = sum(1 for line in blif.splitlines() if line.strip().startswith(".latch"))
        subckt_count = sum(1 for line in blif.splitlines() if ".subckt" in line)
        print(f"  .latch count: {latch_count}")
        print(f"  .subckt count: {subckt_count}")

        # 2. Liberty
        print("\n" + "=" * 60)
        print("Step 2: Technology Library")
        print("=" * 60)
        print(f"Liberty file: {lib_path}")
        print(f"Liberty size: {os.path.getsize(lib_path)} bytes")

        # 3. Run ABC synthesis
        print("\n" + "=" * 60)
        print("Step 3: Run ABC Synthesis")
        print("=" * 60)
        abc_path = os.path.expanduser("~/.local/bin/abc")
        synth = ABCSynthesizer(abc_path=abc_path)
        if not synth.is_available():
            print(f"ERROR: ABC not found at {abc_path}.")
            sys.exit(1)

        print(f"ABC binary: {synth.abc_path}")
        result = synth.run(
            input_blif=blif_path,
            liberty=lib_path,
            output_verilog=mapped_v,
            wlm=WireLoadModel(slope=0.05, intercept=0.01),
            cwd=tmpdir,
        )

        print(f"Area  : {result.area}")
        print(f"Delay : {result.delay}")
        print(f"Gates : {result.gates}")
        print(f"Depth : {result.depth}")

        # 4. Show mapped Verilog snippet
        print("\n" + "=" * 60)
        print("Step 4: Mapped Verilog (first 15 lines)")
        print("=" * 60)
        if result.mapped_verilog:
            for line in result.mapped_verilog.splitlines()[:15]:
                print(line)
        else:
            print("No mapped Verilog generated.")

        # 5. Check for sequential elements in mapped Verilog
        print("\n" + "=" * 60)
        print("Step 5: Sequential elements in mapped Verilog")
        print("=" * 60)
        if result.mapped_verilog:
            lines = result.mapped_verilog.splitlines()
            seq_lines = [l for l in lines if "always" in l.lower() or "reg " in l.lower()]
            print(f"Found {len(seq_lines)} lines containing 'always' or 'reg'.")
            for line in seq_lines[:5]:
                print(line.strip())

        # 6. ABC stdout tail
        print("\n" + "=" * 60)
        print("Step 6: ABC stdout tail")
        print("=" * 60)
        for line in result.stdout.splitlines()[-20:]:
            if any(k in line.lower() for k in ["area", "delay", "gate", "depth", "lat", "lev", "nd "]):
                print(line)

        print("\n" + "=" * 60)
        print("Sequential synthesis demo completed successfully!")
        print("=" * 60)


if __name__ == "__main__":
    main()
