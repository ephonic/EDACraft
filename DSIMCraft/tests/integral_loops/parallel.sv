`timescale 1ns/1ps
module lane(output reg done=0);
 reg [31:0] i=0,q=0;
 initial begin #1;for(i=0;i<101;i++)q=q*32'd69069+1;done=1;end
endmodule
module top;
 wire first,second;lane u(first),v(second);
 initial begin #2;$finish;end
endmodule
