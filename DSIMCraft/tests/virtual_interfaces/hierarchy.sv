interface bus_if;logic[7:0] data;endinterface
module wrapper;bus_if bus();endmodule
module top;
 wrapper inst();virtual bus_if vif;
 initial begin vif=inst.bus;vif.data=8'hac;if(inst.bus.data!==8'hac)$fatal(1,"hierarchical actual");$display("TRACE virtual hierarchy %0h",inst.bus.data);end
endmodule
