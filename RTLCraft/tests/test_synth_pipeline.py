#!/usr/bin/env python3
"""
Integration tests for the RTL IR → BLIF → ABC synthesis pipeline.

Since ABC is not installed in this environment, these tests verify:
- BLIF generation correctness
- ABC script generation
- Graceful fallback when ABC is missing
- Liberty file generation
"""

import os
import sys
import tempfile

sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen import (
    Module, Input, Output, Reg,
    BLIFEmitter, ABCSynthesizer, WireLoadModel, generate_demo_liberty,
)


class SimpleAdder(Module):
    def __init__(self):
        super().__init__("SimpleAdder")
        self.a = Input(4, "a")
        self.b = Input(4, "b")
        self.y = Output(4, "y")
        @self.comb
        def _logic():
            self.y <<= self.a + self.b


def test_blif_contains_models_and_subckt():
    m = SimpleAdder()
    blif = BLIFEmitter().emit(m)
    # Default adder is now pure AIG (no .subckt)
    assert ".model SimpleAdder" in blif
    assert ".inputs a[0]" in blif
    assert ".outputs y[0]" in blif
    assert "01 1" in blif  # XOR from AIG adder
    assert "11 1" in blif  # AND from AIG adder


def test_abc_script_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        lib_path = os.path.join(tmpdir, "tech.lib")
        generate_demo_liberty(lib_path)
        synth = ABCSynthesizer(abc_path="/fake/abc")
        script = synth.generate_abc_script(
            input_blif="design.blif",
            liberty=lib_path,
            output_verilog="mapped.v",
            output_aig="design.aag",
            wlm=WireLoadModel(slope=0.03, intercept=0.02),
        )
        assert 'read_blif "design.blif"' in script
        assert "strash" in script
        assert "balance" in script and "rewrite" in script
        assert f'read_lib "{lib_path}"' in script
        assert "map" in script
        assert 'write_aiger -z "design.aag"' in script
        assert 'write_verilog "mapped.v"' in script


def test_abc_missing_fallback():
    synth = ABCSynthesizer(abc_path="/nonexistent/abc")
    with tempfile.TemporaryDirectory() as tmpdir:
        blif_path = os.path.join(tmpdir, "design.blif")
        with open(blif_path, "w") as f:
            f.write(".model test\n.end\n")
        with pytest.raises(RuntimeError) as exc_info:
            synth.run(
                input_blif=blif_path,
                liberty="tech.lib",
                output_verilog=os.path.join(tmpdir, "mapped.v"),
                cwd=tmpdir,
            )
        assert "ABC executable not found" in str(exc_info.value)
        script_path = os.path.join(tmpdir, "run_abc.sh")
        assert os.path.exists(script_path)


def test_demo_liberty_generation():
    content = generate_demo_liberty()
    assert "library (demo_tech)" in content
    assert "cell (NAND2X1)" in content
    assert "cell (INVX1)" in content
    assert "cell (DFFX1)" in content
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lib", delete=False) as f:
        f.write(content)
        path = f.name
    generate_demo_liberty(path)
    with open(path) as f:
        assert "NAND2X1" in f.read()
    os.unlink(path)


def test_wire_load_model():
    wlm = WireLoadModel(name="wlm_160k", slope=0.04, intercept=0.01)
    assert wlm.estimate_delay(1) == pytest.approx(0.05)
    assert wlm.estimate_delay(4) == pytest.approx(0.17)


def test_end_to_end_file_generation():
    """Generate BLIF, liberty, and ABC script without running ABC."""
    m = SimpleAdder()
    with tempfile.TemporaryDirectory() as tmpdir:
        blif_path = os.path.join(tmpdir, "adder.blif")
        lib_path = os.path.join(tmpdir, "demo.lib")
        mapped_v = os.path.join(tmpdir, "mapped.v")

        blif = BLIFEmitter().emit(m)
        with open(blif_path, "w") as f:
            f.write(blif)

        generate_demo_liberty(lib_path)

        synth = ABCSynthesizer(abc_path="/fake/abc")
        script = synth.generate_abc_script(
            input_blif=blif_path,
            liberty=lib_path,
            output_verilog=mapped_v,
            wlm=WireLoadModel(),
        )
        abc_cmd_path = blif_path + ".abc"
        with open(abc_cmd_path, "w") as f:
            f.write(script)

        assert os.path.exists(blif_path)
        assert os.path.exists(lib_path)
        assert os.path.exists(abc_cmd_path)
        with open(abc_cmd_path) as f:
            data = f.read()
            assert "read_blif" in data
            assert "read_lib" in data
