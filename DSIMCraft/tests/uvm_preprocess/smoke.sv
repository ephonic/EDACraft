`include "uvm_macros.svh"
import uvm_pkg::*;
class dsim_smoke extends uvm_test;
 `uvm_component_utils(dsim_smoke)
 function new(string name="dsim_smoke",uvm_component parent=null);super.new(name,parent);endfunction
 task run_phase(uvm_phase phase);
  phase.raise_objection(this);#1;$display("TRACE REAL_UVM_SMOKE");phase.drop_objection(this);
 endtask
endclass
module top;initial run_test("dsim_smoke");endmodule
