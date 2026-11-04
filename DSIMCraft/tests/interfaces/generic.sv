`timescale 1ns/1ps
interface bus_if;
 logic[7:0] value=0;
 modport rw(output value);
endinterface
module drive(input logic[7:0] v,interface b);
 initial begin #1;b.value=v;#1;b.value=b.value+3;end
endmodule
module plain(bus_if b,bus_if other);
 initial begin #1.5;other.value=b.value+1;end
endmodule
module top;
 bus_if a();bus_if b();drive d(8'h25,a);plain p(a,b);
 initial begin #2.5;if(a.value!==8'h28||b.value!==8'h26)$fatal(1,"FAIL generic");
 $display("TRACE generic %h %h",a.value,b.value);#1;$finish;end
endmodule
