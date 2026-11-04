`timescale 1ns/1ps
interface bus_if;
 logic[7:0] value=0;
 modport rw(output value);
 modport ro(input value);
endinterface
module writer(bus_if.rw p,input logic[7:0] data);
 initial begin #1;p.value=data;#1;p.value=p.value+1;end
endmodule
module wrapper(bus_if.rw port,input logic[7:0] data);
 writer child(.data(data),.p(port));
endmodule
module reader(bus_if.ro p,output logic[7:0] seen);
 always @* seen=p.value;
endmodule
module top;
 bus_if one();bus_if two();wire[7:0] seen;
 wrapper a(.port(one),.data(8'h20));reader ra(one,seen);
 wrapper b(two.rw,8'h70);
 initial begin #1.5;if(one.value!==8'h20||two.value!==8'h70||seen!==8'h20)$fatal(1,"FAIL forwarding first");
 #1;if(one.value!==8'h21||two.value!==8'h71||seen!==8'h21)$fatal(1,"FAIL forwarding alias");
 $display("TRACE forwarding %h %h %h",one.value,two.value,seen);#1;$finish;end
endmodule
