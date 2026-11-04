interface bus_if;logic data;modport source(output data);endinterface
package types;
 typedef virtual interface bus_if.source vif_t;
 class holder;vif_t value;endclass
endpackage
module top;
 import types::*;
 bus_if a();holder h;
 initial begin h=new();h.value=a.source;h.value.data=1;if(a.data!==1)$fatal(1,"package type");$display("TRACE virtual package %0d",a.data);end
endmodule
