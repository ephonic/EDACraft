`include "uvm_macros.svh"
import uvm_pkg::*;

class packet extends uvm_sequence_item;
  `uvm_object_utils(packet)
  int value;
  function new(string name="packet");super.new(name);endfunction
endclass
class tagged_packet extends packet;
  `uvm_object_utils(tagged_packet)
  function new(string name="tagged_packet");super.new(name);value=100;endfunction
endclass
class packet_sequence extends uvm_sequence#(packet);
  `uvm_object_utils(packet_sequence)
  int count=3;
  function new(string name="packet_sequence");super.new(name);endfunction
  task body();
    for(int i=0;i<count;i++)begin
      packet item;
      item=packet::type_id::create("item");
      start_item(item);item.value+=i;finish_item(item);
    end
  endtask
endclass
class packet_driver extends uvm_driver#(packet);
  `uvm_component_utils(packet_driver)
  uvm_analysis_port#(packet) analysis;
  function new(string name,uvm_component parent);
    super.new(name,parent);analysis=new("analysis",this);
  endfunction
  task run_phase(uvm_phase phase);
    forever begin
      packet item;
      seq_item_port.get_next_item(item);
      #1;
      $display("TRACE UVM_ITEM %0d %s",item.value,item.get_type_name());
      analysis.write(item);seq_item_port.item_done();
    end
  endtask
endclass
class packet_scoreboard extends uvm_component;
  `uvm_component_utils(packet_scoreboard)
  uvm_analysis_imp#(packet,packet_scoreboard) input_port;
  int seen,total;
  function new(string name,uvm_component parent);
    super.new(name,parent);input_port=new("input_port",this);
  endfunction
  function void write(packet item);
    seen++;total+=item.value;
    if(item.get_type_name()!="tagged_packet")`uvm_error("TYPE","factory override was lost")
  endfunction
endclass
class packet_env extends uvm_env;
  `uvm_component_utils(packet_env)
  packet_driver driver;
  uvm_sequencer#(packet) sequencer;
  packet_scoreboard scoreboard;
  int count;
  function new(string name,uvm_component parent);super.new(name,parent);endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if(!uvm_config_db#(int)::get(this,"","count",count))`uvm_fatal("CONFIG","count was not configured")
    driver=packet_driver::type_id::create("driver",this);
    sequencer=uvm_sequencer#(packet)::type_id::create("sequencer",this);
    scoreboard=packet_scoreboard::type_id::create("scoreboard",this);
  endfunction
  function void connect_phase(uvm_phase phase);
    driver.seq_item_port.connect(sequencer.seq_item_export);
    driver.analysis.connect(scoreboard.input_port);
  endfunction
endclass
class dsim_integration extends uvm_test;
  `uvm_component_utils(dsim_integration)
  packet_env env;
  function new(string name="dsim_integration",uvm_component parent=null);super.new(name,parent);endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    packet::type_id::set_type_override(tagged_packet::get_type());
    env=packet_env::type_id::create("env",this);
  endfunction
  task run_phase(uvm_phase phase);
    packet_sequence sequence_value;
    phase.raise_objection(this);
    sequence_value=packet_sequence::type_id::create("sequence_value");
    sequence_value.count=env.count;sequence_value.start(env.sequencer);
    #1;
    if(env.scoreboard.seen!=3||env.scoreboard.total!=303)`uvm_fatal("SCOREBOARD","transaction count or sum mismatch")
    $display("TRACE REAL_UVM_SMOKE INTEGRATION %0d %0d",env.scoreboard.seen,env.scoreboard.total);
    phase.drop_objection(this);
  endtask
endclass
module top;
  initial begin
    uvm_config_db#(int)::set(null,"uvm_test_top.env","count",3);
    run_test("dsim_integration");
  end
  initial begin #100;$fatal(1,"UVM integration watchdog expired");end
endmodule
