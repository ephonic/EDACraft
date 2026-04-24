"""
Tests for rtlgen.verilog_import — Verilog → rtlgen Python API converter.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from rtlgen.verilog_import import VerilogImporter
from rtlgen.codegen import VerilogEmitter


FIXTURES_DIR = Path(__file__).parent / "verilog_import_fixtures"


class TestVerilogImporter:
    def test_scan_repo_finds_modules(self):
        importer = VerilogImporter(FIXTURES_DIR)
        importer.scan_repo()
        assert "Counter" in importer.modules
        assert "FullAdder" in importer.modules
        assert "Top" in importer.modules

    def test_emit_counter(self):
        importer = VerilogImporter(FIXTURES_DIR)
        importer.scan_repo()
        code = importer.emit_module("Counter")
        assert "class Counter(Module):" in code
        assert "self.clk = Input(1" in code
        assert "self.count = Output(8" in code
        assert "@self.comb" in code
        assert "@self.seq(" in code
        assert "with If(" in code
        assert "with Else():" in code

    def test_emit_full_adder(self):
        importer = VerilogImporter(FIXTURES_DIR)
        importer.scan_repo()
        code = importer.emit_module("FullAdder")
        assert "class FullAdder(Module):" in code
        assert "self.a = Input(1" in code
        assert "self.sum = Output(1" in code
        assert "self.sum <<= " in code

    def test_emit_top_with_params(self):
        importer = VerilogImporter(FIXTURES_DIR)
        importer.scan_repo()
        code = importer.emit_module("Top")
        assert "class Top(Module):" in code
        assert 'self.add_param("WIDTH", 8)' in code
        assert "self.instantiate(" in code

    def test_counter_runnable(self):
        """Generated code should be executable and produce valid Verilog."""
        importer = VerilogImporter(FIXTURES_DIR)
        importer.scan_repo()
        code = importer.emit_module("Counter")

        # Inject required imports into the execution namespace
        namespace = {}
        exec("from rtlgen import Module, Input, Output, Wire, Reg, VerilogEmitter", namespace)
        exec("from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen", namespace)
        exec(code, namespace)

        Counter = namespace["Counter"]
        inst = Counter()
        emitter = VerilogEmitter()
        verilog = emitter.emit(inst)

        assert "module Counter" in verilog
        assert "input clk" in verilog
        assert "input rst" in verilog
        assert "input en" in verilog
        assert "output [7:0] count" in verilog
        assert "assign count = count_reg" in verilog or "always @(*)" in verilog or "always_comb" in verilog
        assert "always @(posedge clk" in verilog or "always_ff" in verilog

    def test_full_adder_runnable(self):
        importer = VerilogImporter(FIXTURES_DIR)
        importer.scan_repo()
        code = importer.emit_module("FullAdder")

        namespace = {}
        exec("from rtlgen import Module, Input, Output, Wire, Reg, VerilogEmitter", namespace)
        exec("from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen", namespace)
        exec(code, namespace)

        FullAdder = namespace["FullAdder"]
        inst = FullAdder()
        emitter = VerilogEmitter()
        verilog = emitter.emit(inst)

        assert "module FullAdder" in verilog
        assert "assign sum = " in verilog
        assert "assign cout = " in verilog

    def test_alu_case(self):
        """Test case statement conversion."""
        importer = VerilogImporter(FIXTURES_DIR)
        importer.scan_repo()
        code = importer.emit_module("ALU")

        namespace = {}
        exec("from rtlgen import Module, Input, Output, Wire, Reg, VerilogEmitter", namespace)
        exec("from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen", namespace)
        exec(code, namespace)

        ALU = namespace["ALU"]
        inst = ALU()
        emitter = VerilogEmitter()
        verilog = emitter.emit(inst)

        assert "module ALU" in verilog
        assert "case (" in verilog
        assert "default:" in verilog


class TestEUConversion:
    """Test conversion of the EU code base."""

    EU_DIR = Path(__file__).parent / "eu"

    @pytest.mark.skipif(not EU_DIR.exists(), reason="EU directory not present")
    def test_eu_scan(self):
        importer = VerilogImporter(self.EU_DIR)
        importer.scan_repo()
        # At least some modules should parse successfully
        assert len(importer.modules) >= 30

    @pytest.mark.skipif(not EU_DIR.exists(), reason="EU directory not present")
    def test_eu_emit_logical(self):
        importer = VerilogImporter(self.EU_DIR)
        importer.scan_repo()
        if "js_vm_logical" not in importer.modules:
            pytest.skip("js_vm_logical not parsed")
        code = importer.emit_module("js_vm_logical")
        assert "class js_vm_logical(Module):" in code
        assert "self.clk = Input(1" in code
        assert "with Switch(" in code
        assert "with sw.case(" in code

    @pytest.mark.skipif(not EU_DIR.exists(), reason="EU directory not present")
    def test_eu_emit_add(self):
        importer = VerilogImporter(self.EU_DIR)
        importer.scan_repo()
        if "add" not in importer.modules:
            pytest.skip("add not parsed")
        code = importer.emit_module("add")
        assert "class add(Module):" in code
        assert "self.clk = Input(1" in code
