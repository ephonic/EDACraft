"""
rtlgen.uvmvip — 专用总线协议 VIP 生成器

为 rtlgen.protocols 中的标准总线协议（APB、AXI4-Lite）生成
协议感知的 UVM VIP：interface、transaction、driver、monitor、agent 等。
"""
from __future__ import annotations

from typing import Dict


class UVMVIPEmitter:
    """协议 VIP 发射器。"""

    def __init__(self, indent: str = "    "):
        self.indent = indent

    # -----------------------------------------------------------------
    # APB VIP
    # -----------------------------------------------------------------
    def emit_apb_vip(
        self,
        addr_width: int = 32,
        data_width: int = 32,
        pkg_name: str = "apb_vip_pkg",
    ) -> Dict[str, str]:
        strb_width = data_width // 8
        files: Dict[str, str] = {}
        files["apb_if.sv"] = self._emit_apb_if(addr_width, data_width, strb_width)
        files["apb_transaction.sv"] = self._emit_apb_transaction(data_width, addr_width, strb_width, pkg_name)
        files["apb_sequencer.sv"] = self._emit_apb_sequencer(pkg_name)
        files["apb_sequence.sv"] = self._emit_apb_sequence(pkg_name)
        files["apb_driver.sv"] = self._emit_apb_driver(pkg_name)
        files["apb_monitor.sv"] = self._emit_apb_monitor(pkg_name)
        files["apb_agent.sv"] = self._emit_apb_agent(pkg_name)
        return files

    def _emit_apb_if(self, addr_width: int, data_width: int, strb_width: int) -> str:
        return f"""interface apb_if (input logic pclk, input logic presetn);
    logic                      psel;
    logic                      penable;
    logic                      pwrite;
    logic  [{addr_width-1}:0] paddr;
    logic  [{data_width-1}:0] pwdata;
    logic  [{strb_width-1}:0] pstrb;
    logic  [2:0]               pprot;
    logic  [{data_width-1}:0] prdata;
    logic                      pready;
    logic                      pslverr;

    clocking cb @(posedge pclk);
        output psel, penable, pwrite, paddr, pwdata, pstrb, pprot;
        input  prdata, pready, pslverr;
    endclocking

    modport MP (clocking cb);
endinterface
"""

    def _emit_apb_transaction(self, data_width: int, addr_width: int, strb_width: int, pkg_name: str) -> str:
        return f"""`ifndef APB_TRANSACTION_SV
`define APB_TRANSACTION_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class apb_transaction extends uvm_sequence_item;
    `uvm_object_utils_begin(apb_transaction)
        `uvm_field_int(addr, UVM_ALL_ON)
        `uvm_field_int(data, UVM_ALL_ON)
        `uvm_field_int(pwrite, UVM_ALL_ON)
        `uvm_field_int(pprot, UVM_ALL_ON)
        `uvm_field_int(pstrb, UVM_ALL_ON)
        `uvm_field_int(pready, UVM_ALL_ON)
        `uvm_field_int(pslverr, UVM_ALL_ON)
    `uvm_object_utils_end

    rand bit [{addr_width-1}:0] addr;
    rand bit [{data_width-1}:0] data;
    rand bit                    pwrite;
    rand bit [2:0]              pprot;
    rand bit [{strb_width-1}:0] pstrb;
    bit                         pready;
    bit                         pslverr;

    function new(string name = "apb_transaction");
        super.new(name);
    endfunction

endclass : apb_transaction

`endif // APB_TRANSACTION_SV
"""

    def _emit_apb_sequencer(self, pkg_name: str) -> str:
        return f"""`ifndef APB_SEQUENCER_SV
`define APB_SEQUENCER_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class apb_sequencer extends uvm_sequencer #(apb_transaction);
    `uvm_component_utils(apb_sequencer)

    function new(string name = "apb_sequencer", uvm_component parent = null);
        super.new(name, parent);
    endfunction

endclass : apb_sequencer

`endif // APB_SEQUENCER_SV
"""

    def _emit_apb_sequence(self, pkg_name: str) -> str:
        return f"""`ifndef APB_BASE_SEQUENCE_SV
`define APB_BASE_SEQUENCE_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class apb_base_sequence extends uvm_sequence #(apb_transaction);
    `uvm_object_utils(apb_base_sequence)

    function new(string name = "apb_base_sequence");
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

endclass : apb_base_sequence

class apb_random_sequence extends apb_base_sequence;
    `uvm_object_utils(apb_random_sequence)

    rand int num_transactions = 10;

    function new(string name = "apb_random_sequence");
        super.new(name);
    endfunction

    virtual task body();
        apb_transaction txn;
        repeat (num_transactions) begin
            txn = apb_transaction::type_id::create("txn");
            start_item(txn);
            if (!txn.randomize()) `uvm_fatal(get_name(), "Randomize failed")
            finish_item(txn);
        end
    endtask

endclass : apb_random_sequence

`endif // APB_BASE_SEQUENCE_SV
"""

    def _emit_apb_driver(self, pkg_name: str) -> str:
        return f"""`ifndef APB_DRIVER_SV
`define APB_DRIVER_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class apb_driver extends uvm_driver #(apb_transaction);
    `uvm_component_utils(apb_driver)

    virtual apb_if.MP vif;

    function new(string name = "apb_driver", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual task run_phase(uvm_phase phase);
        forever begin
            seq_item_port.get_next_item(req);
            // SETUP phase
            vif.cb.psel    <= 1'b1;
            vif.cb.penable <= 1'b0;
            vif.cb.pwrite  <= req.pwrite;
            vif.cb.paddr   <= req.addr;
            vif.cb.pwdata  <= req.data;
            vif.cb.pstrb   <= req.pstrb;
            vif.cb.pprot   <= req.pprot;
            @vif.cb;
            // ENABLE phase
            vif.cb.penable <= 1'b1;
            while (vif.cb.pready == 1'b0) @vif.cb;
            req.pready  = vif.cb.pready;
            req.pslverr = vif.cb.pslverr;
            if (!req.pwrite) req.data = vif.cb.prdata;
            vif.cb.psel    <= 1'b0;
            vif.cb.penable <= 1'b0;
            seq_item_port.item_done();
        end
    endtask

endclass : apb_driver

`endif // APB_DRIVER_SV
"""

    def _emit_apb_monitor(self, pkg_name: str) -> str:
        return f"""`ifndef APB_MONITOR_SV
`define APB_MONITOR_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class apb_monitor extends uvm_monitor;
    `uvm_component_utils(apb_monitor)

    virtual apb_if.MP vif;
    uvm_analysis_port #(apb_transaction) ap;

    function new(string name = "apb_monitor", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        ap = new("ap", this);
    endfunction

    virtual task run_phase(uvm_phase phase);
        apb_transaction txn;
        forever begin
            @vif.cb;
            if (vif.cb.psel && vif.cb.penable && vif.cb.pready) begin
                txn = apb_transaction::type_id::create("txn");
                txn.addr    = vif.cb.paddr;
                txn.pwrite  = vif.cb.pwrite;
                txn.pprot   = vif.cb.pprot;
                txn.pstrb   = vif.cb.pstrb;
                txn.pready  = vif.cb.pready;
                txn.pslverr = vif.cb.pslverr;
                if (txn.pwrite)
                    txn.data = vif.cb.pwdata;
                else
                    txn.data = vif.cb.prdata;
                ap.write(txn);
            end
        end
    endtask

endclass : apb_monitor

`endif // APB_MONITOR_SV
"""

    def _emit_apb_agent(self, pkg_name: str) -> str:
        return f"""`ifndef APB_AGENT_SV
`define APB_AGENT_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class apb_agent extends uvm_agent;
    `uvm_component_utils(apb_agent)

    apb_sequencer sqr;
    apb_driver    drv;
    apb_monitor   mon;

    function new(string name = "apb_agent", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        sqr = apb_sequencer::type_id::create("sqr", this);
        drv = apb_driver::type_id::create("drv", this);
        mon = apb_monitor::type_id::create("mon", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        drv.seq_item_port.connect(sqr.seq_item_export);
    endfunction

endclass : apb_agent

`endif // APB_AGENT_SV
"""

    # -----------------------------------------------------------------
    # AXI4-Lite VIP
    # -----------------------------------------------------------------
    def emit_axi4lite_vip(
        self,
        addr_width: int = 32,
        data_width: int = 32,
        pkg_name: str = "axi4lite_vip_pkg",
    ) -> Dict[str, str]:
        strb_width = data_width // 8
        files: Dict[str, str] = {}
        files["axi4lite_if.sv"] = self._emit_axi4lite_if(addr_width, data_width, strb_width)
        files["axi4lite_transaction.sv"] = self._emit_axi4lite_transaction(data_width, addr_width, strb_width, pkg_name)
        files["axi4lite_sequencer.sv"] = self._emit_axi4lite_sequencer(pkg_name)
        files["axi4lite_sequence.sv"] = self._emit_axi4lite_sequence(pkg_name)
        files["axi4lite_driver.sv"] = self._emit_axi4lite_driver(pkg_name)
        files["axi4lite_monitor.sv"] = self._emit_axi4lite_monitor(pkg_name)
        files["axi4lite_agent.sv"] = self._emit_axi4lite_agent(pkg_name)
        return files

    def _emit_axi4lite_if(self, addr_width: int, data_width: int, strb_width: int) -> str:
        return f"""interface axi4lite_if (input logic aclk, input logic aresetn);
    // Write address channel
    logic  [{addr_width-1}:0] awaddr;
    logic                     awvalid;
    logic                     awready;
    logic  [2:0]              awprot;
    // Write data channel
    logic  [{data_width-1}:0] wdata;
    logic  [{strb_width-1}:0] wstrb;
    logic                     wvalid;
    logic                     wready;
    // Write response channel
    logic  [1:0]              bresp;
    logic                     bvalid;
    logic                     bready;
    // Read address channel
    logic  [{addr_width-1}:0] araddr;
    logic                     arvalid;
    logic                     arready;
    logic  [2:0]              arprot;
    // Read data channel
    logic  [{data_width-1}:0] rdata;
    logic  [1:0]              rresp;
    logic                     rvalid;
    logic                     rready;

    clocking cb @(posedge aclk);
        output awaddr, awvalid, awprot;
        input  awready;
        output wdata, wstrb, wvalid;
        input  wready;
        input  bresp, bvalid;
        output bready;
        output araddr, arvalid, arprot;
        input  arready;
        input  rdata, rresp, rvalid;
        output rready;
    endclocking

    modport MP (clocking cb);
endinterface
"""

    def _emit_axi4lite_transaction(self, data_width: int, addr_width: int, strb_width: int, pkg_name: str) -> str:
        return f"""`ifndef AXI4LITE_TRANSACTION_SV
`define AXI4LITE_TRANSACTION_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4lite_transaction extends uvm_sequence_item;
    `uvm_object_utils_begin(axi4lite_transaction)
        `uvm_field_int(addr, UVM_ALL_ON)
        `uvm_field_int(data, UVM_ALL_ON)
        `uvm_field_int(wstrb, UVM_ALL_ON)
        `uvm_field_int(write, UVM_ALL_ON)
        `uvm_field_int(resp, UVM_ALL_ON)
        `uvm_field_int(prot, UVM_ALL_ON)
    `uvm_object_utils_end

    rand bit [{addr_width-1}:0] addr;
    rand bit [{data_width-1}:0] data;
    rand bit [{strb_width-1}:0] wstrb;
    rand bit                    write; // 1 = write, 0 = read
    rand bit [2:0]              prot;
    bit      [1:0]              resp;

    function new(string name = "axi4lite_transaction");
        super.new(name);
    endfunction

endclass : axi4lite_transaction

`endif // AXI4LITE_TRANSACTION_SV
"""

    def _emit_axi4lite_sequencer(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4LITE_SEQUENCER_SV
`define AXI4LITE_SEQUENCER_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4lite_sequencer extends uvm_sequencer #(axi4lite_transaction);
    `uvm_component_utils(axi4lite_sequencer)

    function new(string name = "axi4lite_sequencer", uvm_component parent = null);
        super.new(name, parent);
    endfunction

endclass : axi4lite_sequencer

`endif // AXI4LITE_SEQUENCER_SV
"""

    def _emit_axi4lite_sequence(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4LITE_BASE_SEQUENCE_SV
`define AXI4LITE_BASE_SEQUENCE_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4lite_base_sequence extends uvm_sequence #(axi4lite_transaction);
    `uvm_object_utils(axi4lite_base_sequence)

    function new(string name = "axi4lite_base_sequence");
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

endclass : axi4lite_base_sequence

class axi4lite_random_sequence extends axi4lite_base_sequence;
    `uvm_object_utils(axi4lite_random_sequence)

    rand int num_transactions = 10;

    function new(string name = "axi4lite_random_sequence");
        super.new(name);
    endfunction

    virtual task body();
        axi4lite_transaction txn;
        repeat (num_transactions) begin
            txn = axi4lite_transaction::type_id::create("txn");
            start_item(txn);
            if (!txn.randomize()) `uvm_fatal(get_name(), "Randomize failed")
            finish_item(txn);
        end
    endtask

endclass : axi4lite_random_sequence

`endif // AXI4LITE_BASE_SEQUENCE_SV
"""

    def _emit_axi4lite_driver(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4LITE_DRIVER_SV
`define AXI4LITE_DRIVER_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4lite_driver extends uvm_driver #(axi4lite_transaction);
    `uvm_component_utils(axi4lite_driver)

    virtual axi4lite_if.MP vif;

    function new(string name = "axi4lite_driver", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual task run_phase(uvm_phase phase);
        forever begin
            seq_item_port.get_next_item(req);
            if (req.write)
                do_write(req);
            else
                do_read(req);
            seq_item_port.item_done();
        end
    endtask

    virtual task do_write(axi4lite_transaction txn);
        fork
            begin
                vif.cb.awaddr  <= txn.addr;
                vif.cb.awprot  <= txn.prot;
                vif.cb.awvalid <= 1'b1;
                @vif.cb;
                while (vif.cb.awready == 1'b0) @vif.cb;
                vif.cb.awvalid <= 1'b0;
            end
            begin
                vif.cb.wdata  <= txn.data;
                vif.cb.wstrb  <= txn.wstrb;
                vif.cb.wvalid <= 1'b1;
                @vif.cb;
                while (vif.cb.wready == 1'b0) @vif.cb;
                vif.cb.wvalid <= 1'b0;
            end
        join
        vif.cb.bready <= 1'b1;
        @vif.cb;
        while (vif.cb.bvalid == 1'b0) @vif.cb;
        txn.resp = vif.cb.bresp;
        vif.cb.bready <= 1'b0;
    endtask

    virtual task do_read(axi4lite_transaction txn);
        vif.cb.araddr  <= txn.addr;
        vif.cb.arprot  <= txn.prot;
        vif.cb.arvalid <= 1'b1;
        @vif.cb;
        while (vif.cb.arready == 1'b0) @vif.cb;
        vif.cb.arvalid <= 1'b0;

        vif.cb.rready <= 1'b1;
        @vif.cb;
        while (vif.cb.rvalid == 1'b0) @vif.cb;
        txn.data = vif.cb.rdata;
        txn.resp = vif.cb.rresp;
        vif.cb.rready <= 1'b0;
    endtask

endclass : axi4lite_driver

`endif // AXI4LITE_DRIVER_SV
"""

    def _emit_axi4lite_monitor(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4LITE_MONITOR_SV
`define AXI4LITE_MONITOR_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4lite_monitor extends uvm_monitor;
    `uvm_component_utils(axi4lite_monitor)

    virtual axi4lite_if.MP vif;
    uvm_analysis_port #(axi4lite_transaction) ap;

    function new(string name = "axi4lite_monitor", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        ap = new("ap", this);
    endfunction

    virtual task run_phase(uvm_phase phase);
        fork
            write_channel_monitor();
            read_channel_monitor();
        join_none
    endtask

    virtual task write_channel_monitor();
        bit [$bits(vif.cb.awaddr)-1:0] awaddr_l;
        bit [2:0]                        awprot_l;
        bit [$bits(vif.cb.wdata)-1:0]   wdata_l;
        bit [$bits(vif.cb.wstrb)-1:0]   wstrb_l;
        forever begin
            @vif.cb;
            if (vif.cb.awvalid && vif.cb.awready) begin
                awaddr_l = vif.cb.awaddr;
                awprot_l = vif.cb.awprot;
            end
            if (vif.cb.wvalid && vif.cb.wready) begin
                wdata_l = vif.cb.wdata;
                wstrb_l = vif.cb.wstrb;
            end
            if (vif.cb.bvalid && vif.cb.bready) begin
                axi4lite_transaction txn;
                txn = axi4lite_transaction::type_id::create("txn");
                txn.addr  = awaddr_l;
                txn.prot  = awprot_l;
                txn.data  = wdata_l;
                txn.wstrb = wstrb_l;
                txn.write = 1'b1;
                txn.resp  = vif.cb.bresp;
                ap.write(txn);
            end
        end
    endtask

    virtual task read_channel_monitor();
        bit [$bits(vif.cb.araddr)-1:0] araddr_l;
        bit [2:0]                        arprot_l;
        forever begin
            @vif.cb;
            if (vif.cb.arvalid && vif.cb.arready) begin
                araddr_l = vif.cb.araddr;
                arprot_l = vif.cb.arprot;
            end
            if (vif.cb.rvalid && vif.cb.rready) begin
                axi4lite_transaction txn;
                txn = axi4lite_transaction::type_id::create("txn");
                txn.addr  = araddr_l;
                txn.prot  = arprot_l;
                txn.data  = vif.cb.rdata;
                txn.write = 1'b0;
                txn.resp  = vif.cb.rresp;
                ap.write(txn);
            end
        end
    endtask

endclass : axi4lite_monitor

`endif // AXI4LITE_MONITOR_SV
"""

    def _emit_axi4lite_agent(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4LITE_AGENT_SV
`define AXI4LITE_AGENT_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4lite_agent extends uvm_agent;
    `uvm_component_utils(axi4lite_agent)

    axi4lite_sequencer sqr;
    axi4lite_driver    drv;
    axi4lite_monitor   mon;

    function new(string name = "axi4lite_agent", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        sqr = axi4lite_sequencer::type_id::create("sqr", this);
        drv = axi4lite_driver::type_id::create("drv", this);
        mon = axi4lite_monitor::type_id::create("mon", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        drv.seq_item_port.connect(sqr.seq_item_export);
    endfunction

endclass : axi4lite_agent

`endif // AXI4LITE_AGENT_SV
"""


    # -----------------------------------------------------------------
    # AXI4 VIP
    # -----------------------------------------------------------------
    def emit_axi4_vip(
        self,
        id_width: int = 4,
        addr_width: int = 32,
        data_width: int = 32,
        user_width: int = 0,
        pkg_name: str = "axi4_vip_pkg",
    ) -> Dict[str, str]:
        strb_width = data_width // 8
        files: Dict[str, str] = {}
        files["axi4_if.sv"] = self._emit_axi4_if(addr_width, data_width, strb_width, id_width, user_width)
        files["axi4_transaction.sv"] = self._emit_axi4_transaction(data_width, addr_width, strb_width, id_width, user_width, pkg_name)
        files["axi4_sequencer.sv"] = self._emit_axi4_sequencer(pkg_name)
        files["axi4_sequence.sv"] = self._emit_axi4_sequence(pkg_name)
        files["axi4_driver.sv"] = self._emit_axi4_driver(pkg_name)
        files["axi4_monitor.sv"] = self._emit_axi4_monitor(pkg_name)
        files["axi4_agent.sv"] = self._emit_axi4_agent(pkg_name)
        return files

    def _emit_axi4_if(self, addr_width: int, data_width: int, strb_width: int, id_width: int, user_width: int) -> str:
        uw_decl = f"    logic  [{user_width-1}:0] " if user_width > 0 else "    logic "
        awuser_lines = (
            f"    logic  [{user_width-1}:0] awuser;\n" if user_width > 0 else ""
        )
        wuser_lines = (
            f"    logic  [{user_width-1}:0] wuser;\n" if user_width > 0 else ""
        )
        buser_lines = (
            f"    logic  [{user_width-1}:0] buser;\n" if user_width > 0 else ""
        )
        aruser_lines = (
            f"    logic  [{user_width-1}:0] aruser;\n" if user_width > 0 else ""
        )
        ruser_lines = (
            f"    logic  [{user_width-1}:0] ruser;\n" if user_width > 0 else ""
        )
        return f"""interface axi4_if (input logic aclk, input logic aresetn);
    // Write address channel
    logic  [{id_width-1}:0]   awid;
    logic  [{addr_width-1}:0] awaddr;
    logic  [7:0]              awlen;
    logic  [2:0]              awsize;
    logic  [1:0]              awburst;
    logic                     awlock;
    logic  [3:0]              awcache;
    logic  [2:0]              awprot;
    logic  [3:0]              awqos;
    logic  [3:0]              awregion;
    logic                     awvalid;
    logic                     awready;{awuser_lines}
    // Write data channel
    logic  [{data_width-1}:0] wdata;
    logic  [{strb_width-1}:0] wstrb;
    logic                     wlast;
    logic                     wvalid;
    logic                     wready;{wuser_lines}
    // Write response channel
    logic  [{id_width-1}:0]   bid;
    logic  [1:0]              bresp;
    logic                     bvalid;
    logic                     bready;{buser_lines}
    // Read address channel
    logic  [{id_width-1}:0]   arid;
    logic  [{addr_width-1}:0] araddr;
    logic  [7:0]              arlen;
    logic  [2:0]              arsize;
    logic  [1:0]              arburst;
    logic                     arlock;
    logic  [3:0]              arcache;
    logic  [2:0]              arprot;
    logic  [3:0]              arqos;
    logic  [3:0]              arregion;
    logic                     arvalid;
    logic                     arready;{aruser_lines}
    // Read data channel
    logic  [{id_width-1}:0]   rid;
    logic  [{data_width-1}:0] rdata;
    logic  [1:0]              rresp;
    logic                     rlast;
    logic                     rvalid;
    logic                     rready;{ruser_lines}

    clocking cb @(posedge aclk);
        output awid, awaddr, awlen, awsize, awburst, awlock, awcache, awprot, awqos, awregion, awvalid;{awuser_lines.replace("logic", "output")}
        input  awready;
        output wdata, wstrb, wlast, wvalid;{wuser_lines.replace("logic", "output")}
        input  wready;
        input  bid, bresp, bvalid;
        output bready;
        output arid, araddr, arlen, arsize, arburst, arlock, arcache, arprot, arqos, arregion, arvalid;{aruser_lines.replace("logic", "output")}
        input  arready;
        input  rid, rdata, rresp, rlast, rvalid;
        output rready;{ruser_lines.replace("logic", "input ")}
    endclocking

    modport MP (clocking cb);
endinterface
"""

    def _emit_axi4_transaction(self, data_width: int, addr_width: int, strb_width: int, id_width: int, user_width: int, pkg_name: str) -> str:
        uw = f"        `uvm_field_int(awuser, UVM_ALL_ON)\n        `uvm_field_int(wuser, UVM_ALL_ON)\n        `uvm_field_int(aruser, UVM_ALL_ON)\n        `uvm_field_int(ruser, UVM_ALL_ON)\n" if user_width > 0 else ""
        udecl = f"    rand bit [{user_width-1}:0] awuser;\n    rand bit [{user_width-1}:0] wuser;\n    rand bit [{user_width-1}:0] aruser;\n    bit      [{user_width-1}:0] ruser;\n" if user_width > 0 else ""
        return f"""`ifndef AXI4_TRANSACTION_SV
`define AXI4_TRANSACTION_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4_transaction extends uvm_sequence_item;
    `uvm_object_utils_begin(axi4_transaction)
        `uvm_field_int(id, UVM_ALL_ON)
        `uvm_field_int(addr, UVM_ALL_ON)
        `uvm_field_int(len, UVM_ALL_ON)
        `uvm_field_int(size, UVM_ALL_ON)
        `uvm_field_int(burst, UVM_ALL_ON)
        `uvm_field_int(prot, UVM_ALL_ON)
        `uvm_field_int(cache, UVM_ALL_ON)
        `uvm_field_int(qos, UVM_ALL_ON)
        `uvm_field_int(region, UVM_ALL_ON)
        `uvm_field_int(lock, UVM_ALL_ON)
        `uvm_field_int(write, UVM_ALL_ON)
        `uvm_field_int(resp, UVM_ALL_ON)
        `uvm_field_int(last, UVM_ALL_ON)
        `uvm_field_array_int(data, UVM_ALL_ON)
        `uvm_field_array_int(strb, UVM_ALL_ON)
{uw}    `uvm_object_utils_end

    rand bit [{id_width-1}:0]   id;
    rand bit [{addr_width-1}:0] addr;
    rand bit [7:0]              len;
    rand bit [2:0]              size;
    rand bit [1:0]              burst;
    rand bit [2:0]              prot;
    rand bit [3:0]              cache;
    rand bit [3:0]              qos;
    rand bit [3:0]              region;
    rand bit                    lock;
    rand bit                    write;
    rand bit [{data_width-1}:0] data[];
    rand bit [{strb_width-1}:0] strb[];
    bit      [1:0]              resp;
    bit                           last;
{udecl}
    constraint data_size_c {{ data.size() == len + 1; }}
    constraint strb_size_c {{ strb.size() == len + 1; }}

    function new(string name = "axi4_transaction");
        super.new(name);
    endfunction

endclass : axi4_transaction

`endif // AXI4_TRANSACTION_SV
"""

    def _emit_axi4_sequencer(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4_SEQUENCER_SV
`define AXI4_SEQUENCER_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4_sequencer extends uvm_sequencer #(axi4_transaction);
    `uvm_component_utils(axi4_sequencer)

    function new(string name = "axi4_sequencer", uvm_component parent = null);
        super.new(name, parent);
    endfunction

endclass : axi4_sequencer

`endif // AXI4_SEQUENCER_SV
"""

    def _emit_axi4_sequence(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4_BASE_SEQUENCE_SV
`define AXI4_BASE_SEQUENCE_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4_base_sequence extends uvm_sequence #(axi4_transaction);
    `uvm_object_utils(axi4_base_sequence)

    function new(string name = "axi4_base_sequence");
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

endclass : axi4_base_sequence

class axi4_random_sequence extends axi4_base_sequence;
    `uvm_object_utils(axi4_random_sequence)

    rand int num_transactions = 5;

    function new(string name = "axi4_random_sequence");
        super.new(name);
    endfunction

    virtual task body();
        axi4_transaction txn;
        repeat (num_transactions) begin
            txn = axi4_transaction::type_id::create("txn");
            start_item(txn);
            if (!txn.randomize() with {{ len inside {{[0:3]}}; }})
                `uvm_fatal(get_name(), "Randomize failed")
            finish_item(txn);
        end
    endtask

endclass : axi4_random_sequence

`endif // AXI4_BASE_SEQUENCE_SV
"""

    def _emit_axi4_driver(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4_DRIVER_SV
`define AXI4_DRIVER_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4_driver extends uvm_driver #(axi4_transaction);
    `uvm_component_utils(axi4_driver)

    virtual axi4_if.MP vif;

    function new(string name = "axi4_driver", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual task run_phase(uvm_phase phase);
        forever begin
            seq_item_port.get_next_item(req);
            if (req.write)
                do_write(req);
            else
                do_read(req);
            seq_item_port.item_done();
        end
    endtask

    virtual task do_write(axi4_transaction txn);
        // AW channel
        vif.cb.awid     <= txn.id;
        vif.cb.awaddr   <= txn.addr;
        vif.cb.awlen    <= txn.len;
        vif.cb.awsize   <= txn.size;
        vif.cb.awburst  <= txn.burst;
        vif.cb.awlock   <= txn.lock;
        vif.cb.awcache  <= txn.cache;
        vif.cb.awprot   <= txn.prot;
        vif.cb.awqos    <= txn.qos;
        vif.cb.awregion <= txn.region;
        vif.cb.awvalid  <= 1'b1;
        @vif.cb;
        while (vif.cb.awready == 1'b0) @vif.cb;
        vif.cb.awvalid <= 1'b0;

        // W channel (burst beats)
        for (int beat = 0; beat <= txn.len; beat++) begin
            vif.cb.wdata  <= txn.data[beat];
            vif.cb.wstrb  <= txn.strb[beat];
            vif.cb.wlast  <= (beat == txn.len);
            vif.cb.wvalid <= 1'b1;
            @vif.cb;
            while (vif.cb.wready == 1'b0) @vif.cb;
        end
        vif.cb.wvalid <= 1'b0;
        vif.cb.wlast  <= 1'b0;

        // B channel
        vif.cb.bready <= 1'b1;
        @vif.cb;
        while (vif.cb.bvalid == 1'b0) @vif.cb;
        txn.resp = vif.cb.bresp;
        vif.cb.bready <= 1'b0;
    endtask

    virtual task do_read(axi4_transaction txn);
        // AR channel
        vif.cb.arid     <= txn.id;
        vif.cb.araddr   <= txn.addr;
        vif.cb.arlen    <= txn.len;
        vif.cb.arsize   <= txn.size;
        vif.cb.arburst  <= txn.burst;
        vif.cb.arlock   <= txn.lock;
        vif.cb.arcache  <= txn.cache;
        vif.cb.arprot   <= txn.prot;
        vif.cb.arqos    <= txn.qos;
        vif.cb.arregion <= txn.region;
        vif.cb.arvalid  <= 1'b1;
        @vif.cb;
        while (vif.cb.arready == 1'b0) @vif.cb;
        vif.cb.arvalid <= 1'b0;

        // R channel (burst beats)
        txn.data = new[txn.len + 1];
        for (int beat = 0; beat <= txn.len; beat++) begin
            vif.cb.rready <= 1'b1;
            @vif.cb;
            while (vif.cb.rvalid == 1'b0) @vif.cb;
            txn.data[beat] = vif.cb.rdata;
            txn.resp       = vif.cb.rresp;
            txn.last       = vif.cb.rlast;
            if (vif.cb.rlast) break;
        end
        vif.cb.rready <= 1'b0;
    endtask

endclass : axi4_driver

`endif // AXI4_DRIVER_SV
"""

    def _emit_axi4_monitor(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4_MONITOR_SV
`define AXI4_MONITOR_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4_monitor extends uvm_monitor;
    `uvm_component_utils(axi4_monitor)

    virtual axi4_if.MP vif;
    uvm_analysis_port #(axi4_transaction) ap;

    function new(string name = "axi4_monitor", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        ap = new("ap", this);
    endfunction

    virtual task run_phase(uvm_phase phase);
        fork
            write_monitor();
            read_monitor();
        join_none
    endtask

    virtual task write_monitor();
        bit [$bits(vif.cb.awid)-1:0]    awid_l;
        bit [$bits(vif.cb.awaddr)-1:0]  awaddr_l;
        bit [7:0]                         awlen_l;
        axi4_transaction txn;
        int beat;
        forever begin
            @vif.cb;
            if (vif.cb.awvalid && vif.cb.awready) begin
                awid_l   = vif.cb.awid;
                awaddr_l = vif.cb.awaddr;
                awlen_l  = vif.cb.awlen;
                txn = axi4_transaction::type_id::create("txn");
                txn.id   = awid_l;
                txn.addr = awaddr_l;
                txn.len  = awlen_l;
                txn.write = 1'b1;
                txn.data = new[awlen_l + 1];
                txn.strb = new[awlen_l + 1];
                beat = 0;
            end
            if (vif.cb.wvalid && vif.cb.wready && txn != null) begin
                txn.data[beat] = vif.cb.wdata;
                txn.strb[beat] = vif.cb.wstrb;
                beat++;
                if (vif.cb.wlast) begin
                    // Wait for B
                    while (!(vif.cb.bvalid && vif.cb.bready)) @vif.cb;
                    txn.resp = vif.cb.bresp;
                    ap.write(txn);
                    txn = null;
                end
            end
        end
    endtask

    virtual task read_monitor();
        bit [$bits(vif.cb.arid)-1:0]   arid_l;
        bit [$bits(vif.cb.araddr)-1:0] araddr_l;
        bit [7:0]                        arlen_l;
        axi4_transaction txn;
        int beat;
        forever begin
            @vif.cb;
            if (vif.cb.arvalid && vif.cb.arready) begin
                arid_l   = vif.cb.arid;
                araddr_l = vif.cb.araddr;
                arlen_l  = vif.cb.arlen;
                txn = axi4_transaction::type_id::create("txn");
                txn.id    = arid_l;
                txn.addr  = araddr_l;
                txn.len   = arlen_l;
                txn.write = 1'b0;
                txn.data  = new[arlen_l + 1];
                beat = 0;
            end
            if (vif.cb.rvalid && vif.cb.rready && txn != null) begin
                txn.data[beat] = vif.cb.rdata;
                txn.resp       = vif.cb.rresp;
                txn.last       = vif.cb.rlast;
                beat++;
                if (vif.cb.rlast) begin
                    ap.write(txn);
                    txn = null;
                end
            end
        end
    endtask

endclass : axi4_monitor

`endif // AXI4_MONITOR_SV
"""

    def _emit_axi4_agent(self, pkg_name: str) -> str:
        return f"""`ifndef AXI4_AGENT_SV
`define AXI4_AGENT_SV

import {pkg_name}::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class axi4_agent extends uvm_agent;
    `uvm_component_utils(axi4_agent)

    axi4_sequencer sqr;
    axi4_driver    drv;
    axi4_monitor   mon;

    function new(string name = "axi4_agent", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        sqr = axi4_sequencer::type_id::create("sqr", this);
        drv = axi4_driver::type_id::create("drv", this);
        mon = axi4_monitor::type_id::create("mon", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        drv.seq_item_port.connect(sqr.seq_item_export);
    endfunction

endclass : axi4_agent

`endif // AXI4_AGENT_SV
"""
