`include "uvm_macros.svh"
import uvm_pkg::*;
class wide_payload extends uvm_sequence_item;
  logic[8191:0] value;
  `uvm_object_utils_begin(wide_payload)
    `uvm_field_int(value,UVM_PACK|UVM_UNPACK)
  `uvm_object_utils_end
  function new(string name="wide_payload");super.new(name);endfunction
endclass
class dsim_packing extends uvm_test;
  `uvm_component_utils(dsim_packing)
  function new(string name="dsim_packing",uvm_component parent=null);super.new(name,parent);endfunction
  task run_phase(uvm_phase phase);
    wide_payload original,duplicate;
    logic[8191:0] expected;
    bit payload_bits[];
    int packed_size,unpacked_size;
    phase.raise_objection(this);
    original=wide_payload::type_id::create("original");
    duplicate=wide_payload::type_id::create("duplicate");
    expected='0;expected[8191]=1;expected[4096]=1;expected[31:0]=32'hdeadbeef;
    original.value=expected;
    packed_size=original.pack(payload_bits);
    original.value='0;
    unpacked_size=duplicate.unpack(payload_bits);
    if(packed_size<=0||packed_size!=unpacked_size)`uvm_fatal("SIZE","packed size mismatch")
    if(duplicate.value!==expected)`uvm_fatal("DATA","wide payload mismatch")
    #1;$display("TRACE REAL_UVM_SMOKE PACKING %0d %0d",packed_size,unpacked_size);
    phase.drop_objection(this);
  endtask
endclass
module top;
  initial run_test("dsim_packing");
  initial begin #100;$fatal(1,"UVM packing watchdog expired");end
endmodule
