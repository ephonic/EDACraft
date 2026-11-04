`timescale 1ns/1ps
interface lane_if;
 logic[7:0] value=0;
 modport rw(output value);
 modport ro(input value);
endinterface
module producer(lane_if.rw b);
 initial begin #0.5;b.value=7;#1;b.value=19;end
endmodule
module consumer(lane_if.ro b,output logic[7:0] q);
 always @* q=b.value;
endmodule
module lane(output logic[7:0] q);
 lane_if bus();producer p(bus);consumer c(bus,q);
endmodule
module top;
 wire[7:0] one,two;lane a(one);lane b(two);
 initial begin #2.5;$finish;end
endmodule
