`timescale 1ns/1ps
interface bus #(parameter W=8,BIAS=2);
 logic[W-1:0] value=1;
 modport client(import function logic[W-1:0] read(input integer delta=BIAS), task write(input logic[W-1:0] next_value,output integer observed),input value);
 function automatic logic[W-1:0] read(input integer delta=BIAS);read=value+delta;endfunction
 task automatic write(input logic[W-1:0] next_value,output integer observed);
  #2;value=next_value;observed=read(1);
 endtask
modport unused(import task external_method(input integer n));
endinterface
module driver(bus.client b);
 integer got,observed;
 initial begin got=b.read();b.write(.observed(observed),.next_value(got+3));
  #1;if(got!=3||observed!=7||b.value!=6)$fatal(1,"FAIL driver");
  $display("TRACE basic driver %0d %0d %0d",got,observed,b.value);end
endmodule
module wrapper(bus.client p);driver d(p);endmodule
module top;
 bus #(5) b();wrapper w(b.client);integer direct;
 initial begin #1;direct=b.read(4);if(direct!=5||$bits(b.read())!=5)$fatal(1,"FAIL direct");
  #3;if(b.value!=6)$fatal(1,"FAIL shared");$display("TRACE basic top %0d %0d",direct,b.value);#1;$finish;end
endmodule
