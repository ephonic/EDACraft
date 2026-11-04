`include "uvm_macros.svh"
import uvm_pkg::*;
class uvm_payload extends uvm_sequence_item;
  rand bit[7:0] value;
  string label;
  constraint legal_value {value inside {[10:20]};}
  `uvm_object_utils_begin(uvm_payload)
    `uvm_field_int(value,UVM_ALL_ON)
    `uvm_field_string(label,UVM_ALL_ON)
  `uvm_object_utils_end
  function new(string name="uvm_payload");super.new(name);endfunction
endclass
class dsim_utilities extends uvm_test;
  `uvm_component_utils(dsim_utilities)
  function new(string name="dsim_utilities",uvm_component parent=null);super.new(name,parent);endfunction
  task run_phase(uvm_phase phase);
    uvm_payload original,duplicate;
    uvm_object copied;
    uvm_event event_value;
    phase.raise_objection(this);
    original=uvm_payload::type_id::create("original");
    original.srandom(123);
    if(!original.randomize())`uvm_fatal("RANDOM","randomize failed")
    if(original.value<10||original.value>20)`uvm_fatal("CONSTRAINT","constraint was ignored")
    original.label="payload";
    copied=original.clone();
    if(!$cast(duplicate,copied))`uvm_fatal("CLONE","clone returned wrong type")
    if(duplicate==original||!original.compare(duplicate))`uvm_fatal("COMPARE","clone mismatch")
    original.value=30;original.label="changed";
    if(duplicate.value<10||duplicate.value>20||duplicate.label!="payload")`uvm_fatal("ISOLATION","clone shares field storage")
    duplicate.copy(original);
    if(!original.compare(duplicate))`uvm_fatal("COPY","copy mismatch")
    event_value=new("event_value");
    fork
      begin #1;event_value.trigger(original);end
      begin
        event_value.wait_trigger();
        if(event_value.get_trigger_data()!=original)`uvm_fatal("EVENT","trigger data mismatch")
      end
    join
    #1;$display("TRACE REAL_UVM_SMOKE UTILITIES 1");
    phase.drop_objection(this);
  endtask
endclass
module top;
  initial run_test("dsim_utilities");
  initial begin #100;$fatal(1,"UVM utilities watchdog expired");end
endmodule
