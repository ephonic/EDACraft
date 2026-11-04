`timescale 1ns/1ps
module lane #(parameter STEP=3,PERIOD=2)(output logic [7:0] q,output logic error);
 logic [7:0] d;
 integer i;
 wire [7:0] y;
 assign y=d+STEP;
 // The wrapper's variable output is driven through a child port.
 transfer t(y,q);
 initial begin
  error=0;d=0;
  for(i=0;i<8;i=i+1)begin
   #PERIOD;
   if(q!==d+STEP)error=1;
   d=d+STEP;
  end
 end
endmodule
module transfer(input [7:0] d,output [7:0] y);
 assign y=d;
endmodule
module top;
 logic [7:0] a,b;
 logic ea,eb;
 lane #(3,2) left(a,ea);
 lane #(7,3) right(b,eb);
endmodule
