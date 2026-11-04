typedef logic[7:0] payload_t;
interface bus_if;payload_t data;endinterface
package shadow;
 typedef logic[15:0] payload_t;
 typedef virtual bus_if vif_t;
 class holder;vif_t vif;endclass
endpackage
module top;
 bus_if bus();shadow::holder h;
 initial begin h=new();h.vif=bus;h.vif.data=8'ha5;if($bits(h.vif.data)!=8||bus.data!==8'ha5)$fatal(1,"interface lexical type");$display("TRACE virtual lexical %0d %0h",$bits(h.vif.data),bus.data);end
endmodule
