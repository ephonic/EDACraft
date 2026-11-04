`timescale 1ns/1ps
interface wire_if;
 tri[3:0] value;
 modport io(inout value);
endinterface
module drive(wire_if.io p,input logic en,input logic[3:0] data);
 assign p.value=en?data:4'bzzzz;
endmodule
module top;
 wire_if bus();reg e1=0,e2=0;reg[3:0] d1=4'h5,d2=4'h5;
 drive a(bus,e1,d1);drive b(bus.io,e2,d2);
 initial begin #0.5;if(bus.value!==4'hz)$fatal(1,"FAIL highz");
 e1=1;#0.5;if(bus.value!==4'h5)$fatal(1,"FAIL first driver");
 e2=1;#0.5;if(bus.value!==4'h5)$fatal(1,"FAIL shared driver");
 d2=4'ha;#0.5;if(bus.value!==4'hx)$fatal(1,"FAIL conflict");
 e1=0;#0.5;if(bus.value!==4'ha)$fatal(1,"FAIL release");
 $display("TRACE nets %h",bus.value);#0.5;$finish;end
endmodule
