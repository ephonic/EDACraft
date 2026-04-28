"""
rtlgen.uvmgen — UVM Testbench 代码生成器

基于 pyRTL 描述的 Module，自动生成标准的 UVM 验证平台骨架：
- SystemVerilog Interface
- UVM Transaction / Sequencer / Sequence / Driver / Monitor / Agent
- UVM Scoreboard / Environment / Test / Top-level Testbench
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from rtlgen.core import Input, Module, Output
from rtlgen.regmodel import RegBlock


class UVMEmitter:
    """UVM 代码发射器。"""

    def __init__(self, indent: str = "    "):
        self.indent = indent

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def emit_full_testbench(
        self,
        module: Module,
        interface_name: Optional[str] = None,
        pkg_name: Optional[str] = None,
        clock_name: str = "clk",
    ) -> Dict[str, str]:
        """为指定 Module 生成完整 UVM testbench 的所有文件内容。

        返回字典: {filename: content}
        """
        base = module.name
        if_name = interface_name or f"{base}_if"
        pkg = pkg_name or f"{base}_pkg"

        files: Dict[str, str] = {}
        files[f"{if_name}.sv"] = self.emit_interface(module, if_name, clock_name)
        files[f"{pkg}.sv"] = self.emit_package(pkg)
        files[f"{base}_transaction.sv"] = self.emit_transaction(module, base, pkg)
        files[f"{base}_sequencer.sv"] = self.emit_sequencer(module, base, pkg)
        files[f"{base}_sequence.sv"] = self.emit_sequence(module, base, pkg)
        files[f"{base}_driver.sv"] = self.emit_driver(module, base, pkg, if_name, clock_name)
        files[f"{base}_monitor.sv"] = self.emit_monitor(module, base, pkg, if_name, clock_name)
        files[f"{base}_agent.sv"] = self.emit_agent(module, base, pkg)
        files[f"{base}_scoreboard.sv"] = self.emit_scoreboard(module, base, pkg)
        files[f"{base}_env.sv"] = self.emit_env(module, base, pkg)
        files[f"{base}_test.sv"] = self.emit_test(module, base, pkg)
        files["tb_top.sv"] = self.emit_tb_top(module, base, if_name, clock_name)
        return files

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    @staticmethod
    def _to_sv_width(width: int) -> str:
        return f"[{width - 1}:0] " if width > 1 else ""

    def _find_clock(self, module: Module, clock_name: str) -> Optional[str]:
        for n in [clock_name, "clk", "clock", "aclk", "pclk"]:
            if n in module._inputs:
                return n
        return None

    def _port_list(self, module: Module) -> List[Tuple[str, int, str]]:
        """返回 [(name, width, direction), ...]，direction 为 'input'/'output'。"""
        ports = []
        for n, s in module._inputs.items():
            ports.append((n, s.width, "input"))
        for n, s in module._outputs.items():
            ports.append((n, s.width, "output"))
        return ports

    def _data_ports(self, module: Module, clock_name: str) -> List[Tuple[str, int, str]]:
        """排除时钟和复位的端口列表。"""
        ignore = {clock_name, "rst", "reset", "rst_n", "reset_n", "aresetn", "presetn"}
        return [(n, w, d) for n, w, d in self._port_list(module) if n not in ignore]

    # -----------------------------------------------------------------
    # Interface
    # -----------------------------------------------------------------
    def emit_interface(self, module: Module, if_name: str, clock_name: str) -> str:
        clk = self._find_clock(module, clock_name) or clock_name
        lines: List[str] = [
            f"interface {if_name} (input logic {clk});",
            "",
        ]

        for n, w, d in self._port_list(module):
            if n == clk:
                continue
            sv_w = self._to_sv_width(w)
            lines.append(f"    logic {sv_w}{n};")

        lines.append("")
        lines.append(f"    clocking cb @(posedge {clk});")
        for n, w, d in self._data_ports(module, clk):
            dir_mod = "output" if d == "input" else "input"
            sv_w = self._to_sv_width(w)
            lines.append(f"        {dir_mod} {sv_w}{n};")
        lines.append("    endclocking")
        lines.append("")
        lines.append("    modport MP (clocking cb);")
        lines.append(f"endinterface : {if_name}")
        lines.append("")
        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Package
    # -----------------------------------------------------------------
    def emit_package(self, pkg_name: str) -> str:
        return f"""package {pkg_name};
    import uvm_pkg::*;
    `include "uvm_macros.svh"
endpackage : {pkg_name}
"""

    # -----------------------------------------------------------------
    # Transaction
    # -----------------------------------------------------------------
    def emit_transaction(self, module: Module, base: str, pkg_name: str) -> str:
        cls = f"{base}_transaction"
        clk = self._find_clock(module, "clk") or "clk"
        data_ports = self._data_ports(module, clk)

        fields: List[str] = []
        rand_fields: List[str] = []
        for n, w, d in data_ports:
            sv_w = self._to_sv_width(w)
            fields.append(f"    rand logic {sv_w}{n};")
            rand_fields.append(f'        `uvm_field_int({n}, UVM_ALL_ON)')

        fields_str = "\n".join(fields)
        rand_str = "\n".join(rand_fields)

        return f"""`ifndef {cls.upper()}_SV
`define {cls.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {cls} extends uvm_sequence_item;
    `uvm_object_utils_begin({cls})
{rand_str}
    `uvm_object_utils_end

{fields_str}

    function new(string name = "{cls}");
        super.new(name);
    endfunction

endclass : {cls}

`endif // {cls.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Sequencer
    # -----------------------------------------------------------------
    def emit_sequencer(self, module: Module, base: str, pkg_name: str) -> str:
        cls = f"{base}_sequencer"
        txn = f"{base}_transaction"
        return f"""`ifndef {cls.upper()}_SV
`define {cls.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {cls} extends uvm_sequencer #({txn});
    `uvm_component_utils({cls})

    function new(string name = "{cls}", uvm_component parent = null);
        super.new(name, parent);
    endfunction

endclass : {cls}

`endif // {cls.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Sequence
    # -----------------------------------------------------------------
    def emit_sequence(self, module: Module, base: str, pkg_name: str) -> str:
        cls = f"{base}_base_sequence"
        txn = f"{base}_transaction"
        return f"""`ifndef {cls.upper()}_SV
`define {cls.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {cls} extends uvm_sequence #({txn});
    `uvm_object_utils({cls})

    function new(string name = "{cls}");
        super.new(name);
    endfunction

    virtual task pre_body();
        if (starting_phase != null)
            starting_phase.raise_objection(this);
    endtask

    virtual task post_body();
        if (starting_phase != null)
            starting_phase.drop_objection(this);
    endtask

endclass : {cls}

// Simple random sequence
class {base}_random_sequence extends {cls};
    `uvm_object_utils({base}_random_sequence)

    rand int num_transactions = 10;

    function new(string name = "{base}_random_sequence");
        super.new(name);
    endfunction

    virtual task body();
        {txn} txn;
        repeat (num_transactions) begin
            txn = {txn}::type_id::create("txn");
            start_item(txn);
            if (!txn.randomize()) `uvm_fatal(get_name(), "Randomize failed")
            finish_item(txn);
        end
    endtask

endclass : {base}_random_sequence

`endif // {cls.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Driver
    # -----------------------------------------------------------------
    def emit_driver(self, module: Module, base: str, pkg_name: str, if_name: str, clock_name: str) -> str:
        cls = f"{base}_driver"
        txn = f"{base}_transaction"
        clk = self._find_clock(module, clock_name) or clock_name
        inputs = self._data_ports(module, clk)
        input_names = [n for n, w, d in inputs if d == "input"]

        drive_lines = "\n".join([
            f"            vif.{n} <= req.{n};"
            for n in input_names
        ]) or "            // no data inputs to drive"

        return f"""`ifndef {cls.upper()}_SV
`define {cls.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {cls} extends uvm_driver #({txn});
    `uvm_component_utils({cls})

    virtual {if_name}.MP vif;

    function new(string name = "{cls}", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual task run_phase(uvm_phase phase);
        forever begin
            seq_item_port.get_next_item(req);
            @vif.cb;
{drive_lines}
            seq_item_port.item_done();
        end
    endtask

endclass : {cls}

`endif // {cls.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Monitor
    # -----------------------------------------------------------------
    def emit_monitor(self, module: Module, base: str, pkg_name: str, if_name: str, clock_name: str) -> str:
        cls = f"{base}_monitor"
        txn = f"{base}_transaction"
        clk = self._find_clock(module, clock_name) or clock_name
        outputs = [(n, w) for n, w, d in self._data_ports(module, clk) if d == "output"]

        sample_lines = "\n".join([
            f"            txn.{n} = vif.{n};"
            for n, w in outputs
        ]) or "            // no data outputs to sample"

        return f"""`ifndef {cls.upper()}_SV
`define {cls.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {cls} extends uvm_monitor;
    `uvm_component_utils({cls})

    virtual {if_name}.MP vif;
    uvm_analysis_port #({txn}) ap;

    function new(string name = "{cls}", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        ap = new("ap", this);
    endfunction

    virtual task run_phase(uvm_phase phase);
        {txn} txn;
        forever begin
            @vif.cb;
            txn = {txn}::type_id::create("txn");
{sample_lines}
            ap.write(txn);
        end
    endtask

endclass : {cls}

`endif // {cls.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Agent
    # -----------------------------------------------------------------
    def emit_agent(self, module: Module, base: str, pkg_name: str) -> str:
        cls = f"{base}_agent"
        return f"""`ifndef {cls.upper()}_SV
`define {cls.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {cls} extends uvm_agent;
    `uvm_component_utils({cls})

    {base}_sequencer sqr;
    {base}_driver    drv;
    {base}_monitor   mon;

    function new(string name = "{cls}", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        sqr = {base}_sequencer::type_id::create("sqr", this);
        drv = {base}_driver::type_id::create("drv", this);
        mon = {base}_monitor::type_id::create("mon", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        drv.seq_item_port.connect(sqr.seq_item_export);
    endfunction

endclass : {cls}

`endif // {cls.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Scoreboard
    # -----------------------------------------------------------------
    def emit_scoreboard(self, module: Module, base: str, pkg_name: str) -> str:
        cls = f"{base}_scoreboard"
        txn = f"{base}_transaction"
        return f"""`ifndef {cls.upper()}_SV
`define {cls.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {cls} extends uvm_scoreboard;
    `uvm_component_utils({cls})

    uvm_analysis_imp #({txn}, {cls}) exp;

    function new(string name = "{cls}", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        exp = new("exp", this);
    endfunction

    virtual function void write({txn} txn);
        `uvm_info(get_name(), $sformatf("Received transaction: %s", txn.convert2string()), UVM_MEDIUM)
        // TODO: add checking logic
    endfunction

endclass : {cls}

`endif // {cls.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Environment
    # -----------------------------------------------------------------
    def emit_env(self, module: Module, base: str, pkg_name: str) -> str:
        cls = f"{base}_env"
        return f"""`ifndef {cls.upper()}_SV
`define {cls.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {cls} extends uvm_env;
    `uvm_component_utils({cls})

    {base}_agent       agent;
    {base}_scoreboard  sb;

    function new(string name = "{cls}", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        agent = {base}_agent::type_id::create("agent", this);
        sb    = {base}_scoreboard::type_id::create("sb", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        agent.mon.ap.connect(sb.exp);
    endfunction

endclass : {cls}

`endif // {cls.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Test
    # -----------------------------------------------------------------
    def emit_test(self, module: Module, base: str, pkg_name: str) -> str:
        cls = f"{base}_base_test"
        return f"""`ifndef {cls.upper()}_SV
`define {cls.upper()}_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class {cls} extends uvm_test;
    `uvm_component_utils({cls})

    {base}_env env;

    function new(string name = "{cls}", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        env = {base}_env::type_id::create("env", this);
    endfunction

    virtual task run_phase(uvm_phase phase);
        {base}_random_sequence seq;
        phase.raise_objection(this);
        seq = {base}_random_sequence::type_id::create("seq");
        seq.start(env.agent.sqr);
        phase.drop_objection(this);
    endtask

endclass : {cls}

`endif // {cls.upper()}_SV
"""

    # -----------------------------------------------------------------
    # Protocol VIP shortcuts
    # -----------------------------------------------------------------
    def emit_apb_vip(self, addr_width=32, data_width=32, pkg_name="apb_vip_pkg"):
        from rtlgen.uvmvip import UVMVIPEmitter
        return UVMVIPEmitter().emit_apb_vip(addr_width, data_width, pkg_name)

    def emit_axi4lite_vip(self, addr_width=32, data_width=32, pkg_name="axi4lite_vip_pkg"):
        from rtlgen.uvmvip import UVMVIPEmitter
        return UVMVIPEmitter().emit_axi4lite_vip(addr_width, data_width, pkg_name)

    def emit_axi4_vip(self, id_width=4, addr_width=32, data_width=32, user_width=0, pkg_name="axi4_vip_pkg"):
        from rtlgen.uvmvip import UVMVIPEmitter
        return UVMVIPEmitter().emit_axi4_vip(id_width, addr_width, data_width, user_width, pkg_name)

    # -----------------------------------------------------------------
    # RAL Generation
    # -----------------------------------------------------------------
    def emit_ral(self, regblock: RegBlock, pkg_name: str) -> Dict[str, str]:
        base = regblock.name
        reg_classes: List[str] = []
        for reg, _ in regblock.registers:
            reg_classes.append(self._emit_reg_class(reg, base))

        block_class = self._emit_reg_block_class(regblock, base, pkg_name)

        content = f"""`ifndef {base.upper()}_REG_BLOCK_SV
`define {base.upper()}_REG_BLOCK_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

{chr(10).join(reg_classes)}
{block_class}

`endif // {base.upper()}_REG_BLOCK_SV
"""
        return {f"{base}_reg_block.sv": content}

    def _emit_reg_class(self, reg, base: str) -> str:
        cls = f"{base}_{reg.name}_reg"
        field_builds: List[str] = []
        lsb = 0
        for f in reg.fields:
            reset_hex = f"{f.width}'h{f.reset:x}"
            field_builds.append(
                f"        {f.name} = uvm_reg_field::type_id::create(\"{f.name}\");\n"
                f"        {f.name}.configure(this, {f.width}, {lsb}, \"{f.access}\", 0, {reset_hex}, 1, 1, 1);"
            )
            lsb += f.width
        fields_decl = "\n".join(f"    rand uvm_reg_field {f.name};" for f in reg.fields)
        build_body = "\n".join(field_builds)
        return f"""class {cls} extends uvm_reg;
    `uvm_object_utils({cls})

{fields_decl}

    function new(string name = "{cls}");
        super.new(name, {reg.width}, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
{build_body}
    endfunction

endclass : {cls}
"""

    def _emit_reg_block_class(self, regblock: RegBlock, base: str, pkg_name: str) -> str:
        cls = f"{base}_reg_block"
        reg_decls = "\n".join(f"    rand {base}_{reg.name}_reg {reg.name};" for reg, _ in regblock.registers)
        reg_builds: List[str] = []
        for reg, offset in regblock.registers:
            offset_hex = f"32'h{offset:02x}"
            reg_builds.append(
                f"        {reg.name} = {base}_{reg.name}_reg::type_id::create(\"{reg.name}\");\n"
                f"        {reg.name}.configure(this, null, \"\");\n"
                f"        {reg.name}.build();\n"
                '        default_map.add_reg(%s, %s, "%s");' % (reg.name, offset_hex, reg.fields[0].access if reg.fields else "RW")
            )
        build_body = "\n".join(reg_builds)
        return f"""class {cls} extends uvm_reg_block;
    `uvm_object_utils({cls})

{reg_decls}

    function new(string name = "{cls}");
        super.new(name, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        default_map = create_map("default_map", 32'h{regblock.base_addr:08x}, 4, UVM_LITTLE_ENDIAN);
{build_body}
    endfunction

endclass : {cls}
"""

    # -----------------------------------------------------------------
    # Top-level Testbench
    # -----------------------------------------------------------------
    def emit_tb_top(self, module: Module, base: str, if_name: str, clock_name: str) -> str:
        clk = self._find_clock(module, clock_name) or clock_name
        clk_period = "10"

        rst_name = ""
        for r in ["rst", "reset", "rst_n", "reset_n", "aresetn"]:
            if r in module._inputs:
                rst_name = r
                break

        rst_wire = f"    logic {rst_name};\n" if rst_name else ""
        rst_conn = f"        .{rst_name}({rst_name}),\n" if rst_name else ""

        port_conns = []
        for n, s in module._inputs.items():
            if n == clk or n == rst_name:
                continue
            port_conns.append(f"        .{n}(vif.{n}),")
        for n, s in module._outputs.items():
            port_conns.append(f"        .{n}(vif.{n}),")
        port_conns_str = "\n".join(port_conns).rstrip(",")

        return f"""`timescale 1ns/1ps

module tb_top;

    logic {clk};
{rst_wire}
    {if_name} vif (.clk({clk}));

    {module.name} dut (
        .{clk}({clk}),
{rst_conn}{port_conns_str}
    );

    initial begin
        uvm_config_db # (virtual {if_name}.MP)::set(null, "*", "vif", vif);
        run_test("{base}_base_test");
    end

    initial begin
        {clk} = 0;
        forever #{clk_period} {clk} = ~{clk};
    end

endmodule
"""
